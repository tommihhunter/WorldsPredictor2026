# Worlds 2026 research brief (shared by all research subagents)

Today is 15/10/2026 (NZDT). The 2026 League of Legends World Championship Play-In starts 15/10 (Los Angeles).

## Ground rules
1. Your training data is stale for 2026. Treat every roster, result, stat and patch detail you "know" as unverified until you find a 2026 source. If you cannot find it, write `UNKNOWN`. NEVER fill a gap from memory.
2. Cite everything: every stat/claim gets a source URL and access date (15/10/2026). Preferred sources in order: Liquipedia (liquipedia.net/leagueoflegends), Leaguepedia (lol.fandom.com), gol.gg, Oracle's Elixir, lolesports.com; then Sheep Esports, Inven Global, Dexerto, Hotspawn, Dot Esports. Scrim/bootcamp rumours are tagged `LOW-WEIGHT`.
3. Dates as dd/mm/yyyy.
4. gol.gg team/player stat pages are usually the fastest way to get GD@15, FB%, FT%, dragon/herald/baron control, side win rates, per-player KDA/CSD@15/GD@15/KP/DMG%. Use WebFetch on gol.gg pages for the relevant 2026 tournament (e.g. "LCK 2026 Playoffs", "LPL 2026 Split 3 Playoffs" etc.). If gol.gg is unreachable, try Leaguepedia scoreboards / Oracle's Elixir; mark what you couldn't get as UNKNOWN.
5. Be efficient: prioritise (a) confirmed Worlds roster, (b) 2026 placements and international series scores, (c) last-6-weeks form, (d) team stats, (e) player stats, (f) identity/draft. Do not spend forever on one stat; UNKNOWN is acceptable.
6. Distinguish domestic playoffs stats from international-event stats where possible. If only full-year/split aggregates exist, say which sample it is.

## Output per team: `/home/claude/worlds2026/research/teams/<TEAM>.md`
Use this structure exactly (TEAM = the short code given to you, e.g. GEN):

```
# <TEAM> - <Full name> (<Region>, seed <n>)
_Last updated 15/10/2026. Sources accessed 15/10/2026 unless noted._

## Headline
One line.

## Roster (Worlds)
| Role | Player | Nationality | Worlds appearances (prior) | Source |
Subs, head coach, and any roster/coach change since the domestic final.

## 2026 results
- Domestic: each split/playoff placement + final series score.
- International: First Stand / MSI / EWC with every series score.

## Form (last 6 weeks, ~01/09 - 15/10/2026)
Series list with scores; verdict: RISING / PEAKING / FADING / STABLE, with reason.

## Team stats
Table with columns: Metric | Domestic playoffs | International | Source. Rows: games, win rate, avg game duration, GD@15, FB%, FT%, dragon control %, grubs (avg or %), herald %, baron %, WR when ahead @15, WR when behind @15, blue WR, red WR.

## Player stats
Per role: KDA, GD@15, CSD@15, XPD@15, KP%, DMG%, gold share %, solo kills, champion pool size, top-3 champions with W-L. Cite the sample.

## Identity
How they win; how they lose.

## Draft tendencies
First-pick priorities, flex picks, comfortable blind picks, comfort champions opponents ban against them.

## International pedigree
Player Worlds experience; team vs other regions in 2026 (series/game records).

## Intangibles (LOW-WEIGHT)
Travel, bootcamp, scrim rumours, coaching.

## Data gaps
Bullet list of UNKNOWNs.

## Sources
Numbered list: [title](url) - accessed 15/10/2026
```

## Structured output: `/home/claude/worlds2026/data/fragments/<GROUP>_teams.json`
A JSON array, one object per team:
```json
{
  "code": "GEN", "name": "Gen.G", "region": "LCK", "seed": 1,
  "headline": "...",
  "roster": [{"role":"TOP","player":"...","worlds_prior":3}],
  "coach": "...", "roster_change_since_final": "none|...",
  "domestic_2026": [{"event":"LCK 2026 Split 1","placement":"1st","final":"3-1 vs HLE"}],
  "form_6w": {"series":[{"date":"dd/mm/yyyy","opp":"HLE","score":"3-1","event":"..."}], "trend":"RISING|PEAKING|FADING|STABLE"},
  "team_stats": {"sample":"LCK 2026 playoffs","games":0,"wr":null,"avg_len_min":null,"gd15":null,"fb_pct":null,"ft_pct":null,"drag_pct":null,"herald_pct":null,"baron_pct":null,"grubs_avg":null,"wr_ahead15":null,"wr_behind15":null,"blue_wr":null,"red_wr":null},
  "team_stats_intl": { same keys or null },
  "players": [{"role":"TOP","player":"...","kda":null,"gd15":null,"csd15":null,"xpd15":null,"kp":null,"dmg_pct":null,"gold_share":null,"solo_kills":null,"pool":null,"top3":[{"champ":"...","w":0,"l":0}]}],
  "identity": "...", "draft": "...",
  "sources": [{"id":1,"title":"...","url":"...","accessed":"15/10/2026"}]
}
```
Use null for UNKNOWN numbers. Percentages as numbers 0-100.

Also write `/home/claude/worlds2026/data/fragments/<GROUP>_results.json`: a JSON array of every 2026 series your teams played in international events (First Stand, MSI, EWC) and their domestic playoff series:
```json
{"date":"dd/mm/yyyy","event":"MSI 2026","stage":"Bracket R1","team_a":"GEN","team_b":"AL","score_a":3,"score_b":1,"bo":5,"international":true,"source":"url"}
```
Use the team codes in this brief where possible (AL, BLG, TES, IG, GEN, HLE, T1, DK, G2, MKOI, KC, TLAW, LYON, C9, TSW, CFO, MVK, LOS, FURIA). For opponents not at Worlds, use their common short name.

## Final message back to the orchestrator
Return a compact summary (max ~400 words): one-line headline per team, confirmed rosters (one line each), key 2026 results, top data gaps, and anything that contradicts the common narrative. Do not paste the full dossiers back.
