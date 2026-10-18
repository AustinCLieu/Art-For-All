# ArtForAll (LA Hacks AI Hackathon)

Blind users explore famous paintings by voice and touch. An ElevenLabs voice agent leads a guided
tour of a painting, part by part. A 10x10 board of balls raises the shape of the part being discussed.
Goal: the simplest thing that works for the demo. Don't add features that aren't in these docs.

## Files and owners (only edit your own files)
- `main.py`, `stubs.py`, `test_main.py` - Harvey. ElevenLabs conversation + the two client tools; `stubs.py`
  is a fake Mona Lisa + print-only board that `main.py` falls back to until the real parts import.
  Brief: `docs/harvey.md`
- `paintings.py`, `creao.py`, `museum.py`, `prepare_demo.py`, `relief.py`, `test_paintings.py`, `test_pipeline.py`,
  `test_sponsors.py`, `check.py`, `cache/` - Austin. Painting lookup (Wikipedia + Gemini + cache: one
  call picks the parts, then one call per part draws its pattern, in parallel), the live Creao tour
  writer, live Browser Use museum facts, the one-time Browser Use / Creao script, and the 100x100
  heightmaps for the screen's 10,000-pin simulation (`docs/relief.md`). Brief: `docs/austin.md`
- `board.py`, `test_board.py` - Austin. G-code over USB to the board's Marlin firmware.
  Brief (hardware, firmware, calibration, rules): `docs/board.md`
- `screen.py`, `screen/`, `test_screen.py` - Austin. Optional audience screen at http://127.0.0.1:8000:
  the conversation, the board (mirrored or simulated) and what each sponsor's agent is doing. The tour
  never depends on it. `screen/dist/` is built and committed; after UI changes run
  `cd screen && npm install && npm run build`.
- `firmware/` - hardware partner (Sam). Marlin config for the SKR Pico, build and calibration steps.
- Change the contract below only after telling the whole team.

## Contract

### Python functions
- `paintings.load_painting(name: str) -> dict | None` - painting data (below), or None if not found.
- `paintings.save_painting(p: dict) -> None` - writes `cache/<slug of title>.json`.
- `board.show_grid(grid) -> None` - raises the pattern; returns once the last pin is up.
- `board.to_ascii(grid) -> str` - 10 lines of `#` (ball up) and `.` (flat).

### Client tools (ElevenLabs dashboard: type Client, "Wait for response" ticked)
- `open_painting(name)` -> `{found: false}` or
  `{found, title, artist, year, summary, sections: [{number, name, location}], now_showing, description, shape, guide_notes, museum_facts}`
  (it also raises section 1, so the tour can start immediately)
- `show_section(section)` where section is `"next"`, `"previous"` or a section number ->
  `{now_showing, description, shape, guide_notes, museum_facts}`; at either end only
  `{now_showing: "That was the last section." | "This is already the first section."}`;
  before any painting or for a bad section `{error}`

### Painting data (`cache/<id>.json`)
```json
{
  "title": "Mona Lisa", "artist": "Leonardo da Vinci", "year": "c. 1503-1519",
  "summary": "From Wikipedia.", "image": "cache/mona-lisa.jpg",
  "sections": [
    {"number": 1, "name": "her face", "bbox": [0.38, 0.12, 0.62, 0.38], "location": "top center",
     "description": "One or two sentences.", "grid": [[0,0,0,1,1,1,1,0,0,0], "...10 rows of 10..."],
     "relief": "cache/mona-lisa-1-relief.png", "relief_color": "cache/mona-lisa-1-relief-color.png"}
  ],
  "museum_facts": ["optional, from Browser Use"],
  "guide_notes": {"her face": "optional, from Creao"}
}
```
- `number` 1 = the most famous part; sections are in tour order.
- `bbox` = `[x0, y0, x1, y1]` as fractions of the image.
- `location` = the 3x3 cell of the bbox center: top left, top center, top right, center left, center,
  center right, bottom left, bottom center, bottom right.
- `grid` = 10 rows of 10. Row 0 = top (edge farthest from the user), column 0 = user's left, 1 = ball up.
- `relief`, `relief_color` = optional, screen only: 100x100 PNGs of the same part for the 10,000-pin
  simulation (gray = pin height 0-255, and the painting's colour per pin). Format: `docs/relief.md`.

### Board (Marlin G-code over USB, 115200 baud)
- An SKR Pico running Marlin moves a solenoid (on FAN0) under the 10x10 pins on two belts; no endstops.
- Per raised cell, in snake order: `G0 X.. Y..`, `M400`, `M106 S255`, `G4 P50`, `M107`; each line waits
  for Marlin's `ok`. Afterwards the head parks at `X0 Y0`.
- Pins go back down by hand. `show_grid` only raises pins.

## Environment (`.env`, never commit)
`AGENT_ID`, `ELEVENLABS_API_KEY`, `GEMINI_API_KEY`, `BROWSER_USE_API_KEY`, `CREAO_API_KEY`,
`CREAO_AGENT_ID`, `SENTRY_DSN`, `BOARD=sim|serial`, `SERIAL_PORT`

## Run
- Setup once: `brew install portaudio`, `python3 -m venv .venv`, `source .venv/bin/activate`,
  `pip install -r requirements.txt`
- Demo: `source .venv/bin/activate && python main.py` (Ctrl+C ends the conversation)
- Tests are plain scripts, no pytest: `python test_main.py`, `python test_board.py`, `python test_pipeline.py`,
  `python test_screen.py`, `python test_sponsors.py`, `python test_paintings.py` (live, uses Gemini)
- Audience screen: `python main.py` starts it; open http://127.0.0.1:8000. Without any API:
  `python screen.py --demo`

## Rules
- Demo paintings (must load instantly from cache): Mona Lisa, The Starry Night,
  The Great Wave off Kanagawa, Girl with a Pearl Earring.
- Wikimedia requests need a descriptive User-Agent header.
- Tool responses are read aloud by the agent's LLM: keep them short and plain.
- Submissions close Oct 18 at noon Pacific. Feature freeze at 10:00 AM that day.