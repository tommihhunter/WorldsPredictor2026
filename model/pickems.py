#!/usr/bin/env python3
"""
Pick'Ems expected-value sheet.

Official per-pick scoring was NOT verifiable on 15/10/2026 (only stage totals:
Play-In 35, Swiss 125, Knockouts 160). So EV is expressed as probability of a pick
scoring, under the formats reported by third parties:
  Play-In: pick the winner of each of the 6 bracket series (lolpickem: 5 pts each,
           10 for the final).  EV(pick X in slot S) = P(X wins slot S).
  Swiss:   pick 2 teams to go 3-0, 2 teams to go 0-3, and the other advancers
           (format to be confirmed in client on 18/10). EV(3-0 pick) = P(3-0) etc.
Run: python3 model/pickems.py [--stage playin|swiss] -> data/pickems_<stage>.json
"""
import json, os, sys, random, argparse
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ratings as R, simulate as S  # noqa


def playin_slots(st, n=400000, seed=7):
    rng = random.Random(seed)
    c = defaultdict(Counter)
    for _ in range(n):
        a, b = ("KC", "C9"), ("FURIA", "MVK")
        w1 = st.play(*a, 5, rng); l1 = a[1] if w1 == a[0] else a[0]
        w2 = st.play(*b, 5, rng); l2 = b[1] if w2 == b[0] else b[0]
        wm = st.play(w1, w2, 5, rng); lm = w2 if wm == w1 else w1
        em = st.play(l1, l2, 5, rng)
        lf = st.play(lm, em, 5, rng)
        gf = st.play(wm, lf, 5, rng)
        for k, v in (("R1: KC vs C9", w1), ("R1: FURIA vs MVK", w2), ("Winners' match", wm),
                     ("Elimination match", em), ("Lower final", lf), ("Final (Play-In winner)", gf)):
            c[k][v] += 1
    return {k: {t: round(x / n, 4) for t, x in v.most_common()} for k, v in c.items()}


def main():
    os.chdir(os.path.dirname(HERE))
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", default="playin")
    ap.add_argument("--sim", default=None, help="simulation file; default data/sim_<stage>.json if it exists, else data/sim_baseline.json")
    a = ap.parse_args()
    res, m = R.build()
    st = S.SeriesTable(m)
    sim_path = a.sim or (f"data/sim_{a.stage}.json" if os.path.exists(f"data/sim_{a.stage}.json") else "data/sim_baseline.json")
    sim = json.load(open(sim_path))
    print("simulation:", sim_path, "| known:", sim.get("known_results"), "| r1:", sim.get("r1_fixed"))
    out = dict(stage=a.stage, as_of=res["as_of"], simulation=sim_path,
               rules_verified=dict(stage_points={"Play-In": 35, "Swiss": 125, "Knockouts": 160},
                                   source="https://lolesports.com/en-US/pickems/115660540725177488 (accessed 15/10/2026)",
                                   per_pick_scoring="UNKNOWN officially; third-party: Play-In 5 per series, 10 for the final (https://lolpickem.com/worlds-pickems/)",
                                   duplicates_rule="UNKNOWN for 2026 (no source mentions 0-3 picks or a no-duplicate rule)"))
    slots = playin_slots(st)
    picks = []
    pts = {"Final (Play-In winner)": 10}
    for k, d in slots.items():
        best = max(d, key=d.get)
        picks.append(dict(slot=k, pick=best, p_correct=d[best], alternatives=d,
                          ev_points=round(d[best] * pts.get(k, 5), 2)))
    out["playin"] = dict(picks=picks, expected_points=round(sum(p["ev_points"] for p in picks), 2),
                         max_points=35,
                         note="Max-EV pick in each slot = team with highest probability of winning that slot. "
                              "These are mutually consistent here (no slot's best pick contradicts another).")
    T = sim["teams"]
    piw = sim.get("playin_winner_fixed") or "KC"
    swiss_teams = [t for t in T if t not in ("KC", "C9", "FURIA", "MVK")] + [piw]
    def p(t, rs): return round(sum(T[t]["swiss"][r] for r in rs), 4)
    rank = lambda f: sorted(((t, f(t)) for t in swiss_teams), key=lambda x: -x[1])
    p30 = rank(lambda t: T[t]["swiss"]["3-0"]); p03 = rank(lambda t: T[t]["swiss"]["0-3"])
    padv = rank(lambda t: T[t]["p_advance"]); p3132 = rank(lambda t: p(t, ["3-1", "3-2"]))
    pick30 = [t for t, _ in p30[:2]]; pick03 = [t for t, _ in p03[:2]]
    others = [t for t, _ in p3132 if t not in pick30 + pick03][:6]
    out["swiss_preliminary"] = dict(
        warning=("Swiss picks from the published draw; lock 24/10/2026 06:00 NZDT. Play-In winner " + piw + ".") if sim.get("r1_fixed") else
                "PRELIMINARY: Swiss picks open 18/10 and the Round 1 draw is published that day. Re-run before the 24/10 06:00 NZDT lock. " + piw + " used as the Play-In winner placeholder (model favourite).",
        rank_3_0=p30[:6], rank_0_3=p03[:6], rank_advance=padv[:10], rank_3_1_or_3_2=p3132[:10],
        picks={"3-0": pick30, "0-3": pick03, "advance (3-1/3-2), best 6": others},
        ev_reasoning=["3-0 picks go to the highest P(3-0), not simply the strongest teams: T1 (Tier 3) has P(3-0) " +
                      str(T["T1"]["swiss"]["3-0"]) + " vs HLE " + str(T["HLE"]["swiss"]["3-0"]) + " and BLG " + str(T["BLG"]["swiss"]["3-0"]) + ".",
                      "0-3 picks go to the highest P(0-3): CFO and TSW face Tier 1/Tier 2 opponents in round 1 and are the lowest-rated direct entrants.",
                      "Advance picks use P(3-1)+P(3-2) for teams not already used in 3-0, in case the client scores those slots separately; if any advance counts, use P(advance)."])
    json.dump(out, open(f"data/pickems_{a.stage}.json", "w"), indent=1)
    print(json.dumps(out["playin"], indent=1)[:1500]); print(out["swiss_preliminary"]["picks"])


if __name__ == "__main__":
    main()
