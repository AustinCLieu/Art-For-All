// The 10,000-pin simulation's data (docs/relief.md), kept free of three.js and the DOM so node can test it.

export interface Pixels { width: number; height: number; data: Uint8ClampedArray }

// heights[r * size + c] in 0..1; colors[(r * size + c) * 3 + k] = sRGB channel k in 0..1. Row 0 = far edge.
export interface PinField { size: number; heights: Float32Array; colors: Float32Array }

export const RESOLUTIONS: readonly number[] = [10, 20, 25, 50, 100];

// Pin height = red channel of the relief; colour = the relief_color pixel under it.
export function fieldFromPixels(height: Pixels, color: Pixels): PinField {
  const size = height.width;
  const heights = new Float32Array(size * size);
  const colors = new Float32Array(size * size * 3);
  for (let i = 0; i < size * size; i++) {
    heights[i] = height.data[i * 4] / 255;
    for (let k = 0; k < 3; k++) colors[i * 3 + k] = color.data[i * 4 + k] / 255;
  }
  return { size, heights, colors };
}

// n x n pins, each the average of a (size/n) x (size/n) block. n must divide size.
export function resample(f: PinField, n: number): PinField {
  if (n === f.size) return f;
  const b = f.size / n;
  const heights = new Float32Array(n * n);
  const colors = new Float32Array(n * n * 3);
  for (let r = 0; r < n; r++)
    for (let c = 0; c < n; c++) {
      let h = 0;
      const rgb = [0, 0, 0];
      for (let y = r * b; y < (r + 1) * b; y++)
        for (let x = c * b; x < (c + 1) * b; x++) {
          const i = y * f.size + x;
          h += f.heights[i];
          for (let k = 0; k < 3; k++) rgb[k] += f.colors[i * 3 + k];
        }
      const o = r * n + c;
      heights[o] = h / (b * b);
      for (let k = 0; k < 3; k++) colors[o * 3 + k] = rgb[k] / (b * b);
    }
  return { size: n, heights, colors };
}

// Today's board: the section's real up/down grid, coloured like the painting. f must be 10x10.
export function boardField(f: PinField, grid: number[][]): PinField {
  const heights = new Float32Array(100);
  for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) heights[r * 10 + c] = grid[r]?.[c] ? 1 : 0;
  return { size: 10, heights, colors: f.colors };
}
