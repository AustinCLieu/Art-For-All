import type { CSSProperties, RefObject } from "react";
import { css, LANTERN, type RGB } from "../lib/colors";
import "./BallGrid.css";

// Row 0 is the edge farthest from the visitor, as on the real board. Balls rise one row after another.
export function BallGrid({ grid, colors = null, held = false, breathing = false, gridRef }: {
  grid: number[][];
  colors?: RGB[][] | null;
  held?: boolean;
  breathing?: boolean;
  gridRef?: RefObject<HTMLDivElement>;
}) {
  const raised = grid.flat().filter(Boolean).length;
  return (
    <div ref={gridRef} className={`balls${breathing ? " balls--breathing" : ""}`} role="img" aria-label={`${raised} of 100 balls raised`}>
      {grid.map((row, r) =>
        row.map((v, c) => (
          <span
            key={`${r}-${c}`}
            data-cell={`${r}-${c}`}
            className={v === 1 && !held ? "ball ball--up" : "ball"}
            style={{ "--row": r, "--ball": css(colors?.[r]?.[c] ?? LANTERN) } as CSSProperties}
          />
        )),
      )}
    </div>
  );
}
