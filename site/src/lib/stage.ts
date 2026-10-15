// Stage hubs: texts from research/format.md and data/rules_2026.json (accessed 15/10/2026), and the
// Frozen / Latest rules ported from dashboard/index.html (predictions script: latestSet, bracket, draw).
import { pickems, results, series, swiss, type Series } from './data';
import { nzToday, pickemSlots, resultFor, started } from './grading';

export { resultFor, started };

export type Stage = {
  id: 'play-in' | 'swiss' | 'knockouts';
  phase: 'Play-In' | 'Swiss' | 'Knockouts';
  title: string; venue: string; dates: string; format: string; draft: string; lock: string; note: string;
  pickemsStage: 'Play-In' | 'Swiss' | 'Knockouts';
  setKey: 'playin' | 'swiss' | 'knockouts';
  brackets?: [string, string[]][];
};

export const STAGES: Stage[] = [
  {
    id: 'play-in', phase: 'Play-In', pickemsStage: 'Play-In', setKey: 'playin', title: 'Play-In',
    venue: 'Riot Games Arena, Los Angeles',
    dates: '16 to 19/10/2026 NZDT (15 to 18/10 in Los Angeles)',
    format: 'Four teams, double elimination, every series Bo5, no bracket reset in the final. The final winner goes to Swiss as a Tier 4 team.',
    draft: 'Fearless Draft in all six series.',
    lock: '16/10/2026 07:00 NZDT (15/10 11:00 PDT)',
    note: 'Each card shows the favourite, its win chance, and the odds of every winning score; the bold score is the single most likely one and is what gets graded.',
    brackets: [['Round 1', ['PI-R1-A', 'PI-R1-B']], ['Round 2', ['PI-WM', 'PI-EM']], ['Lower final', ['PI-LF']], ['Final', ['PI-GF']]],
  },
  {
    id: 'swiss', phase: 'Swiss', pickemsStage: 'Swiss', setKey: 'swiss', title: 'Swiss stage',
    venue: 'CUTX Event Center, Allen, Texas',
    dates: '24/10 to 01/11/2026 NZDT (23 to 31/10 in Allen, no matches on 27/10)',
    format: '16 teams paired by record, no rematches. 3 wins advance, 3 losses are out, 8 advance. Bo1 in rounds 1 and 2 and for 1-1 teams in round 3; Bo3 whenever a result qualifies or eliminates.',
    draft: 'Standard draft in Bo1s, Fearless Draft in Bo3s.',
    lock: '24/10/2026 06:00 NZDT (23/10 10:00 PDT)',
    note: 'Round 1 draw on 18/10: Tier 1 v Tier 4 and Tier 2 v Tier 3, no same-region pairings in round 1.',
  },
  {
    id: 'knockouts', phase: 'Knockouts', pickemsStage: 'Knockouts', setKey: 'knockouts', title: 'Knockouts',
    venue: 'CUTX Event Center, Allen (quarterfinals, semifinals); Barclays Center, Brooklyn (final)',
    dates: '04/11 to 15/11/2026 NZDT (final 14/11 in Brooklyn)',
    format: 'Eight teams, single elimination, every series Bo5, no third-place match.',
    draft: 'Fearless Draft in every series.',
    lock: '04/11/2026 11:00 NZDT (03/11 14:00 PST)',
    note: 'The quarterfinal draw on 31/10 is random; the baseline assumes no same-region quarterfinals with favourites spread out.',
    brackets: [['Quarterfinals', ['KO-QF1', 'KO-QF2', 'KO-QF3', 'KO-QF4']], ['Semifinals', ['KO-SF1', 'KO-SF2']], ['Final', ['KO-F']]],
  },
];

/** The most advanced staged set (knockouts, swiss, playin), or null when only the baseline exists. */
export const latestSet = (all: Series[] = series()): string | null => ['knockouts', 'swiss', 'playin'].find((o) => all.some((s) => s.set === o)) ?? null;
export const seriesFor = (phase: string, set: string) => series().filter((s) => s.set === set && s.phase === phase);
export const isToday = (s: Series) => (s.time_nz || '').startsWith(nzToday());

const ZONE: Record<string, number> = { PDT: -7, PST: -8, CDT: -5, CST: -6, EDT: -4, EST: -5 };
/** Venue start time as an ISO UTC string, from the zone in `time_venue` ("14/11/2026 11:00 EST (Brooklyn)"). */
export function toUtc(s: Series): string | null {
  const m = /(\d\d)\/(\d\d)\/(\d{4}) (\d\d):(\d\d) ([A-Z]{3})\b/.exec(s.time_venue || '');
  if (!m || !(m[6] in ZONE)) return null;
  return new Date(Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4] - ZONE[m[6]], +m[5])).toISOString();
}
export const bySchedule = (a: Series, b: Series) => (toUtc(a) ?? '9').localeCompare(toUtc(b) ?? '9');

export type View = { set: string; rows: Series[]; note: string; stageNote: string; swissSet: string };
/**
 * The rows one block of a hub shows. set = 'baseline' or the latest staged set; series rows fall back to the
 * baseline when the set has none for this phase. Swiss rows count as re-run only from a Swiss or Knockouts
 * staged run (a Play-In run carries the pre-draw Swiss projection), otherwise the baseline with the note.
 */
export function view(st: Stage, which: 'baseline' | 'latest'): View {
  const set = which === 'baseline' ? 'baseline' : (latestSet() ?? 'baseline');
  const created = series().find((s) => s.set === set)?.created_nz ?? 'UNKNOWN';
  const note = set === 'baseline' ? `Frozen baseline, predicted ${created} and never edited since.` : `Latest staged run (${set}), predicted ${created}. Stages not yet re-run show the frozen baseline.`;
  let rows = seriesFor(st.phase, set);
  let stageNote = '';
  if (!rows.length && set !== 'baseline') { rows = seriesFor(st.phase, 'baseline'); stageNote = 'Not re-run yet; showing the frozen baseline.'; }
  const own = ['swiss', 'knockouts'].includes(set) && swiss().some((x) => x.set === set);
  const swissSet = own ? set : 'baseline';
  if (st.phase === 'Swiss') stageNote = own ? '' : set !== 'baseline' ? 'Not re-run yet (due after the 18/10 draw, before the 24/10 06:00 NZDT lock); showing the frozen baseline.' : 'The round 1 draw is on 18/10. Until then records are averaged over every legal draw.';
  return { set, rows, note, stageNote, swissSet };
}

/** Live Swiss W-L per team: an entered `swiss_record` wins, else counted from finished Swiss series. */
export function swissRecords(): Map<string, string> {
  const wl: Record<string, [number, number]> = {};
  for (const r of results()) {
    if (r.phase !== 'Swiss' || r.kind === 'swiss_record' || !r.winner) continue;
    for (const t of [r.team_a, r.team_b]) if (t) (wl[t] ??= [0, 0])[t === r.winner ? 0 : 1] += 1;
  }
  const m = new Map(Object.entries(wl).map(([t, [w, l]]) => [t, `${w}-${l}`]));
  for (const r of results()) if (r.kind === 'swiss_record' && r.team && r.record) m.set(r.team, r.record);
  return m;
}

/** Pick'Ems rows for a stage with the pick's chance, the actual winner and points earned. */
export const stagePickems = (stage: string) => {
  const p = pickems();
  return pickemSlots().map((x, i) => ({ ...x, p: p[i].p_correct, status: p[i].status })).filter((x) => x.stage === stage);
};

/** Expected vs actual scores over the Bo5 rows (mixLine), actuals from results matched by id and pair. */
export function expectations(rows: Series[]) {
  const bo5 = rows.filter((s) => s.bo === 5);
  const sum = (f: 'pw30' | 'pw31' | 'pw32' | 'p_upset') => bo5.reduce((t, s) => t + (s[f] ?? 0), 0);
  const act = { '3-0': 0, '3-1': 0, '3-2': 0, upset: 0, done: 0 };
  for (const s of bo5) {
    const r = resultFor(s);
    if (!r) continue;
    const a = Number(r.score_a), b = Number(r.score_b);
    const sc = `${Math.max(a, b)}-${Math.min(a, b)}` as '3-0' | '3-1' | '3-2';
    if (sc in act) act[sc] += 1;
    if (r.winner !== s.winner) act.upset += 1;
    act.done += 1;
  }
  return { n: bo5.length, e30: sum('pw30'), e31: sum('pw31'), e32: sum('pw32'), up: sum('p_upset'), act };
}
