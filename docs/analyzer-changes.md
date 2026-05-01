# Statistical Analyzer Changes

Running log of substantive changes to `backend/src/analyzer.py` and the data feeding into it.

## 1. Pick direction is now derived from a single `p_over`

Reworked how `calculate_confidence` chooses the pick side (OVER vs UNDER) and computes the base probability.

### Before

```python
pick_direction = 'OVER' if mu > prop_line else 'UNDER'
base_prob = (1.0 - Φ(z)) if pick_direction == 'OVER' else Φ(z)
```

The side was chosen from the recent average first, then the probability was computed for *that* side. This guaranteed `base_prob ≥ 0.5` — the model couldn't disagree with the side it had just picked, so the probability was never an independent signal. A prop with `mu` 0.05 above the line still got a confident pick.

### After

A single `p_over` — the raw `P(OVER)` from one signed z-score — drives everything:

```python
z = (prop_line - mu) / sigma
p_over = 1.0 - self._normal_cdf(z)

pick_direction = 'OVER' if p_over >= 0.5 else 'UNDER'
base_prob = p_over if pick_direction == 'OVER' else 1.0 - p_over
```

`p_over` is the point of the change. Direction and edge both fall out of this one number: `base_prob = 0.5 + |p_over - 0.5|`, so the edge magnitude shows up directly in `confidence`. Before, the pick direction and the probability were tangled together. Now `p_over` sits there as a single neutral number that answers "what's the probability of OVER?" independent of any pick decision. Thin-edge props (`p_over ≈ 0.5`) now produce `confidence ≈ 50%` instead of being flipped to whichever side `mu` happened to favor.

## 2. Picks are now ranked by expected value, not confidence

The model used to be ranked purely by its own confidence — it never saw the bookmaker's price. A 68% pick at -250 was treated as better than a 55% pick at +110, even though the first has negative EV (you risk too much per win) and the second is positive EV. The fix is to thread price through the pipeline and rank by `EV = p · payout − (1 − p)`.

### Before

`odds_fetcher.convert_to_simple_format` collapsed each stat to a single median line as a `float` and dropped both over and under prices. The analyzer never saw a price, so `rank_picks` could only sort by `confidence`.

### After

**`odds_fetcher.convert_to_simple_format`** now returns

```python
{stat_type: {'line': consensus_line, 'over_price': ..., 'under_price': ...}}
```

The consensus line is the median Over line across bookmakers. Over and Under prices are the median *at that line*, so the two sides are paired apples-to-apples.

**`analyzer.analyze_player`** accepts the dict shape and attaches per-prediction:

- `over_price`, `under_price`
- `price` — the price for the picked side
- `payout` — decimal profit per unit stake (`+110 → 1.10`, `-250 → 0.40`), via the new `_american_to_payout` helper
- `ev = p · payout − (1 − p)`, with `p = confidence / 100`

**`analyzer.rank_picks`** sorts by `ev` instead of `confidence`. Signature changed to take `min_ev` (default 0.0, so positive-EV only) plus an optional `min_confidence` secondary filter. Predictions with `ev=None` (missing price) are dropped from ranking.

**`app.py`** — the `/api/picks/top` endpoint accepts a new `min_ev` query param (default 0.0) and passes both `min_ev` and `min_confidence` to `rank_picks`. The existing frontend call (`?min_confidence=65`) keeps working — it's now applied as a secondary filter on top of EV-based ranking.