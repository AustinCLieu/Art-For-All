# Review: Batch 6, contract, docs and setup consistency (HEAD 9612a6e)

Scope: `CLAUDE.md`, `README.md`, `.env.example`, `requirements.txt`, `.gitignore`, checked against
`main.py`, `stubs.py`, `paintings.py`, `creao.py`, `museum.py`, `prepare_demo.py`, `screen.py`,
`check.py`, the test files, `screen/package.json` and the `cache/` files.

What I checked: I grepped every env var and third-party import. I ran `git check-ignore -v` and
`git ls-files`. I went through the full history of `.env` and scanned all of history for key-shaped
secrets. I looked at the bytes of every version of `README.md`. I ran `python test_main.py` and
`python test_pipeline.py` in the worktree with Browser Use and Creao keys unset (all tests pass,
nothing left behind).

### Strengths
- **No secrets leaked.** `.env` was committed in b404eaa and removed in fcc59d3, but both times it
  was the empty blob (`e69de29`). Scanning all of history for Gemini/ElevenLabs/Browser Use/Sentry
  key patterns found nothing.
- **Env vars match in every direction.** `.env.example`, CLAUDE.md:61-62 and README:127-129 list the
  same 9 vars. Every var the code reads is listed: `AGENT_ID`, `ELEVENLABS_API_KEY`, `SENTRY_DSN`
  (main.py), `CREAO_API_KEY`, `CREAO_AGENT_ID` (creao.py, prepare_demo.py), `BROWSER_USE_API_KEY`
  (museum.py and the SDK), `GEMINI_API_KEY` (read by `genai.Client()` itself) and `BOARD` (screen.py).
  `SERIAL_PORT` is only for the board.py that hasn't landed yet. That is expected.
- **Every third-party import is in `requirements.txt`, and nothing there is unused**: requests,
  google-genai, python-dotenv, pillow, browser-use-sdk, elevenlabs[pyaudio], sentry-sdk.
- **`.gitignore` is correct.** `.env`, `.venv/`, `__pycache__/`, `screen/node_modules/` and
  `cache/*_check.png` are ignored. The 4 demo JSONs and JPGs and `screen/dist/` are tracked and not
  ignored.
- **README encoding is fine now.** fbef3d5 was UTF-16LE with a BOM (`ff fe`), which is why git showed
  "Bin". Since fd95a86 it is plain UTF-8 with no BOM, NULs or CRs, so it renders correctly on GitHub
  and Devpost.
- **The contract matches the code.** The `open_painting` / `show_section` response keys match
  main.py:43-60 (test_main.py asserts the exact key set). The cache JSON key sets in all 4 files match
  the schema. `location` follows the 3x3 rule (paintings.py:143-147). `save_painting` writes
  `cache/<slug>.json`.
- **Commands and filenames are right.** `screen.py --demo`, `test_pipeline.py`, `test_screen.py`,
  the npm `build` script and port 8000 all exist as documented.
- The README is well written for judges: a clear problem statement, honest timings, and a section per
  sponsor with links to the code.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)
1. **`requirements.txt:1-7`: nothing is pinned.** The code relies on APIs that change between SDK
   versions: `browser_use_sdk.v4` (museum.py:3) and the ElevenLabs `Conversation(...,
   callback_agent_response_correction=...)` signature with `ClientTools.handle` (main.py:113-122,
   test_main.py:91). A fresh `pip install` the night before or on a judge's machine could pull a
   breaking release. Fix: pin what is known to work in the team venv: `requests==2.34.2`,
   `google-genai==2.31.0`, `python-dotenv==1.2.4`, `pillow==13.0.0`, `browser-use-sdk==3.12.1`,
   `elevenlabs[pyaudio]==2.73.1`, `sentry-sdk==2.72.0`.
2. **`CLAUDE.md:11` (ownership list) leaves out `museum.py` and `test_pipeline.py`.** Both exist and
   both are Austin's (the README credits museum.py). The rule says "only edit your own files", so
   unlisted files have no owner. Fix: add `museum.py` and `test_pipeline.py` to Austin's line.
3. **"One Gemini call" is wrong in CLAUDE.md:12, README.md:68 and README.md:110.** paintings.py
   makes 1 + N calls: `analyze()` (paintings.py:104-109) and then `draw()` for each section in
   parallel (paintings.py:111-121, 194-196), so up to 11 calls. A judge reading the code will notice.
   Fix: "two Gemini steps: one call picks the parts, then one call per part draws its 10x10 pattern
   in parallel".
4. **The future `board.py` will collide with main.py's silent fallback.** `main.py:14-17` falls back
   to the print-only stub on *any* `ImportError`. board.py will need `pyserial`, which is not in
   `requirements.txt`. So with `BOARD=serial`, a missing `pyserial` (or any import bug in board.py)
   makes the demo silently print to the terminal with no balls moving. screen.py:83 also reports
   `"hardware": true` from `BOARD` alone, whether or not board.py loaded. Fix: add `pyserial` to
   `requirements.txt` when board.py lands, and have main.py print which board it loaded, for example
   `print("Board:", show_grid.__module__)`.
5. **README.md:133 calls `test_main.py` "offline", but it can start a real Browser Use run.**
   `fresh_main()` in test_main.py:33-40 stubs `start_tour_writer` but not `start_museum_facts`. The
   stub Mona Lisa has no `museum_facts`, and main.py loads `.env`. So with `BROWSER_USE_API_KEY` set,
   `open_painting` starts a paid background run. If that run ever finished, `save_painting` would
   overwrite `cache/mona-lisa.json` with the 3-section stub. test_screen.py:139 already does it right.
   Fix (Harvey's file): add `main.start_museum_facts = lambda p: None` in test_main.py's `fresh_main`.

#### Minor (Nice to Have)
1. **README.md:7, 78, 146 still have TODOs** (main track, domain, team). These must be filled in
   before the Devpost submission.
2. **The README repository layout is out of date.** README.md:117 leaves out `test_pipeline.py` and
   `test_screen.py`, and README.md:114 leaves out `sim.py`, which CLAUDE.md:14 lists.
3. **README.md:123 says "create .env with the keys below".** Use `cp .env.example .env` and fill it
   in instead, so nobody mistypes a var name.
4. **`.env.example` has no comments.** One line each would help a new teammate: `CREAO_API_KEY` is
   the agent's `capi_` key, `BOARD=serial` needs `SERIAL_PORT` (e.g. `/dev/tty.usbmodem*`), and
   `SENTRY_DSN` is optional.
5. **The contract (CLAUDE.md:30-35) leaves out `show_section`'s edge replies:**
   `{now_showing: "That was the last section."}`, `{now_showing: "This is already the first
   section."}` and `{error: ...}` (main.py:63-80). The ElevenLabs agent prompt should expect these.
6. **The comment at `main.py:47` is stale.** It says "from Creao, demo paintings only", but
   creao.py:68-78 and README.md:51 say Creao runs for any painting without notes.
7. **`.gitignore` has no `.DS_Store`.** None is tracked yet, but on macOS one easily gets committed
   with `git add .`.
8. **`main.py:1` header comment** lists only 5 env vars. This is harmless, but it drifts from CLAUDE.md.

### Recommendations
- Before the freeze: pin `requirements.txt` (Important 1) and fix the one-line test_main.py stub
  (Important 5). Both are quick and lower the risk of something going wrong on stage.
- Fix the docs in one commit: museum.py/test_pipeline.py ownership, the Gemini call count, and the
  README layout table.
- Tell Teammate 3 that board.py must add `pyserial` to requirements.txt. A startup line saying which
  board is active makes a silent fallback easy to spot during setup.

### Assessment
**Ready to merge?** With fixes
**Reasoning:** No secrets leaked, the env vars, imports, ignore rules, encoding and contract all
match the code, and the offline tests pass. The issues are unpinned dependencies, a few inaccurate
doc statements (ownership, Gemini call count, "offline" test), and a silent-fallback risk for when
board.py lands. None of these block the demo today.
