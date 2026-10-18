// Every string the audience screen shows. Tone: a museum wall label, never a dashboard.

export const WORDMARK = "ArtForAll";

export const COPY = {
  live: "Live",
  agents: "Agents",
  close: "Close",
  idleHeadline: "Some art is meant to be touched.",
  idleHint: "Say “Show me the Mona Lisa”",
  idleFooter: "Best experienced with your hands.",
  offlineKicker: "The gallery is closed",
  offlineHeadline: "The guide is on a break.",
  offlineHint: "Start main.py to open the gallery.",
  lookingUp: "Finding the parts of the painting",
  nowTouching: "Now touching",
  allDown: "All balls down",
  simulated: "Simulated board",
  mirrored: "Mirrored live",
  ofTheCanvas: "of the canvas",
  guide: "Guide",
  visitor: "Visitor",
  speech: { speaking: "speaking", listening: "listening", thinking: "thinking" },
  drawerTitle: "Behind the scenes",
  onTheWire: "On the wire",
  status: { idle: "Waiting", working: "Working", done: "Done", failed: "Failed" },
} as const;

export const SPONSORS = [
  { key: "elevenlabs", name: "ElevenLabs", job: "Voice guide" },
  { key: "gemini", name: "Gemini", job: "Finds the parts, draws each shape" },
  { key: "creao", name: "Creao", job: "Tactile Tour Writer agent" },
  { key: "browser_use", name: "Browser Use", job: "Reads the museum's website" },
] as const;
