# Review: Batch 4, audience screen backend (screen.py, test_screen.py, hooks in b46eac6 / eac90d1)

Verified by: reading screen.py, test_screen.py, the hook diffs, main.py/creao.py/museum.py around the hooks,
screen/src/types.ts and useScreenState.ts, the plan; running `python test_screen.py` (all 11 PASS, macOS,
SDK elevenlabs 2.73.1); probing start_screen against a busy wildcard port and a malformed painting.

### Strengths
- The "tour never depends on the screen" rule is actually enforced, not just claimed: every public function
  (`say`, `correct`, `show_on_screen`, `activity`, `snapshot`, `start_screen`) has its own try/except; every
  importer uses `try/except Exception` with a no-op fallback; and both are tested (`test_never_raises`,
  `test_broken_screen_keeps_the_tour` with `_lock = None`, `test_main_without_screen_file` in a subprocess
  with `sys.modules['screen'] = None`).
- Lock is only held for in-memory copies; `json.dumps` and all socket I/O happen outside it. Request handlers
  run in daemon threads (`daemon_threads = True`), so a slow or dead browser tab cannot stall the tour.
- Bound to `127.0.0.1` only. Path handling is sound: `/cache/` uses `basename` plus an image-extension
  whitelist (no `.json`, no `.env`); app files go through `realpath` + `startswith(dist + os.sep)`; both
  traversal cases are tested.
- Port busy -> `Audience screen off: ...` and `None` (tested). Missing `screen/dist/` -> 503 with a build hint.
- Bounded state: transcript capped at 50 lines; activity keyed by (source, title) so it is bounded by the
  number of paintings opened; `detail` truncated to 120 chars.
- `snapshot()` output matches `screen/src/types.ts` exactly (hardware, transcript[{role,text}],
  painting{title,artist,year,image,sections[{number,name,location}]}, section{index,number,name,location,
  bbox,grid,frame}, activity{elevenlabs,gemini,creao,browser_use}{status,detail}).
- `callback_agent_response_correction` exists in the installed SDK with the `(original, corrected)` signature
  that `screen.correct` takes. `show_on_screen` is called after `show_grid`, so a serial failure never shows a
  frame the board did not raise.
- Hooks are small and additive, as the plan required; `test_main.py` contract untouched.

### Issues

#### Critical (Must Fix)
None found.

#### Important (Should Fix)
1. `requirements.txt:6` (`elevenlabs[pyaudio]`, unpinned) + `main.py` `callback_agent_response_correction=correct`.
   This is the one screen hook that runs outside a try/except: it is a constructor keyword argument. The plan
   pins its reasoning to SDK 2.73.1, but a fresh `pip install` on another laptop (Austin's Windows machine or
   a re-created venv) gets whatever is latest; if a release renames or drops that kwarg, `Conversation(...)`
   raises `TypeError` and the demo does not start at all. Low probability, total impact, trivial fix: pin
   `elevenlabs[pyaudio]==2.73.1` (the version tested). Not strictly a screen.py bug, but it is the screen's
   only path to breaking the tour.

#### Minor (Nice to Have)
1. `screen.py:96-97` `snapshot()` prints `screen.snapshot failed: ...` on every poll (every 300 ms per open tab)
   if the live painting is malformed (verified: a section without `bbox` gives `KeyError('bbox')` repeatedly).
   That would flood the terminal the operator is watching for `Agent:`/`User:` lines. Real paintings from
   `paintings.py` and the four cached ones all have every key (checked), so this is unlikely. Fix: remember the
   last error string and only print when it changes, or use `s.get(...)` in `_views`.
2. `creao.py:45` and `museum.py:21`: the `working` status is reported only after the run is created (Creao
   POST can take up to 30 s), so the chip sits at `idle` during that time. Moving the `activity(... "working",
   "Starting ...")` call to the top of `safe()` makes the sponsor activity visible immediately.
3. `museum.py` `start_museum_facts.safe`: `p["museum_facts"]` is set before `save_painting(p)`; if the save
   raises, the chip says `failed` ("No museum facts this time") although the tour has the facts. Cosmetic.
4. `screen.py:163-180` demo: when the loop ends the process exits and the page goes "offline" immediately.
   For rehearsing in front of judges it is nicer to keep serving (e.g. loop forever or wait for Ctrl+C after
   "Demo finished."). Demo also exits silently-ish (only the "Audience screen off" line) if 8000 is busy;
   a `--port` option would help when main.py is already running.
5. `screen.py:146` `allow_reuse_address` on macOS: verified that start_screen succeeds on a port where another
   process listens on `0.0.0.0` (BSD lets the more specific 127.0.0.1 bind win). Harmless (the page still
   works on localhost), but `test_port_in_use` only covers the same-address case; the docstring "returns None
   if it can't start" isn't the whole story. Informational.
6. `screen.py:89-90` the ElevenLabs chip turns `done / In conversation` on the first transcript line and never
   goes back, even after the session ends. Fine for a single demo run.
7. `screen.py:140` `Cache-Control: no-store` also applies to the 1-1.5 MB painting JPEGs; React keeps the same
   `<img>` so it is fetched once per painting today, but a cacheable header for `/cache/` would be safer if the
   component ever remounts.

### Recommendations
- Pin the ElevenLabs SDK version before the feature freeze (Important 1); it costs nothing.
- Optionally dedupe the snapshot error print (Minor 1) since the terminal is the operator's main view.
- Everything else can wait until after the demo.

### Assessment
**Ready to merge?** With fixes
**Reasoning:** The screen cannot raise, block or slow down the tour through any code path in screen.py, and that
is well tested; the only real risk is the unpinned SDK making the new constructor kwarg fail on a fresh install,
which is a one-line pin.
