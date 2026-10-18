import { test } from "node:test";
import assert from "node:assert/strict";
import { SPEAKING_MS, speechState } from "../src/lib/speaker.ts";

test("speaking right after the newest line changed", () => {
  assert.equal(speechState(1000, 1000 + SPEAKING_MS - 1, true), "speaking");
});

test("thinking once the line is old and Gemini is working", () => {
  assert.equal(speechState(1000, 1000 + SPEAKING_MS, true), "thinking");
});

test("listening otherwise, including before anyone spoke", () => {
  assert.equal(speechState(1000, 1000 + SPEAKING_MS, false), "listening");
  assert.equal(speechState(null, 5000, false), "listening");
});
