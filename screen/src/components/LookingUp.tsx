import { COPY } from "../design/copy";
import { EMPTY_GRID } from "../lib/idleShapes";
import { BallGrid } from "./BallGrid";
import "./LookingUp.css";

// Gemini is finding the parts of a painting that isn't cached yet. Once the image has been
// fetched it shows here immediately, with the sweep passing over it, while the parts are drawn.
export function LookingUp({ detail, image }: { detail: string; image?: string | null }) {
  return (
    <main className="looking">
      <div className="looking__frame" aria-hidden>
        {image && <img className="looking__image" src={image} alt="" />}
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
