// Players: every starter in data/dash/dossiers.json (signature = 2026 season, signature_summer = Summer split),
// with their team, a URL slug and whether a photo was fetched (model/fetch_art.py -> public/art/players/<slug>.webp).
import { existsSync } from 'node:fs';
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
