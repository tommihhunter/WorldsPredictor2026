# Design: Poro Prophet (poroprophet.lol)

A locked design system for the site in `site/`. Every page redesign reads this file before emitting code. Extend or amend this file when the system needs to grow; do not improvise per page.

Written 16/10/2026 after a Hallmark audit (3 critical: card-everything, a tracked uppercase label on every tile, gold doing brand and data at once). Audience: friends following Worlds 2026, mostly on phones between matches. Use case: see the pick and whether it was right. Tone: playful-editorial. Layouts (sidebar, today hero, hub, team page, compare page) are locked from the brainstorm and stay; only the visual layer changes.

## Genre
editorial (playful notes: the poro mascot, the gold accent)

## Macrostructure family
- Home: Stat-Led. The lead stat is today's series (or the next one): the matchup in display type, our pick and its chance as the hero number, the result beside it once played.
- App pages (hubs, Teams, team page, compare, Scorecard, Meta, Demacia Cup): Workbench. Dense, left-aligned, hairline-ruled sections; one lifted panel per page at most.
- Nav: the fixed left sidebar (desktop) and five-item bottom bar (phone) are locked. Footer: Ft2 inline single line, credit only.

## Theme (OKLCH, tokens in `site/src/styles/tokens.css`)
- `--color-paper`    oklch(15% 0.012 250)   ground
- `--color-paper-2`  oklch(20% 0.015 250)   the one lifted panel per page
- `--color-paper-3`  oklch(26% 0.02 250)    raised interactive (chips, badges)
- `--color-rule`     oklch(31% 0.025 250)   hairlines
- `--color-ink`      oklch(95% 0.008 240)
- `--color-ink-2`    oklch(80% 0.015 245)   secondary text
- `--color-ink-3`    oklch(69% 0.02 245)    captions
- `--color-accent`   oklch(80% 0.14 85)     gold: brand, emphasis, the one highlighted number per page; never a data encoding
- `--color-accent-ink` oklch(15% 0.012 250)
- `--color-good`     oklch(75% 0.15 160)    hit, only as text
- `--color-bad`      oklch(72% 0.14 30)     miss, only as text
- `--color-data`     oklch(50% 0.03 250)    bars that are not the leader
- `--color-data-lead` oklch(88% 0.012 240)  the leading bar (ink, not gold)
- `--color-focus`    oklch(80% 0.14 85)

## Typography
- Display: Space Grotesk 700, tracking -0.02em, line-height 1.0. Used once per page at `--text-display` (the team name, today's matchup, "GEN v HLE"); section heads at `--text-xl`.
- Body: IBM Plex Sans 400/600, 16px, line-height 1.55, measure 65ch for prose.
- Outlier: IBM Plex Mono 500 for every number that is data (odds, scores, records, ratings, KDA, dates in tables). Two roles only: data numerals and the wordmark's "26". Never for prose.
- Scale (ratio 1.333): display clamp(2.5rem, 5.5vw, 4.25rem) · xl 1.75rem · lg 1.3125rem · md 1rem · sm 0.875rem · xs 0.8125rem.
- Labels: sentence case, `--text-xs`, `--color-ink-3`, no tracking, no uppercase. Section numbers and eyebrows: off.
- Tables: header cells sentence case, `--text-xs`, `--color-ink-3`; numeric cells mono, right-aligned, `font-variant-numeric: tabular-nums`.

## Spacing
4-point named scale in `tokens.css` (`--space-3xs` 0.25rem to `--space-3xl` 7rem). Section gap `--space-xl` on desktop, `--space-lg` on phones. Pages use tokens, never raw values.

## Surfaces and rules
- Default container: none. Sections are separated by a hairline (`border-top: 1px solid var(--color-rule)`) and a heading.
- `.panel` (paper-2, radius `--radius-panel` 12px, no border, no shadow): at most one per page (Home: Today; compare: summary strip; hub: Today strip; team page: the scouting report).
- Data chrome radius `--radius-data` 4px (badges, bars, chips). Pills (`--radius-pill` 999px) only for chips that switch a view: the Teams filters, the compare format switch, the hub Frozen / Latest toggle and the team page season / Summer toggle.
- No box shadows. Elevation is lightness only.
- Bars: 6px high, square ends, `--color-data`; the leader `--color-data-lead`. The compare page uses a split bar (two halves meeting under the label). Swiss and team cards: no bars, numbers only.

## Colour discipline
- Gold appears at under 5% of any viewport: wordmark mark, LIVE, link hover, and exactly one highlighted number per page (the pick's chance on Home and the hubs, the win chance on compare).
- Right and wrong are words in `--color-good` / `--color-bad` ("hit", "miss"), not pills, not backgrounds.
- Tiers (LOCK, LEAN, COIN FLIP) are plain text in `--color-ink-2`, weight 600 for LOCK only.

## Motion
- `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)`, `--dur-short: 180ms`. Only `opacity` and `transform`.
- Hover: link colour to gold, chips lighten one step. No reveals on scroll, no counters, no bounces.
- `prefers-reduced-motion: reduce`: transitions off.

## Microinteractions
- Silent success. Filters and the compare pickers change the view with no toast.
- `:focus-visible` ring 2px gold, offset 2px, never animated.
- Hover tooltips: none. Everything readable is on the page.

## Copy
- dd/mm/yyyy, NZDT with the venue time alongside, UNKNOWN never guessed, no em dashes. Captions are sentences ("Refitted 16/10 09:50 after every result so far."), not labels.

## Per-page allowances
- Home may show the poro at `--space-2xl` height beside the title; every other page uses the 28px mark only. The 404 page shows the sad poro large.
- App pages: typography and rules only, no enrichment.

## What pages MUST share
Wordmark, sidebar and bottom bar, tokens, the display and body and mono faces, the one-panel rule, the label rule, the gold rule, the table style.

## What pages MAY differ on
Which element is the page's display moment, and which single element is the panel.

## Exports

### tokens.css
See `site/src/styles/tokens.css` (the file is the source of truth; this section mirrors it).
