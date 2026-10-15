#!/usr/bin/env python3
"""
Model switch. MODEL=v4 (default): series-level fit on the full 2026 season with a 2025
region prior (model/ratings_v4.py). MODEL=v3: the earlier game-level fit on playoff and
international data only (model/ratings_v3.py), kept for comparison and for grading the
frozen v3 baseline.
"""
import os as _os
if _os.environ.get("MODEL", "v4") == "v3":
    from ratings_v3 import *          # noqa
    from ratings_v3 import build, Model, REGION, WORLDS, series_probs_mixed, series_summary  # noqa
else:
    from ratings_v4 import *          # noqa
    from ratings_v4 import build, Model, REGION, WORLDS, series_probs_mixed, series_summary  # noqa

if __name__ == "__main__":
    import runpy, sys
    runpy.run_path(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ratings_v3.py" if _os.environ.get("MODEL", "v4") == "v3" else "ratings_v4.py"), run_name="__main__")
