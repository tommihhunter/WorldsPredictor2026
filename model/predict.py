#!/usr/bin/env python3
"""
Build a prediction record (baseline or staged) from the model + simulation.

Run:  python3 model/predict.py --stage baseline   -> data/predictions_baseline.json (refuses to overwrite)
      python3 model/predict.py --stage playin     -> data/predictions_playin.json
      python3 model/predict.py --stage swiss --results data/results_live.json --r1 "GEN-CFO,AL-DK,..."
      python3 model/predict.py --stage knockouts --results data/results_live.json
Each stage checks the clock against ITS OWN first match (Play-In 15/10 11:00 PDT, Swiss 23/10 10:00 PDT, knockouts 03/11 14:00 PST).
With --results, series already decided are taken as fact (Play-In bracket, Play-In winner, Swiss draw and results, QF draw) and
only the undecided series are predicted.
Narrative fields (key matchup, draft angle, form/context, what flips it) are read
from data/narratives_<stage>.json, keyed by series id. Numbers come only from the model.
"""
import json, os, sys, argparse, datetime as dt, hashlib, itertools
import numpy as np
from scipy.optimize import linear_sum_assignment
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ratings as R          # noqa
import simulate as S         # noqa

NZ = dt.timezone(dt.timedelta(hours=13))
PDT = dt.timezone(dt.timedelta(hours=-7))
CT = dt.timezone(dt.timedelta(hours=-5))
EST = dt.timezone(dt.timedelta(hours=-5))
CST = dt.timezone(dt.timedelta(hours=-6))


def t(dt_local, venue_tz, venue_label):
    return dict(venue=dt_local.strftime("%d/%m/%Y %H:%M ") + venue_label,
                nz=dt_local.astimezone(NZ).strftime("%d/%m/%Y %H:%M NZDT"),
                start_utc=dt_local.astimezone(dt.timezone.utc).isoformat())


import re
def dossier_sources(team, k=6):
    """First k source links from the team's dossier (research/teams/<TEAM>.md)."""
    try:
        txt = open(f"research/teams/{team}.md").read()
    except FileNotFoundError:
        return []
    sec = txt.split("## Sources", 1)[-1]
    urls = re.findall(r"https?://[^\s)\]>,;]+", sec)
    seen = []
    for u in urls:
        if u not in seen:
            seen.append(u)
    return [dict(url=u, accessed="15/10/2026") for u in seen[:k]]


def series(m, sid, stage, a, b, bo, when, narr, note=None):
    s = m.series(a, b, bo)
    s.update(id=sid, stage=stage, time=when, note=note)
    # narrative by pairing first (so a changed bracket never shows another matchup's text), then by series id
    s.update(narr.get('|'.join(sorted([a, b]))) or ({} if set(narr.get(sid, {}).get('_teams', [a, b])) != {a, b} else narr.get(sid, {})))
    s["sources"] = dict(dossiers=[f"research/teams/{a}.md", f"research/teams/{b}.md"],
                        links=dossier_sources(a) + dossier_sources(b),
                        results="data/results_2026.json, data/fragments/*_results.json")
    return s


def assign_records(cond):
    slots = ["3-0"] * 2 + ["3-1"] * 3 + ["3-2"] * 3 + ["2-3"] * 3 + ["1-3"] * 3 + ["0-3"] * 2
    teams = list(cond)
    cost = np.array([[-np.log(max(cond[tm][r], 1e-6)) for r in slots] for tm in teams])
    ri, ci = linear_sum_assignment(cost)
    return {teams[i]: slots[j] for i, j in zip(ri, ci)}


FIRST_MATCH = {   # the first series of the stage being predicted: predictions after it are INVALID - post-start
    "baseline": dt.datetime(2026, 10, 15, 11, 0, tzinfo=PDT),
    "playin": dt.datetime(2026, 10, 15, 11, 0, tzinfo=PDT),
    "swiss": dt.datetime(2026, 10, 23, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=-5))),      # 12:00 CDT Allen TX = 10:00 PDT = 24/10 06:00 NZDT
    "knockouts": dt.datetime(2026, 11, 3, 16, 0, tzinfo=CST),                                     # 16:00 CST = 14:00 PST = 04/11 11:00 NZDT
}
VENUE = {"baseline": (PDT, "PDT"), "playin": (PDT, "PDT"), "swiss": (dt.timezone(dt.timedelta(hours=-5)), "CDT"), "knockouts": (CST, "CST")}


def actual_series(row, stage_label):
    """A finished series from results_live.json, in the same shape as a prediction row but marked ACTUAL."""
    return dict(id=row["id"], stage=stage_label, team_a=row["team_a"], team_b=row["team_b"], bo=row.get("bo", 5),
                winner=row["winner"], score=f"{max(row['score_a'], row['score_b'])}-{min(row['score_a'], row['score_b'])}",
                actual=True, p_winner=None, tier="ACTUAL", time=dict(nz=row.get("start_nz"), venue=row.get("date")),
                note="Played before this run; shown as the actual result, not a prediction.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="baseline")
    ap.add_argument("--sims", type=int, default=100000)
    ap.add_argument("--results", default=None, help="data/results_live.json: finished series are taken as fact")
    ap.add_argument("--r1", default=None, help='Swiss round-1 draw, "GEN-CFO,AL-DK,...,G2-PIW" (PIW = Play-In winner)')
    ap.add_argument("--playin-winner", default=None)
    a = ap.parse_args()
    out_path = f"data/predictions_{a.stage}.json"
    os.chdir(os.path.dirname(HERE))
    if a.stage == "baseline" and os.path.exists(out_path):
        sys.exit("Baseline already frozen; refusing to overwrite.")
    narr = json.load(open(f"data/narratives_{a.stage}.json")) if os.path.exists(f"data/narratives_{a.stage}.json") else {}
    known = S.load_known(a.results) if a.results else {}
    rows_by_id = {r["id"]: r for r in (json.load(open(a.results)) if a.results and os.path.exists(a.results) else []) if r.get("kind", "series") == "series"}
    done = {k: r for k, r in rows_by_id.items() if r.get("winner")}
    r1_fixed = S.parse_r1(a.r1) if a.r1 else None

    now = dt.datetime.now(dt.timezone.utc)
    first_match = FIRST_MATCH[a.stage]
    assert now < first_match, f"{a.stage} has started ({first_match.isoformat()}): predictions would be INVALID - post-start"
    sim, res, m, st = S.run(a.sims, 2026, a.playin_winner, r1_fixed, known)

    # ---- Play-In predicted path (favourite at each step) ----
    d1 = dt.datetime(2026, 10, 15, 11, 0, tzinfo=PDT); d1b = dt.datetime(2026, 10, 15, 16, 0, tzinfo=PDT)
    d2 = dt.datetime(2026, 10, 16, 11, 0, tzinfo=PDT); d2b = dt.datetime(2026, 10, 16, 16, 0, tzinfo=PDT)
    d3 = dt.datetime(2026, 10, 17, 11, 0, tzinfo=PDT); d4 = dt.datetime(2026, 10, 18, 11, 0, tzinfo=PDT)
    note_order = "Day 1 order disputed between outlets (KC-C9 or FURIA-MVK first); both start after the 11:00 PDT Pick'Ems lock."
    pi = []
    def pi_series(sid, label, x, y, when, note=None):
        """Actual result if this series is already in --results, else a prediction."""
        if sid in done:
            return actual_series(done[sid], label)
        return series(m, sid, label, x, y, 5, when, narr, note)
    r1a = pi_series("PI-R1-A", "Play-In R1", "KC", "C9", t(d1, PDT, "PDT"), note_order)
    r1b = pi_series("PI-R1-B", "Play-In R1", "FURIA", "MVK", t(d1b, PDT, "PDT"), note_order)
    pi += [r1a, r1b]
    w1, w2 = r1a["winner"], r1b["winner"]
    l1 = "C9" if w1 == "KC" else "KC"; l2 = "MVK" if w2 == "FURIA" else "FURIA"
    pairing_note = None if "PI-R1-A" in done and "PI-R1-B" in done else "Pairing depends on R1 results; time slot order on 16/10 not confirmed."
    wm = pi_series("PI-WM", "Play-In winners' match" + ("" if pairing_note is None else " (predicted pairing)"), w1, w2, t(d2, PDT, "PDT"), pairing_note)
    em = pi_series("PI-EM", "Play-In elimination match" + ("" if pairing_note is None else " (predicted pairing)"), l1, l2, t(d2b, PDT, "PDT"), pairing_note)
    pi += [wm, em]
    lm = w2 if wm["winner"] == w1 else w1
    lf = pi_series("PI-LF", "Play-In lower final" + ("" if "PI-WM" in done and "PI-EM" in done else " (predicted pairing)"), lm, em["winner"], t(d3, PDT, "PDT"))
    gf = pi_series("PI-GF", "Play-In final" + ("" if "PI-LF" in done else " (predicted pairing)"), wm["winner"], lf["winner"], t(d4, PDT, "PDT"),
                   None if "PI-LF" in done else "Bracket reset not mentioned in any source (UNKNOWN); assumed none.")
    pi += [lf, gf]
    pi_matrix = {f"{x}-{y}": m.series(x, y, 5)
                 for x, y in itertools.combinations(S.PLAYIN, 2)}
    piw = known.get("piw") or a.playin_winner or gf["winner"]

    # ---- Swiss: most likely consistent set of records (conditional on predicted Play-In winner) ----
    cond = sim["swiss_conditional"].get(piw) or next(iter(sim["swiss_conditional"].values()))
    recs = assign_records(cond)
    swiss_series = []
    r1_pairs = r1_fixed or known.get("swiss_pairs", {}).get(1)
    if r1_pairs:
        vz, vlabel = VENUE["swiss"]
        for i, (x, y) in enumerate(r1_pairs):
            x = piw if x == "PIW" else x; y = piw if y == "PIW" else y
            sid = f"SW-R1-{x}-{y}"
            hit = done.get(sid) or next((r for r in done.values() if r.get("phase") == "Swiss" and str(r["id"]).startswith("SW-R1-") and {r["team_a"], r["team_b"]} == {x, y}), None)
            if hit:
                swiss_series.append(actual_series(hit, "Swiss round 1")); continue
            swiss_series.append(series(m, sid, "Swiss round 1", x, y, 1, t(dt.datetime(2026, 10, 23, 12, 0, tzinfo=vz), vz, vlabel), narr,
                                       "Start time is the day's first slot; per-match order not published."))
        for rnd in sorted(k for k in known.get("swiss_pairs", {}) if k > 1):
            for x, y in known["swiss_pairs"][rnd]:
                sid = f"SW-R{rnd}-{x}-{y}"
                if sid in done:
                    swiss_series.append(actual_series(done[sid], f"Swiss round {rnd}")); continue
                bo = done.get(sid, {}).get("bo") or rows_by_id.get(sid, {}).get("bo") or 1
                swiss_series.append(series(m, sid, f"Swiss round {rnd}", x, y, bo, dict(nz=None, venue=None), narr))
    swiss = sorted(({"team": tm, "predicted_record": r, "p_record": cond[tm][r],
                     "p_advance": round(sum(cond[tm][x] for x in ("3-0", "3-1", "3-2")), 4),
                     "dist": cond[tm]} for tm, r in recs.items()),
                   key=lambda x: (S.RECORDS.index(x["predicted_record"]), -x["p_advance"]))
    qualifiers = [x["team"] for x in swiss if x["predicted_record"] in ("3-0", "3-1", "3-2")]

    # ---- Knockouts: assumed QF draw ----
    r30 = sorted([x for x in qualifiers if recs[x] == "3-0"], key=lambda z: -m.strength(z))
    r31 = sorted([x for x in qualifiers if recs[x] == "3-1"], key=lambda z: -m.strength(z))
    r32 = sorted([x for x in qualifiers if recs[x] == "3-2"], key=lambda z: -m.strength(z))
    best = None
    for p32 in itertools.permutations(r32, 2):
        rest = r31 + [x for x in r32 if x not in p32]
        for perm in itertools.permutations(rest):
            q = [(r30[0], p32[0]), (perm[0], perm[1]), (r30[1], p32[1]), (perm[2], perm[3])]
            same = sum(R.REGION[x] == R.REGION[y] for x, y in q)
            # prefer: no same-region QFs, then keep the four strongest teams spread across QFs
            spread = sum(abs(m.strength(x) - m.strength(y)) for x, y in q)
            key = (same, -spread)
            if best is None or key < best[0]:
                best = (key, q)
    qpairs = known.get("qf") or best[1]
    qlabel = "Quarterfinal" if known.get("qf") else "Quarterfinal (assumed draw)"
    qdays = [dt.datetime(2026, 11, d, 16, 0, tzinfo=CST) for d in (3, 4, 5, 6)]
    def ko_series(sid, label, x, y, when):
        if sid in done:
            return actual_series(done[sid], label)
        hit = [r for r in done.values() if r.get("phase") == "Knockouts" and {r["team_a"], r["team_b"]} == {x, y}]
        return actual_series(hit[0], label) if hit else series(m, sid, label, x, y, 5, when, narr)
    qf = [ko_series(f"KO-QF{i+1}", qlabel, x, y, t(qdays[i], CST, "CST")) for i, (x, y) in enumerate(qpairs)]
    sfd = [dt.datetime(2026, 11, d, 16, 0, tzinfo=CST) for d in (7, 8)]
    sf = [ko_series("KO-SF1", "Semifinal", qf[0]["winner"], qf[1]["winner"], t(sfd[0], CST, "CST")),
          ko_series("KO-SF2", "Semifinal", qf[2]["winner"], qf[3]["winner"], t(sfd[1], CST, "CST"))]
    fin = ko_series("KO-F", "Final", sf[0]["winner"], sf[1]["winner"], t(dt.datetime(2026, 11, 14, 14, 0, tzinfo=EST), EST, "EST (Brooklyn)"))
    champ = fin["winner"]

    out = dict(
        stage=a.stage,
        supersedes="predictions_baseline_v3_superseded.json (15/10/2026 15:47:43 NZDT; v4 = series-level fit on the full 2026 season incl. regular seasons, 2025 region prior, T1 adjustment halved)" if a.stage == "baseline" else None,
        created_utc=now.strftime("%d/%m/%Y %H:%M:%S UTC"),
        created_nz=now.astimezone(NZ).strftime("%d/%m/%Y %H:%M:%S NZDT"),
        valid_before={a.stage: t(first_match, VENUE[a.stage][0], VENUE[a.stage][1])},
        model=dict(ratings_as_of=res["as_of"], params=res["params"], sims=a.sims),
        ratings=[{k: r[k] for k in ("rank", "code", "region", "tier", "elo", "elo_base", "adj_logit", "sd", "p_vs_avg")} for r in res["teams"]],
        regions=res["regions"],
        playin=dict(series=pi, predicted_winner=piw, p_winner_exact=sim["playin_exact"], all_pairings=pi_matrix),
        swiss=dict(draw_published=bool(r1_pairs),
                   assumption=("Round 1 draw as published; later rounds simulated with the no-rematch rule. Play-In winner " + piw + ("." if known.get("piw") or a.playin_winner else " (predicted)."))
                              if r1_pairs else
                              "Round 1 draw (due 18/10) not published: records are averaged over all legal draws (Tier1 v Tier4, Tier2 v Tier3, no same-region), conditional on the predicted Play-In winner " + piw + ".",
                   series=swiss_series, predicted=swiss, qualifiers=qualifiers),
        knockouts=dict(assumption=("QF draw as published (31/10)." if known.get("qf") else
                                   "QF draw (31/10) is random. Assumed draw: no same-region QFs and favourites spread out; the two 3-0 teams each face a 3-2 team as per the rules."),
                       inputs=dict(results=a.results, r1=a.r1, playin_winner=piw, known=sim.get("known_results")),
                       qf=qf, sf=sf, final=fin),
        champion=champ,
        champion_probabilities={k: v["p_champion"] for k, v in sim["teams"].items()},
        sim_summary=sim["teams"],
        crystal_ball_model=sim["crystal_ball"],
    )
    out.update(narr.get("_extra", {}))
    blob = json.dumps(out, indent=1, sort_keys=False)
    open(out_path, "w").write(blob)
    h = hashlib.sha256(blob.encode()).hexdigest()
    if a.stage == "baseline":
        open("data/predictions_baseline.sha256", "w").write(h + "  predictions_baseline.json\n")
        os.chmod(out_path, 0o444)
    print("wrote", out_path, h[:16])
    print("Play-In:", [(s["team_a"], s["team_b"], s["winner"], s["score"], s.get("p_winner"), s["tier"]) for s in pi])
    if swiss_series: print("Swiss series:", [(s["team_a"], s["team_b"], s["winner"], s.get("p_winner"), s["tier"]) for s in swiss_series])
    print("Swiss:", [(x["team"], x["predicted_record"], x["p_record"]) for x in swiss])
    print("QF:", [(s["team_a"], s["team_b"], s["winner"], s["score"], s.get("p_winner"), s["tier"]) for s in qf])
    print("SF:", [(s["team_a"], s["team_b"], s["winner"], s["score"], s.get("p_winner"), s["tier"]) for s in sf])
    print("F:", (fin["team_a"], fin["team_b"], fin["winner"], fin["score"], fin.get("p_winner"), fin["tier"]))


if __name__ == "__main__":
    main()
