#!/usr/bin/env python3
"""Copy team logos and cached Riot art into site/public/art/ for the Astro build. Run after export_dashboard.py."""
import glob, json, os, re, shutil
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
champs = copy_all(os.path.join(CACHE, "cdn_*_img_champion_*.png"), os.path.join(OUT, "champ"), lambda f: f.split("_img_champion_")[1])
items = copy_all(os.path.join(CACHE, "cdn_*_img_item_*.png"), os.path.join(OUT, "item"), lambda f: f.split("_img_item_")[1])
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
print(f"logos {logos} extras {extras} champions {champs} items {items}")
