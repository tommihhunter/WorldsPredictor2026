#!/usr/bin/env python3
"""
v5 walk-forward test of the candidates in docs/superpowers/specs/2026-10-16-model-v5-design.md.

Sets (A and B as in model/backtest_v4.py):
  A  international events, refit before each event's first day
  B  playoffs + internationals from 01/04/2026, refit at the start of each month
  P  Bo3/Bo5 series between two Worlds teams from 01/03/2026, monthly refits (pool depth)
  S  games between two Worlds teams from 01/03/2026 with known sides, monthly refits (side term)
Metric: mean series-winner log loss (S: game log loss). A candidate is adopted when its best grid point
beats v4 on its main set (A, P or S) with paired-bootstrap P(improvement) >= 0.80 and, for the weight
candidates, set B log loss rises by no more than 0.002. Choosing the best grid point makes P(improvement)
optimistic; the report says so.
Run: python -X utf8 model/backtest_v5.py  -> data/backtest_v5.json
"""
import json, math, os, sys, random, datetime as dt
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ratings_v4 as R, golgg_games as GG, side as SD, pools as PL  # noqa: E402

P_ADOPT, B_SLACK, N_BOOT = 0.80, 0.002, 10000
GRIDS = {
    "w_intl": [dict(w_intl=x) for x in (1.5, 2.0, 3.0)],
    "patch": [dict(patch_n=n, patch_mult=m) for n in (1, 2, 3) for m in (1.5, 2.0)],
}
POOL_BETAS = (0.02, 0.05, 0.1)
SIDE_KS = (20, 50, 100)
ENV = {"w_intl": "W_INTL", "patch_n": "PATCH_N", "patch_mult": "PATCH_MULT"}
START_SP = dt.date(2026, 3, 1)
_fits = {}


def mean(x):
    return sum(x) / len(x) if x else float("nan")


def fit_at(rows, cut, kw):
    key = (cut, tuple(sorted(kw.items())))
    if key not in _fits:
        _fits[key] = R.fit([r for r in rows if r["date"] < cut], as_of=cut, **kw)
    return _fits[key]


def d_pair(f, a, b):
    """v4 prediction logit for a vs b from fit f (temperature + uncertainty shrink, no adjustments); None if unseen."""
    if a not in f["ti"] or b not in f["ti"]:
        return None
    ia, ib = f["ti"][a], f["ti"][b]
    v = f["cov"][ia, ia] + f["cov"][ib, ib] - 2 * f["cov"][ia, ib]
    return (f["s"][ia] - f["s"][ib]) * R.TAU / math.sqrt(1 + math.pi * v * R.TAU ** 2 / 8)


def series_ll(d, r):
    sc = R.series_probs_mixed(d, r["bo"]); need = r["bo"] // 2 + 1
    pa = sum(x for k, x in sc.items() if int(k.split("-")[0]) == need)
    return -math.log(max(pa if r["sa"] > r["sb"] else 1 - pa, 1e-9))


def boot(base, cand, n=N_BOOT, seed=1):
    """Paired bootstrap: share of resamples in which cand's mean log loss is below base's."""
    rng = random.Random(seed); m = len(base)
    diff = [c - b for b, c in zip(base, cand)]
    return sum(1 for _ in range(n) if sum(diff[rng.randrange(m)] for _ in range(m)) < 0) / n


def judge(base, cand, b_base=None, b_cand=None):
    res = dict(n=len(base), ll_v4=round(mean(base), 4), ll=round(mean(cand), 4), p_improve=round(boot(base, cand), 3))
    ok = res["p_improve"] >= P_ADOPT and mean(cand) < mean(base)
    if b_base is not None:
        res.update(b_ll_v4=round(mean(b_base), 4), b_ll=round(mean(b_cand), 4))
        ok = ok and mean(b_cand) <= mean(b_base) + B_SLACK
    res["adopt"] = bool(ok)
    return res


def cuts_A(rows):
    ev = defaultdict(list)
    for r in rows:
        if r["intl"]:
            ev[r["event"]].append(r)
    return [(min(x["date"] for x in rs), rs) for rs in ev.values()]


def monthly(rows, start, keep):
    months = sorted({(r["date"].year, r["date"].month) for r in rows if r["date"] >= start})
    return [(dt.date(y, m, 1), [r for r in rows if (r["date"].year, r["date"].month) == (y, m) and keep(r)]) for y, m in months]


def lls(rows, cuts, kw, extra=None):
    """Per-series log losses over the cuts. extra(r, cut) -> logit shift added to the prediction (pool term)."""
    out = []
    for cut, tests in cuts:
        if sum(1 for r in rows if r["date"] < cut) < 50:
            continue
        f = fit_at(rows, cut, kw)
        for r in tests:
            d = d_pair(f, r["a"], r["b"])
            if d is not None:
                out.append(series_ll(d + (extra(r, cut) if extra else 0.0), r))
    return out


def pool_extra(games, beta):
    cache = {}

    def extra(r, cut):
        if cut not in cache:
            cache[cut] = PL.depths([g for g in games if g["date"] < cut])
        dp = cache[cut]
        if r["bo"] < 3 or r["a"] not in dp or r["b"] not in dp:
            return 0.0
        return beta * (dp[r["a"]] - dp[r["b"]])
    return extra


def side_lls(rows, games, k):
    """(base, cand) game log losses on set S for side shrinkage k."""
    worlds = GG.worlds_teams(); est = {}; base, cand = [], []
    for g in games:
        if g["opp"] not in worlds or g["date"] < START_SP:
            continue
        cut = dt.date(g["date"].year, g["date"].month, 1)
        d = d_pair(fit_at(rows, cut, {}), g["team"], g["opp"])
        if d is None:
            continue
        if cut not in est:
            est[cut] = SD.estimate([x for x in games if x["date"] < cut], k)
        blue, gm = est[cut]
        for out, dd in ((base, d), (cand, d + SD.delta(g["side"], g["team"], g["opp"], blue, gm))):
            p = R.p_game_marginal(dd)
            out.append(-math.log(max(p if g["win"] else 1 - p, 1e-9)))
    return base, cand


def main():
    rows = R.load_series(); games = GG.load_games(); worlds = GG.worlds_teams()
    A = cuts_A(rows)
    B = monthly(rows, dt.date(2026, 4, 1), lambda r: r["kind"] in ("playoffs", "international"))
    Pset = monthly(rows, START_SP, lambda r: r["bo"] >= 3 and r["a"] in worlds and r["b"] in worlds)
    a0, b0 = lls(rows, A, {}), lls(rows, B, {})
    out = dict(generated_nz=dt.datetime.now(dt.timezone(dt.timedelta(hours=13))).strftime("%d/%m/%Y %H:%M NZDT"),
               rule=f"adopt if paired bootstrap ({N_BOOT}) P(improvement) >= {P_ADOPT} on the main set and set B log loss "
                    f"rises by no more than {B_SLACK} (weight candidates); best-of-grid makes P optimistic",
               v4=dict(A=round(mean(a0), 4), nA=len(a0), B=round(mean(b0), 4), nB=len(b0)), candidates={})
    adopted_kw, notes = {}, []
    for fam, grid in GRIDS.items():
        scored = [(kw, lls(rows, A, kw)) for kw in grid]
        for kw, a in scored:
            print(fam, kw, round(mean(a), 4), flush=True)
        kw, a = min(scored, key=lambda x: mean(x[1]))
        res = judge(a0, a, b0, lls(rows, B, kw))
        res.update(best=kw, grid={json.dumps(k): round(mean(x), 4) for k, x in scored})
        out["candidates"][fam] = res
        if res["adopt"]:
            adopted_kw[fam] = kw
    combo = {k: v for kw in adopted_kw.values() for k, v in kw.items()}
    if len(adopted_kw) > 1:
        ac = lls(rows, A, combo)
        best = min(adopted_kw, key=lambda f: out["candidates"][f]["ll"])
        out["combination"] = dict(kw=combo, ll=round(mean(ac), 4), best_single=best)
        if mean(ac) > out["candidates"][best]["ll"]:
            combo = dict(adopted_kw[best])
            notes.append(f"combination lost to {best} alone; shipping {best} only")
    p0 = lls(rows, Pset, combo)
    scored = [(b, lls(rows, Pset, combo, pool_extra(games, b))) for b in POOL_BETAS]
    beta, pc = min(scored, key=lambda x: mean(x[1]))
    out["candidates"]["pool_depth"] = dict(judge(p0, pc), best=dict(pool_beta=beta), grid={str(x): round(mean(y), 4) for x, y in scored},
                                           caveat="Pools rebuilt from games dated before each cut; dates estimated from gol.gg game ids.")
    side_res = {k: side_lls(rows, games, k) for k in SIDE_KS}
    k = min(side_res, key=lambda x: mean(side_res[x][1]))
    out["candidates"]["side"] = dict(judge(*side_res[k]), best=dict(k=k), grid={str(x): round(mean(y[1]), 4) for x, y in side_res.items()},
                                     note="Game-level test. Predictions stay side-neutral: the side of a game is not known before the match.")
    env = {ENV[key]: v for key, v in combo.items()}
    if out["candidates"]["pool_depth"]["adopt"]:
        env["POOL_BETA"] = beta
    if out["candidates"]["side"]["adopt"]:
        notes.append(f"side term passes at k={k}: recorded only, predictions stay side-neutral")
    out["adopted"] = dict(env=env, notes=notes)
    json.dump(out, open(os.path.join(R.ROOT, "data", "backtest_v5.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps(out["adopted"], indent=1))


if __name__ == "__main__":
    main()
