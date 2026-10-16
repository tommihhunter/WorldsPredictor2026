# Website: design (16/10/2026)

## Goal
Turn the draft dashboard into a website a group of friends can open from a link during Worlds 2026, that updates itself as results come in and shows live odds next to the frozen, graded picks.

## Decisions already made (16/10/2026)
- Audience: friends / small group. No SEO, no explainer section.
- Approach A: evolve `dashboard/index.html` (plain HTML/CSS/JS, no framework); it stays the single source for the website and the local single-file build.
- Hosting: GitHub Pages from the repo `tommihhunter/poroprophet`, made public (free Pages, unlimited Action minutes). The visibility change gets its own explicit go when Phase 0 needs it.
- Automation: a scheduled GitHub Action pulls results, refits the live odds, regrades, commits `data/` files to `main` and publishes. Standing exception: the bot may commit `data/` only. Staged Swiss and knockout runs stay manual.

## Out of scope
Model changes (done in v5). Custom domain. Accounts, comments, anything server-side.

## Pages
| Page | Content | Source |
|---|---|---|
| Home (new) | Live title odds (`live.json`, labelled Live, with "as of" time), the next matches with our pick and tier, the model's record so far | design/Main.dc.html, design/Phone.dc.html |
| Bracket | Play-In, Swiss, knockouts: each pick beside the actual result once played | design/Bracket.dc.html; current Predictions tab |
| Teams | 19 dossiers; shareable `#team=GEN` links | design/Team.dc.html; current Dossiers tab |
| Pick'Ems | Entered picks and points so far | current tab, restyled |
| Scorecard | Hits, misses, calibration of the frozen picks | current tab, restyled |
| Meta | Patch 26.18 to 26.20 changes, key champions | current tab, restyled |

Look (from `design/`): dark ground #0B0F14, surface #131A22, line #243040, text #EAF0F6, muted #93A1B3, accent gold #E8B84A; Space Grotesk (headings) and IBM Plex Sans (body) from Google Fonts. Phone: tabs become a bottom bar. Dark only (the artboards are dark); dates dd/mm/yyyy and times NZDT with venue time, no em dashes in copy.

## Build
- `model/build_site.py` (new) writes `dist/site/`: `index.html` (the page plus a fetch-based `dash` shim), `data/<id>.json` for every file in `data/dash/`, `assets.json` (champion, item, lane, objective art as data URIs, built once with the existing Data Dragon cache), and `logos/<CODE>.png`.
- The fetch shim implements the same `dash` interface the page already uses (`data`, `onData`, `calc`, `setLink`, `colors`): it loads all datasets in parallel, then fires the `onData` callbacks. A dataset that fails to load reports `status: 'missing'` (the page already handles that) instead of breaking the page.
- `model/build_local.py` keeps producing the single offline file. The asset collection and page patches (logo badges, footer) move into a shared helper used by both builds, so the two cannot drift.
- `setLink` writes `#<tab>` or `#team=<CODE>`; on load the page opens the tab or team named in the hash.

## Automation (`.github/workflows/`)
- `update.yml`: every 30 minutes from 16/10 to 16/11/2026 NZDT, and on demand. Steps: `update_results.py`; if `data/results_live.json` changed, `scrape_golgg.py` + `build_games.py` (Worlds games enter the fit), then `live.py`, `export_dashboard.py`, `grade.py`; run `tests/test_v5.py`; commit `data/` only (message `data: results update dd/mm/yyyy HH:MM NZDT`, retried with pull --rebase on a race); build the site and deploy it. Pushes made by the Action's own token do not trigger other workflows, so this workflow deploys itself. One run at a time (concurrency group). Outside the date window the job exits immediately.
- `publish.yml`: on every push to `main` (my pushes) and on demand: tests, build, deploy.
- Deploy uses the official Pages actions (upload artifact, deploy). Pages source set to "GitHub Actions" once.

## Error handling
- gol.gg down or unparseable: `update_results.py` already logs and writes nothing; the run still rebuilds from the last good data, so the site stays up.
- Tests fail: no commit, no deploy; the Action run shows red.
- Rows that do not fit the bracket or are ambiguous are skipped and logged (existing behaviour).
- Results added by the bot have no `start_nz` (gol.gg has none); grading treats them as valid because every frozen pick was made before the stage began. Known limit, written in HANDOVER.md.
- The page shows each dataset's "as of" time so stale data is visible.

## Testing
- `tests/check_site.py` (new): builds the site to a temp folder, serves it locally, opens it headless (Playwright, Chromium), visits all six pages and one `#team=` link, and fails on any page error or a missing dataset. Runs in both workflows before deploy, and locally.
- Existing `tests/test_v5.py` runs in both workflows.

## Phases
- Phase 0 (first): repo public (own go), Pages source set, `build_site.py` with the current look, both workflows, `check_site.py`. Done when the current dashboard is live at https://tommihhunter.github.io/poroprophet/ and a Play-In result appears without anyone touching it.
- Phase 1: restyle to the artboards, new Home page, bottom tab bar on phones, `#team=` links. Done before the Swiss stage starts (24/10/2026 06:00 NZDT).

## Risks
- gol.gg blocks or rate-limits the Action's IP: results then come in by hand (README schema), and the site still publishes.
- A bot commit racing my push: handled by rebase-and-retry; my own pushes pull first.
- Public repo exposes the research and code: checked 16/10, no employer name, no secrets.
