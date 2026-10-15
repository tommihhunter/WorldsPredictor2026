#!/usr/bin/env python3
"""
Headless check of the v2 site: serve site/dist under /WorldsPredictor2026/, open every page in PAGES at
1280 and 390 px, and fail on page errors, console errors (except 404s under art/logos/), any 404 response,
root-absolute links that skip the base path, and sideways scroll at 390 px. Pages not built yet are skipped.
Screenshots go to site/dist/shots/<page>-<width>.png.
Run: python -X utf8 model/export_site_assets.py && (cd site && npm run build) && python -X utf8 tests/check_site.py
"""
import functools, http.server, os, re, shutil, sys, tempfile, threading
from playwright.sync_api import sync_playwright

PAGES = ["", "scorecard/", "meta/", "play-in/", "swiss/", "knockouts/", "demacia-cup/", "teams/", "teams/gen/",
         "teams/mvk/", "teams/compare/", "teams/compare/gen-vs-hle/"]
WIDTHS = [1280, 390]
BASE = "WorldsPredictor2026"
OPTIONAL = f"/{BASE}/art/logos/"  # missing logos are allowed to 404

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "site", "dist")
BAD_LINK = re.compile(rf'(?:href|src)="/(?!{BASE}/)[^"]*"')


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    if not os.path.exists(os.path.join(DIST, "index.html")):
        sys.exit("build the site first: (cd site && npm run build)")
    problems, checked, skipped = [], [], []

    for dirpath, _, files in os.walk(DIST):
        for f in files:
            if f.endswith(".html"):
                path = os.path.join(dirpath, f)
                with open(path, encoding="utf-8") as fh:
                    for hit in sorted(set(BAD_LINK.findall(fh.read()))):
                        problems.append(f"link without base path in {os.path.relpath(path, DIST)}: {hit}")

    tmp = tempfile.mkdtemp()
    shutil.copytree(DIST, os.path.join(tmp, BASE), ignore=shutil.ignore_patterns("shots"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=tmp))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/{BASE}/"
    shots = os.path.join(DIST, "shots"); os.makedirs(shots, exist_ok=True)

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
                    page.close()
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
