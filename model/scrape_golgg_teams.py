#!/usr/bin/env python3
"""
Team-level draft and style data for the 19 Worlds teams from gol.gg team pages (2026 = gol.gg season S16).

    python3 model/scrape_golgg_teams.py                      -> data/golgg_teams_2026.json (splits ALL + Summer)
    python3 model/scrape_golgg_teams.py --split ALL,Summer,Spring --out data/x.json

Sources per team and split (team ids are per season on gol.gg; the S16 list page is the id authority):
    list   https://gol.gg/teams/list/season-S16/split-ALL/tournament-ALL/
    stats  https://gol.gg/teams/team-stats/<id>/split-<split>/tournament-ALL/
    draft  https://gol.gg/teams/team-draft/<id>/split-<split>/tournament-ALL/
    icons  https://gol.gg/champion/list/season-S16/split-ALL/tournament-ALL/  (icon filename -> gol.gg champion name)

What each page offers (exact labels are kept in stats_raw / page_tables):
  stats: Region, Season, "Win Rate" record + %, "Average game duration"; blocks Economy, Aggression, Objectives, Vision;
         "Most banned champions by <team>" / "against <team>" (top 6, Overall / Blue Side / Red Side, % of games);
         Chart.js data for wins/losses by side and elemental dragons killed/lost; "<team> player's stats" table
         (Role, Player, KDA, KP %, VSPM, Dmg %, Gold %, Champions played) split into "Last line-up" and "Subs".
  draft: "# Games", "Win Rate", "Average Game Duration"; "Role priority" (average pick order per role);
         "First Picked", "Last Picked", "Banned by <code>", "Banned Against <code>" (top 10 counts);
         per-game draft log (20 draft slots per team: grayscale icon = ban, colour icon = pick) which is the basis of
         the derived team-level pick / ban lists in this file (gol.gg has no team "most picked" table).
Champion names are gol.gg's own display names (KSante, Kaisa, RekSai, Chogath, KogMaw, LeBlanc, Lee Sin, Wukong...),
identical to data/golgg_players_2026.json. No packages beyond the standard library.
"""
import re, html, json, os, sys, time, argparse, urllib.request, datetime as dt
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
UA = {"User-Agent": "Mozilla/5.0"}
SEASON = "S16"
LIST_URL = "https://gol.gg/teams/list/season-S16/split-ALL/tournament-ALL/"
STATS_URL = "https://gol.gg/teams/team-stats/{tid}/split-{split}/tournament-ALL/"
DRAFT_URL = "https://gol.gg/teams/team-draft/{tid}/split-{split}/tournament-ALL/"
CHAMP_LIST_URL = "https://gol.gg/champion/list/season-S16/split-ALL/tournament-ALL/"
SPLITS = ["Pre-Season", "Winter", "Spring", "Summer", "ALL"]
SPLIT_ALIAS = {"pre": "Pre-Season", "preseason": "Pre-Season", "pre-season": "Pre-Season", "winter": "Winter",
               "spring": "Spring", "summer": "Summer", "all": "ALL"}
OUT_DEFAULT = "data/golgg_teams_2026.json"
RAW_DIR_DEFAULT = "/tmp/claude-0/-home-claude/1d204bdd-0868-575c-b191-950a1b7d4400/scratchpad/golgg_teams"
SLEEP = 0.5

# dossier code -> (gol.gg team name, gol.gg S16 team id as known on 15/10/2026; None = resolve from the list page)
TEAMS = {
    "AL": ("Anyone s Legend", 2848), "BLG": ("Bilibili Gaming", 2849), "TES": ("Top Esports", 2852),
    "IG": ("Invictus Gaming", 2850), "GEN": ("Gen.G", 2804), "HLE": ("Hanwha Life Esports", 2805), "T1": ("T1", 2809),
    "DK": ("Dplus KIA", 2802), "G2": ("G2 Esports", 2897), "MKOI": ("Movistar KOI", 2900), "KC": ("Karmine Corp", 2899),
    "TLAW": ("Team Liquid", 2813), "LYON": ("LYON", 2954), "C9": ("Cloud9", 2812), "TSW": ("Team Secret Whales", 2887),
    "CFO": ("CTBC Flying Oyster", 2880), "LOS": ("Los Grandes", 2895), "FURIA": ("FURIA", 2889),
    "MVK": ("MVK Esports", None),
}

# exact gol.gg stat labels (as printed on the stats page, incl. trailing colon/space) -> normalised key(s)
LABEL_MAP = {
    "Gold Per Minute:": "gpm", "Gold Differential per Minute:": "gdm", "Gold Differential at 15 min:": "gd15",
    "Win Rate when ahead at 15 min:": "wr_when_ahead_15_pct", "CS Per Minute:": "cspm",
    "CS Differential at 15 min:": "csd15", "Tower Differential at 15 min:": "towerd15",
    "Avg. Tower Difference:": "tower_diff_avg", "First Tower :": "first_tower_pct",
    "Damage Per Minute:": "dpm", "First Blood:": "first_blood_pct", "Kills Per Game:": "kills_pg",
    "Deaths Per Game:": "deaths_pg", "Average Kill / Death Ratio:": "kd_ratio", "Average Assists / Kill:": "assists_per_kill",
    "Plates / game (TOP|MID|BOT):": "plates_pg", "Dragons / game:": "dragons_pg", "Dragons at 15 min:": "dragons_at15",
    "Voidgrubs / game:": "voidgrubs_pg", "Herald / game:": "herald_pg", "Nashors / game:": "barons_pg",
    "Vision Score Per Minute:": "vspm", "Wards Per Minute:": "wpm", "Vision Wards Per Minute:": "vwpm",
    "Wards Cleared Per Minute:": "wcpm", "% Wards Cleared:": "wards_cleared_pct",
}
# Draft log layout on the draft tab. A game with known pick order has 20 cells per team row: bans 0-5, picks 6-11,
# bans 12-15, picks 16-19. The first-listed team (the one named first in the game title, NOT necessarily blue side)
# occupies indexes 0,2,4 | 6,9,10 | 13,15 | 17,18 and the second-listed team the rest, so the row gives each team's
# own ban/pick order 1-5 but not the chronological interleaving. A game without pick-order data has 15 cells:
# 10 interleaved ban cells followed by a block of 5 picks in unknown order.
SLOT_KIND = ["ban"] * 6 + ["pick"] * 6 + ["ban"] * 4 + ["pick"] * 4
FIRST_ROW_SLOTS = {0, 2, 4, 6, 9, 10, 13, 15, 17, 18}

_last_fetch = 0.0


def get(url):
    """urllib GET with Mozilla UA, 40 s timeout, 3 attempts, >= SLEEP s between pages."""
    global _last_fetch
    req = urllib.request.Request(url, headers=UA)
    err = None
    for attempt in range(3):
        wait = SLEEP - (time.time() - _last_fetch)
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                _last_fetch = time.time()
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            err = e
            _last_fetch = time.time()
            time.sleep(2 + 3 * attempt)
    raise err


def fetch(url, raw_dir, name):
    page = get(url)
    if raw_dir:
        with open(os.path.join(raw_dir, name), "w", encoding="utf-8") as f:
            f.write(page)
    return page


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").strip()


def num(s):
    """'+166' -> 166, '58%' -> 58.0, '31.44' -> 31.44, '-' -> None."""
    if s is None:
        return None
    s = s.strip().replace("%", "").replace("+", "").replace(",", "")
    if s in ("", "-"):
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def pct(s):
    v = num(s)
    return None if v is None else float(v)


def mmss_to_min(s):
    m = re.fullmatch(r"(\d+):(\d\d)", s.strip())
    return round(int(m.group(1)) + int(m.group(2)) / 60, 2) if m else None


def r1(x):
    return None if x is None else round(x, 1)


# ----------------------------------------------------------------------------------------------- list / champion map

def parse_team_list(page):
    """gol.gg name -> team id for the season list page (first id per name)."""
    out = {}
    for tid, name in re.findall(r"team-stats/(\d+)/[^']*'[^>]*>([^<]*)</a>", page):
        out.setdefault(html.unescape(name).strip(), tid)
    return out


def icon_map_from(page):
    """icon filename stem -> gol.gg champion display name, from any page that has <img alt='..' src='..champions_icon/X.png'>."""
    m = {}
    for alt, fn in re.findall(r"alt='([^']*)'\s+src='[^']*champions_icon/([^'/]+)\.png'", page):
        m[fn] = html.unescape(alt)
    for fn, alt in re.findall(r"src='[^']*champions_icon/([^'/]+)\.png'\s+alt='([^']*)'", page):
        m[fn] = html.unescape(alt)
    return m


# ----------------------------------------------------------------------------------------------- stats page

def page_title_team(page):
    m = re.search(r"<title>(.*?) stats in ", page, re.S)
    return html.unescape(m.group(1)).strip() if m else None


def parse_header(page):
    """Region / Season / record / win rate / average game duration from the '<team> stats' table."""
    out = {}
    m = re.search(r"Region : </td>\s*<td[^>]*>([^<]*)<", page)
    out["region"] = m.group(1).strip() if m else None
    m = re.search(r"Season : </td>\s*<td[^>]*>([^<]*)<", page)
    out["season"] = m.group(1).strip() if m else None
    m = re.search(r"Win Rate : </td>\s*<td[^>]*>\s*(\d+)W\s*-\s*(\d+)L", page)
    out["wins"], out["losses"] = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    m = re.search(r"Win Rate : </td>.*?line-height:1\.2em'>([\d.]+)%</div>", page, re.S)
    out["wr_page_pct"] = pct(m.group(1)) if m else None
    m = re.search(r"Average game duration : </td>\s*<td[^>]*>([^<]*)<", page)
    out["avg_game_time"] = m.group(1).strip() if m else None
    return out


def parse_stat_blocks(page):
    """Economy / Aggression / Objectives / Vision tables -> {block: {exact label: raw value text}}."""
    out = {}
    for m in re.finditer(r"<thead><tr><th colspan='2'>(Economy|Aggression|Objectives|Vision)</th></tr></thead>"
                         r"<tbody>(.*?)</tbody>", page, re.S):
        block, body = m.group(1), m.group(2)
        rows = {}
        # value cells may hold a nested 'tablebarg' bar table, so split on the label cell instead of matching whole rows
        for chunk in re.split(r"<tr><td style='text-align:right'>", body)[1:]:
            lab, _, val = chunk.partition("</td>")
            lab = text(lab)
            if not lab:
                continue
            mm = re.search(r"line-height:1\.2em'>([^<]*)</div>", val)
            if mm:
                rows[lab] = text(mm.group(1))
            else:
                mm = re.match(r"\s*<td[^>]*>(.*?)</td>", val, re.S)
                rows[lab] = text(mm.group(1)) if mm else text(val)
        out[block] = rows
    return out


def normalise_stats(blocks, notes, where):
    """Flatten the raw blocks into numeric keys via LABEL_MAP; unknown labels are reported in notes."""
    st = {k: None for k in LABEL_MAP.values()}
    st.update(dict(plates_top=None, plates_mid=None, plates_bot=None, dragon_share_pct=None, herald_share_pct=None,
                   baron_share_pct=None))
    for block, rows in blocks.items():
        for lab, raw in rows.items():
            key = LABEL_MAP.get(lab)
            if key is None:
                notes.append(f"{where}: unmapped stat label {lab!r} = {raw!r} (kept in stats_raw only)")
                continue
            if key == "plates_pg":
                mm = re.match(r"([\d.]+)\s*\(([\d.]+)\|([\d.]+)\|([\d.]+)\)", raw)
                if mm:
                    st["plates_pg"], st["plates_top"], st["plates_mid"], st["plates_bot"] = map(float, mm.groups())
                else:
                    st["plates_pg"] = num(raw)
            elif key in ("dragons_pg", "herald_pg", "barons_pg"):
                mm = re.match(r"([\d.]+)\s*\(([\d.]+)%\)", raw)
                share_key = {"dragons_pg": "dragon_share_pct", "herald_pg": "herald_share_pct", "barons_pg": "baron_share_pct"}[key]
                if mm:
                    st[key], st[share_key] = float(mm.group(1)), float(mm.group(2))
                else:
                    st[key] = num(raw)
            elif key.endswith("_pct"):
                st[key] = pct(raw)
            else:
                st[key] = num(raw)
    return st


def parse_ban_tables(page, team_name):
    """'Most banned champions by/against <team>' -> {'Overall': [(champ, pct)], 'Blue Side': ..., 'Red Side': ...}."""
    out = {}
    for kind in ("by", "against"):
        cap = f"<caption>Most banned champions {kind} {team_name}</caption>"
        i = page.find(cap)
        if i < 0:
            out[kind] = None
            continue
        j = page.find("</table>\n  </div>", i)
        seg = page[i:j if j > 0 else i + 20000]
        rows = {}
        for lab, body in re.findall(r"<tr><td class='p-1[^']*'>(Overall|Blue Side|Red Side)</td>(.*?)(?=<tr><td class='p-1|</table>)", seg, re.S):
            rows[lab] = [dict(champ=html.unescape(a), pct=pct(p))
                         for a, p in re.findall(r"alt='([^']*)'[^>]*/></a><br/>\s*([\d.]+)%", body)]
        out[kind] = rows
    return out


def parse_chart(page, var):
    """Chart.js 'var WRData = {labels:[...], datasets:[{label, data:[..]}, ...]}' -> (labels, {label: [ints]})."""
    i = page.find(f"var {var} =")
    if i < 0:
        return None, None
    seg = page[i:page.find("</script>", i)]
    labels = [l.strip("' ") for l in re.search(r"labels:\s*\[(.*?)\]", seg, re.S).group(1).split(",")]
    data = {}
    for lab, vals in re.findall(r"label:\s*'([^']*)'.*?data\s*:\s*\[([\d,\s]*)\]", seg, re.S):
        data[lab] = [int(v) for v in vals.replace(" ", "").split(",") if v != ""]
    return labels, data


def parse_players(page):
    """'<team> player's stats' table -> list of players with status Last line-up / Subs and their champion pools."""
    i = page.find("player's stats</caption>")
    if i < 0:
        return [], []
    seg = page[i:page.find("</tbody>", i)]
    head = re.findall(r"<th[^>]*>(.*?)</th>", seg[:seg.find("<tbody>")], re.S)
    cols = [text(h) for h in head]
    # gol.gg only prints the 'Last line-up' / 'Subs' dividers when the team used more than five players
    players, status = [], ("Last line-up" if "<em>Last line-up</em>" not in seg else None)
    for part in re.split(r"(?=<tr><td colspan='8'><em>|<tr><td><img src='\.\./_img/role/)", seg):
        m = re.match(r"<tr><td colspan='8'><em>([^<]*)</em>", part)
        if m:
            status = m.group(1).strip()
            continue
        m = re.match(r"<tr><td><img src='\.\./_img/role/(\w+)\.png'[^>]*>\s*(\w+)</td><td>(?:<img[^>]*alt='([^']*)'/>)?&nbsp;"
                     r"<a title='[^']*' href='\.\./players/player-stats/(\d+)/[^']*'>([^<]*)</a></td>(.*)", part, re.S)
        if not m:
            continue
        role, role_txt, country, pid, name, rest = m.groups()
        cells = re.findall(r"<td class='text-center'>(.*?)</td>", rest, re.S)[:5]
        vals = []
        for c in cells:
            mm = re.search(r"line-height:20px'>([^<]*)</span>", c)
            vals.append(text(mm.group(1)) if mm else text(c))
        vals += [None] * (5 - len(vals))
        champs = [dict(champ=html.unescape(a), games=int(g), wr=pct(w), kda=num(k)) for a, w, k, g in re.findall(
            r"<img[^>]*alt='([^']*)'[^>]*/>\s*<span>\s*<strong>[^<]*</strong><br/>\s*Winrate : ([\d.]+)%<br/>\s*KDA : ([\d.]+|-)\s*</span>\s*</a><br/>\s*(\d+)</span>",
            rest, re.S)]
        champs.sort(key=lambda x: (-x["games"], -(x["wr"] or 0)))
        players.append(dict(role=role, player=html.unescape(name), pid=pid, country=country, status=status,
                            kda=num(vals[0]), kp_pct=pct(vals[1]), vspm=num(vals[2]), dmg_pct=pct(vals[3]),
                            gold_pct=pct(vals[4]), games=sum(c["games"] for c in champs), n_champs=len(champs), champs=champs))
    return players, cols


def parse_tournaments(page):
    sel = re.search(r"<select[^>]*cbtournament[^>]*>(.*?)</select>", page, re.S)
    return [html.unescape(v) for v in re.findall(r"option value='([^']*)'", sel.group(1)) if v != "ALL"] if sel else []


# ----------------------------------------------------------------------------------------------- draft page

def parse_draft_header(page):
    out = {}
    m = re.search(r"# Games</div>\s*<div[^>]*>\s*(\d+)", page)
    if not m:
        m = re.search(r"# Games\s*(?:<[^>]+>\s*)*(\d+)", page)
    out["games"] = int(m.group(1)) if m else None
    seg = page[page.find("# Games"):page.find("# Games") + 3000]
    m = re.search(r"Win Rate.*?([\d.]+)%", seg, re.S)
    out["wr_pct"] = pct(m.group(1)) if m else None
    m = re.search(r"Average Game Duration\s*(?:<[^>]+>\s*)*(\d+:\d\d)", seg, re.S)
    out["avg_game_time"] = m.group(1) if m else None
    return out


def parse_role_priority(page):
    i = page.find("Role priority</th>")
    if i < 0:
        return None
    seg = page[i:page.find("</table>", i)]
    return {role: num(v) for role, v in re.findall(r"role/(\w+)\.png'/>\s*\w+<br/>([\d.]+)", seg)}


def parse_icon_count_table(page, header, icons):
    """'First Picked' / 'Last Picked' / 'Banned by X' / 'Banned Against X' -> [(champ, count)], plus whether truncated."""
    m = re.search(r"<th[^>]*>%s</th>" % re.escape(header), page)
    if not m:
        return None
    i = m.start()
    seg = page[i:page.find("</table>", i)]
    rows = [dict(champ=icons.get(fn, fn), n=int(n)) for fn, n in re.findall(r"champions_icon/([^'/]+)\.png'/><br/>(\d+)", seg)]
    return dict(rows=rows, truncated="...</div>" in seg)


def parse_draft_games(page):
    """Per-game draft log -> list of games with both teams' 20 draft slots."""
    games = []
    pat = re.compile(r"<a href='\.\./game/stats/(\d+)/page-game/' title='[^']*'>([^<]*)</a></td><td>([^<]*)</td>"
                     r"<td class='text-center'><span class='(text_victory|text_defeat)'>([^<]*)</span></td><td><table>(.*?)</table>", re.S)
    for gid, title, stage, cls, res, body in pat.findall(page):
        teams = []
        for m in re.finditer(r"<tr><td width='100px'><img[^>]*alt='(Blue|Red) Side'[^>]*/>\s*([^<]*)</td>(.*?)(?=<tr><td width='100px'|$)", body, re.S):
            side, code, cells_html = m.group(1), m.group(2).strip(), m.group(3)
            cells = re.findall(r"<td>(.*?)</td>", cells_html, re.S)
            slots = []
            for c in cells:
                mm = re.search(r"champions_icon/([^'/]+)\.png", c)
                if not mm:
                    slots.append(None)
                else:
                    slots.append((mm.group(1), "ban" if "grayscale" in c else "pick"))
            teams.append(dict(side=side[0], code=code, slots=slots))
        res_code, res_word = res.strip().rsplit(" ", 1)
        games.append(dict(game_id=gid, title=html.unescape(title), stage=stage.strip(), result_code=res_code,
                          win=(res_word == "WIN"), teams=teams))
    return games


def derive_from_draft(games, icons, notes, where):
    """Team-level picks / bans / opponent picks with win rates and pick numbers from the per-game draft log."""
    pk = defaultdict(lambda: dict(games=0, wins=0, blue=0, red=0, slots=[], n_first=0, n_last=0, n_phase1=0))
    bb = defaultdict(lambda: dict(n=0, blue=0, red=0, n_phase1=0, n_first_ban=0))
    ba = defaultdict(lambda: dict(n=0, blue=0, red=0, n_phase1=0))
    opp = defaultdict(lambda: dict(games=0, wins_vs=0))
    n_games, n_blue, n_red, blue_w, red_w, bad, no_order, odd = 0, 0, 0, 0, 0, 0, 0, 0
    opp_codes = Counter()
    for g in games:
        own = [t for t in g["teams"] if t["code"] == g["result_code"]]
        other = [t for t in g["teams"] if t["code"] != g["result_code"]]
        if len(own) != 1 or len(other) != 1:
            bad += 1
            continue
        own, other = own[0], other[0]
        ordered = len(own["slots"]) == 20 and len(other["slots"]) == 20
        if not ordered:
            no_order += 1
            if len(own["slots"]) != 15 or len(other["slots"]) != 15:
                odd += 1
        opp_codes[other["code"]] += 1
        n_games += 1
        side = own["side"]
        if side == "B":
            n_blue += 1
            blue_w += g["win"]
        else:
            n_red += 1
            red_w += g["win"]
        first_row = g["teams"][0] is own
        pick_no, ban_no = 0, 0
        for idx, cell in enumerate(own["slots"]):
            if cell is None:
                continue
            fn, kind = cell
            ch = icons.get(fn, fn)
            if ordered and (SLOT_KIND[idx] != kind or (idx in FIRST_ROW_SLOTS) != first_row):
                odd += 1
            if kind == "pick":
                pick_no += 1
                d = pk[ch]
                d["games"] += 1
                d["wins"] += g["win"]
                d["blue" if side == "B" else "red"] += 1
                if ordered:
                    d["slots"].append(pick_no)
                    d["n_first"] += pick_no == 1
                    d["n_last"] += pick_no == 5
                    d["n_phase1"] += idx < 12
            else:
                ban_no += 1
                d = bb[ch]
                d["n"] += 1
                d["blue" if side == "B" else "red"] += 1
                if ordered:
                    d["n_phase1"] += idx < 6
                    d["n_first_ban"] += ban_no == 1
                elif len(own["slots"]) == 15:
                    d["n_phase1"] += idx < 6
                    d["n_first_ban"] += ban_no == 1
        for idx, cell in enumerate(other["slots"]):
            if cell is None:
                continue
            fn, kind = cell
            ch = icons.get(fn, fn)
            if kind == "ban":
                d = ba[ch]
                d["n"] += 1
                d["blue" if side == "B" else "red"] += 1   # side = OUR side when the opponent banned it
                if ordered or len(other["slots"]) == 15:
                    d["n_phase1"] += idx < 6
            else:
                d = opp[ch]
                d["games"] += 1
                d["wins_vs"] += g["win"]
    if bad:
        notes.append(f"{where}: {bad} draft-log game(s) skipped (could not identify the team's row)")
    if no_order:
        notes.append(f"{where}: {no_order} game(s) have no pick-order data on gol.gg (15-cell rows); their picks/bans are "
                     f"counted but excluded from avg_pick_no / n_first_pick / n_last_pick / n_phase1 (see n_order_known)")
    if odd:
        notes.append(f"{where}: {odd} draft-log row(s)/cell(s) did not match the expected layout")
    picks = sorted((dict(champ=c, games=d["games"], wins=d["wins"], wr=r1(100 * d["wins"] / d["games"]),
                         blue=d["blue"], red=d["red"], n_order_known=len(d["slots"]),
                         avg_pick_no=round(sum(d["slots"]) / len(d["slots"]), 2) if d["slots"] else None,
                         n_first_pick=d["n_first"], n_last_pick=d["n_last"], n_phase1=d["n_phase1"])
                    for c, d in pk.items()), key=lambda x: (-x["games"], -x["wr"], x["champ"]))
    bans_by = sorted((dict(champ=c, n=d["n"], rate=r1(100 * d["n"] / n_games), blue=d["blue"], red=d["red"],
                           n_phase1=d["n_phase1"], n_first_ban=d["n_first_ban"]) for c, d in bb.items()),
                     key=lambda x: (-x["n"], x["champ"]))
    bans_against = sorted((dict(champ=c, n=d["n"], rate=r1(100 * d["n"] / n_games), when_team_blue=d["blue"],
                                when_team_red=d["red"], n_phase1=d["n_phase1"]) for c, d in ba.items()),
                          key=lambda x: (-x["n"], x["champ"]))
    picked_against = sorted((dict(champ=c, games=d["games"], team_wins_vs=d["wins_vs"],
                                  team_wr_vs=r1(100 * d["wins_vs"] / d["games"])) for c, d in opp.items()),
                            key=lambda x: (-x["games"], x["champ"]))
    presence = {}
    for p in picks:
        presence[p["champ"]] = presence.get(p["champ"], 0) + p["games"]
    for b in bans_by:
        presence[b["champ"]] = presence.get(b["champ"], 0) + b["n"]
    for b in bans_against:
        presence[b["champ"]] = presence.get(b["champ"], 0) + b["n"]
    presence = sorted((dict(champ=c, n=n, rate=r1(100 * n / n_games)) for c, n in presence.items()),
                      key=lambda x: (-x["n"], x["champ"]))
    return dict(games=n_games, blue_games=n_blue, red_games=n_red, blue_wins=blue_w, red_wins=red_w,
                opponents=dict(opp_codes.most_common()), picks=picks, bans_by=bans_by, bans_against=bans_against,
                picked_against=picked_against, presence=presence)


# ----------------------------------------------------------------------------------------------- per team / split

def scrape_split(code, name, tid, split, icons, raw_dir, notes):
    where = f"{code} split-{split}"
    stats_url = STATS_URL.format(tid=tid, split=split)
    draft_url = DRAFT_URL.format(tid=tid, split=split)
    sp = fetch(stats_url, raw_dir, f"{code}_{split}_stats.html")
    dp = fetch(draft_url, raw_dir, f"{code}_{split}_draft.html")
    icons.update(icon_map_from(sp))
    title_team = page_title_team(sp)
    if title_team != name:
        notes.append(f"{where}: page title team {title_team!r} != expected {name!r}")
    hdr = parse_header(sp)
    blocks = parse_stat_blocks(sp)
    stats = normalise_stats(blocks, notes, where)
    bans = parse_ban_tables(sp, name)
    wr_labels, wr_data = parse_chart(sp, "WRData")
    dr_labels, dr_data = parse_chart(sp, "dragonData")
    players, player_cols = parse_players(sp)
    dh = parse_draft_header(dp)
    role_prio = parse_role_priority(dp)
    games = parse_draft_games(dp)
    dcode = Counter(g["result_code"] for g in games).most_common(1)
    golgg_code = dcode[0][0] if dcode else None
    derived = derive_from_draft(games, icons, notes, where) if games else None

    wins, losses = hdr["wins"], hdr["losses"]
    total = (wins or 0) + (losses or 0)
    side = None
    if wr_data and "Wins" in wr_data and "Losses" in wr_data and wr_labels == ["Blue Side", "Red Side"]:
        bw, rw = wr_data["Wins"]
        bl, rl = wr_data["Losses"]
        side = dict(blue=dict(games=bw + bl, wins=bw, losses=bl, wr=r1(100 * bw / (bw + bl)) if bw + bl else None),
                    red=dict(games=rw + rl, wins=rw, losses=rl, wr=r1(100 * rw / (rw + rl)) if rw + rl else None))
        if bw + bl + rw + rl != total:
            notes.append(f"{where}: blue+red games {bw + bl + rw + rl} != record games {total}")
    else:
        notes.append(f"{where}: side win-rate chart missing")
    dragons = None
    if dr_data:
        dragons = {lab: dict(killed=k, lost=l) for lab, k, l in
                   zip(dr_labels, dr_data.get("Dragons killed", []), dr_data.get("Dragons lost", []))}
    if total == 0:
        notes.append(f"{where}: no games (empty page)")
    if dh["games"] is not None and dh["games"] != total:
        notes.append(f"{where}: draft tab counts {dh['games']} games but the stats page record has {total}")
    if derived and derived["games"] != total:
        notes.append(f"{where}: draft log holds {derived['games']} of the {total} games (gol.gg has no draft for the "
                     f"rest); derived pick/ban rates use the draft-log game count")
    if derived and side and (derived["blue_games"], derived["red_games"]) != (side["blue"]["games"], side["red"]["games"]):
        notes.append(f"{where}: draft-log side split {derived['blue_games']}/{derived['red_games']} != chart "
                     f"{side['blue']['games']}/{side['red']['games']}")
    for kind in ("by", "against"):
        if not bans.get(kind):
            notes.append(f"{where}: 'Most banned champions {kind}' table missing")
    page_tables = dict(
        banned_by_pct=bans.get("by"), banned_against_pct=bans.get("against"),
        role_priority=role_prio,
        first_picked=parse_icon_count_table(dp, "First Picked", icons),
        last_picked=parse_icon_count_table(dp, "Last Picked", icons),
        banned_by_count=parse_icon_count_table(dp, f"Banned by {golgg_code}", icons) if golgg_code else None,
        banned_against_count=parse_icon_count_table(dp, f"Banned Against {golgg_code}", icons) if golgg_code else None,
    )
    for k in ("role_priority", "first_picked", "last_picked", "banned_by_count", "banned_against_count"):
        if page_tables[k] is None:
            notes.append(f"{where}: draft tab table {k} not found")
    # cross-check: draft-tab ban counts (top 10) vs counts derived from the draft log
    if derived and page_tables["banned_by_count"]:
        d = {b["champ"]: b["n"] for b in derived["bans_by"]}
        diff = [(r["champ"], r["n"], d.get(r["champ"])) for r in page_tables["banned_by_count"]["rows"] if d.get(r["champ"]) != r["n"]]
        if diff:
            notes.append(f"{where}: ban counts on draft tab differ from draft log for {diff}")
    return dict(
        urls=dict(stats=stats_url, draft=draft_url), region=hdr["region"], season=hdr["season"],
        games=total, wins=wins, losses=losses, record=f"{wins}W-{losses}L" if wins is not None else None,
        wr=r1(100 * wins / total) if total else None, wr_page_pct=hdr["wr_page_pct"], wr_draft_tab_pct=dh["wr_pct"],
        avg_game_time=hdr["avg_game_time"], avg_game_min=mmss_to_min(hdr["avg_game_time"]) if hdr["avg_game_time"] else None,
        side=side, stats=stats, stats_raw=blocks, dragons_by_type=dragons,
        draft=dict(golgg_code=golgg_code, role_priority=role_prio,
                   picks=derived["picks"] if derived else None, bans_by=derived["bans_by"] if derived else None,
                   bans_against=derived["bans_against"] if derived else None,
                   picked_against=derived["picked_against"] if derived else None,
                   presence=derived["presence"] if derived else None,
                   opponents=derived["opponents"] if derived else None,
                   n_games_in_log=derived["games"] if derived else 0),
        page_tables=page_tables,
        players=players, player_table_columns=player_cols,
        games_log=[dict(game_id=g["game_id"], title=g["title"], stage=g["stage"], win=g["win"],
                        side=next((t["side"] for t in g["teams"] if t["code"] == g["result_code"]), None),
                        opponent=next((t["code"] for t in g["teams"] if t["code"] != g["result_code"]), None),
                        picks=[icons.get(c[0], c[0]) for t in g["teams"] if t["code"] == g["result_code"]
                               for c in t["slots"] if c and c[1] == "pick"],
                        bans=[icons.get(c[0], c[0]) for t in g["teams"] if t["code"] == g["result_code"]
                              for c in t["slots"] if c and c[1] == "ban"],
                        opp_picks=[icons.get(c[0], c[0]) for t in g["teams"] if t["code"] != g["result_code"]
                                   for c in t["slots"] if c and c[1] == "pick"],
                        opp_bans=[icons.get(c[0], c[0]) for t in g["teams"] if t["code"] != g["result_code"]
                                  for c in t["slots"] if c and c[1] == "ban"]) for g in games],
    ), parse_tournaments(sp)


def summary_line(code, t):
    s = t["splits"].get("ALL") or next(iter(t["splits"].values()))
    sd = s.get("side") or {}
    b, r = sd.get("blue", {}), sd.get("red", {})
    top = ", ".join(f"{p['champ']} {p['games']}g {p['wr']}%" for p in (s["draft"]["picks"] or [])[:3])
    ba = ", ".join(f"{p['champ']} {p['n']}" for p in (s["draft"]["bans_against"] or [])[:3])
    parts = [f"{code:5} {s['record'] or '-':9} {s['wr']}%", f"blue {b.get('wins')}-{b.get('losses')} ({b.get('wr')}%)",
             f"red {r.get('wins')}-{r.get('losses')} ({r.get('wr')}%)"]
    for sp, x in t["splits"].items():
        if sp != "ALL":
            parts.append(f"{sp} {x['record']}")
    return " | ".join(parts) + f"\n      picks: {top}\n      banned vs: {ba}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="ALL,Summer", help="comma list of gol.gg S16 splits (default ALL,Summer)")
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--raw-dir", default=RAW_DIR_DEFAULT, help="directory for raw HTML copies ('' to skip)")
    args = ap.parse_args()
    splits = []
    for s in args.split.split(","):
        sp = SPLIT_ALIAS.get(s.strip().lower())
        if sp is None:
            sys.exit(f"unknown split {s!r}; gol.gg S16 splits: {', '.join(SPLITS)}")
        splits.append(sp)
    raw_dir = args.raw_dir or None
    if raw_dir:
        os.makedirs(raw_dir, exist_ok=True)

    notes = []
    print("fetching S16 team list")
    tlist = parse_team_list(fetch(LIST_URL, raw_dir, "team_list_S16.html"))
    print(len(tlist), "teams listed for S16")
    print("fetching champion list (icon -> name map)")
    icons = icon_map_from(fetch(CHAMP_LIST_URL, raw_dir, "champion_list_S16.html"))
    print(len(icons), "champion icons mapped")

    out = {}
    for code, (name, known) in TEAMS.items():
        listed = tlist.get(name)
        if listed is None:
            cands = {k: v for k, v in tlist.items() if name.lower() in k.lower()}
            notes.append(f"{code}: {name!r} not on the S16 list page exactly; candidates {cands}; using known id {known}")
            tid = known
        else:
            tid = listed
            if known is not None and str(known) != str(listed):
                notes.append(f"{code}: list page id {listed} differs from known id {known}; using list page id")
            elif known is None:
                notes.append(f"{code}: id {listed} resolved from the S16 list page ({name})")
        if tid is None:
            notes.append(f"{code}: no team id, skipped")
            continue
        team = dict(name=name, golgg_id=int(tid), splits={})
        for sp in splits:
            print(f"{code} {name} id {tid} split-{sp}")
            try:
                team["splits"][sp], tours = scrape_split(code, name, tid, sp, icons, raw_dir, notes)
            except Exception as e:  # keep going, report
                notes.append(f"{code} split-{sp}: FAILED {type(e).__name__}: {e}")
                team["splits"][sp] = None
                continue
            if sp == "ALL" or "tournaments_in_dropdown" not in team:
                team["tournaments_in_dropdown"] = tours
            x = team["splits"][sp]
            print(f"   {x['record']} {x['wr']}% | blue {x['side']['blue']['wr'] if x['side'] else None}% red "
                  f"{x['side']['red']['wr'] if x['side'] else None}% | {len(x['draft']['picks'] or [])} champs picked, "
                  f"{len(x['players'])} players, {x['draft']['n_games_in_log']} games in draft log")
        out[code] = team

    # -------- verification
    for code, t in out.items():
        for sp, x in t["splits"].items():
            if x is None:
                continue
            w = f"{code} split-{sp}"
            if x["games"] == 0:
                continue
            if not (0 <= (x["wr"] or 0) <= 100):
                notes.append(f"{w}: win rate out of range {x['wr']}")
            picks = x["draft"]["picks"] or []
            if any(picks[i]["games"] < picks[i + 1]["games"] for i in range(len(picks) - 1)):
                notes.append(f"{w}: picks not sorted by games desc")
            short = [g["title"] for g in x["games_log"] if len(g["picks"]) != 5 or len(g["opp_picks"]) != 5]
            deficit = sum(5 - len(g["picks"]) for g in x["games_log"])
            if picks and sum(p["games"] for p in picks) != 5 * x["draft"]["n_games_in_log"] - deficit:
                notes.append(f"{w}: pick total {sum(p['games'] for p in picks)} != 5 x {x['draft']['n_games_in_log']} games")
            missing = [k for k, v in x["stats"].items() if v is None]
            if missing:
                notes.append(f"{w}: null stats {missing} (gol.gg prints '-' for them on this page)")
            if short:
                notes.append(f"{w}: {len(short)} game(s) in the draft log show fewer than 5 picks for a team on gol.gg "
                             f"(incomplete data there): {short}")
            lineup = [p for p in x["players"] if p["status"] == "Last line-up"]
            if len(lineup) != 5:
                notes.append(f"{w}: 'Last line-up' has {len(lineup)} players, not 5")

    labels = {}
    for t in out.values():
        for x in t["splits"].values():
            if x:
                for blk, rows in x["stats_raw"].items():
                    for lab in rows:
                        labels.setdefault(blk, [])
                        if lab not in labels[blk]:
                            labels[blk].append(lab)
    general = [
        "Team ids are per season on gol.gg (team-stats URLs carry no season segment); every id was taken from or checked "
        "against the season-S16 list page and each page title was checked to read '<team> stats in S16' / 'in <split> Split (S16)'.",
        "gol.gg's stats page has no team-level 'most picked champions' table. draft.picks / bans_by / bans_against / "
        "picked_against / presence are derived from the per-game draft log on the team's Draft tab (20 draft slots per "
        "team per game; grayscale icon = ban, colour icon = pick); the tab's own top-10 count tables (First Picked, Last "
        "Picked, Banned by/Against <code>) are kept verbatim under page_tables and agree with the derived counts.",
        "Pick numbering: avg_pick_no / n_first_pick / n_last_pick count the team's own picks 1-5 in draft order "
        "(1 = the team's first pick of the game, 5 = its last pick); n_phase1 = picked in the first pick phase (3 of 5 picks). "
        "gol.gg's log orders the two rows by the game title, not by side, so only each team's own order is used, never the "
        "blue/red interleaving. Games whose draft shows no pick order on gol.gg (15-cell rows) count toward games/wins/bans "
        "but not toward the order metrics; n_order_known says how many of a champion's games had order data.",
        "page_tables.banned_by_pct / banned_against_pct are the stats page's top-6 tables; Overall % is the share of all the "
        "team's games, and the Blue Side / Red Side rows are also expressed as a share of ALL games (they sum to Overall), "
        "not of games on that side.",
        "stats.dragon_share_pct / herald_share_pct / baron_share_pct are the unlabeled percentages gol.gg prints in "
        "parentheses after 'Dragons / game', 'Herald / game', 'Nashors / game'; they match the team's share of that "
        "objective (taken / (taken + conceded)). gol.gg's team page gives NO first-dragon, first-herald or first-baron "
        "rate; those are null (not present).",
        "First Tower, First Blood and 'Win Rate when ahead at 15 min' are percentages (0-100). Game time is 'mm:ss' plus "
        "avg_game_min as decimal minutes.",
        "Champion names are gol.gg display names exactly as shown in img alt text (KSante, Kaisa, RekSai, Chogath, KogMaw, "
        "KhaZix, LeBlanc, Lee Sin, Jarvan IV, Wukong, Dr. Mundo...), the same spellings as data/golgg_players_2026.json.",
        "players = the '<team> player's stats' table (status 'Last line-up' = current five, 'Subs' = everyone else who "
        "played); per-player champs carry games / wr / kda from the hover text, games = sum of the player's champion games.",
        "tournaments_in_dropdown is the stats page's tournament filter list, which gol.gg does not filter by split, so it "
        "is the team's season-wide event list.",
        "Not present on gol.gg team pages (null / absent): first dragon, first herald, first baron rates, team KDA, "
        "per-side average game time, team-level 'most picked' table, pick-priority per champion beyond the derived pick numbers.",
    ]
    doc = dict(
        source=dict(list_url=LIST_URL, stats_url=STATS_URL, draft_url=DRAFT_URL, champion_list_url=CHAMP_LIST_URL,
                    season=SEASON, splits=splits, scope="2026 season (gol.gg S16), tournament-ALL per split",
                    accessed=dt.date.today().strftime("%d/%m/%Y"), stats_page_labels=labels,
                    draft_tab_tables=["Role priority", "First Picked", "Last Picked", "Banned by <code>",
                                      "Banned Against <code>", "per-game draft log"]),
        notes=general + notes, teams=out)
    with open(args.out, "w") as f:
        json.dump(doc, f, indent=1)

    print("\n=== summary (split-ALL; other splits as records) ===")
    for code, t in out.items():
        print(summary_line(code, t))
    print("\n=== notes ===")
    print("\n".join(notes) if notes else "(none)")
    print("wrote", args.out, "-", len(out), "teams")


if __name__ == "__main__":
    main()
