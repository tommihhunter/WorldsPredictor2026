#!/usr/bin/env python3
"""Copy team logos and cached Riot art into site/public/art/ for the Astro build, and resize the poroprophets/ mascots. Run after export_dashboard.py."""
import glob, json, os, re, shutil
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "public", "art")
CACHE = os.path.join(ROOT, "dashboard", "ddragon_cache")
nkey = lambda n: re.sub(r"[^a-z]", "", str(n).lower())

def copy_all(pattern, dest, rename=lambda f: f):
    os.makedirs(dest, exist_ok=True); n = 0
    for p in sorted(glob.glob(pattern)):
        shutil.copyfile(p, os.path.join(dest, rename(os.path.basename(p)))); n += 1
    return n

logos = copy_all(os.path.join(ROOT, "dashboard", "logos", "*.png"), os.path.join(OUT, "logos"))
extras = copy_all(os.path.join(ROOT, "dashboard", "extras", "*.png"), os.path.join(OUT, "extras"))
regions = copy_all(os.path.join(ROOT, "dashboard", "regions", "*.png"), os.path.join(OUT, "regions"))
objectives = copy_all(os.path.join(ROOT, "dashboard", "objectives", "*.png"), os.path.join(OUT, "objectives"))
champs = copy_all(os.path.join(CACHE, "cdn_*_img_champion_*.png"), os.path.join(OUT, "champ"), lambda f: f.split("_img_champion_")[1])
items = copy_all(os.path.join(CACHE, "cdn_*_img_item_*.png"), os.path.join(OUT, "item"), lambda f: f.split("_img_item_")[1])
# Splash ("centered", 1280x720) and loading-screen tiles for the champions the cache holds: resized for the web.
def resize_all(kind, dest, width):
    os.makedirs(dest, exist_ok=True); n = 0
    for p in sorted(glob.glob(os.path.join(CACHE, f"cdn_img_champion_{kind}_*_0.jpg"))):
        name = os.path.basename(p).split(f"_{kind}_")[1].rsplit("_", 1)[0]
        im = Image.open(p).convert("RGB")
        im.resize((width, round(im.height * width / im.width)), Image.LANCZOS).save(os.path.join(dest, f"{name}.jpg"), quality=82, optimize=True); n += 1
    return n
splash = resize_all("centered", os.path.join(OUT, "splash"), 960)
tiles = resize_all("tiles", os.path.join(OUT, "tile"), 240)
files = set(os.listdir(os.path.join(OUT, "champ")))
art = {nkey(f[:-4]): f for f in files}
# Display names differ from Riot ids for some champions (Wukong is MonkeyKing, Renata Glasc is Renata): map those too.
for p in glob.glob(os.path.join(CACHE, "cdn_*_data_en_US_champion.json")):
    for cid, c in json.load(open(p, encoding="utf-8"))["data"].items():
        if f"{cid}.png" in files:
            art.setdefault(nkey(c["name"]), f"{cid}.png")
os.makedirs(os.path.join(ROOT, "site", "src", "lib"), exist_ok=True)
with open(os.path.join(ROOT, "site", "src", "lib", "art.json"), "w", encoding="utf-8") as fh:
    json.dump(art, fh, indent=0, sort_keys=True)
# Mascots: poroprophets/*.jpg are the source of truth; sizes are what the site uses (brand mark, home, 404, favicon, OG).
PORO = os.path.join(OUT, "poro"); os.makedirs(PORO, exist_ok=True)
for name, src in (("main", "PoroMain.jpg"), ("dopey", "PoroDopey.jpg")):
    im = Image.open(os.path.join(ROOT, "poroprophets", src)).convert("RGB")
    im.resize((256, 256), Image.LANCZOS).save(os.path.join(PORO, f"{name}-256.png"), optimize=True)
    im.resize((512, 512), Image.LANCZOS).save(os.path.join(PORO, f"{name}-512.webp"), quality=82)
    if name == "main":
        im.resize((64, 64), Image.LANCZOS).save(os.path.join(PORO, "favicon.png"), optimize=True)
        im.resize((180, 180), Image.LANCZOS).save(os.path.join(PORO, "apple-touch.png"), optimize=True)
print("poro", ", ".join(f"{f} {os.path.getsize(os.path.join(PORO, f)) // 1024} kB" for f in sorted(os.listdir(PORO))))
print(f"logos {logos} extras {extras} regions {regions} objectives {objectives} champions {champs} items {items} splash {splash} tiles {tiles}")
