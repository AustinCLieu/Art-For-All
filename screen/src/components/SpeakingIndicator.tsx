import type { CSSProperties } from "react";
import type { Speech } from "../lib/speaker";
import "./SpeakingIndicator.css";

// Eight dots on a ring, like ripples around your feet in teamLab's water room.
export function SpeakingIndicator({ state }: { state: Speech }) {
  return (
    <span className={`speech speech--${state}`} aria-hidden>
      {Array.from({ length: 8 }, (_, i) => (
        <span key={i} className="speech__dot" style={{ "--i": i } as CSSProperties} />
      ))}
    </span>
  );
}
