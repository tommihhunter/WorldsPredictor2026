#!/usr/bin/env python3
"""
v5 candidate 5: Fearless pool depth from gol.gg game logs.

depth(team) = (number of distinct champions the team picked at least min_games times, in any pick slot,
over the games given) / 5. Pass only games before the cut. gol.gg lists picks in draft order (not by role),
so pick position is ignored. Games with fewer than 5 recorded picks are skipped.
"""
from collections import Counter, defaultdict
import golgg_games as GG


def depths(games, min_games=2):
    worlds = GG.worlds_teams()
    pool = defaultdict(Counter)

    def add(team, picks):
        if team in worlds and len(picks) == 5:
            pool[team].update(picks)

    for g in games:
        add(g["team"], g.get("picks", []))
        add(g["opp"], g.get("opp_picks", []))
    return {t: sum(1 for n in c.values() if n >= min_games) / 5 for t, c in pool.items()}
