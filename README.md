# Worlds 2026 analysis and prediction

Start with `HANDOVER.md` (current state and next steps) and `CLAUDE.md` (rules for agents). `design/` holds the Claude Design artboards (`*.dc.html` + `canvas.json`) for the intended public-site look. `requirements.txt` lists the Python packages.

Built 15/10/2026 (NZDT). Dashboard: "Worlds 2026 Predictor" artifact (Dashboard type).

## Files
- `research/teams/<TEAM>.md` 19 dossiers (the brief said 17; there are 19 qualified teams). `research/meta.md`, `research/format.md`, `research/regions.md`.
- `data/teams.json`, `data/results_2026.json` (international series), `data/results_domestic_2026.json`.
- `model/ratings.py` is a switch: MODEL=v4 (default) -> `model/ratings_v4.py`, series-level Bradley-Terry with per-series form shock on every 2026 series (`data/series_2026.json`, scraped by `model/scrape_golgg.py` and built by `model/build_games.py`), 2025 region prior (`data/region_prior_2025.json`). MODEL=v3 -> `model/ratings_v3.py` (old game-level fit on playoff data). Validation: `model/backtest_v4.py`, review in `MODEL_REVIEW.md`.
- `data/adjustments.json` qualitative adjustments (cap +/-0.405 logit = +/-10 pp vs an even opponent).
- `model/simulate.py` Play-In exact + Swiss/KO Monte Carlo -> `data/sim_baseline.json`.
- `model/predict.py --stage <baseline|playin|swiss|knockouts>` -> `data/predictions_<stage>.json`. Baseline is frozen (read-only, SHA-256 in `data/predictions_baseline.sha256`). Current baseline = v4, created 15/10/2026 17:08:07 NZDT; v1-v3 kept as `predictions_baseline_v*_superseded.json`.
- `model/pickems.py` -> `data/pickems_<stage>.json`.
- `model/export_dashboard.py` -> `data/dash/*.json` (the dashboard's datasets).
- `model/grade.py` -> `data/grading.json` from `data/results_live.json`.
- `model/scrape_golgg_players.py` -> `data/golgg_players_2026.json` (full-season player stats and champion pools for the 95 players; feeds the dossiers' player table).
- `model/sweep_check.py` -> `data/sweep_check.json` (walk-forward check of the Bo5 exact-score mix; see MODEL_REVIEW.md).
- `model/scrape_golgg_players.py --split Summer --out data/golgg_players_summer_2026.json` -> Summer-split view of the same (gol.gg "Summer" = each league's final regular split + playoffs, plus EWC/KeSPA Cup/Worlds Play-In games).
- `model/scrape_golgg_teams.py` -> `data/golgg_teams_2026.json` (19 teams, season and Summer: record, side win rates, objectives, pick/ban tables, role pick priority, per-game draft log; raw pages kept in the scratchpad).
- `data/patch_state.json` + `research/patches_26_18_to_26_20.md`: every champion/item/system change in 26.18-26.20 from the official notes (built by a one-off script; regenerate by hand from the notes).
- `research/rules_2026.md` + `data/rules_2026.json`: draft mode per stage (Fearless in every Bo3/Bo5), Pick'Ems points per pick, lock times, Swiss pairing rules, Right of First Selection, roster flags (369 confirmed as TES top).
- `model/update_results.py` -> merges finished Worlds series from gol.gg into `data/results_live.json` (see "Pulling results" below).
- `site/` the website (Astro, static): pages in `site/src/pages/`, data loaders in `site/src/lib/data.ts`, client scripts in `site/public/js/`. `cd site && npm ci && npm run build` -> `site/dist/`, deployed by `.github/workflows/publish.yml` and `update.yml`, checked by `tests/check_site.py`. See HANDOVER.md "Website".
- `model/export_site_assets.py` -> `site/public/art/` (logos, extras, champion and item art) and `site/src/lib/art.json`. Run after `export_dashboard.py`, before the site build.
- `model/dcgi_check.py` -> `data/dash/dcgi.json`: walk-forward check of the v4 model on the Demacia Cup Global Invitational (03 to 17/10/2026), shown on the site's Demacia Cup hub.

## Refreshing data
Dashboard datasets changed on 15/10/2026 evening: `dossiers` (season + Summer player tables, team stats/draft from gol.gg, flags), `patch_changes` (26.18-26.20), new `patch_state` (chip flags), `overview` (draft modes, Pick'Ems points, locks). The dossiers tab has a season / Summer toggle; bracket detail panels show an 'On paper' comparison (descriptive only, not used by the model).

Re-run `python3 model/scrape_golgg.py && python3 model/build_games.py` to pull new series (Worlds games will appear under a new gol.gg tournament name: add it to TOURNAMENTS in scrape_golgg.py with league INTL / kind international).

## Staged runs still to do
1. Swiss: after the round 1 draw (18/10), before 24/10/2026 06:00 NZDT. Add Play-In results to `data/results_2026.json`-style domestic file, fix the Play-In winner (`simulate.py --playin-winner`), feed the actual R1 draw (`r1_fixed`), re-check rosters/patch, re-run predict/pickems/export, re-upload datasets.
2. Knockouts: after the QF draw (31/10), before 04/11/2026 11:00 NZDT.

## Updating results on the dashboard
Run `python3 model/update_results.py` (or append rows to `data/results_live.json` by hand), then `model/export_dashboard.py`, upload `data/dash/results.json` as a new asset and update `datasets/results` (`url`, `name`, `updated`). The Scorecard tab grades itself.

## Pulling results from gol.gg (`model/update_results.py`)

gol.gg has registered two tournaments for Worlds 2026 (both pages existed on 15/10/2026, with no series played yet):

| gol.gg name | URL | Phases | Stage labels |
|---|---|---|---|
| `Worlds 2026 Play-In` | https://gol.gg/tournament/tournament-matchlist/Worlds%202026%20Play-In/ | Play-In | `ROUND1` for the two opening series; later labels are expected to be `ROUND2`, `ROUND3`, `FINALS` (not yet visible) |
| `Worlds 2026 Main Event` | https://gol.gg/tournament/tournament-matchlist/Worlds%202026%20Main%20Event/ | Swiss + Knockouts | 2025 used `ROUND1`..`ROUND5`, `QUARTERFINALS`, `SEMIFINALS`, `FINALS` |

Both names are in `TOURNAMENTS` at the top of the script; `--tournament "Name=Play-In|Main"` adds or overrides one without editing the file. The S16 list at `https://gol.gg/tournament/ajax.trlist.php` (POST `season=S16`) only shows tournaments with games played, so Worlds will appear there once the first series is in.

```
python3 model/update_results.py --dry-run     # fetch, show what would change, write nothing
python3 model/update_results.py               # merge into data/results_live.json
python3 model/export_dashboard.py             # then upload data/dash/results.json as before
python3 model/grade.py                        # optional: data/grading.json
```

What it does:
- Parses the match lists (series rows only; gol.gg gives no per-game rows there, so `data/results_games_live.json` is not written; each row's series page is kept in `source.series_url`).
- Keeps only finished series: one side has the wins the inferred bo needs. Play-In and Knockouts are Bo5. Swiss rounds 1-2 are Bo1; round 3 is Bo3 when both teams are 2-0 or both 0-2 (records come from the earlier rows), Bo1 for 1-1 teams; rounds 4-5 are Bo3. An in-progress Bo3 at 1-0 is therefore skipped, and unplayed rows (` - `) are ignored. If records are inconsistent and a 1-0 is ambiguous the row is skipped with an `AMBIGUOUS` message; `--trust-golgg-winner` accepts gol.gg's winner marker in that case.
- Maps gol.gg names to the project codes (`CODES` in the script, incl. "Anyone s Legend" = AL, "MVK Esports" = MVK, "Team Liquid" = TLAW, "Team Secret Whales" = TSW, "CTBC Flying Oyster" = CFO, "Los Grandes" = LOS, "Movistar KOI" = MKOI). An unmapped name skips that row with a message.
- Ids: `PI-R1-A` (KC/C9) and `PI-R1-B` (FURIA/MVK) by team pair; `PI-WM`, `PI-EM`, `PI-LF`, `PI-GF` by bracket logic from the R1 results, processed in date order (a final that is a rematch of R1 lands in `PI-GF`, not on the R1 row). Swiss: `SW-R<n>-<A>-<B>`. Knockouts: `KO-F` for the final; a quarterfinal or semifinal updates an existing Knockouts row with the same team pair and round (e.g. a hand-made `KO-QF1` after the draw), otherwise `KO-QF-<A>-<B>` / `KO-SF-<A>-<B>`. The Scorecard matches results to predictions by id + pair, then phase + pair, so the appended ids grade fine.
- Merge rules: existing rows are updated in place, scores are oriented to the row's existing `team_a`/`team_b`, and hand-entered fields (`start_nz`, stage, notes) are never overwritten. A row that already has a different winner or score is left alone and reported as `CONFLICT` unless `--overwrite` is given. Teams that reach 3 wins or 3 losses in Swiss get a `{"kind":"swiss_record","team","record"}` row (what `grade.py` reads for Swiss records).
- Idempotent: rows are compared ignoring `source.accessed`; with nothing new the file is not rewritten.

Row schema (kind `series`):
```
{"id": "PI-R1-A", "phase": "Play-In|Swiss|Knockouts", "kind": "series", "stage": "Play-In R1",
 "golgg_stage": "ROUND1", "round": 3 (Swiss only), "date": "15/10/2026" (gol.gg's venue date),
 "start_nz": "16/10/2026 07:00" or null, "team_a": "KC", "team_b": "C9", "score_a": 3, "score_b": 1,
 "winner": "KC", "bo": 5, "patch": "26.20",
 "source": {"url": "<match list>", "series_url": "https://gol.gg/game/stats/<id>/page-summary/", "accessed": "dd/mm/yyyy HH:MM NZDT"}}
```
`start_nz` is only ever hand-entered (gol.gg has no start times); `grade.py` uses it to reject post-start predictions, so add it for rows the script appends if that check matters.

Offline test: `--page "Worlds 2026 Play-In=/path/saved.html" --results /path/copy.json` parses a saved page and writes elsewhere; only tournaments given a page are processed.

