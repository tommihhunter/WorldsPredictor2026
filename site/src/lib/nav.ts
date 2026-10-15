import { overview } from './data';
export type NavItem = { id: string; label: string; path: string; group: 'event' | 'reference' | 'home' };
export const NAV: NavItem[] = [
  { id: 'home', label: 'Home', path: '', group: 'home' },
  { id: 'play-in', label: 'Play-In', path: 'play-in/', group: 'event' },
  { id: 'swiss', label: 'Swiss', path: 'swiss/', group: 'event' },
  { id: 'knockouts', label: 'Knockouts', path: 'knockouts/', group: 'event' },
  { id: 'demacia-cup', label: 'Demacia Cup', path: 'demacia-cup/', group: 'event' },
  { id: 'teams', label: 'Teams', path: 'teams/', group: 'reference' },
  { id: 'scorecard', label: 'Scorecard', path: 'scorecard/', group: 'reference' },
  { id: 'meta', label: 'Meta', path: 'meta/', group: 'reference' },
];
/** Stage in play, from the next Pick'Ems lock the pipeline exports (data/rules_2026.json dates). */
export function liveStage(): string {
  const lock = overview().next_lock ?? '';
  if (lock.includes('24/10/2026')) return 'play-in';
  if (lock.includes('04/11/2026')) return 'swiss';
  return 'knockouts';
}
