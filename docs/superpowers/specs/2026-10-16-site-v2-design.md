# Site v2: design (16/10/2026)

## Goal
Replace the single-page dashboard with a feature-complete static site in Astro: a Home, one hub per event stage, a Teams explorer (browse grid, scouting-report team pages, a userbenchmark-style compare page per pairing), Scorecard and Meta. Same data, same bot, same look; proper pages with shareable addresses and a sidebar.

## Decisions already made (16/10/2026, brainstorm)
- Stack: Astro 7 (as MoesBlog), TypeScript strict, static output, hosted on GitHub Pages. Read-only; no accounts, no server. The LB standard stack was judged overkill.
- Data is read at build time from `data/dash/*.json`. Only two things are interactive in the browser: the Teams grid filter and sort, and the compare page's team pickers (which navigate between static pages).
- Navigation: option A. Fixed left sidebar on desktop with two groups, Event (Play-In, Swiss, Knockouts, Demacia Cup, with a LIVE marker on the stage being played) and Reference (Teams, Scorecard, Meta). On phones a five-item bottom bar: Home, the current stage, Teams, Scorecard, More (a sheet with the rest).
- Home (option B, "today hero"): today's or the next series with our pick and result, linking into the hub; then live top-10 title odds beside tiles for record, Pick'Ems points, next lock and model version. The favourite is just row 1.
- Event hub (option B, "today first"): header (dates, venue, format, draft rules, Pick'Ems lock) with the Frozen / Latest toggle; a Today strip; the bracket (Play-In, Knockouts) or standings table (Swiss: predicted record, live W-L, advance chance); the series list with tap-to-expand detail (draft angle, key matchup, exact-score odds, on-paper comparison, sources); Pick'Ems for the stage; expected vs actual sweeps; next lock. On phones the bracket scrolls sideways round by round.
- Demacia Cup hub: the same template with a banner "model test: picks generated after the event, fit only on games before 03/10/2026" and a results box (log loss vs coin flip vs region rule, hit rate by region matchup).
- Teams grid: 19 cards (logo, name, region and seed, rank, tier, rating, live title odds, form), filter by region and tier, sort by title odds, rating, win rate, GD@15, blue-side win rate, pool depth.
- Team page (option B): header with "Compare with..." and "Link"; desktop two columns, numbers left (odds tiles live next to frozen, path through Worlds, key stats with season/Summer toggle, players with pools, draft habits, sources) and the scouting report pinned on the right; phone one column, numbers first, jump chips under the header, report at the bottom.
- Compare page: `/teams/compare/<a>-vs-<b>/`, one static page per unordered pairing (171). Header cards with VS, roster lines, swap chips, Bo1 / Bo3 / Bo5 switch; summary strip (win chance in that format, live title odds, rank); metric groups in order Model, 2026 season, Lanes, Champion pool overlap (Fearless), Head to head (every 2026 series between them and 2025 internationals where they met; "never met" when none). Rows are value | label + verdict + difference | value with bars, leading side in gold. No verdict box.
- Scorecard and Meta: the current content carried over, plus a Crystal Ball section on the Scorecard.
- Mockups were layout only; the look comes from `design/*.dc.html` (ground #0B0F14, surface #131A22, raised #1C2633, line #243040, text #EAF0F6, secondary #B6C2D1, muted #93A1B3, gold #E8B84A, risk #F08A7A; Space Grotesk headings, IBM Plex Sans body).
- Retire `dashboard/index.html`, `model/build_site.py` and `model/build_local.py` once v2 is live and checked.

## Out of scope
Match pages, a model explainer page, browse by champion, accounts or comments, custom domain (separate, pending the name), Phase 1 of the old page (done).

## Data contract
Astro reads only `data/dash/*.json`. New or changed exports from `model/export_dashboard.py`:
- `dossiers.json` gains `report` (object with `who`, `wins_by`, `loses_to`, `draft` prose from the existing dossier fields) and `pool_depth`.
- `h2h.json` (new): one row per 2026 series between two Worlds teams and per 2025 international series between them: `a, b, date, tournament, stage, sa, sb, bo, patch, year`.
- `matchups.json` (new): `a, b, p_game, p_bo3, p_bo5` for every pairing, from `data/matchups.json` and the series mixture.
- `dcgi.json` (new, from `model/dcgi_check.py`): the Demacia Cup series with walk-forward picks and results, plus a summary row (n, log loss, coin flip, region rule, hit rate by region pair).
- Everything else as today: `live`, `ratings`, `series`, `swiss`, `results`, `pickems`, `crystal`, `overview`, `regions`, `patch_changes`, `patch_state`, `meta_champs`, `meta_fit`.
Art: champion, item, lane and objective icons come from the existing Data Dragon cache, copied into `site/public/art/` by a small Python step, never fetched by the browser from Riot.

## Build and deploy
- `site/` holds the Astro project (`package.json`, `astro.config.mjs` with `site` set to the Pages URL and `base` handled for the repo path, `src/`, `public/`). Node 24, npm, Astro 7.3.x, TypeScript strict, Biome for lint.
- `model/export_site_assets.py` (new) copies logos and the needed art into `site/public/`.
- Both workflows gain: setup-node, `npm ci` in `site/`, `npm run build`; the Pages artifact is `site/dist`. The Update workflow keeps committing `data/` only.
- `tests/check_site.py` serves `site/dist` and opens Home, each hub, Teams, one team page, one compare page, Scorecard and Meta at desktop and 390 px; fails on page errors, missing pages or sideways scroll.

## Error handling
- A missing optional export (for example `dcgi.json` before the check has run) renders a "not available yet" section, never a build failure.
- A team without a logo gets the colour badge.
- A pairing with no history shows "never met in 2025 or 2026".
- Bot data that fails the model tests is not committed, as today.

## Phases
1. Pipeline: exports (`report`, `pool_depth`, `h2h`, `matchups`, `dcgi`), assets step, Demacia Cup check.
2. Astro skeleton: layout, sidebar, bottom bar, theme, data loaders, Home, Scorecard, Meta.
3. Event hubs including Demacia Cup.
4. Teams: grid, team pages, compare pages.
5. Workflows, check, cutover, retire the old page.

## Risks
- 171 compare pages plus 19 team pages: build time stays seconds, but every data commit rebuilds everything; acceptable.
- The Swiss lock (24/10/2026 06:00 NZDT) is a data deadline, not a site deadline; the Swiss run happens on time with whichever site is live.
- The old page is retired only after `check_site.py` passes on v2 and a manual look at every page type.
