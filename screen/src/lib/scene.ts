import type { State } from "../types";

export type Scene = "offline" | "idle" | "looking-up" | "touring";

export function pickScene(state: State | null, online: boolean): Scene {
  if (!online || !state) return "offline";
  if (state.painting) return "touring";
  if (state.activity.gemini.status === "working") return "looking-up";
  return "idle";
}
