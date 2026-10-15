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
