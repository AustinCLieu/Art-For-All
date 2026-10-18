import { useLayoutEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import { css, LANTERN, type RGB } from "../lib/colors";
import { FLY_MS, LIT_MS, ROW_MS } from "../lib/flow";
import { normalizeGrid } from "../lib/grid";
import type { Section } from "../types";
import "./BorderlessFlow.css";

interface Dot { key: string; row: number; x: number; y: number; dx: number; dy: number; size: number; from: number; color: string }

const WELL_SCALE = 0.62; // matches .ball { transform: scale(0.62) }

// The part of the painting lifts off as dots and lands on the board, teamLab-style: art moving between rooms.
export function BorderlessFlow({ section, colors, frameRef, wellsRef, onLanded }: {
  section: Section;
  colors: RGB[][] | null;
  frameRef: RefObject<HTMLDivElement>;
  wellsRef: RefObject<HTMLDivElement>;
  onLanded: () => void;
}) {
  const [dots, setDots] = useState<Dot[]>([]);
  const [flying, setFlying] = useState(false);
  const landed = useRef(onLanded);
  landed.current = onLanded;

  useLayoutEffect(() => {
    const frame = frameRef.current?.querySelector(".stage__clip")?.getBoundingClientRect();
    const wells = wellsRef.current;
    if (!frame || !wells) {
      landed.current();
      return;
    }
    const [x0, y0, x1, y1] = section.bbox;
    const cw = ((x1 - x0) * frame.width) / 10;
    const ch = ((y1 - y0) * frame.height) / 10;
    const next: Dot[] = [];
    normalizeGrid(section.grid).forEach((row, r) =>
      row.forEach((v, c) => {
        if (v !== 1) return;
        const well = wells.querySelector(`[data-cell="${r}-${c}"]`)?.getBoundingClientRect();
        if (!well) return;
        const size = well.width / WELL_SCALE;
        const x = frame.left + x0 * frame.width + (c + 0.5) * cw;
        const y = frame.top + y0 * frame.height + (r + 0.5) * ch;
        next.push({
          key: `${r}-${c}`,
          row: r,
          x,
          y,
          dx: well.left + well.width / 2 - x,
          dy: well.top + well.height / 2 - y,
          size,
          from: Math.max(0.15, Math.min(cw, ch, size) / size) * 0.7,
          color: css(colors?.[r]?.[c] ?? LANTERN),
        });
      }),
    );
    if (next.length === 0) {
      landed.current();
      return;
    }
    setDots(next);
    const go = window.setTimeout(() => setFlying(true), LIT_MS);
    const done = window.setTimeout(() => landed.current(), LIT_MS + FLY_MS + 9 * ROW_MS);
    return () => {
      window.clearTimeout(go);
      window.clearTimeout(done);
    };
  }, [section, frameRef, wellsRef]); // colors are read once when the flight starts

  return (
    <div className="flow" aria-hidden>
      {dots.map((d) => (
        <span
          key={d.key}
          className="flow__dot"
          style={{
            left: d.x - d.size / 2,
            top: d.y - d.size / 2,
            width: d.size,
            height: d.size,
            transform: flying ? `translate(${d.dx}px, ${d.dy}px) scale(1)` : `scale(${d.from})`,
            transitionDelay: flying ? `${d.row * ROW_MS}ms` : "0ms",
            "--dot": d.color,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}
