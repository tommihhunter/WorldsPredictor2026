#!/usr/bin/env python3
"""
Build the standalone local copy of the dashboard (one HTML file, everything embedded).

* Same page as the hosted dashboard (dashboard/index.html), run through a small
  `dash` shim so it works from a file, offline, and in previews that block the network.
* Game art from Riot's Data Dragon (official developer CDN; mirrored at
  github.com/noxelisdev/LoL_DDragon), downloaded at build time and embedded:
    - square icons for every champion named anywhere in the data
    - splash art for the three most-contested champions
    - tile portraits for the Crystal Ball champion answers
    - item icons for the 26.20 item changes
* Team logos: logos the user supplied (LOGO_FILES / dashboard/logos/*.png) are
  embedded; other teams look for logos/<CODE>.png next to the file, else keep
  their colour badge.
Run: python3 model/build_local.py  -> dist/worlds2026_predictor.html (override with W26_OUT=/path)
"""
import json, os, re, io, base64, glob, urllib.request
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = os.environ.get("W26_OUT", os.path.join(ROOT, "dist", "worlds2026_predictor.html"))
DD = "https://ddragon.leagueoflegends.com"
CACHE = "dashboard/ddragon_cache"
os.makedirs(CACHE, exist_ok=True)
LOGO_FILES = {"T1": "/root/.claude/uploads/1d204bdd-0868-575c-b191-950a1b7d4400/9198c31c-image.png"}
LOGO_FILES.update({os.path.basename(p)[:-4]: p for p in glob.glob("dashboard/logos/*.png")})


def get(url):
    path = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9._-]", "_", url.split("ddragon.leagueoflegends.com/")[-1]))
    if not os.path.exists(path):
        with urllib.request.urlopen(url, timeout=30) as r:
            open(path, "wb").write(r.read())
    return open(path, "rb").read()


def data_uri(raw, size, fmt="JPEG", q=82, crop=None):
    im = Image.open(io.BytesIO(raw)).convert("RGBA" if fmt == "PNG" else "RGB")
    if crop:
        im = im.crop(crop(im))
    im.thumbnail(size, Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, fmt, **({"quality": q, "optimize": True} if fmt == "JPEG" else {"optimize": True}))
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


nkey = lambda n: re.sub(r"[^a-z]", "", str(n).lower())


SHIM = """<script>
window.W26_LOGOS = __LOGOS__;
window.W26_LOGO_PLATES = __PLATES__;
window.W26_ASSETS = __ASSETS__;
(() => {
  const DATA = __DATA__;
  const calcs = {}, cbs = [];
  const dark = matchMedia('(prefers-color-scheme: dark)');
  const colors = () => ['#E8B84A', '#6d9eff', '#3ccf91', '#ff7a6b', '#b18cff', '#3fc6cf', '#f06aa8', '#9aa7b8'];   // dark site, gold accent first
  window.dash = {
    get colors() { return colors(); },
    data(id) {
      if (id in DATA) return { status: 'ok', data: DATA[id], columns: DATA[id][0] ? Object.keys(DATA[id][0]) : [], meta: [] };
      if (calcs[id]) return { status: 'ok', data: calcs[id](), meta: [] };
      return { status: 'missing', data: [] };
    },
    onData(fn) { cbs.push(fn); try { fn(); } catch (e) { console.error(e); } },
    calc(id, o) { calcs[id] = () => o.fn(...o.inputs.map((i) => DATA[i] || (calcs[i] ? calcs[i]() : []))); },
    setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) {} },
    params: () => ({}), setParams() {}, resetParams() {}, refresh() {},
  };
  dark.addEventListener('change', () => cbs.forEach((f) => { try { f(); } catch (e) { console.error(e); } }));
})();
</script>"""


def build_parts():
    data = {os.path.basename(p)[:-5]: json.load(open(p)) for p in glob.glob("data/dash/*.json")}
    version = json.loads(get(f"{DD}/api/versions.json"))[0]
    champs = json.loads(get(f"{DD}/cdn/{version}/data/en_US/champion.json"))["data"]
    items = json.loads(get(f"{DD}/cdn/{version}/data/en_US/item.json"))["data"]
    name_to_id = {}
    for cid, c in champs.items():
        name_to_id[c["name"]] = cid

    # every champion named anywhere in the dashboard's data (case-sensitive, whole word)
    blob = json.dumps(data, ensure_ascii=False)
    blob_alt = blob.replace("KSante", "K'Sante")
    used = sorted(n for n in name_to_id if re.search(r"(?<![A-Za-z])" + re.escape(n) + r"(?![A-Za-z])", blob_alt))
    assets = {"champ": {}, "tile": {}, "splash": {}, "item": {}, "names": used, "version": version}
    for n in used:
        assets["champ"][nkey(n)] = data_uri(get(f"{DD}/cdn/{version}/img/champion/{name_to_id[n]}.png"), (64, 64))
    for c in data.get("meta_champs", [])[:3]:
        cid = name_to_id.get(c["champion"])
        if cid:
            assets["splash"][nkey(c["champion"])] = data_uri(get(f"{DD}/cdn/img/champion/centered/{cid}_0.jpg"), (720, 405), q=74)
    for c in data.get("crystal", []):
        if c["q"] in (1, 2, 3) and c["answer"] in name_to_id:
            assets["tile"][nkey(c["answer"])] = data_uri(get(f"{DD}/cdn/img/champion/tiles/{name_to_id[c['answer']]}_0.jpg"), (120, 120))
    item_names = [r["name"] for r in data.get("patch_changes", []) if r["kind"] == "item"]
    for nm in item_names:
        iid = next((k for k, v in items.items() if v.get("name", "").lower() == nm.lower() and v.get("gold", {}).get("purchasable", True)), None) \
            or next((k for k, v in items.items() if v.get("name", "").lower() == nm.lower()), None)
        if iid:
            assets["item"][nkey(nm)] = data_uri(get(f"{DD}/cdn/{version}/img/item/{iid}.png"), (64, 64))
    missing_items = [n for n in item_names if nkey(n) not in assets["item"]]
    # lane and objective icons from the LoL_DDragon "extras" pack (github.com/noxelisdev/LoL_DDragon/tree/master/extras)
    EX = "dashboard/extras"
    assets["lane"] = {k: data_uri(open(f"{EX}/{f}.png", "rb").read(), (40, 40), fmt="PNG") for k, f in
                      [("top", "top"), ("jungle", "jungle"), ("mid", "middle"), ("bot", "bottom"), ("support", "support")] if os.path.exists(f"{EX}/{f}.png")}
    assets["obj"] = {k: data_uri(open(f"{EX}/{f}.png", "rb").read(), (48, 48), fmt="PNG") for k, f in
                     [("baron", "nashor"), ("gold", "gold"), ("dragon", "infernal")] if os.path.exists(f"{EX}/{f}.png")}

    page = open("dashboard/index.html").read()

    old_badge = """  const badge = (code, attrs = {}) => {
    const g = regionOf(code);
    const b = el('span', { ...attrs, cls: 'badge' + (attrs.cls ? ' ' + attrs.cls : ''), title: attrs.title || (g ? `${code} · ${g}` : code), text: code });
    b.style.setProperty('--b', regionColor(g));
    return b;
  };"""
    new_badge = """  const badge = (code, attrs = {}) => {
    const g = regionOf(code);
    const b = el('span', { ...attrs, cls: 'badge' + (attrs.cls ? ' ' + attrs.cls : ''), title: attrs.title || (g ? `${code} · ${g}` : code) });
    b.style.setProperty('--b', regionColor(g));
    const im = el('img', { cls: 'logo ' + ((window.W26_LOGO_PLATES || {})[code] || ''), alt: '', src: window.W26_LOGOS[code] || `logos/${code}.png` });
    im.addEventListener('error', () => im.remove(), { once: true });
    b.append(im, document.createTextNode(code));
    return b;
  };"""
    assert old_badge in page
    page = page.replace(old_badge, new_badge)
    _meta = json.load(open("dashboard/logos/_meta.json")) if os.path.exists("dashboard/logos/_meta.json") else {"plates": {}}
    _meta["plates"]["HLE"] = "on-dark"

    head = """<!doctype html>
<html lang="en-NZ">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Worlds 2026 Predictor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root {
  --color-bg: #0B0F14; --color-panel: #131A22; --color-fg: #EAF0F6; --color-fg-muted: #93A1B3;
  --color-border-line: #243040; --color-ok: #4cc98a; --color-warn: #E8B84A; --color-bad: #F08A7A;
  --cds-chart-grid: #1C2633; --cds-chart-muted: #5B6B80;
  --font-anthropic-sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-anthropic-serif: "Space Grotesk", "IBM Plex Sans", system-ui, sans-serif;
  --cds-font-size-caption: 12.5px; --cds-font-size-body: 14.5px; --cds-font-size-heading: 17px; --cds-font-size-title: 28px;
  --cds-font-weight-medium: 600;
  --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 12px; --cds-gap-lg: 20px; --cds-gap-xl: 32px;
  --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 12px; --cds-pad-lg: 18px; --cds-pad-xl: 28px;
  --cds-radius: 16px; --cds-dur-slow: 300ms;
  color-scheme: dark;
}
html, body { margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); font-size: 14px; }
#dash-root { padding-block: 24px 48px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.w26 .badge { gap: 6px; }
.w26 .badge img.logo { height: 18px; width: auto; max-width: 40px; object-fit: contain; border-radius: 3px; }

.w26 h3 .badge img.logo { width: 22px; height: 22px; }
</style>
</head>
<body>
<div id="dash-root">
"""
    foot = f"""
<p style="max-width:1180px;margin:32px auto 0;font-size:11.5px;color:var(--color-fg-muted)">Team logos from github.com/lootmarket/esport-team-logos. Champion, item, lane and objective art from Riot Games' Data Dragon and the LoL_DDragon extras pack (patch {version}), used under Riot's Legal Jibber Jabber policy. Worlds 2026 Predictor isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing League of Legends.</p>
"""
    return dict(data=data, assets=assets, missing_items=missing_items, used=used, version=version, logo_files=LOGO_FILES,
                plates=_meta["plates"], page=page, head=head, foot=foot)


def main():
    p = build_parts()
    logos = {k: "data:image/png;base64," + base64.b64encode(open(v, "rb").read()).decode() for k, v in p["logo_files"].items() if os.path.exists(v)}
    page = p["page"].replace("Ask Claude to add results and this page grades itself.",
                             "This file is a snapshot: ask Claude for a fresh copy as results come in.")
    shim = (SHIM.replace("__LOGOS__", json.dumps(logos)).replace("__PLATES__", json.dumps(p["plates"])).replace("__ASSETS__", json.dumps(p["assets"]))
            .replace("__DATA__", json.dumps(p["data"], ensure_ascii=False)))
    html = p["head"] + shim + "\n" + page + p["foot"] + "\n</div>\n</body>\n</html>\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(html)
    print(OUT, f"{len(html)/1e6:.2f} MB", "| champions:", len(p["used"]), "| splash:", list(p["assets"]["splash"]), "| tiles:", list(p["assets"]["tile"]),
          "| items:", list(p["assets"]["item"]), "missing items:", p["missing_items"], "| logos:", sorted(logos))


if __name__ == "__main__":
    main()
