#!/usr/bin/env python3
"""One-off art fetch for the site (run by hand, not by the bot): league logos and player photos (lolesports), objective
icons (CommunityDragon match-history set) and champion splash art (Data Dragon) for every team's most-picked champion
and the 12 most contested champions. Files land in dashboard/ (regions/, objectives/, ddragon_cache/) with
sources and the access date in dashboard/regions/_meta.json; model/export_site_assets.py copies them into the site.
Rate-limited to 0.4 s between requests. Skips files that already exist."""
import datetime, io, json, os, time, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(ROOT, "dashboard")
UA = {"User-Agent": "Mozilla/5.0 worlds2026-predictor (personal fan project)"}
# lolesports' public web client key (the same one lolesports.com sends from the browser)
LOLESPORTS_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
TODAY = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=13)).strftime("%d/%m/%Y")

def get(url, headers=None):
    time.sleep(0.4)
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def save_png(data, path, height):
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    im = im.resize((round(im.width * height / im.height), height), Image.LANCZOS)
    im.save(path, optimize=True)

meta = {}
# 1. league logos: our region codes -> lolesports league slugs
REG = os.path.join(DASH, "regions"); os.makedirs(REG, exist_ok=True)
SLUG = {"LCK": "lck", "LPL": "lpl", "LEC": "lec", "LCS": "lcs", "LCP": "lcp", "CBLOL": "cblol-brazil", "WORLDS": "worlds", "DCGI": "demacia_cup"}
leagues = json.loads(get("https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-GB", {"x-api-key": LOLESPORTS_KEY}))["data"]["leagues"]
by_slug = {l["slug"]: l for l in leagues}
for code, slug in SLUG.items():
    out = os.path.join(REG, f"{code}.png")
    src = by_slug[slug]["image"].replace("http://", "https://")
    if not os.path.exists(out):
        save_png(get(src), out, 96)
    meta[f"regions/{code}.png"] = {"source": src, "via": "esports-api.lolesports.com getLeagues", "accessed": TODAY}

# 2. objective icons (CommunityDragon, the client's match-history set)
OBJ = os.path.join(DASH, "objectives"); os.makedirs(OBJ, exist_ok=True)
for name in ("baron", "dragon", "herald", "tower", "inhibitor"):
    out = os.path.join(OBJ, f"{name}.png")
    src = f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-match-history/global/default/{name}-100.png"
    if not os.path.exists(out):
        save_png(get(src), out, 64)
    meta[f"objectives/{name}.png"] = {"source": src, "accessed": TODAY}

# 3. splash art (Data Dragon "centered"): each team's most-picked champion and the top 12 contested
art = json.load(open(os.path.join(ROOT, "site", "src", "lib", "art.json"), encoding="utf-8"))
key = lambda n: "".join(c for c in str(n).lower() if c.isalpha())
want = set()
for d in json.load(open(os.path.join(ROOT, "data", "dash", "dossiers.json"), encoding="utf-8")):
    picks = ((d.get("team_season") or {}).get("picks") or [])
    if picks: want.add(picks[0]["champ"])
for c in sorted(json.load(open(os.path.join(ROOT, "data", "dash", "meta_champs.json"), encoding="utf-8")), key=lambda c: c["rank"])[:12]:
    want.add(c["champion"])
CACHE = os.path.join(DASH, "ddragon_cache")
for name in sorted(want):
    f = art.get(key(name))
    if not f:
        print("no champion id for", name); continue
    cid = f[:-4]
    out = os.path.join(CACHE, f"cdn_img_champion_centered_{cid}_0.jpg")
    src = f"https://ddragon.leagueoflegends.com/cdn/img/champion/centered/{cid}_0.jpg"
    if not os.path.exists(out):
        open(out, "wb").write(get(src))
    meta[f"splash/{cid}.jpg"] = {"source": src, "accessed": TODAY}

# 4. player photos: the official lolesports headshot of every starter in data/dash/dossiers.json, matched by name
#    within the team's lolesports roster. All normalised to one 520x400 transparent canvas, head-and-shoulders centred.
PLY = os.path.join(DASH, "players"); os.makedirs(PLY, exist_ok=True)
TEAM_SLUG = {"GEN": "geng", "T1": "t1", "HLE": "hanwha-life-esports", "DK": "dwg-kia", "BLG": "bilibili-gaming", "AL": "anyones-legend",
             "IG": "invictus-gaming", "TES": "top-esports", "G2": "g2-esports", "KC": "karmine-corp", "MKOI": "mad-lions", "TLAW": "team-liquid",
             "LYON": "lyon-gaming", "C9": "cloud9", "TSW": "team-secret-whales", "CFO": "ctbc-flying-oyster", "FURIA": "furia", "LOS": "los",
             "MVK": "saigon-buffalo-esports"}
teams = {t["slug"]: t for t in json.loads(get("https://esports-api.lolesports.com/persisted/gw/getTeams?hl=en-GB", {"x-api-key": LOLESPORTS_KEY}))["data"]["teams"]}
alnum = lambda s: "".join(c for c in str(s).lower() if c.isalnum())
n_players, missing = 0, []
for d in json.load(open(os.path.join(ROOT, "data", "dash", "dossiers.json"), encoding="utf-8")):
    roster = {alnum(p["summonerName"]): p for p in teams.get(TEAM_SLUG.get(d["code"], ""), {}).get("players", [])}
    for pl in d.get("signature") or []:
        hit = roster.get(alnum(pl["player"]))
        if not hit or not hit.get("image"):
            missing.append(f'{d["code"]} {pl["player"]}'); continue
        slug = alnum(pl["player"]); out = os.path.join(PLY, f"{slug}.webp")
        src = hit["image"].replace("http://", "https://")
        if not os.path.exists(out):
            im = Image.open(io.BytesIO(get(src))).convert("RGBA")
            im = im.resize((round(im.width * 400 / im.height), 400), Image.LANCZOS)
            canvas = Image.new("RGBA", (520, 400), (0, 0, 0, 0))
            canvas.paste(im, ((520 - im.width) // 2, 0), im)
            canvas.save(out, quality=85, method=6)
        meta[f"players/{slug}.webp"] = {"source": src, "via": "esports-api.lolesports.com getTeams", "player": pl["player"], "team": d["code"], "accessed": TODAY}
        n_players += 1
print("players", n_players, "missing", missing)

json.dump(meta, open(os.path.join(REG, "_meta.json"), "w", encoding="utf-8"), indent=1)
print(f"regions {len(SLUG)}, objectives 5, splash {len(want)}")
