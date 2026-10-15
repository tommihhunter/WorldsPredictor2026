#!/usr/bin/env python3
"""
Pull finished Worlds 2026 series from gol.gg and merge them into data/results_live.json
(the file the Scorecard tab and model/grade.py grade against).

Usage
  python3 model/update_results.py --dry-run            # show what would change, write nothing
  python3 model/update_results.py                      # merge and write data/results_live.json
  python3 model/update_results.py --overwrite          # let gol.gg replace a conflicting hand-entered result
  python3 model/update_results.py --page "Worlds 2026 Play-In=/path/saved.html" --results /tmp/x.json
                                                       # offline: parse saved pages, write elsewhere (tests)

Source pages (configurable in TOURNAMENTS below or with --tournament NAME=PHASE):
  https://gol.gg/tournament/tournament-matchlist/Worlds%202026%20Play-In/     stage labels ROUND1 ...
  https://gol.gg/tournament/tournament-matchlist/Worlds%202026%20Main%20Event/ ROUND1-5 (Swiss),
                                                   QUARTERFINALS, SEMIFINALS, FINALS (Knockouts)
Only the series score is on the match list (no per-game rows); the per-series summary page
link is recorded in source.series_url and is not scraped.

Row written (kind "series"):
  {id, phase: Play-In|Swiss|Knockouts, kind, stage, golgg_stage, round (Swiss only), date dd/mm/yyyy,
   start_nz (kept if hand-entered, else null), team_a, team_b, score_a, score_b, winner, bo, patch,
   source: {url, series_url, accessed}}
Ids: Play-In PI-R1-A / PI-R1-B by team pair, PI-WM / PI-EM / PI-LF / PI-GF by bracket logic from the
R1 results; Swiss SW-R<n>-<A>-<B>; Knockouts KO-F for the final, otherwise an existing row with the
same phase and team pair (e.g. a hand-made KO-QF1), else KO-QF-<A>-<B> / KO-SF-<A>-<B>.
Swiss bo: rounds 1-2 Bo1; round 3 Bo3 when both teams are 2-0 or both 0-2 (from the earlier rows),
Bo1 otherwise; rounds 4-5 Bo3. A series counts as finished only when one side has the wins the
inferred bo needs, so an in-progress Bo3 at 1-0 is skipped. Teams that reach 3 wins or 3 losses
also get a {"kind": "swiss_record", "team", "record"} row (grade.py reads those).

Idempotent: rows are compared ignoring source.accessed; when nothing changes the file is not
rewritten. Hand-entered fields (start_nz, notes, team order) are never overwritten, and a row that
already has a different winner/score is left alone unless --overwrite is given.
"""
import argparse, copy, datetime as dt, hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_PATH = os.path.join(ROOT, "data", "results_live.json")
UA = {"User-Agent": "Mozilla/5.0"}
NZ = dt.timezone(dt.timedelta(hours=13))  # NZDT; the project uses fixed +13 through the event

# gol.gg tournament name -> which phases it holds ("Play-In", or "Main" = Swiss + Knockouts)
TOURNAMENTS = {
    "Worlds 2026 Play-In": "Play-In",
    "Worlds 2026 Main Event": "Main",
}

# Play-In round 1 slots (team pairs are unordered)
PLAYIN_R1 = {"PI-R1-A": ("KC", "C9"), "PI-R1-B": ("FURIA", "MVK")}
PLAYIN_STAGE = {"PI-R1-A": "Play-In R1", "PI-R1-B": "Play-In R1", "PI-WM": "Play-In winners' match",
                "PI-EM": "Play-In elimination match", "PI-LF": "Play-In lower final", "PI-GF": "Play-In final"}
KO_STAGE = {"QUARTERFINALS": ("QF", "Quarterfinal"), "SEMIFINALS": ("SF", "Semifinal"), "FINALS": ("F", "Final")}

# gol.gg team name -> code (the 19 Worlds teams; aliases cover gol.gg's spelling drift)
CODES = {
    "Anyone s Legend": "AL", "Anyone's Legend": "AL", "Bilibili Gaming": "BLG", "Top Esports": "TES",
    "Invictus Gaming": "IG", "Gen.G": "GEN", "Gen.G eSports": "GEN", "Gen.G Esports": "GEN",
    "Hanwha Life Esports": "HLE", "Hanwha Life eSports": "HLE", "T1": "T1", "Dplus KIA": "DK",
    "G2 Esports": "G2", "Movistar KOI": "MKOI", "Karmine Corp": "KC", "Team Liquid": "TLAW",
    "Team Liquid Honda": "TLAW", "LYON": "LYON", "Cloud9": "C9", "Team Secret Whales": "TSW",
    "CTBC Flying Oyster": "CFO", "MVK Esports": "MVK", "Los Grandes": "LOS", "FURIA": "FURIA", "FURIA Esports": "FURIA",
}
SHORT = {"KC": "KC", "C9": "C9", "FURIA": "FURIA", "MVK": "MVK", "GEN": "GEN", "AL": "AL", "TLAW": "TLAW", "TL": "TLAW",
         "G2": "G2", "LOS": "LOS", "TSW": "TSW", "HLE": "HLE", "BLG": "BLG", "LYON": "LYON", "MKOI": "MKOI", "T1": "T1",
         "TES": "TES", "CFO": "CFO", "IG": "IG", "DK": "DK"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


_NORM = {norm(k): v for k, v in CODES.items()}


def code_of(name):
    if name in CODES:
        return CODES[name]
    if name in SHORT:
        return SHORT[name]
    return _NORM.get(norm(name))


# ---------------------------------------------------------------- fetch / parse
def matchlist_url(name):
    return "https://gol.gg/tournament/tournament-matchlist/" + urllib.parse.quote(name) + "/"


def fetch(name):
    url = matchlist_url(name)
    req = urllib.request.Request(url, headers=UA)
    err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(2 + attempt * 3)
    raise err


CELL = re.compile(r"<td([^>]*)>(.*?)</td>", re.S)
SCORE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


def parse(page):
    """Series rows from a gol.gg match list, in page order (newest first).
    score_a/score_b are None for an unplayed row (' - ')."""
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = CELL.findall(tr)
        if len(cells) < 7:
            continue
        attrs = [a for a, _ in cells]
        text = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for _, c in cells]
        try:
            d = dt.datetime.strptime(text[6], "%Y-%m-%d").date()
        except ValueError:
            continue
        m = SCORE.match(text[2])
        sa, sb = (int(m[1]), int(m[2])) if m else (None, None)
        link = re.search(r"href=['\"]([^'\"]*?/game/stats/(\d+)/[^'\"]*)['\"]", cells[0][1])
        series_url = None
        if link:
            series_url = "https://gol.gg/game/stats/%s/page-summary/" % link.group(2)
        victory = "text_victory" in attrs[1] and "a" or ("text_victory" in attrs[3] and "b" or None)
        out.append(dict(team_a=text[1], team_b=text[3], score_a=sa, score_b=sb, stage=text[4].strip().upper(),
                        patch=text[5].strip() or None, date=d.strftime("%d/%m/%Y"), iso_date=d.isoformat(),
                        series_url=series_url, golgg_victory=victory))
    return out


# ---------------------------------------------------------------- classification
def swiss_round(stage):
    m = re.match(r"^ROUND\s*(\d+)$", stage)
    return int(m[1]) if m else None


def phase_of(kind, stage):
    if kind == "Play-In" or stage.startswith("PLAY"):
        return "Play-In"
    if stage in KO_STAGE:
        return "Knockouts"
    return "Swiss"


def pair(a, b):
    return tuple(sorted((a, b)))


def finished(sa, sb, bo):
    need = bo // 2 + 1
    if sa is None or sb is None:
        return False
    if sa >= need and sb >= need:
        return False
    return max(sa, sb) == need


# ---------------------------------------------------------------- build candidate rows
def build_rows(scraped, existing, log, trust_victory=False):
    """scraped: list of (tournament, kind, url, parsed_row). Returns list of new/updated series rows (with ids)
    plus swiss_record rows. Chronological processing drives the Play-In bracket and Swiss bo inference."""
    items = []
    for ti, (tname, kind, url, rows) in enumerate(scraped):
        n = len(rows)
        for i, r in enumerate(rows):
            a, b = code_of(r["team_a"]), code_of(r["team_b"])
            if not a or not b:
                log(f"SKIP unmapped team name(s) {r['team_a']!r} / {r['team_b']!r} ({tname} {r['stage']}); add to CODES")
                continue
            ph = phase_of(kind, r["stage"])
            rnd = swiss_round(r["stage"]) if ph == "Swiss" else None
            # page is newest-first; (date, round, reversed page index) gives chronological order
            items.append((r["iso_date"], rnd or 0, ti, n - i, dict(r, a=a, b=b, phase=ph, round=rnd, tournament=tname, url=url)))
    items.sort(key=lambda x: x[:4])

    out, records = [], {}
    # ---- Play-In bracket state
    slots = {}      # slot id -> dict(winner, loser, pair)
    confirmed = set()  # slots filled from gol.gg in this run (seeded ones may still be confirmed/updated)
    exist_by_id = {r["id"]: r for r in existing if r.get("kind") == "series" and r.get("id")}
    for sid in PLAYIN_STAGE:  # hand-entered Play-In results already in the file seed the bracket
        e = exist_by_id.get(sid)
        if e and e.get("winner") and e.get("team_a") and e.get("team_b"):
            slots[sid] = dict(winner=e["winner"], loser=e["team_b"] if e["winner"] == e["team_a"] else e["team_a"],
                              pair=pair(e["team_a"], e["team_b"]))
    SLOT_ROUND = {"PI-R1-A": 1, "PI-R1-B": 1, "PI-WM": 2, "PI-EM": 2, "PI-LF": 3, "PI-GF": 4}

    def expected_pairs():
        exp = {k: pair(*v) for k, v in PLAYIN_R1.items()}
        ra, rb = slots.get("PI-R1-A"), slots.get("PI-R1-B")
        if ra and rb:
            exp["PI-WM"] = pair(ra["winner"], rb["winner"])
            exp["PI-EM"] = pair(ra["loser"], rb["loser"])
        wm, em = slots.get("PI-WM"), slots.get("PI-EM")
        if wm and em:
            exp["PI-LF"] = pair(wm["loser"], em["winner"])
        lf = slots.get("PI-LF")
        if wm and lf:
            exp["PI-GF"] = pair(wm["winner"], lf["winner"])
        return exp

    # ---- Swiss state (records from finished rows, including hand-entered ones already in the file)
    wins, losses = {}, {}
    for e in existing:
        if e.get("kind") == "series" and e.get("phase") == "Swiss" and e.get("winner"):
            loser = e["team_b"] if e["winner"] == e["team_a"] else e["team_a"]
            wins[e["winner"]] = wins.get(e["winner"], 0) + 1
            losses[loser] = losses.get(loser, 0) + 1
    seen_swiss = {(e.get("round"), pair(e["team_a"], e["team_b"])) for e in existing
                  if e.get("kind") == "series" and e.get("phase") == "Swiss" and e.get("winner")}
    rec = lambda t: (wins.get(t, 0), losses.get(t, 0))

    for _, _, _, _, r in items:
        a, b, ph, sa, sb = r["a"], r["b"], r["phase"], r["score_a"], r["score_b"]
        score = "unplayed" if sa is None else f"{sa}-{sb}"
        label = f"{r['tournament']} {r['stage']} {a} {score} {b} ({r['date']})"
        if sa is None:
            log(f"skip unplayed: {label}")
            continue
        # ---- bo
        if ph in ("Play-In", "Knockouts"):
            bo = 5
        else:
            rnd = r["round"]
            if rnd in (1, 2):
                bo = 1
            elif rnd == 3:
                ra, rb = rec(a), rec(b)
                if ra == rb and ra in ((2, 0), (0, 2)):
                    bo = 3
                elif ra == rb == (1, 1):
                    bo = 1
                else:
                    bo = 3 if max(sa, sb) >= 2 else None
            elif rnd and rnd >= 4:
                bo = 3
            else:
                bo = 3 if max(sa, sb) >= 2 else None
            if bo is None:
                if max(sa, sb) == 1 and trust_victory and r["golgg_victory"]:
                    bo = 1
                else:
                    log(f"AMBIGUOUS Swiss bo (records {rec(a)} v {rec(b)}), skipped: {label}  "
                        f"(re-run later, or --trust-golgg-winner if gol.gg marks it final)")
                    continue
        if not finished(sa, sb, bo):
            if r["golgg_victory"] and trust_victory:
                log(f"accepting gol.gg winner flag on incomplete score (Bo{bo}): {label}")
            else:
                extra = " (gol.gg marks a winner; pass --trust-golgg-winner to accept)" if r["golgg_victory"] else ""
                log(f"skip in progress / incomplete for Bo{bo}: {label}{extra}")
                continue
        winner, loser = (a, b) if sa > sb else (b, a)
        if r["golgg_victory"] and {"a": a, "b": b}[r["golgg_victory"]] != winner:
            log(f"WARNING gol.gg victory flag disagrees with score: {label}")

        row = dict(id=None, phase=ph, kind="series", stage=None, golgg_stage=r["stage"], date=r["date"], start_nz=None,
                   team_a=a, team_b=b, score_a=sa, score_b=sb, winner=winner, bo=bo, patch=r["patch"],
                   source=dict(url=r["url"], series_url=r["series_url"]))
        # ---- ids
        if ph == "Play-In":
            exp = expected_pairs()
            cands = [sid for sid, p in exp.items() if p == pair(a, b) and sid not in confirmed]
            lr = swiss_round(r["stage"]) or (4 if r["stage"] == "FINALS" else None)  # round implied by gol.gg's label
            if lr and any(SLOT_ROUND[s] == lr for s in cands):
                cands = [s for s in cands if SLOT_ROUND[s] == lr]
            if not cands:
                log(f"SKIP Play-In series does not fit the bracket (slots so far {sorted(slots)}): {label}")
                continue
            sid = cands[0]
            if len(cands) > 1:
                log(f"WARNING several Play-In slots fit {label}: {cands}; using {sid}")
            if lr and SLOT_ROUND[sid] != lr:
                log(f"WARNING gol.gg label {r['stage']} but bracket logic puts {label} in {sid}")
            slots[sid] = dict(winner=winner, loser=loser, pair=pair(a, b))
            confirmed.add(sid)
            row.update(id=sid, stage=PLAYIN_STAGE[sid])
        elif ph == "Swiss":
            rnd = r["round"]
            key = (rnd, pair(a, b))
            if key in seen_swiss:
                pass  # record already counted from the existing file
            else:
                seen_swiss.add(key)
                wins[winner] = wins.get(winner, 0) + 1
                losses[loser] = losses.get(loser, 0) + 1
            tag = f"R{rnd}" if rnd else re.sub(r"[^A-Z0-9]+", "", r["stage"])
            row.update(id=f"SW-{tag}-{a}-{b}", round=rnd, stage=f"Swiss round {rnd}" if rnd else f"Swiss {r['stage'].title()}")
        else:
            short, name = KO_STAGE[r["stage"]]
            row.update(id="KO-F" if short == "F" else f"KO-{short}-{a}-{b}", stage=name)
        out.append(row)

    for t in sorted(set(wins) | set(losses)):
        w, l = rec(t)
        if w >= 3 or l >= 3:
            records[t] = dict(id=f"SW-REC-{t}", phase="Swiss", kind="swiss_record", team=t, record=f"{w}-{l}")
    return out, list(records.values())


# ---------------------------------------------------------------- merge
def find_existing(existing, row):
    """Existing row for an incoming one. Play-In and the final: by id only (the bracket fixes the id, and a
    rematch must not land on the round-1 row). Swiss: by id, else same round + team pair. QF/SF: by id,
    else a Knockouts row of the same round (id KO-QF* / KO-SF*) with the same team pair."""
    series = [e for e in existing if e.get("kind") == "series"]
    for e in series:
        if e.get("id") == row["id"]:
            return e
    if row["phase"] == "Play-In" or row["id"] == "KO-F":
        return None
    prefix = "KO-" + row["id"].split("-")[1] if row["phase"] == "Knockouts" else None
    for e in series:
        if e.get("phase") != row["phase"]:
            continue
        if pair(e.get("team_a", ""), e.get("team_b", "")) != pair(row["team_a"], row["team_b"]):
            continue
        if row["phase"] == "Swiss" and e.get("round") not in (None, row.get("round")):
            continue
        if prefix and not str(e.get("id", "")).startswith(prefix):
            continue
        return e
    return None


def strip_accessed(r):
    r = copy.deepcopy(r)
    if isinstance(r.get("source"), dict):
        r["source"].pop("accessed", None)
    return r


def merge(existing, incoming, records, accessed, overwrite, log):
    """Returns (new_list, changes). changes: list of (kind, id, detail)."""
    out = copy.deepcopy(existing)
    changes = []
    for row in incoming:
        e = find_existing(out, row)
        if e is None:
            new = dict(row)
            new["source"]["accessed"] = accessed
            out.append(new)
            changes.append(("add", new["id"], f"{new['team_a']} {new['score_a']}-{new['score_b']} {new['team_b']} ({new['stage']}, {new['date']})"))
            continue
        # orient scores to the existing row's team order
        flip = e.get("team_a") == row["team_b"] and e.get("team_b") == row["team_a"]
        sa, sb = (row["score_b"], row["score_a"]) if flip else (row["score_a"], row["score_b"])
        if e.get("winner") and (e.get("winner") != row["winner"] or (e.get("score_a"), e.get("score_b")) != (sa, sb)):
            if not overwrite:
                log(f"CONFLICT {e['id']}: file has {e.get('team_a')} {e.get('score_a')}-{e.get('score_b')} {e.get('team_b')} "
                    f"winner {e.get('winner')}, gol.gg has {row['team_a']} {row['score_a']}-{row['score_b']} {row['team_b']}; "
                    f"kept the file (use --overwrite)")
                continue
            log(f"OVERWRITE {e['id']} from gol.gg")
        upd = dict(score_a=sa, score_b=sb, winner=row["winner"], bo=row["bo"], date=row["date"], patch=row["patch"],
                   golgg_stage=row["golgg_stage"])
        if row.get("round") is not None:
            upd["round"] = row["round"]
        for k in ("phase", "kind", "stage", "team_a", "team_b"):
            if not e.get(k):
                upd[k] = row[k] if not (flip and k in ("team_a", "team_b")) else row[{"team_a": "team_b", "team_b": "team_a"}[k]]
        if "start_nz" not in e:
            upd["start_nz"] = None
        cur_src = {k: v for k, v in e["source"].items() if k != "accessed"} if isinstance(e.get("source"), dict) else {}
        src = dict(cur_src, url=row["source"]["url"], series_url=row["source"]["series_url"])
        before = strip_accessed(e)
        diff = {k: v for k, v in upd.items() if e.get(k) != v}
        if src != cur_src:
            diff["source"] = src
        if not diff:
            continue
        e.update(diff)
        e["source"] = dict(src, accessed=accessed)
        after = strip_accessed(e)
        changed = [k for k in after if before.get(k) != after.get(k)]
        changes.append(("update", e["id"], f"{e['team_a']} {e['score_a']}-{e['score_b']} {e['team_b']} winner {e['winner']}; fields {changed}"))
    # swiss records: keyed on (kind, team)
    for rrow in records:
        e = next((x for x in out if x.get("kind") == "swiss_record" and x.get("team") == rrow["team"]), None)
        if e is None:
            out.append(dict(rrow))
            changes.append(("add", rrow["id"], f"swiss record {rrow['team']} {rrow['record']}"))
        elif e.get("record") != rrow["record"]:
            if e.get("record") and not overwrite:
                log(f"CONFLICT swiss record {rrow['team']}: file {e.get('record')} vs computed {rrow['record']}; kept the file")
                continue
            e["record"] = rrow["record"]
            changes.append(("update", e.get("id") or rrow["id"], f"swiss record {rrow['team']} -> {rrow['record']}"))
    return out, changes


def dump(rows):
    return "[\n " + ",\n ".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n]\n"


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest() if os.path.exists(path) else None


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print the changes, write nothing")
    ap.add_argument("--results", default=RESULTS_PATH, help="results file to merge into (default data/results_live.json)")
    ap.add_argument("--page", action="append", default=[], metavar="NAME=FILE",
                    help="offline: use a saved match-list page for tournament NAME; only listed tournaments are processed")
    ap.add_argument("--tournament", action="append", default=[], metavar="NAME=Play-In|Main",
                    help="override/add a gol.gg tournament name and which phases it holds")
    ap.add_argument("--overwrite", action="store_true", help="let gol.gg replace a conflicting result already in the file")
    ap.add_argument("--trust-golgg-winner", action="store_true",
                    help="accept a series as finished when gol.gg marks a winner even if the score does not complete the inferred bo")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    log = (lambda *a: None) if args.quiet else (lambda *a: print(*a, file=sys.stderr))

    tournaments = dict(TOURNAMENTS)
    for t in args.tournament:
        name, _, kind = t.partition("=")
        tournaments[name] = kind or "Main"
    pages = {}
    for p in args.page:
        name, _, path = p.partition("=")
        pages[name] = open(path, encoding="utf-8").read()
    if pages:
        tournaments = {k: v for k, v in tournaments.items() if k in pages}
        for k in pages:
            tournaments.setdefault(k, "Main")

    existing = json.load(open(args.results, encoding="utf-8")) if os.path.exists(args.results) else []
    before_sha = sha(args.results)

    scraped = []
    for name, kind in tournaments.items():
        url = matchlist_url(name)
        if name in pages:
            page = pages[name]
        else:
            try:
                page = fetch(name)
            except Exception as e:  # noqa: BLE001
                log(f"FETCH FAILED {name}: {e}")
                continue
            time.sleep(0.6)
        rows = parse(page)
        played = [r for r in rows if r["score_a"] is not None]
        log(f"{name}: {len(rows)} listed series, {len(played)} with a score")
        scraped.append((name, kind, url, rows))

    incoming, records = build_rows(scraped, existing, log, trust_victory=args.trust_golgg_winner)
    accessed = dt.datetime.now(NZ).strftime("%d/%m/%Y %H:%M NZDT")
    merged, changes = merge(existing, incoming, records, accessed, args.overwrite, log)

    print(f"finished series found: {len(incoming)}; swiss records: {len(records)}; "
          f"rows in file: {len(existing)} -> {len(merged)}; changes: {len(changes)}")
    for kind, rid, detail in changes:
        print(f"  {kind:<6} {rid:<16} {detail}")
    if not changes:
        print("no changes; file not written")
        return 0
    if args.dry_run:
        print("dry run; file not written")
        return 0
    tmp = args.results + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(dump(merged))
    os.replace(tmp, args.results)
    print(f"wrote {args.results} (sha256 {before_sha and before_sha[:12]} -> {sha(args.results)[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
