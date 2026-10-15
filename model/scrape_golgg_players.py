#!/usr/bin/env python3
"""
Player stats and champion pools for the 95 Worlds players from gol.gg (2026 = gol.gg season S16).

Default (full season, all tournaments)  -> data/golgg_players_2026.json
    python3 model/scrape_golgg_players.py
Single split (recency view)              -> data/golgg_players_<split>_2026.json (or --out)
    python3 model/scrape_golgg_players.py --split Summer --out data/golgg_players_summer_2026.json

Source: https://gol.gg/players/list/season-S16/split-<split>/tournament-ALL/ (stats table)
        https://gol.gg/players/player-stats/<id>/season-S16/split-<split>/tournament-ALL/ (champion pool)
gol.gg split labels for S16: Pre-Season, Winter, Spring, Summer, ALL. Player ids are always resolved from
the split-ALL list page (ids are identical across splits); the split page is only used for the split stats.
A split run also carries season_games (from data/golgg_players_2026.json) so the recent share is visible, and
lists per league which gol.gg tournaments the split covers (taken from the split page's tournament dropdown).
"""
import re, html, json, os, sys, time, argparse, urllib.request, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
UA = {"User-Agent": "Mozilla/5.0"}
SEASON = "S16"
LIST_URL = "https://gol.gg/players/list/season-S16/split-{split}/tournament-ALL/"
PLAYER_URL = "https://gol.gg/players/player-stats/{pid}/season-S16/split-{split}/tournament-ALL/"
SPLITS = ["Pre-Season", "Winter", "Spring", "Summer", "ALL"]
SPLIT_ALIAS = {"pre": "Pre-Season", "preseason": "Pre-Season", "pre-season": "Pre-Season", "winter": "Winter",
               "spring": "Spring", "summer": "Summer", "all": "ALL"}
SEASON_FILE = "data/golgg_players_2026.json"
# dossier name -> gol.gg name where they differ
ALIAS = {"Hans Sama": "Hans Sama", "ON": "ON", "SiuLoong": "SiuLoong"}
ROLE_FIX = {"JUNGLE": "JNG", "BOT": "ADC", "SUPPORT": "SUP"}
# league -> prefixes of gol.gg tournament names that belong to that league (used for the per-league notes)
LEAGUE_PREFIX = {"LCK": ("LCK 20", "LCK Cup"), "LPL": ("LPL 20",), "LEC": ("LEC 20",), "LCS": ("LCS 20",),
                 "LCP": ("LCP 20",), "CBLOL": ("CBLOL",)}
INTL_KEYS = ("Worlds", "MSI", "First Stand", "Esports World Cup", "KeSPA", "Demacia", "World Star", "Americas Cup")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            err = e
            time.sleep(2 + 3 * attempt)
    raise err


def num(s):
    s = s.replace("%", "").strip()
    try:
        return float(s) if "." in s or "-" in s[1:] else int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def parse_list(page, split="ALL"):
    """name -> [row dicts incl. pid] for one list page (split-specific links in the table)."""
    head = re.search(r"<thead>(.*?)</thead>", page, re.S).group(1)
    cols = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<th[^>]*>(.*?)</th>", head, re.S)]
    out = {}
    pat = r"player-stats/(\d+)/season-S16/split-%s/tournament-ALL/' title='[^']*'>([^<]*)</a></td>(.*?)</tr>" % re.escape(split)
    for pid, name, rest in re.findall(pat, page, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", rest, re.S)]
        row = dict(zip(cols[1:], cells))
        out.setdefault(html.unescape(name), []).append(dict(pid=pid, **row))
    return out


def parse_tournaments(page):
    """Tournament names offered by the list page's tournament dropdown (split-filtered on gol.gg)."""
    sel = re.search(r"<select[^>]*cbtournament[^>]*>(.*?)</select>", page, re.S)
    if not sel:
        return []
    return [html.unescape(v) for v in re.findall(r"option value='([^']*)'", sel.group(1)) if v != "ALL"]


def parse_champs(page):
    out = []
    for alt, games, wr, kda in re.findall(
            r"champion-stats/\d+/[^']*'><img[^>]*alt='([^']*)'[^>]*/>[^<]*</a></td>\s*<td[^>]*>(\d+)</td>\s*<td[^>]*>.*?line-height:1\.2em'>([\d.]+)%</div>.*?</td>\s*<td[^>]*>([\d.]+|-)</td>",
            page, re.S):
        out.append(dict(champ=html.unescape(alt), games=int(games), wr=float(wr), kda=None if kda == "-" else float(kda)))
    return out


def stats_from_row(c):
    return dict(games=num(c.get("Games", "")), wr=num(c.get("Win rate", "")), kda=num(c.get("KDA", "")),
                kp=num(c.get("KP%", "")), dmg_pct=num(c.get("DMG%", "")), gold_pct=num(c.get("Gold%", "")),
                gd15=num(c.get("GD@15", "")), csd15=num(c.get("CSD@15", "")), xpd15=num(c.get("XPD@15", "")),
                dpm=num(c.get("DPM", "")), csm=num(c.get("CSM", "")), vspm=num(c.get("VSPM", "")),
                solo_kills=num(c.get("Solo Kills", "")))


def empty_stats():
    return dict(games=0, wr=None, kda=None, kp=None, dmg_pct=None, gold_pct=None, gd15=None, csd15=None, xpd15=None,
                dpm=None, csm=None, vspm=None, solo_kills=None)


def league_notes(split, tournaments, regions):
    """Per-league description of what the split covers on gol.gg, from the split page's tournament dropdown."""
    notes = []
    for lg in regions:
        evs = [t for t in tournaments if t.startswith(LEAGUE_PREFIX.get(lg, (lg,))) and " CL " not in t]
        notes.append(f"{lg}: gol.gg split-{split} = " + (", ".join(sorted(evs)) if evs else "no tournaments of this league"))
    intl = [t for t in tournaments if any(k in t for k in INTL_KEYS)]
    if intl:
        notes.append(f"International/other events also inside split-{split} on gol.gg (included in the players' split "
                     f"stats if they played them): {', '.join(sorted(intl))}")
    notes.append("gol.gg maps every league onto four S16 split labels regardless of the league's own naming: Pre-Season "
                 "(Kespa Cup 2025), Winter (LCK Cup / LPL Split 1 / LCP Split 1 / CBLOL Cup / LCS Lock-In / LEC Versus / "
                 "First Stand), Spring (LCK Rounds 1-2 + Road to MSI / LPL Split 2 / LCP Split 2 / CBLOL Split 1 / LCS+LEC "
                 "Spring / MSI) and Summer (LCK Rounds 3-4 + Season Play-In/Playoffs / LPL Split 3 + Grand + Regional "
                 "Finals / LCP Split 3 / CBLOL Split 2 / LCS+LEC Summer / EWC / Worlds Play-In). The four splits sum to "
                 "the split-ALL season total.")
    notes.append("Stats are per player (own games only); a split value is the player's own games in that split, so "
                 "subs/mid-season joiners show fewer games than team-mates and split_share = games / season_games.")
    return notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="ALL", help="gol.gg split label: Pre-Season (alias Pre), Winter, Spring, Summer, ALL (default)")
    ap.add_argument("--out", default=None, help="output JSON path (default data/golgg_players_2026.json for ALL, "
                                                "data/golgg_players_<split>_2026.json otherwise)")
    args = ap.parse_args()
    split = SPLIT_ALIAS.get(args.split.lower())
    if split is None:
        sys.exit(f"unknown split {args.split!r}; gol.gg S16 splits: {', '.join(SPLITS)}")
    out_path = args.out or (SEASON_FILE if split == "ALL" else f"data/golgg_players_{split.lower().replace('-', '')}_2026.json")
    list_all_url = LIST_URL.format(split="ALL")
    list_split_url = LIST_URL.format(split=split)
    player_url = PLAYER_URL.format(pid="{pid}", split=split)

    teams = json.load(open("data/teams.json"))
    rosters, regions = {}, {}
    for t in teams if isinstance(teams, list) else teams.values():
        code = t["code"]
        regions[code] = t.get("region")
        for p in t["roster"]:
            rosters.setdefault(code, []).append((ROLE_FIX.get(p["role"], p["role"]), p["player"].strip()))

    # season_games lookup (by pid, falling back to team+player) for split runs
    season = {}
    if split != "ALL" and os.path.exists(SEASON_FILE):
        for code, ps in json.load(open(SEASON_FILE))["teams"].items():
            for p in ps:
                if p.get("found"):
                    season[("pid", p["pid"])] = p.get("games")
                    season[("name", code, p["player"])] = p.get("games")

    print("fetching player list (split-ALL, for ids)")
    plist = parse_list(get(list_all_url), "ALL")
    print(len(plist), "players on gol.gg 2026")
    if split == "ALL":
        split_rows, tournaments = None, None
    else:
        time.sleep(0.4)
        print(f"fetching player list (split-{split}, for split stats)")
        page = get(list_split_url)
        split_rows = {c["pid"]: c for rows in parse_list(page, split).values() for c in rows}
        tournaments = parse_tournaments(page)
        print(len(split_rows), f"players with games in split-{split};", len(tournaments), "tournaments in that split")
    _cache = {}

    def split_cache(s):
        """pid -> list row for another split (fetched lazily, only for players with 0 games in the requested split)."""
        if s not in _cache:
            time.sleep(0.4)
            _cache[s] = {c["pid"]: c for rows in parse_list(get(LIST_URL.format(split=s)), s).values() for c in rows}
        return _cache[s]

    out, notes = {}, []
    for code, ps in rosters.items():
        out[code] = []
        for role, name in ps:
            cands = plist.get(ALIAS.get(name, name)) or plist.get(name.lower()) or [c for k, c in plist.items() if k.lower() == name.lower()]
            if cands and isinstance(cands[0], list):
                cands = cands[0]
            if not cands:
                notes.append(f"{code} {name}: not found")
                out[code].append(dict(role=role, player=name, found=False))
                continue
            cands = sorted(cands, key=lambda c: -(num(c.get("Games") or "0") or 0))
            if len(cands) > 1:
                notes.append(f"{code} {name}: {len(cands)} ids, took pid {cands[0]['pid']} with {cands[0].get('Games')} games (others: {[(c['pid'], c.get('Games')) for c in cands[1:]]})")
            c = cands[0]
            if split == "ALL":
                page = get(player_url.format(pid=c["pid"]))
                champs = sorted(parse_champs(page), key=lambda x: (-x["games"], -x["wr"]))
                rec = dict(role=role, player=name, found=True, pid=c["pid"], **stats_from_row(c),
                           n_champs=len(champs), champs=champs)
                time.sleep(0.4)
            else:
                row = split_rows.get(c["pid"])
                extra = {}
                if row is None:
                    stats, champs = empty_stats(), []
                    # which earlier split holds this player's most recent games?
                    last = None
                    for s in reversed(SPLITS[:SPLITS.index(split)]):
                        r = split_cache(s).get(c["pid"])
                        if r:
                            last = (s, num(r.get("Games", "")))
                            break
                    extra = dict(last_split_with_games=last[0] if last else None, last_split_games=last[1] if last else None)
                    notes.append(f"{code} {name}: 0 games in split-{split} (pid {c['pid']}, {c.get('Games')} season games; "
                                 f"most recent games in split-{last[0]}: {last[1]})" if last else
                                 f"{code} {name}: 0 games in split-{split} and in no other S16 split (pid {c['pid']})")
                else:
                    page = get(player_url.format(pid=c["pid"]))
                    champs = sorted(parse_champs(page), key=lambda x: (-x["games"], -x["wr"]))
                    stats = stats_from_row(row)
                    time.sleep(0.4)
                if stats["wr"] is not None:
                    stats["wr"] = float(stats["wr"])
                sg = season.get(("pid", c["pid"]), season.get(("name", code, name)))
                share = round(stats["games"] / sg, 3) if sg else None
                rec = dict(role=role, player=name, found=True, pid=c["pid"], split=split, **stats,
                           season_games=sg, split_share=share, **extra, n_champs=len(champs), champs=champs)
            out[code].append(rec)
            print(code, role, name, c["pid"], rec["games"], "games", len(champs), "champs")

    if split == "ALL":
        source = dict(url=list_all_url, player_url=player_url,
                      scope="2026 season (gol.gg S16), all tournaments incl. regular season, playoffs and internationals",
                      accessed=dt.date.today().strftime("%d/%m/%Y"))
        doc = dict(source=source, notes=notes, teams=out)
    else:
        leagues = sorted(set(r for r in regions.values() if r))
        coverage = league_notes(split, tournaments, leagues)
        source = dict(url=list_split_url, ids_url=list_all_url, player_url=player_url, split=split,
                      scope=f"2026 season (gol.gg S16), split-{split} only; season_games from {SEASON_FILE} (split-ALL)",
                      tournaments_in_split=tournaments, accessed=dt.date.today().strftime("%d/%m/%Y"))
        doc = dict(source=source, notes=coverage + notes, teams=out)
    json.dump(doc, open(out_path, "w"), indent=1)
    print("\n".join(doc["notes"]))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
