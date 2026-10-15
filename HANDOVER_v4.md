# v4 model: DONE (15/10/2026 17:15 NZDT). v4 is the frozen baseline; dashboard and local file updated.

Historical notes below.

## Live state
- Baseline v3 is still the frozen baseline and the dashboard shows v3. Nothing from v4 has been published.
- Play-In Pick'Ems and Crystal Ball lock 16/10/2026 07:00 NZDT; the entered picks come from v3 (data/pickems_playin.json).

## Done
1. `model/scrape_golgg.py`: scrapes every 2026 series from gol.gg match lists -> `data/golgg_series_2026.json` (1,068 series, 2,739 games, 42 tournaments incl. all regular seasons). Note: last edit wrapped the scrape in `main()`; verify the file parses before running (`python3 -c "import ast;ast.parse(open('model/scrape_golgg.py').read())"`).
2. `model/build_games.py`: maps names to codes, derives regions, classifies kind (regular/playoffs/international/qualifier), splits the one 1-1 series into Bo1s -> `data/series_2026.json`, `data/team_map.json`. Cross-check: all 61 international series match the hand-compiled `results_2026.json`; Americas Cup (6 series) is not on gol.gg and is added from the hand file inside `ratings_v4.load_series()`.
3. `model/ratings_v4.py`: series-level Bradley-Terry with the per-series shock inside the fit (L-BFGS, analytic gradient, Hessian covariance). Defaults HALF_LIFE 120, W_REG 0.5, W_QUAL 0.6, SIGMA 0.9, TAU 1.0. Reports region gaps with sd.
4. `model/backtest_v4.py` -> `data/backtest_v4.json`. Findings (walk-forward):
   - regular-season weight 0.5 best on both test sets;
   - shock sd: internationals prefer 1.2, domestic playoffs 0.9 -> use 1.0;
   - half-life: internationals prefer 60-120, playoffs 240+ -> keep 120;
   - temperature: 0.8-1.0 -> use 0.9;
   - on international series v4 (LL 0.637) still only ties the naive "stronger region wins 70%" rule (LL 0.622), because early-season refits have no cross-region data yet. EWC-time fits are on par with naive.

## Next steps (in order)
1. Scrape 2025 internationals (gol.gg S15: "First Stand 2025", "2025 Mid-Season Invitational", "Esports World Cup 2025", "Worlds 2025 Play-In", "Worlds 2025 Main Event") and fit a region-only model on them to use as the prior MEAN for region effects in v4 (prior sd stays 1.0). Re-run backtest A; expect First Stand/MSI log loss to drop.
2. Set SIGMA=1.0, TAU=0.9 in ratings_v4 defaults; run `python3 model/ratings_v4.py`.
3. Point `simulate.py`, `predict.py`, `pickems.py` at ratings_v4 (they import `ratings`; simplest is an env switch or `import ratings_v4 as R`), re-run, compare v3 vs v4 title odds and the Play-In series.
4. Decide on T1 adjustment (+0.20 -> +0.10 recommended), re-freeze as baseline v4 only if before the Play-In lock; otherwise v4 becomes the Swiss staged run (before 24/10 06:00 NZDT) and v3 stays the frozen baseline.
5. Export dashboard datasets (`export_dashboard.py` expects ratings.json keys `elo_base`, `sd`, `p_vs_avg`, `adjustment`, `rank`, `tier`: all present in v4), rebuild local file (`build_local.py`), upload.
