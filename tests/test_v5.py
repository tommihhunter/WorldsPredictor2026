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
import pools as PL  # noqa: E402
import backtest_v5 as BT  # noqa: E402
import simulate as S  # noqa: E402

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


def test_pool_depths_counts_repeat_picks_only():
    a = dict(team="KC", opp="X", picks=["Aatrox", "Vi", "Ahri", "Jinx", "Rell"], opp_picks=[])
    b = dict(team="KC", opp="X", picks=["Gnar", "Vi", "Ahri", "Jinx", "Rell"], opp_picks=[])
    short = dict(team="KC", opp="X", picks=["Gnar", "Vi", "Ahri"], opp_picks=[])
    # top: Aatrox x2 counts, Gnar x1 does not (the 3-pick game is skipped); other positions: one champion each
    assert PL.depths([a, a, b, short])["KC"] == 1.0


def test_pool_depths_on_real_logs():
    d = PL.depths(GG.load_games())
    assert len(d) == 19 and all(1 <= v <= 40 for v in d.values()), d


def test_model_pool_term_only_in_bo3_plus():
    m = R.Model(full_fit(), [], depths={"GEN": 10.0, "T1": 8.0}, pool_beta=0.1)
    assert abs((m.d_game("GEN", "T1", 5) - m.d_game("GEN", "T1", 1)) - 0.2) < 1e-9
    assert m.d_game("GEN", "KC", 5) == m.d_game("GEN", "KC", 1)      # KC has no depth: no term
    m0 = R.Model(full_fit(), [])
    assert m0.d_game("GEN", "T1", 5) == m0.d_game("GEN", "T1", 1)    # default: v4 behaviour


def test_boot_direction():
    assert BT.boot([1.0] * 40, [0.9] * 40, n=200) == 1.0
    assert BT.boot([1.0] * 40, [1.1] * 40, n=200) == 0.0


def test_series_ll_matches_model():
    r = dict(bo=5, sa=3, sb=1)
    sc = R.series_probs_mixed(0.4, 5)
    pa = sc["3-0"] + sc["3-1"] + sc["3-2"]
    assert abs(BT.series_ll(0.4, r) - (-math.log(pa))) < 1e-12


def test_judge_rules():
    assert BT.judge([1.0] * 40, [0.9] * 40)["adopt"]
    assert not BT.judge([1.0] * 40, [1.1] * 40)["adopt"]
    assert not BT.judge([1.0] * 40, [0.9] * 40, [1.0] * 40, [1.01] * 40)["adopt"]   # B worse by more than 0.002


def test_model_switch_follows_backtest():
    import subprocess
    env = {k: v for k, v in os.environ.items() if k not in ("MODEL", "W_INTL", "PATCH_N", "PATCH_MULT", "POOL_BETA")}
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", "import ratings; print(ratings.MODEL_NAME)"],
                         cwd=os.path.join(ROOT, "model"), capture_output=True, text=True, env=env)
    adopted = json.load(open(os.path.join(ROOT, "data", "backtest_v5.json"), encoding="utf-8"))["adopted"]["env"]
    assert out.stdout.strip() == ("v5" if adopted else "v4"), out.stdout + out.stderr


def test_as_of_env_and_default():
    assert R.AS_OF == dt.date(2026, 10, 15)          # pinned by this file's header
    import subprocess
    env = {k: v for k, v in os.environ.items() if k != "AS_OF"}
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", "import ratings_v4 as R; print(R.AS_OF)"],
                         cwd=os.path.join(ROOT, "model"), capture_output=True, text=True, env=env)
    assert out.stdout.strip() == str(dt.datetime.now(dt.timezone(dt.timedelta(hours=13))).date()), out.stdout + out.stderr


def test_load_known_playin_by_slot_and_empty():
    import tempfile
    assert S.load_known(None)["playin"] == {}
    rows = [dict(id="PI-R1-A", phase="Play-In", kind="series", team_a="KC", team_b="C9", winner="KC"),
            dict(id="PI-GF", phase="Play-In", kind="series", team_a="C9", team_b="KC", winner="C9")]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(rows, fh)
    k = S.load_known(fh.name)
    os.unlink(fh.name)
    assert k["playin"] == {"PI-R1-A": "KC", "PI-GF": "C9"} and k["piw"] == "C9"


def test_playin_rematch_final_uses_slot_result():
    st = S.SeriesTable(R.Model(full_fit(), []))
    rng = random.Random(3)
    # KC beat C9 in round 1, C9 wins the rematch in the final: the Play-In winner must be C9 every time
    k = {"PI-R1-A": "KC", "PI-R1-B": "FURIA", "PI-WM": "KC", "PI-EM": "C9", "PI-LF": "C9", "PI-GF": "C9"}
    assert all(S.playin_sample(st, rng, k) == "C9" for _ in range(50))


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
