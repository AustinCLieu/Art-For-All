import { COPY, SPONSORS } from "../design/copy";
import type { State } from "../types";
import "./AgentDrawer.css";

// What each sponsor's piece is doing. Slides over the right column; never reflows the layout.
export function AgentDrawer({ open, activity, frame, onClose }: {
  open: boolean;
  activity: State["activity"];
  frame: string | null;
  onClose: () => void;
}) {
  return (
    <aside className={`drawer${open ? " drawer--open" : ""}`} aria-label={COPY.drawerTitle}>
      <header className="drawer__head">
        <h2 className="drawer__title">{COPY.drawerTitle}</h2>
        <button type="button" className="key-button label" onClick={onClose}>
          <kbd>S</kbd> {COPY.close}
        </button>
      </header>
      <ul className="drawer__rows">
        {SPONSORS.map(({ key, name, job }) => {
          const a = activity[key];
          return (
            <li key={key} className={`agent agent--${a.status}`}>
              <span className="agent__status label">
                <span className="agent__dot" aria-hidden />
                {COPY.status[a.status]}
              </span>
              <span className="agent__name">{name}</span>
              <span className="agent__job">{job}</span>
              <span className="agent__detail label">{a.detail || "—"}</span>
            </li>
          );
        })}
      </ul>
      <div className="drawer__wire">
        <span className="label">{COPY.onTheWire}</span>
        <code>{frame ?? "Z"}</code>
      </div>
    </aside>
  );
}
