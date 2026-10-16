# Design: Poro Prophet (poroprophet.lol), lore system

The locked design system for the site in `site/`. Every page reads this file before emitting code. Extend or amend this file when the system needs to grow; do not improvise per page.

Written 16/10/2026. At the owner's request this lore system **replaces the 16/10/2026 Hallmark system** (sidebar, Space Grotesk and IBM Plex, hairline sections, one panel per page). Where the two disagree, this file wins, including the old "sidebar locked" rule.

Reference: `design/lore/` holds the owner's Claude Design handoff. `design/lore/README.md` is the spec, the `.dc.html` files hold the exact values (inline styles), and `design/lore/screenshots/*.png` are the visual target (desktop 1920 left, phone 390 right).

## Genre
Lore. The Poro Prophet mascot palette: deep violet ground, antique gold accent, muted teal for data. Cinzel display type, Spectral body type, solid rounded panels instead of outlined cards, and much less on each page. Audience: friends following Worlds 2026, often on phones between matches. Each page leads with what you need for Pick'Ems.

## Tokens (`site/src/styles/tokens.css`)
Colour:
- `--bg` #15112A page
- `--surface` #1E1939 panels and cards
- `--surface-warm` #2A2238 warm callouts (risk, notes, points)
- `--line` #251F43 row hairlines inside lists and tables, footer top border
- `--line-strong` #2C2550 panel header dividers, phone header and bottom bar borders
- `--line-head` #3A3163 desktop header and masthead bottom border
- `--track` #2A2448 empty bar track
- `--fg` #EEEAF6 primary text; `--fg2` #E0DCEE paragraphs
- `--muted` #C6C0DD labels, captions, table heads; `--muted2` #D4CFE7 sub-labels; `--dim` #B8B0D4 ranks, minor numbers
- `--gold` #D9B45A primary accent: active nav, section labels, champion %, lock chips, links, the leading bar
- `--teal` #86BDB5 data accent: win %, probability bars, positive values; use sparingly
- `--risk` #F29A8B nerfs, "go 0-3", wrong calls
- `--bar-alt` #7C6FB0 non-leading bars in ranked lists
- `--split-off` #3A3163 losing side of a split bar, neutral chip outline
- `--hover` #241E44 row and link-row hover
- Swiss record ramp, 3-0 to 0-3: `--rec-30` #6FE3D4, `--rec-31` #4FB3A8, `--rec-32` #2F7F78, `--rec-23` #6B5A9E, `--rec-13` #514382, `--rec-03` #3B3063. The only place the brighter teal appears.

Spacing: `--space-3xs` 4px to `--space-3xl` 80px; `--page-max` 1600px; `--gutter` 40px (18px on phones).
Shape: `--radius` 14px, `--radius-sm` 10px, `--radius-nav` 3px, `--radius-bar` 3px, `--radius-pill` 999px, `--inset` and `--inset-warm` highlights.

## Type
- Google Fonts: Cinzel 500/600/700 (`--font-display`) and Spectral 400/500/600 (`--font-body`).
- Body: Spectral 500, 17px (16px on phones), line-height 1.55, tabular numerals everywhere.
- Labels and captions: Spectral 600, 15 to 17px, gold or `--muted`. Sentence case.
- Display: Cinzel 700. Page h1 `clamp(40px, 3.8vw, 64px)` line-height 1.05 (30px on phones). Home h2 `clamp(44px, 4.6vw, 80px)`. Section h2 32px (22px on phones). Panel h3 26px (18px on phones).
- Team codes and names in lists: Cinzel 700, 17 to 22px (`.code`).
- Big numbers: Cinzel 600 (`.big`). Champion % `clamp(72px, 6vw, 112px)` gold, match % 52px teal, stat tiles 56px.
- Cinzel only at 14px and up, preferably 17px and up. Cinzel sets lowercase as small capitals, so write words in normal case, never in capitals.
- **No italics anywhere. No uppercase text-transform with tracking**, except the tier tag (13px, 600, .1em) and the nav (Cinzel 600 with .08em tracking in the header, .1em in the masthead).

## Shape
- Panel: `--surface`, 14px radius, inset highlight, no border.
- Warm callout: `--surface-warm`, 14px radius, gold inset highlight.
- Card (series or team button): `--surface`, 14px radius, transparent 1px border. Selected: teal border plus a 1px teal ring. The Final card: gold border.
- Chips: pill, 5px 12px, Spectral 600 15px. Lock chip: gold text, 1px gold border, no fill. Active or result chip: gold fill, dark text.
- Tier tag: LOCK gold, LEAN teal, COIN FLIP `--muted2`. Tiers rate the winner only.
- Bars: 6px (4px compact), radius 3px, on `--track`. The leader is gold, the rest `--bar-alt` or teal by context.
- Split bar: 4px, two parts in proportion to the win %, 3px gap, teal and `--split-off`.
- Section separation comes from spacing (56 to 72px), not rules. Section headers have no underline. Rows inside lists: `border-top: 1px solid var(--line)`, 10 to 14px padding.

## Layout
- `.page`: main column capped at 1600px, padding 56px top, 40px sides, 80px bottom, 56px gap.
- `.cols`: `repeat(auto-fit, minmax(min(100%, 520px), 1fr))`, 56px row gap, 72px column gap; stacks below about 1150px.
- Fixed-width tables and grids (Swiss, Knockouts path, Meta, Scorecard) sit in `.scroll` (overflow-x auto) or collapse to a phone layout. No horizontal page scroll at 390px. Grid tracks use `minmax(0, 1fr)`.

## Chrome
- **Header** (`Header.astro`, every page but Home): 84px, `--line-head` bottom border, inner width 1600px with 40px padding. Left: 44px avatar (2px bg ring, 3px gold ring) and "Poro Prophet" in Cinzel 700 26px. Right: the nav from `NAV` in `site/src/lib/nav.ts`, Cinzel 600 15px .08em, 8px 12px padding, 2px gap, nowrap; the active link is gold-filled with dark text and a 3px radius. Far right: the lock chip from `overview.next_lock` ("Swiss lock 24/10, 06:00 NZDT"). The nav wraps on narrow desktop.
- **Masthead** (`Masthead.astro`, Home only): a 15px meta row (build date with weekday, the stage line in teal from `stageLine()`, "Baseline sealed {baseline_created}"), a centred 60px avatar with "Poro Prophet" at `clamp(40px, 3.4vw, 60px)`, and a centred wrapping nav (16px, .1em, 8px 16px).
- **Footer** (`Footer.astro`): 14px `--muted`, sources and the export stamp on the left, the fan-project disclaimer on the right, `--line` top border. Pages can pass their own left text (for example which prediction set a hub shows).
- **Phone (< 640px)**: the header shrinks to a 36px avatar and the page title (Cinzel 21px), with a compact lock chip ("Locks 24/10") on the right; Home shows the avatar and wordmark only. The nav moves to the fixed bottom bar (`BottomBar.astro`): Home, Play-In, Swiss, Teams, More. Each tab is a 7px rotated-square marker over a 13px label, gold when active. More opens a bottom sheet with Knockouts, Scorecard, Meta and Demacia Cup, each with a one-line description; More reads active on those pages.

## Data rules
- Every number comes from `data/dash/*.json` through `site/src/lib/data.ts`; copy that embeds a number is generated. Missing values print `UNKNOWN`.
- Dates dd/mm/yyyy, times NZDT. No em dashes in any content. Links go through `url()`.
- Hubs show the latest staged set (`view(stage, 'latest')`), and the footer names which set and when it was predicted. The Scorecard grades the frozen baseline.

## Pages
- **Home**: masthead; "The prophecy" (champion, a sentence from `champion_p`, stat panel with a 116px logo disc, likeliest final and spoiler, the final's venue and date) beside the Pick'Ems panel for the stage of the next lock (`lockStage()`). Then Title odds (top 10, leader gold) beside the "Where the orb is clouded" callout and Quick picks.
- **Play-In**: intro with a "Who wins the Play-In" panel; 4-column bracket of selectable series cards; detail panel (chips, key matchup, draft angle, what flips it, score chances); our Pick'Ems table.
- **Swiss**: intro; Pick'Ems panel (Go 3-0, Go 0-3, Advance); every team's likely record with the six-stop ramp and a gold line at the predicted top-8 cut.
- **Knockouts**: intro with a points callout; 3-column bracket (QF, SF, Final with a gold border, 760px minimum height); how far each team goes (champion bars gold).
- **Teams**: intro with region chips; card grid `repeat(auto-fill, minmax(280px, 1fr))` linking to each team's own route; the dossier page carries the path strip, adjustment callout, stat cells, report and player table. Compare pages use the same panels, chips, split bars and Cinzel names.
- **Scorecard**: stat strip (4 cells); series table; tier breakdown; a callout to the Demacia Cup.
- **Meta**: patch, draft and "Why so many 3-0 calls" panels; most contested champions (top 12); Pick'Ems points and locks.
- **Demacia Cup**: intro with a "Partial data" callout; stat strip; every call; what it taught us.
- **404**: the sad poro, the intro block and a lock-style chip back to Home.

## Interaction and motion
- Hover on links and nav: colour to gold. Rows and link rows: `--hover` background.
- Play-In bracket selection: click selects, the detail panel updates. No animations.
- `:focus-visible` is a 2px gold ring. `prefers-reduced-motion: reduce` turns transitions and animations off.

## Polish pass rules (17/10/2026, supersede any size or spacing above)
- Fonts: Riot's Beaufort for LoL (display, set in capitals, `--track-caps`) and Spiegel (body). Cinzel and Spectral are retired.
- Type: only the eight `--fs-*` tokens in `site/src/styles/tokens.css` (13, 15, 16, 20, 24, 32, page-title clamp, hero clamp). Phone values swap in automatically. No raw `font-size: NNpx` in pages or components.
- Spacing: only the `--space-*` tokens (4, 8, 12, 16, 24, 32, 48, 64, 80). Sections are 48px apart, panels pad 24/32, rows pad 12. Hairlines and icon sizes are the only raw pixel values.
- One content edge: header, page and footer all use `--wrap` with `--gutter` padding, so the logo, page titles and footer text line up.
- Colour: gold is brand, active nav, lock chips, eyebrows and the ONE number that matters in a view. Teal and risk are status (right / wrong, up / down, go 3-0 / go 0-3). Every other number is `--fg`; bars carry the comparison.
- Hierarchy per view: one display moment (h1 or hero number), then section titles, then content. Nothing repeats the brand mark inside the page.
- Every interactive element has hover, focus-visible and active states; transitions 120ms on colour only.
- Tier tags: LOCK gold, LEAN --fg2, COIN FLIP --muted (teal stays status-only). The 60ch measure sits on `.lede`, not on `.intro`.
