# Website Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the live site the artboard look (dark ground, gold accent, Space Grotesk headings, pill tabs that scroll sideways on phones), a Home page that leads with live title odds and the next matches, results beside picks on the Bracket, and shareable team links (`#team=GEN`).

**Architecture:** One CSS skin block appended to the page's own `<style>` plus new token values in the shared head (`model/build_local.py`, used by both builds). Home reuses the existing Overview section (`id="overview"`, renamed in the tab bar) with two new cards fed by `live` and `series`/`results`. A new script at the very end of the page renders them, so the `grading` calculation it reads is already registered. Bracket and Teams changes are small additions inside their existing scripts.

**Tech Stack:** Plain HTML/CSS/JS in `dashboard/index.html`; Python build (`model/build_local.py`, `model/build_site.py`); Playwright check (`tests/check_site.py`).

**Spec:** `docs/superpowers/specs/2026-10-16-website-design.md` (Phase 1). One deliberate change from the spec: on phones the tabs become a sideways-scrolling row of pills at the top, as drawn in `design/Phone.dc.html`, not a bottom bar.

## Global Constraints

- Repo root `worlds2026_bundle/worlds2026/`. FIRST `git pull --ff-only` (the bot pushes `data/` to main; retry once on a DNS error), then branch `site-phase1`. Local commits only; never push.
- Run Python as `python -X utf8`. Never edit `data/predictions_baseline.json`; `cd data && sha256sum -c predictions_baseline.sha256` must print OK after every task.
- Keep every tab's `data-page` id unchanged (`overview`, `dossiers`, `meta`, `predictions`, `pickems`, `scorecard`): deep links and `tests/check_site.py` depend on them.
- Copy: no em dashes in new text (the existing `—` empty-cell placeholders stay), dates dd/mm/yyyy, times NZDT.
- Palette (from `design/`): ground #0B0F14, surface #131A22, raised #1C2633, line #243040, text #EAF0F6, secondary text #B6C2D1, muted #93A1B3, accent gold #E8B84A, risk #F08A7A, bar #5B6B80. Fonts: Space Grotesk 500/700 (headings), IBM Plex Sans 400/500/600 (body).
- Commit messages plain, no `Co-Authored-By` trailer.

## Review Focus

- `live.json` missing or empty: the Home odds card shows "Live odds not available yet." and nothing else breaks (Task 2 code path; checked by building with the file present and reading the fallback branch).
- Every series already played: "Next up" falls back to "No upcoming predicted series." instead of an empty card.
- An ACTUAL row (a played series carried in a staged set) must show its result but never "pick right/wrong".
- `#team=XYZ` for an unknown code: no error, the page just opens normally.
- Phone width 390 px: no horizontal page scroll (tables scroll inside their own wrappers). Task 4 checks it.

---

### Task 1: dark theme, fonts, header mark, renamed and reordered tabs

**Files:**
- Modify: `model/build_local.py` (head literal, shim `colors`), `model/build_site.py` (shim `colors`), `dashboard/index.html` (header line 191, nav lines 196 to 203, append CSS before `</style>` at line 187)

**Interfaces:**
- Produces: CSS classes `.brand-mark`; CSS custom properties on `.w26`: `--w26-acc` (#E8B84A), `--w26-surface-2` (#1C2633), `--w26-text-2` (#B6C2D1). `dash.colors[0]` is gold in both builds.

- [ ] **Step 1: Pull and branch**

```bash
cd worlds2026_bundle/worlds2026
git pull --ff-only || (sleep 3 && git pull --ff-only)
git checkout -b site-phase1
```

- [ ] **Step 2: Head tokens in `model/build_local.py`**

Replace the fonts line

```
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
```

with

```
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
```

Replace these lines inside `:root { ... }`:

```
  --color-bg: #f6f7f9; --color-panel: #ffffff; --color-fg: #15191f; --color-fg-muted: #5d6673;
  --color-border-line: #dde1e7; --color-ok: #17804f; --color-warn: #a2650a; --color-bad: #c0352b;
  --cds-chart-grid: #e7eaef; --cds-chart-muted: #aab2bf;
```

with

```
  --color-bg: #0B0F14; --color-panel: #131A22; --color-fg: #EAF0F6; --color-fg-muted: #93A1B3;
  --color-border-line: #243040; --color-ok: #4cc98a; --color-warn: #E8B84A; --color-bad: #F08A7A;
  --cds-chart-grid: #1C2633; --cds-chart-muted: #5B6B80;
```

Replace `  --font-anthropic-serif: "Fraunces", Georgia, "Times New Roman", serif;` with `  --font-anthropic-serif: "Space Grotesk", "IBM Plex Sans", system-ui, sans-serif;`, `  --cds-radius: 10px; --cds-dur-slow: 300ms;` with `  --cds-radius: 16px; --cds-dur-slow: 300ms;`, and `  color-scheme: light;` with `  color-scheme: dark;`. Delete the whole `@media (prefers-color-scheme: dark) { :root { ... } }` block (the 7 lines starting `@media (prefers-color-scheme: dark) {`). The site is dark only.

- [ ] **Step 3: Shim colours, both builds**

In `model/build_local.py` (`SHIM`) and `model/build_site.py` (`SHIM`) replace

```
  const colors = () => dark.matches
    ? ['#6d9eff', '#ff7a6b', '#3ccf91', '#e8b03f', '#b18cff', '#3fc6cf', '#f06aa8', '#9aa7b8']
    : ['#2c62d1', '#cf3f30', '#17885c', '#a8720a', '#7a4fc9', '#0b8791', '#b8336f', '#5e6b7d'];
```

with

```
  const colors = () => ['#E8B84A', '#6d9eff', '#3ccf91', '#ff7a6b', '#b18cff', '#3fc6cf', '#f06aa8', '#9aa7b8'];   // dark site, gold accent first
```

(The `dark` constant and its listener stay; they are harmless.)

- [ ] **Step 4: Header and tabs in `dashboard/index.html`**

Replace `    <h1 class="site-title">Worlds 2026 Predictor</h1>` with

```html
    <h1 class="site-title"><span class="brand-mark" aria-hidden="true">26</span>Worlds 2026 Predictor</h1>
```

Replace the six `<button class="tab" ...>` lines (lines 197 to 202) with this order and labels (ids and `data-page` unchanged):

```html
    <button class="tab" role="tab" id="tab-overview" data-page="overview" aria-selected="true">Home</button>
    <button class="tab" role="tab" id="tab-predictions" data-page="predictions" aria-selected="false">Bracket</button>
    <button class="tab" role="tab" id="tab-dossiers" data-page="dossiers" aria-selected="false">Teams</button>
    <button class="tab" role="tab" id="tab-pickems" data-page="pickems" aria-selected="false">Pick'Ems</button>
    <button class="tab" role="tab" id="tab-scorecard" data-page="scorecard" aria-selected="false">Scorecard</button>
    <button class="tab" role="tab" id="tab-meta" data-page="meta" aria-selected="false">Meta</button>
```

Change the Overview page title `<h2 class="page-title">Overview</h2>` to `<h2 class="page-title">Home</h2>`.

- [ ] **Step 5: Skin CSS**

Insert immediately before the `</style>` that closes the page's style block (the one right after the line starting `@media (max-width: 520px) { .w26 .dl, .w26 .detail .dl`):

```css
/* ---------- site skin (design/*.dc.html, 16/10/2026) ---------- */
.w26 { --w26-acc: #E8B84A; --w26-surface-2: #1C2633; --w26-text-2: #B6C2D1; max-width: 1280px; }
.w26 .site-title, .w26 .page-title, .w26 .card-title { font-family: var(--font-anthropic-serif); font-weight: 700; letter-spacing: -0.01em; }
.w26 .site-title { display: flex; align-items: center; gap: 12px; font-size: 22px; }
.w26 .brand-mark { width: 28px; height: 28px; border-radius: 8px; background: var(--w26-acc); color: #0B0F14; display: inline-flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex: none; }
.w26 .tabs { background: var(--color-bg); gap: 4px; }
.w26 .tab { border: 0; border-radius: 8px; padding: 10px 14px; font-size: 14px; color: var(--w26-text-2); }
.w26 .tab[aria-selected="true"] { background: #161D27; color: var(--color-fg); font-weight: 600; border: 0; }
.w26 .label { letter-spacing: .08em; }
.w26 a:hover { color: var(--w26-acc); }
@media (max-width: 640px) {
  .w26 .tabs { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; gap: 6px; }
  .w26 .tabs::-webkit-scrollbar { display: none; }
  .w26 .tab { white-space: nowrap; border-radius: 999px; padding: 8px 12px; font-size: 13px; border: 1px solid var(--color-border-line); }
  .w26 .tab[aria-selected="true"] { background: var(--w26-surface-2); border-color: transparent; }
  .w26 .site-title { font-size: 16px; }
}
```

- [ ] **Step 6: Build both, run the site check**

```bash
python -X utf8 model/build_local.py
python -X utf8 model/build_site.py
python -X utf8 tests/check_site.py
```

Expected: both builds print their summary lines; the check prints `site OK` (tab order is read from the page, so the new order is fine).

- [ ] **Step 7: Commit**

```bash
(cd data && sha256sum -c predictions_baseline.sha256)
git add model/build_local.py model/build_site.py dashboard/index.html
git commit -m "Site skin: dark artboard palette, Space Grotesk headings, brand mark, renamed tabs, phone pill tabs"
```

---

### Task 2: Home cards (live title odds, next up, model record)

**Files:**
- Modify: `dashboard/index.html` (overview markup after the `.tiles` block; CSS skin block; new `<script>` appended after the last `</script>` in the file)

**Interfaces:**
- Consumes: datasets `live` (rows `team, p_champion, generated_nz`), `series` (rows `set, id, team_a, team_b, winner, p_winner, pw30, pw31, pw32, bo, time_nz, actual`), `results` (rows `id, team_a, team_b, winner`), calc `grading` (rows `set, n, correct`); helpers `window.W26.el/pct/rows/badge/teamLogo/show`.
- Produces: elements `#live-card`, `#live-odds` (one `.odds-row` per team, top 10), `#live-note`, `#next-card`, `#next-list` (up to 4 `a.next`), `#record-pill`.

- [ ] **Step 1: Markup**

In `dashboard/index.html`, directly after the closing `    </div>` of `<div class="tiles">` in the overview section (before `    <div class="card" id="rankings-card">`), insert:

```html
    <div class="grid home-row">
      <div class="card" id="live-card">
        <div class="card-head"><h3 class="card-title">Title odds</h3><span class="pill strong">Live</span></div>
        <p class="card-note" id="live-note">Refitted after every Worlds result; finished series are taken as fact.</p>
        <div class="odds" id="live-odds"></div>
      </div>
      <div class="card" id="next-card">
        <div class="card-head"><h3 class="card-title">Next up</h3><span class="pill" id="record-pill">Model record: no results yet</span></div>
        <div class="nextlist" id="next-list"></div>
      </div>
    </div>
```

- [ ] **Step 2: CSS (append to the end of the skin block from Task 1, before `</style>`)**

```css
.w26 .odds { display: grid; gap: 10px; }
.w26 .odds-row { display: grid; grid-template-columns: 24px 96px minmax(0, 1fr) 56px; align-items: center; gap: 12px; }
.w26 .odds-bar { height: 10px; border-radius: 999px; background: var(--w26-surface-2); overflow: hidden; }
.w26 .odds-bar > span { display: block; height: 100%; border-radius: 999px; background: #5B6B80; }
.w26 .odds-bar > span.lead { background: var(--w26-acc); }
.w26 .nextlist { display: grid; gap: 10px; }
.w26 a.next { display: grid; grid-template-columns: 48px minmax(0, 1fr) auto; align-items: center; gap: 14px; padding: 12px; border: 1px solid var(--color-border-line); border-radius: 12px; text-decoration: none; color: inherit; }
.w26 a.next:hover { border-color: var(--w26-acc); color: inherit; }
.w26 a.next img { width: 44px; height: 44px; object-fit: contain; }
.w26 .next-main { display: grid; gap: 3px; min-width: 0; }
.w26 .next-p { font-family: var(--font-anthropic-serif); font-size: 22px; font-weight: 700; color: var(--w26-acc); }
@media (max-width: 640px) { .w26 .odds-row { grid-template-columns: 20px 80px minmax(0, 1fr) 48px; gap: 8px; } }
```

- [ ] **Step 3: Script (append after the last `</script>` in the file)**

```html
<script>
// ---------- home: live title odds, next up, model record ----------
(() => {
  const { el, pct, rows } = window.W26;
  const pairKey = (x) => x.id + '|' + [x.team_a, x.team_b].sort().join('|');
  const sortKey = (s) => { const m = /(\d\d)\/(\d\d)\/(\d{4}) (\d\d):(\d\d)/.exec(s.time_nz || ''); return m ? m[3] + m[2] + m[1] + m[4] + m[5] : '9'; };
  dash.onData(() => {
    const live = (rows('live') || []).slice().sort((a, b) => b.p_champion - a.p_champion);
    const top = live.slice(0, 10); const max = top.length ? (top[0].p_champion || 1) : 1;
    document.getElementById('live-odds').replaceChildren(...(top.length ? top.map((x, i) => {
      const fill = el('span', { cls: i === 0 ? 'lead' : null }); fill.style.width = (100 * x.p_champion / max).toFixed(1) + '%';
      return el('div', { cls: 'odds-row' }, [el('span', { cls: 'cap muted num', text: String(i + 1) }), window.W26.badge(x.team),
        el('span', { cls: 'odds-bar' }, [fill]), el('span', { cls: 'num strong r', text: pct(x.p_champion, 1) })]);
    }) : [el('p', { cls: 'muted cap', text: 'Live odds not available yet.' })]));
    if (live[0]) document.getElementById('live-note').textContent = `Refitted ${live[0].generated_nz} on every result so far; finished series are taken as fact. The frozen picks never change.`;

    const series = rows('series') || []; const res = rows('results') || [];
    const played = new Set(res.filter((r) => r.winner).map(pairKey));
    const open = (s) => !s.actual && s.p_winner != null && !played.has(pairKey(s));
    const set = ['knockouts', 'swiss', 'playin', 'baseline'].find((st) => series.some((s) => s.set === st && open(s)));
    const next = series.filter((s) => s.set === set && open(s)).sort((a, b) => sortKey(a).localeCompare(sortKey(b))).slice(0, 4);
    document.getElementById('next-list').replaceChildren(...(next.length ? next.map((s) => el('a', { cls: 'next', href: '#predictions' }, [
      window.W26.teamLogo(s.winner) || window.W26.badge(s.winner),
      el('span', { cls: 'next-main' }, [el('span', { cls: 'strong', text: `${s.team_a} v ${s.team_b}` }),
        el('span', { cls: 'cap muted', text: `${s.time_nz || 'Time TBC'}. ${s.winner} to win` + (s.bo === 5 ? `. 3-0 ${pct(s.pw30)}, 3-1 ${pct(s.pw31)}, 3-2 ${pct(s.pw32)}` : '') })]),
      el('span', { cls: 'next-p num', text: pct(s.p_winner) }),
    ])) : [el('p', { cls: 'muted cap', text: 'No upcoming predicted series.' })]));

    const g = (dash.data('grading').data || []).find((x) => x.set === 'baseline');
    document.getElementById('record-pill').textContent = g && g.n ? `Model record: ${g.correct}/${g.n} winners` : 'Model record: no results yet';
  });
  document.getElementById('next-list').addEventListener('click', (e) => { if (e.target.closest('a.next')) { e.preventDefault(); window.W26.show('predictions'); } });
})();
</script>
```

- [ ] **Step 4: Build and check**

```bash
python -X utf8 model/build_site.py
python -X utf8 tests/check_site.py
python -X utf8 -c "
from playwright.sync_api import sync_playwright
import functools, http.server, threading
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory='dist/site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    pg = p.chromium.launch().new_page(); pg.goto(f'http://127.0.0.1:{srv.server_address[1]}/')
    pg.wait_for_function('Array.isArray(window.W26_MISSING)')
    print('odds rows', pg.locator('#live-odds .odds-row').count(), '| next', pg.locator('#next-list a.next').count(), '|', pg.inner_text('#record-pill'))
"
```

Expected: `site OK`; then `odds rows 10 | next 2 | Model record: no results yet` (two Play-In R1 series are still open in the committed data; if the bot has since added results, `next` and the record reflect them).

- [ ] **Step 5: Commit**

```bash
(cd data && sha256sum -c predictions_baseline.sha256)
git add dashboard/index.html
git commit -m "Home: live title odds, next up with picks, model record"
```

---

### Task 3: results beside picks on the Bracket, shareable team links

**Files:**
- Modify: `dashboard/index.html` (predictions script: `matchCard`; dossiers script: card head chips and end of `draw()`; CSS skin block)

**Interfaces:**
- Consumes: dataset `results`; dossier cards already have `id="team-<CODE>"`; `window.W26.show(id)`.
- Produces: `.result` line inside a match card when that series has a result; `a.pill.teamlink` (`href="#team=<CODE>"`) in each dossier card head; on load or `hashchange`, `#team=<CODE>` opens Teams and scrolls to that card.

- [ ] **Step 1: Result line in `matchCard`**

In the predictions script, directly after `  const matchCard = (s, key) => {` and its first line `    const aWin = s.winner === s.team_a;`, add:

```js
    const r = (rows('results') || []).find((x) => x.winner && x.id === s.id && [x.team_a, x.team_b].sort().join() === [s.team_a, s.team_b].sort().join());
    const score = r ? `${Math.max(r.score_a, r.score_b)}-${Math.min(r.score_a, r.score_b)}` : '';
    const resultLine = !r ? null : el('span', { cls: 'row cap result' }, [el('span', { cls: 'strong', text: `Result: ${r.winner} ${score}` }),
      s.actual ? null : pill(r.winner === s.winner ? 'pick right' : 'pick wrong', r.winner === s.winner ? 'good' : 'bad')]);
```

and add `resultLine,` as the last child in the array passed to `el('button', { cls: 'match', ... }, [ ... ])` (after the `el('span', { cls: 'split cap muted' }, ...)` entry, before the closing `]);`).

- [ ] **Step 2: Team link chip**

In the dossiers script, in the card head chips array

```js
          el('div', { cls: 'chips' }, [pill(`#${rank[x.code] || '—'} in model`, 'strong'), pill(`${x.region} seed ${x.seed}`, ''), pill(x.stage_start, x.stage_start === 'Play-In' ? 'warn' : '')]),
```

append a fourth child so it ends `..., pill(x.stage_start, x.stage_start === 'Play-In' ? 'warn' : ''), el('a', { cls: 'pill teamlink', href: '#team=' + x.code, text: 'Link' })]),`.

- [ ] **Step 3: Open `#team=CODE`**

In the dossiers script, add `let openedHash = '';` on the line after `let region = 'All'; let split = 'season';`. At the very end of `function draw() { ... }` (after the `document.getElementById('dossier-grid').replaceChildren(...)` statement), add:

```js
    const m = /^#team=([A-Za-z0-9]+)$/.exec(location.hash);
    const code = m ? m[1].toUpperCase() : '';
    const card = code && code !== openedHash ? document.getElementById('team-' + code) : null;
    if (card) {
      openedHash = code;
      window.W26.show('dossiers');
      history.replaceState(null, '', '#team=' + code);
      card.scrollIntoView({ block: 'start' });
    }
```

and after `dash.onData(draw);` in that script add `  window.addEventListener('hashchange', () => { openedHash = ''; draw(); });`. (If the dossiers script registers its draw differently, register the listener next to that registration and report it.)

- [ ] **Step 4: CSS (append to the skin block)**

```css
.w26 .match .result { color: var(--color-fg); }
.w26 a.pill.teamlink { text-decoration: none; color: var(--w26-acc); border-color: currentColor; }
```

- [ ] **Step 5: Build, check, commit**

```bash
python -X utf8 model/build_site.py
python -X utf8 tests/check_site.py
(cd data && sha256sum -c predictions_baseline.sha256)
git add dashboard/index.html
git commit -m "Bracket shows results beside picks; shareable #team= links on Teams"
```

Expected: `site OK`.

---

### Task 4: extend the site check (Home, team link, phone width) and screenshots

**Files:**
- Modify: `tests/check_site.py`

**Interfaces:**
- Produces: `check_site.py` also fails when the Home odds card has fewer than 10 rows, when `#team=GEN` does not open Teams with the GEN card in view, or when a 390 px wide page scrolls sideways; it writes screenshots to `dist/shots/` (`home.png`, `home_phone.png`, `bracket.png`, `team_gen.png`).

- [ ] **Step 1: Add the checks**

In `tests/check_site.py`, inside the `with sync_playwright() as p:` block, after the existing deep-link check and before `browser.close()`, add:

```python
        shots = os.path.join(ROOT, "dist", "shots"); os.makedirs(shots, exist_ok=True)
        page.goto(url); page.reload()
        page.wait_for_function("Array.isArray(window.W26_MISSING)", timeout=30000)
        if page.locator("#live-odds .odds-row").count() < 10:
            problems.append("Home: fewer than 10 live odds rows")
        page.screenshot(path=os.path.join(shots, "home.png"), full_page=True)
        page.click('.w26 .tab[data-page="predictions"]'); page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(shots, "bracket.png"), full_page=True)
        page.goto(url + "#team=GEN"); page.reload()
        page.wait_for_function("Array.isArray(window.W26_MISSING)", timeout=30000)
        page.wait_for_timeout(300)
        in_view = page.evaluate("(() => { const c = document.getElementById('team-GEN'); if (!c) return false; const r = c.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0; })()")
        if not page.is_visible("#dossiers") or not in_view:
            problems.append("#team=GEN did not open Teams at the GEN card")
        page.screenshot(path=os.path.join(shots, "team_gen.png"))
        phone = browser.new_page(viewport={"width": 390, "height": 844})
        phone.on("pageerror", lambda e: problems.append(f"phone page error: {e}"))
        phone.goto(url)
        phone.wait_for_function("Array.isArray(window.W26_MISSING)", timeout=30000)
        if phone.evaluate("document.documentElement.scrollWidth > innerWidth + 1"):
            problems.append("phone: page scrolls sideways at 390 px")
        phone.screenshot(path=os.path.join(shots, "home_phone.png"), full_page=True)
```

- [ ] **Step 2: Run**

```bash
python -X utf8 model/build_site.py
python -X utf8 tests/check_site.py
```

Expected: `site OK`. If the phone check fails, find the element wider than the viewport (`[...document.querySelectorAll('.w26 *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1)`), fix it in the skin CSS (wrap or `min-width: 0`), and report what it was.

- [ ] **Step 3: Run the model tests and commit**

```bash
python -X utf8 tests/test_v5.py
(cd data && sha256sum -c predictions_baseline.sha256)
git add tests/check_site.py dashboard/index.html
git commit -m "Site check: Home odds, team deep link, phone width, screenshots"
```

---

## Final gate (head)

- Review the screenshots in `dist/shots/` against `design/Main.dc.html` and `design/Phone.dc.html`.
- `python -X utf8 tests/test_v5.py` 18/18; `tests/check_site.py` `site OK`; baseline sha OK; no new em dashes (`git diff main..site-phase1 | grep "^+" | grep -c "—"` counts only the existing placeholder style, review each hit).
- Push only after the three gates; the Publish workflow deploys it.
