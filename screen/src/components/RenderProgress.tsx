import type { CSSProperties } from "react";
import { COPY } from "../design/copy";
import type { Render } from "../types";
import "./RenderProgress.css";

// One bar for the whole screen: how far the 10,000-pin reliefs are from rendered.
// Shows while they render (including the model-download "preparing" phase), hides when done.
export function RenderProgress({ render }: { render: Render }) {
  const active = render.total > 0 && (render.phase === "preparing" || render.phase === "rendering");
  if (!active) return null;
  const preparing = render.phase === "preparing";
  // While the depth model downloads, done is 0: show a faint pulsing sliver instead of an empty bar.
  const fraction = preparing ? 0.08 : render.done / render.total;
  return (
    <div className={`render render--${render.phase}`} role="status" aria-live="polite">
      <div className="render__text label">
        <span>{preparing ? COPY.renderPreparing : COPY.renderLabel}</span>
        {!preparing && <span className="render__count">{render.done} / {render.total}</span>}
      </div>
      <div className="render__track" aria-hidden>
        <div className="render__fill" style={{ "--p": fraction } as CSSProperties} />
      </div>
    </div>
  );
}
