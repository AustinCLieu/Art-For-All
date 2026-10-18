export function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** "03:12" for 192000 ms. Minutes keep counting past 59. */
export function formatClock(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${pad(Math.floor(s / 60))}:${pad(s % 60)}`;
}
