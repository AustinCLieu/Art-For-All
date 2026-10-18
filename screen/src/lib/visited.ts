export interface Visited {
  title: string | null;
  numbers: number[]; // section numbers shown for this painting, in order
}

export const NO_VISITS: Visited = { title: null, numbers: [] };

export function visit(prev: Visited, title: string | null, number: number | null): Visited {
  if (title !== prev.title) return { title, numbers: number === null ? [] : [number] };
  if (number === null || prev.numbers.includes(number)) return prev;
  return { title, numbers: [...prev.numbers, number] };
}
