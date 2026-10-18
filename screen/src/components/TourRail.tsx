import type { SectionSummary } from "../types";
import "./TourRail.css";

// One ball per part: visited (filled), now (lantern with halo), still to come (hollow ring).
export function TourRail({ sections, current, visited }: {
  sections: SectionSummary[];
  current: number | null;
  visited: number[];
}) {
  return (
    <ol className="rail">
      {sections.map((s) => {
        const state = s.number === current ? "now" : visited.includes(s.number) ? "done" : "next";
        return (
          <li key={s.number} className={`rail__stop rail__stop--${state}`} aria-current={state === "now" ? "step" : undefined}>
            <span className="rail__ball" aria-hidden />
            <span className="rail__name label">{s.name}</span>
          </li>
        );
      })}
    </ol>
  );
}
