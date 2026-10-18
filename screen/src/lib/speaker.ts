// screen.py sends no audio state, so who is talking is inferred from the transcript.

export type Speech = "speaking" | "listening" | "thinking";
export const SPEAKING_MS = 4000;

/** changedAt: when the newest transcript line last changed (null = never). thinking: Gemini is working. */
export function speechState(changedAt: number | null, now: number, thinking: boolean): Speech {
  if (changedAt !== null && now - changedAt < SPEAKING_MS) return "speaking";
  return thinking ? "thinking" : "listening";
}
