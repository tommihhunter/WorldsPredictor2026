#!/usr/bin/env python3
"""
Worlds 2026 team-strength model, v4: series-level fit with a per-series form shock,
on the full 2026 season (regular season + playoffs + internationals, gol.gg scrape).

Run:  python3 model/ratings_v4.py            (from the worlds2026/ folder)
Out:  data/ratings.json, data/matchups.json

MODEL
-----
  strength(team)  = R[region] + u[team]              R ~ N(0, SIGMA_R^2), u ~ N(0, SIGMA_U^2)
  series i (a vs b, best-of n):  one shared shock e_i ~ N(0, SIGMA^2)
  P(a wins one game | e_i) = sigmoid(s_a - s_b + e_i)
  P(exact score)  = E_e[ C(need-1+k, k) p^need q^k ]    (Gauss-Hermite, 31 nodes)
  Penalised, weighted log-likelihood maximised with L-BFGS (analytic gradient);
  the observed-information Hessian at the optimum gives the posterior covariance.

  Weights per series = recency * kind weight
     recency    = 0.5 ** (days before AS_OF / HALF_LIFE)
     kind       = regular season W_REG, playoffs 1.0, international 1.0, EWC online qualifiers W_QUAL

  Why series-level: a 3-0 is one observation of a dominant day, not three independent
  wins. Fitting games independently inflated rating gaps (v3 needed a 0.75 temperature
  to compensate) and understated uncertainty. Here the shock is part of the fit, so the
  same model generates the predictions.

PREDICTION
  d        = s_a - s_b, shrunk for posterior uncertainty: d / sqrt(1 + pi * Var(d) / 8)
  p_game   = E_e[sigmoid(d + e)]                   (marginal single-game probability)
  series   = exact-score distribution from the same mixture; predicted score = modal score
             for the predicted winner; tiers LOCK >= 75%, LEAN 60-74.99%, COIN FLIP < 60%.
  TAU      = post-hoc temperature on d, 0.9 (walk-forward: 0.8-1.0 best; 1.2 worse).

CHOICES (walk-forward, model/backtest_v4.py and the region-prior test, 15/10/2026)
  W_REG 0.5 (best on both test sets), SIGMA 1.0 (internationals prefer 1.2, domestic
  playoffs 0.9), HALF_LIFE 120 (internationals prefer 60-120, playoffs 240+), TAU 0.9.
  Region prior: 2025 international results (First Stand, MSI, EWC, Worlds 2025; 91 series,
  gol.gg) fitted region-only, centred, times PRIOR_SHRINK 0.7, prior sd SIGMA_R 0.7.
  On the 67 international series of 2026 this takes series log loss from 0.637 (no prior)
  to 0.616; the naive "stronger region wins 70%" rule scores 0.622, a coin flip 0.693.
  Qualitative adjustments (data/adjustments.json) add a capped logit shift (+/-0.405).
"""
import json, math, os, re, sys, datetime as dt
from math import comb
import numpy as np
from scipy.optimize import minimize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

NZ = dt.timezone(dt.timedelta(hours=13))
AS_OF = (dt.datetime.strptime(os.environ["AS_OF"], "%d/%m/%Y").date() if os.environ.get("AS_OF")
         else dt.datetime.now(NZ).date())   # fit date: today (NZDT) unless pinned; AS_OF=15/10/2026 reproduces the baseline fit
HALF_LIFE = float(os.environ.get("HALF_LIFE", 120))
W_REG = float(os.environ.get("W_REG", 0.5))
W_QUAL = float(os.environ.get("W_QUAL", 0.6))
SIGMA_R = float(os.environ.get("SIGMA_R", 0.7))
SIGMA_U = float(os.environ.get("SIGMA_U", 0.8))
SIGMA = float(os.environ.get("SIGMA", 1.0))            # per-series shock sd (fitted; see fit_sigma)
TAU = float(os.environ.get("TAU", 0.9))
PRIOR_SHRINK = float(os.environ.get("PRIOR_SHRINK", 0.7))   # 2025 region strengths x this = prior mean for 2026 region effects
W_INTL = float(os.environ.get("W_INTL", 1.0))          # v5 candidate 2: weight of international series (v4 = 1.0)
PATCH_N = int(os.environ.get("PATCH_N", 0))            # v5 candidate 3: boost series on the last N patches before the cut (0 = off)
PATCH_MULT = float(os.environ.get("PATCH_MULT", 1.0))  # ... by this multiplier
POOL_BETA = float(os.environ.get("POOL_BETA", 0.0))    # v5 candidate 5: logit per unit of pool-depth gap in Bo3/Bo5 (0 = off)
_rp = json.load(open("data/region_prior_2025.json")) if os.path.exists("data/region_prior_2025.json") else {}
_rp_mean = (sum(_rp.values()) / len(_rp)) if _rp else 0.0
R_PRIOR = {g: PRIOR_SHRINK * (v - _rp_mean) for g, v in _rp.items()}   # centred
LOGIT_CAP = math.log(0.6 / 0.4)
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(31)
GH_W = GH_W / GH_W.sum()

WORLDS = ["AL", "BLG", "TES", "IG", "GEN", "HLE", "T1", "DK", "G2", "MKOI", "KC",
          "TLAW", "LYON", "C9", "TSW", "CFO", "MVK", "LOS", "FURIA"]
TEAM_MAP = json.load(open("data/team_map.json"))
REGION = {v["code"]: v["region"] for v in TEAM_MAP.values()}


def pdate(s):
    d, m, y = s.split("/"); return dt.date(int(y), int(m), int(d))


def load_series():
    rows = []
    for r in json.load(open("data/series_2026.json")):
        rows.append(dict(date=pdate(r["date"]), a=r["a"], b=r["b"], sa=r["sa"], sb=r["sb"], bo=r["bo"],
                         kind=r["kind"], event=r["tournament"], intl=r["intl"], patch=r.get("patch") or None))
    # Americas Cup 2026 (LCS v CBLOL) is not on gol.gg: take it from the hand-compiled file
    alias = {"DPLUS": "DK", "MIBR.LOS": "LOS", "Sentinels": "SEN"}
    for h in json.load(open("data/results_2026.json")):
        if h["event"] == "Americas Cup 2026":
            a, b = alias.get(h["team_a"], h["team_a"]), alias.get(h["team_b"], h["team_b"])
            if a in REGION and b in REGION:
                rows.append(dict(date=pdate(h["date"]), a=a, b=b, sa=int(h["score_a"]), sb=int(h["score_b"]),
                                 bo=2 * max(int(h["score_a"]), int(h["score_b"])) - 1, kind="international",
                                 event="Americas Cup 2026", intl=True, patch=None))
    return rows


def kind_weight(k):
    return {"regular": W_REG, "qualifier": W_QUAL, "international": W_INTL}.get(k, 1.0)


def recent_patches(rows, n):
    """The n most recent patch labels in rows (gol.gg labels such as '16.20'); empty set when n is 0."""
    if not n:
        return set()
    vs = sorted({r["patch"] for r in rows if r.get("patch")}, key=lambda p: tuple(int(x) for x in re.findall(r"\d+", p)))
    return set(vs[-n:])


# ---------- series likelihood pieces ----------
def _score_terms(bo):
    """(need, k, coef) for the winning side with k losses."""
    need = bo // 2 + 1
    return need, [(k, comb(need - 1 + k, k)) for k in range(need)]


def series_probs_mixed(d, bo, sigma=None):
    """Exact-score distribution for team A given latent logit d and shock sd sigma."""
    sigma = SIGMA if sigma is None else sigma
    need, terms = _score_terms(bo)
    p = 1 / (1 + np.exp(-(d + sigma * GH_X)))
    q = 1 - p
    out = {}
    for k, c in terms:
        out[f"{need}-{k}"] = float(np.sum(GH_W * c * p ** need * q ** k))
        out[f"{k}-{need}"] = float(np.sum(GH_W * c * q ** need * p ** k))
    return out


def p_game_marginal(d, sigma=None):
    sigma = SIGMA if sigma is None else sigma
    return float(np.sum(GH_W / (1 + np.exp(-(d + sigma * GH_X)))))


def fit(rows, half_life=None, sigma=None, w_reg=None, w_qual=None, as_of=None, r_prior=None,
        w_intl=None, patch_n=None, patch_mult=None):
    half_life = HALF_LIFE if half_life is None else half_life
    sigma = SIGMA if sigma is None else sigma
    w_reg = W_REG if w_reg is None else w_reg
    w_qual = W_QUAL if w_qual is None else w_qual
    as_of = AS_OF if as_of is None else as_of
    w_intl = W_INTL if w_intl is None else w_intl
    patch_n = PATCH_N if patch_n is None else patch_n
    patch_mult = PATCH_MULT if patch_mult is None else patch_mult
    recent = recent_patches(rows, patch_n)
    kinds = {"regular": w_reg, "qualifier": w_qual, "international": w_intl}
    teams = sorted({r["a"] for r in rows} | {r["b"] for r in rows})
    regions = sorted({REGION[t] for t in teams})
    ti = {t: i for i, t in enumerate(teams)}; ri = {g: i for i, g in enumerate(regions)}
    nR, nT = len(regions), len(teams); P = nR + nT
    M = np.zeros((nT, P))
    for t in teams:
        M[ti[t], ri[REGION[t]]] = 1.0; M[ti[t], nR + ti[t]] = 1.0
    prec = np.array([1 / SIGMA_R ** 2] * nR + [1 / SIGMA_U ** 2] * nT)
    r_prior = R_PRIOR if r_prior is None else r_prior
    mu = np.array([r_prior.get(g, 0.0) for g in regions] + [0.0] * nT)   # prior means (regions from 2025, teams 0)

    A = np.array([ti[r["a"]] for r in rows]); B = np.array([ti[r["b"]] for r in rows])
    X = M[A] - M[B]                                   # n x P
    W = np.array([0.5 ** (max((as_of - r["date"]).days, 0) / half_life) * kinds.get(r["kind"], 1.0)
                  * (patch_mult if r.get("patch") in recent else 1.0) for r in rows])
    # winner-side representation: n_win games by the winner, n_lose by the loser, sign = +1 if a won
    sign = np.array([1.0 if r["sa"] > r["sb"] else -1.0 for r in rows])
    nwin = np.array([max(r["sa"], r["sb"]) for r in rows], dtype=float)
    nlos = np.array([min(r["sa"], r["sb"]) for r in rows], dtype=float)
    # C(need-1+k,k) is a constant in theta: drop it from the objective

    def nll_grad(theta):
        d = (X @ theta) * sign                        # logit for the winner
        z = d[:, None] + sigma * GH_X[None, :]        # n x K
        p = 1 / (1 + np.exp(-z)); q = 1 - p
        f = np.exp(nwin[:, None] * np.log(p + 1e-300) + nlos[:, None] * np.log(q + 1e-300))   # n x K
        L = f @ GH_W                                  # mixture likelihood per series
        g = (f * (nwin[:, None] * q - nlos[:, None] * p)) @ GH_W / L      # dlogL/dd
        nll = -np.sum(W * np.log(L)) + 0.5 * np.sum(prec * (theta - mu) ** 2)
        grad = -(X.T @ (W * g * sign)) + prec * (theta - mu)
        return nll, grad

    res = minimize(nll_grad, mu.copy(), jac=True, method="L-BFGS-B", options=dict(maxiter=2000, ftol=1e-12, gtol=1e-8))
    theta = res.x
    # observed information by central differences of the analytic gradient
    H = np.zeros((P, P)); h = 1e-4
    for j in range(P):
        e = np.zeros(P); e[j] = h
        H[:, j] = (nll_grad(theta + e)[1] - nll_grad(theta - e)[1]) / (2 * h)
    H = 0.5 * (H + H.T)
    cov_theta = np.linalg.inv(H)
    s = M @ theta; cov_s = M @ cov_theta @ M.T
    return dict(teams=teams, ti=ti, s=s, cov=cov_s, cov_theta=cov_theta, ri=ri, regions=regions,
                R={g: float(theta[ri[g]]) for g in regions},
                R_sd={g: float(math.sqrt(cov_theta[ri[g], ri[g]])) for g in regions},
                nll=float(res.fun), converged=bool(res.success), sigma=sigma,
                n_games={t: float(sum(r["sa"] + r["sb"] for r in rows if t in (r["a"], r["b"]))) for t in teams},
                w_games={t: float(sum(W[i] * (r["sa"] + r["sb"]) for i, r in enumerate(rows) if t in (r["a"], r["b"]))) for t in teams})


def fit_sigma(rows, grid=(0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5)):
    """Profile the shock sd by penalised likelihood (the prior terms are the same for every sigma)."""
    out = {}
    for sg in grid:
        f = fit(rows, sigma=sg); out[sg] = f["nll"]
    return out


def series_summary(a, b, d, bo, sigma=None):
    sc = series_probs_mixed(d, bo, sigma)
    need = bo // 2 + 1
    pa = sum(v for k, v in sc.items() if int(k.split("-")[0]) == need)
    winner, pw = (a, pa) if pa >= 0.5 else (b, 1 - pa)
    widx = 0 if winner == a else 1
    key = max((k for k in sc if int(k.split("-")[widx]) == need), key=lambda k: sc[k])
    w_score = "-".join(sorted(key.split("-"), key=int, reverse=True))
    tier = "LOCK" if pw >= 0.75 else ("LEAN" if pw >= 0.60 else "COIN FLIP")
    assert abs(sum(sc.values()) - 1) < 1e-9
    return dict(team_a=a, team_b=b, bo=bo, p_game_a=round(p_game_marginal(d, sigma), 4), p_series_a=round(pa, 4),
                winner=winner, p_winner=round(pw, 4), score=w_score, p_score=round(sc[key], 4),
                tier=tier, exact={k: round(v, 4) for k, v in sc.items()})


class Model:
    def __init__(self, fitres, adjustments, depths=None, pool_beta=0.0):
        self.f = fitres; self.adj = {a["code"]: a for a in adjustments}
        self.depths = depths or {}; self.pool_beta = pool_beta

    def strength(self, t):
        return TAU * float(self.f["s"][self.f["ti"][t]]) + self.adj.get(t, {}).get("delta_logit", 0.0)

    def d_game(self, a, b, bo=1):
        ia, ib = self.f["ti"][a], self.f["ti"][b]; c = self.f["cov"]
        v = (c[ia, ia] + c[ib, ib] - 2 * c[ia, ib]) * TAU ** 2
        d = (self.strength(a) - self.strength(b)) / math.sqrt(1 + math.pi * v / 8)
        if bo >= 3 and self.pool_beta and a in self.depths and b in self.depths:
            d += self.pool_beta * (self.depths[a] - self.depths[b])
        return d

    def p_game(self, a, b):
        return p_game_marginal(self.d_game(a, b), self.f["sigma"])

    def series(self, a, b, bo):
        return series_summary(a, b, self.d_game(a, b, bo), bo, self.f["sigma"])


def load_adjustments():
    path = "data/adjustments.json"
    if not os.path.exists(path):
        return []
    adj = json.load(open(path))
    for a in adj:
        if abs(a["delta_logit"]) > LOGIT_CAP + 1e-9: raise ValueError(f"adjustment for {a['code']} exceeds cap")
        if not a.get("reason") or not a.get("source"): raise ValueError(f"adjustment for {a['code']} needs reason and source")
    return adj


def build(write=True):
    rows = load_series()
    f = fit(rows)
    depths = None
    if POOL_BETA:
        import golgg_games, pools
        depths = pools.depths(golgg_games.load_games())
    m = Model(f, load_adjustments(), depths, POOL_BETA)
    to_elo = lambda s: 1500 + 400 / math.log(10) * s
    mean_s = float(np.mean([m.strength(t) for t in WORLDS]))
    out = []
    for t in WORLDS:
        i = f["ti"][t]; base = TAU * float(f["s"][i]); adjd = m.strength(t)
        out.append(dict(code=t, region=REGION[t], base_logit=round(float(f["s"][i]), 4), adj_logit=round(adjd, 4),
                        sd=round(math.sqrt(f["cov"][i, i]), 4), elo_base=round(to_elo(base)), elo=round(to_elo(adjd)),
                        p_vs_avg=round(p_game_marginal(adjd - mean_s, f["sigma"]), 4),
                        games=int(f["n_games"][t]), weighted_games=round(f["w_games"][t], 1), adjustment=m.adj.get(t)))
    out.sort(key=lambda r: -r["adj_logit"])
    for k, r in enumerate(out):
        r["rank"] = k + 1
        r["tier"] = ("S" if r["p_vs_avg"] >= 0.65 else "A" if r["p_vs_avg"] >= 0.55 else "B" if r["p_vs_avg"] >= 0.40 else "C")
    # region gap uncertainty
    ri = f["ri"]; ct = f["cov_theta"]
    def gap(g1, g2):
        v = ct[ri[g1], ri[g1]] + ct[ri[g2], ri[g2]] - 2 * ct[ri[g1], ri[g2]]
        return dict(gap=round(f["R"][g1] - f["R"][g2], 3), sd=round(math.sqrt(v), 3))
    res = dict(as_of=AS_OF.strftime("%d/%m/%Y"), generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
               model=os.environ.get("MODEL_LABEL", "v4") + ": series-level Bradley-Terry with per-series form shock on the full 2026 season (gol.gg); see model/ratings_v4.py and data/backtest_v5.json",
               params=dict(half_life_days=HALF_LIFE, region_prior_2025_shrink=PRIOR_SHRINK, region_prior_mean=R_PRIOR, w_regular=W_REG, w_qualifier=W_QUAL, sigma_series=f["sigma"], tau=TAU, w_international=W_INTL, patch_boost=dict(last_n=PATCH_N, mult=PATCH_MULT), pool_beta=POOL_BETA,
                           sigma_region=SIGMA_R, sigma_team=SIGMA_U, n_series=len(rows),
                           n_games=int(sum(r["sa"] + r["sb"] for r in rows)), converged=f["converged"]),
               regions={g: dict(rating=round(f["R"][g], 4), sd=round(f["R_sd"][g], 4), elo=round(to_elo(f["R"][g]))) for g in f["regions"]},
               region_gaps={"LCK-LPL": gap("LCK", "LPL"), "LPL-LEC": gap("LPL", "LEC"), "LEC-LCS": gap("LEC", "LCS"), "LCS-CBLOL": gap("LCS", "CBLOL"), "CBLOL-LCP": gap("CBLOL", "LCP")},
               teams=out)
    if write:
        json.dump(res, open("data/ratings.json", "w"), indent=1)
        mat = {a: {b: round(m.p_game(a, b), 4) for b in WORLDS if b != a} for a in WORLDS}
        json.dump(dict(as_of=res["as_of"], p_game=mat), open("data/matchups.json", "w"), indent=1)
    return res, m


if __name__ == "__main__":
    if "--sigma" in sys.argv:
        rows = load_series()
        for sg, nll in fit_sigma(rows).items(): print(f"sigma {sg}: penalised NLL {nll:.2f}")
        sys.exit()
    res, m = build()
    print(f"series={res['params']['n_series']} games={res['params']['n_games']} sigma={res['params']['sigma_series']} converged={res['params']['converged']}")
    print("Regions:", {g: v["elo"] for g, v in sorted(res["regions"].items(), key=lambda x: -x[1]["rating"])}, "| gaps:", res["region_gaps"])
    for r in res["teams"]:
        a = r["adjustment"]["delta_logit"] if r["adjustment"] else 0
        print(f"{r['rank']:>2} {r['tier']} {r['code']:<6}{r['region']:<6} elo {r['elo']:>5} (adj {a:+.2f}) sd {r['sd']:.2f} pVsAvg {r['p_vs_avg']:.2f} games {r['games']} (w {r['weighted_games']})")
