"""Checks for the v5 model work. Run: python -X utf8 tests/test_v5.py (no pytest needed)."""
import os, sys, json, math, random, datetime as dt
os.environ.setdefault("AS_OF", "15/10/2026")          # pin the fit date so v4 is reproducible
for _k in ("W_INTL", "PATCH_N", "PATCH_MULT", "POOL_BETA", "MODEL"):
    os.environ.pop(_k, None)                           # v4 defaults
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "model"))
import ratings_v4 as R  # noqa: E402
import golgg_games as GG  # noqa: E402
import side as SD  # noqa: E402

_FIT = {}


def full_fit():
    if "f" not in _FIT:
        _FIT["f"] = R.fit(R.load_series())
    return _FIT["f"]


def test_v4_defaults_reproduce_frozen_ratings():
    path = os.path.join(ROOT, "tests", "fixtures", "ratings_v4_2026-10-15.json")
    saved = {t["code"]: t["base_logit"] for t in json.load(open(path, encoding="utf-8"))["teams"]}
    res, _ = R.build(write=False)
    worst = max(abs(t["base_logit"] - saved[t["code"]]) for t in res["teams"])
    assert worst < 1e-3, f"v4 defaults drifted: max base_logit diff {worst:.5f}"


def test_load_series_keeps_patch():
    rows = R.load_series()
    assert all("patch" in r for r in rows)
    assert sum(1 for r in rows if r["patch"]) > 1000


def test_recent_patches():
    rows = [dict(patch="16.9"), dict(patch="16.10"), dict(patch="16.2"), dict(patch=None)]
    assert R.recent_patches(rows, 2) == {"16.9", "16.10"}
    assert R.recent_patches(rows, 0) == set()


def test_w_intl_moves_ratings():
    heavy = R.fit(R.load_series(), w_intl=3.0)
    assert heavy["converged"]
    assert max(abs(full_fit()["s"] - heavy["s"])) > 1e-3


def test_patch_boost_moves_ratings():
    f = R.fit(R.load_series(), patch_n=2, patch_mult=2.0)
    assert max(abs(full_fit()["s"] - f["s"])) > 1e-3


def test_games_have_dates_in_order():
    G = GG.load_games()
    assert len(G) > 1000
    assert len({g["id"] for g in G}) == len(G)
    assert all(g["side"] in ("B", "R") for g in G)
    assert len(GG.worlds_teams()) == 19
    ds = [g["date"] for g in G]
    assert dt.date(2026, 1, 1) <= min(ds) and max(ds) <= dt.date(2026, 10, 15)
    inversions = sum(1 for x, y in zip(ds, ds[1:]) if y < x)
    assert inversions / len(ds) < 0.05, f"game ids are not chronological enough: {inversions} inversions in {len(ds)}"


def _sg(team, side, win, opp="X"):
    return dict(team=team, opp=opp, side=side, win=win)


def test_side_estimate_shrinks_and_ranks():
    games = ([_sg("G2", "B", True)] * 40 + [_sg("G2", "B", False)] * 10 + [_sg("G2", "R", True)] * 20 + [_sg("G2", "R", False)] * 30
             + [_sg("KC", "B", True)] * 30 + [_sg("KC", "B", False)] * 20 + [_sg("KC", "R", True)] * 30 + [_sg("KC", "R", False)] * 20)
    blue, g = SD.estimate(games, k=20)
    assert abs(blue - math.log(0.6 / 0.4)) < 1e-9          # blue side won 120 of 200
    assert g["G2"] > 0.3 > g["KC"]
    _, g_inf = SD.estimate(games, k=1e9)
    assert abs(g_inf["G2"]) < 1e-3                          # infinite shrinkage removes the team term


def test_side_delta_is_antisymmetric_and_safe():
    blue, g = 0.1, {"G2": 0.6}
    assert abs(SD.delta("B", "G2", "KC", blue, g) + SD.delta("R", "KC", "G2", blue, g)) < 1e-12
    assert SD.delta("B", "NEW", "OTHER", blue, g) == blue     # unknown teams: global blue edge only
    assert SD.estimate([], k=50) == (0.0, {})


if __name__ == "__main__":
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f(); print("PASS", n)
        except Exception as e:  # noqa: BLE001
            failed += 1; print("FAIL", n, "-", type(e).__name__, e)
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
