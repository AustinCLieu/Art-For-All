# 10,000-pin simulation: data for the 3D pin bed

The real board is 10x10 pins, up or down (`grid`). To show what better hardware could do, every section
also gets a **100x100 heightmap**: 10,000 pins, each at its own height, like a pin-art bed shaped to the
painting. Backend: `relief.py` (Austin). Frontend: the 3D view (Harvey). Label it on screen as a
simulation.

## Where the data is

Built: press `P` on the audience screen (`screen/src/components/PinModal.tsx`, three.js in `src/lib/pinScene.ts`).

`/api/state` -> `section.relief` and `section.relief_color`: URLs, or `null` when a section has none
(stub paintings, or a relief that failed). They change with the section, like `grid`.

```json
"section": {"number": 1, "name": "her figure", "grid": [[...]],
            "relief": "/cache/mona-lisa-1-relief.png?v=1792300000",
            "relief_color": "/cache/mona-lisa-1-relief-color.png?v=1792300000"}
```

Both are 100x100 PNGs, about 10 KB each. Fetch them once per section: the state poll only carries the URLs.
The `?v=` changes when a relief is made again, so the browser never shows a stale one.

## Format

- **`relief`**: grayscale. Pin height = the red channel of each pixel: `0` = fully down, `255` = fully up.
  Inside the painting the lowest pin is about 26 (10%), so the part stands apart from the bars.
- **`relief_color`**: the painting's colour under each pin, for colouring the pin tops.
- Pixel (x, y) = pin in column x, row y. Row 0 = the top (the edge farthest from the visitor), column 0 =
  the visitor's left, the same as `grid`.
- The part is centered and never stretched, like the 10x10 grid: a tall part has bars at the left and
  right, a wide one at the top and bottom. Bars are height 0 and black.
- The heights come from a depth model (Depth Anything V2) on the section's crop, plus 20% brushwork and
  edges, so near things (a face, the wave's crest) stand up and far things (sky, background) sink.

## Reading it in the browser

`usePaintingPixels` in `screen/src/lib/hooks.ts` already turns an image URL into pixels. Same idea:

```ts
async function pixels(url: string): Promise<ImageData> {
  const img = new Image();
  img.src = url;
  await img.decode();
  const canvas = document.createElement("canvas");
  canvas.width = img.width;
  canvas.height = img.height;
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(img, 0, 0);
  return ctx.getImageData(0, 0, img.width, img.height);
}

const h = await pixels(section.relief);         // heights[r][c] = h.data[(r * 100 + c) * 4] / 255
const col = await pixels(section.relief_color); // rgb at the same index: data[i], data[i + 1], data[i + 2]
```

## Ideas for the view (your call)

- three.js `InstancedMesh`: one pin shape drawn 10,000 times is a single draw call, so it stays smooth.
  Set each instance's height from `h`, its colour from `col`, and add `OrbitControls` to look from the top
  or from the side.
- Animate between sections (pins sliding to their new heights) to sell the "bed reshaping" feel.
- Two sliders make the pitch: resolution (10, 20, 25, 50, 100 pins per side: average 100/N x 100/N
  blocks) and levels (2, 4, 16, 256: `Math.round(v * (L - 1)) / (L - 1)`). All of it comes from the one
  heightmap; at 10 pins and 2 levels it looks like today's board.

## Making reliefs

- Opening a painting with missing reliefs starts them in the background; the tour never waits. They land
  one section at a time in tour order, about 0.2-1 s each (plus ~9 s to load the model the first time),
  so for a new painting expect `relief: null` for a few seconds, then the URL. Show the 10x10 board or a
  flat bed until it arrives.
- The four demo paintings already have theirs (committed in `cache/`).
- By hand: `python relief.py` (sections without one) or `python relief.py --force` (all, after tuning).
- Needs `torch` and `transformers` (in `requirements.txt`). Without them, or before the model's first
  ~100 MB download, reliefs fall back to the painting's brightness, which looks flatter.
