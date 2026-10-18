import { test } from "node:test";
import assert from "node:assert/strict";
import { pickScene } from "../src/lib/scene.ts";
import type { State } from "../src/types.ts";

const waiting = { status: "idle", detail: "" } as const;
function state(over: Partial<State> = {}): State {
  return {
    hardware: false,
    transcript: [],
    painting: null,
    section: null,
    activity: { elevenlabs: waiting, gemini: waiting, creao: waiting, browser_use: waiting },
    ...over,
  };
}
const painting = { title: "Mona Lisa", artist: "Leonardo da Vinci", year: "c. 1503", image: null, sections: [] };

test("offline when main.py is not answering or nothing arrived yet", () => {
  assert.equal(pickScene(state(), false), "offline");
  assert.equal(pickScene(null, true), "offline");
});

test("touring as soon as a painting is open", () => {
  assert.equal(pickScene(state({ painting }), true), "touring");
});

test("looking-up while Gemini works and no painting is open", () => {
  const s = state();
  s.activity.gemini = { status: "working", detail: "Looking up The Birth of Venus" };
  assert.equal(pickScene(s, true), "looking-up");
});

test("idle otherwise", () => {
  assert.equal(pickScene(state(), true), "idle");
});
