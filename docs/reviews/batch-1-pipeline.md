# Review: Batch 1, painting pipeline

Scope: `paintings.py`, `test_pipeline.py`, `test_paintings.py`, `check.py` at 9612a6e.
Checked against `CLAUDE.md` (Contract, Rules), `docs/austin.md` and
`docs/superpowers/plans/2026-10-17-detailed-tactile-sections.md`.

What I ran:
- `python test_pipeline.py`: all 7 tests pass and leave no stray `cache/zz-test-painting.*` files.
- A scratch script that replaced `http.get`, `ask_gemini` and `genai.Client` with functions that raise,
  then called `load_painting` on demo-name variants. It also checked every cached JSON: slug matches the
  filename, the image exists, `number` runs 1..n, every grid is exactly 10x10 ints in 0/1, bbox is
  ordered and inside [0,1], `location == to_location(bbox)`, no blank grids, and guide notes cover every
  section. All 4 demo files pass. Mona Lisa, Starry Night, Great Wave and Girl with a Pearl Earring
  (plus "mona lisa by leonardo da vinci", "starry night", "the great wave", "Starry Night by Van Gogh")
  load from cache with no network call.
- I did not run `test_paintings.py`, because it makes live Gemini calls.

### Strengths
- **Matches the contract.** `load_painting`/`save_painting` signatures are unchanged. Sections come out
  with exactly `number, name, bbox, location, description, grid`, and the test asserts that key order.
  `to_location` follows the 3x3 rule in `CLAUDE.md`, and `number` is reassigned after dropping sections,
  so the tour has no gaps.
- **Failure paths fail soft, where it counts.** `load_painting` wraps the whole fetch, so a Wikipedia
  stall, a Gemini error or bad JSON returns `None` and the agent says "not found" instead of crashing.
  Bad sections (missing `box_2d`, wrong length, non-numeric) are skipped. Failed or blank drawings are
  dropped. The image file is written only after everything parsed, so failures leave no stray files.
- **Grids can't go malformed.** `fix_grid` always returns 10x10 of 0/1, whether Gemini sends numbers,
  `"1"` or `#`/`.` strings, and whether rows are short, long, missing or extra.
- **`crop_square` is better than the plan's version.** It sorts inverted boxes and sets an 8 px minimum
  side, so degenerate boxes can't produce a zero-size crop. A test covers this.
- **Network hygiene.** A shared `requests.Session` sends the descriptive User-Agent on every Wikimedia
  call, including the image download. Every request has (connect, read) timeouts and a small
  connect-retry.
- **Fast enough.** The per-section drawings run in parallel, so load time is roughly call 1 plus the
  slowest drawing.
- **Offline tests are good.** They fake Gemini and HTTP at the right seams and check real behaviour:
  dropping and renumbering, the bbox conversion from `box_2d` order, thinking levels, mime types, and the
  title appearing in each draw prompt.

### Issues

#### Critical (Must Fix)
None. The four demo paintings load from cache without network, and their data is valid.

#### Important (Should Fix)

1. **One unreadable cache file breaks every painting lookup.** `paintings.py:69-77` (`from_cache`) and
   `paintings.py:64-67` (`save_painting`).
   - What's wrong: `from_cache` runs `json.load` on every `cache/*.json` and reads `p["title"]`, outside
     any try. It also runs before the try in `load_painting` (`paintings.py:150`). Meanwhile
     `save_painting` truncates and rewrites the file in place. The Creao thread (`creao.py:60`) and the
     Browser Use thread (`museum.py:42`) both call it in the background after a live painting opens.
     `_lock` only serializes writers; readers never take it.
   - Why it matters: if `open_painting` runs while a background write is in progress (for example,
     asking for Mona Lisa just as Birth of Venus's museum facts land), `from_cache` reads a half-written
     file and raises `JSONDecodeError`. The client tool then errors. The same happens if a crash ever
     leaves a truncated file, or if any stray `.json` without `title` lands in `cache/`. In those cases
     every lookup fails, the demo paintings included, until the file is fixed.
   - How to fix (two small changes):
     (a) In `save_painting`, write to `path + ".tmp"`, then `os.replace(tmp, path)`. The replace is
     atomic, so a reader sees either the old file or the new one.
     (b) In `from_cache`, wrap each file's load in `try/except Exception: continue`, so one bad file
     is skipped.

2. **The Gemini calls have no timeout.** `paintings.py:96-101`.
   - What's wrong: `genai.Client()` is built without `http_options`. In google-genai 2.31,
     `HttpOptions.timeout` defaults to `None`.
   - Why it matters: `open_painting` is a blocking client tool with "Wait for response" ticked. If one
     of the up-to-11 Gemini calls stalls on hackathon Wi-Fi, `load_painting` never returns, and the live
     "ask for The Birth of Venus" moment hangs. Wikipedia calls are bounded (`T = (5, 30)`); Gemini is
     not.
   - How to fix: `genai.Client(http_options=types.HttpOptions(timeout=45_000))` (milliseconds). A
     timed-out draw is already dropped; a timed-out call 1 already returns `None`.

3. **Plan Task 3 is only partly done: three demo paintings still have the old coarse sections.**
   This is a plan deviation, not a code bug.
   - What's wrong: the plan says to regenerate all four demo paintings with 5-10 detailed sections (for
     example "her face, then eye / lips / pearl earring") and re-run `prepare_demo.py`. Only Mona Lisa
     was regenerated (commit `3d9196f`). The other three still have their old sections:
     - Girl with a Pearl Earring has 4: face, earring, turban, jacket. There are no eye or lip sections.
     - Great Wave has 3.
     - Starry Night has 4.
   - Why it matters: the teammate feedback this plan exists to fix ("you feel the face's circle, not
     the eyes") still applies to three of the four demo paintings. The data is valid, so the demo won't
     break. It just won't show the improvement.
   - How to fix: run plan Task 3 Steps 2-5 for the other three (`test_paintings.py`, then `check.py`,
     then `prepare_demo.py`, so the guide notes match the new section names). Or decide on purpose to
     keep the reviewed old grids and tick the task off with a note. The old Great Wave grids are
     readable, so keeping them is defensible.

4. **Small wording differences send a demo painting to the network.** `paintings.py:59-62, 75`.
   - What's wrong: matching is plain substring matching after stripping "the" and "by ...".
     "girl with the pearl earring" misses the cache (I confirmed it went to the network). So would
     "Van Gogh's The Starry Night" spoken differently, or "Kanagawa wave".
   - Why it matters: online, this still ends at the cached file after a Wikipedia search
     (`paintings.py:170-173`), so it costs about 1-2 s and needs Wi-Fi. Offline, or with Wikipedia
     slow, a demo painting comes back "not found". The rule is "must load instantly from cache".
   - How to fix: in `core`, also drop articles everywhere, e.g.
     `re.sub(r"\b(the|a|an)\b", " ", ...)` and collapse spaces. Optionally, give the ElevenLabs agent
     prompt the four exact titles.

#### Minor (Nice to Have)

5. **The cache match is too loose in other ways.** `paintings.py:75`.
   - An empty name matches the first file in glob order: `load_painting("")` returned Mona Lisa.
   - Longer titles that contain a cached title match it: "Starry Night Over the Rhone" returned The
     Starry Night. Short words do too: "Lisa", "Girl".
   - Glob order is arbitrary, so with more cached paintings, which one wins can vary.
   - For the demo, guard `if not want: return None`. Otherwise this is acceptable.

6. **`to_location` misreads boxes outside the image.** `paintings.py:143-147, 184-185`.
   - What's wrong: `box_2d` values outside 0-1000 aren't clamped. If the center falls below -1/3,
     `int(cy * 3)` is -1, and index -1 is "bottom" or "right": the opposite side.
   - How to fix: clamp each value with `max(0, min(1000, v))` before dividing.

7. **A grid sent as one newline-joined string is silently wrong.** `paintings.py:125`.
   - What's wrong: if Gemini returns `"grid": "...##...\n..."` (a single string), `fix_grid` treats each
     character as a row, so only column 0 is used. The result is valid but meaningless.
   - How to fix: add `if isinstance(grid, str): grid = grid.split()`.

8. **`save_painting` copies only the top level.** `paintings.py:67`.
   - What's wrong: `dict(p)` is a shallow copy. Today it's fine, because `creao.py` and `museum.py`
     replace `guide_notes`/`museum_facts` rather than mutating them.
   - Why it matters: if anything ever mutates those nested values in place while another thread dumps,
     `json.dump` can raise "dictionary changed size during iteration".
   - How to fix: `json.loads(json.dumps(p))` under the lock, or just leave a comment.

9. **The image is always saved as `.jpg`.** `paintings.py:180, 201-202`.
   - What's wrong: the file gets a `.jpg` name even when Wikimedia served PNG (or WebP) bytes.
   - Why it matters: Pillow and browsers sniff the content, so it works, but the name lies. The image
     download also doesn't call `raise_for_status()`. An HTML 403/429 page is caught later (Gemini or
     Pillow fails, and the result is `None`), so this costs a wasted Gemini call, not a crash.

10. **The Wikipedia page key isn't URL-encoded.** `paintings.py:85`.
    - What's wrong: the key is pasted into the summary URL path as-is. Titles containing `?`, `#` or `/`
      (for example Gauguin's "Where Do We Come From? ...") break the summary request.
    - How to fix: use `requests.utils.quote(key, safe="")`.

11. **`test_paintings.py` has no asserts.** `test_paintings.py:7-18`.
    - What's wrong: the brief's checks ("asdfgh returns None", aliases hit the cache) are printed, not
      asserted, so a regression is easy to miss.
    - How to fix: assert the three default cases, and assert that the alias load takes under 0.1 s.

12. **The offline tests miss the code that most affects the demo.** `test_pipeline.py`.
    - What's missing: no test covers `load_painting` cache hits without network, `from_cache` aliasing,
      `load_painting` returning `None` when `fetch_painting` raises, all 9 `to_location` cells, or
      `analyze`'s list unwrapping.
    - How to fix: one cheap test, in the style of the scratch script above. Patch `http.get` and
      `ask_gemini` to raise, then assert all four demo titles load. That is the main guard for the
      "instant from cache" rule.
    - Also, `import os` sits mid-file (`test_pipeline.py:34`), and the duplicated fake-HTTP setup could
      share a helper.

13. **`check.py` has small rough edges.** `check.py:13-14`.
    - `font_size=` needs Pillow 10.1 or newer, but `requirements.txt` doesn't pin a version.
    - The script writes `*_check.png` files into `cache/`, where they could be committed by accident.
      Add `cache/*_check.png` to `.gitignore`.

14. **Cache paths depend on the working directory.** `paintings.py:16`.
    - What's wrong: `CACHE = "cache"` and the stored `image` path are relative to wherever Python is
      started. Run from another directory, the cache misses and a new empty `cache/` is created there.
    - Why it's minor: `CLAUDE.md` says to run from the repo root.
    - How to fix: anchor on `os.path.dirname(__file__)` for robustness.

### Recommendations
- Before the feature freeze, do Important #1 (atomic write plus a tolerant `from_cache`) and #2 (the
  Gemini timeout). They are about 6 lines together, and they remove the two ways the live demo can hang
  or crash.
- Do #4 (article-insensitive `core`) and the empty-name guard from #5. Then add the network-forbidden
  cache test from #12 so it stays fixed.
- Decide explicitly on #3: regenerate the other three demo paintings tonight, or mark Task 3 as
  intentionally limited to Mona Lisa.
- The rest can wait until after the hackathon.
- One note on the plan itself: it has no step to time a live (uncached) load against the ElevenLabs
  tool timeout, only "if any took more than about 20 s". Measure the Birth of Venus load once and keep
  it under about 20 s, using `thinking="low"` in `draw` if needed.

### Assessment
**Ready to merge?** With fixes

**Reasoning:** The pipeline matches the contract, and the four demo paintings load valid data from
cache with no network. But a concurrent background save can crash every lookup (#1), and an unbounded
Gemini call can hang the live uncached demo (#2). Both are small, local fixes that should go in before
the freeze.
