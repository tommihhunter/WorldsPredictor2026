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
