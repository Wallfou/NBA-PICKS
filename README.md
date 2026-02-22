# NBA Picks

## Bugs and Improvements During Development

---

### 1. Slow Loading (~2 minutes)

**Problem:** The `generate_all_picks` loop was fully sequential — each of the 143 players waited for the previous NBA API call to finish. With a 30-second timeout and 6 timed-out players, that was up to 3 minutes wasted just waiting.

**Fix:** Parallelized the game-log fetches using `ThreadPoolExecutor` in two phases:

- **Phase 1 (parallel):** Launches up to 3 concurrent NBA API requests. Timed-out players now fail in 10 seconds instead of 30.
- **Phase 2 (fast):** Generates predictions purely from already-fetched data — no more API calls, no more sleeps.

---

### 2. `/api/allPlayers` Returning 500

**Problem:** The `/api/allPlayers` endpoint was called at the same time as parallel picks generation. The concurrent threads were already hammering `stats.nba.com`, and when `PlayerIndex` tried to open another connection, the NBA API throttled it — timing out after 30 seconds and returning a 500.

**Root cause:** Too much concurrency. The `PlayerIndex` call had no timeout set, so it sat and waited the full 30 seconds before giving up.

**Fix:**
- Reduced `max_workers` from 8 → 3, giving other endpoints room to breathe.
- Added a timeout to `PlayerIndex` with retry logic (up to 3 attempts, 2-second pause between each). If all attempts fail, the endpoint returns a `503` with a friendly error instead of crashing with a `500`.

---

### 3. Duplicate Games from `ScoreboardV2`

**Problem:** `ScoreboardV2` can return duplicate rows for the same game (e.g., both a scheduled and an updated entry for the same `GAME_ID`).

**Fix:** Added a `drop_duplicates(subset=['GAME_ID'])` call in the fetcher immediately after the API response, before the data is cached or returned.
