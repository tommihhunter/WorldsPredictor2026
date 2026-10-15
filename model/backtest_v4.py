#!/usr/bin/env python3
"""
Walk-forward validation for v4. Two test sets:
  (A) international series: refit on everything before each event's first day, predict the event.
  (B) all playoff + international series from 01/04 on, refit at the start of each month.
Grid over half-life, regular-season weight, shock sd and temperature.
Metrics: series-winner log loss / Brier / accuracy, exact-score log loss, and the predicted vs
actual Bo5 score mix. Run: python3 model/backtest_v4.py -> data/backtest_v4.json
"""
import json, math, os, sys, itertools, datetime as dt
from collections import defaultdict, Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ratings_v4 as R  # noqa

rows = R.load_series()
HL = [60, 120, 240, 100000]
WREG = [0.25, 0.5, 1.0]
SIG = [0.3, 0.6, 0.9, 1.2]
TAUS = [0.8, 1.0, 1.2]


def predict_set(train_cuts, hl, wreg, sig):
    """train_cuts: list of (cut_date, [test rows]). Returns list of (d_raw, var, row)."""
    out = []
    for cut, tests in train_cuts:
        train = [r for r in rows if r["date"] < cut]
        if len(train) < 50:
            continue
        f = R.fit(train, half_life=hl, sigma=sig, w_reg=wreg, as_of=cut)
        for r in tests:
            if r["a"] not in f["ti"] or r["b"] not in f["ti"]:
                continue
            ia, ib = f["ti"][r["a"]], f["ti"][r["b"]]
            v = f["cov"][ia, ia] + f["cov"][ib, ib] - 2 * f["cov"][ia, ib]
            out.append((f["s"][ia] - f["s"][ib], v, r))
    return out


def score(preds, tau, sig):
    n = 0; lls = llx = br = 0.0; acc = 0; mixa = Counter(); mixp = defaultdict(float); n5 = 0
    for d_raw, v, r in preds:
        d = d_raw * tau / math.sqrt(1 + math.pi * v * tau * tau / 8)
        sc = R.series_probs_mixed(d, r["bo"], sig); need = r["bo"] // 2 + 1
        pa = sum(x for k, x in sc.items() if int(k.split("-")[0]) == need)
        y = r["sa"] > r["sb"]; pw = pa if y else 1 - pa
        lls += -math.log(max(pw, 1e-9)); br += (1 - pw) ** 2; acc += (pa >= 0.5) == y
        llx += -math.log(max(sc[f"{r['sa']}-{r['sb']}"], 1e-9)); n += 1
        if r["bo"] == 5:
            n5 += 1; mixa[f"3-{min(r['sa'], r['sb'])}"] += 1
            for k in range(3): mixp[f"3-{k}"] += sc[f"3-{k}"] + sc[f"{k}-3"]
    return dict(n=n, series_logloss=round(lls / n, 4), brier=round(br / n, 4), acc=round(acc / n, 3), exact_logloss=round(llx / n, 4),
                bo5=n5, mix_actual={k: round(c / n5, 3) for k, c in sorted(mixa.items())}, mix_pred={k: round(c / n5, 3) for k, c in sorted(mixp.items())})


# test set A: international events
ev = defaultdict(list)
for r in rows:
    if r["intl"]: ev[r["event"]].append(r)
cutsA = [(min(x["date"] for x in rs), rs) for rs in ev.values()]
# test set B: playoffs + internationals from April, monthly refits
months = sorted({(r["date"].year, r["date"].month) for r in rows if r["date"] >= dt.date(2026, 4, 1)})
cutsB = [(dt.date(y, m, 1), [r for r in rows if (r["date"].year, r["date"].month) == (y, m) and r["kind"] in ("playoffs", "international")]) for y, m in months]

results = {"A_international": {}, "B_playoffs_and_intl": {}}
for hl, wreg, sig in itertools.product(HL, WREG, SIG):
    pa = predict_set(cutsA, hl, wreg, sig); pb = predict_set(cutsB, hl, wreg, sig)
    for tau in TAUS:
        k = f"hl{hl}_wreg{wreg}_sig{sig}_tau{tau}"
        results["A_international"][k] = score(pa, tau, sig)
        results["B_playoffs_and_intl"][k] = score(pb, tau, sig)
    print("done", hl, wreg, sig, flush=True)
json.dump(results, open(os.path.join(R.ROOT, "data", "backtest_v4.json"), "w"), indent=1)
for part in results:
    print("==", part)
    for k, m in sorted(results[part].items(), key=lambda x: x[1]["series_logloss"])[:8]:
        print(f"{k:<36} n={m['n']} LL={m['series_logloss']} brier={m['brier']} acc={m['acc']} exactLL={m['exact_logloss']} mix={m['mix_pred']} actual={m['mix_actual']}")
