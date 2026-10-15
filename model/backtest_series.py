#!/usr/bin/env python3
"""
Choose SIGMA_SERIES (per-series form shock) and re-check TAU.

1. In-sample exact-score fit: for every 2026 Bo3/Bo5 series, the likelihood of the
   exact score under the fitted ratings, for a grid of (tau, sigma). Shows how much
   the shock fixes the score mix (actual 3-0/3-1/3-2 vs predicted).
2. Walk-forward (out-of-sample): refit on games before each core international event,
   predict its series; series log loss, Brier and exact-score log loss.
Run: python3 model/backtest_series.py -> data/backtest_series.json
"""
import json, math, os, sys, datetime as dt
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ratings as R  # noqa

rows = R.load_games()
TAUS = (0.6, 0.75, 0.9, 1.0)
SIGMAS = (0.0, 0.7, 1.0, 1.3, 1.6, 2.0)


def score_key(r):
    return f"{r['sa']}-{r['sb']}"


def bo_of(r):
    return 2 * max(r["sa"], r["sb"]) - 1


def eval_preds(items, tau, sigma):
    """items: (d_raw, v, r). Returns metrics."""
    n = 0; ll_s = ll_x = br = 0.0
    mix_act = Counter(); mix_pred = defaultdict(float); n5 = 0
    for d_raw, v, r in items:
        bo = bo_of(r)
        if bo not in (3, 5):
            continue
        d = d_raw * tau / math.sqrt(1 + math.pi * v * tau * tau / 8)
        sc = R.series_probs_mixed(d, bo, sigma)
        need = bo // 2 + 1
        pa = sum(x for k, x in sc.items() if int(k.split("-")[0]) == need)
        y = r["sa"] > r["sb"]
        pw = pa if y else 1 - pa
        ll_s += -math.log(max(1e-9, pw)); br += (1 - pw) ** 2
        ll_x += -math.log(max(1e-9, sc[score_key(r)]))
        n += 1
        if bo == 5:
            n5 += 1
            mix_act[f"3-{min(r['sa'], r['sb'])}"] += 1
            for k in range(3):
                mix_pred[f"3-{k}"] += sc[f"3-{k}"] + sc[f"{k}-3"]
    return dict(n=n, series_logloss=round(ll_s / n, 4), brier=round(br / n, 4), exact_logloss=round(ll_x / n, 4),
                bo5=n5, mix_actual={k: round(v / n5, 3) for k, v in sorted(mix_act.items())} if n5 else {},
                mix_pred={k: round(v / n5, 3) for k, v in sorted(mix_pred.items())} if n5 else {})


# 1. in-sample
f = R.fit(rows)
ins = []
for r in rows:
    ia, ib = f["ti"][r["a"]], f["ti"][r["b"]]
    v = f["cov"][ia, ia] + f["cov"][ib, ib] - 2 * f["cov"][ia, ib]
    ins.append((f["s"][ia] - f["s"][ib], v, r))
res = {"in_sample": {}, "walk_forward": {}}
for t in TAUS:
    for sg in SIGMAS:
        res["in_sample"][f"tau{t}_sig{sg}"] = eval_preds(ins, t, sg)

# 2. walk-forward on core international events
events = defaultdict(list)
for r in rows:
    if r["intl"] and r["w_ev"] == 1.0:
        events[r["event"]].append(r)
wf = []
for ev, rs in events.items():
    start = min(r["date"] for r in rs)
    train = [r for r in rows if r["date"] < start]
    if len(train) < 30:
        continue
    R.AS_OF = start
    g = R.fit(train)
    for r in rs:
        if r["a"] not in g["ti"] or r["b"] not in g["ti"]:
            continue
        ia, ib = g["ti"][r["a"]], g["ti"][r["b"]]
        v = g["cov"][ia, ia] + g["cov"][ib, ib] - 2 * g["cov"][ia, ib]
        wf.append((g["s"][ia] - g["s"][ib], v, r))
R.AS_OF = dt.date(2026, 10, 15)
for t in TAUS:
    for sg in SIGMAS:
        res["walk_forward"][f"tau{t}_sig{sg}"] = eval_preds(wf, t, sg)

json.dump(res, open(os.path.join(os.path.dirname(HERE), "data", "backtest_series.json"), "w"), indent=1)
for part in ("in_sample", "walk_forward"):
    print("==", part)
    for k, m in sorted(res[part].items(), key=lambda x: x[1]["exact_logloss"])[:10]:
        print(k, "n", m["n"], "seriesLL", m["series_logloss"], "brier", m["brier"], "exactLL", m["exact_logloss"], "bo5", m["bo5"], m["mix_actual"], m["mix_pred"])
