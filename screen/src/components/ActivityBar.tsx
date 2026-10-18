import type { State, Status } from "../types";

const CHIPS: { key: keyof State["activity"]; name: string; job: string }[] = [
  { key: "elevenlabs", name: "ElevenLabs", job: "Voice guide" },
  { key: "gemini", name: "Gemini", job: "Finds the parts, draws each shape" },
  { key: "creao", name: "Creao", job: "Tactile Tour Writer agent" },
  { key: "browser_use", name: "Browser Use", job: "Reads the museum's website" },
];

const WORDS: Record<Status, string> = { idle: "Waiting", working: "Working...", done: "Done", failed: "Failed" };

export function ActivityBar({ activity }: { activity: State["activity"] }) {
  return (
    <footer className="activity">
      {CHIPS.map(({ key, name, job }) => {
        const a = activity[key];
        return (
          <div key={key} className={`chip ${a.status}`}>
            <span className="dot" aria-hidden />
            <div>
              <strong>{name}</strong> <span className="job">{job}</span>
              <p className="detail">{a.detail || WORDS[a.status]}</p>
            </div>
          </div>
        );
      })}
    </footer>
  );
}
