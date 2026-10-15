# Worlds 2026 prediction model: critical review (15/10/2026, baseline v3)

## Verdict
The pipeline is sound and reproducible, but its out-of-sample skill is thin. On the 60 international series of 2026 (walk-forward), it scores log loss 0.628 / Brier 0.219; a naive rule "the stronger region wins 70%" scores 0.611 / 0.210; a coin flip is 0.693 / 0.250. Almost all of the model's edge is the region hierarchy. Team-level ratings, built only from playoff games, add noise rather than signal at international level. Treat series odds as rough and exact scores as near-coin-flips.

## What holds up
- Hierarchical Bradley-Terry with region effects learned from cross-region games (not hand-set).
- Temperature (0.75) and series form shock (0.8) were both backtested, and series-winner log loss / Brier improved or held.
- Simulation follows the published format: Tier1 v Tier4 and Tier2 v Tier3 in round 1, no same-region round-1 pairs, Bo3 when a result qualifies or eliminates, no rematches, QF draw per Riot's primer.
- Baseline frozen with a checksum; staged runs separate; grading code in place.

## Findings, ranked by impact
1. **No regular-season games at all.** 804 games in the fit, every one a playoff, regional final or international game. Teams have 22 to 40 weighted games. IG's two bad regular splits (35%, 40% win rate) are invisible, so IG is rated 6th; KC's 9-0 Summer regular season is invisible too. Double-elimination playoffs also over-sample good teams' wins. One IG loss (0-3 to TTG, Split 2) was dropped for a missing date.
2. **The LCK-LPL gap is statistically weak.** +0.52 logit raw (+0.39 after temperature) with region sd about 0.55 each. Head to head is 5-5 in series. The gap comes from third parties: LCK 14-2 vs LCS and 9-0 vs LCP; LPL 2-3 vs LCP (TES lost to TSW) and from EWC weighting (gap drops to +0.38 with EWC removed). Four of the top five and the champion pick rest on it.
3. **Fit and prediction are inconsistent.** The fit treats every game as independent; prediction assumes a shared per-series shock. Sweeps therefore inflate rating gaps in the fit (a 3-0 counts as three independent wins) and the Laplace covariance understates uncertainty. The temperature is partly a patch for this.
4. **Manual adjustments decide close calls.** T1 +0.20 lifts T1's title odds from 10% to 17% and flips the T1/HLE order (and Crystal Ball Q17). It is a judgment about pedigree, not a measurement. BLG -0.05 and the LCS venue +0.05 are negligible.
5. **Parameters tuned on small samples.** Temperature from 60 series (0.6 was best; 0.75 chosen by judgment), shock from 138 series, half-life 120 d never validated. Sensitivity: GEN title odds 25% to 34% across settings; KC-C9 is the matchup most sensitive to half-life (gap 0.36 to 0.80 logit).
6. **The model ignores everything but results.** Patch, meta, player stats, roster changes (except TES), side selection, Fearless pool depth, head-to-head specifics and travel all live in the dossiers and feed nothing numerically.
7. **Pick'Ems EV assumes unverified rules** (equal points per slot, independent scoring, no duplicate restriction).
8. Minor data issues: EWC group games dated "15-16/07"; MSI dates may be a day off; DCGI partial with inferred regions; team_a listed first won 70% of entered series (harmless for BT, but shows ordering bias in data entry).

## Recommended changes (in order)
1. Add 2026 regular-season games at reduced weight (e.g. 0.5) for all six leagues. Largest expected improvement.
2. Fit at series level with the shock (or down-weight games within a series) and re-estimate temperature; expect it to move toward 1.0.
3. Publish uncertainty: bootstrap intervals on title odds and region gaps; show the LCK-LPL gap with its sd on the Overview.
4. Halve the T1 adjustment to +0.10 or show both variants; keep every adjustment visible.
5. Validate half-life in the walk-forward backtest alongside temperature and shock.
6. Before the Swiss re-run (24/10 lock): fold in Play-In results and the round-1 draw; before the knockout lock: use Swiss Bo1/Bo3 results, which are the first same-patch, cross-region evidence.
7. Date and restore the dropped IG series.

## Follow-up (15/10/2026 17:15 NZDT): v4 implemented
- Data: full 2026 season from gol.gg (1,068 series / 2,739 games, all 42 tournaments incl. regular seasons; Americas Cup added from the hand file). All 61 international series matched the hand-compiled results exactly.
- Model: series-level fit with the shock inside the likelihood; regular season at 0.5 weight; shock sd 1.0; half-life 120 d; temperature 0.9; 2025 international results (91 series) as a centred, 0.7-shrunk prior mean for region effects with prior sd 0.7.
- Validation (67 international series, walk-forward): log loss 0.616 vs 0.637 without the prior, 0.622 for the naive region rule, 0.693 coin flip. Domestic playoffs + internationals from April (169 series): 0.611.
- T1 adjustment halved to +0.10. Other adjustments unchanged.
- Effects vs v3: GEN title 28.5% -> 33.6%; HLE 13% -> 17%, level with T1 (17%); IG 6th -> 8th (bad regular splits now count); TSW 17th -> 13th; C9 above FURIA (Play-In 24% each, KC 49%); LCK-LPL gap +0.65 (sd 0.60), shown on the Overview.
- Still open: the region gap is about one standard error from zero; the dossiers' qualitative material still feeds nothing numerically; Pick'Ems scoring rules unverified.

## Follow-up (15/10/2026 evening NZDT): is 3-0 really the most likely score?
Question raised: 12 of the 13 baseline series show 3-0 as the predicted score. Check (`model/sweep_check.py`, output `data/sweep_check.json`): every 2026 Bo5 predicted walk-forward with the v4 settings, 178 series.
- Actual mix: 44% 3-0, 31% 3-1, 25% 3-2. Model at shock sd 1.0: 72 sweeps expected vs 78 seen, 61 3-1s vs 56, 45 3-2s vs 44. It slightly under-predicts sweeps, not over.
- By favourite strength (single-game chance): 0.50-0.55, favourite's wins were 34% 3-0 / 39% 3-1 / 27% 3-2 (model 39/35/26); 0.55-0.60: 39/36/25 (model 43/34/23); 0.60-0.65: 64/14/23 (model 46/33/21); 0.65-0.72: 59/35/6; above 0.72: 67/17/17. So 3-0 is the most common result at every strength except true coin flips, where 3-1 edges it within noise.
- Prediction sd grid: exact-score log loss is best at 0.85-1.0 (1.675) and worst with no shock (1.715); modal-score hit rate 32-33% from 0.7 up.
- Caveat: 2025 international Bo5s were the opposite (31 series: 8 sweeps, 10 3-1s, 13 3-2s; MSI 2025 had nine 3-2s). 2026 internationals were sweep-heavy (13 of 20 Bo5s at MSI 2026). The model follows 2026.
Decision: keep sd 1.0 and the modal score as the graded prediction. The dashboard shows the full score split per series and the expected mix per bracket so "3-0" reads as the single most likely score (about 35-45%), not a forecast that each series will be a sweep.

## Dossier change (same evening)
Player rows and champion pools now come from the whole 2026 season on gol.gg (`model/scrape_golgg_players.py` -> `data/golgg_players_2026.json`, 95 players, 43-177 games each): games, KDA, GD@15, KP, pool size and the five most-played champions with games and win rate. Previously they came from one playoff sample (often 1-3 games per champion).

## Data expansion (15/10/2026 evening NZDT)
Five datasets added in parallel (all gol.gg or official Riot sources, accessed 15/10/2026): Summer-split player stats and pools; team pages (record, blue/red win rate, objective shares, pick/ban tables, role pick priority, per-game draft log); every change in patches 26.18-26.20; the 2026 World Championship Event-Specific Ruleset (Fearless in every Bo3 and Bo5, Right of First Selection, Pick'Ems points 5/5/5/5/5/10, 10 per Swiss advancer + 45 record bonus, 10/20/80 in knockouts, locks); and a results updater for the two gol.gg Worlds tournaments. None of this feeds the rating yet; it is descriptive in the dossiers and bracket detail. Candidates to test after the Play-In: a side-selection term (G2 74% blue vs 49% red; BLG 72% on red), a Fearless pool-depth term for Bo5s, and a staleness penalty for 369 (no games since March; TES already carries -0.20 for the ZUIAN visa situation).

## v5 candidates (16/10/2026 NZDT)
Walk-forward test of the candidates in `docs/superpowers/specs/2026-10-16-model-v5-design.md` (`model/backtest_v5.py` -> `data/backtest_v5.json`, run 16/10/2026 09:47 NZDT). Rule: adopt when the best grid point beats v4 with paired-bootstrap P(improvement) of 0.80 or more on its main set and, for the weight candidates, set B log loss rises by no more than 0.002. Picking the best grid point makes P(improvement) optimistic.

| Candidate | Set | n | v4 log loss | Candidate log loss | P(improve) | Best setting | Adopted |
|---|---|---|---|---|---|---|---|
| International weight | A (B check) | 67 (169) | 0.6162 (0.6119) | 0.6230 (0.6126) | 0.146 | w_intl 1.5 | no |
| Patch recency | A (B check) | 67 (169) | 0.6162 (0.6119) | 0.6164 (0.6191) | 0.491 | patch_n 2, patch_mult 1.5 | no |
| Fearless pool depth | P: Bo3/Bo5 between Worlds teams | 147 | 0.6576 | 0.6572 | 0.596 | pool_beta 0.02 | no |
| Side term | S: games between Worlds teams | 497 | 0.6720 | 0.6683 | 0.892 | k 100 | passes the rule (recorded only) |

Outcome: nothing passed that can change a prediction; v4 stays the model (`data/backtest_v5.json` `adopted.env` is empty, so `model/ratings.py` selects v4). Worlds games enter the fit from the Swiss staged run on (`model/scrape_golgg.py` now lists both Worlds tournaments). 369 staleness stays a manual adjustment.

What this means: we tried four tweaks and asked each one to beat the current model on past matches it had not seen yet, by a clear margin. Giving international games extra weight made the predictions worse at every setting tried. Leaning harder on the latest patches, and rewarding teams with deeper champion pools in Fearless series, made no real difference: the scores moved in the fourth decimal place, which is noise. The only tweak that clearly helped is knowing which side (blue or red) each team plays on, but that is not known for each game when we make the prediction, so it cannot be used for the predictions we publish. The predictions therefore stay exactly as they were.
