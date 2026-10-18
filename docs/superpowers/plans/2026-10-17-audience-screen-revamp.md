# Audience Screen Revamp ("Borderless Night") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the audience screen (`screen/`) as the "Borderless Night" design: Paper file first (story,
research, design system, components, screens, storyboard), then React code that matches it, then a
decision record for the Devpost Paper-track write-up.

**Architecture:** Frontend only. `screen.py`, the `/api/state` JSON, `types.ts` and `useScreenState.ts` are
untouched. Pure logic lives in `screen/src/lib/*.ts` and is tested with Node's built-in test runner.
React hooks live in `lib/hooks.ts`. Each component is one `.tsx` plus one `.css`. All tokens are in
`design/tokens.css`, using the same names as the Paper file's tokens.

**Tech Stack:** React 18.3 + TypeScript 5.6 + Vite 5.4 (existing), @fontsource fonts (new),
node:test on Node 24 (type stripping, no new test dependency), Paper MCP, Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-10-17-audience-screen-revamp-design.md`
(read it first; inspiration codes such as `V01` point into `docs/design/inspiration.md`).

## Global Constraints

- Only frontend files change: nothing in `screen.py`, `main.py`, `paintings.py`, `test_screen.py`, or the JSON contract.
- Colours (exact): ink `#08090B`, stone `#131518`, stone-2 `#1C1F23`, paper `#F2EADC`, paper-dim `#B4AB9C`,
  paper-faint `#7E776D` (decoration and ≥24px text only), lantern `#FFB547` (the only accent: "now"),
  moss `#8CC48A` and koi `#FF6B4A` (drawer status only).
- Fonts: Instrument Serif (display, title, kicker, numeral), Instrument Sans (captions, body), JetBrains Mono
  500 uppercase +0.14em (labels). Self-hosted via @fontsource. No text smaller than 13px.
- Shape language: circles and 1px `stone-2` hairlines only. No cards, no rounded panels, no drop shadows.
  Glow is the only depth.
- Status is never colour-only: every status also shows a word.
- Copy reads like a museum placard; all visible strings live in `screen/src/design/copy.ts`.
- Every animation has a reduced-motion fallback (opacity fade ≤200ms or none).
- Layout designed at 1920×1080, scales to 1440×900, must also fit a 1280×720 projector with no page scroll
  (`@media (max-height: 800px)` tightening), and stacks below 1100px wide.
- Keep the robustness rules from commit 5066f10: grids are always drawn as exactly 10×10 of 0/1
  (`normalizeGrid`), a painting image that fails to load is hidden (no broken-image icon), and
  `useScreenState.ts` (2s fetch timeout) stays untouched.
- After UI changes the built `screen/dist/` is committed (`cd screen && npm run build`).
- Feature freeze 2026-10-18 10:00 PT.
- Commits: no attribution lines.

## File map

```
screen/package.json                 + 3 font deps, + "test" script
screen/src/main.tsx                 font imports + design/tokens.css (styles.css removed in Task 15)
screen/src/design/tokens.css        all tokens + base element styles + shared keyframes
screen/src/design/copy.ts           all strings, WORDMARK, SPONSORS
screen/src/lib/colors.ts            averageColor, cellColors, lift, css, LANTERN, RGB, Pixels
screen/src/lib/format.ts            pad, formatClock
screen/src/lib/scene.ts             pickScene, Scene
screen/src/lib/speaker.ts           speechState, Speech, SPEAKING_MS
screen/src/lib/visited.ts           visit, Visited, NO_VISITS
screen/src/lib/flow.ts              shouldFly, Shown, LIT_MS, FLY_MS, ROW_MS
screen/src/lib/idleShapes.ts        IDLE_SHAPES, EMPTY_GRID
screen/src/lib/grid.ts              normalizeGrid
screen/src/lib/motion.ts            reducedMotion
screen/src/lib/hooks.ts             usePaintingPixels, useSpeaker, useVisited, useFlow, useSessionClock
screen/src/components/*.tsx + .css  TopStrip Room PaintingStage Spotlight Placard BallGrid TouchBoard
                                    Captions SpeakingIndicator TourRail AgentDrawer IdleScreen LookingUp BorderlessFlow
screen/src/App.tsx                  rewritten in Task 15
screen/test/*.test.ts               node:test files for lib/
DELETE: screen/src/styles.css, components/PaintingView.tsx, Transcript.tsx, ActivityBar.tsx, Board.tsx (old)
docs/design/screens/                before/after screenshots (PNG)
docs/design/paper/                  Paper exports (PNG per artboard + combined PDF)
docs/design/design-decisions.md     Devpost-facing decision record
```

---

### Task 1: Capture "before" screenshots of the current screen

**Files:**
- Create: `docs/design/screens/before-touring-1920.png`, `before-touring-1440.png`, `before-empty-1920.png`

**Interfaces:**
- Consumes: the current committed `screen/dist/` (old UI). Do not rebuild before this task.
- Produces: images used in Task 17's before/after comparison.

- [ ] **Step 1: Start the old screen in demo mode on port 8001 (background)**

Run: `source .venv/bin/activate && python screen.py --demo --port 8001` (run_in_background)
Expected: prints `Audience screen: http://127.0.0.1:8001`

- [ ] **Step 2: Screenshot with the Playwright MCP**

Load `mcp__playwright__browser_resize`, `browser_navigate`, `browser_take_screenshot`, `browser_wait_for`
with ToolSearch. Then:
1. resize to 1920×1080, navigate to `http://127.0.0.1:8001`, wait 8s (a painting section is showing), and
   screenshot to `docs/design/screens/before-touring-1920.png`;
2. resize to 1440×900 and screenshot to `before-touring-1440.png`.

- [ ] **Step 3: Empty-state screenshot**

Stop the demo process. Start a server with no tour:
`python -c "import screen,threading; screen.start_screen(8002); threading.Event().wait()"` (background).
Navigate to `http://127.0.0.1:8002` at 1920×1080 and screenshot to `before-empty-1920.png`. Stop the server.

- [ ] **Step 4: Commit**

```bash
git add docs/design/screens/before-*.png
git commit -m "docs: screenshots of the audience screen before the revamp"
```

---

### Task 2: Foundation: fonts, tokens, copy, test harness

**Files:**
- Modify: `screen/package.json`
- Create: `screen/src/design/tokens.css`, `screen/src/design/copy.ts`, `screen/test/smoke.test.ts`
- Modify: `screen/src/main.tsx`

**Interfaces:**
- Produces: CSS custom properties (names below) used by every component and by the Paper file in
  Task 5; `COPY`, `WORDMARK`, `SPONSORS` from `design/copy.ts`; the `npm test` command.

- [ ] **Step 1: Install fonts (exact versions)**

Run: `cd screen && npm install --save-exact @fontsource/instrument-serif @fontsource-variable/instrument-sans @fontsource-variable/jetbrains-mono`
Expected: three entries added to `dependencies` with no `^`.

- [ ] **Step 2: Add the test script to `screen/package.json`**

In `"scripts"` add `"test": "node --test test/*.test.ts"` so it reads:

```json
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "node --test test/*.test.ts"
  },
```

- [ ] **Step 3: Write a smoke test proving the harness runs TypeScript**

`screen/test/smoke.test.ts`:

```ts
import { test } from "node:test";
import assert from "node:assert/strict";

test("node runs TypeScript tests", () => {
  const n: number = 1 + 1;
  assert.equal(n, 2);
});
```

Run: `cd screen && npm test`
Expected: `# pass 1`, `# fail 0` (an ExperimentalWarning about type stripping is fine).

- [ ] **Step 4: Create `screen/src/design/tokens.css`**

```css
/* "Lantern Water": the teamLab Planets water room at night. Every colour is an object in that room.
   Token names match the Paper file "Tactile Art Guide — Design"; change both together. */
:root {
  color-scheme: dark;

  --color-ink: #08090b;        /* black water: page */
  --color-stone: #131518;      /* wet stone: drawer */
  --color-stone-2: #1c1f23;    /* stone edge: hairlines, empty wells */
  --color-paper: #f2eadc;      /* lantern paper: text (16.7:1) */
  --color-paper-dim: #b4ab9c;  /* paper in shadow: secondary text (8.8:1) */
  --color-paper-faint: #7e776d;/* decoration and >=24px text only (4.5:1) */
  --color-lantern: #ffb547;    /* lantern flame: the one accent, "now" */
  --color-moss: #8cc48a;       /* drawer: done */
  --color-koi: #ff6b4a;        /* drawer: failed */

  --font-serif: "Instrument Serif", Georgia, serif;
  --font-sans: "Instrument Sans Variable", "Instrument Sans", system-ui, sans-serif;
  --font-mono: "JetBrains Mono Variable", "JetBrains Mono", ui-monospace, monospace;
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;

  /* Designed at 1920 wide; 75% at 1440; never smaller than the 1440 size. */
  --text-numeral: clamp(270px, 18.75vw, 360px);
  --text-display: clamp(60px, 4.1667vw, 80px);
  --text-title: clamp(36px, 2.5vw, 48px);
  --text-kicker: clamp(22px, 1.4583vw, 28px);
  --text-caption-now: clamp(24px, 1.5625vw, 30px);
  --text-body: clamp(17px, 1.0417vw, 20px);
  --text-label: clamp(13px, 0.7292vw, 14px);
  --leading-display: 1;
  --leading-caption-now: 1.333;
  --leading-body: 1.5;
  --tracking-display: -0.02em;
  --tracking-label: 0.14em;

  --spacing-1: 4px;
  --spacing-2: 8px;
  --spacing-3: 12px;
  --spacing-4: 16px;
  --spacing-5: 24px;
  --spacing-6: 32px;
  --spacing-7: 48px;
  --spacing-8: 64px;
  --spacing-9: 96px;
  --spacing-10: 128px;
  --gutter: clamp(48px, 5vw, 96px);
  --margin-x: clamp(24px, 3.3333vw, 64px);
  --margin-y: clamp(20px, 2.0833vw, 40px);
  --radius-full: 9999px;
  --breakpoint-stack: 1100px;

  --ease-rise: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-light: cubic-bezier(0.22, 1, 0.36, 1);
  --dur-fade: 200ms;
  --dur-ball: 400ms;
  --stagger-row: 70ms;
  --dur-spot: 600ms;
  --dur-flow: 900ms;
  --dur-ripple: 1600ms;
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --dur-ball: var(--dur-fade);
    --stagger-row: 0ms;
    --dur-spot: var(--dur-fade);
  }
}

* { box-sizing: border-box; }
html, body, #root { margin: 0; min-height: 100%; }
body {
  background: var(--color-ink);
  color: var(--color-paper);
  font-family: var(--font-sans);
  font-size: var(--text-body);
  line-height: var(--leading-body);
  -webkit-font-smoothing: antialiased;
}

/* Mono museum-label text. */
.label {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: var(--font-weight-medium);
  letter-spacing: var(--tracking-label);
  text-transform: uppercase;
  line-height: 1.4;
}

/* Keycap button: "[S] Agents" and "[S] Close". */
.key-button {
  all: unset;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  color: var(--color-paper-dim);
}
.key-button:hover, .key-button[aria-pressed="true"] { color: var(--color-paper); }
.key-button:focus-visible { outline: 1px solid var(--color-lantern); outline-offset: 4px; }
kbd {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  padding: 1px 6px;
  border: 1px solid var(--color-paper-faint);
  border-radius: 3px;
}

@keyframes pulse { 50% { opacity: 0.35; } }
```

- [ ] **Step 5: Create `screen/src/design/copy.ts`**

```ts
// Every string the audience screen shows. Tone: a museum wall label, never a dashboard.

export const WORDMARK = "Tactile Art Guide"; // placeholder until the team picks the real name

export const COPY = {
  live: "Live",
  agents: "Agents",
  close: "Close",
  idleHeadline: "Some art is meant to be touched.",
  idleHint: "Say “Show me the Mona Lisa”",
  idleFooter: "Best experienced with your hands.",
  offlineKicker: "The gallery is closed",
  offlineHeadline: "The guide is on a break.",
  offlineHint: "Start main.py to open the gallery.",
  lookingUp: "Finding the parts of the painting",
  nowTouching: "Now touching",
  allDown: "All balls down",
  simulated: "Simulated board",
  mirrored: "Mirrored live",
  ofTheCanvas: "of the canvas",
  guide: "Guide",
  visitor: "Visitor",
  speech: { speaking: "speaking", listening: "listening", thinking: "thinking" },
  drawerTitle: "Behind the scenes",
  onTheWire: "On the wire",
  status: { idle: "Waiting", working: "Working", done: "Done", failed: "Failed" },
} as const;

export const SPONSORS = [
  { key: "elevenlabs", name: "ElevenLabs", job: "Voice guide" },
  { key: "gemini", name: "Gemini", job: "Finds the parts, draws each shape" },
  { key: "creao", name: "Creao", job: "Tactile Tour Writer agent" },
  { key: "browser_use", name: "Browser Use", job: "Reads the museum's website" },
] as const;
```

- [ ] **Step 6: Load fonts and tokens in `screen/src/main.tsx`**

Replace the file with (the old `styles.css` stays imported until Task 15 so the old UI keeps working):

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";
import "@fontsource-variable/instrument-sans";
import "@fontsource-variable/jetbrains-mono";
import "./design/tokens.css";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 7: Type-check**

Run: `cd screen && npx tsc -p .`
Expected: no output, exit 0.

- [ ] **Step 8: Commit**

```bash
git add screen/package.json screen/package-lock.json screen/src/main.tsx screen/src/design screen/test/smoke.test.ts
git commit -m "screen: design tokens, self-hosted fonts, copy and node:test harness"
```

---

### Task 3: Pure logic modules (TDD)

**Files:**
- Create: `screen/src/lib/colors.ts`, `format.ts`, `scene.ts`, `speaker.ts`, `visited.ts`, `flow.ts`, `grid.ts`, `idleShapes.ts`, `motion.ts`
- Test: `screen/test/colors.test.ts`, `format.test.ts`, `scene.test.ts`, `speaker.test.ts`, `visited.test.ts`, `flow.test.ts`, `grid.test.ts`
- Delete: `screen/test/smoke.test.ts`

**Interfaces:**
- Consumes: `State`, `Line` types from `screen/src/types.ts` (type-only imports).
- Produces (exact signatures used by later tasks):
  - `type RGB = [number, number, number]`; `interface Pixels { data: ArrayLike<number>; width: number; height: number }`
  - `LANTERN: RGB`; `averageColor(px: Pixels, x0?: number, y0?: number, x1?: number, y1?: number): RGB`
  - `cellColors(px: Pixels, bbox: [number, number, number, number], minLightness?: number): RGB[][]`
  - `lift(c: RGB, minLightness?: number): RGB`; `css(c: RGB, alpha?: number): string`
  - `pad(n: number): string`; `formatClock(ms: number): string`
  - `type Scene = "offline" | "idle" | "looking-up" | "touring"`; `pickScene(state: State | null, online: boolean): Scene`
  - `type Speech = "speaking" | "listening" | "thinking"`; `SPEAKING_MS = 4000`; `speechState(changedAt: number | null, now: number, thinking: boolean): Speech`
  - `interface Visited { title: string | null; numbers: number[] }`; `NO_VISITS: Visited`; `visit(prev: Visited, title: string | null, number: number | null): Visited`
  - `interface Shown { title: string | null; number: number | null }`; `shouldFly(prev: Shown, next: Shown): boolean`; `LIT_MS = 350`, `FLY_MS = 900`, `ROW_MS = 30`
  - `IDLE_SHAPES: { title: string; part: string; grid: number[][] }[]`; `EMPTY_GRID: number[][]`
  - `normalizeGrid(grid: unknown): number[][]` (always 10 rows × 10 cells of 0/1)
  - `reducedMotion(): boolean`

Tests import with the `.ts` extension (Node requires it). `src/lib` files may only import other files as
`import type` (erased by Node), so the tests can load them.

- [ ] **Step 1: Write the failing tests**

`screen/test/colors.test.ts`:

```ts
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
```

`screen/test/format.test.ts`:

```ts
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
```

`screen/test/scene.test.ts`:

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { pickScene } from "../src/lib/scene.ts";
import type { State } from "../src/types.ts";

const waiting = { status: "idle", detail: "" } as const;
function state(over: Partial<State> = {}): State {
  return {
    hardware: false,
    transcript: [],
    painting: null,
    section: null,
    activity: { elevenlabs: waiting, gemini: waiting, creao: waiting, browser_use: waiting },
    ...over,
  };
}
const painting = { title: "Mona Lisa", artist: "Leonardo da Vinci", year: "c. 1503", image: null, sections: [] };

test("offline when main.py is not answering or nothing arrived yet", () => {
  assert.equal(pickScene(state(), false), "offline");
  assert.equal(pickScene(null, true), "offline");
});

test("touring as soon as a painting is open", () => {
  assert.equal(pickScene(state({ painting }), true), "touring");
});

test("looking-up while Gemini works and no painting is open", () => {
  const s = state();
  s.activity.gemini = { status: "working", detail: "Looking up The Birth of Venus" };
  assert.equal(pickScene(s, true), "looking-up");
});

test("idle otherwise", () => {
  assert.equal(pickScene(state(), true), "idle");
});
```

`screen/test/speaker.test.ts`:

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { SPEAKING_MS, speechState } from "../src/lib/speaker.ts";

test("speaking right after the newest line changed", () => {
  assert.equal(speechState(1000, 1000 + SPEAKING_MS - 1, true), "speaking");
});

test("thinking once the line is old and Gemini is working", () => {
  assert.equal(speechState(1000, 1000 + SPEAKING_MS, true), "thinking");
});

test("listening otherwise, including before anyone spoke", () => {
  assert.equal(speechState(1000, 1000 + SPEAKING_MS, false), "listening");
  assert.equal(speechState(null, 5000, false), "listening");
});
```

`screen/test/visited.test.ts`:

```ts
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
```

`screen/test/flow.test.ts`:

```ts
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
```

`screen/test/grid.test.ts`:

```ts
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
```

Delete `screen/test/smoke.test.ts`.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `cd screen && npm test`
Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `../src/lib/colors.ts` (and the others).

- [ ] **Step 3: Implement the modules**

`screen/src/lib/colors.ts`:

```ts
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
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
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
```

`screen/src/lib/format.ts`:

```ts
export function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** "03:12" for 192000 ms. Minutes keep counting past 59. */
export function formatClock(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${pad(Math.floor(s / 60))}:${pad(s % 60)}`;
}
```

`screen/src/lib/scene.ts`:

```ts
import type { State } from "../types";

export type Scene = "offline" | "idle" | "looking-up" | "touring";

export function pickScene(state: State | null, online: boolean): Scene {
  if (!online || !state) return "offline";
  if (state.painting) return "touring";
  if (state.activity.gemini.status === "working") return "looking-up";
  return "idle";
}
```

`screen/src/lib/speaker.ts`:

```ts
// screen.py sends no audio state, so who is talking is inferred from the transcript.

export type Speech = "speaking" | "listening" | "thinking";
export const SPEAKING_MS = 4000;

/** changedAt: when the newest transcript line last changed (null = never). thinking: Gemini is working. */
export function speechState(changedAt: number | null, now: number, thinking: boolean): Speech {
  if (changedAt !== null && now - changedAt < SPEAKING_MS) return "speaking";
  return thinking ? "thinking" : "listening";
}
```

`screen/src/lib/visited.ts`:

```ts
export interface Visited {
  title: string | null;
  numbers: number[]; // section numbers shown for this painting, in order
}

export const NO_VISITS: Visited = { title: null, numbers: [] };

export function visit(prev: Visited, title: string | null, number: number | null): Visited {
  if (title !== prev.title) return { title, numbers: number === null ? [] : [number] };
  if (number === null || prev.numbers.includes(number)) return prev;
  return { title, numbers: [...prev.numbers, number] };
}
```

`screen/src/lib/flow.ts`:

```ts
// The Borderless flow: lit cells leave the painting and land on the board. Timings in ms.
export const LIT_MS = 350; // cells glow on the painting before they leave
export const FLY_MS = 900; // same as --dur-flow
export const ROW_MS = 30; // each row leaves a little after the one above

export interface Shown {
  title: string | null;
  number: number | null;
}

/** Fly only between two parts of the same painting (the first part just rises in place). */
export function shouldFly(prev: Shown, next: Shown): boolean {
  return prev.number !== null && next.number !== null && prev.title === next.title && prev.number !== next.number;
}
```

`screen/src/lib/idleShapes.ts`:

```ts
// Section 1 of each demo painting, copied from cache/*.json. The attract screen cycles through them.

export const EMPTY_GRID: number[][] = Array.from({ length: 10 }, () => Array<number>(10).fill(0));

export const IDLE_SHAPES: { title: string; part: string; grid: number[][] }[] = [
  {
    title: "Mona Lisa",
    part: "her figure",
    grid: [
      [0, 0, 0, 1, 1, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0, 1, 0, 0, 0], [0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
      [0, 1, 0, 0, 0, 0, 0, 1, 0, 0], [0, 1, 0, 1, 1, 1, 0, 1, 0, 0], [0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
      [0, 1, 1, 1, 1, 1, 1, 1, 0, 0], [1, 0, 0, 0, 0, 0, 0, 0, 1, 0], [1, 0, 0, 1, 1, 1, 1, 0, 1, 0],
      [0, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    ],
  },
  {
    title: "The Starry Night",
    part: "the swirling sky",
    grid: [
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 0, 0, 0], [0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
      [0, 1, 0, 1, 1, 1, 0, 1, 0, 0], [0, 1, 0, 1, 0, 0, 0, 1, 0, 0], [0, 1, 0, 1, 1, 1, 1, 1, 0, 0],
      [0, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ],
  },
  {
    title: "The Great Wave off Kanagawa",
    part: "the great wave's crest",
    grid: [
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 0],
      [0, 1, 1, 0, 0, 0, 0, 1, 1, 1], [1, 1, 0, 0, 0, 0, 0, 0, 1, 1], [1, 1, 0, 0, 0, 0, 0, 0, 0, 1],
      [1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ],
  },
  {
    title: "Girl with a Pearl Earring",
    part: "her face",
    grid: [
      [0, 0, 0, 1, 1, 1, 1, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
      [0, 1, 1, 1, 1, 1, 1, 1, 1, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
      [0, 1, 1, 1, 1, 1, 1, 1, 1, 0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 0], [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ],
  },
];
```

`screen/src/lib/grid.ts`:

```ts
// Always exactly 10x10 of 0/1, so a short row or junk from the model can't shift every later cell.
export function normalizeGrid(grid: unknown): number[][] {
  const rows = Array.isArray(grid) ? grid : [];
  return Array.from({ length: 10 }, (_, r) => {
    const row: unknown = rows[r];
    return Array.from({ length: 10 }, (_, c) => (Array.isArray(row) && Number(row[c]) ? 1 : 0));
  });
}
```

`screen/src/lib/motion.ts`:

```ts
export function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `cd screen && npm test`
Expected: `# fail 0`; all 21 tests pass.

- [ ] **Step 5: Type-check**

Run: `cd screen && npx tsc -p .`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add screen/src/lib screen/test
git commit -m "screen: pure helpers for painting colours, scenes, speech, tour and flow"
```

---

### Task 4: Paper file, tokens and the Story page

**Files:** the Paper file "Tactile Art Guide — Design" (created via MCP). No repo files.

**Interfaces:**
- Consumes: `screen/src/design/tokens.css` (Task 2) as the single source of token values.
- Produces: a Paper file whose tokens use exactly the CSS names in tokens.css. Tasks 5–9 build on it.

- [ ] **Step 1: Load Paper tools and the guide**

ToolSearch `select:` the Paper tools `get_guide, create_file, create_page, update_pages, create_artboard,
write_html, create_tokens, set_tokens, get_tokens, get_screenshot, update_styles, set_text_content,
duplicate_nodes, finish_working_on_nodes, get_font_family_info, export, export_combined_pdf, get_basic_info`.
Call `get_guide({topic: "paper-mcp-instructions"})` and follow it (small writes, screenshot reviews,
finish_working_on_nodes).

- [ ] **Step 2: Create the file and pages**

`create_file` named `Tactile Art Guide — Design`. Name page 1 `1 · Story` and add pages `2 · Research`,
`3 · Design system`, `4 · Components`, `5 · Screens`, `6 · Borderless flow`.

- [ ] **Step 3: Create the tokens**

Read `screen/src/design/tokens.css`. Pass every custom property in its `:root` block (all `--color-*`,
`--font-*`, `--font-weight-*`, `--text-*`, `--leading-*`, `--tracking-*`, `--spacing-*`, `--radius-*`,
`--breakpoint-*`) to `create_tokens` with the same names and values. For `--text-*`, use the 1920 value
(the third argument of each `clamp()`): numeral 360px, display 80px, title 48px, kicker 28px,
caption-now 30px, body 20px, label 14px. Skip `--gutter`, `--margin-*`, `--ease-*`, `--dur-*` and
`--stagger-row` (motion is documented on page 3 instead). Verify with `get_tokens`.

- [ ] **Step 4: Build the Story artboard (1920×1080, page 1)**

`create_artboard` "Story" 1920×1080 with background `var(--color-ink)`. Build it in small writes:
1. Mono label at the top left, `LA HACKS 2026 · PAPER TRACK`, in paper-dim.
2. Display headline (Instrument Serif 120px, leading 1, tracking −0.02em, max 11ch) at left: "Some art is
   meant to be touched."
3. Kicker (Instrument Serif italic 28px, paper-dim) under it: "We walked through teamLab in Tokyo, knee-deep in
   lit water, and wondered who gets left outside."
4. A three-column row on a 1px stone-2 top rule, each with a mono label and a 20px Instrument Sans paragraph:
   - `THE VISITOR HEARS`: "A voice guide (ElevenLabs) tours a famous painting part by part."
   - `THE VISITOR FEELS`: "A 10×10 board of balls raises the shape of the part being described."
   - `THE ROOM SEES`: "This screen: what the visitor hears and feels, live, for everyone watching."
5. At the right, a 10×10 ball grid (circles, gap 14px, 40px balls): wells `--color-stone-2`, raised balls
   in `--color-lantern` with a `0 0 18px` lantern glow, forming the Mona Lisa "her figure" grid from
   `screen/src/lib/idleShapes.ts`.

- [ ] **Step 5: Review**

`get_screenshot` the artboard. Write the one-line checkpoint verdict (spacing, typography, contrast,
alignment, artboard fit, repetition) and fix anything found. `finish_working_on_nodes`.

---

### Task 5: Research page

**Files:** Paper page `2 · Research`. No repo files.

**Interfaces:**
- Consumes: `docs/design/inspiration.md` (descriptions); the Mobbin image links below (valid until about 2026-11-16).

- [ ] **Step 1: References board (artboard "References", 1920 wide, height fit-content, ink background)**

Title in serif display: "147 screens, 23 that shaped it." Then a 4-column grid of reference tiles. Each tile:
- the image (`<img>` with the URL below, width 100%);
- the mono code and app name;
- one line of take/leave copied from `docs/design/inspiration.md` for that code.

Use these 23 STRONG references (code | app | image URL):

```
B05 | Variant | https://mobbin.com/api/mcp/short/SaGps645
B15 | one year | https://mobbin.com/api/mcp/short/k74y2YMJ
B19 | Tesla | https://mobbin.com/api/mcp/short/5Rl6Qnvd
B20 | Polestar | https://mobbin.com/api/mcp/short/tvWe0Slz
C10 | Mindtrip | https://mobbin.com/api/mcp/short/TYOTmO9X
C11 | Tolan | https://mobbin.com/api/mcp/short/UNymXM8x
T01 | Gusto | https://mobbin.com/api/mcp/short/U2Du1Pp4
T03 | Hers | https://mobbin.com/api/mcp/short/X4XVPXvc
T08 | Etsy | https://mobbin.com/api/mcp/short/tayPpAi2
A07 | Base44 | https://mobbin.com/api/mcp/short/FmSD9HQQ
A12 | n8n | https://mobbin.com/api/mcp/short/6N25KCCH
I03 | Harvest "Time in this Time" | https://mobbin.com/api/mcp/short/EQfBV9QE
I07 | Studio Freight | https://mobbin.com/api/mcp/short/YoTacxbF
I09 | COLLINS | https://mobbin.com/api/mcp/short/FtPt2tIn
I15 | Cosmos | https://mobbin.com/api/mcp/short/eAusrZ2W
I22 | Oryzo | https://mobbin.com/api/mcp/short/FqJTy2Uh
I26 | Chronicle | https://mobbin.com/api/mcp/short/ChWxLwS3
I28 | Cosmos | https://mobbin.com/api/mcp/short/jwh8hcVV
H04 | Substack | https://mobbin.com/api/mcp/short/bEFZtVlP
H10 | Visitors | https://mobbin.com/api/mcp/short/fsOTufiD
V01 | Delphi | https://mobbin.com/api/mcp/short/RowiSW5X
V03 | PlayAI | https://mobbin.com/api/mcp/short/2nGVPpgV
V12 | Delphi | https://mobbin.com/api/mcp/short/gm2kmZBN
```

If Paper refuses remote images, keep the tile without an image (code, app and note only) and say so in the
task report.

- [ ] **Step 2: Patterns and directions (artboard "Synthesis", 1920×1080)**

On the left, the 7 patterns as a numbered list (serif numerals 48px, Instrument Sans 20px text):
1. Darkness, with light as the material.
2. Serif display plus mono labels (museum placard).
3. Dots as the shared language.
4. Huge numerals for "where am I".
5. Hand-made marks beat AI-generic.
6. The UI takes its colour from the art.
7. Avoid AI gradients, glowing orbs, dense log tables and card soup.

On the right, three direction columns:
- A "Borderless Night" (marked CHOSEN in lantern);
- B "Wall Label";
- C "Pin Art".

Each column has one-sentence pros and cons taken from spec §1.

- [ ] **Step 3: Review and finish**

`get_screenshot` both artboards, write the checkpoint verdict, fix any issues, then `finish_working_on_nodes`.

---

### Task 6: Design system page

**Files:** Paper page `3 · Design system`.

- [ ] **Step 1: Colour artboard (1920 wide, fit-content)**

For each of the 9 colour tokens, show a 160px swatch circle and, below it, the token name (mono), the hex,
the scene object (e.g. "black water") and the contrast on ink (paper 16.7:1, paper-dim 8.8:1, paper-faint
4.5:1 ("decoration only"), lantern 11.3:1, moss 9.8:1, koi 7.1:1). Under the swatches, write the three
rules: "One intense colour moment: lantern means now.", "Status is never colour-only.", "Raised balls take
the colour of the painting under them."

- [ ] **Step 2: Type artboard (1920 wide, fit-content)**

One specimen row per `--text-*` token: the token name and size in mono at left, and a sample at its real
size at right:
- numeral "02" (outline: transparent fill, 1px paper-faint stroke);
- display "Mona Lisa";
- title "her eyes";
- kicker "Leonardo da Vinci" (italic);
- caption-now "Her eyes follow you across the room.";
- body "Leonardo painted her without eyebrows.";
- label "NOW TOUCHING · 02 / 05".

- [ ] **Step 3: Space, shape, motion, voice artboard (1920×1080)**

- Spacing: bars for `--spacing-1…10` with their px values.
- Shape: a well, a raised ball, a rail stop (hollow, filled, lantern with halo), and a 1px hairline, with the
  caption "Circles and hairlines. Light is the only depth."
- Motion: a table with token, value and use (from spec §3).
- Voice: two columns, DO and DON'T, with the spec §3 examples.

- [ ] **Step 4: Review and finish**

`get_screenshot`, write the verdict, fix, then `finish_working_on_nodes`.

---

### Task 7: Components page

**Files:** Paper page `4 · Components`. One artboard per component (ink background, fit-content), each
showing every state side by side with a mono caption naming the state.

- [ ] **Step 1: Ball and BallGrid.** States: well (stone-2 circle at 62% scale), raised lantern ball, raised
  ball in a painting colour (use `rgb(196 152 98)` with its glow), breathing (paper-faint well).
- [ ] **Step 2: TopStrip.** Wordmark (Instrument Serif italic 28px), live tag (8px lantern dot with glow,
  mono `LIVE 03:12`), `[S] AGENTS` keycap button, in both drawer-closed and drawer-open states.
- [ ] **Step 3: Spotlight tag.** Four positions: above-right, above-left, below-right, below-left. Each has a
  hand-drawn hook (SVG path `M1 23 C 8 21, 12 9, 19 7 S 33 3, 39 1`, 1.5px lantern, round caps) and the
  mono text `02 · HER EYES` in lantern.
- [ ] **Step 4: SpeakingIndicator.** Three states (speaking, listening, thinking): a ring of 8 dots, each
  3px, on a 20px circle, in lantern. Show speaking with two faded outer rings drawn statically.
- [ ] **Step 5: Captions.** Four lines: newest in Instrument Sans 500 30/40 paper; older lines at 20px in
  paper-dim, then 70% and 45% opacity. Mono speaker labels, with the speaking indicator and the state word
  in lantern on the newest line only.
- [ ] **Step 6: TourRail.** Five stops (2 done, 1 now, 2 next) with hairline connectors: solid paper-dim
  between done stops, dotted paper-faint toward next stops. Mono names below each stop.
- [ ] **Step 7: AgentDrawer.** A 520px stone panel with a 1px stone-2 left rule, serif title "Behind the
  scenes" and four agent rows, one per status: WAITING (paper-faint dot), WORKING (lantern), DONE (moss),
  FAILED (koi), each with the status word. Plus the "On the wire" mono frame row.
- [ ] **Step 8: Board.** The giant outline numeral "02" behind a 10×10 BallGrid, the `SIMULATED BOARD` badge
  at top right, `NOW TOUCHING · 02 / 05` in lantern mono, "her eyes" title, and "top center of the canvas"
  in paper-dim mono.
- [ ] **Step 9: Review and finish.** Screenshot each artboard, write a verdict per artboard, fix, then
  `finish_working_on_nodes`.

---

### Task 8: Screens and storyboard

**Files:** Paper pages `5 · Screens` and `6 · Borderless flow`.

**Interfaces:**
- Consumes: the component artboards from Task 7 (duplicate them with `duplicate_nodes` or
  `<x-paper-clone>`), and painting images.

- [ ] **Step 1: Get painting image URLs**

Run:
`curl -s "https://en.wikipedia.org/w/api.php?action=query&titles=Mona_Lisa|The_Starry_Night&prop=pageimages&piprop=thumbnail&pithumbsize=1200&format=json" -H "User-Agent: TactileArtGuide/1.0 (LA Hacks 2026 design file)"`
Use the two `thumbnail.source` URLs as `<img>` sources.

- [ ] **Step 2: "Touring — Mona Lisa" (1920×1080)**

Grid: 64px side margins, 40px top and bottom, columns 58fr / 42fr, gutter 96px.
- Top strip.
- Left column: the painting (height 720px) with a radial glow behind it (painting average colour at 12%),
  the spotlight on section 2 "her eyes" (bbox 0.36, 0.195 → 0.575, 0.25 of the image: dim outside at 62%
  ink, 1.5px lantern edge), the tag above-right, and the placard below (*Leonardo da Vinci* / Mona Lisa /
  `C. 1503–1506`).
- Right column: the Board (Task 7 Step 8; balls coloured in warm browns sampled from the painting), then
  4 caption lines.
- Bottom: TourRail with her figure (done), her eyes (now), her enigmatic smile, the winding path and
  bridge, the misty mountains (next).

- [ ] **Step 3: More screens**

Duplicate and adapt the touring screen into:
- "Touring — The Starry Night": section 2 "the crescent moon", bbox 0.78, 0.02 → 0.98, 0.28, with the tag
  flipped left; blue glow; balls in blues and yellows.
- "Touring — drawer open": the drawer over the right column.
- "Idle": board at left showing the Mona Lisa idle shape in lantern; at right the kicker
  `Mona Lisa · her figure`, the display headline, the lantern mono hint, and the footer.
- "Offline": idle at 35% board opacity with the offline copy from `copy.ts`.
- "Looking up": a dashed paper-faint 3:4 frame with a lantern sweep band, the label
  `FINDING THE PARTS OF THE PAINTING`, the detail line in serif title "Looking up The Birth of Venus",
  and a breathing board.
- "Touring — 1440": a 1440×900 copy with sizes at 75%.
- "Narrow — 400": a 400 wide, fit-content copy, stacked: painting, placard, board, captions, rail.

- [ ] **Step 4: Storyboard (page 6, four artboards of 960×540)**

Cropped to the painting and the board side by side:
1. "Spotlight glides": the spotlight moving from her figure to her eyes (draw a ghost of the old box at
   30%).
2. "The part lights up": a faint 10% grid over the bbox, with the raised cells of "her eyes" lit in lantern.
3. "Dots fly": the lit dots midway between the painting and the board, with motion trails as 1px lantern
   hairlines.
4. "Balls rise": the board with the balls raised in painting colours and row-stagger arrows in the margin.

Each frame gets a mono caption with its timing: `0–600 MS`, `0–350 MS`, `350–1250 MS`, `+70 MS PER ROW`.

- [ ] **Step 5: Review and finish**

Screenshot every artboard, write the verdicts, fix, then `finish_working_on_nodes`.

---

### Task 9: Export the Paper file into the repo

**Files:**
- Create: `docs/design/paper/*.png`, `docs/design/paper/tactile-art-guide-design.pdf`

- [ ] **Step 1:** `export` each artboard as PNG at 1x into `docs/design/paper/`, named
  `<page-number>-<artboard-name-kebab>.png` (e.g. `5-touring-mona-lisa.png`).
- [ ] **Step 2:** `export_combined_pdf` of all pages to `docs/design/paper/tactile-art-guide-design.pdf`.
- [ ] **Step 3:** `ls docs/design/paper` and confirm one PNG per artboard plus the PDF.
- [ ] **Step 4: Commit**

```bash
git add docs/design/paper
git commit -m "docs: Paper design file exports (story, research, system, components, screens, flow)"
```

---

### Task 10: React hooks

**Files:**
- Create: `screen/src/lib/hooks.ts`

**Interfaces:**
- Consumes: Task 3 modules.
- Produces:
  - `usePaintingPixels(src: string | null): Pixels | null`
  - `useSpeaker(lines: Line[], thinking: boolean): Speech`
  - `useVisited(title: string | null, number: number | null): number[]`
  - `useFlow(title: string | null, section: Section | null): { flowFor: Section | null; held: boolean; landed: () => void }`
  - `useSessionClock(online: boolean): string`

- [ ] **Step 1: Write `screen/src/lib/hooks.ts`**

```ts
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Line, Section } from "../types";
import type { Pixels } from "./colors";
import { shouldFly, type Shown } from "./flow";
import { formatClock } from "./format";
import { reducedMotion } from "./motion";
import { speechState, type Speech } from "./speaker";
import { NO_VISITS, visit } from "./visited";

const SAMPLE_WIDTH = 200; // enough pixels for a 10x10 grid inside small parts

/** The painting's pixels, read once per image. Null while loading or if the canvas can't be read. */
export function usePaintingPixels(src: string | null): Pixels | null {
  const [pixels, setPixels] = useState<Pixels | null>(null);
  useEffect(() => {
    setPixels(null);
    if (!src) return;
    let alive = true;
    const img = new Image();
    img.onload = () => {
      try {
        const w = SAMPLE_WIDTH;
        const h = Math.max(1, Math.round((img.naturalHeight * w) / img.naturalWidth));
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(img, 0, 0, w, h);
        if (alive) setPixels(ctx.getImageData(0, 0, w, h));
      } catch {
        // tainted canvas: callers fall back to lantern
      }
    };
    img.src = src;
    return () => {
      alive = false;
    };
  }, [src]);
  return pixels;
}

/** Who is talking, inferred from when the newest transcript line last changed. */
export function useSpeaker(lines: Line[], thinking: boolean): Speech {
  const last = lines[lines.length - 1];
  const key = last ? `${lines.length}:${last.text}` : "";
  const [changedAt, setChangedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false; // lines already on screen when the page opens are not "speaking"
      return;
    }
    if (key) setChangedAt(Date.now());
  }, [key]);
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(t);
  }, []);
  return speechState(changedAt, now, thinking);
}

/** Section numbers shown for the current painting, in order. */
export function useVisited(title: string | null, number: number | null): number[] {
  const [v, setV] = useState(NO_VISITS);
  useEffect(() => setV((prev) => visit(prev, title, number)), [title, number]);
  return v.numbers;
}

/** Starts the Borderless flow when the part changes; `held` keeps the board's balls down until it lands. */
export function useFlow(title: string | null, section: Section | null) {
  const [flowFor, setFlowFor] = useState<Section | null>(null);
  const prev = useRef<Shown>({ title: null, number: null });
  const number = section?.number ?? null;
  useLayoutEffect(() => {
    const next = { title, number };
    if (section && shouldFly(prev.current, next) && !reducedMotion()) setFlowFor(section);
    prev.current = next;
  }, [title, number]); // section is read for this render only; a new object with the same number must not re-fly
  const landed = useCallback(() => setFlowFor(null), []);
  return { flowFor, held: flowFor !== null, landed };
}

/** "03:12" since this tab first saw main.py online. */
export function useSessionClock(online: boolean): string {
  const start = useRef<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  if (online && start.current === null) start.current = Date.now();
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  return formatClock(start.current === null ? 0 : now - start.current);
}
```

- [ ] **Step 2: Type-check and run the tests**

Run: `cd screen && npx tsc -p . && npm test`
Expected: exit 0; `# fail 0`.

- [ ] **Step 3: Commit**

```bash
git add screen/src/lib/hooks.ts
git commit -m "screen: hooks for painting pixels, speech, visited parts, flow and session clock"
```

---

### Task 11: Shell components: TopStrip, Room, AgentDrawer

**Files:**
- Create: `screen/src/components/TopStrip.tsx` + `.css`, `Room.tsx` + `.css`, `AgentDrawer.tsx` + `.css`

**Interfaces:**
- Consumes: `COPY`, `WORDMARK`, `SPONSORS`; `useSessionClock`; `State`.
- Produces:
  - `TopStrip({ online, drawerOpen, onToggleDrawer }: { online: boolean; drawerOpen: boolean; onToggleDrawer: () => void })`
  - `Room({ image }: { image: string | null })`, which reads the CSS var `--glow` set by App
  - `AgentDrawer({ open, activity, frame, onClose }: { open: boolean; activity: State["activity"]; frame: string | null; onClose: () => void })`

- [ ] **Step 1: `TopStrip.tsx`**

```tsx
import { COPY, WORDMARK } from "../design/copy";
import { useSessionClock } from "../lib/hooks";
import "./TopStrip.css";

export function TopStrip({ online, drawerOpen, onToggleDrawer }: {
  online: boolean;
  drawerOpen: boolean;
  onToggleDrawer: () => void;
}) {
  const elapsed = useSessionClock(online);
  return (
    <header className="top-strip">
      <span className="wordmark">{WORDMARK}</span>
      <div className="top-strip__right">
        {online && (
          <span className="live label">
            <span className="live__dot" aria-hidden />
            {COPY.live} <span className="live__time">{elapsed}</span>
          </span>
        )}
        <button type="button" className="key-button label" aria-pressed={drawerOpen} onClick={onToggleDrawer}>
          <kbd>S</kbd> {COPY.agents}
        </button>
      </div>
    </header>
  );
}
```

`TopStrip.css`:

```css
.top-strip { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-5); }
.wordmark { font-family: var(--font-serif); font-style: italic; font-size: var(--text-kicker); line-height: 1; }
.top-strip__right { display: flex; align-items: center; gap: var(--spacing-6); }
.live { display: inline-flex; align-items: center; gap: var(--spacing-2); }
.live__dot { width: 8px; height: 8px; border-radius: var(--radius-full); background: var(--color-lantern); box-shadow: 0 0 12px var(--color-lantern); animation: pulse 2s ease-in-out infinite; }
.live__time { color: var(--color-paper-dim); }
@media (prefers-reduced-motion: reduce) { .live__dot { animation: none; } }
```

- [ ] **Step 2: `Room.tsx`**

```tsx
import "./Room.css";

// The painting's light filling the room: a blurred copy behind everything, tinted by --glow (set by App).
export function Room({ image }: { image: string | null }) {
  return (
    <div className="room" aria-hidden>
      {image && (
        <img key={image} className="room__blur" src={image} alt="" onError={(e) => (e.currentTarget.style.display = "none")} />
      )}
    </div>
  );
}
```

`Room.css`:

```css
.room { position: fixed; inset: 0; z-index: -1; overflow: hidden; background: radial-gradient(ellipse 70% 60% at 30% 45%, var(--glow, transparent), transparent 70%), var(--color-ink); }
.room__blur { position: absolute; inset: -10%; width: 120%; height: 120%; object-fit: cover; filter: blur(90px) saturate(1.2); opacity: 0.16; }
```

- [ ] **Step 3: `AgentDrawer.tsx`**

```tsx
import { COPY, SPONSORS } from "../design/copy";
import type { State } from "../types";
import "./AgentDrawer.css";

// What each sponsor's piece is doing. Slides over the right column; never reflows the layout.
export function AgentDrawer({ open, activity, frame, onClose }: {
  open: boolean;
  activity: State["activity"];
  frame: string | null;
  onClose: () => void;
}) {
  return (
    <aside className={`drawer${open ? " drawer--open" : ""}`} aria-label={COPY.drawerTitle}>
      <header className="drawer__head">
        <h2 className="drawer__title">{COPY.drawerTitle}</h2>
        <button type="button" className="key-button label" onClick={onClose}>
          <kbd>S</kbd> {COPY.close}
        </button>
      </header>
      <ul className="drawer__rows">
        {SPONSORS.map(({ key, name, job }) => {
          const a = activity[key];
          return (
            <li key={key} className={`agent agent--${a.status}`}>
              <span className="agent__status label">
                <span className="agent__dot" aria-hidden />
                {COPY.status[a.status]}
              </span>
              <span className="agent__name">{name}</span>
              <span className="agent__job">{job}</span>
              <span className="agent__detail label">{a.detail || "—"}</span>
            </li>
          );
        })}
      </ul>
      <div className="drawer__wire">
        <span className="label">{COPY.onTheWire}</span>
        <code>{frame ?? "Z"}</code>
      </div>
    </aside>
  );
}
```

`AgentDrawer.css`:

```css
.drawer { position: fixed; top: 0; right: 0; bottom: 0; z-index: 10; width: min(520px, 92vw); display: flex; flex-direction: column; gap: var(--spacing-7); padding: var(--margin-y) var(--spacing-7); background: var(--color-stone); border-left: 1px solid var(--color-stone-2); transform: translateX(100%); visibility: hidden; transition: transform 500ms var(--ease-light), visibility 0s linear 500ms; }
.drawer--open { transform: none; visibility: visible; transition: transform 500ms var(--ease-light); }
.drawer__head { display: flex; justify-content: space-between; align-items: baseline; }
.drawer__title { margin: 0; font-family: var(--font-serif); font-weight: 400; font-size: var(--text-title); line-height: 1; }
.drawer__rows { list-style: none; margin: 0; padding: 0; }
.agent { display: grid; grid-template-columns: 120px minmax(0, 1fr); column-gap: var(--spacing-5); row-gap: var(--spacing-1); padding: var(--spacing-5) 0; border-top: 1px solid var(--color-stone-2); }
.agent__status { grid-row: span 3; display: flex; align-items: center; gap: var(--spacing-2); align-self: start; color: var(--color-paper-dim); }
.agent__dot { width: 8px; height: 8px; border-radius: var(--radius-full); background: var(--color-paper-faint); }
.agent--working .agent__status { color: var(--color-lantern); }
.agent--working .agent__dot { background: var(--color-lantern); animation: pulse 1.2s ease-in-out infinite; }
.agent--done .agent__status { color: var(--color-moss); }
.agent--done .agent__dot { background: var(--color-moss); }
.agent--failed .agent__status { color: var(--color-koi); }
.agent--failed .agent__dot { background: var(--color-koi); }
.agent__name { font-weight: var(--font-weight-semibold); }
.agent__job { color: var(--color-paper-dim); }
.agent__detail { color: var(--color-paper); text-transform: none; letter-spacing: 0.02em; }
.drawer__wire { display: grid; gap: var(--spacing-2); margin-top: auto; color: var(--color-paper-dim); }
.drawer__wire code { font-family: var(--font-mono); font-size: var(--text-label); word-break: break-all; }
@media (prefers-reduced-motion: reduce) { .drawer, .drawer--open { transition: none; } .agent--working .agent__dot { animation: none; } }
```

- [ ] **Step 4: Type-check**

Run: `cd screen && npx tsc -p .` (expected: exit 0)

- [ ] **Step 5: Commit**

```bash
git add screen/src/components/TopStrip.* screen/src/components/Room.* screen/src/components/AgentDrawer.*
git commit -m "screen: top strip, room glow and sponsor drawer components"
```

---

### Task 12: Art column: PaintingStage, Spotlight, Placard

**Files:**
- Create: `screen/src/components/PaintingStage.tsx` + `.css`, `Spotlight.tsx` + `.css`, `Placard.tsx` + `.css`

**Interfaces:**
- Consumes: `Painting`, `Section`; `pad`.
- Produces:
  - `PaintingStage({ painting, section, frameRef, grid }: { painting: Painting; section: Section | null; frameRef: RefObject<HTMLDivElement>; grid: boolean })`. `frameRef` wraps the image box that Task 16 measures.
  - `SpotlightBox({ bbox, grid })` and `SpotlightTag({ section })`
  - `Placard({ painting }: { painting: Painting })`

- [ ] **Step 1: `Spotlight.tsx`**

```tsx
import type { CSSProperties } from "react";
import { pad } from "../lib/format";
import type { Section } from "../types";
import "./Spotlight.css";

type Bbox = [number, number, number, number];

function box([x0, y0, x1, y1]: Bbox): CSSProperties {
  return { left: `${x0 * 100}%`, top: `${y0 * 100}%`, width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%` };
}

/** Inside the clipped image: dims everything except the part. `grid` shows the 10x10 cells during the flow. */
export function SpotlightBox({ bbox, grid }: { bbox: Bbox; grid: boolean }) {
  return <div className={`spotlight${grid ? " spotlight--grid" : ""}`} style={box(bbox)} aria-hidden />;
}

/** Outside the clip: the part's name hung on a hand-drawn hook at the box corner. */
export function SpotlightTag({ section }: { section: Section }) {
  const [x0, y0, x1] = section.bbox;
  const left = x1 > 0.7 && x0 > 0.3; // no room on the right
  const below = y0 < 0.08; // no room above
  const cls = `spot-tag label${left ? " spot-tag--left" : ""}${below ? " spot-tag--below" : ""}`;
  return (
    <div className="spot-anchor" style={box(section.bbox)} aria-hidden>
      <span className={cls}>
        <svg className="spot-tag__hook" viewBox="0 0 40 24">
          <path d="M1 23 C 8 21, 12 9, 19 7 S 33 3, 39 1" />
        </svg>
        {pad(section.number)} · {section.name}
      </span>
    </div>
  );
}
```

`Spotlight.css`:

```css
.spotlight, .spot-anchor { position: absolute; pointer-events: none; transition: left var(--dur-spot) var(--ease-light), top var(--dur-spot) var(--ease-light), width var(--dur-spot) var(--ease-light), height var(--dur-spot) var(--ease-light); }
.spotlight { border: 1.5px solid var(--color-lantern); box-shadow: 0 0 0 100vmax rgb(8 9 11 / 0.62); }
.spotlight--grid { background-image: linear-gradient(to right, rgb(242 234 220 / 0.18) 1px, transparent 1px), linear-gradient(to bottom, rgb(242 234 220 / 0.18) 1px, transparent 1px); background-size: 10% 10%; }
.spot-tag { --sx: 1; --sy: 1; position: absolute; bottom: calc(100% + 6px); left: calc(100% - 4px); display: flex; align-items: flex-start; gap: var(--spacing-1); white-space: nowrap; color: var(--color-lantern); text-shadow: 0 0 8px var(--color-ink), 0 0 2px var(--color-ink); }
.spot-tag__hook { width: 40px; height: 24px; flex: none; margin-top: 6px; fill: none; stroke: var(--color-lantern); stroke-width: 1.5; stroke-linecap: round; transform: scale(var(--sx), var(--sy)); }
.spot-tag--left { left: auto; right: calc(100% - 4px); flex-direction: row-reverse; --sx: -1; }
.spot-tag--below { bottom: auto; top: calc(100% + 6px); align-items: flex-end; --sy: -1; }
.spot-tag--below .spot-tag__hook { margin-top: 0; margin-bottom: 6px; }
```

- [ ] **Step 2: `PaintingStage.tsx`**

```tsx
import { useState, type RefObject } from "react";
import type { Painting, Section } from "../types";
import { SpotlightBox, SpotlightTag } from "./Spotlight";
import "./PaintingStage.css";

export function PaintingStage({ painting, section, frameRef, grid }: {
  painting: Painting;
  section: Section | null;
  frameRef: RefObject<HTMLDivElement>;
  grid: boolean;
}) {
  const [failed, setFailed] = useState<string | null>(null); // image that failed to load: show the blank frame
  const showImage = painting.image && failed !== painting.image;
  return (
    <figure className="stage">
      <div className="stage__frame" ref={frameRef}>
        <div className="stage__clip">
          {showImage ? (
            <img src={painting.image!} alt={painting.title} onError={() => setFailed(painting.image)} />
          ) : (
            <div className="stage__blank" />
          )}
          {section && <SpotlightBox bbox={section.bbox} grid={grid} />}
        </div>
        {section && <SpotlightTag section={section} />}
      </div>
    </figure>
  );
}
```

`PaintingStage.css`:

```css
.stage { margin: 0; flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; }
.stage__frame { position: relative; line-height: 0; max-width: 100%; }
.stage__clip { position: relative; overflow: hidden; }
.stage__clip img { display: block; max-width: 100%; max-height: calc(100vh - 380px); box-shadow: 0 0 120px var(--glow, transparent); }
.stage__blank { width: 40vh; aspect-ratio: 3 / 4; background: var(--color-stone); }
@media (max-width: 1100px) { .stage__clip img { max-height: 70vh; } }
```

- [ ] **Step 3: `Placard.tsx`**

```tsx
import type { Painting } from "../types";
import "./Placard.css";

// Museum wall label: artist, title, year.
export function Placard({ painting }: { painting: Painting }) {
  return (
    <div className="placard">
      <p className="placard__artist">{painting.artist}</p>
      <h1 className="placard__title">{painting.title}</h1>
      {painting.year && <p className="placard__year label">{painting.year}</p>}
    </div>
  );
}
```

`Placard.css`:

```css
.placard { display: grid; gap: var(--spacing-2); }
.placard__artist { margin: 0; font-family: var(--font-serif); font-style: italic; font-size: var(--text-kicker); line-height: 1.1; color: var(--color-paper-dim); }
.placard__title { margin: 0; font-family: var(--font-serif); font-weight: 400; font-size: var(--text-display); line-height: var(--leading-display); letter-spacing: var(--tracking-display); }
.placard__year { margin: 0; color: var(--color-paper-dim); }
```

- [ ] **Step 4:** `cd screen && npx tsc -p .` (expected: exit 0)
- [ ] **Step 5: Commit**

```bash
git add screen/src/components/PaintingStage.* screen/src/components/Spotlight.* screen/src/components/Placard.*
git commit -m "screen: painting stage with spotlight, hand-drawn tag and placard"
```

---

### Task 13: BallGrid and Board

**Files:**
- Create: `screen/src/components/BallGrid.tsx` + `.css`, `screen/src/components/Board.tsx` + `.css`
  (overwrites the old `Board.tsx`, which is no longer imported once App is replaced in Task 15. Until then
  the old App imports `Board` with props `{section, hardware}`, so **name the new file `TouchBoard.tsx`**
  and export `TouchBoard`. Task 15 deletes the old `Board.tsx`.)

**Interfaces:**
- Consumes: `RGB`, `LANTERN`, `css`; `pad`; `EMPTY_GRID`; `COPY`.
- Produces:
  - `BallGrid({ grid, colors, held, breathing, gridRef }: { grid: number[][]; colors?: RGB[][] | null; held?: boolean; breathing?: boolean; gridRef?: RefObject<HTMLDivElement> })`. Each ball has `data-cell="r-c"`.
  - `TouchBoard({ section, total, hardware, colors, held, wellsRef }: { section: Section | null; total: number; hardware: boolean; colors: RGB[][] | null; held: boolean; wellsRef: RefObject<HTMLDivElement> })`

- [ ] **Step 1: `BallGrid.tsx`**

```tsx
import type { CSSProperties, RefObject } from "react";
import { css, LANTERN, type RGB } from "../lib/colors";
import "./BallGrid.css";

// Row 0 is the edge farthest from the visitor, as on the real board. Balls rise one row after another.
export function BallGrid({ grid, colors = null, held = false, breathing = false, gridRef }: {
  grid: number[][];
  colors?: RGB[][] | null;
  held?: boolean;
  breathing?: boolean;
  gridRef?: RefObject<HTMLDivElement>;
}) {
  const raised = grid.flat().filter(Boolean).length;
  return (
    <div ref={gridRef} className={`balls${breathing ? " balls--breathing" : ""}`} role="img" aria-label={`${raised} of 100 balls raised`}>
      {grid.map((row, r) =>
        row.map((v, c) => (
          <span
            key={`${r}-${c}`}
            data-cell={`${r}-${c}`}
            className={v === 1 && !held ? "ball ball--up" : "ball"}
            style={{ "--row": r, "--ball": css(colors?.[r]?.[c] ?? LANTERN) } as CSSProperties}
          />
        )),
      )}
    </div>
  );
}
```

`BallGrid.css`:

```css
/* A well is a ball at 62% scale (BorderlessFlow divides measured well size by 0.62). */
.balls { width: 100%; aspect-ratio: 1; display: grid; grid-template-columns: repeat(10, 1fr); grid-template-rows: repeat(10, 1fr); gap: 2.6%; }
.ball { border-radius: var(--radius-full); background: var(--color-stone-2); transform: scale(0.62); transition: transform var(--dur-ball) var(--ease-rise) calc(var(--row) * var(--stagger-row)), background-color var(--dur-ball) var(--ease-light) calc(var(--row) * var(--stagger-row)), box-shadow var(--dur-ball) var(--ease-light) calc(var(--row) * var(--stagger-row)); }
.ball--up { transform: scale(1); background: radial-gradient(circle at 35% 30%, color-mix(in srgb, var(--ball) 35%, white), var(--ball) 55%, color-mix(in srgb, var(--ball) 70%, black)); box-shadow: 0 0 18px color-mix(in srgb, var(--ball) 45%, transparent); }
.balls--breathing .ball { animation: breathe 2.4s var(--ease-light) infinite; animation-delay: calc(var(--row) * 120ms); }
@keyframes breathe { 50% { background-color: var(--color-paper-faint); } }
@media (prefers-reduced-motion: reduce) { .balls--breathing .ball { animation: none; } }
```

- [ ] **Step 2: `TouchBoard.tsx`**

```tsx
import type { RefObject } from "react";
import { COPY } from "../design/copy";
import type { RGB } from "../lib/colors";
import { pad } from "../lib/format";
import { normalizeGrid } from "../lib/grid";
import type { Section } from "../types";
import { BallGrid } from "./BallGrid";
import "./TouchBoard.css";

export function TouchBoard({ section, total, hardware, colors, held, wellsRef }: {
  section: Section | null;
  total: number;
  hardware: boolean;
  colors: RGB[][] | null;
  held: boolean;
  wellsRef: RefObject<HTMLDivElement>;
}) {
  return (
    <section className="board">
      <span className="board__numeral" aria-hidden>{section ? pad(section.number) : ""}</span>
      <span className="board__badge label">{hardware ? COPY.mirrored : COPY.simulated}</span>
      <div className="board__grid">
        <BallGrid grid={normalizeGrid(section?.grid)} colors={colors} held={held} gridRef={wellsRef} />
      </div>
      <p className="board__label label">
        {section ? `${COPY.nowTouching} · ${pad(section.number)} / ${pad(total)}` : COPY.allDown}
      </p>
      {section && <h2 className="board__name">{section.name}</h2>}
      {section && <p className="board__where label">{section.location} {COPY.ofTheCanvas}</p>}
    </section>
  );
}
```

`TouchBoard.css`:

```css
.board { position: relative; isolation: isolate; display: grid; justify-items: start; gap: var(--spacing-2); padding-top: var(--spacing-6); }
.board__grid { width: min(100%, 44vh); margin-bottom: var(--spacing-4); }
.board__numeral { position: absolute; z-index: -1; right: 0; top: 50%; transform: translateY(-55%); font-family: var(--font-serif); font-size: var(--text-numeral); line-height: 1; color: transparent; -webkit-text-stroke: 1px var(--color-paper-faint); opacity: 0.55; pointer-events: none; }
.board__badge { position: absolute; top: 0; right: 0; color: var(--color-paper-dim); }
.board__label { margin: 0; color: var(--color-lantern); }
.board__name { margin: 0; font-family: var(--font-serif); font-weight: 400; font-size: var(--text-title); line-height: 1.05; }
.board__where { margin: 0; color: var(--color-paper-dim); }
@media (max-width: 1100px) { .board__grid { width: min(100%, 420px); } }
```

- [ ] **Step 3:** `cd screen && npx tsc -p .` (expected: exit 0)
- [ ] **Step 4: Commit**

```bash
git add screen/src/components/BallGrid.* screen/src/components/TouchBoard.*
git commit -m "screen: ball grid and touch board with painting-coloured balls"
```

---

### Task 14: Captions, SpeakingIndicator, TourRail, IdleScreen, LookingUp

**Files:**
- Create: `Captions.tsx` + `.css`, `SpeakingIndicator.tsx` + `.css`, `TourRail.tsx` + `.css`,
  `IdleScreen.tsx` + `.css`, `LookingUp.tsx` + `.css` (all in `screen/src/components/`)

**Interfaces:**
- Produces:
  - `Captions({ lines, speech }: { lines: Line[]; speech: Speech })`
  - `SpeakingIndicator({ state }: { state: Speech })`
  - `TourRail({ sections, current, visited }: { sections: SectionSummary[]; current: number | null; visited: number[] })`
  - `IdleScreen({ offline }: { offline: boolean })`
  - `LookingUp({ detail }: { detail: string })`

- [ ] **Step 1: `SpeakingIndicator.tsx`**

```tsx
import type { CSSProperties } from "react";
import type { Speech } from "../lib/speaker";
import "./SpeakingIndicator.css";

// Eight dots on a ring, like ripples around your feet in teamLab's water room.
export function SpeakingIndicator({ state }: { state: Speech }) {
  return (
    <span className={`speech speech--${state}`} aria-hidden>
      {Array.from({ length: 8 }, (_, i) => (
        <span key={i} className="speech__dot" style={{ "--i": i } as CSSProperties} />
      ))}
    </span>
  );
}
```

`SpeakingIndicator.css`:

```css
.speech { position: relative; display: inline-block; width: 20px; height: 20px; flex: none; }
.speech__dot { position: absolute; left: 50%; top: 50%; width: 3px; height: 3px; margin: -1.5px; border-radius: var(--radius-full); background: var(--color-lantern); transform: rotate(calc(var(--i) * 45deg)) translateY(-7px); }
.speech--speaking .speech__dot { animation: ripple var(--dur-ripple) var(--ease-light) infinite; }
.speech--thinking { animation: orbit 1.6s linear infinite; }
.speech--thinking .speech__dot { opacity: calc(0.25 + var(--i) * 0.1); }
.speech--listening .speech__dot { animation: pulse 3s ease-in-out infinite; opacity: 0.8; }
@keyframes ripple { from { transform: rotate(calc(var(--i) * 45deg)) translateY(-4px); opacity: 1; } to { transform: rotate(calc(var(--i) * 45deg)) translateY(-11px); opacity: 0; } }
@keyframes orbit { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .speech, .speech__dot { animation: none !important; } }
```

- [ ] **Step 2: `Captions.tsx`**

```tsx
import { COPY } from "../design/copy";
import type { Speech } from "../lib/speaker";
import type { Line } from "../types";
import { SpeakingIndicator } from "./SpeakingIndicator";
import "./Captions.css";

// The last four lines as captions: newest largest, older ones step down and fade.
export function Captions({ lines, speech }: { lines: Line[]; speech: Speech }) {
  const recent = lines.slice(-4);
  const first = lines.length - recent.length;
  return (
    <section className="captions" aria-live="polite">
      {recent.map((l, i) => {
        const age = recent.length - 1 - i; // 0 = newest
        return (
          <p key={first + i} className={`caption caption--age${age}`}>
            <span className="caption__who label">
              {age === 0 && <SpeakingIndicator state={speech} />}
              {l.role === "user" ? COPY.visitor : COPY.guide}
              {age === 0 && <span className="caption__state">{COPY.speech[speech]}</span>}
            </span>
            <span className="caption__text">{l.text}</span>
          </p>
        );
      })}
    </section>
  );
}
```

`Captions.css`:

```css
.captions { flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: flex-end; gap: var(--spacing-4); overflow: hidden; -webkit-mask-image: linear-gradient(to bottom, transparent, #000 25%); mask-image: linear-gradient(to bottom, transparent, #000 25%); }
.caption { margin: 0; display: grid; gap: var(--spacing-1); }
.caption__who { display: flex; align-items: center; gap: var(--spacing-2); color: var(--color-paper-dim); }
.caption__state { color: var(--color-lantern); }
.caption__text { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; color: var(--color-paper-dim); }
.caption--age0 .caption__text { -webkit-line-clamp: 4; font-size: var(--text-caption-now); line-height: var(--leading-caption-now); font-weight: var(--font-weight-medium); color: var(--color-paper); }
.caption--age2 { opacity: 0.7; }
.caption--age3 { opacity: 0.45; }
```

- [ ] **Step 3: `TourRail.tsx`**

```tsx
import type { SectionSummary } from "../types";
import "./TourRail.css";

// One ball per part: visited (filled), now (lantern with halo), still to come (hollow ring).
export function TourRail({ sections, current, visited }: {
  sections: SectionSummary[];
  current: number | null;
  visited: number[];
}) {
  return (
    <ol className="rail">
      {sections.map((s) => {
        const state = s.number === current ? "now" : visited.includes(s.number) ? "done" : "next";
        return (
          <li key={s.number} className={`rail__stop rail__stop--${state}`} aria-current={state === "now" ? "step" : undefined}>
            <span className="rail__ball" aria-hidden />
            <span className="rail__name label">{s.name}</span>
          </li>
        );
      })}
    </ol>
  );
}
```

`TourRail.css`:

```css
.rail { grid-column: 1 / -1; list-style: none; margin: 0; padding: 0; display: flex; }
.rail__stop { position: relative; flex: 1; min-width: 0; display: grid; justify-items: start; gap: var(--spacing-2); color: var(--color-paper-dim); }
.rail__stop::after { content: ""; position: absolute; top: 7px; left: 26px; right: 10px; border-top: 1px dotted var(--color-paper-faint); }
.rail__stop:last-child::after { display: none; }
.rail__stop--done::after { border-top-style: solid; border-color: var(--color-paper-dim); }
.rail__ball { width: 14px; height: 14px; border-radius: var(--radius-full); border: 1px solid var(--color-paper-faint); transition: background-color var(--dur-spot) var(--ease-light), box-shadow var(--dur-spot) var(--ease-light); }
.rail__stop--done .rail__ball { background: var(--color-paper-dim); border-color: transparent; }
.rail__stop--now .rail__ball { background: var(--color-lantern); border-color: transparent; box-shadow: 0 0 0 5px rgb(255 181 71 / 0.25), 0 0 18px var(--color-lantern); }
.rail__stop--now .rail__name { color: var(--color-paper); }
.rail__name { max-width: 92%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 1100px) { .rail { flex-direction: column; gap: var(--spacing-3); } .rail__stop::after { display: none; } .rail__stop { grid-template-columns: 14px 1fr; align-items: center; } }
```

- [ ] **Step 4: `IdleScreen.tsx`**

```tsx
import { useEffect, useState } from "react";
import { COPY } from "../design/copy";
import { IDLE_SHAPES } from "../lib/idleShapes";
import { reducedMotion } from "../lib/motion";
import { BallGrid } from "./BallGrid";
import "./IdleScreen.css";

const CYCLE_MS = 8000; // --dur-idle

// Attract mode: the board draws each demo painting's best-known part while nobody is touring.
export function IdleScreen({ offline }: { offline: boolean }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (offline || reducedMotion()) return;
    const t = window.setInterval(() => setI((n) => (n + 1) % IDLE_SHAPES.length), CYCLE_MS);
    return () => window.clearInterval(t);
  }, [offline]);
  const shape = IDLE_SHAPES[i];
  return (
    <main className={`idle${offline ? " idle--offline" : ""}`}>
      <div className="idle__board">
        <BallGrid grid={shape.grid} />
      </div>
      <div className="idle__copy">
        <p className="idle__kicker">{offline ? COPY.offlineKicker : `${shape.title} · ${shape.part}`}</p>
        <h1 className="idle__headline">{offline ? COPY.offlineHeadline : COPY.idleHeadline}</h1>
        <p className="idle__hint label">{offline ? COPY.offlineHint : COPY.idleHint}</p>
      </div>
      <p className="idle__footer label">{COPY.idleFooter}</p>
    </main>
  );
}
```

`IdleScreen.css`:

```css
.idle { grid-column: 1 / -1; grid-row: 2 / 4; display: grid; grid-template-columns: 42fr 58fr; grid-template-rows: 1fr auto; align-items: center; column-gap: var(--gutter); }
.idle__board { width: min(100%, 60vh); justify-self: center; transition: opacity var(--dur-spot) var(--ease-light); }
.idle__kicker { margin: 0; font-family: var(--font-serif); font-style: italic; font-size: var(--text-kicker); color: var(--color-paper-dim); }
.idle__headline { margin: var(--spacing-3) 0 var(--spacing-6); max-width: 11ch; font-family: var(--font-serif); font-weight: 400; font-size: calc(var(--text-display) * 1.5); line-height: var(--leading-display); letter-spacing: var(--tracking-display); }
.idle__hint { margin: 0; color: var(--color-lantern); }
.idle__footer { grid-column: 1 / -1; margin: 0; color: var(--color-paper-dim); }
.idle--offline .idle__board { opacity: 0.35; }
.idle--offline .idle__hint { color: var(--color-paper-dim); }
@media (max-width: 1100px) { .idle { grid-template-columns: 1fr; row-gap: var(--spacing-7); } }
```

- [ ] **Step 5: `LookingUp.tsx`**

```tsx
import { COPY } from "../design/copy";
import { EMPTY_GRID } from "../lib/idleShapes";
import { BallGrid } from "./BallGrid";
import "./LookingUp.css";

// Gemini is finding the parts of a painting that isn't cached yet.
export function LookingUp({ detail }: { detail: string }) {
  return (
    <main className="looking">
      <div className="looking__frame" aria-hidden>
        <span className="looking__sweep" />
      </div>
      <div className="looking__side">
        <p className="looking__label label">{COPY.lookingUp}</p>
        <p className="looking__detail">{detail}</p>
        <div className="looking__board">
          <BallGrid grid={EMPTY_GRID} breathing />
        </div>
      </div>
    </main>
  );
}
```

`LookingUp.css`:

```css
.looking { grid-column: 1 / -1; grid-row: 2 / 4; display: grid; grid-template-columns: 58fr 42fr; column-gap: var(--gutter); align-items: center; }
.looking__frame { position: relative; justify-self: center; height: min(70vh, 720px); aspect-ratio: 3 / 4; border: 1px dashed var(--color-paper-faint); overflow: hidden; }
.looking__sweep { position: absolute; left: 0; right: 0; top: 0; height: 30%; background: linear-gradient(to bottom, transparent, rgb(255 181 71 / 0.18), transparent); animation: sweep 2.4s var(--ease-light) infinite; }
@keyframes sweep { from { transform: translateY(-100%); } to { transform: translateY(340%); } }
.looking__label { margin: 0; color: var(--color-lantern); }
.looking__detail { margin: var(--spacing-3) 0 var(--spacing-7); font-family: var(--font-serif); font-size: var(--text-title); line-height: 1.05; }
.looking__board { width: min(100%, 36vh); }
@media (prefers-reduced-motion: reduce) { .looking__sweep { animation: none; top: 35%; } }
@media (max-width: 1100px) { .looking { grid-template-columns: 1fr; row-gap: var(--spacing-7); } }
```

- [ ] **Step 6:** `cd screen && npx tsc -p .` (expected: exit 0)
- [ ] **Step 7: Commit**

```bash
git add screen/src/components/Captions.* screen/src/components/SpeakingIndicator.* screen/src/components/TourRail.* screen/src/components/IdleScreen.* screen/src/components/LookingUp.*
git commit -m "screen: captions, speaking ripple, tour rail, idle and looking-up scenes"
```

---

### Task 15: BorderlessFlow, the new App, and removal of the old UI

**Files:**
- Create: `screen/src/components/BorderlessFlow.tsx` + `.css`, `screen/src/App.css`
- Replace: `screen/src/App.tsx`
- Modify: `screen/src/main.tsx` (drop `./styles.css`)
- Delete: `screen/src/styles.css`, `screen/src/components/PaintingView.tsx`, `Transcript.tsx`, `ActivityBar.tsx`, `Board.tsx`

**Interfaces:**
- Consumes: everything from Tasks 3, 10–14.
- Produces: `BorderlessFlow({ section, colors, frameRef, wellsRef, onLanded }: { section: Section; colors: RGB[][] | null; frameRef: RefObject<HTMLDivElement>; wellsRef: RefObject<HTMLDivElement>; onLanded: () => void })`

- [ ] **Step 1: `BorderlessFlow.tsx`**

```tsx
import { useLayoutEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import { css, LANTERN, type RGB } from "../lib/colors";
import { FLY_MS, LIT_MS, ROW_MS } from "../lib/flow";
import { normalizeGrid } from "../lib/grid";
import type { Section } from "../types";
import "./BorderlessFlow.css";

interface Dot { key: string; row: number; x: number; y: number; dx: number; dy: number; size: number; from: number; color: string }

const WELL_SCALE = 0.62; // matches .ball { transform: scale(0.62) }

// The part of the painting lifts off as dots and lands on the board, teamLab-style: art moving between rooms.
export function BorderlessFlow({ section, colors, frameRef, wellsRef, onLanded }: {
  section: Section;
  colors: RGB[][] | null;
  frameRef: RefObject<HTMLDivElement>;
  wellsRef: RefObject<HTMLDivElement>;
  onLanded: () => void;
}) {
  const [dots, setDots] = useState<Dot[]>([]);
  const [flying, setFlying] = useState(false);
  const landed = useRef(onLanded);
  landed.current = onLanded;

  useLayoutEffect(() => {
    const frame = frameRef.current?.querySelector(".stage__clip")?.getBoundingClientRect();
    const wells = wellsRef.current;
    if (!frame || !wells) {
      landed.current();
      return;
    }
    const [x0, y0, x1, y1] = section.bbox;
    const cw = ((x1 - x0) * frame.width) / 10;
    const ch = ((y1 - y0) * frame.height) / 10;
    const next: Dot[] = [];
    normalizeGrid(section.grid).forEach((row, r) =>
      row.forEach((v, c) => {
        if (v !== 1) return;
        const well = wells.querySelector(`[data-cell="${r}-${c}"]`)?.getBoundingClientRect();
        if (!well) return;
        const size = well.width / WELL_SCALE;
        const x = frame.left + x0 * frame.width + (c + 0.5) * cw;
        const y = frame.top + y0 * frame.height + (r + 0.5) * ch;
        next.push({
          key: `${r}-${c}`,
          row: r,
          x,
          y,
          dx: well.left + well.width / 2 - x,
          dy: well.top + well.height / 2 - y,
          size,
          from: Math.max(0.15, Math.min(cw, ch, size) / size) * 0.7,
          color: css(colors?.[r]?.[c] ?? LANTERN),
        });
      }),
    );
    if (next.length === 0) {
      landed.current();
      return;
    }
    setDots(next);
    const go = window.setTimeout(() => setFlying(true), LIT_MS);
    const done = window.setTimeout(() => landed.current(), LIT_MS + FLY_MS + 9 * ROW_MS);
    return () => {
      window.clearTimeout(go);
      window.clearTimeout(done);
    };
  }, [section, frameRef, wellsRef]); // colors are read once when the flight starts

  return (
    <div className="flow" aria-hidden>
      {dots.map((d) => (
        <span
          key={d.key}
          className="flow__dot"
          style={{
            left: d.x - d.size / 2,
            top: d.y - d.size / 2,
            width: d.size,
            height: d.size,
            transform: flying ? `translate(${d.dx}px, ${d.dy}px) scale(1)` : `scale(${d.from})`,
            transitionDelay: flying ? `${d.row * ROW_MS}ms` : "0ms",
            "--dot": d.color,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}
```

`BorderlessFlow.css`:

```css
.flow { position: fixed; inset: 0; z-index: 5; pointer-events: none; }
.flow__dot { position: fixed; border-radius: var(--radius-full); background: var(--dot); box-shadow: 0 0 14px var(--dot); transition: transform var(--dur-flow) var(--ease-light); animation: lit var(--dur-spot) var(--ease-light); }
@keyframes lit { from { opacity: 0; } }
```

- [ ] **Step 2: Replace `screen/src/App.tsx`**

```tsx
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { AgentDrawer } from "./components/AgentDrawer";
import { BorderlessFlow } from "./components/BorderlessFlow";
import { Captions } from "./components/Captions";
import { IdleScreen } from "./components/IdleScreen";
import { LookingUp } from "./components/LookingUp";
import { PaintingStage } from "./components/PaintingStage";
import { Placard } from "./components/Placard";
import { Room } from "./components/Room";
import { TopStrip } from "./components/TopStrip";
import { TouchBoard } from "./components/TouchBoard";
import { TourRail } from "./components/TourRail";
import { averageColor, cellColors, css, LANTERN } from "./lib/colors";
import { useFlow, usePaintingPixels, useSpeaker, useVisited } from "./lib/hooks";
import { pickScene } from "./lib/scene";
import { useScreenState } from "./useScreenState";
import "./App.css";

export function App() {
  const { state, online } = useScreenState();
  const scene = pickScene(state, online);
  const painting = state?.painting ?? null;
  const section = state?.section ?? null;

  const [drawerOpen, setDrawerOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "s" || e.key === "S") setDrawerOpen((o) => !o);
      if (e.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const pixels = usePaintingPixels(painting?.image ?? null);
  const average = useMemo(() => (pixels ? averageColor(pixels) : LANTERN), [pixels]);
  const bboxKey = section?.bbox.join(",");
  const colors = useMemo(
    () => (pixels && section ? cellColors(pixels, section.bbox) : null),
    [pixels, bboxKey], // bboxKey, not section: polls create a new section object with the same bbox
  );
  const speech = useSpeaker(state?.transcript ?? [], state?.activity.gemini.status === "working");
  const visited = useVisited(painting?.title ?? null, section?.number ?? null);
  const { flowFor, held, landed } = useFlow(painting?.title ?? null, section);
  const frameRef = useRef<HTMLDivElement>(null);
  const wellsRef = useRef<HTMLDivElement>(null);

  return (
    <div className={`app app--${scene}`} style={{ "--glow": css(average, 0.12) } as CSSProperties}>
      <Room image={scene === "touring" ? painting?.image ?? null : null} />
      <TopStrip online={online} drawerOpen={drawerOpen} onToggleDrawer={() => setDrawerOpen((o) => !o)} />
      {scene === "offline" && <IdleScreen offline />}
      {scene === "idle" && <IdleScreen offline={false} />}
      {scene === "looking-up" && state && <LookingUp detail={state.activity.gemini.detail} />}
      {scene === "touring" && state && painting && (
        <>
          <div className="col col--art">
            <PaintingStage painting={painting} section={section} frameRef={frameRef} grid={flowFor !== null} />
            <Placard painting={painting} />
          </div>
          <div className="col col--touch">
            <TouchBoard section={section} total={painting.sections.length} hardware={state.hardware} colors={colors} held={held} wellsRef={wellsRef} />
            <Captions lines={state.transcript} speech={speech} />
          </div>
          <TourRail sections={painting.sections} current={section?.number ?? null} visited={visited} />
          {flowFor && (
            <BorderlessFlow key={flowFor.number} section={flowFor} colors={colors} frameRef={frameRef} wellsRef={wellsRef} onLanded={landed} />
          )}
        </>
      )}
      {state && <AgentDrawer open={drawerOpen} activity={state.activity} frame={section?.frame ?? null} onClose={() => setDrawerOpen(false)} />}
    </div>
  );
}
```

- [ ] **Step 3: `screen/src/App.css`**

```css
/* One continuous dark room: strip on top, art | touch, rail at the bottom. No cards. */
.app { position: relative; isolation: isolate; height: 100vh; display: grid; grid-template-columns: 58fr 42fr; grid-template-rows: auto minmax(0, 1fr) auto; column-gap: var(--gutter); row-gap: var(--spacing-6); padding: var(--margin-y) var(--margin-x); }
.col { min-height: 0; display: flex; flex-direction: column; }
.col--art { gap: var(--spacing-5); }
.col--touch { gap: var(--spacing-7); }
@media (max-width: 1100px) {
  .app { height: auto; min-height: 100vh; grid-template-columns: 1fr; grid-template-rows: auto; }
  .captions { max-height: 60vh; }
}
/* 720p and 768p projectors: everything on one screen. */
@media (max-height: 800px) and (min-width: 1101px) {
  .app { row-gap: var(--spacing-4); }
  .col--touch { gap: var(--spacing-5); }
  .board__grid { width: min(100%, 38vh); }
  .board__numeral { font-size: 200px; }
  .stage__clip img { max-height: calc(100vh - 300px); }
  .placard__title { font-size: 48px; }
}
```

- [ ] **Step 4: Remove the old UI**

In `screen/src/main.tsx` delete the line `import "./styles.css";`. Then run:
`git rm screen/src/styles.css screen/src/components/PaintingView.tsx screen/src/components/Transcript.tsx screen/src/components/ActivityBar.tsx screen/src/components/Board.tsx`

- [ ] **Step 5: Tests, type-check, build**

Run: `cd screen && npm test && npm run build`
Expected: `# fail 0`; tsc clean; vite prints `dist/index.html` and `dist/assets/*.js`, `*.css`, `*.woff2`.

Run (repo root): `source .venv/bin/activate && python test_screen.py`
Expected: all tests pass, as before.

- [ ] **Step 6: Commit**

```bash
git add -A screen
git commit -m "screen: Borderless Night layout, flow transition, rebuilt dist"
```

---

### Task 16: Visual verification against Paper

**Files:**
- Create: `docs/design/screens/after-*.png`
- Modify: whichever component `.css` files need fixes (then rebuild `dist/`)

**Interfaces:**
- Consumes: the Paper exports in `docs/design/paper/` (Task 9) as the reference.

- [ ] **Step 1: Run the demo on port 8001** (background): `python screen.py --demo --port 8001`

- [ ] **Step 2: Screenshots with the Playwright MCP**, saved to `docs/design/screens/`:
  - 1920×1080: `after-looking-up-1920.png` (within 2s of load), `after-touring-1920.png` (about 10s in),
    `after-flow-1920.png` (taken 0.6s after a part change, mid-flight: the demo changes part every 6s),
    `after-drawer-1920.png` (press `s` first, then press `s` again to close).
  - 1440×900: `after-touring-1440.png`.
  - 1280×720 (projector): `after-touring-1280x720.png`; confirm
    `document.documentElement.scrollHeight <= innerHeight` with `browser_evaluate`.
  - 400×900: `after-narrow-400.png` (full page).
  - Reduced motion: `browser_emulate_media` with `reducedMotion: "reduce"`, then `after-reduced-1920.png`.
  - Idle: stop the demo and start `python -c "import screen,threading; screen.start_screen(8002); threading.Event().wait()"`;
    take `after-idle-1920.png` from `http://127.0.0.1:8002`.
  - Offline: stop that server and wait 1s; take `after-offline-1920.png`.

- [ ] **Step 3: Compare.** Open each screenshot next to its Paper export with the Read tool. For each pair,
  write one line covering layout, type sizes, colours, spacing and alignment. Fix differences in the
  component CSS, run `cd screen && npm run build`, and retake that screenshot. Also confirm:
  - no horizontal scroll at 400 wide;
  - no text under 13px (`browser_evaluate`:
    `[...document.querySelectorAll('body *')].filter(e=>e.childNodes[0]?.nodeType===3&&parseFloat(getComputedStyle(e).fontSize)<13).length === 0`);
  - the flow screenshot shows dots between the painting and the board.

- [ ] **Step 4: Commit**

```bash
git add docs/design/screens screen
git commit -m "screen: match Paper designs; after screenshots"
```

---

### Task 17: Devpost decision record

**Files:**
- Create: `docs/design/design-decisions.md`

**Interfaces:**
- Consumes: the spec, `docs/design/inspiration.md`, `docs/design/paper/*`, `docs/design/screens/before-*` and `after-*`.

- [ ] **Step 1: Write `docs/design/design-decisions.md` with exactly these sections**

1. **The story (why this exists).** The teamLab visit (water room, works that react to you and flow
   between rooms); the realisation that immersive art is visual-only; the screen's role (sighted judges
   and the room watching a blind visitor's tour).
2. **Before / after.** Embed `screens/before-touring-1920.png` and `screens/after-touring-1920.png` side by
   side, plus the after flow, idle and drawer shots. Add one paragraph on what changed: three boxed panels
   and chat bubbles became one continuous room; system font became a placard type system; a gold box
   became a spotlight plus a flowing transition.
3. **How we worked.** Audit of the 5 old sections and their states → 147 Mobbin references in 9 sections
   (link `inspiration.md`) → 7 patterns → 3 directions → chosen direction → Paper file (link
   `paper/tactile-art-guide-design.pdf`) → code that matches it.
4. **Judging criteria → decisions.** A table with the columns: criterion | decision | evidence. Rows:
   - Hierarchy: light is the only hierarchy; one lantern accent means "now"; display/label scale contrast.
   - Legibility: AAA contrast ratios (16.7:1, 8.8:1); 13px floor; captions newest-largest; sized for 3m.
   - Consistency: one shape language (the ball); one token set shared by Paper and CSS; 8px spacing.
   - Contrast: ratios table; paper-faint restricted to decoration.
   - Ease of use: zero interaction needed; `S` key drawer; status words, not just colours; offline and
     idle states explain themselves.
   - Craft and character: the Lantern Water palette from real objects; hand-drawn hook; the Borderless flow;
     balls coloured by the painting; museum voice.
5. **Design system decisions.** One subsection each for colour, type, space, shape, motion and voice.
   Each states the decision, the reason, and the inspiration codes it came from, for example:
   - "Speaking ripple ← Delphi V01 + PlayAI V03";
   - "Giant numeral ← Polestar B20";
   - "Placard lockup ← Harvest I03";
   - "Drawer ← Base44 A07";
   - "Rail ← Gusto T01 + Etsy T08";
   - "Idle copy ← Cosmos I15 + Visitors H10";
   - "Painting-coloured UI ← Savee P03 + TIDAL P09".
6. **The signature moment: Borderless flow.** The 4 storyboard frames (`paper/6-*.png`) with timings, and
   why it matters: it shows in one motion that this part of the painting becomes this shape under your hand.
7. **What we rejected and why.** Directions B and C; blue-purple AI orbs (C01, V10); log tables (A02,
   A10); chat bubbles; cards; a light mode (we committed to the dark teamLab room; mention a projector test only if one was actually run).
8. **Accessibility of the screen itself.** Contrast, words alongside colour, reduced motion, `aria-live`
   captions, ball grid `role="img"` with a raised count.
9. **Devpost: "Design" section (ready to paste).** 150–250 words in plain first-person-plural prose
   covering story, process, system, signature moment and craft. Link the Paper file only if the team
   has made a public share link; otherwise point to `docs/design/paper/tactile-art-guide-design.pdf`.

- [ ] **Step 2: Check it.** Every image path exists (`ls` each). No claims about things that weren't done
  (for example, only mention projector testing if it happened).

- [ ] **Step 3: Commit**

```bash
git add docs/design/design-decisions.md
git commit -m "docs: design decision record and Devpost design section"
```
