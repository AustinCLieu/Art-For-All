import type { CSSProperties } from "react";
import type { Section } from "../types";

const FLAT: number[][] = Array.from({ length: 10 }, () => Array<number>(10).fill(0));

// Row 0 is the edge farthest from the visitor, as on the real board. Balls move one row at a time.
// Always exactly 10x10 of 0/1, so a short row can't shift every later cell.
const normalize = (grid: unknown[][] | undefined): number[][] =>
  Array.from({ length: 10 }, (_, r) => Array.from({ length: 10 }, (_, c) => (Number(grid?.[r]?.[c]) ? 1 : 0)));

export function Board({ section, hardware }: { section: Section | null; hardware: boolean }) {
  const grid = section ? normalize(section.grid) : FLAT;
  const raised = grid.flat().filter(Boolean).length;
  return (
    <section className="panel board-panel">
      <h2>{hardware ? "Touch board, mirrored live" : "Touch board, simulated"}</h2>
      <p className="now">{section ? section.name : "All balls down"}</p>
      <div className="board" role="img" aria-label={`${raised} of 100 balls raised`}>
        {grid.map((row, r) =>
          row.map((v, c) => (
            <span key={`${r}-${c}`} className={v ? "pin up" : "pin"} style={{ "--row": r } as CSSProperties} />
          )),
        )}
      </div>
      <p className="caption">
        {hardware ? "The same frame the physical board is showing" : "The same frames the physical board receives over serial"}
      </p>
      <code className="frame">{section?.frame ?? "Z"}</code>
    </section>
  );
}
