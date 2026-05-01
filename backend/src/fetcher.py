import requests
import pandas as pd
from datetime import datetime, timedelta

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
ESPN_WEB_BASE = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ESPN abbreviates a handful of teams differently from the NBA's standard
# 3-char codes. Normalize so downstream consumers can rely on the canonical form
TEAM_ABBR_OVERRIDES = {
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "SA": "SAS",
    "UTAH": "UTA",
}


def _normalize_abbr(abbr: str) -> str:
    return TEAM_ABBR_OVERRIDES.get(abbr, abbr)


# Generational suffixes the Odds API and ESPN format inconsistently
# "Tim Hardaway Jr" vs "Tim Hardaway Jr."
_NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def normalize_name(name: str) -> str:
    """Lowercase, strip periods/commas, used for cross-source name comparison."""
    return (name or "").lower().replace(".", "").replace(",", "").strip()


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _split_made(value):
    if isinstance(value, str) and "-" in value:
        return _to_float(value.split("-")[0])
    return _to_float(value)


class NBAFetcher:
    def __init__(self):
        self.resolved_game_date = None

    def get_today_games(self, max_lookahead_days: int = 7):
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for day_offset in range(max_lookahead_days):
            check_date = base_date + timedelta(days=day_offset)
            date_str = check_date.strftime('%Y-%m-%d')
            date_url = check_date.strftime('%Y%m%d')

            try:
                resp = requests.get(
                    f"{ESPN_BASE}/scoreboard",
                    params={"dates": date_url},
                    headers=HEADERS,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"ESPN scoreboard error for {date_str}: {e}")
                continue

            events = data.get("events") or []
            if events:
                rows = []
                for ev in events:
                    competitions = ev.get("competitions") or [{}]
                    competitors = competitions[0].get("competitors") or []
                    home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                    away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                    home_abbr = _normalize_abbr((home.get("team") or {}).get("abbreviation") or "")
                    away_abbr = _normalize_abbr((away.get("team") or {}).get("abbreviation") or "")
                    venue = (competitions[0].get("venue") or {}).get("fullName") or ""
                    status = (ev.get("status") or {}).get("type") or {}
                    rows.append({
                        "GAME_ID": str(ev.get("id") or ""),
                        "GAMECODE": f"{date_url}/{away_abbr}{home_abbr}",
                        "GAME_DATE_EST": date_str,
                        "HOME_TEAM_ABBREVIATION": home_abbr,
                        "VISITOR_TEAM_ABBREVIATION": away_abbr,
                        "GAME_STATUS_TEXT": status.get("shortDetail") or status.get("description") or "",
                        "GAME_STATUS_ID": status.get("id") or 0,
                        "ARENA_NAME": venue,
                    })

                df = pd.DataFrame(rows)
                if 'GAME_ID' in df.columns:
                    df = df.drop_duplicates(subset=['GAME_ID'])
                if day_offset == 0:
                    print(f"Found {len(df)} games today ({date_str})")
                else:
                    print(f"No games today. Found {len(df)} games on {date_str} (+{day_offset} day{'s' if day_offset > 1 else ''})")
                self.resolved_game_date = date_str
                return df

            print(f"No games on {date_str}, checking next day...")

        print(f"No games found within the next {max_lookahead_days} days")
        self.resolved_game_date = None
        return pd.DataFrame()

    def get_player_stats(self, player_id, num_games: int = 15, timeout: int = 15):
        resp = requests.get(
            f"{ESPN_WEB_BASE}/athletes/{player_id}/gamelog",
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        labels = data.get("labels") or []
        idx = {label: i for i, label in enumerate(labels)}
        events_meta = data.get("events") or {}

        rows = []
        for season_type in data.get("seasonTypes") or []:
            name = (season_type.get("displayName") or "").lower()
            # Only include real games — skip preseason/all-star
            if "regular" not in name and "post" not in name:
                continue
            for category in season_type.get("categories") or []:
                # Skip per-month/by-opponent breakdowns; only the flat "events" list has eventId entries
                for ev in category.get("events") or []:
                    stats = ev.get("stats") or []
                    if not stats:
                        continue
                    eid = str(ev.get("eventId") or "")
                    meta = events_meta.get(eid) or {}
                    rows.append({
                        "GAME_ID": eid,
                        "GAME_DATE": meta.get("gameDate"),
                        "MATCHUP": (meta.get("opponent") or {}).get("displayName") or "",
                        "MIN": _to_float(stats[idx["MIN"]]) if "MIN" in idx and idx["MIN"] < len(stats) else 0.0,
                        "PTS": _to_float(stats[idx["PTS"]]) if "PTS" in idx and idx["PTS"] < len(stats) else 0.0,
                        "REB": _to_float(stats[idx["REB"]]) if "REB" in idx and idx["REB"] < len(stats) else 0.0,
                        "AST": _to_float(stats[idx["AST"]]) if "AST" in idx and idx["AST"] < len(stats) else 0.0,
                        "BLK": _to_float(stats[idx["BLK"]]) if "BLK" in idx and idx["BLK"] < len(stats) else 0.0,
                        "STL": _to_float(stats[idx["STL"]]) if "STL" in idx and idx["STL"] < len(stats) else 0.0,
                        "FG3M": _split_made(stats[idx["3PT"]]) if "3PT" in idx and idx["3PT"] < len(stats) else 0.0,
                    })

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows).drop_duplicates(subset=["GAME_ID"])
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="coerce")
        df = df.dropna(subset=["GAME_DATE"]).sort_values("GAME_DATE", ascending=False).reset_index(drop=True)
        return df.head(num_games)

    def get_active_players_with_stats(self, timeout: int = 30):
        """Return list of {id, name, team, jersey, position, pts, reb, ast} for players
        with stats this season. Single ESPN call, ~200-500 players."""
        now = datetime.now()
        
        season_year = now.year + 1 if now.month >= 9 else now.year

        resp = requests.get(
            f"{ESPN_WEB_BASE}/statistics/byathlete",
            params={"limit": 1000, "season": season_year},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # Build {category_name: {stat_name: index}} lookups using the semantic `names` array
        cat_index = {}
        for cat in data.get("categories") or []:
            names = cat.get("names") or []
            cat_index[cat.get("name")] = {n: i for i, n in enumerate(names)}

        def _stat(values, cat_name, stat_name):
            i = cat_index.get(cat_name, {}).get(stat_name)
            if i is None or i >= len(values):
                return 0.0
            return _to_float(values[i])

        players = []
        for entry in data.get("athletes") or []:
            athlete = entry.get("athlete") or {}
            pid = athlete.get("id")
            try:
                pid_int = int(pid)
            except (TypeError, ValueError):
                continue

            cat_values = {c.get("name"): (c.get("values") or []) for c in entry.get("categories") or []}

            team_abbr = ""
            teams = athlete.get("teams") or []
            if teams:
                team_abbr = teams[0].get("abbreviation") or ""
            elif athlete.get("teamShortName"):
                team_abbr = athlete["teamShortName"]
            team_abbr = _normalize_abbr(team_abbr)

            position = (athlete.get("position") or {}).get("abbreviation") or ""

            players.append({
                "id": pid_int,
                "name": athlete.get("displayName") or "",
                "team": team_abbr,
                "jersey": str(athlete.get("jersey") or ""),
                "position": position,
                "pts": _stat(cat_values.get("offensive", []), "offensive", "avgPoints"),
                "reb": _stat(cat_values.get("general", []), "general", "avgRebounds"),
                "ast": _stat(cat_values.get("offensive", []), "offensive", "avgAssists"),
            })

        return players

    def find_player_id(self, name: str, players: list):
        """Look up an ESPN player ID by display name. Checks the pre-fetched list first,
        then falls back to ESPN's search endpoint for players not in the season-stats list
        (e.g., injured players who haven't played yet)."""
        target = normalize_name(name)
        for p in players:
            if normalize_name(p["name"]) == target:
                return p["id"]
        # Fuzzy: match by last name, ignoring generational suffixes ("Jr", "III", ...)
        parts = [t for t in target.split() if t not in _NAME_SUFFIXES]
        if parts:
            last = parts[-1]
            for p in players:
                if last in normalize_name(p["name"]):
                    return p["id"]

        try:
            resp = requests.get(
                "https://site.api.espn.com/apis/common/v3/search",
                params={"query": name, "limit": 5, "type": "player"},
                headers=HEADERS,
                timeout=8,
            )
            resp.raise_for_status()
            items = resp.json().get("items") or []
            for item in items:
                if item.get("league") == "nba" and normalize_name(item.get("displayName") or "") == target:
                    return int(item["id"])
            for item in items:
                if item.get("league") == "nba":
                    return int(item["id"])
        except Exception as e:
            print(f"ESPN search failed for {name}: {e}")
        return None
