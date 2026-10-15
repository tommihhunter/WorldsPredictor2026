# Worlds 2026 Predictor: instructions for the agent working in this repo

Read HANDOVER.md first (current state, what is next, how to verify), then README.md (file map), then MODEL_REVIEW.md (why the model is the way it is). Do not start by rebuilding anything.

## Ground rules (from the owner, do not relax them)
- Dates are dd/mm/yyyy. Times are NZDT (UTC+13) with the venue time alongside where a match is referenced.
- No em dashes anywhere in content the owner might send or publish (dashboard text, README, notes). Use commas, colons or "to".
- Treat prior knowledge as unverified. Every fact in research/ and the dashboard carries a URL and an access date; keep that standard for anything you add. Unknowns are written `UNKNOWN`, never guessed.
- `data/predictions_baseline.json` is FROZEN (read-only, SHA-256 in `data/predictions_baseline.sha256`). Never edit it. A changed prediction is a new staged file (`data/predictions_<stage>.json`) or a new superseded copy with a timestamp. `model/predict.py --stage baseline` refuses to overwrite.
- No look-ahead. A prediction written after a series has started is `INVALID - post-start`; `model/predict.py` asserts the clock and `model/grade.py` enforces it from `start_nz`.
- Confidence tiers: LOCK 75% and up, LEAN 60 to 74%, COIN FLIP below 60%. Tiers rate the winner only, never the score.
- Qualitative adjustments (`data/adjustments.json`) are capped at +/-0.405 logit (about 10 percentage points against an even opponent) and need a written reason and a source.
- Keep the Play-In, Swiss and knockout stage gates: do the stage's data refresh, re-run, verify, then publish. Say what you assumed.
- Do not change model parameters without a walk-forward backtest result that justifies it (model/backtest_v4.py, model/sweep_check.py). The owner specifically asked that "3-0 as modal score" stay as is unless the Play-In calibration says otherwise (see MODEL_REVIEW.md, sweep check section).
- The owner's employer and company name are never mentioned in this project.

## How to work
- Step-gate: discovery (read the files named in HANDOVER.md, run the dry-run commands) -> plan (list exact files you will touch) -> code. Ask before anything irreversible (deleting data, re-freezing, publishing to the live dashboard).
- Use explicit file paths in every plan and summary.
- When something does not fit, classify it: fix now / acceptable with a visible signal in the UI or data / known limit written to HANDOVER.md.
- End every piece of work with the verification checklist in HANDOVER.md and name the single biggest risk in what you changed.
- Python 3.11+, numpy, scipy, Pillow, playwright (chromium) for render checks. `pip install -r requirements.txt`.
- Network: gol.gg (scrapes), ddragon.leagueoflegends.com (champion art), leagueoflegends.com (patch notes), lolesports.com. Rate-limit scrapes (0.4 to 0.5 s between pages) and keep the User-Agent the scripts set.

## Where things are
- `model/` scripts (entry points in README.md); `data/` inputs and outputs; `data/dash/` the dashboard datasets; `dashboard/index.html` the page; `dashboard/logos`, `dashboard/extras`, `dashboard/ddragon_cache` the art; `research/` cited notes and the 19 team dossiers; `design/` the Claude Design artboards for the public site look; `HANDOVER.md` the live state.
