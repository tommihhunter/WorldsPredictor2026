// Players: every starter in data/dash/dossiers.json (signature = 2026 season, signature_summer = Summer split),
// with their team, a URL slug and whether a photo was fetched (model/fetch_art.py -> public/art/players/<slug>.webp).
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { displayName, dossiers, ratings, type Player } from './data';

export const ROLES = ['TOP', 'JNG', 'MID', 'ADC', 'SUP'] as const;
export type Role = (typeof ROLES)[number];
export const ROLE_NAME: Record<Role, string> = { TOP: 'Top', JNG: 'Jungle', MID: 'Mid', ADC: 'Bot', SUP: 'Support' };
// plural for "2nd of 19 mids"
export const ROLE_PLURAL: Record<Role, string> = { TOP: 'top laners', JNG: 'junglers', MID: 'mids', ADC: 'bot laners', SUP: 'supports' };
const normRole = (r: string): Role => (({ JUNGLE: 'JNG', BOT: 'ADC', SUPPORT: 'SUP' } as Record<string, Role>)[r.toUpperCase()] ?? (r.toUpperCase() as Role));
export const playerSlug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]/g, '');

export type PlayerRow = {
  slug: string; player: string; role: Role; code: string; team: string; region: string; teamRank: number;
  season: Player; summer: Player | null; photo: boolean;
};

let cache: PlayerRow[] | null = null;
export function players(): PlayerRow[] {
  if (cache) return cache;
  const rank = new Map(ratings().map((r) => [r.code, r]));
  const rows: PlayerRow[] = [];
  for (const d of dossiers()) {
    const r = rank.get(d.code);
    for (const p of d.signature ?? []) {
      const slug = playerSlug(p.player);
      rows.push({
        slug, player: p.player, role: normRole(p.role), code: d.code, team: displayName(r?.name ?? d.name), region: r?.region ?? d.region,
        teamRank: r?.rank ?? 99, season: p, summer: (d.signature_summer ?? []).find((x) => playerSlug(x.player) === slug) ?? null,
        photo: existsSync(resolve(process.cwd(), 'public', 'art', 'players', `${slug}.webp`)),
      });
    }
  }
  // teammates together, teams in model-rank order, roles top to support
  cache = rows.sort((a, b) => a.teamRank - b.teamRank || ROLES.indexOf(a.role) - ROLES.indexOf(b.role));
  return cache;
}

export const ordinal = (n: number) => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`; };

/** Rank of a player's stat among the starters in the same role for one split (higher is better unless told otherwise). */
export function roleRank(p: PlayerRow, field: 'kda' | 'gd15' | 'kp' | 'games' | 'n_champs', split: 'season' | 'summer', higher = true) {
  const own = (split === 'summer' ? p.summer ?? p.season : p.season)[field];
  if (own == null) return null;
  const field_ = players().filter((x) => x.role === p.role)
    .map((x) => (split === 'summer' ? x.summer ?? x.season : x.season)[field])
    .filter((v): v is number => v != null);
  const k = field_.filter((v) => (higher ? v > own : v < own)).length + 1;
  return { k, n: field_.length, label: `${ordinal(k)} of ${field_.length} ${ROLE_PLURAL[p.role]}`, tone: k <= 3 ? 'teal' : k > field_.length - 3 ? 'risk' : 'muted' };
}

// ---- wiki profile (model/fetch_wiki.py -> data/dash/wiki_players.json, from Liquipedia, CC BY-SA 3.0)
export type Wiki = {
  player: string; url: string; native_name: string; romanized_name: string; birth_date: string; country: string;
  socials: Record<string, string>;
  history: { from: string; to: string; team: string }[];
  achievements: { date: string; place: string; tier: string; tournament: string; score: string; opponent: string }[];
  awards: { date: string; tier: string; tournament: string; award: string }[];
  accessed: string;
};
let wikiCache: Record<string, Wiki> | null = null;
export function wikiOf(p: PlayerRow): Wiki | null {
  if (!wikiCache) {
    const f = resolve(process.env.W26_DASH ?? resolve(process.cwd(), '..', 'data', 'dash'), 'wiki_players.json');
    wikiCache = existsSync(f) ? JSON.parse(readFileSync(f, 'utf8')) : {};
  }
  return wikiCache![p.player.toLowerCase()] ?? null;
}
/** "2001-03-03" -> "03/03/2001"; anything else unchanged ("Present"). */
export const isoToNz = (d: string) => {
  const m = /^(\d{4})-(\d{2}|\?\?)-(\d{2}|\?\?)$/.exec(d);
  if (!m) return d;
  const [, y, mo, da] = m;
  return mo === '??' ? y : da === '??' ? `${mo}/${y}` : `${da}/${mo}/${y}`;
};
/** Whole years between an ISO birth date and today (build day). */
export const ageOf = (iso: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
  const [y, m, d] = iso.split('-').map(Number), now = new Date();
  return now.getUTCFullYear() - y - (now.getUTCMonth() + 1 < m || (now.getUTCMonth() + 1 === m && now.getUTCDate() < d) ? 1 : 0);
};
/** Team history newest first, with back-to-back spells at the same team merged. */
export const careerOf = (w: Wiki) => {
  const out: { from: string; to: string; team: string }[] = [];
  for (const h of w.history) {
    const prev = out.at(-1);
    if (prev && prev.team === h.team) prev.to = h.to; else out.push({ ...h });
  }
  return out.reverse();
};
/** Awards worth listing: MVPs, all-league and all-pro teams, rookie awards (not "Player of the Series/Game/Week"). */
export const honoursOf = (w: Wiki) => w.awards.filter((a) => /MVP|All-|Rookie/i.test(a.award) && !/Player of the (Series|Game|Week)/i.test(a.award));
