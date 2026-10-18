# Relief Render Progress Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show one progress bar on the audience screen that tracks how far the 10,000-pin reliefs (the "3D relief" heightmaps) are from finished rendering.

**Architecture:** The reliefs are already made one section at a time in a background thread (`paintings.add_reliefs`), writing into the same painting dict the screen polls. We add a tiny progress channel to `screen.py` (`render(phase, done, total)` + a `render` field in `snapshot()`), have `paintings.add_reliefs` report progress as each section lands, and draw a single bar in the React app that appears while rendering and hides when done. Everything stays optional: a failure in the progress path never affects the tour or the reliefs.

**Tech Stack:** Python 3 stdlib (`screen.py`, `paintings.py`), React + TypeScript + Vite (`screen/`), plain-script tests (`test_screen.py`, `test_pipeline.py`).

## Global Constraints

- Only touch Austin-owned files: `screen.py`, `screen/`, `test_screen.py`, `paintings.py`, `test_pipeline.py` (per `CLAUDE.md`). Do not change the `CLAUDE.md` contract section (this touches only the internal `/api/state` JSON, which `test_screen.py` keeps in sync).
- Every public function in `screen.py` and the relief path must never raise — wrap bodies in `try/except` that prints and returns, matching the existing `say`/`activity` pattern. An exception inside a screen call must not break the tour.
- Keep copy in museum-wall-label tone (`screen/src/design/copy.ts`), never dashboard tone.
- Use only existing design tokens from `screen/src/design/tokens.css` (`--color-lantern`, `--color-stone-2`, `--color-paper-dim`, `--radius-full`, `--spacing-*`, `--margin-x`, `--ease-light`, `--dur-fade`). The accent is `--color-lantern` (#ffb547), the one accent colour.
- Tests are plain scripts (no pytest): run with `python test_screen.py` and `python test_pipeline.py`.
- After any UI change, rebuild the committed bundle: `cd screen && npm install && npm run build`. `screen/dist/` is committed.
- The `render` snapshot field shape is fixed and shared by backend and frontend: `{"phase": "idle" | "preparing" | "rendering" | "done", "done": int, "total": int}`.

---

## File Structure

- `screen.py` (modify) — add module state `_render`, a `render(phase, done, total)` reporter, include `render` in `snapshot()`, and emit a simulated sequence in `demo()` so the bar is visible offline.
- `paintings.py` (modify) — import `render` from `screen` (with a no-op stub fallback), and report progress from `add_reliefs` / `start_reliefs`.
- `test_screen.py` (modify) — reset `_render` in `reset()`, add `test_render_progress`, extend `test_never_raises`.
- `test_pipeline.py` (modify) — extend `test_add_reliefs` to assert progress reached `done`.
- `screen/src/types.ts` (modify) — add the `Render` interface and `render` on `State`.
- `screen/src/design/copy.ts` (modify) — add `renderLabel` and `renderPreparing` strings.
- `screen/src/components/RenderProgress.tsx` (create) — the single bar; returns `null` when not rendering.
- `screen/src/components/RenderProgress.css` (create) — the bar's styles.
- `screen/src/App.tsx` (modify) — mount `<RenderProgress>` once, above the scenes.
- `screen/dist/**` (rebuilt) — committed Vite build output.

---

### Task 1: Backend render progress channel in `screen.py`

**Files:**
- Modify: `screen.py` (module state near `_activity`; new `render()` after `activity()`; `snapshot()` output; `demo()`)
- Test: `test_screen.py`

**Interfaces:**
- Produces: `screen.render(phase: str, done: int = 0, total: int = 0) -> None` (never raises); `screen._render` dict `{"phase", "done", "total"}`; `snapshot()["render"]` with the same shape.
- Consumes: the existing `_lock`, `snapshot()` structure, and `demo()`.

- [ ] **Step 1: Write the failing test**

Add to `test_screen.py` after `test_agent_chips`:

```python
def test_render_progress():
    reset()
    assert screen.snapshot()["render"] == {"phase": "idle", "done": 0, "total": 0}
    screen.render("preparing", 0, 4)
    assert screen.snapshot()["render"] == {"phase": "preparing", "done": 0, "total": 4}
    screen.render("rendering", 2, 4)
    assert screen.snapshot()["render"] == {"phase": "rendering", "done": 2, "total": 4}
    screen.render("done", 4, 4)
    assert screen.snapshot()["render"] == {"phase": "done", "done": 4, "total": 4}
```

And update `reset()` (top of `test_screen.py`) to clear the new state:

```python
def reset():
    with screen._lock:
        screen._transcript.clear()
        screen._activity.clear()
        screen._live.update(painting=None, index=0)
        screen._render.update(phase="idle", done=0, total=0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python test_screen.py`
Expected: FAIL with `AttributeError: module 'screen' has no attribute '_render'` (or `render`).

- [ ] **Step 3: Add the module state**

In `screen.py`, below the `_activity = {}` line (currently line ~21), add:

```python
_render = {"phase": "idle", "done": 0, "total": 0}  # 10,000-pin reliefs: one global progress bar
```

- [ ] **Step 4: Add the `render()` reporter**

In `screen.py`, immediately after the `activity(...)` function (after its `return`/`except` block, ~line 60), add:

```python
def render(phase, done=0, total=0):
    """Progress of the 10,000-pin reliefs. phase is preparing, rendering, done or idle. Never raises."""
    try:
        entry = {"phase": str(phase), "done": int(done), "total": int(total)}
        with _lock:
            _render.update(entry)
    except Exception as e:
        print(f"screen.render failed: {e!r}")
```

- [ ] **Step 5: Include `render` in `snapshot()`**

In `screen.py`, in `snapshot()`, extend the initial `out` dict (currently starts `out = {"hardware": ...`) to include a default render, and copy the live value inside the lock.

Change the initializer to add one key:

```python
    out = {"hardware": os.getenv("BOARD", "sim") == "serial", "transcript": [], "painting": None,
           "section": None, "render": {"phase": "idle", "done": 0, "total": 0},
           "activity": {k: dict(IDLE) for k in ("elevenlabs", "gemini", "creao", "browser_use")}}
```

Then, inside the `with _lock:` block in `snapshot()` (after `p, i = _live["painting"], _live["index"]`), add:

```python
            out["render"] = dict(_render)
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python test_screen.py`
Expected: PASS (all tests, including `test_render_progress`).

- [ ] **Step 7: Extend `test_never_raises` for bad render input**

In `test_screen.py`, inside `test_never_raises`, after the existing `screen.activity("creao", "working", Bad(), "Mona Lisa")` line, add:

```python
    screen.render("rendering", "not a number", 4)  # int("not a number") raises inside, must be swallowed
```

- [ ] **Step 8: Run the test to verify it still passes**

Run: `python test_screen.py`
Expected: PASS. (The bad `int(...)` is caught; the snapshot stays valid.)

- [ ] **Step 9: Commit**

```bash
git add screen.py test_screen.py
git commit -m "feat(screen): add relief render progress channel to snapshot"
```

---

### Task 2: Report relief progress from `paintings.py`

**Files:**
- Modify: `paintings.py` (the `from screen import ...` try/except at ~line 8; `add_reliefs` at ~line 353; `start_reliefs` at ~line 368)
- Test: `test_pipeline.py` (`test_add_reliefs` at ~line 330)

**Interfaces:**
- Consumes: `screen.render(phase, done, total)` from Task 1.
- Produces: `add_reliefs` emits `render("preparing", 0, total)`, then `render("rendering", i, total)` per section, then `render("done", total, total)`; `start_reliefs` emits `render("idle")` when there is nothing to render.

- [ ] **Step 1: Write the failing test**

In `test_pipeline.py`, extend `test_add_reliefs`. Add `import screen` at the top of the function body and assert the final progress after `add_reliefs`:

```python
def test_add_reliefs():
    import screen
    Image.new("RGB", (100, 100), "white").save("cache/zz-relief.jpg")
    p = {"title": "Zz Relief", "image": "cache/zz-relief.jpg",
         "sections": [{"number": 1, "name": "a", "bbox": [0.1, 0.1, 0.5, 0.5]},
                      {"number": 2, "name": "b", "bbox": [0.5, 0.5, 0.9, 0.9], "relief": "keep.png"}]}
    try:
        paintings.add_reliefs(p)
        saved = json.load(open("cache/zz-relief.json"))
        files = sorted(os.path.basename(f) for f in glob.glob("cache/zz-relief*"))
    finally:
        for f in glob.glob("cache/zz-relief*"):
            os.remove(f)
    assert saved["sections"][0]["relief"] == "cache/zz-relief-1-relief.png"
    assert saved["sections"][0]["relief_color"] == "cache/zz-relief-1-relief-color.png"
    assert saved["sections"][1]["relief"] == "keep.png"  # already had one: left alone without force
    assert files == ["zz-relief-1-relief-color.png", "zz-relief-1-relief.png", "zz-relief.jpg", "zz-relief.json"]
    assert screen.snapshot()["render"] == {"phase": "done", "done": 2, "total": 2}  # both sections counted
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python test_pipeline.py`
Expected: FAIL on the final assert — `render` stays `{"phase": "idle", "done": 0, "total": 0}` because `add_reliefs` does not report yet.

- [ ] **Step 3: Import `render` in `paintings.py`**

In `paintings.py`, replace the existing screen import block (currently):

```python
try:
    from screen import activity  # audience screen; optional
except Exception:  # nothing here depends on the screen
    def activity(*args, **kwargs):
        pass
```

with:

```python
try:
    from screen import activity, render  # audience screen; optional
except Exception:  # nothing here depends on the screen
    def activity(*args, **kwargs):
        pass
    def render(*args, **kwargs):
        pass
```

- [ ] **Step 4: Report progress from `add_reliefs`**

In `paintings.py`, replace the body of `add_reliefs` (currently):

```python
def add_reliefs(p, force=False):
    """Make the 10,000-pin heightmaps of p's sections that have none (all with force), in tour order.
    A section whose relief fails is left without one. Saves and returns p."""
    with Image.open(p["image"]) as img:
        img = img.convert("RGB")
    for s in p["sections"]:
        if force or not s.get("relief"):
            m, = make_reliefs(img, [s])
            if m:  # one at a time: the screen shows each relief as soon as it lands
                s.update(save_relief(m, f"{CACHE}/{slug(p['title'])}-{s['number']}"))
    save_painting(p)
    return p
```

with:

```python
def add_reliefs(p, force=False):
    """Make the 10,000-pin heightmaps of p's sections that have none (all with force), in tour order.
    A section whose relief fails is left without one. Saves and returns p."""
    with Image.open(p["image"]) as img:
        img = img.convert("RGB")
    total = len(p["sections"])
    render("preparing", 0, total)  # model may still be downloading on the first make_reliefs call
    for i, s in enumerate(p["sections"], start=1):
        if force or not s.get("relief"):
            m, = make_reliefs(img, [s])
            if m:  # one at a time: the screen shows each relief as soon as it lands
                s.update(save_relief(m, f"{CACHE}/{slug(p['title'])}-{s['number']}"))
        render("rendering", i, total)  # count processed sections, so the bar always reaches 100%
    render("done", total, total)
    save_painting(p)
    return p
```

- [ ] **Step 5: Reset progress when there is nothing to render in `start_reliefs`**

In `paintings.py`, in `start_reliefs`, update the early-return guard (currently):

```python
    if not make_reliefs or all(s.get("relief") for s in p["sections"]):
        return
```

to:

```python
    if not make_reliefs or all(s.get("relief") for s in p["sections"]):
        render("idle")  # cached or already complete: no bar for this painting
        return
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python test_pipeline.py`
Expected: PASS (including the new `render` assert in `test_add_reliefs`).

- [ ] **Step 7: Run the full screen test to confirm no regression**

Run: `python test_screen.py`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add paintings.py test_pipeline.py
git commit -m "feat(paintings): report relief render progress to the screen"
```

---

### Task 3: Frontend types and copy

**Files:**
- Modify: `screen/src/types.ts`
- Modify: `screen/src/design/copy.ts`

**Interfaces:**
- Produces: `Render` type (`phase`, `done`, `total`) and `State.render`; `COPY.renderLabel`, `COPY.renderPreparing`. Consumed by Tasks 4 and 5.
- Consumes: the `render` snapshot field from Task 1.

- [ ] **Step 1: Add the `Render` type and `State.render`**

In `screen/src/types.ts`, after the `Activity` interface (before `export interface State`), add:

```typescript
export interface Render {
  phase: "idle" | "preparing" | "rendering" | "done";
  done: number;
  total: number;
}
```

Then, inside `export interface State { ... }`, add a `render` field right after `section`:

```typescript
export interface State {
  hardware: boolean;
  transcript: Line[];
  painting: Painting | null;
  section: Section | null;
  render: Render;
  activity: {
    elevenlabs: Activity;
    gemini: Activity;
    creao: Activity;
    browser_use: Activity;
  };
}
```

- [ ] **Step 2: Add the copy strings**

In `screen/src/design/copy.ts`, inside the `COPY` object, after the `pinsNoWebgl` line, add:

```typescript
  renderLabel: "Rendering the 3D relief",
  renderPreparing: "Preparing the 3D relief…",
```

- [ ] **Step 3: Type-check**

Run: `cd screen && npx tsc --noEmit`
Expected: No errors (the new fields are referenced by later tasks; this step only confirms the types compile).

- [ ] **Step 4: Commit**

```bash
git add screen/src/types.ts screen/src/design/copy.ts
git commit -m "feat(screen): add Render type and progress copy"
```

---

### Task 4: The `RenderProgress` component

**Files:**
- Create: `screen/src/components/RenderProgress.tsx`
- Create: `screen/src/components/RenderProgress.css`

**Interfaces:**
- Consumes: `Render` from `../types`, `COPY` from `../design/copy`.
- Produces: `RenderProgress({ render }: { render: Render })` — a single fixed bar, or `null` when `phase` is not `preparing`/`rendering` or `total` is 0. Consumed by Task 5.

- [ ] **Step 1: Create the component**

Create `screen/src/components/RenderProgress.tsx`:

```tsx
import type { CSSProperties } from "react";
import { COPY } from "../design/copy";
import type { Render } from "../types";
import "./RenderProgress.css";

// One bar for the whole screen: how far the 10,000-pin reliefs are from rendered.
// Shows while they render (including the model-download "preparing" phase), hides when done.
export function RenderProgress({ render }: { render: Render }) {
  const active = render.total > 0 && (render.phase === "preparing" || render.phase === "rendering");
  if (!active) return null;
  const preparing = render.phase === "preparing";
  // While the depth model downloads, done is 0: show a faint pulsing sliver instead of an empty bar.
  const fraction = preparing ? 0.08 : render.done / render.total;
  return (
    <div className={`render render--${render.phase}`} role="status" aria-live="polite">
      <div className="render__text label">
        <span>{preparing ? COPY.renderPreparing : COPY.renderLabel}</span>
        {!preparing && <span className="render__count">{render.done} / {render.total}</span>}
      </div>
      <div className="render__track" aria-hidden>
        <div className="render__fill" style={{ "--p": fraction } as CSSProperties} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create the styles**

Create `screen/src/components/RenderProgress.css`:

```css
.render {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 8;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  padding: var(--spacing-5) var(--margin-x) var(--spacing-3);
  pointer-events: none;
  background: linear-gradient(to top, rgb(8 9 11 / 0.85), transparent);
}
.render__text { display: flex; justify-content: space-between; color: var(--color-paper-dim); }
.render__count { color: var(--color-lantern); }
.render__track {
  position: relative;
  height: 4px;
  border-radius: var(--radius-full);
  background: var(--color-stone-2);
  overflow: hidden;
}
.render__fill {
  position: absolute;
  inset: 0;
  transform-origin: left;
  transform: scaleX(var(--p));
  background: var(--color-lantern);
  border-radius: var(--radius-full);
  transition: transform var(--dur-fade) var(--ease-light);
}
.render--preparing .render__fill { animation: render-pulse 1.4s ease-in-out infinite; }
@keyframes render-pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.7; } }
@media (prefers-reduced-motion: reduce) {
  .render--preparing .render__fill { animation: none; opacity: 0.5; }
  .render__fill { transition: none; }
}
```

- [ ] **Step 3: Type-check**

Run: `cd screen && npx tsc --noEmit`
Expected: No errors (component compiles; it is not yet mounted).

- [ ] **Step 4: Commit**

```bash
git add screen/src/components/RenderProgress.tsx screen/src/components/RenderProgress.css
git commit -m "feat(screen): add RenderProgress bar component"
```

---

### Task 5: Mount the bar in `App.tsx`

**Files:**
- Modify: `screen/src/App.tsx`

**Interfaces:**
- Consumes: `RenderProgress` from `./components/RenderProgress`, `state.render` from Task 3.
- Produces: the bar rendered once, above all scenes, whenever `state` exists.

- [ ] **Step 1: Import the component**

In `screen/src/App.tsx`, add the import alongside the other component imports (keep imports alphabetical — place after the `Room` import):

```tsx
import { RenderProgress } from "./components/RenderProgress";
```

- [ ] **Step 2: Mount it once, above the scenes**

In `screen/src/App.tsx`, inside the returned JSX, add the bar right after the `<TopStrip ... />` line (so it sits above every scene and the component itself decides whether to show):

```tsx
      {state && <RenderProgress render={state.render} />}
```

- [ ] **Step 3: Type-check and build**

Run: `cd screen && npx tsc --noEmit && npm run build`
Expected: No type errors; Vite build succeeds and writes `screen/dist/`.

- [ ] **Step 4: Commit**

```bash
git add screen/src/App.tsx
git commit -m "feat(screen): mount the render progress bar in App"
```

---

### Task 6: Make the bar visible offline via `screen.py --demo`, then verify and rebuild

**Files:**
- Modify: `screen.py` (`demo()`)
- Rebuild: `screen/dist/**`

**Interfaces:**
- Consumes: `render()` from Task 1.
- Produces: a simulated progress sequence during `demo()` so `python screen.py --demo` shows the bar without any API keys.

- [ ] **Step 1: Emit a simulated sequence in `demo()`**

In `screen.py`, in `demo()`, inside the `for path in sorted(...)` loop, after the existing `activity("gemini", "done", f"{p['title']}: ready from cache")` line, add a short simulated render so the bar is visible offline:

```python
        total = len(p["sections"])
        render("preparing", 0, total)
        time.sleep(1.5)
        for n in range(1, total + 1):
            render("rendering", n, total)
            time.sleep(0.8)
        render("done", total, total)
```

- [ ] **Step 2: Run the screen test to confirm nothing regressed**

Run: `python test_screen.py`
Expected: PASS. (`demo()` is not exercised by tests, but `render`/`snapshot` are.)

- [ ] **Step 3: Manually verify the bar**

Run: `python screen.py --demo` and open http://127.0.0.1:8000.
Expected: For each painting, a thin lantern-coloured bar appears at the bottom — a faint pulse during "Preparing the 3D relief…", then filling "1 / N … N / N" as it renders, then disappearing. Ctrl+C to stop.

- [ ] **Step 4: Rebuild the committed bundle**

Run: `cd screen && npm install && npm run build`
Expected: `screen/dist/` is regenerated with the new component.

- [ ] **Step 5: Run the full test suite one more time**

Run: `python test_screen.py && python test_pipeline.py`
Expected: Both PASS.

- [ ] **Step 6: Commit**

```bash
git add screen.py screen/dist
git commit -m "feat(screen): simulate render progress in demo and rebuild bundle"
```

---

## Self-Review

**1. Spec coverage (one progress bar for image/relief rendering):**
- Backend progress source — Task 1 (`screen.render` + snapshot) and Task 2 (`paintings.add_reliefs` reports it). ✓
- One bar in the frontend — Task 4 (`RenderProgress`, returns `null` unless rendering) + Task 5 (mounted once in `App`). ✓
- Shows the model-download/"preparing" phase from the screenshot — `render("preparing", 0, total)` in `add_reliefs` + the preparing pulse state. ✓
- Visible/verifiable offline — Task 6 demo simulation + manual check. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows full code; exact file paths and run commands with expected output. ✓

**3. Type consistency:** The snapshot shape `{"phase","done","total"}` is identical in `screen.render`, `snapshot()`, `test_render_progress`, the `Render` TS interface, and `RenderProgress`. Phases `idle|preparing|rendering|done` match between `paintings.py` emissions, the TS union, and the component's `active` check. `render.done`/`render.total` are integers backend-side and numbers frontend-side. ✓

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-18-render-progress-bar.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
