#!/usr/bin/env python3
"""
Per-game rows for the 19 Worlds teams from gol.gg team pages (data/golgg_teams_2026.json, games_log),
with an estimated date per game. Used by the v5 side and pool-depth candidates (model/side.py, model/pools.py).

games_log has no dates. gol.gg game ids grow with time, so each game takes the date of the nearest anchor
at or below its id; an anchor is a game whose (team, opponent, stage) matches exactly one date in
data/series_2026.json. Anchor dates are smoothed with a rolling median over +-5 anchors (by id), which drops
isolated mismatches (a stage label reused by another tournament). Games below the first anchor take the
first anchor's date. Checked 16/10/2026: 2.4% of consecutive games out of date order (45 of 1856).
"""
import bisect, json, os, statistics, datetime as dt
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS = {"FUR": "FURIA", "BFX": "BNK", "KRX": "DRX", "TT": "TTG", "SHFT": "SHIFT"}   # gol.gg short names -> series codes
_CACHE = {}


def _pdate(s):
    d, m, y = s.split("/")
    return dt.date(int(y), int(m), int(d))


def _teams():
    if "teams" not in _CACHE:
        path = os.path.join(ROOT, "data", "golgg_teams_2026.json")
        _CACHE["teams"] = json.load(open(path, encoding="utf-8"))["teams"]
    return _CACHE["teams"]


def worlds_teams():
    return set(_teams())


def load_games():
    """Unique games sorted by id: dict(id, date, team, opp, side 'B'/'R', win, picks, opp_picks, stage).
    side and win are from team's point of view; a game between two Worlds teams appears once."""
    if "games" in _CACHE:
        return _CACHE["games"]
    series = json.load(open(os.path.join(ROOT, "data", "series_2026.json"), encoding="utf-8"))
    dates = defaultdict(set)
    for r in series:
        dates[(r["a"], r["b"], r["stage"])].add(_pdate(r["date"]))
        dates[(r["b"], r["a"], r["stage"])].add(_pdate(r["date"]))
    raw, anchors = {}, []
    for team, t in _teams().items():
        for g in t["splits"]["ALL"]["games_log"]:
            gid = int(g["game_id"])
            opp = ALIAS.get(g["opponent"], g["opponent"])
            ds = dates.get((team, opp, g["stage"]), set())
            if len(ds) == 1:
                anchors.append((gid, next(iter(ds))))
            raw.setdefault(gid, dict(id=gid, team=team, opp=opp, side=g["side"], win=bool(g["win"]),
                                     picks=g["picks"], opp_picks=g["opp_picks"], stage=g["stage"]))
    anchors.sort()
    ords = [a[1].toordinal() for a in anchors]
    anchors = [(a[0], dt.date.fromordinal(int(statistics.median(ords[max(0, i - 5): i + 6])))) for i, a in enumerate(anchors)]
    ids = [a[0] for a in anchors]
    for g in raw.values():
        g["date"] = anchors[max(bisect.bisect_right(ids, g["id"]) - 1, 0)][1]
    _CACHE["games"] = sorted(raw.values(), key=lambda g: g["id"])
    return _CACHE["games"]
