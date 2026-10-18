import type { CSSProperties } from "react";
import { pad } from "../lib/format";
import type { Section } from "../types";
import "./Spotlight.css";

type Bbox = [number, number, number, number];

function box([x0, y0, x1, y1]: Bbox): CSSProperties {
  return { left: `${x0 * 100}%`, top: `${y0 * 100}%`, width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%` };
}

/** Inside the clipped image: dims everything except the part. `grid` shows the 10x10 cells during the flow. */
export function SpotlightBox({ bbox, grid }: { bbox: Bbox; grid: boolean }) {
  return <div className={`spotlight${grid ? " spotlight--grid" : ""}`} style={box(bbox)} aria-hidden />;
}

/** Outside the clip: the part's name hung on a hand-drawn hook at the box corner. */
export function SpotlightTag({ section }: { section: Section }) {
  const [x0, y0, x1] = section.bbox;
  const left = x1 > 0.7 && x0 > 0.3; // no room on the right
  const below = y0 < 0.08; // no room above
  const cls = `spot-tag label${left ? " spot-tag--left" : ""}${below ? " spot-tag--below" : ""}`;
  return (
    <div className="spot-anchor" style={box(section.bbox)} aria-hidden>
      <span className={cls}>
        <svg className="spot-tag__hook" viewBox="0 0 40 24">
          <path d="M1 23 C 8 21, 12 9, 19 7 S 33 3, 39 1" />
        </svg>
        {pad(section.number)} · {section.name}
      </span>
    </div>
  );
}
