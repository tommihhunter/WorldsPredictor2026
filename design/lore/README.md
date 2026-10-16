# Handoff: Poro Prophet site redesign (Worlds 2026 Predictor)

## Overview
A full visual redesign of the public site in `site/` (Astro, static). The structure, routes and nav stay the same: Home, Play-In, Swiss, Knockouts, Demacia Cup, Teams, Scorecard and Meta. The look is new: "lore" styling from the Poro Prophet mascot palette (deep violet, antique gold, muted teal), Cinzel display type, Spectral body type, solid rounded panels instead of outlined cards, and much less on each page.

Target: 1920 x 1080 desktop first, content capped at 1600px, collapsing cleanly down to a 390px phone.

## About the design files
The `.dc.html` files in this folder are **design references made in HTML**. They are prototypes that show the intended look and behaviour, not production code. Open them in a browser to view them (they need `support.js` next to them). **Recreate them in the existing Astro site** (`site/src/pages/*.astro`, `site/src/styles/global.css`, `site/src/lib/*.ts`) using its patterns: class-based CSS in `global.css`, data from `site/src/lib/data.ts` (the `data/dash/*.json` datasets), and nav from `site/src/lib/nav.ts`. Do not ship the HTML or copy the inline styles verbatim. Turn the repeated values into CSS custom properties and classes.

All numbers in the mocks are snapshots from `data/dash/*.json` (exported 16/10/2026). In the real site, every number must come from the datasets, never be hard-coded.

Repo rules from `CLAUDE.md` still apply: dd/mm/yyyy dates, NZDT times, no em dashes in content, `UNKNOWN` for missing values, and don't touch model or data files.

## Fidelity
**High fidelity.** Colours, type, spacing, radii and copy are final. Match them closely, adapting to `global.css` conventions.

## Design tokens
Replace the `:root` block in `global.css` with these (the names are suggestions).

Colours:
- `--bg` #15112A (page)
- `--surface` #1E1939 (panels and cards)
- `--surface-warm` #2A2238 (callouts that used to be gold-outlined: risk, notes)
- `--line` #251F43 (row hairlines inside lists and tables)
- `--line-strong` #2C2550 (header bottom border, panel header dividers)
- `--track` #2A2448 (empty bar track)
- `--fg` #EEEAF6 (primary text)
- `--fg2` #E0DCEE (secondary text, paragraphs)
- `--muted` #C6C0DD (labels, captions, table heads)
- `--muted2` #D4CFE7 (sub-labels, e.g. "over Cloud9")
- `--dim` #B8B0D4 (ranks, minor numbers)
- `--gold` #D9B45A (primary accent: active nav, section labels, champion %, lock chips, links)
- `--teal` #86BDB5 (data accent: win %, probability bars, positive values; use sparingly)
- `--risk` #F29A8B (nerfs, "go 0-3", wrong calls)
- `--bar-alt` #7C6FB0 (non-leading bars in ranked lists)

Swiss record bar ramp (3-0 to 0-3): #6FE3D4, #4FB3A8, #2F7F78, #6B5A9E, #514382, #3B3063. This ramp is the one place the brighter teal remains. Optionally mute the first stop to #86BDB5.

Type (Google Fonts: `Cinzel` 500/600/700, `Spectral` 400/500/600):
- Body: Spectral 500, 17 to 18px, line-height 1.55. Numerals tabular (`font-variant-numeric: tabular-nums`).
- Labels and captions: Spectral 600, 15 to 17px, gold or `--muted`. **No uppercase tracking and no italics anywhere.**
- Display: Cinzel 700. Page h1 `clamp(40px, 3.8vw, 64px)`, line-height 1.05. Home h2 `clamp(44px, 4.6vw, 80px)`. Section h2 32px. Panel h3 26px.
- Team codes and names in lists: Cinzel 700, 17 to 22px.
- Big numbers: Cinzel 600. Champion % `clamp(72px, 6vw, 112px)` gold. Match % 52px teal. Stat tiles 56px.
- Use Cinzel only at 14px and up, and preferably 17px and up.

Shape:
- Panel: `background: var(--surface); border-radius: 14px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);` and **no border**.
- Warm callout: `background: var(--surface-warm); border-radius: 14px; box-shadow: inset 0 1px 0 rgba(217,180,90,0.18);`
- Selected card: `border: 1px solid var(--teal)` plus `box-shadow: 0 0 0 1px var(--teal)`. Unselected cards have a transparent 1px border so they don't shift.
- Chips: `border-radius: 999px; padding: 5px 12px; font: 600 15px Spectral`. Lock chip: gold text with a 1px gold border, no fill.
- Tier tag (LOCK / LEAN / COIN FLIP): 13px, weight 600, letter-spacing .1em. Colours: LOCK gold, LEAN teal, COIN FLIP `--muted2`.
- Bars: 6px tall (4 to 5px in compact spots), radius 3px, on `--track`. The leader is gold, the rest `--bar-alt` or teal depending on context.
- Split bar (match win %): 4px grid `{pa}fr {100-pa}fr`, gap 3px, teal and #3A3163.
- Section separation comes from spacing (56 to 72px gaps), **not** rules. Section headers have no underline.
- Rows inside lists: `border-top: 1px solid var(--line)`, padding 10 to 14px.

Spacing: page padding 56px top, 40px sides, 80px bottom. Main column gap 56px. Two-column sections use `repeat(auto-fit, minmax(min(100%, 520px), 1fr))` with a 56px row gap and 72px column gap.

## Global layout
**Header** (`Site Header.dc.html`, shared by every page except Home): 84px tall with a `--line-strong` bottom border, inner width capped at 1600px with 40px padding.
- Left: the Poro avatar (44px circle with a 2px bg ring and a 3px gold ring), then "Poro Prophet" in Cinzel 700 26px.
- Right: the nav, Cinzel 600 15px with .08em tracking, 8px 12px padding, 2px gap and `white-space: nowrap`, so it stays on one line at 1600px. The active link is gold-filled with dark text and a 3px radius.
- Far right: a lock chip with the next Pick'Ems lock, taken from `overview.next_lock`.

**Home masthead** (Home only):
- A 15px meta row: date, the current stage (left in `--muted2`, centre in teal), and "Baseline sealed {baseline_created}".
- A centred avatar (60px) and "Poro Prophet" in Cinzel 700 `clamp(40px, 3.4vw, 60px)`.
- A centred nav that wraps, with `white-space: nowrap` on each link.

**Footer**: 14px `--muted` text, sources on the left and the fan-project disclaimer on the right, with a top border in `--line`.

**Phone (< 640px)**: the header shrinks to the avatar plus the page title. The nav moves to a fixed 5-tab bottom bar (Home, Play-In, Swiss, Teams, More), which matches the existing `.bottombar`. Each tab is a 7px rotated-square marker above a 13px label, gold when active. "More" opens a bottom sheet with Knockouts, Scorecard, Meta and Demacia Cup, each with a one-line description. See `Phone Pages.dc.html`.

## Screens

### Home (`Home.dc.html`)
Row 1, two columns:
- **Left, "The prophecy":**
  - A gold label, then the h2 "The orb favours {champion name}".
  - A 28px Spectral line: "One in every three futures ends with them lifting the cup." Generate this from `champion_p`, or simplify it.
  - A stat panel holding a 116px logo disc, the champion % (gold, huge) with "to win Worlds" under it, and a column of three key/value pairs: likeliest final, likeliest spoiler, and the final's venue and date.
  - A closing paragraph.
- **Right, the "Your {stage} Pick'Ems" panel:**
  - Panel header with the h3 and the lock chip.
  - Two cells, "Go 3-0" (teal) and "Go 0-3" (risk), each listing 2 teams with logo, code and %.
  - An "Advance 3-1 or 3-2" grid with 6 teams.
  - A status line, e.g. "Preliminary until the draw" plus the last result.
  - An "All Swiss picks →" link row (hover background #241E44).
  - Data: `pickems.json` filtered to the live stage (`liveStage()` in `nav.ts`). In the Play-In, this panel shows the two R1 series instead, as in `Home Redesign.dc.html` 3a.

Row 2, two columns:
- **Left:** "Title odds", top 10 of `ratings.json` by `p_champion`, in two columns of rows (rank, code, bar, %). The leader is gold.
- **Right:**
  - The warm callout "Where the orb is clouded": `risk_assumption` in short form at 24px, then `risk_detection` at 17px.
  - "Quick picks": Play-In winner, Swiss 3-0 and Finals MVP from `overview`.

### Play-In (`Play-In.dc.html`)
- **Intro:** the h1 "Four teams, one Swiss spot" and an intro line, with a "Who wins the Play-In" panel on the right (4 rows: logo, code, bar, %).
- **Bracket:** 4 columns (Round 1, Round 2, Lower final, Final). Each series card is a button showing:
  - when, and the tier tag;
  - two team rows (logo, code, % or the final score);
  - a split bar;
  - a note ("Likeliest KC 3-0 (27%)", or "Called it. Score call 3-0 missed" once played).
  - Clicking a card selects it (teal border).
- **Detail panel** for the selected series:
  - title with both logos;
  - chips: the call, the score call, the tier, and the final result once played (gold fill);
  - a `dl` with key matchup, draft angle and what flips it, taken from the matchup data in `matchups.json`;
  - right side, "Score chances" bars for every exact score.
  - If there is no write-up yet, show the sentence "The matchup write-up is added once both teams are known."
- **"Our Play-In Pick'Ems" table:** slot, our pick (logo), chance right, the field, and status ("Hit, +5" in gold, otherwise "Pending").

### Swiss (`Swiss.dc.html`)
- **Intro.**
- **Pick'Ems panel:** a header with a "Preliminary" outline chip and the lock chip, then 3 cells: Go 3-0, Go 0-3, and Advance (a 3x2 grid).
- **"Every team's likely record":** a legend for the 6-colour ramp, then 16 rows, each with:
  - logo, code and region;
  - likeliest record and its %;
  - advance % (teal if 50% or more);
  - a 22px stacked bar of `p30 to p03` using fr units.
  - A **gold top border** on row 9 marks the predicted top-8 cut.
  - Data: `swiss.json` for the current set.

### Knockouts (`Knockouts.dc.html`)
- **Intro**, plus a warm callout with the points and lock.
- **Bracket:** 3 columns (QF, SF, Final) using `justify-content: space-around` with a 760px minimum height so the rounds line up. The Final card has a gold border. After the 31/10 draw, use the real draw.
- **"How far each team goes":** top 10 teams with QF, SF, Final and Champion bars (champion in gold). Data: `ratings.json` `p_advance`, `p_semis`, `p_final` and `p_champion`.

### Teams (`Teams.dc.html`)
- **Intro**, with region filter chips on the right (All, LCK, LPL, LEC, LCS, LCP, CBLOL). The active chip is gold-filled.
- **Card grid:** `repeat(auto-fill, minmax(280px, 1fr))`. Each card is a button showing logo, name, region and seed (plus "Play-In" if relevant), rank, title % (gold), advance % (teal) and trend (PEAKING and RISING teal, FADING risk, STABLE muted).
- **Dossier panel** for the selected team:
  - 108px logo disc, name, headline and title %;
  - a 5-cell path strip: Win Play-In or "Direct to Swiss", Advance, Semifinal, Final, Trend;
  - a manual adjustment callout if `adj_logit` is not 0;
  - 8 stat cells from `dossiers.json` `team_season`;
  - a `dl` with wins by, loses to, last 3 series, coach and sample;
  - a player table: role, player, KDA, GD@15, and the top 3 champions from `signature`.
- In the real site, each team should probably be its own route (`teams/[code]/`) rather than one-page selection. Keep the card grid on `teams/`.

### Scorecard (`Scorecard.dc.html`)
- **Stat strip** (one panel, 4 cells): winners called, exact scores, log loss, Pick'Ems points.
- **Series table:** start, series, our call, result, winner right or wrong, score right or missed.
- **Sidebar:**
  - "By confidence tier" (LOCK, LEAN, COIN FLIP: record and %). Note that tiers rate the winner only.
  - A warm callout linking to Demacia Cup.
- Data: `results.json` and `grading.ts`. Calls made after a series started show as `INVALID - post-start`.

### Meta (`Meta.dc.html`)
- **Three panels:** Patch 26.20 (down and up lists), Draft (Fearless rules), and a warm callout "Why so many 3-0 calls".
- **"Most contested champions":** rank, champion, roles, presence bar, picks, win rate, patch flag (nerfed risk, buffed teal, unchanged dim). Show the top 12 by default. Data: `meta_champs.json`.
- **"Pick'Ems points and locks":** 3 rows from `overview.pickems_points` and `locks_nz`.

### Demacia Cup (`Demacia Cup.dc.html`)
- **Intro**, plus a "Partial data" warm callout.
- **Stat strip:** winners called, log loss, region rule, coin flip.
- **"Every call" list:** date, stage, the two teams with logos, pick and %, actual result, Right or Wrong.
- **Sidebar:** a "What it taught us" callout and the region matchup hit counts.
- Data: `data/dash/dcgi.json`.

## Interactions and behaviour
- Hover on links and nav: colour changes to gold.
- Play-In bracket and Teams grid: click selects, and the detail panel below updates. There are no animations.
- Responsive:
  - Every two-column section uses auto-fit, so it stacks below about 1150px.
  - Fixed-width table grids (Swiss, Knockouts path, Meta, Scorecard) should get `overflow-x: auto` wrappers on narrow screens, or collapse to the phone layouts.
  - Nav wraps on narrow desktop.
- The "live" stage drives the Home Pick'Ems panel, the header lock chip and the masthead stage label (`liveStage()` and `overview.next_lock`).

## Assets
- `poroprophets/PoroMain.jpg`: the mascot avatar. It's in the repo at the same path. Copy it into `site/public/art/`.
- `dashboard/logos/*.png`: team logos, already copied to `site/public/art/` by `model/export_site_assets.py`.
- MVK has no logo in the repo. The mocks show a blank space, so use a fallback (code initials in a 28px disc).
- Fonts: Cinzel and Spectral from Google Fonts.

## Files
- `screenshots/01-home.png` … `08-demacia-cup.png`: each page at 1920 wide (left) with its 390px phone view (right). Knockouts also shows the "More" sheet, and Teams shows both the list and the dossier on phone. Use these as the visual target. The `.dc.html` files are the source of truth for exact values.
- `Home.dc.html`, `Play-In.dc.html`, `Swiss.dc.html`, `Knockouts.dc.html`, `Teams.dc.html`, `Scorecard.dc.html`, `Meta.dc.html`, `Demacia Cup.dc.html`: one desktop page each.
- `Site Header.dc.html`: the shared header (the `active` prop picks the highlighted link).
- `Phone Pages.dc.html`: every page at 390px, plus the More sheet and a team dossier.
- `support.js`: the runtime needed to open the `.dc.html` files in a browser. Reference only.

## Suggested order
1. Tokens and base classes in `global.css` (panel, callout, chip, tier tag, bar, row list, page intro).
2. Header, footer and phone bottom bar in the layout component.
3. Home, then Play-In and Swiss, which are live soonest. Then Teams, Knockouts, Scorecard, Meta and Demacia Cup.
4. Run `tests/check_site.py` and `npm run build`, then check at 1920, 1280 and 390 wide.
