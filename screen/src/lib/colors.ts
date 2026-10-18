// Colours taken from the painting: the room's glow and each raised ball. Pure, so node:test can run it.

export type RGB = [number, number, number];
export interface Pixels {
  data: ArrayLike<number>; // RGBA, row by row (ImageData fits)
  width: number;
  height: number;
}

export const LANTERN: RGB = [255, 181, 71];

/** Mean colour of the pixel rectangle [x0, x1) × [y0, y1); lantern if it falls outside the image. */
export function averageColor(px: Pixels, x0 = 0, y0 = 0, x1 = px.width, y1 = px.height): RGB {
  const xa = Math.max(0, Math.floor(x0));
  const ya = Math.max(0, Math.floor(y0));
  const xb = Math.min(px.width, Math.max(xa + 1, Math.floor(x1)));
  const yb = Math.min(px.height, Math.max(ya + 1, Math.floor(y1)));
  let r = 0, g = 0, b = 0, n = 0;
  for (let y = ya; y < yb; y++) {
    for (let x = xa; x < xb; x++) {
      const i = (y * px.width + x) * 4;
      r += px.data[i];
      g += px.data[i + 1];
      b += px.data[i + 2];
      n++;
    }
  }
  return n ? [Math.round(r / n), Math.round(g / n), Math.round(b / n)] : LANTERN;
}

/** 10×10 colours for a bbox ([x0, y0, x1, y1] as fractions), each lifted so it glows on black. */
export function cellColors(px: Pixels, bbox: [number, number, number, number], minLightness = 0.55): RGB[][] {
  const [x0, y0, x1, y1] = bbox;
  const left = x0 * px.width;
  const top = y0 * px.height;
  const cw = ((x1 - x0) * px.width) / 10;
  const ch = ((y1 - y0) * px.height) / 10;
  return Array.from({ length: 10 }, (_, r) =>
    Array.from({ length: 10 }, (_, c) =>
      lift(averageColor(px, left + c * cw, top + r * ch, left + (c + 1) * cw, top + (r + 1) * ch), minLightness),
    ),
  );
}

/** Raise HSL lightness to at least minLightness, keeping hue and saturation. */
export function lift(c: RGB, minLightness = 0.55): RGB {
  const [r, g, b] = c.map((v) => v / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (l >= minLightness) return c;
  const d = max - min;
  const s = d === 0 ? 0 : Math.min(1, d / (1 - Math.abs(2 * l - 1))); // clamp: float error can exceed 1
  let h = 0;
  if (d !== 0) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60;
    if (h < 0) h += 360;
  }
  return hslToRgb(h, s, minLightness);
}

function hslToRgb(h: number, s: number, l: number): RGB {
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    return Math.round((l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))) * 255);
  };
  return [f(0), f(8), f(4)];
}

export function css([r, g, b]: RGB, alpha = 1): string {
  return alpha === 1 ? `rgb(${r} ${g} ${b})` : `rgb(${r} ${g} ${b} / ${alpha})`;
}
