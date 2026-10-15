# Model v5: design (16/10/2026)

## Goal
Improve the v4 rating model before the Swiss lock (24/10/2026 06:00 NZDT), evidence-led: a change ships only if a walk-forward backtest says it helps. If nothing helps, v4 stays and the site says so. Also give the model a "live" mode that refits on Worlds games as they are played, for the live odds view.

## Out of scope
Website, GitHub Action and hosting (separate spec). The frozen baseline (`data/predictions_baseline.json`) is never touched. No change to the shock sd / 3-0 modal score decision unless `model/sweep_check.py` says so after the Play-In.

## Candidates
| # | Change | How it enters the model | Test |
|---|---|---|---|
| 1 | Worlds 2026 games in the fit | Add "Worlds 2026 Play-In" and "Worlds 2026 Main Event" to `TOURNAMENTS` in `model/scrape_golgg.py` (league INTL, kind international) | None: more data at the existing international weight |
| 2 | International weight `W_INTL` | Kind weight for international series (v4 = 1.0); grid 1.0, 1.5, 2.0, 3.0 | Walk-forward |
| 3 | Patch recency | Extra weight multiplier for series on the last N patches before the cut (v4 = none); grid: last 1, 2, 3 patches at x1.5 and x2 | Walk-forward |
| 4 | Team side term | Per-team blue-minus-red logit, estimated from `games_log` sides in `data/golgg_teams_2026.json` (19 Worlds teams only), shrunk toward a global blue-side effect | Game-level walk-forward on games between two Worlds teams where the side is known; used in predictions only where the side is known or set by Right of First Selection, otherwise neutral (averaged over sides) |
| 5 | Fearless pool depth | Series-level logit shift `beta * (depth_a - depth_b)` for Bo3/Bo5; depth = per team, distinct champions picked 2+ times (any pick slot; gol.gg lists picks in draft order, not by role) divided by 5, rebuilt from `games_log` using only games before the cut | Walk-forward on Bo3/Bo5 series between two Worlds teams. Chronology from gol.gg game ids (assumed increasing over time; verified first). If ids are not chronological, fall back to a late-season-only test and label the result "leakage possible" |
| 6 | 369 staleness | Stays a manual adjustment in `data/adjustments.json` (cap +/-0.405, reason + source), not a model term | Not testable |

## Evidence rule
- Test sets (as in `model/backtest_v4.py`): A = 2026 international events (refit before each event's first day); B = domestic playoffs + internationals from 01/04/2026 (refit monthly). Candidate 4 and 5 use the subsets described above.
- Metric: mean series-winner log loss (candidate 4: game log loss).
- A candidate is adopted when, against v4 on set A, it lowers mean log loss with a paired bootstrap (10,000 resamples of series) P(improvement) of 80% or more, and it does not raise set B log loss by more than 0.002.
- Adopted candidates are combined and the combination re-tested the same way; a combination that loses to its best single part ships as that part only.
- Every result (adopted or not) is written to `data/backtest_v5.json` and summarised in a new "v5" section of `MODEL_REVIEW.md`.

## Code shape
- `model/ratings_v4.py`: candidates 2, 3 and 5 become optional parameters of `fit()` / `Model` with defaults that reproduce v4 exactly. Regression check: with defaults, `build(write=False)` matches the committed `data/ratings.json` team logits to 1e-6.
- `model/side.py` (new, small): estimates candidate 4 from `games_log`; `Model.p_game` takes an optional side argument.
- `model/pools.py` (new, small): time-ordered pool depth for candidate 5.
- `model/ratings.py`: `MODEL=v5` uses v4 code with the adopted settings; default switches to v5 only if something is adopted.
- `model/backtest_v5.py` (new): runs all candidates, the bootstrap and the combination; writes `data/backtest_v5.json`.
- Live mode: `model/ratings.py` gains `AS_OF` from the environment (default today in NZDT) so the Action can refit on the latest games; live odds come from `simulate.py --results data/results_live.json` and are exported to a separate `data/dash/live.json`. Graded predictions stay in the staged `data/predictions_<stage>.json` files.

## Timeline
- 16 to 18/10: candidates 2 to 5 implemented and backtested locally (data already on disk).
- Around 19/10 (Swiss draw): Play-In games scraped (needs gol.gg, so via the GitHub Action or a network that can reach it), v5 decision made, Swiss staged run.
- Before 24/10/2026 06:00 NZDT: Swiss predictions published.

## Risks
- Small samples: set A has about 67 series, so most candidates will likely fail the evidence rule. That is an acceptable outcome.
- Candidates 4 and 5 only cover games between Worlds teams; their effect sizes will be noisy.
- gol.gg access from this machine is blocked; the Play-In scrape depends on the Action or another network.
