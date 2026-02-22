### Bugs and Improvements During Development

1. Slow loading (~2 minutes): The generate_all_picks loop is fully sequential — each of the 143 players waits for the previous NBA API call to finish. With a 30-second timeout and 6 timed-out players, that's up to 3 minutes wasted just waiting. Parallelizing the game-log fetches with a thread pool + shorter timeout will cut this dramatically. 

The new code does two phases:
Phase 1 (parallel) — launches up to 8 concurrent NBA API requests via ThreadPoolExecutor. With 8 workers, 143 requests that each take ~0.5s should complete in roughly 9 seconds instead of ~90 seconds. Timed-out players now fail in 10 seconds instead of 30.
Phase 2 (fast) — generates predictions purely from already-fetched data, no more API calls and no more sleeps.

Additional problem:

Problem 2 — /api/allPlayers returning 500 (the real crash)
Look at the end of each traceback:
File "/Users/kennethfan/nba-picks/backend/app.py", line 453, in get_players    idx = playerindex.PlayerIndex(season='2025-26', league_id='00')
The /api/allPlayers endpoint was called at the same time as the parallel picks generation. The 8 concurrent threads were already hammering stats.nba.com, and when PlayerIndex tried to open yet another connection to the same host, the NBA API throttled/dropped it — timing out after 30s and returning a 500.
The PlayerIndex call in get_players has no timeout set, so it sits and waits the full default 30 seconds before giving up.
Root cause: too much concurrency
With 8 parallel workers all hitting stats.nba.com simultaneously (even with the 0.6s sleep per thread), you're opening 8 connections at once. When anything else (like PlayerIndex) tries to join, the NBA API throttles everything.
Two things to fix:
Reduce max_workers from 8 down to something like 3–4 to avoid saturating the connection pool
Add a timeout to the PlayerIndex call in get_players (line 453) so it fails fast and returns a proper error instead of hanging for 30 seconds and returning a 500

Two fixes applied:
max_workers reduced from 8 → 3 — only 3 concurrent NBA API connections at a time instead of 8, giving other endpoints like /api/allPlayers room to breathe.
PlayerIndex now retries up to 3 times with a 2-second pause between attempts. If all 3 fail (e.g. during a heavy picks generation run), it returns a 503 with a friendly error message instead of a 500 crash. The frontend's existing retry button on the Players page can then be used to try again once the picks generation finishes.

