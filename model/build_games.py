#!/usr/bin/env python3
"""
Build the canonical 2026 series dataset for the model from the gol.gg scrape.

Input : data/golgg_series_2026.json (model/scrape_golgg.py)
Output: data/series_2026.json  one row per series:
        {date, tournament, stage, kind, league, a, b, sa, sb, bo, region_a, region_b, intl}
        data/team_map.json      gol.gg name -> code, region

Rules
- Codes: the 19 Worlds teams use the brief's codes; everyone else a short code.
- Region of a team = the league whose domestic tournaments it played in (derived, then checked).
- kind by stage: WEEK*/GROUPS*/SWISS*/SEEDING/TIEBREAKERS and numbered ROUNDs inside a
  regular-season tournament are "regular"; FINALS/SEMIFINALS/QUARTERFINALS/PLAYOFFS.*/
  PLAYIN.*/PLAY-IN*/LAST.CHANCE/3RD.* and anything inside a playoff tournament are "playoffs";
  international tournaments are "international"; EWC online qualifiers are "qualifier".
- bo = 2*max(score)-1 when one side reached the majority (1-0 -> Bo1, 2-x -> Bo3, 3-x -> Bo5).
  A 1-1 (one LCK Rounds 3-4 series) is split into two Bo1 rows.
- Cross-checked against the hand-compiled data/results_2026.json: every disagreement printed.
"""
import json, os, re, collections, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

CODES = {
 "Anyone s Legend": "AL", "Bilibili Gaming": "BLG", "Top Esports": "TES", "Invictus Gaming": "IG",
 "Gen.G": "GEN", "Hanwha Life Esports": "HLE", "T1": "T1", "Dplus KIA": "DK",
 "G2 Esports": "G2", "Movistar KOI": "MKOI", "Karmine Corp": "KC",
 "Team Liquid": "TLAW", "LYON": "LYON", "Cloud9": "C9",
 "Team Secret Whales": "TSW", "CTBC Flying Oyster": "CFO", "MVK Esports": "MVK",
 "Los Grandes": "LOS", "FURIA": "FURIA",
 # others
 "BNK FearX": "BNK", "DN SOOPers": "DNS", "HANJIN BRION": "BRO", "KT Rolster": "KT", "Kiwoom DRX": "DRX", "Nongshim RedForce": "NS",
 "EDward Gaming": "EDG", "JD Gaming": "JDG", "LGD Gaming": "LGD", "LNG Esports": "LNG", "Ninjas in Pyjamas": "NIP", "Oh My God": "OMG",
 "Team WE": "WE", "ThunderTalk Gaming": "TTG", "Ultra Prime": "UP", "Weibo Gaming": "WBG",
 "Fnatic": "FNC", "GIANTX": "GX", "Karmine Corp Blue": "KCB", "Los Ratones": "LR", "Natus Vincere": "NAVI", "SK Gaming": "SK",
 "Solary": "SLY", "Team Heretics": "TH", "Team Vitality": "VIT", "Galions": "GAL",
 "Dignitas": "DIG", "Disguised": "DSG", "FlyQuest": "FLY", "Sentinels": "SEN", "Shopify Rebellion": "SR",
 "Deep Cross Gaming": "DCG", "DetonatioN FocusMe": "DFM", "Fukuoka SoftBank HAWKS gaming": "SHG", "GAM Esports": "GAM", "Ground Zero Gaming": "GZ",
 "Fluxo W7M": "FLX", "LOUD": "LOUD", "Leviatan": "LEV", "RED Canids": "RED", "Vivo Keyd Stars": "VKS", "paiN Gaming": "PAIN", "Shifters": "SHIFT",
}
PLAYOFF_STAGE = re.compile(r"^(FINALS|SEMIFINALS|QUARTERFINALS|PLAYOFFS|PLAYIN|PLAY-IN|LAST\.CHANCE|3RD|KNIGHTS)")

rows = json.load(open("data/golgg_series_2026.json"))
missing = sorted({n for r in rows for n in (r["team_a"], r["team_b"]) if n not in CODES})
assert not missing, f"unmapped team names: {missing}"

# region per team from domestic appearances
seen = collections.defaultdict(collections.Counter)
for r in rows:
    if r["league"] != "INTL":
        for n in (r["team_a"], r["team_b"]):
            seen[CODES[n]][r["league"]] += 1
region = {}
for code, c in seen.items():
    lg, n = c.most_common(1)[0]
    if len(c) > 1:
        print("team seen in several leagues:", code, dict(c))
    region[code] = lg
for code in set(CODES.values()):
    region.setdefault(code, "UNKNOWN")
unknown = [c for c, g in region.items() if g == "UNKNOWN"]
if unknown:
    print("teams with no domestic games (region unknown):", unknown)

def kind_of(r):
    if r["kind"] == "international":
        return "international"
    if r["kind"] == "qualifier":
        return "qualifier"
    if r["kind"] == "playoffs" or PLAYOFF_STAGE.match(r["stage"]):
        return "playoffs"
    return "regular"

out = []
def push(r, sa, sb):
    a, b = CODES[r["team_a"]], CODES[r["team_b"]]
    bo = 2 * max(sa, sb) - 1
    out.append(dict(date=r["date"], tournament=r["tournament"], stage=r["stage"], kind=kind_of(r), league=r["league"],
                    a=a, b=b, sa=sa, sb=sb, bo=bo, region_a=region[a], region_b=region[b], patch=r["patch"],
                    intl=r["league"] == "INTL"))
for r in rows:
    if r["score_a"] == r["score_b"]:
        for _ in range(r["score_a"]):
            push(r, 1, 0); push(r, 0, 1)
        print("split tied series into Bo1s:", r["team_a"], r["score_a"], r["score_b"], r["team_b"], r["date"])
    else:
        push(r, r["score_a"], r["score_b"])

json.dump(out, open("data/series_2026.json", "w"), indent=0, ensure_ascii=False)
json.dump({n: dict(code=c, region=region[c]) for n, c in CODES.items()}, open("data/team_map.json", "w"), indent=1)

# ---- cross-check vs hand-compiled international results ----
hand = json.load(open("data/results_2026.json"))
alias = {"DPLUS": "DK", "MIBR.LOS": "LOS", "Sentinels": "SEN", "GIANTX": "GX"}
def key(a, b): return frozenset((alias.get(a, a), alias.get(b, b)))
gl = collections.defaultdict(list)
for r in out:
    if r["intl"]:
        gl[key(r["a"], r["b"])].append(r)
mism = 0; unmatched = 0
for h in hand:
    if h.get("event_group") == "supplementary":
        continue
    cands = gl.get(key(h["team_a"], h["team_b"]), [])
    hs = tuple(sorted((h["score_a"], h["score_b"]), reverse=True))
    if not cands:
        unmatched += 1; print("hand-compiled series not on gol.gg:", h["event"], h["team_a"], h["score_a"], h["score_b"], h["team_b"]); continue
    if not any(tuple(sorted((c["sa"], c["sb"]), reverse=True)) == hs for c in cands):
        mism += 1; print("score mismatch:", h["event"], h["team_a"], h["score_a"], h["score_b"], h["team_b"], "gol.gg:", [(c["a"], c["sa"], c["sb"], c["b"], c["date"]) for c in cands])
print(f"cross-check vs hand-compiled internationals: {len([h for h in hand if h.get('event_group')!='supplementary'])} series, {mism} score mismatches, {unmatched} unmatched")
k = collections.Counter(r["kind"] for r in out)
g = collections.Counter()
for r in out: g[r["kind"]] += r["sa"] + r["sb"]
print("series by kind:", dict(k)); print("games by kind:", dict(g), "total games", sum(g.values()))
print("regions:", dict(collections.Counter(region[c] for c in set(CODES.values()))))
