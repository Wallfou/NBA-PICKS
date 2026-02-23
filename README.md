## Bugs and Improvements During Development


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

---

### 4. Directional Cushion Logic Bug in `analyzer.py`

**Problem:** OVER/UNDER picks were selected using the mean vs. the line, but `_calculate_cushion()` used `abs(dist)` — so being far below the line would inflate cushion even when the pick was OVER, and vice versa. Cushion was always "good" when the mean was far from the line, regardless of whether that distance supported the pick direction.

**Root cause:** Cushion should be *directional* — it should reward distance in the direction of the pick and penalize distance against it:

- If pick is **OVER**: cushion increases when `average - line > 0`
- If pick is **UNDER**: cushion increases when `line - average > 0`

**Fix:** Pass `pick_direction` into `_calculate_cushion()` and compute a signed distance:

---

### 5. Noisy Hit Rate with Small Sample Size

**Problem:** Hit rate was calculated as raw wins / games (e.g., 7/10 = 70%). With only 10 recent games, this is extremely noisy — a single game can swing confidence dramatically. This made confidence scores unstable and overly reactive.

**Root cause:** Small sample sizes exaggerate variance. A 7/10 stretch may look strong, but statistically it is fragile and highly sensitive to one additional result.

**Fix:** Replaced raw hit rate with a smoothed estimate using a **Beta prior**:

```
p̂ = (hits + α) / (n + α + β)
```

Using a mild prior of:

- α = 2  
- β = 2  

This gently pulls estimates toward 50% without overpowering real data. The effect:

- 7/10 (70%) → slightly reduced toward ~64%
- 1/2 (50%) → pulled closer to 50% baseline
- 0 games → defaults to 50% instead of 0%

