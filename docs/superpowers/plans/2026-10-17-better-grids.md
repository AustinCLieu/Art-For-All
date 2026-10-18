# Better Tactile Grids Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the 10x10 grid for each painting section clearly recognizable by touch, for the four demo paintings and for any painting a judge names live.

**Architecture:** Three changes inside `paintings.py`'s drawing step, then a one-time redraw of the cache.
(B) Crop each section tightly and letterbox it onto a gray square, so Gemini sees only that part, and tell it to draw only that part, filling the board.
(C) A cheap code check, `grid_problems`, rejects drawings that are too sparse, too small or solid blobs.
(A) Each section gets 3 drafts in parallel. The drafts that pass the check go to one Gemini "judge" call, which looks at the crop next to the rendered boards and picks the most recognizable.
(D) A `--redraw` flag on `prepare_demo.py` redraws the cached demo paintings. A person then reviews every grid and rewrites the board half of each guide note.

**Tech Stack:** Python 3, Pillow (`Image`, `ImageDraw`), google-genai (`gemini-3-flash-preview`), plain-script tests (no pytest).

**Spec:** No separate spec file. The design was agreed in chat and is summarized under "Background" below.

## Background (why each change)

Measured on `cache/*.json` on 2026-10-17:
- 7 of 16 cached grids are solid blobs. They are Girl with a Pearl Earring (all 4), Mount Fuji, the cypress tree, and the village. They were drawn before `GRID_PROMPT` said "not solid blobs" and were never redrawn.
- "her eyes" (Mona Lisa) has the bbox `[0.36, 0.195, 0.575, 0.25]`, which is wide and thin. `crop_square` pads it out to a square of painting, so Gemini also sees the forehead and nose and draws brows, eyes and nose. Each eye ends up only 2x3 balls.
- One draw per section, no check: whatever comes back first is cached (e.g. "her enigmatic smile" is three stacked curves).
- Blob metric used by `grid_problems`: "interior" balls are raised balls whose 4 neighbours are all raised. All 7 blobs have interior/total ≥ 0.38. All 9 outlines are ≤ 0.10. The threshold is 0.3.
- `creao.py` sends Creao only section names, so Creao can't write notes that describe the board. The current "board-true" guide notes were edited by hand in commit `d69dfa1`. After redrawing, they have to be rewritten by hand the same way.

## Global Constraints

- Work on branch `feat/better-grids` (already created off `main`). Do not commit to `main`.
- `paintings.py`, `prepare_demo.py`, `test_pipeline.py` and `cache/` belong to Austin (CLAUDE.md). Harvey tells Austin before merging.
- Do not change the contract in CLAUDE.md. `load_painting` / `save_painting` signatures, the painting JSON schema and `grid` format (10 rows of 10, 0/1, row 0 = top) all stay the same.
- No new dependencies. `ImageDraw` is part of Pillow, which is already installed.
- Tests are plain scripts: `python test_pipeline.py`. A test is a module-level `def test_*()` and runs automatically.
- The demo paintings must still load from cache with the network forbidden (`test_demo_paintings_load_without_network`).
- Feature freeze: 2026-10-18 10:00 AM Pacific. Tasks 1-4 are code. Task 5 is a live redraw that needs `GEMINI_API_KEY`.
- Activate the venv first: `source .venv/bin/activate`.

---

### Task 1: Tight letterboxed crop + "draw only this part" prompt (B)

**Files:**
- Modify: `paintings.py` (`GRID_PROMPT` at lines 35-54, `crop_square` at lines 142-149, the import line 4)
- Test: `test_pipeline.py` (`test_crop_square`, `test_crop_square_degenerate`)

**Interfaces:**
- Produces: `crop_square(img, bbox, pad=0.05) -> PIL.Image` (RGB, square, at least 8x8). The part fills one axis and gray `(128, 128, 128)` bars fill the other. The name and positional arguments are the same as before, so `fetch_painting` needs no change.

- [ ] **Step 1: Write the failing tests**

Replace `test_crop_square` and `test_crop_square_degenerate` in `test_pipeline.py` with:

```python
def test_crop_square():
    img = Image.new("RGB", (100, 200), "red")
    c = paintings.crop_square(img, [0.2, 0.1, 0.4, 0.2])  # 20x20 px box at (20, 20)
    assert c.size == (22, 22)  # 20 * (1 + 2 * 0.05)
    tall = paintings.crop_square(img, [0.0, 0.0, 0.1, 0.5])  # 10x100 px box at the image's left edge
    assert tall.size == (105, 105)  # clipped to the image, then letterboxed
    assert tall.getpixel((tall.width // 2, 50)) == (255, 0, 0)  # the part, in the middle
    assert tall.getpixel((tall.width - 1, 50)) == (128, 128, 128)  # gray bar, not more painting

def test_crop_square_degenerate():
    img = Image.new("RGB", (200, 100))
    for bbox in ([0.6, 0.6, 0.4, 0.4], [0.5, 0.5, 0.5001, 0.5001]):  # inverted, sub-pixel
        c = paintings.crop_square(img, bbox)
        assert c.size[0] == c.size[1] and c.size[0] >= 8 and c.mode == "RGB"

def test_grid_prompt_asks_for_only_the_part():
    p = paintings.GRID_PROMPT.format(name="her eyes", title="Mona Lisa", description="d")
    assert "Draw only her eyes" in p and "Gray bars" in p
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python test_pipeline.py`
Expected: AssertionError in `test_crop_square` (the old crop gives `(26, 26)`)

- [ ] **Step 3: Implement**

In `paintings.py`, replace `crop_square`:

```python
def crop_square(img, bbox, pad=0.05):
    """Cut bbox out of img with a little padding and center it on a gray square: the shape isn't
    stretched on the board, and neighboring parts of the painting stay out of the drawing."""
    w, h = img.size
    x0, x1 = sorted((bbox[0] * w, bbox[2] * w))
    y0, y1 = sorted((bbox[1] * h, bbox[3] * h))
    bw, bh = max(x1 - x0, 1) * (1 + 2 * pad), max(y1 - y0, 1) * (1 + 2 * pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    part = img.crop([max(0, round(cx - bw / 2)), max(0, round(cy - bh / 2)),
                     min(w, round(cx + bw / 2)), min(h, round(cy + bh / 2))]).convert("RGB")
    side = max(part.width, part.height, 8)
    out = Image.new("RGB", (side, side), (128, 128, 128))
    out.paste(part, ((side - part.width) // 2, (side - part.height) // 2))
    return out
```

Replace the first five lines of `GRID_PROMPT` (up to and including `- About 15-50 raised balls, using most of the board.`). Keep the rest, from `- A person is a head...` through the examples and the `Return JSON` line, unchanged:

```python
GRID_PROMPT = """This crop is "{name}" from {title}: {description}
Gray bars at the edges are padding, not painting.
A blind person will feel it on a 10x10 board of raised balls. Draw only {name}, nothing around it,
and make it fill the board. Don't trace the pixels. First decide what this is and the clearest way
fingers could recognize it, then draw that.
- Outlines and key features, not solid blobs: a filled shape feels like a flat block.
- About 15-50 raised balls, reaching across at least 7 rows or 7 columns.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python test_pipeline.py`
Expected: every test prints `ok`. `test_fetch_painting` still passes because it doesn't check crop size.

- [ ] **Step 5: Commit**

```bash
git add paintings.py test_pipeline.py
git commit -m "paintings.py: crop each part tightly onto a gray square and ask Gemini to draw only that part"
```

---

### Task 2: `grid_problems` cheap checks (C)

**Files:**
- Modify: `paintings.py` (add after `fix_grid`)
- Test: `test_pipeline.py`

**Interfaces:**
- Produces: `grid_problems(grid: list[list[int]]) -> list[str]`. It returns `[]` when the grid looks fine. Otherwise it returns any of `"empty"`, `"too few balls"` (< 12), `"too many balls"` (> 60), `"too small"` (the raised balls span fewer than 7 rows and fewer than 7 columns), `"solid block"` (more than 30% of balls are interior). The input is a `fix_grid` result (10x10 of 0/1).

- [ ] **Step 1: Write the failing test**

Add to `test_pipeline.py` (module level, near the top after `DEMO`, so later tasks can reuse the constants):

```python
OUTLINE = ["...####...", ".##....##.", "#........#", "#.##..##.#", "#........#",
           "#...##...#", "#........#", "#..####..#", ".#......#.", "..######.."]  # the prompt's face
CYPRESS = ["....#.....", "....##....", "...###....", "...###....", "..#####...",
           ".######...", ".#######..", ".#######..", "#########.", "##########"]  # an old cached blob
BLOB = ["##########"] * 10
TINY = ["..####...."]

def test_grid_problems():
    g = paintings.fix_grid
    assert paintings.grid_problems(g(OUTLINE)) == []
    assert paintings.grid_problems(g(CYPRESS)) == ["solid block"]
    assert paintings.grid_problems(g(BLOB)) == ["too many balls", "solid block"]
    assert paintings.grid_problems(g(TINY)) == ["too few balls", "too small"]
    assert paintings.grid_problems(g([])) == ["empty"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_pipeline.py`
Expected: `AttributeError: module 'paintings' has no attribute 'grid_problems'`

- [ ] **Step 3: Implement**

Add to `paintings.py` right after `fix_grid`:

```python
def grid_problems(grid):
    """What would make this grid hard to feel; [] if it looks fine. Code only, no Gemini.
    A ball is 'interior' when all 4 neighbours are raised: blobs are mostly interior, outlines aren't."""
    n = sum(map(sum, grid))
    if not n:
        return ["empty"]
    rows = [r for r in range(10) if any(grid[r])]
    cols = [c for c in range(10) if any(row[c] for row in grid)]
    inner = sum(1 for r in range(1, 9) for c in range(1, 9) if grid[r][c] and grid[r - 1][c]
                and grid[r + 1][c] and grid[r][c - 1] and grid[r][c + 1])
    problems = []
    if n < 12:
        problems.append("too few balls")
    if n > 60:
        problems.append("too many balls")
    if max(rows[-1] - rows[0], cols[-1] - cols[0]) + 1 < 7:
        problems.append("too small")
    if inner > 0.3 * n:
        problems.append("solid block")
    return problems
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python test_pipeline.py`
Expected: all `ok`

- [ ] **Step 5: Commit**

```bash
git add paintings.py test_pipeline.py
git commit -m "paintings.py: grid_problems flags sparse, tiny and solid-blob grids"
```

---

### Task 3: Three drafts per section + judge call (A)

**Files:**
- Modify: `paintings.py`. Add `ImageDraw` to the PIL import. Add `DRAFTS`, `JUDGE_PROMPT`, `board_image`, `contact_sheet`, `draft`, `pick`. Rewrite `draw`.
- Test: `test_pipeline.py`. Add new tests and update the assertions at the end of `test_fetch_painting`.

**Interfaces:**
- Consumes: `grid_problems(grid) -> list[str]` (Task 2), `fix_grid`, `jpeg`, `ask_gemini(image_bytes, mime, prompt, thinking) -> dict`.
- Produces:
  - `DRAFTS = 3`
  - `board_image(grid, cell=24) -> PIL.Image` (240x240 for the default cell)
  - `contact_sheet(crop_bytes: bytes, grids: list) -> bytes`. It returns a JPEG of size `(240 + 260 * len(grids), 240)`: the crop first, then each board.
  - `pick(crop_bytes, title, s, grids) -> grid`. One Gemini call with `JUDGE_PROMPT` (it contains `"Which drawing"` and `"{n} drawings"`) and thinking `"low"`. It returns `grids[best - 1]`, or `grids[0]` on any failure or an out-of-range answer.
  - `draw(crop_bytes, title, s) -> grid | None`. The signature is unchanged. It makes `DRAFTS` parallel draft calls (thinking `"medium"`, prompt contains `"This crop is"`) and drops failed or empty drafts. If none remain it returns `None`. With 0 passing drafts it returns the draft with the fewest problems; with 1 unique passing draft it returns that one; with 2 or more it calls `pick`.

- [ ] **Step 1: Write the failing tests**

Add to `test_pipeline.py`:

```python
def fake_draws(answers, judge_says=None):
    """A stand-in for ask_gemini: drafts pop from answers (a grid, or an Exception to raise),
    the judge call returns judge_says. Records (prompt, thinking) for every call."""
    calls = []
    def fake(image_bytes, mime, prompt, thinking):
        calls.append((prompt, thinking))
        if "Which drawing" in prompt:
            return judge_says
        a = answers.pop()  # list.pop is atomic, safe from the draft threads
        if isinstance(a, Exception):
            raise a
        return {"idea": "x", "grid": a}
    return fake, calls

def run_draw(fake):
    old = paintings.ask_gemini
    paintings.ask_gemini = fake
    try:
        return paintings.draw(paintings.jpeg(Image.new("RGB", (50, 50))), "T",
                              {"name": "her face", "description": "A face."})
    finally:
        paintings.ask_gemini = old

def test_draw_judges_between_good_drafts():
    fake, calls = fake_draws([OUTLINE, BLOB, OUTLINE[::-1]], {"best": 2})
    g = run_draw(fake)
    assert g in (paintings.fix_grid(OUTLINE), paintings.fix_grid(OUTLINE[::-1]))
    judge = [(p, t) for p, t in calls if "Which drawing" in p]
    assert len(calls) == paintings.DRAFTS + 1 and len(judge) == 1
    assert "2 drawings" in judge[0][0] and judge[0][1] == "low"  # the blob never reaches the judge

def test_draw_skips_judge_for_one_good_draft():
    fake, calls = fake_draws([OUTLINE, OUTLINE, BLOB], {"best": 1})  # duplicates count once
    assert run_draw(fake) == paintings.fix_grid(OUTLINE)
    assert len(calls) == paintings.DRAFTS

def test_draw_keeps_least_bad_when_none_pass():
    fake, calls = fake_draws([BLOB, CYPRESS, TINY])
    assert run_draw(fake) == paintings.fix_grid(CYPRESS)  # 1 problem beats 2
    assert len(calls) == paintings.DRAFTS

def test_draw_none_when_all_fail():
    fake, _ = fake_draws([RuntimeError("down"), ["." * 10] * 10, RuntimeError("down")])
    assert run_draw(fake) is None

def test_pick():
    crop = paintings.jpeg(Image.new("RGB", (50, 50)))
    a, b = paintings.fix_grid(OUTLINE), paintings.fix_grid(OUTLINE[::-1])
    old = paintings.ask_gemini
    try:
        for says, want in (({"best": 2}, b), ([{"best": 2}], b), ({"best": 7}, a), ({}, a)):
            paintings.ask_gemini = lambda *args, says=says: says
            assert paintings.pick(crop, "T", {"name": "x"}, [a, b]) == want, says
    finally:
        paintings.ask_gemini = old

def test_contact_sheet():
    crop = paintings.jpeg(Image.new("RGB", (50, 80)))
    sheet = Image.open(BytesIO(paintings.contact_sheet(crop, [paintings.fix_grid(OUTLINE)] * 2)))
    assert sheet.format == "JPEG" and sheet.size == (240 + 260 * 2, 240)
```

Then update the end of `test_fetch_painting`. Replace these three lines:

```python
    first, draws = prompts[0], prompts[1:]
    assert first[0] == "image/png" and first[1] == "low"
    assert len(draws) == 3 and all(m == "image/jpeg" and t == "medium" for m, t, _ in draws)
```

with:

```python
    first, draws = prompts[0], prompts[1:]
    assert first[0] == "image/png" and first[1] == "low"
    # 3 sections x DRAFTS drafts; every draft is too small to pass grid_problems, so no judge call
    assert len(draws) == 3 * paintings.DRAFTS
    assert all(m == "image/jpeg" and t == "medium" and "This crop is" in pr for m, t, pr in draws)
```

`test_fetch_painting_drops_bad_sections` needs no change. Its "blank" section returns empty grids for every draft, so `draw` returns `None` and the section is dropped.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python test_pipeline.py`
Expected: `test_fetch_painting` fails on `paintings.DRAFTS` (`AttributeError`). It runs before the new tests because tests run in file order.

- [ ] **Step 3: Implement**

In `paintings.py` change `from PIL import Image` to `from PIL import Image, ImageDraw`.

Add after `GRID_PROMPT`:

```python
JUDGE_PROMPT = """Left: "{name}" from {title}. Right: {n} drawings of it for a 10x10 board of raised
balls (white = raised), numbered 1 to {n} from left to right. Which drawing would a blind person most
easily recognize as {name} by touch? Return JSON: {{"best": 1}}"""

DRAFTS = 3  # drawings per section; a judge call picks the best of the ones that pass grid_problems
```

Replace `draw` (currently lines 122-132) with:

```python
def board_image(grid, cell=24):
    """The grid as the board looks: white balls raised, gray flat."""
    img = Image.new("RGB", (cell * 10, cell * 10), "black")
    d = ImageDraw.Draw(img)
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            d.ellipse([c * cell + 3, r * cell + 3, (c + 1) * cell - 3, (r + 1) * cell - 3],
                      fill="white" if v else (60, 60, 60))
    return img

def contact_sheet(crop_bytes, grids):
    """The crop, then each grid as a board, side by side: what the judge call looks at."""
    crop = Image.open(BytesIO(crop_bytes)).convert("RGB").resize((240, 240))
    sheet = Image.new("RGB", (240 + 260 * len(grids), 240), "white")
    sheet.paste(crop, (0, 0))
    for i, g in enumerate(grids, start=1):
        sheet.paste(board_image(g), (260 * i, 0))
    return jpeg(sheet)

def draft(crop_bytes, title, s):
    """One drawing of a section from its crop. None if the call fails."""
    try:
        data = ask_gemini(crop_bytes, "image/jpeg", GRID_PROMPT.format(
            name=s["name"], title=title, description=s["description"]), "medium")
        if isinstance(data, list):
            data = data[0]
        return fix_grid(data["grid"])
    except Exception as e:  # one draft fewer, the others may still work
        print(f"draw failed for {s['name']!r}: {e!r}")
        return None

def pick(crop_bytes, title, s, grids):
    """Call 3: Gemini compares the drawings next to the crop. The first one if that call fails."""
    try:
        data = ask_gemini(contact_sheet(crop_bytes, grids), "image/jpeg", JUDGE_PROMPT.format(
            name=s["name"], title=title, n=len(grids)), "low")
        if isinstance(data, list):
            data = data[0]
        best = int(data["best"])
        return grids[best - 1] if 1 <= best <= len(grids) else grids[0]
    except Exception as e:
        print(f"judge failed for {s['name']!r}: {e!r}")
        return grids[0]

def draw(crop_bytes, title, s):
    """Call 2, once per section: DRAFTS drawings in parallel, cheap checks, then a judge call if more
    than one passes. None if every drawing failed or came back empty."""
    with ThreadPoolExecutor(DRAFTS) as pool:
        drafts = [g for g in pool.map(lambda _: draft(crop_bytes, title, s), range(DRAFTS))
                  if g and any(map(any, g))]
    if not drafts:
        return None
    good = [g for g in drafts if not grid_problems(g)]
    good = [g for i, g in enumerate(good) if g not in good[:i]]  # identical drafts count once
    if not good:
        return min(drafts, key=lambda g: len(grid_problems(g)))
    return good[0] if len(good) == 1 else pick(crop_bytes, title, s, good)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python test_pipeline.py`
Expected: all `ok`

- [ ] **Step 5: Commit**

```bash
git add paintings.py test_pipeline.py
git commit -m "paintings.py: three drafts per section, drop failing ones, a Gemini judge picks the best"
```

---

### Task 4: `redraw` for cached paintings + `prepare_demo.py --redraw`

**Files:**
- Modify: `paintings.py`. Add `draw_all` and `redraw`, and make `fetch_painting` use `draw_all`.
- Modify: `prepare_demo.py`. Add the `--redraw` flag.
- Test: `test_pipeline.py`

**Interfaces:**
- Consumes: `draw(crop_bytes, title, s)` (Task 3), `crop_square` (Task 1), `save_painting`.
- Produces:
  - `draw_all(img, title, sections) -> list[grid | None]`, one per section in order, drawn in parallel.
  - `redraw(p: dict) -> dict`. It redraws every section of `p` from `p["image"]` and keeps the old grid when a section's drawing fails. It also keeps `guide_notes` and `museum_facts`, then calls `save_painting(p)` and returns `p`.

- [ ] **Step 1: Write the failing test**

Add to `test_pipeline.py`:

```python
def test_redraw():
    os.makedirs("cache", exist_ok=True)
    Image.new("RGB", (100, 100), "white").save("cache/zz-redraw.jpg")
    old_grid = paintings.fix_grid(TINY)
    p = {"title": "Zz Redraw", "artist": "A", "year": "1", "summary": "S.", "image": "cache/zz-redraw.jpg",
         "guide_notes": {"good": "keep me"},
         "sections": [{"number": 1, "name": "good", "bbox": [0.1, 0.1, 0.5, 0.5], "location": "top left",
                       "description": "Good.", "grid": old_grid},
                      {"number": 2, "name": "broken", "bbox": [0.5, 0.5, 0.9, 0.9], "location": "center",
                       "description": "Broken.", "grid": old_grid}]}
    def fake(image_bytes, mime, prompt, thinking):
        if '"broken"' in prompt:
            raise RuntimeError("down")
        return {"grid": OUTLINE}
    old = paintings.ask_gemini
    paintings.ask_gemini = fake
    try:
        paintings.redraw(p)
        saved = json.load(open("cache/zz-redraw.json"))
    finally:
        paintings.ask_gemini = old
        for ext in ("json", "jpg"):
            if os.path.exists(f"cache/zz-redraw.{ext}"):
                os.remove(f"cache/zz-redraw.{ext}")
    assert saved["sections"][0]["grid"] == paintings.fix_grid(OUTLINE)
    assert saved["sections"][1]["grid"] == old_grid  # failed redraw keeps the old grid
    assert saved["guide_notes"] == {"good": "keep me"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_pipeline.py`
Expected: `AttributeError: module 'paintings' has no attribute 'redraw'`

- [ ] **Step 3: Implement**

In `paintings.py`, add before `fetch_painting`:

```python
def draw_all(img, title, sections):
    """A grid (or None) for every section, all drawn at once: load time = the slowest section."""
    crops = [jpeg(crop_square(img, s["bbox"])) for s in sections]
    with ThreadPoolExecutor(len(sections)) as pool:
        return list(pool.map(lambda c, s: draw(c, title, s), crops, sections))

def redraw(p):
    """Draw every section of a cached painting again from its saved image: same parts, new grids.
    A section whose drawing fails keeps its old grid. Guide notes are kept; the ones that describe
    the board must be rewritten by hand afterwards. Saves and returns p."""
    with Image.open(p["image"]) as img:
        grids = draw_all(img, p["title"], p["sections"])
    for s, g in zip(p["sections"], grids):
        if g:
            s["grid"] = g
    save_painting(p)
    return p
```

In `fetch_painting`, replace these four lines:

```python
    img = Image.open(BytesIO(resp.content))
    crops = [jpeg(crop_square(img, s["bbox"])) for s in sections]
    activity("gemini", "working", f"Drawing {len(sections)} shapes in parallel")
    with ThreadPoolExecutor(len(sections)) as pool:  # all drawings at once: load time = slowest one
        grids = list(pool.map(lambda c, s: draw(c, wiki["title"], s), crops, sections))
```

with:

```python
    activity("gemini", "working", f"Drawing {len(sections)} shapes in parallel")
    grids = draw_all(Image.open(BytesIO(resp.content)), wiki["title"], sections)
```

In `prepare_demo.py`, change the import to `from paintings import load_painting, save_painting, redraw`. Then insert right after the `if not p: ... continue` block:

```python
    if "--redraw" in sys.argv:  # new grids from the saved image; then rewrite the board half of guide_notes by hand
        redraw(p)
        for s in p["sections"]:
            print(f"\n{p['title']} {s['number']}. {s['name']}")
            print("\n".join("".join("#" if v else "." for v in row) for row in s["grid"]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python test_pipeline.py`
Expected: all `ok`. `test_fetch_painting` still passes because it goes through `draw_all` now.

- [ ] **Step 5: Commit**

```bash
git add paintings.py prepare_demo.py test_pipeline.py
git commit -m "paintings.py, prepare_demo.py: redraw cached paintings with --redraw, keep notes and facts"
```

---

### Task 5: Redraw and curate the four demo paintings (D)

Live: needs `GEMINI_API_KEY` in `.env`. About 4 paintings × ~4 sections × 4 calls ≈ 65 Gemini calls. It does not call Creao: `guide_notes` already exist, so `prepare_demo.py` skips it. It also does not call Browser Use: `museum_facts` already exist.

**Files:**
- Modify: `cache/mona-lisa.json`, `cache/the-starry-night.json`, `cache/the-great-wave-off-kanagawa.json`, `cache/girl-with-a-pearl-earring.json`
- Test: `test_pipeline.py` (`test_demo_cache_is_valid`)

- [ ] **Step 1: Write the failing regression check**

In `test_demo_cache_is_valid`, add this line right after `assert any(map(any, s["grid"])), (path, s["name"])`:

```python
            assert not paintings.grid_problems(s["grid"]), (path, s["name"], paintings.grid_problems(s["grid"]))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python test_pipeline.py`
Expected: AssertionError naming one of the 7 blob sections, e.g. `('cache/girl-with-a-pearl-earring.json', 'her face', ['solid block'])`

- [ ] **Step 3: Redraw**

Run: `python prepare_demo.py --redraw`
Expected: each painting prints every section's new grid, then `<title> done: N facts, M notes`.

- [ ] **Step 4: Review every grid by hand**

Open `python screen.py --demo` (http://127.0.0.1:8000) or read the printed grids next to `cache/*.jpg`. For each section, ask: "Told only the section name, would someone feeling this recognize it?" Mona Lisa "her eyes" should now show two large eyes filling the board, with no nose or brows. If a grid is still bad, either rerun `python prepare_demo.py --redraw` (drafts vary from run to run) or hand-edit that section's `grid` in the JSON (10 rows of 10, 0/1). Every grid must pass `grid_problems`.

- [ ] **Step 5: Rewrite the board half of each guide note**

For every section in each painting's `guide_notes`, rewrite the sentences that describe the balls so they match the new grid. Use 1-2 sentences in the `d69dfa1` style, e.g. "The two short lines across the top mark her brow...". Keep the final fact sentence as it is. Plain text, no markdown, no `*`. The notes are read aloud.

- [ ] **Step 6: Run all offline tests**

Run: `python test_pipeline.py && python test_main.py && python test_screen.py && python test_sponsors.py`
Expected: all `ok`. `test_demo_paintings_load_without_network` still passes.

- [ ] **Step 7: Commit**

```bash
git add cache/ test_pipeline.py
git commit -m "cache: redraw the demo paintings' grids, rewrite board notes to match, check grids in tests"
```

---

### Task 6: Live check of a new painting's load time

**Files:** none changed unless the timing is too slow (see Step 3).

- [ ] **Step 1: Run the live test**

Run: `python test_paintings.py`
Expected: passes (Mona Lisa still loads from cache in < 0.1 s).

- [ ] **Step 2: Time an uncached painting, then remove it**

```bash
python -c "import time, paintings; t = time.time(); p = paintings.load_painting('The Scream'); print(round(time.time() - t, 1), 's'); [print(s['name']) or print('\n'.join(''.join('#' if v else '.' for v in r) for r in s['grid'])) for s in p['sections']]"
rm -f cache/the-scream.json cache/the-scream.jpg
```

Expected: the grids are outlines, not blobs. Note the time. Before this change it was 1 analyze call plus 1 draw round; now it is 1 analyze call, 1 draft round and 1 judge round. Delete the cached file so `test_demo_cache_is_valid` doesn't check a painting nobody curated.

- [ ] **Step 3: Only if the load took longer than 40 s**

Set `DRAFTS = 2` in `paintings.py`, rerun `python test_pipeline.py` and Step 2, then commit:

```bash
git add paintings.py
git commit -m "paintings.py: two drafts per section to keep live lookups fast"
```

- [ ] **Step 4: Hand off**

Push `feat/better-grids` and open a PR to `main`. Tell Austin, who owns `paintings.py` and `cache/`, before merging. Merge before the 10:00 AM feature freeze on 2026-10-18.
