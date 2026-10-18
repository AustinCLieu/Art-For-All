import { COPY, WORDMARK } from "../design/copy";
import { useSessionClock } from "../lib/hooks";
import "./TopStrip.css";

export function TopStrip({ online, drawerOpen, onToggleDrawer, pinsOpen, onTogglePins }: {
  online: boolean;
  drawerOpen: boolean;
  onToggleDrawer: () => void;
  pinsOpen: boolean;
  onTogglePins: () => void;
}) {
  const elapsed = useSessionClock(online);
  return (
    <header className="top-strip">
      <span className="wordmark">{WORDMARK}</span>
      <div className="top-strip__right">
        {online && (
          <span className="live label">
            <span className="live__dot" aria-hidden />
            {COPY.live} <span className="live__time">{elapsed}</span>
          </span>
        )}
        <button type="button" className="key-button label" aria-pressed={pinsOpen} onClick={onTogglePins}>
          <kbd>P</kbd> {COPY.pins}
        </button>
        <button type="button" className="key-button label" aria-pressed={drawerOpen} onClick={onToggleDrawer}>
          <kbd>S</kbd> {COPY.agents}
        </button>
      </div>
    </header>
  );
}
