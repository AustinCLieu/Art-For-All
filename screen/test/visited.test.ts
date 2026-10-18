import { test } from "node:test";
import assert from "node:assert/strict";
import { NO_VISITS, visit } from "../src/lib/visited.ts";

test("a new painting starts a new tour", () => {
  const a = visit(NO_VISITS, "Mona Lisa", 1);
  assert.deepEqual(a, { title: "Mona Lisa", numbers: [1] });
  assert.deepEqual(visit(a, "The Starry Night", 2), { title: "The Starry Night", numbers: [2] });
  assert.deepEqual(visit(a, "The Starry Night", null), { title: "The Starry Night", numbers: [] });
});

test("parts are remembered once, in the order shown", () => {
  let v = visit(NO_VISITS, "Mona Lisa", 1);
  v = visit(v, "Mona Lisa", 3);
  v = visit(v, "Mona Lisa", 1);
  assert.deepEqual(v.numbers, [1, 3]);
});

test("nothing new returns the same object", () => {
  const v = visit(NO_VISITS, "Mona Lisa", 1);
  assert.equal(visit(v, "Mona Lisa", 1), v);
  assert.equal(visit(v, "Mona Lisa", null), v);
});
