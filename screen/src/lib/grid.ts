// Always exactly 10x10 of 0/1, so a short row or junk from the model can't shift every later cell.
export function normalizeGrid(grid: unknown): number[][] {
  const rows = Array.isArray(grid) ? grid : [];
  return Array.from({ length: 10 }, (_, r) => {
    const row: unknown = rows[r];
    return Array.from({ length: 10 }, (_, c) => (Array.isArray(row) && Number(row[c]) ? 1 : 0));
  });
}
