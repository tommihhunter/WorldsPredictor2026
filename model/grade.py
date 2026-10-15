#!/usr/bin/env python3
"""
Phase 5 grading. Run after each stage and after the final.

Input:  data/results_live.json  (append results as the event runs)
  series row:       {"id":"PI-R1-A","phase":"Play-In","kind":"series","date_nz":"16/10/2026",
                     "start_nz":"16/10/2026 07:00","team_a":"KC","team_b":"C9","score_a":3,"score_b":1,"winner":"KC"}
  swiss record row: {"kind":"swiss_record","team":"GEN","record":"3-0"}
Output: data/grading.json + printed report.

Rules: a prediction is graded only if it was created before the series started
(`start_nz`); otherwise it is flagged INVALID - post-start and excluded.
Pairing match: explicit id first, then same phase + same two teams, then a
conditional Play-In pairing (staged sets only).
"""
import json, math, glob, os, datetime as dt
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
NZ = dt.timezone(dt.timedelta(hours=13))


def parse_nz(s):
    try:
        return dt.datetime.strptime(s.replace(" NZDT", "").replace(" NZST", ""), "%d/%m/%Y %H:%M:%S").replace(tzinfo=NZ)
    except ValueError:
        return dt.datetime.strptime(s.replace(" NZDT", ""), "%d/%m/%Y %H:%M").replace(tzinfo=NZ)


series = json.load(open("data/dash/series.json"))
results = json.load(open("data/results_live.json"))
pair = lambda s: tuple(sorted((s["team_a"], s["team_b"])))
sets = sorted({s["set"].replace("_conditional", "") for s in series})


def match(r, st):
    pool = [s for s in series if s["set"] in (st, st + "_conditional") and not s.get("actual") and s.get("p_series_a") is not None]
    for cond in (lambda s: s["id"] == r.get("id") and pair(s) == pair(r) and s["set"] == st,
                 lambda s: s["phase"] == r.get("phase") and pair(s) == pair(r) and s["set"] == st,
                 lambda s: pair(s) == pair(r) and s["set"] == st + "_conditional"):
        hit = [s for s in pool if cond(s)]
        if hit:
            return hit[0]
    return None


report = {}
for st in sets:
    g = dict(n=0, correct=0, exact=0, brier=0.0, ll=0.0, invalid=[], tiers=defaultdict(lambda: [0, 0, 0.0]), misses=[])
    for r in results:
        if r.get("kind") == "swiss_record" or not r.get("winner"):
            continue
        s = match(r, st)
        if not s:
            continue
        if r.get("start_nz") and parse_nz(s["created_nz"]) >= parse_nz(r["start_nz"]):
            g["invalid"].append(r["id"]); continue
        p_win = s["p_series_a"] if r["winner"] == s["team_a"] else 1 - s["p_series_a"]
        hit = s["winner"] == r["winner"]
        sc = f"{max(r['score_a'], r['score_b'])}-{min(r['score_a'], r['score_b'])}"
        g["n"] += 1; g["correct"] += hit; g["exact"] += hit and sc == s["score"]
        g["brier"] += (1 - p_win) ** 2; g["ll"] += -math.log(max(1e-9, p_win))
        t = g["tiers"][s["tier"]]; t[0] += 1; t[1] += hit; t[2] += s["p_winner"]
        if not hit:
            g["misses"].append(dict(id=r["id"], predicted=f"{s['winner']} {s['score']}", p=s["p_winner"],
                                    actual=f"{r['winner']} {sc}", surprise=round(-math.log(max(1e-9, p_win)), 3)))
    n = g["n"] or 1
    report[st] = dict(graded=g["n"], winner_acc=g["correct"] / n if g["n"] else None,
                      exact_acc=g["exact"] / n if g["n"] else None, brier=g["brier"] / n if g["n"] else None,
                      logloss=g["ll"] / n if g["n"] else None, invalid_post_start=g["invalid"],
                      calibration={k: dict(n=v[0], hit=v[1] / v[0], stated=v[2] / v[0]) for k, v in g["tiers"].items()},
                      worst_misses=sorted(g["misses"], key=lambda m: -m["surprise"])[:3])

# Swiss records
sw = json.load(open("data/dash/swiss.json"))
actual = {r["team"]: r["record"] for r in results if r.get("kind") == "swiss_record"}
if actual:
    for st in {x["set"] for x in sw}:
        rows = [x for x in sw if x["set"] == st and x["team"] in actual]
        report.setdefault(st, {})["swiss"] = dict(
            exact_record=sum(x["predicted_record"] == actual[x["team"]] for x in rows),
            qualifier_hits=sum(x["qualifies"] == (actual[x["team"]] in ("3-0", "3-1", "3-2")) for x in rows), teams=len(rows))

# Pick'Ems (Play-In; third-party scoring 5 per series, 10 final)
pk = json.load(open("data/dash/pickems.json"))
pts = poss = 0
for p in pk:
    r = next((x for x in results if x.get("id") == p["slot_id"] and x.get("winner")), None)
    if r and p["points"]:
        poss += p["points"]; pts += p["points"] if r["winner"] == p["pick"] else 0
report["pickems_playin"] = dict(earned=pts, possible_so_far=poss, stage_max=35)
report["graded_at_nz"] = dt.datetime.now(NZ).strftime("%d/%m/%Y %H:%M NZDT")
json.dump(report, open("data/grading.json", "w"), indent=1, default=float)
print(json.dumps(report, indent=1, default=float))
