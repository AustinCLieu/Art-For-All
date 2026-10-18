# What happened to each review item

All fixes are on the `code-review` branch. Offline tests: `test_main.py` 12, `test_pipeline.py` 14,
`test_screen.py` 12, `test_sponsors.py` 7, all passing. Several fixes touch Austin's files (paintings,
creao, museum, prepare_demo, screen, cache, tests) at Harvey's request, so Austin should read this list.

## Fixed

| Batch | Item | Change |
| --- | --- | --- |
| 1 | I-1 one bad cache file breaks every lookup | `save_painting` writes a temp file then `os.replace`; `from_cache` skips unreadable files (tested) |
| 1 | I-2 Gemini has no timeout | `HttpOptions(timeout=45_000)` (ms) |
| 1 | I-4 "girl with the pearl earring" misses the cache | `core()` drops a/an/the anywhere (tested) |
| 1 | M5-M10 | empty name returns None; `box_2d` clamped; one-string grid split; deep copy on save; image download `raise_for_status`; page key URL-encoded |
| 1 | M11, M12 | `test_paintings.py` asserts its defaults; `test_pipeline.py` loads the demo paintings with the network forbidden, checks the cache schema and all 9 locations |
| 2 | I-1 guide notes describe a relief | All 15 notes rewritten to 2-3 sentences: where the shape is on the board (checked against each grid) plus one fact kept from the Creao note. Creao prompt in `docs/austin.md` updated: **paste it into the agent at agent.creao.ai** |
| 2 | I-2 duplicate paid runs | lock-guarded set of titles in progress in `creao.py` and `museum.py` (tested) |
| 2 | I-3 Browser Use waits up to 30 min | one 300 s deadline, cancel on `TimeoutError` (tested) |
| 2 | I-4 Creao key sent to any host | `Authorization` only for `creao.ai` hosts (tested) |
| 2 | M-1, M-2, M-3, M-5, M-6, M-8 | notes matched ignoring case then by order; needs both Creao env vars; facts must be strings; markdown removed and "no markdown" in the task; Starry Night names lowercased, Mona Lisa section 1 is "her figure"; `prepare_demo.py` skips cached facts unless `--refresh` |
| 3 | #1 silent stub fallback | falls back only when `paintings.py` / `board.py` themselves are missing; prints which loaded (tested) |
| 3 | #2 tests can start paid runs | `fresh_main` stubs `start_museum_facts` |
| 3 | #3 board failure ends the voice tour | `show_grid` errors go to Sentry, the agent still gets the words (tested) |
| 3 | #4, #5, #8, #10 | second Ctrl+C kills; lock around the tool bodies; "2.0" / "section 2" accepted; SIGINT handler before `start_session` |
| 4 | I-1 unpinned SDK | `requirements.txt` pinned (with batch 6 I-1) |
| 4 | M-1, M-2, M-3, M-4, M-7 | snapshot error printed once; "working" chip at thread start; failed save no longer reports failed facts; demo stays up and takes `--port`; painting images cacheable |
| 5 | I-1 720p overflow | measured in Chrome: 22 px spill at 1280x720 and 3 px at 1366x768 before; fits now (`max-height: 800px` rule) |
| 5 | M-1 to M-6 | scroll on `[lines]`; 2 s fetch timeout; grid normalized to 10x10; broken image hidden; `aria-hidden="true"`; `dist/` rebuilt |
| 6 | I-1 to I-5, M-2 to M-8 | pins + `pyserial`; owners; Gemini call count; README layout, tests, `cp .env.example .env`; `.env.example` comments; contract edge replies; stale comments; `.DS_Store` |

## Not changed, and why

- **1 I-3 (regenerate three demo paintings with detailed sections):** needs live Gemini and Creao runs
  and a person checking the grids. Team decision.
- **1 M-13 (`cache/*_check.png` not ignored):** it already is (`.gitignore` line 4).
- **1 M-14 (absolute `CACHE` path):** would write absolute `image` paths into new cache files, against
  the contract (`"image": "cache/mona-lisa.jpg"`). `CLAUDE.md` says to run from the repo root.
- **3 #7 (send `museum_facts` only with section 1):** changes the client-tool contract; needs the team.
- **2 M-4 (cancel a timed-out Creao run):** no known cancel endpoint; the run ID is already printed.
- **2 M-7 (`museum.py` imports `parse_json` from `creao.py`):** both are Austin's and have no extra
  dependencies; not worth a copy.
- **4 M-5, M-6:** informational / fine for a single demo run.
- **5 M-3 error boundary:** the grid normalization removes the known way to crash the render.
- **6 M-1 README TODOs (track, domain, team):** need the team's answers before Devpost.
- **Teammate 3:** `board.py` must use `pyserial` (now in requirements). If it fails to import,
  `main.py` now stops with the error instead of silently using the print-only board.
