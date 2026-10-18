import { COPY } from "../design/copy";
import { EMPTY_GRID } from "../lib/idleShapes";
import { BallGrid } from "./BallGrid";
import "./LookingUp.css";

// Gemini is finding the parts of a painting that isn't cached yet.
export function LookingUp({ detail }: { detail: string }) {
  return (
    <main className="looking">
      <div className="looking__frame" aria-hidden>
        <span className="looking__sweep" />
      </div>
      <div className="looking__side">
        <p className="looking__label label">{COPY.lookingUp}</p>
        <p className="looking__detail">{detail}</p>
        <div className="looking__board">
          <BallGrid grid={EMPTY_GRID} breathing />
        </div>
      </div>
    </main>
  );
}
