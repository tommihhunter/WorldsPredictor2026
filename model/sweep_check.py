#!/usr/bin/env python3
"""Is 3-0 really the most likely Bo5 score? Walk-forward check of the exact-score model on 2026 Bo5s.
Fit with the baseline settings (sigma 1.0 inside the fit), then score Bo5 series with several prediction sigmas.
Run: python3 model/sweep_check.py"""
import math, sys, os, json, datetime as dt
from collections import defaultdict, Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ratings_v4 as R
rows = R.load_series()
TAU = R.TAU

def walk():
    ev = defaultdict(list)
    for r in rows:
        if r["intl"]: ev[r["event"]].append(r)
    cuts = [(min(x["date"] for x in rs), rs) for rs in ev.values()]
    months = sorted({(r["date"].year, r["date"].month) for r in rows if r["date"] >= dt.date(2026, 3, 1)})
    cuts += [(dt.date(y, m, 1), [r for r in rows if (r["date"].year, r["date"].month) == (y, m) and r["kind"] in ("playoffs", "qualifier") and r["bo"] == 5]) for y, m in months]
    out = []
    for cut, tests in cuts:
        tests = [r for r in tests if r["bo"] == 5]
        if not tests: continue
        train = [r for r in rows if r["date"] < cut]
        f = R.fit(train, as_of=cut, r_prior=R.R_PRIOR)
        for r in tests:
            if r["a"] not in f["ti"] or r["b"] not in f["ti"]: continue
            ia, ib = f["ti"][r["a"]], f["ti"][r["b"]]
            v = f["cov"][ia, ia] + f["cov"][ib, ib] - 2 * f["cov"][ia, ib]
            d = (f["s"][ia] - f["s"][ib]) * TAU / math.sqrt(1 + math.pi * v * TAU * TAU / 8)
            out.append((d, r))
    return out

preds = walk()
print("Bo5 series scored walk-forward:", len(preds))
print("\nActual Bo5 mix overall:", Counter(f"3-{min(r['sa'], r['sb'])}" for _, r in preds))

# by favourite band: what did the favourite's wins look like?
bands = [(0.5, 0.55), (0.55, 0.6), (0.6, 0.65), (0.65, 0.72), (0.72, 1.0)]
print("\nFavourite's single-game chance (sigma 1.0 marginal) vs what actually happened")
print(f"{'band':<12}{'n':>4}{'fav won':>9}{'  of fav wins: 3-0':>19}{'3-1':>6}{'3-2':>6}{'  model P(3-0|win)':>19}{'P(3-1|win)':>12}{'P(3-2|win)':>12}")
for lo, hi in bands:
    sel = []
    for d, r in preds:
        pg = R.p_game_marginal(abs(d), 1.0)
        if lo <= pg < hi: sel.append((d, r, pg))
    if not sel: continue
    favwin = [(d, r) for d, r, _ in sel if (r["sa"] > r["sb"]) == (d >= 0)]
    c = Counter(f"3-{min(r['sa'], r['sb'])}" for _, r in favwin)
    mp = np.zeros(3)
    for d, r, _ in sel:
        sc = R.series_probs_mixed(abs(d), 5, 1.0); pw = sum(sc[f"3-{k}"] for k in range(3))
        mp += np.array([sc[f"3-{k}"] / pw for k in range(3)])
    mp /= len(sel)
    nfw = max(len(favwin), 1)
    print(f"{lo:.2f}-{hi:.2f}  {len(sel):>4}{len(favwin)/len(sel):>9.0%}{c['3-0']/nfw:>19.0%}{c['3-1']/nfw:>6.0%}{c['3-2']/nfw:>6.0%}{mp[0]:>19.0%}{mp[1]:>12.0%}{mp[2]:>12.0%}")

# scoring by prediction sigma
print("\nPrediction sigma: exact-score log loss, modal-score hit rate, calibration of P(3-0)")
print(f"{'sigma':<7}{'exactLL':>9}{'modal hit':>11}{'pred sweeps':>13}{'actual':>8}{'pred 3-1':>10}{'actual':>8}{'pred 3-2':>10}{'actual':>8}")
act = Counter(f"3-{min(r['sa'], r['sb'])}" for _, r in preds)
for sig in (0.0, 0.3, 0.5, 0.7, 0.85, 1.0, 1.2):
    ll = 0; hit = 0; ps = np.zeros(3)
    for d, r in preds:
        sc = R.series_probs_mixed(d, 5, sig) if sig > 0 else R.series_probs_mixed(d, 5, 1e-6)
        ll += -math.log(max(sc[f"{r['sa']}-{r['sb']}"], 1e-9))
        hit += max(sc, key=sc.get) == f"{r['sa']}-{r['sb']}"
        for k in range(3): ps[k] += sc[f"3-{k}"] + sc[f"{k}-3"]
    n = len(preds)
    print(f"{sig:<7}{ll/n:>9.4f}{hit/n:>11.1%}{ps[0]:>13.1f}{act['3-0']:>8}{ps[1]:>10.1f}{act['3-1']:>8}{ps[2]:>10.1f}{act['3-2']:>8}")
json.dump(dict(n=len(preds), rows=[dict(d=round(d, 4), a=r["a"], b=r["b"], sa=r["sa"], sb=r["sb"], date=r["date"].isoformat(), event=r.get("event") or r.get("tournament")) for d, r in preds]),
          open(os.path.join(R.ROOT, "data", "sweep_check.json"), "w"), indent=1)
