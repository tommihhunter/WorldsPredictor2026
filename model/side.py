#!/usr/bin/env python3
"""
v5 candidate 4: side term from gol.gg game logs (19 Worlds teams).

For a game with team a on blue against team b on red:
    delta_logit(a) = blue + (g[a] + g[b]) / 2      and for a on red: -(blue + (g[a] + g[b]) / 2)
blue = global blue-side logit edge in the games given; g[t] = team t's blue-minus-red logit gap beyond the
global edge, shrunk toward 0 by n_eff / (n_eff + k), n_eff = 1 / (1/n_blue + 1/n_red).
"""
import math
from collections import defaultdict
import golgg_games as GG


def _logit(p):
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def _records(games):
    worlds = GG.worlds_teams()
    rec = defaultdict(lambda: {"B": [0, 0], "R": [0, 0]})      # side -> [wins, games]
    for g in games:
        rec[g["team"]][g["side"]][0] += int(g["win"]); rec[g["team"]][g["side"]][1] += 1
        if g["opp"] in worlds:
            other = "R" if g["side"] == "B" else "B"
            rec[g["opp"]][other][0] += int(not g["win"]); rec[g["opp"]][other][1] += 1
    return rec


def estimate(games, k=50):
    """(blue, g) from the games given (pass only games before the cut)."""
    if not games:
        return 0.0, {}
    blue = _logit(sum(g["win"] == (g["side"] == "B") for g in games) / len(games))
    g = {}
    for t, r in _records(games).items():
        (wb, nb), (wr, nr) = r["B"], r["R"]
        if not nb or not nr:
            g[t] = 0.0
            continue
        gap = _logit((wb + 0.5) / (nb + 1)) - _logit((wr + 0.5) / (nr + 1)) - 2 * blue
        neff = 1 / (1 / nb + 1 / nr)
        g[t] = gap * neff / (neff + k)
    return blue, g


def delta(a_side, a, b, blue, g):
    """Logit shift for team a playing on a_side ('B' or 'R') against b."""
    s = blue + (g.get(a, 0.0) + g.get(b, 0.0)) / 2
    return s if a_side == "B" else -s
