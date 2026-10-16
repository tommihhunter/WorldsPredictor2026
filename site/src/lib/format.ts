export const pct = (x: number | null | undefined, dp = 0) => (x == null || Number.isNaN(Number(x)) ? 'UNKNOWN' : `${(Number(x) * 100).toFixed(dp)}%`);
export const num = (x: number | null | undefined, dp = 1) => (x == null ? 'UNKNOWN' : Number(x).toFixed(dp));
export const nz = (s: string | null | undefined, keepZone = false) => (!s ? 'UNKNOWN' : keepZone ? s : s.replace(' NZDT', ''));
/** One-decimal percent site wide; below 0.05% reads "<0.1%". */
export const pct1 = (x: number | null | undefined) => (x == null || Number.isNaN(Number(x)) ? 'UNKNOWN' : Number(x) > 0 && Number(x) < 0.0005 ? '<0.1%' : `${(Number(x) * 100).toFixed(1)}%`);
/**
 * Data prose in NZ time: a few exported team headlines carry a UTC clock time or a bare US-venue date.
 * "15/10 23:00 UTC" becomes "16/10 12:00 NZDT"; a bare "dd/mm" at the end of a bracket is dropped (its NZ date is not knowable from the text).
 */
export const nzProse = (s: string) => s
  .replace(/(\d\d)\/(\d\d) (\d\d):(\d\d) UTC/g, (_m, d, mo, h, mi) => {
    const t = new Date(Date.UTC(2026, +mo - 1, +d, +h + 13, +mi));
    return `${String(t.getUTCDate()).padStart(2, '0')}/${String(t.getUTCMonth() + 1).padStart(2, '0')} ${String(t.getUTCHours()).padStart(2, '0')}:${mi} NZDT`;
  })
  .replace(/\s*\(\d\d\/\d\d\)/g, '')
  .replace(/ \d\d\/\d\d\)/g, ')');
