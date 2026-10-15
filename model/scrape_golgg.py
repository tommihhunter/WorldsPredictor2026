#!/usr/bin/env python3
"""
Scrape every 2026 series (regular season, playoffs, internationals) from gol.gg match
lists into data/golgg_series_2026.json. One consistent source for the whole year.

Each row: {tournament, stage, team_a, team_b, score_a, score_b, date (dd/mm/yyyy), patch,
           kind: regular|playoffs|international|qualifier, league}
Run: python3 model/scrape_golgg.py
"""
import re, html, json, os, time, urllib.request, urllib.parse, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
UA = {"User-Agent": "Mozilla/5.0"}

TOURNAMENTS = {
 # name: (league, kind)
 "LCK Cup 2026": ("LCK", "regular"), "LCK 2026 Rounds 1-2": ("LCK", "regular"), "LCK 2026 Rounds 3-4": ("LCK", "regular"),
 "LCK 2026 Road to MSI": ("LCK", "playoffs"), "LCK 2026 Season Play-In": ("LCK", "playoffs"), "LCK 2026 Season Playoffs": ("LCK", "playoffs"),
 "LPL 2026 Split 1": ("LPL", "regular"), "LPL 2026 Split 1 Playoffs": ("LPL", "playoffs"),
 "LPL 2026 Split 2": ("LPL", "regular"), "LPL 2026 Split 2 Playoffs": ("LPL", "playoffs"),
 "LPL 2026 Split 3": ("LPL", "regular"), "LPL 2026 Grand Finals": ("LPL", "playoffs"), "LPL 2026 Regional Finals": ("LPL", "playoffs"),
 "LEC 2026 Versus Season": ("LEC", "regular"), "LEC 2026 Versus Playoffs": ("LEC", "playoffs"),
 "LEC 2026 Spring Season": ("LEC", "regular"), "LEC 2026 Spring Playoffs": ("LEC", "playoffs"),
 "LEC 2026 Summer Season": ("LEC", "regular"), "LEC 2026 Summer Playoffs": ("LEC", "playoffs"),
 "LCS 2026 Lock-In": ("LCS", "playoffs"), "LCS 2026 Spring": ("LCS", "regular"), "LCS 2026 Spring Playoffs": ("LCS", "playoffs"),
 "LCS 2026 Summer": ("LCS", "regular"), "LCS 2026 Summer Playoffs": ("LCS", "playoffs"),
 "LCP 2026 Split 1": ("LCP", "regular"), "LCP 2026 Split 1 Playoffs": ("LCP", "playoffs"),
 "LCP 2026 Split 2": ("LCP", "regular"), "LCP 2026 Split 2 Playoffs": ("LCP", "playoffs"), "LCP 2026 Split 3": ("LCP", "regular"),
 "CBLOL Cup 2026": ("CBLOL", "regular"), "CBLOL 2026 Split 1": ("CBLOL", "regular"), "CBLOL 2026 Split 1 Playoffs": ("CBLOL", "playoffs"),
 "CBLOL 2026 Split 2": ("CBLOL", "regular"), "CBLOL 2026 Split 2 Playoffs": ("CBLOL", "playoffs"),
 "2026 First Stand": ("INTL", "international"), "MSI 2026": ("INTL", "international"), "Esports World Cup 2026": ("INTL", "international"),
 "EWC 2026 Online Qualifier - Korea": ("LCK", "qualifier"), "EWC 2026 Online Qualifier - EMEA": ("LEC", "qualifier"),
 "EWC 2026 Online Qualifier - APAC": ("LCP", "qualifier"), "EWC 2026 Qualifier NA": ("LCS", "qualifier"),
 "EWC 2026 Online Qualifier - South America": ("CBLOL", "qualifier"),
}


def fetch(name):
    url = "https://gol.gg/tournament/tournament-matchlist/" + urllib.parse.quote(name) + "/"
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            time.sleep(2 + attempt * 3)
            err = e
    raise err


def parse(page):
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 7:
            continue
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", cells[2])
        if not m:
            continue
        try:
            d = dt.datetime.strptime(cells[6], "%Y-%m-%d").date()
        except ValueError:
            continue
        out.append(dict(team_a=cells[1], team_b=cells[3], score_a=int(m[1]), score_b=int(m[2]), stage=cells[4], patch=cells[5],
                        date=d.strftime("%d/%m/%Y")))
    return out


def main():
  rows = []
  for name, (league, kind) in TOURNAMENTS.items():
      page = fetch(name)
      got = parse(page)
      for g in got:
          g.update(tournament=name, league=league, kind=kind)
      rows += got
      print(f"{name:<45} {len(got):>4} series")
      time.sleep(0.6)
  json.dump(rows, open("data/golgg_series_2026.json", "w"), indent=0, ensure_ascii=False)
  names = sorted({r["team_a"] for r in rows} | {r["team_b"] for r in rows})
  json.dump(names, open("data/golgg_team_names.json", "w"), indent=0, ensure_ascii=False)
  print("total series", len(rows), "| distinct team names", len(names))


if __name__ == "__main__":
    main()
