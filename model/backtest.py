#!/usr/bin/env python3
"""
Walk-forward backtest of the rating model on 2026 international series.

For every core international series (First Stand, MSI, EWC, Americas Cup), refit
the model on games dated strictly before that event's first day, predict the
series, and score it. Tests temperature scaling of the logit (tau < 1 = less
confident) and the recency half-life. Qualitative adjustments are NOT used here.

Run: python3 model/backtest.py   -> data/backtest.json
"""
import json, math, os, sys, datetime as dt
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ratings as R  # noqa

rows = R.load_games()
events = defaultdict(list)
for r in rows:
    if r["intl"] and r["w_ev"] == 1.0:
        events[r["event"]].append(r)

results = {}
for hl in (60, 120, 240):
    for tau in (0.6, 0.8, 1.0, 1.2):
        preds = []
        for ev, rs in events.items():
            start = min(r["date"] for r in rs)
            train = [r for r in rows if r["date"] < start]
            if len(train) < 30:
                continue
            R.AS_OF = start
            f = R.fit(train, half_life=hl)
            for r in rs:
                a, b = r["a"], r["b"]
                if a not in f["ti"] or b not in f["ti"]:
                    continue
                ia, ib = f["ti"][a], f["ti"][b]
                v = f["cov"][ia, ia] + f["cov"][ib, ib] - 2 * f["cov"][ia, ib]
                d = (f["s"][ia] - f["s"][ib]) * tau
                p = 1 / (1 + math.exp(-d / math.sqrt(1 + math.pi * v * tau * tau / 8)))
                bo = max(1, 2 * max(r["sa"], r["sb"]) - 1)
                sc = R.series_probs(p, bo)
                need = bo // 2 + 1
                pa = sum(x for k, x in sc.items() if int(k.split("-")[0]) == need)
                y = 1 if r["sa"] > r["sb"] else 0
                preds.append((ev, a, b, pa, y))
        n = len(preds)
        brier = sum((p - y) ** 2 for *_, p, y in preds) / n
        ll = -sum(math.log(max(1e-9, p if y else 1 - p)) for *_, p, y in preds) / n
        acc = sum((p >= 0.5) == (y == 1) for *_, p, y in preds) / n
        bins = defaultdict(lambda: [0, 0, 0.0])
        for *_, p, y in preds:
            pw = max(p, 1 - p); yw = y if p >= 0.5 else 1 - y
            tier = "LOCK" if pw >= .75 else "LEAN" if pw >= .6 else "COIN FLIP"
            bins[tier][0] += 1; bins[tier][1] += yw; bins[tier][2] += pw
        results[f"hl{hl}_tau{tau}"] = dict(n=n, brier=round(brier, 4), logloss=round(ll, 4), acc=round(acc, 3),
            tiers={k: dict(n=v[0], hit=round(v[1] / v[0], 3), mean_p=round(v[2] / v[0], 3)) for k, v in bins.items()})
R.AS_OF = dt.date(2026, 10, 15)
json.dump(results, open(os.path.join(os.path.dirname(HERE), "data", "backtest.json"), "w"), indent=1)
for k, v in sorted(results.items(), key=lambda x: x[1]["logloss"]):
    print(k, v["n"], "brier", v["brier"], "ll", v["logloss"], "acc", v["acc"], v["tiers"])
