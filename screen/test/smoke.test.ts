import { test } from "node:test";
import assert from "node:assert/strict";

test("node runs TypeScript tests", () => {
  const n: number = 1 + 1;
  assert.equal(n, 2);
});
