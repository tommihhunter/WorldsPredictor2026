# Plan: "lore" redesign of the site (owner's Claude Design handoff)

Spec: `design/lore/README.md` (the owner's handoff, high fidelity, final). Visual source of truth: `design/lore/*.dc.html` (inline styles hold the exact values; `{{...}}`, `<sc-for>`, `<sc-if>` are template syntax; the script block at the bottom of each file holds the mock data, which is a snapshot of `data/dash`). Visual target: `design/lore/screenshots/*.png` (desktop 1920 left, phone 390 right).

Branch `lore-redesign`, local only. Nothing is pushed without the owner's three gates.

## Decisions (head, 16/10/2026)
1. The owner's design replaces the Hallmark system. `design.md` is rewritten to describe the lore system and supersedes the old one, including the old "sidebar locked" rule: desktop uses the top header from `Site Header.dc.html`; Home uses the masthead instead of the header.
2. Routes stay: `/`, `play-in/`, `swiss/`, `knockouts/`, `demacia-cup/`, `teams/`, `teams/[slug]/`, `teams/compare/`, `teams/compare/[pair]/`, `scorecard/`, `meta/`, 404. Team dossiers stay their own routes (README Teams section); the card grid links to them. Compare pages are not mocked: restyle them in the same system (panels, chips, split bars, Cinzel names).
3. Hubs drop the Frozen / Latest toggle. Brackets, series cards and detail panels show `view(stage, 'latest')` from `site/src/lib/stage.ts` (latest staged set, falls back to the frozen baseline), and the page footer names which set and when it was predicted. The Scorecard keeps grading the frozen baseline.
4. Home's Pick'Ems panel shows the stage of the next lock (`overview.next_lock`: 24/10 means Swiss, 04/11 means Knockouts). Add `lockStage()` to `site/src/lib/nav.ts` for this. The Play-In variant (R1 series) is skipped: the Play-In lock has passed.
5. Teams grid keeps the region chips (`.chip[data-region]`) and drops the sort chips (the design ranks by rating only). `tests/check_site.py` is updated to match.
6. No hard-coded numbers. Copy lines in the mocks that embed numbers are generated from data (for example "One in every three futures" from `champion_p`: use a simple fraction phrase, or "About N in 100 futures"). Missing values print `UNKNOWN`.
7. Likeliest final: the frozen baseline `KO-F` series row. Likeliest spoiler: the underdog of the baseline knockout series with the highest `p_upset`, with its round name.
8. Fonts: Cinzel 500/600/700 and Spectral 400/500/600 from Google Fonts replace Space Grotesk and IBM Plex.
9. Phone (< 640px): header shows avatar plus page title; bottom bar of five tabs (Home, Play-In, Swiss, Teams, More) with a 7px rotated-square marker; More opens a sheet with Knockouts, Scorecard, Meta, Demacia Cup, each with a one-line description (see `Phone Pages.dc.html`). `site/src/lib/icons.ts` goes once nothing imports it.
10. MVK has a logo now (`dashboard/logos/MVK.png`); keep a code-initials 28px disc fallback for any team without art.

## Shared class contract (foundation defines these in `site/src/styles/global.css`; pages use them and add page-only CSS in their own `<style>` block)
Tokens on `:root` exactly as named in the README (`--bg --surface --surface-warm --line --line-strong --track --fg --fg2 --muted --muted2 --dim --gold --teal --risk --bar-alt`, the six `--rec-30 ... --rec-03` ramp stops, `--split-off` #3A3163, `--hover` #241E44), fonts `--font-display` (Cinzel) and `--font-body` (Spectral), plus spacing and radius tokens.

- Layout: `.page` (main column, 1600px cap, 56/40/80 padding, 56px gap), `.cols` (auto-fit two columns, minmax(min(100%,520px),1fr), 56px row gap, 72px column gap), `.intro` (eyebrow + h1 + lede), `.eyebrow` (gold Spectral 600 label), `.lede`.
- Surfaces: `.panel` (surface, 14px radius, inset highlight, no border), `.panel-head` (h3 + chips, `--line-strong` divider), `.callout` (surface-warm, gold inset), `.card` (button-like series or team card: surface, 14px radius, transparent 1px border) and `.card.is-selected` (teal border + ring), `.card.is-final` (gold border).
- Text: `h1` page title, `h2` section (32px, no underline), `h3` panel (26px), `.code` (team code, Cinzel 700), `.num` (tabular numerals), `.muted .muted2 .dim .gold .teal .risk`.
- Data: `.chip` (pill, 600 15px), `.chip.lock` (gold outline), `.chip.on` (gold fill, dark text), `.tier` with `.tier.lock .tier.lean .tier.coin`, `.bar` (6px track, radius 3) with `<i style="width:x%">` and modifiers `.bar.gold .bar.teal .bar.alt .bar.thin`, `.split` (4px grid split bar, `--pa` custom property), `.rows` (list with `border-top: 1px solid var(--line)` rows), `.kv` (definition list grid), `.stat-strip` (one panel, N cells, big Cinzel 600 numbers), `.logo` (team logo box, sizes via `--s`), `.disc` (round logo disc).
- Chrome: `Header.astro` (desktop header + phone title bar), `Masthead.astro` (Home), `Footer.astro` (two slots: sources left, disclaimer right), `BottomBar.astro` (phone tabs + More sheet).

## Agents and file ownership
| Agent | Owns (create or edit) |
| --- | --- |
| F foundation (runs first) | `site/src/styles/tokens.css`, `site/src/styles/global.css`, `site/src/layouts/Base.astro`, `site/src/components/{Header,Masthead,Footer,BottomBar,Logo,Tier}.astro`, `site/src/lib/nav.ts`, `design.md`, `site/public/art/poro/` (avatar from `poroprophets/PoroMain.jpg` if needed), `site/src/pages/404.astro` |
| P1 Home + Swiss | `site/src/pages/index.astro`, `site/src/pages/swiss.astro`, new `site/src/components/PickemsPanel.astro`, new `site/src/components/RecordTable.astro` |
| P2 Play-In + Knockouts | `site/src/pages/play-in.astro`, `site/src/pages/knockouts.astro`, new `site/src/components/SeriesCard.astro`, `SeriesDetail.astro`, `site/public/js/select.js` |
| P3 Teams | `site/src/pages/teams/**`, `TeamCard.astro`, `PlayersTable.astro`, `CompareRow.astro`, `CompareView.astro`, `PathTable.astro`, `DraftBlock.astro`, `ChampIcon.astro`, `site/public/js/teams-grid.js`, `site/public/js/compare-pick.js`, the Teams checks in `tests/check_site.py` |
| P4 Scorecard + Meta + Demacia Cup | `site/src/pages/{scorecard,meta,demacia-cup}.astro` |
| Head (after) | review the whole diff, delete components nothing imports, build, `tests/check_site.py`, localhost preview, commits |

Nobody edits `model/`, `data/`, or another agent's files. Page agents never edit `global.css`, `tokens.css` or `Base.astro`; if a shared class is missing they add page-scoped CSS and report it. Builders do not commit.

## Verify (every agent, then head)
```
cd site && W26_BASE=/ npm run build
```
Then the head runs `python -X utf8 tests/check_site.py` (with `W26_BASE=/` and `MSYS2_ENV_CONV_EXCL=W26_BASE` in Git Bash), `python -X utf8 -m pytest -q tests`, checks 1920, 1280 and 390 wide against the screenshots, greps `site/dist` for em dashes, and serves `site/dist` on localhost:5454.
