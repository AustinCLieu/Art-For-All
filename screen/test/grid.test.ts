import { test } from "node:test";
import assert from "node:assert/strict";
import { normalizeGrid } from "../src/lib/grid.ts";

test("a good grid passes through as 0/1", () => {
  const g = Array.from({ length: 10 }, (_, r) => Array.from({ length: 10 }, (_, c) => (r === c ? 1 : 0)));
  assert.deepEqual(normalizeGrid(g), g);
});

test("short rows, missing rows, junk and non-arrays become a clean 10x10", () => {
  const out = normalizeGrid([[1, 1], "x", [0, 2, "1", null]]);
  assert.equal(out.length, 10);
  assert.ok(out.every((row) => row.length === 10 && row.every((v) => v === 0 || v === 1)));
  assert.deepEqual(out[0].slice(0, 3), [1, 1, 0]);
  assert.deepEqual(out[2].slice(0, 4), [0, 1, 1, 0]);
  assert.deepEqual(normalizeGrid(undefined), normalizeGrid([]));
});
