# ESPN Data Source Migration

Switched the NBA data source away from `stats.nba.com` (via the `nba_api` package) to ESPN's public JSON endpoints

## Background

The backend originally fetched all NBA data through the community-maintained
`nba_api` Python library, which wraps `https://stats.nba.com/stats/...`.
I used three endpoints from it:

- `scoreboardv2.ScoreboardV2` — today's games
- `playergamelog.PlayerGameLog` — recent games per player
- `playerindex.PlayerIndex` — full active-player list with season averages

I also used `nba_api.stats.static.players` (a bundled offline list) as a
fallback for resolving names to NBA player IDs.

`stats.nba.com` is unreliable: it silently throttles connections it
doesn't like by hanging the request until it times out. I saw this
both from AWS Lambda (where it was always blocked) and from my
home network (intermittent 30-second read timeouts).
Even after sending full browser-style headers (`User-Agent`, `Referer`,
`Origin`, `x-nba-stats-origin`), `curl` calls hung for 15+ seconds and
returned nothing. That confirmed the issue was IP-level soft blocking,
not headers.

## Why ESPN

I considered three options before picking one:

1. `balldontlie.io` — clean REST API, free tier of 5 requests/minute.
   Easy migration but rate-limited.
2. ESPN's hidden JSON endpoints — same endpoints `espn.com` uses
   internally. No auth, no key, very generous rate limits in practice.
3. `cdn.nba.com` static JSON files — reliable but only covers
   schedules, not player game logs.

ESPN was the right pick because it covers everything I need in one
provider, has no auth requirement, and isn't aggressively blocked.
The trade-off is that the endpoints are undocumented, so I had to
reverse-engineer their shape.

## How the endpoints were found

ESPN's mobile and web apps make requests to public hosts. The two
relevant ones are:

- `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/...`
- `https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/...`

I confirmed each one by hitting it with `curl` and inspecting the JSON shape with a small
Python script before writing any code.

## What I probed

Each probe was a `curl` call piped into Python to print the JSON keys

### 1. Scoreboard

```
GET https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD
```

Returned an `events` array with `id`, `name`, `status.type.name`, and
nested `competitions[0].competitors[]` containing home/away teams and
abbreviations. Confirmed 3 games for the test date.

### 2. Team roster

```
GET https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{abbr}/roster
```

Returned `athletes[]` with player ID, full name, position, jersey, etc.
Useful as a backup, but not the primary path because it requires 30
team calls to cover the league.

### 3. Per-player game log

```
GET https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{playerId}/gamelog
```

Returned a top-level `events` map (keyed by event ID) with metadata
like `gameDate` and `opponent`, plus a `seasonTypes` array. Each
`seasonTypes[].categories[].events[]` entry had a `stats` array
indexed by the top-level `labels` array:

```
labels: [MIN, FG, FG%, 3PT, 3P%, FT, FT%, REB, AST, BLK, STL, PF, TO, PTS]
```

Stats like `3PT` were strings of the form `"made-attempted"` (e.g.
`"7-12"`), so I wrote a `_split_made` helper to pull the made count.

### 4. League-wide season stats

```
GET https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete?limit=1000&season=2026
```

Returned every player who has stats this season in a single call
(~227 players). Each entry had:

- `athlete` — id, displayName, teams, position, jersey
- `categories` — `general`, `offensive`, `defensive`, each with a
  `values` array

Top-level `categories[].labels` had duplicates (`REB` appeared twice,
once for totals and once for averages), so I used `categories[].names`
instead — those are unique semantic keys like `avgRebounds` and
`avgPoints`.

### 5. Player search

```
GET https://site.api.espn.com/apis/common/v3/search?query=NAME&type=player
```

Returned `items[]` with `id`, `displayName`, `league`. I use this as
a fallback for players who haven't played enough games this season to
appear in the season-stats endpoint (e.g., recently activated players,
or players on extended injury).

## What was implemented

### `backend/src/fetcher.py` — full rewrite

The class kept same method signatures so callers wouldn't have to change. Internally:

- `get_today_games(max_lookahead_days)` now hits ESPN's scoreboard
  for each candidate date and returns a DataFrame with `GAME_ID`,
  `GAMECODE` (constructed as `YYYYMMDD/AWAYHOME` to match the format
  the existing `Games.tsx` page parses), `GAME_STATUS_TEXT`,
  `ARENA_NAME`, etc.
- `get_player_stats(player_id, num_games, timeout)` hits the gamelog
  endpoint, parses the labelled stats array, joins each row with its
  game date from the top-level events map, drops anything that isn't
  regular season or postseason, and returns a DataFrame sorted by
  date descending. The output columns match exactly what
  `analyzer.py` already expects: `GAME_DATE, MIN, PTS, REB, AST,
  BLK, STL, FG3M, MATCHUP`.
- `get_active_players_with_stats(timeout)` hits the bulk
  byathlete endpoint and returns a list of dicts shaped like
  `{id, name, team, jersey, position, pts, reb, ast}`.
- `find_player_id(name, players)` looks up an ESPN player ID by name,
  first against a passed-in list (typically the cached players list),
  with a search-endpoint fallback for misses.

Module-level constants `ESPN_BASE`, `ESPN_WEB_BASE`, and `HEADERS`
hold the host URLs and a Chrome-style User-Agent.

### `backend/app.py` — targeted edits

- Deleted the hardcoded `KNOWN_PLAYERS` map (32 hand-maintained
  name-to-NBA-ID entries) and the `fetch_player_id_from_nba_api`
  static-list fallback.
- Added a single helper `_get_cached_active_players()` that returns
  the cached ESPN players list, refreshing it on cache miss.
- `generate_all_picks()` now builds its name-to-ID map from the
  cached active-players list and falls back to
  `fetcher.find_player_id()` for misses. The map is no longer
  hardcoded — every player resolution goes through ESPN.
- The `/api/allPlayers` route no longer imports
  `nba_api.stats.endpoints.playerindex`. It calls
  `fetcher.get_active_players_with_stats()` and reuses the existing
  24-hour `players_cache`.
- A small earlier change set `app.run(use_reloader=False)` to stop
  Flask debug mode from doubling every NBA-API call. This is still
  useful with ESPN to avoid wasted calls.

## ID space change

The old code passed NBA-issued player IDs (e.g. `201939` for Stephen
Curry). The new code passes ESPN-issued player IDs (e.g. `3975` for
Stephen Curry).

### Frontend headshot URL swap

The headshot CDN was tied to the old NBA IDs, so player photos broke after the ID swap. Updated both `Players.tsx` and `Picks.tsx` to use ESPN's CDN, which works with the new IDs:

- Old: `https://cdn.nba.com/headshots/nba/latest/260x190/{id}.png`
- New: `https://a.espncdn.com/i/headshots/nba/players/full/{id}.png`

### Team abbreviation normalization

ESPN uses non-standard 2- or 4-char abbreviations for five teams: `NY`, `GS`, `NO`, `SA`, `UTAH`. The frontend's `parseTeams()` slices `GAMECODE` assuming exactly 3 chars per team, so `NY` + `ATL` came out as `NYA` / `TL` and broke logo and name lookups. Added a `TEAM_ABBR_OVERRIDES` map and `_normalize_abbr()` helper in `fetcher.py` that converts ESPN's codes to the NBA standard (`NY → NYK`, `GS → GSW`, `NO → NOP`, `SA → SAS`, `UTAH → UTA`). Applied in both `get_today_games()` and `get_active_players_with_stats()` so all downstream consumers see consistent 3-char codes.

### Player name normalization

The Odds API spells generational suffixes without a period (`"Tim Hardaway Jr"`, `"Kelly Oubre Jr"`) while ESPN includes one (`"Tim Hardaway Jr."`). Exact lowercase string matching missed these players in two places:
- `_filter_players_today()` in `app.py` filtered them out of `/api/allPlayers?today_only=true`.
- The fuzzy fallback in `find_player_id()` treated `"jr"` as the last name and matched the first random player containing `"jr"`.

Added a `normalize_name()` helper in `fetcher.py` that lowercases and strips periods/commas, plus a `_NAME_SUFFIXES` set (`jr`, `sr`, `ii`, `iii`, `iv`) used to skip suffix tokens during fuzzy last-name matching. Applied in `find_player_id()`, `_filter_players_today()`, and `generate_all_picks()`'s ID lookup.

## Possible improvements

2. Increase parallelism in `generate_all_picks` (currently `max_workers=2`, `sleep=1.5s` — tuned for stats.nba.com). ESPN can handle 4–5 workers at 0.3s spacing.
4. Retry+backoff wrapper around ESPN calls — one retry on 0.5s backoff covers most transient 5xxs.
5. Tune SAM deploy cache TTLs for freshness, not network reachability — the AWS-block workaround is no longer needed.
6. Replace the `/search` fallback in `find_player_id` with `/teams/{abbr}/roster` (search occasionally returns retired players).
