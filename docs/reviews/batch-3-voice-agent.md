# Review: Batch 3, voice agent (`main.py`, `stubs.py`, `test_main.py`)

Scope: `git diff 4b825dc 9612a6e -- main.py stubs.py test_main.py`. Checked against `CLAUDE.md` (Contract, Rules),
`docs/harvey.md`, `docs/superpowers/plans/2026-10-17-main-with-stubs.md` and `2026-10-17-quick-prizes.md`.
Also checked against the installed SDKs (`elevenlabs` 2.73.1 `conversation.py`, `sentry-sdk` 2.72.0).
`python test_main.py` was run with the API keys blanked: 10/10 PASS. I probed the edge cases offline against
the real cache. No live conversation and no paid calls were made.

### Strengths
- **The tool response shapes match the contract.** `open_painting` returns exactly `found, title, artist, year, summary, sections[{number,name,location}], now_showing, description, shape, guide_notes, museum_facts`. A normal `show_section` returns exactly `now_showing, description, shape, guide_notes, museum_facts`. A test pins both (`test_main.py:56`, `:69`). No grids or bboxes reach the LLM.
- **`as_tool` (`main.py:83-92`) fixes two real SDK problems.** First, it JSON-encodes the result, because ElevenLabs rejects a non-string result. Second, it reports to Sentry and then re-raises. The SDK (`conversation.py:319-325`) turns a raised exception into `is_error` without logging it. Re-raising keeps that path, so the agent can still say something went wrong. Both behaviours have tests (`test_main.py:85-115`).
- **The edge cases are handled and tested.**
  - `previous` at section 1 and `next` at the last section give short spoken sentences.
  - Out-of-range numbers are clamped (`"99"` goes to the last section, `"0"` and `"-1"` go to the first).
  - Non-numeric input returns a short error.
  - `show_section` before any painting is open returns a short error.
  - A missing `section` key is handled (`params.get`).
  - Opening a painting resets the tour to section 1.
- **The board call does not block the conversation.** Sync client tools run on `ClientTools.thread_pool` through `run_in_executor` (`conversation.py:297`), so a slow `show_grid` doesn't stall the websocket or the audio threads.
- **The screen is properly optional.** It is imported under `except Exception`, and every `screen.*` function catches its own errors. That matters because an exception in an ElevenLabs callback ends the conversation. `callback_agent_response_correction` matches the SDK signature `(str, str)`. `screen.py` beats the `screen/` directory on import because `screen/` has no `__init__.py`. I verified this: `main.say.__module__ == "screen"`.
- **Sentry with no `SENTRY_DSN`** gives `sentry_sdk.init(dsn=None)`, which is a no-op. The tour runs the same either way.
- **The plan was followed closely.** The deviations from the reference `main.py` are the ones the later plans called for: `as_tool` (quick-prizes), the screen hooks and the `__main__` guard (audience-screen), and `start_museum_facts`. The stub Mona Lisa satisfies the painting schema, and `test_stub_painting` checks the grid shape, the 0/1 values and that each location is one of the 9 allowed cells.
- **Responses are short.** About 2.6 KB for `open_painting` on The Starry Night and about 1.6 KB for `show_section`.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)

1. **The stub fallback hides real import failures inside the real modules.** This is the biggest demo risk in this batch.
   - **Where:** `main.py:10-17` (and `:18-27`).
   - **What's wrong:** `except ImportError` also catches a `ModuleNotFoundError` for a dependency *inside* `paintings.py` or `board.py`, and nothing gets printed.
   - **How I checked:** I ran `sys.modules['google.genai'] = None` and then `import main`. The result was `load_painting from: stubs`, and `start_tour_writer` and `start_museum_facts` were both silently replaced by the no-ops, because `creao` and `museum` import `paintings`. After that, `load_painting('The Starry Night')` returned `None`, so the agent would say "I couldn't find that painting" for a cached demo painting.
   - **The board will hit this.** `plan.md:157` shows `board.py` doing `import serial`, and `pyserial` is **not in `requirements.txt`**. On a fresh venv, the real board would silently become the print-only stub. Voice works, nothing rises, and the terminal gives no clue why.
   - **Why it matters:** this fails silently on stage, or it costs debugging time at rehearsal.
   - **Fix:** fall back only when the module itself is missing, and print which one is in use. For example:
     ```python
     try:
         from board import show_grid, to_ascii
     except ModuleNotFoundError as e:
         if e.name != "board": raise
         from stubs import show_grid, to_ascii
         print("board.py not found: using the print-only stub board")
     ```
     Do the same for `paintings`, `creao` and `museum`. Also tell Teammate 3 to add `pyserial` to `requirements.txt`, which is Austin's or the team's file.

2. **`test_main.py` can start real, paid Browser Use runs and hit the real cache.**
   - **Where:** `test_main.py:33-40`.
   - **What's wrong:** `fresh_main()` stubs `start_tour_writer` but not `start_museum_facts`. The stub Mona Lisa has no `museum_facts`, so whenever `.env` has `BROWSER_USE_API_KEY`, each `open_painting` call starts a Browser Use run on a daemon thread. Four tests call it.
   - **Why it matters:**
     - Each call can create a billed run.
     - If a run ever finished, `save_painting(stub)` would overwrite `cache/mona-lisa.json` (the real 5-section demo painting) with the 3-section stub.
     - The background thread also mutates the module-level `stubs.MONA_LISA` dict.
     - This breaks the rule in the file's own header: "no audio, no network".
   - **Fix:** add `main.start_museum_facts = lambda p: None` to `fresh_main()`. Optionally also add `main.show_on_screen = lambda *a: None`.

3. **A board failure ends the voice tour instead of only the touch part.**
   - **Where:** `main.py:39-41`.
   - **What's wrong:** if `show_grid` raises (serial unplugged, no `OK`, port busy), the whole tool call errors. The agent gets `is_error` with no description or shape, so it cannot keep guiding by voice. In addition, `state["index"]` has already advanced (line 39 runs before line 40), so the agent and the board disagree about which part is up.
   - **Why it matters:** the board is the most fragile part of the live demo.
   - **Fix:** wrap only the board call:
     ```python
     try: show_grid(s["grid"])
     except Exception as e: sentry_sdk.capture_exception(e); print(f"Board failed: {e!r}")
     ```
     Then still return the payload. Sentry still gets the error, which keeps the "catches any tool error" goal.

#### Minor (Nice to Have)

4. **A hung board blocks Ctrl+C, and you can't press it again to get out** (`main.py:124-125`).
   - The SIGINT handler only calls `end_session()`. `ClientTools.stop()` calls `thread_pool.shutdown(wait=False)`, but at interpreter exit `concurrent.futures` joins its worker threads.
   - So if `show_grid` is stuck in a serial read with no timeout, the process won't exit. A second Ctrl+C just calls `end_session()` again, and the only way out is Ctrl+\.
   - Fix: inside the handler, restore the default with `signal.signal(signal.SIGINT, signal.SIG_DFL)` so a second Ctrl+C kills the process. Also ask Teammate 3 for a serial read timeout. Optionally send `Z` on exit so the balls drop.

5. **No lock around the shared tour state** (`main.py:34`, `:62-81`).
   - The SDK's `ThreadPoolExecutor` can run two tool calls at once, for example when the user interrupts during a slow uncached `open_painting`.
   - Then `state["index"]` read-modify-write can race, and two `show_grid` calls could interleave on the serial port.
   - This is unlikely with "Wait for response" ticked. A single `threading.Lock` around the body of each tool would close it.

6. **Uncached paintings can start a duplicate Browser Use run** (`main.py:57`).
   - `paintings.from_cache` returns a fresh dict on each call, and Browser Use only writes `museum_facts` to the cache when it finishes.
   - So re-opening the same uncached painting within those minutes starts another paid run.
   - All 4 demo paintings already have facts cached, so the demo is not affected.

7. **`museum_facts` is repeated in full in every section payload** (`main.py:48`).
   - This follows the contract, but it is about 450-800 characters per call and is most of each response.
   - It nudges the LLM to repeat the same facts at every section, which works against "keep them short".
   - Fix: only include it in the first section's payload. That is a contract change, so tell the team first, or leave it as is.

8. **Some section inputs aren't accepted.**
   - Where: `main.py:78`.
   - What happens: `"2.0"`, `"section 2"` and `"two"` all return the error. The agent will usually retry with a plain digit, so this only costs a turn.
   - Fix: parse with `re.search(r"\d+", want)`.

9. **Some responses fall outside the contract.**
   - The boundary responses and the error responses (`{"now_showing": ...}` alone, and `{"error": ...}`) don't have the documented `show_section` shape.
   - They come straight from the reference code and read well aloud, so I would keep them. Consider adding a line to the contract so other consumers, such as the screen, don't assume every key is present.

10. **The order of startup calls is fragile** (`main.py:123-124`).
    - `start_session()` runs before the SIGINT handler is installed. Ctrl+C in that window raises a normal `KeyboardInterrupt` after the websocket thread has started.
    - Harmless in practice. Install the handler first.

### Recommendations
- **Before the freeze:** fix #1 (narrow the fallback, print which implementation is active, add `pyserial` to requirements), #2 (one line in `fresh_main`) and #3 (keep talking when the board fails). Each is a few lines and removes a silent or stage-visible failure.
- **At rehearsal, confirm the startup log names the real modules.** With #1 fixed, it should print nothing about stubs. Then Ctrl+C with the real board attached and check that the process exits.
- **Plan note:** the reference `main.py` in `docs/harvey.md` uses the same broad `except ImportError` pattern, so the issue started in the plan. Worth fixing there too, so later copies don't reintroduce it.

### Assessment
**Ready to merge?** With fixes

**Reasoning:** The tool shapes, navigation edge cases, JSON encoding, Sentry reporting and the optional screen are correct, tested and match the plan. Still, fix the silent stub fallback (#1), which will hide a missing `pyserial` or Gemini dependency, and the test that can start paid Browser Use runs (#2) before the demo, ideally with #3 as well.
