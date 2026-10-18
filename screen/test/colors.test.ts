import { test } from "node:test";
import assert from "node:assert/strict";
import { averageColor, cellColors, css, lift, LANTERN, type Pixels } from "../src/lib/colors.ts";

function image(width: number, height: number, at: (x: number, y: number) => [number, number, number]): Pixels {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++) {
      const [r, g, b] = at(x, y);
      data.set([r, g, b, 255], (y * width + x) * 4);
    }
  return { data, width, height };
}

test("averageColor averages and rounds", () => {
  const px = image(2, 1, (x) => (x === 0 ? [255, 0, 0] : [0, 0, 255]));
  assert.deepEqual(averageColor(px), [128, 0, 128]);
});

test("averageColor outside the image falls back to lantern", () => {
  assert.deepEqual(averageColor(image(2, 2, () => [0, 0, 0]), 5, 5, 6, 6), LANTERN);
});

test("cellColors splits the bbox into a 10x10 grid", () => {
  const px = image(10, 10, (x, y) => [x * 20, y * 20, 0]);
  const cells = cellColors(px, [0, 0, 1, 1], 0);
  assert.equal(cells.length, 10);
  assert.equal(cells[0].length, 10);
  assert.deepEqual(cells[3][7], [140, 60, 0]);
});

test("lift raises dark colours to the lightness floor and keeps bright ones", () => {
  assert.deepEqual(lift([0, 0, 0]), [140, 140, 140]);
  assert.deepEqual(lift([20, 0, 0]), [255, 26, 26]);
  assert.deepEqual(lift(LANTERN), LANTERN);
});

test("css writes modern rgb()", () => {
  assert.equal(css([1, 2, 3]), "rgb(1 2 3)");
  assert.equal(css([1, 2, 3], 0.12), "rgb(1 2 3 / 0.12)");
});
