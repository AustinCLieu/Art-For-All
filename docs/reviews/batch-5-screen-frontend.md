# Review: Batch 5, audience screen frontend (`screen/src`, configs)

Scope: `git diff 4b825dc..9612a6e -- screen/src screen/index.html screen/vite.config.ts screen/tsconfig.json screen/package.json`
(13 files, 404 lines). Compared against `docs/superpowers/plans/2026-10-17-audience-screen.md` (Task 3),
`CLAUDE.md` and `screen.py` (`snapshot()` / `_views()`).

Checks I ran:
- Every file in scope is **byte-for-byte identical** to the code block for it in the plan (I extracted
  the 13 blocks with a script and compared them). So the implementation follows the plan exactly, and
  every issue below is an issue in the plan itself.
- `types.ts` compared field by field with `screen.snapshot()` / `_views()`.
- All 4 cached paintings: image is `.jpg` (served by `/cache/`), every grid is 10 rows of 10, every
  section has `location`, `year` is a string.
- `screen/dist/assets/index-BNJ5VTov.js` contains the current UI strings ("Waiting for main.py",
  "Tactile Tour Writer agent", "All balls down", "no-store", `--row`, `scrollHeight`). dist and src were
  committed together in cea346a and src hasn't changed since, so dist is not stale.
- I did not run `tsc` (there is no `screen/node_modules` in this worktree) and did not open it in a
  browser (no Playwright). The layout numbers in I-1 are worked out from the CSS, not measured.

### Strengths
- **The types match the backend.** All `State` fields, the four activity keys, `image: string | null`,
  `painting`/`section` being null together (`_views` returns both or neither), `bbox` as a 4-tuple and
  `frame` all match `screen.py`. `test_screen.py` checks the same shape on the Python side.
- **The polling hook is solid** (`useScreenState.ts`). It chains `setTimeout` (no overlapping requests,
  unlike `setInterval`). The `alive` flag plus `clearTimeout` stops it cleanly on unmount, including
  under StrictMode's double mount in dev. It re-renders only when the JSON text changes. `cache:
  "no-store"` is set, and errors (non-200, network failure, bad JSON) all go to `online = false`
  without throwing. No leaks.
- **The empty and offline states work.** Before the first poll and while main.py is down, every
  component gets a safe default (`?? null`, `?? []`, `FLAT` grid, the "No painting yet" panel, the
  transcript hint, `ActivityBar` hidden until there is state). Losing the backend keeps the last frame
  on screen and turns the pill red, which is the right call for a live demo.
- **The board orientation is correct.** It renders rows top to bottom and columns left to right, so
  row 0 is at the top (the edge farthest from the visitor) and column 0 is on the visitor's left, as
  `CLAUDE.md` says. The "one row at a time" animation is only a CSS delay (`--row`), cheap and
  self-contained.
- **It is demo-safe.** It uses system fonts and no CDN, has a `prefers-reduced-motion` fallback, an
  `aria-label` on the board, and pins exact dependency versions. The Vite dev proxy uses 127.0.0.1 (the
  comment explains the IPv6 reason). The image URL is built on the server (`/cache/<basename>`), so the
  client never has to resolve paths.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)
**I-1. The board panel probably overflows on a 1280x720 or 1366x768 screen.**
`screen/src/styles.css:23,31,49,66`
- **What's wrong:** The board is `min(100%, 52vh)` tall, and the panel also holds the heading, the
  section name, the caption and a 101-character `F...` frame line that wraps to about two lines. My
  estimate from the CSS:
  - At 1280x720 the stage row is about 505px tall, but the board panel needs about 545px.
  - At 1366x768 it is about 6px over.
  - At 1920x1080 it fits easily.
- **Why it matters:** `.panel` has no `overflow: hidden`, so the caption and frame line would spill out
  of the panel and over the sponsor chips. That would be visible to judges if the projector or
  mirrored laptop runs at 720p.
- **How to fix:** First check it in Chrome DevTools at 1280x720. If it overflows, change `52vh` to
  about `44vh` in `.board`, or hide `.frame` below a height breakpoint
  (`@media (max-height: 800px) { .frame { display: none } }`).

#### Minor (Nice to Have)
**M-1. Transcript auto-scroll can stop once the transcript is full.**
`screen/src/components/Transcript.tsx:6-10`
- **What's wrong:** The effect depends on `[lines.length, last]`. After 50 lines (`MAX_LINES`), the
  length stays at 50. If the new last line has the same text as the old one (the visitor says "Next."
  twice in a row), neither dependency changes and the panel doesn't scroll.
- **Why it's minor:** The `--demo` run has only 36 lines, but a long rehearsal plus the live demo
  without restarting main.py could hit it.
- **How to fix:** Use `[lines]` as the dependency. The array identity only changes when the JSON
  changes, thanks to the `last.current` check in the hook.

**M-2. No timeout on the poll request.** `screen/src/useScreenState.ts:15`
- **What's wrong:** If screen.py accepts the connection but never answers (for example, main.py
  suspended with Ctrl+Z, or the server thread stalled), the `await fetch` never returns. Polling stops
  and the pill stays green ("Live") while the data is frozen.
- **How to fix:** Add `signal: AbortSignal.timeout(2000)` to the fetch options.

**M-3. No error boundary.** `screen/src/main.tsx:6-10`
- **What's wrong:** Any error during render blanks the whole page. Today the backend guarantees the
  shape: `_views` would raise on a `None` row and `snapshot()` falls back to `painting: null`. But a
  grid row stored as a string would get through Python (`for v in row` works on strings) and then
  throw at `row.map` in `Board.tsx:16`.
- **Why it's minor:** It is unlikely with the cached paintings, all of which I verified.
- **How to fix:** Either add a 10-line class `ErrorBoundary` around `<App/>` that shows the last good
  frame or "Screen error, refresh", or coerce the grid in `Board`:
  `Array.from({length:10},(_,r)=>Array.from({length:10},(_,c)=>Number(grid?.[r]?.[c])||0))`. The
  second also fixes M-4.

**M-4. The board assumes the grid is exactly 10x10.** `screen/src/components/Board.tsx:8,15-19`
- **What's wrong:** A short or long row would shift every later cell, because CSS grid places cells in
  order, and the shape would look wrong.
- **How to fix:** Normalize the grid as shown in M-3.

**M-5. A missing image shows a broken-image icon.** `screen/src/components/PaintingView.tsx:16`
- **What's wrong:** For a painting that wasn't cached and whose image 404s, or one with a `.webp` or
  `.tif` image (`screen.py` only serves `.jpg`, `.jpeg` and `.png`), the browser shows a broken icon
  with the alt text, and the gold box is positioned over the alt text.
- **How to fix:** Add `onError={(e) => (e.currentTarget.style.display = "none")}`.

**M-6. React warning in dev only.** `screen/src/components/ActivityBar.tsx:19`
- **What's wrong:** `aria-hidden` without a value renders as `aria-hidden="true"`, which is fine. This
  is a nit only: React may warn in dev about passing a boolean `true` to an `aria-*` attribute, which
  `aria-hidden={true}` avoids.
- **Why it doesn't matter for the demo:** The production build is unaffected.

**M-7. No automated frontend check.** `screen/package.json:8`
- **What's wrong:** `npm run build` runs `tsc`, but nothing runs it in CI or in the plain-script test
  suite. The plan relies on a manual browser check (Task 6, Step 1), which is reasonable for a
  hackathon.
- **What to do:** Make sure whoever touches `screen/src` before the freeze runs `npm run build` and
  commits `dist/`, as `CLAUDE.md` says.

### Recommendations
1. Before the freeze, open `python screen.py --demo` at the projector's real resolution (or in DevTools
   at 1280x720) and confirm I-1. It is the only issue an audience is likely to see.
2. If there is time: the `[lines]` scroll fix (M-1), the fetch timeout (M-2) and the grid
   normalization (M-3/M-4). Each is a one-line change. Rebuild `dist/` afterwards.
3. Plan note: the plan put the full source inline, which made this batch exact and easy to check. It
   just didn't budget for small projector resolutions or a timeout on polling.

### Assessment
**Ready to merge?** Yes (I-1 is cosmetic and should be checked at the projector resolution; it can't
crash anything).

**Reasoning:** The frontend matches the plan exactly, its types match `screen.py`, it handles the empty
and offline states and unmounting cleanly, and the board orientation is correct. The remaining items
are layout and robustness polish that can't blank the screen or affect the tour.
