#!/usr/bin/env python3
"""
Headless check of the v2 site: serve site/dist under $W26_BASE (default /poroprophet/), open every page in PAGES at
1280 and 390 px, and fail on page errors, console errors (except 404s under art/logos/), any 404 response,
root-absolute links that skip the base path, and sideways scroll at 390 px. Pages not built yet are skipped.
Screenshots go to site/shots/<page>-<width>.png (outside dist, so they are never published).
Run: python -X utf8 model/export_site_assets.py && (cd site && npm run build) && python -X utf8 tests/check_site.py
"""
import functools, http.server, os, re, shutil, sys, tempfile, threading
from playwright.sync_api import sync_playwright

PAGES = ["", "scorecard/", "meta/", "play-in/", "swiss/", "knockouts/", "demacia-cup/", "teams/", "teams/gen/",
         "teams/mvk/", "teams/compare/", "teams/compare/gen-vs-hle/"]
WIDTHS = [1280, 390]
BASE = os.environ.get("W26_BASE", "/poroprophet").strip("/")  # same env as site/astro.config.mjs
PREFIX = f"/{BASE}" if BASE else ""
OPTIONAL = f"{PREFIX}/art/logos/"  # missing logos are allowed to 404

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "site", "dist")
BAD_LINK = re.compile(rf'(?:href|src)="/(?!{BASE}/)[^"]*"') if BASE else None  # base "/": every root link is fine


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


VISIBLE_CARDS = "[...document.querySelectorAll('#teams-grid > a')].filter(c => c.offsetParent !== null)"


def check_teams_chips(page, tag, problems):
    """Teams grid: the LCK chip leaves only LCK cards; Blue side then puts the best blue-side record first."""
    page.click(".chip[data-region='LCK']")
    regions = page.evaluate(f"{VISIBLE_CARDS}.map(c => c.dataset.region)")
    print(f"{tag}: LCK chip shows {regions}")
    if not regions or set(regions) != {"LCK"}:
        problems.append(f"{tag}: LCK chip shows {regions}")
    page.click(".chip[data-sort='blue']")
    blues = page.evaluate(f"{VISIBLE_CARDS}.map(c => Number(c.dataset.blue))")
    print(f"{tag}: Blue side order {blues}, hash {page.evaluate('location.hash')}")
    if not blues or blues[0] != max(blues):
        problems.append(f"{tag}: Blue side sort puts {blues[:1]} first, max is {max(blues or [0])}")
    if page.evaluate("location.hash") != "#region=LCK&sort=blue":
        problems.append(f"{tag}: hash not written: {page.evaluate('location.hash')}")


def check_teams_nojs(browser, target, problems):
    """With JavaScript off every card shows, in rank order."""
    ctx = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(target, wait_until="networkidle")
    ranks = [int(x) for x in page.locator("#teams-grid > a:visible").evaluate_all("cs => cs.map(c => c.dataset.rank)")]
    print(f"teams no-JS: ranks {ranks}")
    if ranks != list(range(1, 20)):
        problems.append(f"teams no-JS: expected ranks 1 to 19 in order, got {ranks}")
    ctx.close()


REPORT_HEADINGS = ["Who they are", "Wins by", "Loses to", "Draft"]


def check_team_gen(page, tag, problems):
    """GEN team page: the four scouting-report headings and 5 visible player rows (one split shown at a time)."""
    heads = page.locator("#report h4").all_inner_texts()
    rows = page.locator("#players tr.player-row:visible").count()
    print(f"{tag}: report headings {heads}, player rows {rows}")
    if [h.strip().lower() for h in heads] != [h.lower() for h in REPORT_HEADINGS]:
        problems.append(f"{tag}: report headings {heads}, expected {REPORT_HEADINGS}")
    if rows != 5:
        problems.append(f"{tag}: expected 5 player rows, got {rows}")


def check_compare_pick(page, tag, problems):
    """Compare pickers: T1 then HLE lands on the canonical hle-vs-t1 page."""
    page.select_option("#compare-pick select[name=a]", "T1")
    page.select_option("#compare-pick select[name=b]", "HLE")
    with page.expect_navigation():
        page.click("#compare-pick button[type=submit]")
    print(f"{tag}: pickers T1, HLE -> {page.url}")
    if not page.url.endswith(f"{PREFIX}/teams/compare/hle-vs-t1/"):
        problems.append(f"{tag}: pickers landed on {page.url}, expected .../teams/compare/hle-vs-t1/")


def main():
    if not os.path.exists(os.path.join(DIST, "index.html")):
        sys.exit("build the site first: (cd site && npm run build)")
    problems, checked, skipped = [], [], []
    if not os.path.exists(os.path.join(DIST, "404.html")):  # GitHub Pages serves this for unknown paths
        problems.append("404.html missing from site/dist")

    for dirpath, _, files in (os.walk(DIST) if BAD_LINK else []):
        for f in files:
            if f.endswith(".html"):
                path = os.path.join(dirpath, f)
                with open(path, encoding="utf-8") as fh:
                    for hit in sorted(set(BAD_LINK.findall(fh.read()))):
                        problems.append(f"link without base path in {os.path.relpath(path, DIST)}: {hit}")

    tmp = tempfile.mkdtemp()
    shutil.copytree(DIST, os.path.join(tmp, BASE), ignore=shutil.ignore_patterns("shots"), dirs_exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=tmp))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}{PREFIX}/"
    shots = os.path.join(os.path.dirname(DIST), "shots"); os.makedirs(shots, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for pg in PAGES:
                if not os.path.exists(os.path.join(DIST, pg, "index.html")):
                    skipped.append(pg or "home")
                    print(f"{pg or 'home'}: not built yet, skipped")
                    continue
                name = pg.strip("/").replace("/", "-") or "home"
                checked.append(name)
                for w in WIDTHS:
                    tag = f"{name} @{w}"
                    page = browser.new_page(viewport={"width": w, "height": 900 if w > 600 else 844})
                    page.on("pageerror", lambda e, t=tag: problems.append(f"{t}: page error: {e}"))
                    page.on("console", lambda m, t=tag: problems.append(f"{t}: console error: {m.text} {m.location.get('url', '')}")
                            if m.type == "error" and OPTIONAL not in (m.location.get("url") or "") else None)
                    page.on("response", lambda r, t=tag: problems.append(f"{t}: 404 {r.url}")
                            if r.status == 404 and OPTIONAL not in r.url else None)
                    page.goto(url + pg, wait_until="networkidle")
                    if w == 390 and page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"):
                        problems.append(f"{tag}: page scrolls sideways")
                    page.screenshot(path=os.path.join(shots, f"{name}-{w}.png"), full_page=True)
                    if pg == "teams/":
                        check_teams_chips(page, tag, problems)
                    if pg == "teams/gen/":
                        check_team_gen(page, tag, problems)
                    if pg == "teams/compare/":
                        check_compare_pick(page, tag, problems)
                    page.close()
                if pg == "teams/":
                    check_teams_nojs(browser, url + pg, problems)
            browser.close()
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    print("pages checked:", checked)
    print("pages skipped:", skipped)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("site OK")


if __name__ == "__main__":
    main()
