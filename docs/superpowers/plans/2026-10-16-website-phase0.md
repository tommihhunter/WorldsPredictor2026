# Website Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the current dashboard live on GitHub Pages with a scheduled Action that pulls Worlds results, refreshes live odds and grading, commits `data/`, and republishes.

**Architecture:** `model/build_local.py` is split into a reusable `build_parts()` (data, Data Dragon art, logos, patched page, head, foot) and its existing `main()` (single offline file, byte-identical output). A new `model/build_site.py` reuses `build_parts()` to write a multi-file site (`dist/site/`) whose small `dash` shim fetches `data/<id>.json` and `assets.json` and then fires the page's `onData` callbacks. `tests/check_site.py` serves the build and opens every tab headless. Two workflows: `publish.yml` (push to main, manual) and `update.yml` (every 30 minutes in the event window, manual).

**Tech Stack:** Python 3.12, Pillow, Playwright (Chromium), GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-pages-artifact@v3`, `actions/deploy-pages@v4`).

**Spec:** `docs/superpowers/specs/2026-10-16-website-design.md` (Phase 0 only; Phase 1 restyle gets its own plan).

## Global Constraints

- Repo root `worlds2026_bundle/worlds2026/`; branch `site-phase0` (create in Task 1). Local commits only; never push (pushing, the visibility change and Pages settings are the head's gated Task 4).
- Run Python as `python -X utf8`; new code opens files with `encoding="utf-8"`.
- `data/predictions_baseline.json` is frozen: `cd data && sha256sum -c predictions_baseline.sha256` must print OK after every task.
- No new runtime dependencies in `requirements.txt` (Playwright is already there). No em dashes in prose. Dates dd/mm/yyyy, times NZDT.
- The bot may commit `data/` only (standing exception, 16/10/2026).
- Commit messages plain, no `Co-Authored-By` trailer.

## Review Focus

- A dataset file that fails to load must not blank the page: the shim marks it missing and still renders; `check_site.py` reports it.
- Teams without a logo file (MVK) request `logos/MVK.png` and get a 404; that resource error is expected and must not fail the check, but page errors must.
- Opening a deep link (`#tab-scorecard`) must land on that tab after the data loads.
- The update workflow must not commit or deploy when nothing changed on a scheduled run, and must never stage files outside `data/`.
- A push race between the bot and a human push: rebase and retry, never force.

---

### Task 1: split `model/build_local.py` into `build_parts()` + `main()` (output unchanged)

**Files:**
- Modify: `model/build_local.py`

**Interfaces:**
- Produces: `build_local.build_parts() -> dict` with keys `data` (dict id -> rows from `data/dash/*.json`), `assets` (dict, as embedded today), `missing_items` (list), `used` (list of champion names), `version` (str), `logo_files` (dict CODE -> png path), `plates` (dict CODE -> css class, HLE forced to "on-dark"), `page` (str: `dashboard/index.html` with the logo-badge patch applied, snapshot note NOT replaced), `head` (str), `foot` (str, formatted with the version). `build_local.main()` writes the single file exactly as today. `build_local.ROOT`, `build_local.OUT` stay module constants. Importing the module must not build anything.

- [ ] **Step 1: Branch and record today's output hash**

```bash
cd worlds2026_bundle/worlds2026
git checkout -b site-phase0
python -X utf8 model/build_local.py
sha256sum dist/worlds2026_predictor.html | tee dist/build_local_before.sha
```

Expected: the usual summary line (path, size about 1 MB, champions, logos). If it fails, STOP and report.

- [ ] **Step 2: Refactor**

Keep every string literal and every computation exactly as it is; only move code. Structure:
- Module level keeps: the docstring, imports, `ROOT`, `os.chdir(ROOT)`, `OUT`, `DD`, `CACHE`, `os.makedirs(CACHE, exist_ok=True)`, `LOGO_FILES` (both lines), and the helpers `get`, `data_uri`, `nkey`.
- New `def build_parts():` contains, in the same order, everything from `data = {...}` down to and including the `head = """..."""` and `foot = f"""..."""` assignments, EXCEPT: the line that replaces "Ask Claude to add results and this page grades itself." and the whole `shim` construction (the `shim = """<script>...` literal, `_meta` loading, the HLE plate override and the `shim = (shim.replace(...))` line). Move the `_meta` load and the `_meta["plates"]["HLE"] = "on-dark"` override into `build_parts()` too (they produce `plates`). It ends with `return dict(data=data, assets=assets, missing_items=missing_items, used=used, version=version, logo_files=LOGO_FILES, plates=_meta["plates"], page=page, head=head, foot=foot)`.
- The data-URI logo dict (`logos = {k: "data:image/png;base64," ...}`) moves into `main()`.
- New `SHIM = """<script>..."""` module constant holding the existing shim literal unchanged (with its `__LOGOS__`, `__PLATES__`, `__ASSETS__`, `__DATA__` placeholders).
- New `def main():` does: `p = build_parts()`; builds `logos` (data URIs from `p["logo_files"]`, same expression as today); `page = p["page"].replace("Ask Claude to add results and this page grades itself.", "This file is a snapshot: ask Claude for a fresh copy as results come in.")`; `shim = (SHIM.replace("__LOGOS__", json.dumps(logos)).replace("__PLATES__", json.dumps(p["plates"])).replace("__ASSETS__", json.dumps(p["assets"])).replace("__DATA__", json.dumps(p["data"], ensure_ascii=False)))`; `html = p["head"] + shim + "\n" + page + p["foot"] + "\n</div>\n</body>\n</html>\n"`; then the existing `os.makedirs`, write and print lines (using `p[...]` for `used`, `assets`, `missing_items`).
- End of file: `if __name__ == "__main__": main()`.

- [ ] **Step 3: Verify byte-identical output**

```bash
python -X utf8 model/build_local.py
sha256sum dist/worlds2026_predictor.html
cat dist/build_local_before.sha
python -X utf8 -c "import sys; sys.path.insert(0,'model'); import build_local as B; p=B.build_parts(); print(sorted(p), len(p['data']), p['version'])"
```

Expected: the two hashes are identical; the last line prints the 10 keys, the dataset count and `16.20.1`. If the hashes differ, fix the refactor until they match (do not change any string).

- [ ] **Step 4: Commit**

```bash
(cd data && sha256sum -c predictions_baseline.sha256)
git add model/build_local.py
git commit -m "build_local: split into build_parts() and main(), output unchanged"
```

---

### Task 2: `model/build_site.py` and `tests/check_site.py`

**Files:**
- Create: `model/build_site.py`, `tests/check_site.py`

**Interfaces:**
- Consumes: `build_local.build_parts()`, `build_local.ROOT`.
- Produces: `python -X utf8 model/build_site.py` writes `dist/site/` (override with env `W26_SITE`): `index.html`, `.nojekyll`, `assets.json`, `data/<id>.json` for every dataset, `logos/<CODE>.png` for every logo file. In the page: `window.W26_MISSING` (array of dataset ids that failed to load) is set once loading finishes. `python -X utf8 tests/check_site.py` exits 0 when the site renders every tab and a deep link with no page errors and no missing dataset, else prints the problems and exits 1.

- [ ] **Step 1: Write the check first**

Create `tests/check_site.py`:

```python
#!/usr/bin/env python3
"""
Headless check of the built website: serve dist/site, open the page, wait for the data, click every tab,
open a deep link, and fail on any page error, console error (except 404s for optional logos) or missing dataset.
Run: python -X utf8 model/build_site.py && python -X utf8 tests/check_site.py
"""
import functools, http.server, os, sys, threading
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.environ.get("W26_SITE", os.path.join(ROOT, "dist", "site"))


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    if not os.path.exists(os.path.join(SITE, "index.html")):
        sys.exit("build the site first: python -X utf8 model/build_site.py")
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=SITE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda e: problems.append(f"page error: {e}"))
        page.on("console", lambda m: problems.append(f"console error: {m.text}")
                if m.type == "error" and "Failed to load resource" not in m.text else None)
        page.goto(url)
        page.wait_for_function("Array.isArray(window.W26_MISSING)", timeout=30000)
        problems += [f"dataset missing: {d}" for d in page.evaluate("window.W26_MISSING")]
        tabs = page.eval_on_selector_all(".w26 .tab", "els => els.map(e => e.dataset.page)")
        if len(tabs) < 6:
            problems.append(f"expected 6 tabs, found {tabs}")
        for t in tabs:
            page.click(f'.w26 .tab[data-page="{t}"]')
            page.wait_for_timeout(150)
            if not page.is_visible(f"#{t}"):
                problems.append(f"tab {t} not visible after click")
        page.goto(url + "#" + tabs[-1])
        page.reload()
        page.wait_for_function("Array.isArray(window.W26_MISSING)", timeout=30000)
        if not page.is_visible(f"#{tabs[-1]}"):
            problems.append(f"deep link #{tabs[-1]} did not open that tab")
        browser.close()
    srv.shutdown()
    print("tabs checked:", tabs)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("site OK")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `python -X utf8 tests/check_site.py`
Expected: exits with `build the site first: python -X utf8 model/build_site.py`.

- [ ] **Step 3: Create `model/build_site.py`**

```python
#!/usr/bin/env python3
"""
Build the website (GitHub Pages) from the same page as the local single file (model/build_local.py).

dist/site/ (override with W26_SITE=/path):
  index.html     the dashboard page + a small `dash` shim that fetches the datasets below
  data/<id>.json one file per dataset in data/dash/
  assets.json    champion, item, lane and objective art (data URIs, from the Data Dragon cache)
  logos/<CODE>.png
  .nojekyll      serve files as-is on GitHub Pages
A dataset that fails to load is listed in window.W26_MISSING and shown as missing; the page still renders.
Run: python -X utf8 model/build_site.py   (then python -X utf8 tests/check_site.py)
"""
import json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import build_local as BL  # noqa: E402

OUT = os.environ.get("W26_SITE", os.path.join(BL.ROOT, "dist", "site"))
SHIM = """<script>
window.W26_LOGOS = __LOGOS__;
window.W26_LOGO_PLATES = __PLATES__;
window.W26_ASSETS = null;
(() => {
  const IDS = __IDS__;
  const DATA = {}, calcs = {}, cbs = [];
  let ready = false;
  const fire = (fn) => { try { fn(); } catch (e) { console.error(e); } };
  const dark = matchMedia('(prefers-color-scheme: dark)');
  const colors = () => dark.matches
    ? ['#6d9eff', '#ff7a6b', '#3ccf91', '#e8b03f', '#b18cff', '#3fc6cf', '#f06aa8', '#9aa7b8']
    : ['#2c62d1', '#cf3f30', '#17885c', '#a8720a', '#7a4fc9', '#0b8791', '#b8336f', '#5e6b7d'];
  window.dash = {
    get colors() { return colors(); },
    data(id) {
      if (id in DATA) return { status: 'ok', data: DATA[id], columns: DATA[id][0] ? Object.keys(DATA[id][0]) : [], meta: [] };
      if (calcs[id]) return { status: 'ok', data: calcs[id](), meta: [] };
      return { status: ready ? 'missing' : 'loading', data: [] };
    },
    onData(fn) { cbs.push(fn); if (ready) fire(fn); },
    calc(id, o) { calcs[id] = () => o.fn(...o.inputs.map((i) => DATA[i] || (calcs[i] ? calcs[i]() : []))); },
    setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) {} },
    params: () => ({}), setParams() {}, resetParams() {}, refresh() {},
  };
  const get = (u) => fetch(u, { cache: 'no-cache' }).then((r) => (r.ok ? r.json() : Promise.reject(new Error(u + ' ' + r.status))));
  Promise.all([
    ...IDS.map((id) => get('data/' + id + '.json').then((d) => { DATA[id] = d; }).catch((e) => console.warn('dataset missing', id, e))),
    get('assets.json').then((a) => { window.W26_ASSETS = a; }).catch((e) => console.warn('art missing', e)),
  ]).then(() => {
    ready = true;
    window.W26_MISSING = IDS.filter((id) => !(id in DATA));
    cbs.forEach(fire);
    const h = location.hash.slice(1);
    if (h && window.W26 && window.W26.show && document.getElementById(h)) window.W26.show(h);
  });
  dark.addEventListener('change', () => { if (ready) cbs.forEach(fire); });
})();
</script>"""


def main():
    p = BL.build_parts()
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "data")); os.makedirs(os.path.join(OUT, "logos"))
    for name, rows in p["data"].items():
        json.dump(rows, open(os.path.join(OUT, "data", name + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(p["assets"], open(os.path.join(OUT, "assets.json"), "w", encoding="utf-8"))
    logos = {}
    for code, path in p["logo_files"].items():
        if os.path.exists(path):
            shutil.copyfile(path, os.path.join(OUT, "logos", code + ".png"))
            logos[code] = f"logos/{code}.png"
    page = p["page"].replace("Ask Claude to add results and this page grades itself.",
                             "Results are added automatically as they are played.")
    head = p["head"].replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<link rel="icon" href="data:,">', 1)
    shim = (SHIM.replace("__LOGOS__", json.dumps(logos)).replace("__PLATES__", json.dumps(p["plates"]))
            .replace("__IDS__", json.dumps(sorted(p["data"]))))
    html = head + shim + "\n" + page + p["foot"] + "\n</div>\n</body>\n</html>\n"
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    print(OUT, f"index.html {len(html) / 1e3:.0f} kB", "| datasets:", len(p["data"]), "| logos:", sorted(logos),
          "| missing items:", p["missing_items"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Build and check, expect PASS**

```bash
python -X utf8 model/build_site.py
python -X utf8 tests/check_site.py
```

Expected: build prints `index.html` around 80 to 100 kB and all datasets; the check prints the six tabs and `site OK`. If the check reports a page error, fix the shim (not the page) and report what it was.

- [ ] **Step 5: Commit**

```bash
(cd data && sha256sum -c predictions_baseline.sha256)
git add model/build_site.py tests/check_site.py
git commit -m "Website build: multi-file site with a fetch-based dash shim, headless check"
```

---

### Task 3: GitHub Actions workflows and docs

**Files:**
- Create: `.github/workflows/publish.yml`, `.github/workflows/update.yml`
- Modify: `HANDOVER.md` (new "Website" section after "What this is"), `README.md` (one line under "Files")

**Interfaces:**
- Consumes: `model/update_results.py`, `model/scrape_golgg.py`, `model/build_games.py`, `model/live.py`, `model/export_dashboard.py`, `model/grade.py`, `tests/test_v5.py`, `model/build_site.py`, `tests/check_site.py`.
- Produces: workflow names `Publish` and `Update results`; both deploy to Pages in concurrency group `pages`.

- [ ] **Step 1: Create `.github/workflows/publish.yml`**

```yaml
name: Publish
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: |
          pip install numpy scipy Pillow playwright
          python -m playwright install --with-deps chromium
      - name: Model tests
        run: python -X utf8 tests/test_v5.py
      - name: Build site
        run: python -X utf8 model/build_site.py
      - name: Check site
        run: python -X utf8 tests/check_site.py
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist/site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Create `.github/workflows/update.yml`**

```yaml
name: Update results
on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:
permissions:
  contents: write
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  update:
    runs-on: ubuntu-latest
    outputs:
      publish: ${{ steps.data.outputs.publish }}
    steps:
      - name: Event window (16/10 to 16/11/2026 NZDT)
        id: window
        run: |
          d=$(TZ=Pacific/Auckland date +%Y%m%d)
          if [ "${{ github.event_name }}" != "schedule" ] || { [ "$d" -ge 20261016 ] && [ "$d" -le 20261116 ]; }; then
            echo "run=yes" >> "$GITHUB_OUTPUT"
          else
            echo "outside the event window ($d)"; echo "run=no" >> "$GITHUB_OUTPUT"
          fi
      - uses: actions/checkout@v4
        if: steps.window.outputs.run == 'yes'
      - uses: actions/setup-python@v5
        if: steps.window.outputs.run == 'yes'
        with:
          python-version: "3.12"
      - name: Install model
        if: steps.window.outputs.run == 'yes'
        run: pip install numpy scipy Pillow
      - name: Pull results and refresh data
        id: data
        if: steps.window.outputs.run == 'yes'
        run: |
          python -X utf8 model/update_results.py
          if git diff --quiet -- data/results_live.json; then
            echo "no new results"
            if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then echo "publish=yes" >> "$GITHUB_OUTPUT"; else echo "publish=no" >> "$GITHUB_OUTPUT"; fi
            exit 0
          fi
          python -X utf8 model/scrape_golgg.py
          python -X utf8 model/build_games.py
          python -X utf8 model/live.py
          python -X utf8 model/export_dashboard.py
          python -X utf8 model/grade.py
          echo "publish=yes" >> "$GITHUB_OUTPUT"
      - name: Model tests
        if: steps.data.outputs.publish == 'yes'
        run: python -X utf8 tests/test_v5.py
      - name: Commit data (data/ only)
        if: steps.data.outputs.publish == 'yes'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/
          if git diff --cached --quiet; then echo "no data changes to commit"; exit 0; fi
          git commit -m "data: results update $(TZ=Pacific/Auckland date '+%d/%m/%Y %H:%M') NZDT"
          for i in 1 2 3; do git push && exit 0; git pull --rebase; done
          exit 1
      - name: Install browser
        if: steps.data.outputs.publish == 'yes'
        run: |
          pip install playwright
          python -m playwright install --with-deps chromium
      - name: Build and check site
        if: steps.data.outputs.publish == 'yes'
        run: |
          python -X utf8 model/build_site.py
          python -X utf8 tests/check_site.py
      - uses: actions/upload-pages-artifact@v3
        if: steps.data.outputs.publish == 'yes'
        with:
          path: dist/site
  deploy:
    needs: update
    if: needs.update.outputs.publish == 'yes'
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Validate the YAML locally**

```bash
python -m pip install --quiet pyyaml
python -X utf8 -c "import yaml,glob; [print(f, sorted(yaml.safe_load(open(f, encoding='utf-8'))['jobs'])) for f in glob.glob('.github/workflows/*.yml')]"
```

Expected: `publish.yml ['build', 'deploy']` and `update.yml ['deploy', 'update']`. (pyyaml is a local check tool only; do not add it to requirements.txt.)

- [ ] **Step 4: Docs**

In `HANDOVER.md`, after the "## What this is" paragraph, add:

```markdown
## Website
- Live site: https://tommihhunter.github.io/poroprophet/ (GitHub Pages, built by `model/build_site.py` from the same page as the local file; `tests/check_site.py` opens every tab headless before each deploy).
- `.github/workflows/publish.yml`: every push to main (and on demand) runs the model tests, builds, checks and deploys.
- `.github/workflows/update.yml`: every 30 minutes from 16/10 to 16/11/2026 NZDT (and on demand) pulls Worlds results from gol.gg; when there is something new it rescrapes, refreshes live odds, exports, regrades, runs the tests, commits `data/` only (bot commit, agreed 16/10/2026) and deploys. Pull before working locally: the bot pushes to main.
- Rows the bot adds have no `start_nz` (gol.gg has no start times); grading treats them as valid because every frozen pick was made before its stage began.
```

In `README.md`, under "## Files", add the line:

```markdown
- `model/build_site.py` -> `dist/site/` (the website; deployed by `.github/workflows/publish.yml` and `update.yml`), checked by `tests/check_site.py`.
```

- [ ] **Step 5: Commit**

```bash
(cd data && sha256sum -c predictions_baseline.sha256)
git add .github/workflows/publish.yml .github/workflows/update.yml HANDOVER.md README.md
git commit -m "GitHub Actions: publish on push, scheduled results update with data-only bot commits"
```

---

### Task 4: go live (head only, gated)

Not for a subagent. The head shows Tommi, verbatim, every remote action and waits for an explicit go: (1) merge `site-phase0` into `main` and push; (2) `gh repo edit tommihhunter/poroprophet --visibility public --accept-visibility-change-consequences`; (3) `gh api -X POST repos/tommihhunter/poroprophet/pages -f build_type=workflow`; (4) `gh workflow run publish.yml` then `gh workflow run "Update results"`. Then verify: the Publish run is green, the URL serves the page, `tests/check_site.py` against the live URL equivalent passes (open it headless), and the Update run fetched gol.gg (its log shows the Play-In match list) without errors.
