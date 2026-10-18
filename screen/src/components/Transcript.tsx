import { useEffect, useRef } from "react";
import type { Line } from "../types";

export function Transcript({ lines }: { lines: Line[] }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = box.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [lines]); // a new array only when the state changed, so this also scrolls once 50 lines are full

  return (
    <section className="panel transcript-panel">
      <h2>Conversation</h2>
      <div className="lines" ref={box}>
        {lines.length === 0 && <p className="hint">Say "Show me the Mona Lisa."</p>}
        {lines.map((l, i) => (
          <p key={i} className={`line ${l.role}`}>
            <span className="who">{l.role === "user" ? "Visitor" : "Guide"}</span>
            {l.text}
          </p>
        ))}
      </div>
    </section>
  );
}
