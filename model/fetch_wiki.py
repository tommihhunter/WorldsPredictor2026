#!/usr/bin/env python3
"""One-off wiki fetch (run by hand, not by the bot): player profiles and team achievements from Liquipedia
(https://liquipedia.net/leagueoflegends, text under CC BY-SA 3.0, credited on the site).

Players (every starter in data/dash/dossiers.json): the infobox from the page wikitext (native and romanised name,
birth date, country, roles, socials), and from the rendered page the team history, the achievements table and the
awards table. Teams: the achievements table of each Worlds team's page.
Output: data/dash/wiki_players.json, data/dash/wiki_teams.json. Raw pages are cached in dashboard/wiki_cache/
(git-ignored) so a rerun only fetches what is missing.
Liquipedia API rules: a descriptive User-Agent, gzip, at most one parse request per 30 s and one other request per 2 s."""
import datetime, gzip, html, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "dashboard", "wiki_cache"); os.makedirs(CACHE, exist_ok=True)
API = "https://liquipedia.net/leagueoflegends/api.php"
UA = {"User-Agent": "PoroProphet/1.0 (personal fan site poroprophet.lol; github.com/tommihhunter)", "Accept-Encoding": "gzip"}
TODAY = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=13)).strftime("%d/%m/%Y")
last = {"parse": 0.0, "query": 0.0}

def api(params, kind):
    wait = (30 if kind == "parse" else 2) - (time.time() - last[kind])
    if wait > 0: time.sleep(wait)
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode({**params, 'format': 'json'})}", headers=UA)
    for attempt in range(4):  # network blips (DNS, resets): wait and retry, then give up loudly
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read(); b = gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b
            break
        except OSError as err:
            if attempt == 3: raise
            print("retry after", err, flush=True); time.sleep(30 * (attempt + 1))
    last[kind] = time.time()
    return json.loads(b)

def rendered(page):
    """Rendered HTML of a page (cached)."""
    f = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9_.-]", "_", page) + ".html")
    if os.path.exists(f): return open(f, encoding="utf-8").read()
    j = api({"action": "parse", "page": page, "prop": "text", "redirects": 1}, "parse")
    h = j.get("parse", {}).get("text", {}).get("*", "") if "error" not in j else ""
    open(f, "w", encoding="utf-8").write(h)
    print("parsed", page, len(h), flush=True)
    return h

def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def table_after(h, heading):
    """Rows (lists of cell texts) of the first table2 table after a section heading."""
    i = h.find(f'id="{heading}"')
    if i < 0: return []
    k = h.find("<table", i); e = h.find("</table>", k)
    if k < 0 or e < 0: return []
    rows = []
    for tr in re.findall(r'<tr class="table2&#95;&#95;row--body[^"]*"[^>]*>(.*?)</tr>', h[k:e], re.S):
        rows.append([text(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)])
    return rows

def history(h):
    i = h.find(">History<")
    if i < 0: return []
    e = h.find("</table>", i)
    out = []
    for dates, team in re.findall(r'<td class="th-mono"[^>]*>(.*?)</td><td[^>]*>.*?<a [^>]*>([^<]+)</a>', h[i:e], re.S):
        d = text(dates).split("—")
        out.append({"from": d[0].strip(), "to": (d[1].strip() if len(d) > 1 else ""), "team": html.unescape(team).strip()})
    return out

def infobox(wikitext):
    m = re.search(r"\{\{Infobox player(.*?)\n\}\}", wikitext, re.S)
    if not m: return None
    return {k.strip(): v.strip() for k, v in re.findall(r"\n\|([a-z_]+)=([^\n]*)", m.group(1))}

dossiers = json.load(open(os.path.join(ROOT, "data", "dash", "dossiers.json"), encoding="utf-8"))

# ---- players
players = [(d["code"], p["player"]) for d in dossiers for p in (d.get("signature") or [])]
boxes = {}
names = [n for _, n in players]
for i in range(0, len(names), 50):
    j = api({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "titles": "|".join(names[i:i + 50]), "redirects": 1}, "query")
    redirect = {r["to"]: r["from"] for r in j["query"].get("redirects", [])}
    norm = {n["to"]: n["from"] for n in j["query"].get("normalized", [])}
    for pg in j["query"]["pages"].values():
        title = pg.get("title", "")
        asked = norm.get(redirect.get(title, title), redirect.get(title, title))
        wt = pg["revisions"][0]["slots"]["main"]["*"] if "revisions" in pg else ""
        boxes[asked] = (title, infobox(wt))

# a shared name lands on a disambiguation page: search "<name> <team>" for "<name> (...)" pages with an infobox
TEAM_NAME = {d["code"]: d["name"] for d in dossiers}
for code, name in players:
    if boxes.get(name, (name, None))[1]: continue
    j = api({"action": "query", "list": "search", "srsearch": f"{name} {TEAM_NAME.get(code, code)}", "srnamespace": 0, "srlimit": 10}, "query")
    for hit in j["query"]["search"]:
        t = hit["title"]
        if not t.lower().startswith(name.lower() + " ("): continue
        k = api({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "titles": t}, "query")
        pg = next(iter(k["query"]["pages"].values()))
        box = infobox(pg["revisions"][0]["slots"]["main"]["*"]) if "revisions" in pg else None
        if not box: continue
        # accept only if the player's latest team in their history is our team (a shared name can match the wrong player)
        latest = (history(rendered(t)) or [{}])[-1].get("team", "")
        a, b = re.sub(r"[^a-z0-9]", "", latest.lower()), re.sub(r"[^a-z0-9]", "", TEAM_NAME.get(code, code).lower())
        first = re.sub(r"[^a-z0-9]", "", TEAM_NAME.get(code, code).split()[0].lower())
        if a and (a in b or b in a or first in a or code.lower() in a):
            boxes[name] = (t, box); print("resolved", name, "->", t, "(latest team", latest + ")", flush=True); break
        print("rejected", t, "latest team", latest, flush=True)

out_players, missing = {}, []
for code, name in players:
    title, box = boxes.get(name, (name, None))
    if not box:
        missing.append(f"{code} {name}"); continue
    h = rendered(title)
    out_players[name.lower()] = {
        "player": name, "team": code, "page": title, "url": f"https://liquipedia.net/leagueoflegends/{urllib.parse.quote(title.replace(' ', '_'))}",
        "native_name": box.get("name", ""), "romanized_name": box.get("romanized_name", ""), "birth_date": box.get("birth_date", ""),
        "country": box.get("country", ""), "roles": box.get("roles", ""),
        "socials": {k: box[k] for k in ("twitch", "twitter", "instagram", "youtube") if box.get(k)},
        "history": history(h),
        # achievements cells: date, place, tier, (league icon), tournament, team, score, opponent, prize
        "achievements": [{"date": r[0], "place": r[1], "tier": r[2], "tournament": r[4], "score": r[6] if len(r) > 6 else "", "opponent": r[7] if len(r) > 7 else ""} for r in table_after(h, "Achievements") if len(r) >= 5],
        # awards cells: date, tier, (league icon), tournament, award, team, prize
        "awards": [{"date": r[0], "tier": r[1], "tournament": r[3], "award": re.sub(r"\s*\[\s*\d+\s*\]$", "", r[4])} for r in table_after(h, "Awards") if len(r) >= 5],
        "accessed": TODAY,
    }
    json.dump(out_players, open(os.path.join(ROOT, "data", "dash", "wiki_players.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("players", len(out_players), "missing", missing, flush=True)

# ---- teams
TEAM_PAGE = {"GEN": "Gen.G Esports", "T1": "T1", "HLE": "Hanwha Life Esports", "DK": "Dplus", "BLG": "Bilibili Gaming", "AL": "Anyone's Legend",
             "IG": "Invictus Gaming", "TES": "Top Esports", "G2": "G2 Esports", "KC": "Karmine Corp", "MKOI": "Movistar KOI", "TLAW": "Team Liquid",
             "LYON": "LYON", "C9": "Cloud9", "TSW": "Team Whales", "CFO": "CTBC Flying Oyster", "FURIA": "FURIA Esports", "LOS": "LOS", "MVK": "MVK Esports"}
out_teams = {}
for code, page in TEAM_PAGE.items():
    h = rendered(page)
    i = h.find('infobox-header-2">Achievements'); e = h.find("infobox-header", i + 50) if i >= 0 else -1
    titles = re.findall(r'lightmode"><a href="[^"]+" title="([^"]+)"', h[i:e]) if i >= 0 else []
    res = rendered(f"{page}/Results")
    # Results table cells: date, place, tier, type, (league icon), tournament, result, prize (columns can vary; keep raw too)
    rows = []
    k = res.find("<table")
    while k >= 0:
        e2 = res.find("</table>", k)
        for tr in re.findall(r'<tr class="table2&#95;&#95;row--body[^"]*"[^>]*>(.*?)</tr>', res[k:e2], re.S):
            cells = [text(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(cells) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0]): rows.append(cells)
        k = res.find("<table", e2)
    out_teams[code] = {
        "page": page, "url": f"https://liquipedia.net/leagueoflegends/{urllib.parse.quote(page.replace(' ', '_'))}",
        "titles": titles, "results": rows, "accessed": TODAY,
    }
    json.dump(out_teams, open(os.path.join(ROOT, "data", "dash", "wiki_teams.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("teams", len(out_teams), "with results", sum(1 for t in out_teams.values() if t["results"]), flush=True)
