import { test } from "node:test";
import assert from "node:assert/strict";
import { shouldFly } from "../src/lib/flow.ts";

test("flies when the part changes within the same painting", () => {
  assert.equal(shouldFly({ title: "Mona Lisa", number: 1 }, { title: "Mona Lisa", number: 2 }), true);
});

test("does not fly on the first part, a new painting, the same part, or no part", () => {
  assert.equal(shouldFly({ title: null, number: null }, { title: "Mona Lisa", number: 1 }), false);
  assert.equal(shouldFly({ title: "Mona Lisa", number: 2 }, { title: "The Starry Night", number: 1 }), false);
  assert.equal(shouldFly({ title: "Mona Lisa", number: 2 }, { title: "Mona Lisa", number: 2 }), false);
  assert.equal(shouldFly({ title: "Mona Lisa", number: 2 }, { title: "Mona Lisa", number: null }), false);
});
