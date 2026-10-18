import { useEffect, useState } from "react";
import { COPY } from "../design/copy";
import { IDLE_SHAPES } from "../lib/idleShapes";
import { reducedMotion } from "../lib/motion";
import { BallGrid } from "./BallGrid";
import "./IdleScreen.css";

const CYCLE_MS = 8000; // --dur-idle

// Attract mode: the board draws each demo painting's best-known part while nobody is touring.
export function IdleScreen({ offline }: { offline: boolean }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (offline || reducedMotion()) return;
    const t = window.setInterval(() => setI((n) => (n + 1) % IDLE_SHAPES.length), CYCLE_MS);
    return () => window.clearInterval(t);
  }, [offline]);
  const shape = IDLE_SHAPES[i];
  return (
    <main className={`idle${offline ? " idle--offline" : ""}`}>
      <div className="idle__board">
        <BallGrid grid={shape.grid} />
      </div>
      <div className="idle__copy">
        <p className="idle__kicker">{offline ? COPY.offlineKicker : `${shape.title} · ${shape.part}`}</p>
        <h1 className="idle__headline">{offline ? COPY.offlineHeadline : COPY.idleHeadline}</h1>
        <p className="idle__hint label">{offline ? COPY.offlineHint : COPY.idleHint}</p>
      </div>
      <p className="idle__footer label">{COPY.idleFooter}</p>
    </main>
  );
}
