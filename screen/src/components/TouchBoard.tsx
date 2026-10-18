import type { RefObject } from "react";
import { COPY } from "../design/copy";
import type { RGB } from "../lib/colors";
import { pad } from "../lib/format";
import { normalizeGrid } from "../lib/grid";
import type { Section } from "../types";
import { BallGrid } from "./BallGrid";
import "./TouchBoard.css";

export function TouchBoard({ section, total, hardware, colors, held, wellsRef }: {
  section: Section | null;
  total: number;
  hardware: boolean;
  colors: RGB[][] | null;
  held: boolean;
  wellsRef: RefObject<HTMLDivElement>;
}) {
  return (
    <section className="board">
      <span className="board__numeral" aria-hidden>{section ? pad(section.number) : ""}</span>
      <span className="board__badge label">{hardware ? COPY.mirrored : COPY.simulated}</span>
      <div className="board__grid">
        <BallGrid grid={normalizeGrid(section?.grid)} colors={colors} held={held} gridRef={wellsRef} />
      </div>
      <p className="board__label label">
        {section ? `${COPY.nowTouching} · ${pad(section.number)} / ${pad(total)}` : COPY.allDown}
      </p>
      {section && <h2 className="board__name">{section.name}</h2>}
      {section && <p className="board__where label">{section.location} {COPY.ofTheCanvas}</p>}
    </section>
  );
}
