import { test } from "node:test";
import assert from "node:assert/strict";
import { boardField, fieldFromPixels, resample, RESOLUTIONS, type Pixels } from "../src/lib/pins.ts";

// size x size RGBA image where pixel (x, y) = fn(x, y) -> [r, g, b]
function img(size: number, fn: (x: number, y: number) => [number, number, number]): Pixels {
  const data = new Uint8ClampedArray(size * size * 4);
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) {
      const [r, g, b] = fn(x, y);
      data.set([r, g, b, 255], (y * size + x) * 4);
    }
  return { width: size, height: size, data };
}

test("heights come from the red channel, colours from the colour image, row-major", () => {
  const h = img(4, (x, y) => [x === 1 && y === 2 ? 255 : 0, 0, 0]);
  const c = img(4, () => [255, 0, 51]);
  const f = fieldFromPixels(h, c);
  assert.equal(f.size, 4);
  assert.equal(f.heights[2 * 4 + 1], 1);
  assert.equal(f.heights[0], 0);
  assert.deepEqual([...f.colors.slice(0, 2)], [1, 0]);
  assert.ok(Math.abs(f.colors[2] - 0.2) < 1e-6); // Float32 can't hold 0.2 exactly
});

test("resample averages blocks of heights and colours", () => {
  // left half 255, right half 0 -> at 2x2 each left cell is 1, right 0; at 1x1 it's 0.5
  const h = img(4, (x) => [x < 2 ? 255 : 0, 0, 0]);
  const f = fieldFromPixels(h, h);
  const two = resample(f, 2);
  assert.deepEqual([...two.heights], [1, 0, 1, 0]);
  const one = resample(f, 1);
  assert.equal(one.size, 1);
  assert.equal(one.heights[0], 0.5);
  assert.equal(one.colors[0], 0.5);
  assert.equal(resample(f, 4), f, "same size returns the field unchanged");
});

test("boardField takes heights from the real 10x10 grid and keeps the colours", () => {
  const f = resample(fieldFromPixels(img(100, () => [128, 10, 20]), img(100, () => [255, 0, 0])), 10);
  const grid = Array.from({ length: 10 }, (_, r) => Array.from({ length: 10 }, (_, c) => (r === 0 && c === 9 ? 1 : 0)));
  const b = boardField(f, grid);
  assert.equal(b.heights[9], 1);
  assert.equal(b.heights[0], 0);
  assert.equal(b.colors[0], 1);
});

test("every resolution divides 100", () => {
  assert.deepEqual([...RESOLUTIONS], [10, 20, 25, 50, 100]);
  assert.ok(RESOLUTIONS.every((n) => 100 % n === 0));
});
