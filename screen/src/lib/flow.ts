// The Borderless flow: lit cells leave the painting and land on the board. Timings in ms.
export const LIT_MS = 350; // cells glow on the painting before they leave
export const FLY_MS = 900; // same as --dur-flow
export const ROW_MS = 30; // each row leaves a little after the one above

export interface Shown {
  title: string | null;
  number: number | null;
}

/** Fly only between two parts of the same painting (the first part just rises in place). */
export function shouldFly(prev: Shown, next: Shown): boolean {
  return prev.number !== null && next.number !== null && prev.title === next.title && prev.number !== next.number;
}
