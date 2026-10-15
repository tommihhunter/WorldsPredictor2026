export const pct = (x: number | null | undefined, dp = 0) => (x == null || Number.isNaN(Number(x)) ? 'UNKNOWN' : `${(Number(x) * 100).toFixed(dp)}%`);
export const num = (x: number | null | undefined, dp = 1) => (x == null ? 'UNKNOWN' : Number(x).toFixed(dp));
export const signed = (x: number | null | undefined) => (x == null ? 'UNKNOWN' : `${x > 0 ? '+' : ''}${Math.round(Number(x))}`);
export const nz = (s: string | null | undefined, keepZone = false) => (!s ? 'TBC' : keepZone ? s : s.replace(' NZDT', ''));
