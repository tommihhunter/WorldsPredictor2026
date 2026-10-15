#!/usr/bin/env python3
"""
Live odds for the site: refit on everything played so far (fit date = today unless AS_OF is set), take every
finished Worlds series in data/results_live.json as fact, simulate the rest. Writes data/dash/live.json.
Never touches the graded predictions (data/predictions_*.json). Note: refreshes data/ratings.json and
data/matchups.json as a side effect (simulate.run calls ratings.build).
Run: python -X utf8 model/live.py [--sims 20000]
"""
import argparse, datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import simulate as S  # noqa: E402

ROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sims", type=int, default=20000); a = ap.parse_args()
    known = S.load_known(os.path.join(ROOT, "data", "results_live.json"))
    out, res, model, st = S.run(a.sims, 2026, None, None, known)
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=13))).strftime("%d/%m/%Y %H:%M NZDT")
    rows = [dict(team=t, region=S.R.REGION[t], p_playin_win=d["p_playin_win"], p_advance=d["p_advance"], p_semis=d["p_semis"],
                 p_final=d["p_final"], p_champion=d["p_champion"], as_of=res["as_of"], generated_nz=now, model=res["model"],
                 known=json.dumps(out["known_results"])) for t, d in out["teams"].items()]
    json.dump(rows, open(os.path.join(ROOT, "data", "dash", "live.json"), "w", encoding="utf-8"), indent=1)
    print(f"live.json: {len(rows)} teams, as_of {res['as_of']}, known {out['known_results']}")


if __name__ == "__main__":
    main()
