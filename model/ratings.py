#!/usr/bin/env python3
"""
Model switch.
  MODEL=v5: v4 code with the settings adopted by model/backtest_v5.py (data/backtest_v5.json, adopted.env).
            The default whenever that file adopted anything.
  MODEL=v4: the v4 defaults (series-level fit on the full 2026 season with a 2025 region prior, model/ratings_v4.py).
  MODEL=v3: the earlier game-level fit (model/ratings_v3.py), kept for comparison.
"""
import os as _os, json as _json
_BT = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "backtest_v5.json")
_ADOPTED = _json.load(open(_BT, encoding="utf-8")).get("adopted", {}).get("env", {}) if _os.path.exists(_BT) else {}
MODEL_NAME = _os.environ.get("MODEL", "v5" if _ADOPTED else "v4")
_os.environ.setdefault("MODEL_LABEL", MODEL_NAME)
if MODEL_NAME == "v5":
    for _k, _v in _ADOPTED.items():
        _os.environ.setdefault(_k, str(_v))
if MODEL_NAME == "v3":
    from ratings_v3 import *          # noqa
    from ratings_v3 import build, Model, REGION, WORLDS, series_probs_mixed, series_summary  # noqa
else:
    from ratings_v4 import *          # noqa
    from ratings_v4 import build, Model, REGION, WORLDS, series_probs_mixed, series_summary  # noqa

if __name__ == "__main__":
    import runpy
    runpy.run_path(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ratings_v3.py" if MODEL_NAME == "v3" else "ratings_v4.py"),
                   run_name="__main__")
