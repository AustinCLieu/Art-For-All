// The JSON that screen.py serves at /api/state. Keep in sync with screen.snapshot().

export type Role = "user" | "agent";

export interface Line {
  role: Role;
  text: string;
}

export interface SectionSummary {
  number: number;
  name: string;
  location: string;
}

export interface Painting {
  title: string;
  artist: string;
  year: string;
  image: string | null;
  sections: SectionSummary[];
}

export interface Section extends SectionSummary {
  index: number;
  bbox: [number, number, number, number];
  grid: number[][];
  frame: string;
  // 10,000-pin simulation (docs/relief.md): 100x100 PNG URLs, or null if this section has none.
  relief: string | null;       // grayscale: brightness = pin height, 0 = down, 255 = fully up
  relief_color: string | null; // the painting under each pin, black outside the painting
}

export type Status = "idle" | "working" | "done" | "failed";

export interface Activity {
  status: Status;
  detail: string;
}

export interface State {
  hardware: boolean;
  transcript: Line[];
  painting: Painting | null;
  section: Section | null;
  activity: {
    elevenlabs: Activity;
    gemini: Activity;
    creao: Activity;
    browser_use: Activity;
  };
}
