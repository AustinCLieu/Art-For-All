import { test } from "node:test";
import assert from "node:assert/strict";
import { formatClock, pad } from "../src/lib/format.ts";

test("pad makes two digits", () => {
  assert.equal(pad(2), "02");
  assert.equal(pad(12), "12");
});

test("formatClock is mm:ss and never negative", () => {
  assert.equal(formatClock(0), "00:00");
  assert.equal(formatClock(192_000), "03:12");
  assert.equal(formatClock(-5), "00:00");
  assert.equal(formatClock(3_600_000), "60:00");
});
