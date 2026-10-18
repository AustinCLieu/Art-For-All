import { COPY } from "../design/copy";
import type { Speech } from "../lib/speaker";
import type { Line } from "../types";
import { SpeakingIndicator } from "./SpeakingIndicator";
import "./Captions.css";

// The last four lines as captions: newest largest, older ones step down and fade.
export function Captions({ lines, speech }: { lines: Line[]; speech: Speech }) {
  const recent = lines.slice(-4);
  const first = lines.length - recent.length;
  return (
    <section className="captions" aria-live="polite">
      {recent.map((l, i) => {
        const age = recent.length - 1 - i; // 0 = newest
        return (
          <p key={first + i} className={`caption caption--age${age}`}>
            <span className="caption__who label">
              {age === 0 && <SpeakingIndicator state={speech} />}
              {l.role === "user" ? COPY.visitor : COPY.guide}
              {age === 0 && <span className="caption__state">{COPY.speech[speech]}</span>}
            </span>
            <span className="caption__text">{l.text}</span>
          </p>
        );
      })}
    </section>
  );
}
