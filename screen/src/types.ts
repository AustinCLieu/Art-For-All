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
