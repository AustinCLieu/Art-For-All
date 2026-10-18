import type { State } from "../types";

export type Scene = "offline" | "idle" | "looking-up" | "touring";

export function pickScene(state: State | null, online: boolean): Scene {
  if (!online || !state) return "offline";
  const looking = state.activity.gemini.status === "working";
  // A new lookup whose image is ready shows over any painting still on screen from before.
  if (looking && state.preview) return "looking-up";
  if (state.painting) return "touring";
  if (looking) return "looking-up";
  return "idle";
}
