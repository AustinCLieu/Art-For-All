import { useLayoutEffect, useRef, type CSSProperties } from "react";
import { COPY } from "../design/copy";
import type { Speech } from "../lib/speaker";
import type { Line } from "../types";
import { SpeakingIndicator } from "./SpeakingIndicator";
import "./Captions.css";

const CHARS_PER_SECOND = 15; // about how fast the guide speaks

// Lyrics-style captions. The newest turn is large and pinned to the bottom; the agent's text arrives
// whole before it is spoken, so a turn too long for the space scrolls at speaking pace, karaoke-like.
// Older turns sit above it, step down and fade out the top. The visitor's words are lantern-coloured.
// While the guide answers, the visitor's last words stay pinned at the top so the audience knows what was asked.
export function Captions({ lines, speech }: { lines: Line[]; speech: Speech }) {
  const now = lines[lines.length - 1];
  const asked = now?.role === "agent" ? lastUserLine(lines) : null;
  const past = lines.slice(-3, -1).filter((l) => l !== asked);
  const first = lines.length - 1 - past.length;
  return (
    <section className="captions" aria-live="polite">
      {asked && (
        <p key={asked.text} className="caption caption--asked caption--user">
          <span className="caption__who label">{COPY.visitorAsked}</span>
          <span className="caption__text">{asked.text}</span>
        </p>
      )}
      <div className="captions__past">
        {past.map((l, i) => (
          <p key={`${first + i}:${l.text}`} className={`caption caption--age${past.length - i} caption--${l.role}`}>
            <span className="caption__who label">{who(l)}</span>
            <span className="caption__text">{l.text}</span>
          </p>
        ))}
      </div>
      {now && <NowLine key={`${lines.length}:${now.text}`} line={now} speech={speech} />}
    </section>
  );
}

function NowLine({ line, speech }: { line: Line; speech: Speech }) {
  const windowRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const win = windowRef.current, text = textRef.current;
    if (!win || !text) return;
    const measure = () => {
      const overflow = text.scrollHeight - win.clientHeight > 4 ? text.scrollHeight - win.clientHeight : 0;
      win.classList.toggle("caption__window--scrolls", overflow > 0);
      win.style.setProperty("--scroll", `${-overflow}px`);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(win);
    return () => ro.disconnect();
  }, [line.text]);
  const style = { "--read": `${line.text.length / CHARS_PER_SECOND}s` } as CSSProperties;
  return (
    <p className={`caption caption--now caption--${line.role}`}>
      <span className="caption__who label">
        <SpeakingIndicator state={speech} />
        {who(line)}
        <span className="caption__state">{COPY.speech[speech]}</span>
      </span>
      <span className="caption__window" ref={windowRef} style={style}>
        <span className="caption__text" ref={textRef}>{line.text}</span>
      </span>
    </p>
  );
}

function lastUserLine(lines: Line[]): Line | null {
  for (let i = lines.length - 1; i >= 0; i--) if (lines[i].role === "user") return lines[i];
  return null;
}

const who = (l: Line) => (l.role === "user" ? COPY.visitor : COPY.guide);
