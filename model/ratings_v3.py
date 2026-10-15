#!/usr/bin/env python3
"""
Worlds 2026 team-strength model.

Run:  python3 model/ratings.py            (from the worlds2026/ folder)
Out:  data/ratings.json, data/matchups.json

METHOD (all in this file, no hidden steps)
------------------------------------------
1. Data
   * data/results_2026.json  : every 2026 international series (First Stand, MSI,
     EWC, Americas Cup = "core"; Demacia Cup Global Invitational = "supplementary").
   * data/fragments/*_results.json : domestic playoff/season-final series per region
     (rows flagged international=true are dropped there, because the international
     file is the single source of truth for those).
   * Each series a-b is expanded into `score_a` game wins for A and `score_b` for B.
     Game order inside a series is unknown, so every game is treated as one
     independent Bernoulli trial.

2. Model: weighted, hierarchical Bradley-Terry (logistic) on games
       strength(team) = R[region] + u[team]
       P(A beats B in one game) = sigmoid(strength_A - strength_B)
   Priors (ridge / Gaussian):  R ~ N(0, SIGMA_R^2),  u ~ N(0, SIGMA_U^2).
   - Domestic games identify u (who is better inside a region).
   - International games identify R (how regions compare), plus u for the teams
     that played abroad. This is how the region head-to-head matrix enters the
     rating: it is not a hand-set multiplier, it is learned from the cross-region
     games.
   - Teams with no international games (IG, CFO, MVK, LOS) inherit their region
     rating plus their domestic offset, with more uncertainty.
   Game weight = recency * event weight
       recency = 0.5 ** (days_before_15/10/2026 / HALF_LIFE)
       event weight: core international 1.0, domestic 1.0, online qualifiers 0.8,
                     supplementary (DCGI, mostly non-Worlds rosters) 0.5
   Fitted by Newton-Raphson (exact gradient/Hessian of the penalised weighted
   log-likelihood). The inverse Hessian gives a posterior covariance.

3. Uncertainty-aware game probability
       d = s_A - s_B,  v = Var(s_A - s_B)
       p = sigmoid( d / sqrt(1 + pi*v/8) )        (probit approximation)
   This shrinks probabilities toward 50% when we know little about a team, which is
   what calibration needs.
   Temperature: fitted logits are multiplied by TAU = 0.75 before use. The walk-
   forward backtest (model/backtest.py, 60 international series in 2026) showed
   TAU = 1.0 was overconfident (LOCKs hit 76% at a mean stated 84%; LEANs 57% at
   66%); log loss was best at TAU = 0.6. Earlier 2026 events had thinner training
   data than Worlds will, so we take a partial shrink, 0.75.

4. Qualitative adjustments (data/adjustments.json): each is a logit shift capped at
   +/- logit(0.60) = 0.405, i.e. at most +/-10 percentage points of single-game win
   probability against an evenly matched opponent ("max +/-10% per team").
   Each one carries a written reason and a source.

5. Series maths from p (per-game win prob of A), q = 1-p
     Bo1:  P(A) = p
     Bo3:  P(2-0) = p^2           P(2-1) = 2 p^2 q
           P(0-2) = q^2           P(1-2) = 2 q^2 p
     Bo5:  P(3-0) = p^3           P(3-1) = 3 p^3 q        P(3-2) = 6 p^3 q^2
           P(0-3) = q^3           P(1-3) = 3 q^3 p        P(2-3) = 6 q^3 p^2
   (coefficient = C(n-1+k, k): the winner must take the last game, the k losses
   can fall in any of the earlier games.) These sum to exactly 1.
   Predicted score = most likely exact score for the predicted winner.
   Series form shock (added 15/10/2026, baseline v3): one random logit shock
   e ~ N(0, SIGMA_SERIES^2) per series, shared by all its games, integrated out by
   Gauss-Hermite quadrature (series_probs_mixed). The latent logit is scaled up so the
   single-game win probability is unchanged (the ratings were fitted on games).
   Independent games under-predicted sweeps: 2026 Bo5s ended 3-0 45% of the time vs
   30% expected. SIGMA_SERIES was chosen by out-of-sample exact-score log loss on 138
   Bo3/Bo5 series (monthly walk-forward refits, domestic + international): best at
   0.8-1.0 (Bo5 exact-score log loss 1.667 at 0 -> 1.642 at 0.8; series log loss
   0.590 -> 0.592). 0.8 is used. With it, 3-0 is the most likely score once the
   favourite's single-game chance passes ~53%; closer series stay 3-1. The 48-series
   international-only backtest (model/backtest_series.py) also improves: exact-score
   log loss 1.687 -> ~1.56.
   Tier: LOCK >= 75%, LEAN 60-74.99%, COIN FLIP < 60% (series win probability of
   the predicted winner).
"""
import json, math, glob, os, sys, datetime as dt
from math import comb
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

AS_OF = dt.date(2026, 10, 15)
HALF_LIFE = float(os.environ.get("HALF_LIFE", 120))   # days
SIGMA_R = 1.0
SIGMA_U = 0.8
LOGIT_CAP = math.log(0.6 / 0.4)                          # 0.405
TAU = float(os.environ.get("TAU", 0.75))                 # temperature on fitted logits, from model/backtest.py
SIGMA_SERIES = float(os.environ.get("SIGMA_SERIES", 0.8))  # per-series "form on the day" shock (logit sd), from model/backtest_series.py
_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(31)
_GH_W = _GH_W / _GH_W.sum()

WORLDS = ["AL", "BLG", "TES", "IG", "GEN", "HLE", "T1", "DK", "G2", "MKOI", "KC",
          "TLAW", "LYON", "C9", "TSW", "CFO", "MVK", "LOS", "FURIA"]

ALIASES = {"DPLUS": "DK", "Dplus": "DK", "MIBR.LOS": "LOS", "Sentinels": "SEN",
           "Team Liquid": "TLAW", "TL": "TLAW", "GX": "GIANTX"}

REGION = {
    # Worlds teams
    "AL": "LPL", "BLG": "LPL", "TES": "LPL", "IG": "LPL",
    "GEN": "LCK", "HLE": "LCK", "T1": "LCK", "DK": "LCK",
    "G2": "LEC", "MKOI": "LEC", "KC": "LEC",
    "TLAW": "LCS", "LYON": "LCS", "C9": "LCS",
    "TSW": "LCP", "CFO": "LCP", "MVK": "LCP",
    "LOS": "CBLOL", "FURIA": "CBLOL",
    # others seen in the data
    "JDG": "LPL", "WE": "LPL", "LGD": "LPL", "WBG": "LPL", "EDG": "LPL", "TTG": "LPL",
    "OMG": "LPL", "NIP": "LPL",
    "BNK": "LCK", "KT": "LCK", "BRO": "LCK", "DRX": "LCK", "SOOPers": "LCK", "NS": "LCK",
    "VIT": "LEC", "NAVI": "LEC", "GIANTX": "LEC", "FNC": "LEC", "SK": "LEC", "TH": "LEC",
    "SEN": "LCS", "FLY": "LCS", "SR": "LCS", "DSG": "LCS",
    "GAM": "LCP", "DCG": "LCP", "SHG": "LCP", "DFM": "LCP", "GZ": "LCP", "VKS": "LCP",
    "RED": "CBLOL", "LOUD": "CBLOL", "FLX": "CBLOL", "VKS_BR": "CBLOL",
}


def parse_date(s, fallback):
    if not s or s in ("UNKNOWN", "None"):
        return fallback
    s = str(s).split("-")[0] if len(str(s)) > 10 and "-" in str(s) and "/" in str(s) else str(s)
    # handle '15-16/07/2026' -> '15/07/2026'
    if "-" in s and "/" in s:
        d, rest = s.split("-", 1)
        s = d + "/" + rest.split("/", 1)[1]
    try:
        d, m, y = s.split("/")
        return dt.date(int(y), int(m), int(d))
    except Exception:
        return fallback


EVENT_FALLBACK = {  # approximate midpoints when a row has no date (only affects recency)
    "Americas Cup 2026": dt.date(2026, 3, 6), "MSI 2026": dt.date(2026, 7, 5),
    "EWC 2026": dt.date(2026, 7, 16), "Esports World Cup 2026": dt.date(2026, 7, 16),
}


def code(t):
    t = ALIASES.get(t, t)
    return t


def load_games():
    rows = []
    intl = json.load(open("data/results_2026.json"))
    for r in intl:
        w_ev = 0.5 if r.get("event_group") == "supplementary" else 1.0
        d = parse_date(r.get("date"), EVENT_FALLBACK.get(r["event"], dt.date(2026, 7, 1)))
        rows.append(dict(date=d, a=code(r["team_a"]), b=code(r["team_b"]), sa=int(r["score_a"]),
                         sb=int(r["score_b"]), w_ev=w_ev, intl=True, event=r["event"]))
    seen = set()
    for f in sorted(glob.glob("data/fragments/*_results.json")):
        for r in json.load(open(f)):
            if r.get("international"):
                continue
            ev = r.get("event", "")
            d = parse_date(r.get("date"), EVENT_FALLBACK.get(ev, None))
            if d is None:
                continue
            a, b = code(r["team_a"]), code(r["team_b"])
            k = (d, frozenset([a, b]), ev)
            if k in seen:
                continue
            seen.add(k)
            try:
                sa, sb = int(r["score_a"]), int(r["score_b"])
            except Exception:
                continue
            w_ev = 0.8 if "Qualifier" in ev else 1.0
            rows.append(dict(date=d, a=a, b=b, sa=sa, sb=sb, w_ev=w_ev, intl=False, event=ev))
    return rows


def fit(rows, half_life=HALF_LIFE):
    teams = sorted({r["a"] for r in rows} | {r["b"] for r in rows})
    missing = [t for t in teams if t not in REGION]
    for t in missing:
        REGION[t] = "OTHER"
    regions = sorted({REGION[t] for t in teams})
    ti = {t: i for i, t in enumerate(teams)}
    ri = {g: i for i, g in enumerate(regions)}
    nR, nT = len(regions), len(teams)
    P = nR + nT
    # design: s = M theta, theta = [R..., u...]
    M = np.zeros((nT, P))
    for t in teams:
        M[ti[t], ri[REGION[t]]] = 1.0
        M[ti[t], nR + ti[t]] = 1.0
    prior_prec = np.array([1 / SIGMA_R**2] * nR + [1 / SIGMA_U**2] * nT)

    A, B, WA, WB = [], [], [], []
    for r in rows:
        days = (AS_OF - r["date"]).days
        w = (0.5 ** (max(days, 0) / half_life)) * r["w_ev"]
        A.append(ti[r["a"]]); B.append(ti[r["b"]])
        WA.append(w * r["sa"]); WB.append(w * r["sb"])
    A, B, WA, WB = map(np.array, (A, B, WA, WB))
    X = M[A] - M[B]                       # each row: s_a - s_b in theta space
    n = WA + WB
    theta = np.zeros(P)
    for it in range(100):
        d = X @ theta
        p = 1 / (1 + np.exp(-d))
        grad = X.T @ (WA - n * p) - prior_prec * theta
        H = -(X.T * (n * p * (1 - p))) @ X - np.diag(prior_prec)
        step = np.linalg.solve(H, grad)
        theta -= step
        if np.max(np.abs(step)) < 1e-10:
            break
    cov_theta = np.linalg.inv(-H)
    s = M @ theta
    cov_s = M @ cov_theta @ M.T
    R = {g: float(theta[ri[g]]) for g in regions}
    return dict(teams=teams, ti=ti, s=s, cov=cov_s, R=R, regions=regions,
                R_sd={g: float(math.sqrt(cov_theta[ri[g], ri[g]])) for g in regions},
                n_games={t: float(sum(r["sa"] + r["sb"] for r in rows if t in (r["a"], r["b"]))) for t in teams},
                iters=it + 1)


# ---------- series maths ----------
def series_probs(p, bo):
    """Exact-score distribution for team A with per-game win prob p."""
    q = 1 - p
    need = bo // 2 + 1
    out = {}
    for k in range(need):          # A wins need-k ... A loses k games
        out[f"{need}-{k}"] = comb(need - 1 + k, k) * p**need * q**k
        out[f"{k}-{need}"] = comb(need - 1 + k, k) * q**need * p**k
    return out


def series_probs_mixed(d, bo, sigma=None):
    """Exact-score distribution when the per-game logit d gets one random shock per series:
    d_series = d + e, e ~ N(0, sigma^2), drawn once and shared by every game in the series.
    Games stay independent *given* the shock, so a team that is better on the day tends to
    win cleanly (more 3-0s and 2-0s), as 2026 data shows. Integrated with Gauss-Hermite."""
    sigma = SIGMA_SERIES if sigma is None else sigma
    if sigma <= 0:
        return series_probs(1 / (1 + math.exp(-d)), bo)
    # keep the single-game win probability unchanged (the ratings were fitted on games):
    # E[sigmoid(d_lat + e)] ~= sigmoid(d)  =>  d_lat = d * sqrt(1 + pi * sigma^2 / 8)
    d_lat = d * math.sqrt(1 + math.pi * sigma * sigma / 8)
    out = {}
    for x, w in zip(_GH_X, _GH_W):
        for k, v in series_probs(1 / (1 + math.exp(-(d_lat + sigma * x))), bo).items():
            out[k] = out.get(k, 0.0) + w * v
    return out


def series_summary(a, b, p, bo, d=None, sigma=None):
    sc = series_probs(p, bo) if d is None else series_probs_mixed(d, bo, sigma)
    need = bo // 2 + 1
    pa = sum(v for k, v in sc.items() if int(k.split("-")[0]) == need)
    winner, pw = (a, pa) if pa >= 0.5 else (b, 1 - pa)
    widx = 0 if winner == a else 1
    key = max((k for k in sc if int(k.split("-")[widx]) == need), key=lambda k: sc[k])
    w_score = "-".join(sorted(key.split("-"), key=int, reverse=True))   # winner-loser, e.g. "3-1"
    tier = "LOCK" if pw >= 0.75 else ("LEAN" if pw >= 0.60 else "COIN FLIP")
    assert abs(sum(sc.values()) - 1) < 1e-9
    return dict(team_a=a, team_b=b, bo=bo, p_game_a=round(p, 4), p_series_a=round(pa, 4),
                winner=winner, p_winner=round(pw, 4), score=w_score, p_score=round(sc[key], 4),
                tier=tier, exact={k: round(v, 4) for k, v in sc.items()})


class Model:
    def __init__(self, fitres, adjustments):
        self.f = fitres
        self.adj = {a["code"]: a for a in adjustments}

    def strength(self, t):
        """Effective strength = TAU * fitted logit + qualitative adjustment."""
        i = self.f["ti"][t]
        return TAU * float(self.f["s"][i]) + self.adj.get(t, {}).get("delta_logit", 0.0)

    def d_game(self, a, b, bo=1):  # bo unused in v3
        """Effective per-game logit for A over B (uncertainty-shrunk, before the series shock)."""
        ia, ib = self.f["ti"][a], self.f["ti"][b]
        c = self.f["cov"]
        v = (c[ia, ia] + c[ib, ib] - 2 * c[ia, ib]) * TAU ** 2
        d = self.strength(a) - self.strength(b)
        return d / math.sqrt(1 + math.pi * v / 8)

    def p_game(self, a, b):
        """Per-game win probability at average form (no series shock)."""
        return 1 / (1 + math.exp(-self.d_game(a, b)))

    def series(self, a, b, bo):
        """Series summary including the per-series form shock."""
        return series_summary(a, b, self.p_game(a, b), bo, d=self.d_game(a, b))


def load_adjustments():
    path = "data/adjustments.json"
    if not os.path.exists(path):
        return []
    adj = json.load(open(path))
    for a in adj:
        if abs(a["delta_logit"]) > LOGIT_CAP + 1e-9:
            raise ValueError(f"adjustment for {a['code']} exceeds +/-10% cap")
        if not a.get("reason") or not a.get("source"):
            raise ValueError(f"adjustment for {a['code']} needs reason and source")
    return adj


def build():
    rows = load_games()
    f = fit(rows)
    adj = load_adjustments()
    m = Model(f, adj)
    # sensitivity: ratings under other half-lives
    sens = {}
    for hl in (90, 180):
        g = fit(rows, half_life=hl)
        sens[hl] = {t: float(g["s"][g["ti"][t]]) for t in WORLDS}

    to_elo = lambda s: 1500 + 400 / math.log(10) * s
    # p vs an "average Worlds team" (mean adjusted strength of the 19)
    mean_s = float(np.mean([m.strength(t) for t in WORLDS]))
    out = []
    for t in WORLDS:
        i = f["ti"][t]
        base = float(f["s"][i]) * TAU; adjd = m.strength(t)
        out.append(dict(
            code=t, region=REGION[t], base_logit=round(float(f["s"][i]), 4), base_eff=round(base, 4), adj_logit=round(adjd, 4),
            sd=round(math.sqrt(f["cov"][i, i]), 4),
            elo_base=round(to_elo(base)), elo=round(to_elo(adjd)),
            p_vs_avg=round(1 / (1 + math.exp(-(adjd - mean_s))), 4),
            weighted_games=round(f["n_games"][t], 1),
            adjustment=m.adj.get(t),
            sens_hl90=round(sens[90][t], 3), sens_hl180=round(sens[180][t], 3)))
    out.sort(key=lambda r: -r["adj_logit"])
    for k, r in enumerate(out):
        r["rank"] = k + 1
        # tiers by win probability vs an average Worlds team
        r["tier"] = ("S" if r["p_vs_avg"] >= 0.65 else "A" if r["p_vs_avg"] >= 0.55 else
                     "B" if r["p_vs_avg"] >= 0.40 else "C")
    res = dict(as_of=AS_OF.strftime("%d/%m/%Y"), generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
               method="Hierarchical weighted Bradley-Terry on games; see model/ratings.py docstring",
               params=dict(half_life_days=HALF_LIFE, tau=TAU, sigma_series=SIGMA_SERIES, sigma_region=SIGMA_R, sigma_team=SIGMA_U,
                           n_series=len(rows), n_games=int(sum(r['sa'] + r['sb'] for r in rows)),
                           newton_iters=f["iters"]),
               regions={g: dict(rating=round(f["R"][g], 4), sd=round(f["R_sd"][g], 4),
                                elo=round(to_elo(f["R"][g]))) for g in f["regions"]},
               teams=out)
    json.dump(res, open("data/ratings.json", "w"), indent=1)

    # full pairwise matrix among Worlds teams
    mat = {a: {b: round(m.p_game(a, b), 4) for b in WORLDS if b != a} for a in WORLDS}
    json.dump(dict(as_of=res["as_of"], p_game=mat), open("data/matchups.json", "w"), indent=1)
    return res, m


if __name__ == "__main__":
    res, m = build()
    print(f"series={res['params']['n_series']} games={res['params']['n_games']} iters={res['params']['newton_iters']}")
    print("Regions:", {g: v["elo"] for g, v in sorted(res["regions"].items(), key=lambda x: -x[1]["rating"])})
    for r in res["teams"]:
        a = r["adjustment"]["delta_logit"] if r["adjustment"] else 0
        print(f"{r['rank']:>2} {r['tier']} {r['code']:<6}{r['region']:<6} elo {r['elo']:>5} (base {r['elo_base']}, adj {a:+.2f}) "
              f"sd {r['sd']:.2f}  pVsAvg {r['p_vs_avg']:.2f}  hl90 {r['sens_hl90']:+.2f} hl180 {r['sens_hl180']:+.2f}  games {r['weighted_games']}")
