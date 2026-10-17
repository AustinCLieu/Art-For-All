# Tactile Art Guide (LA Hacks AI Hackathon)

Blind users explore famous paintings by voice and touch. An ElevenLabs voice agent leads a guided
tour of a painting, part by part. A 10x10 board of balls raises the shape of the part being discussed.
Goal: the simplest thing that works for the demo. Don't add features that aren't in these docs.

## Files and owners (only edit your own files)
- `main.py`, `stubs.py`, `test_main.py` - Harvey. ElevenLabs conversation + the two client tools; `stubs.py`
  is a fake Mona Lisa + print-only board that `main.py` falls back to until the real parts import.
  Brief: `docs/harvey.md`
- `paintings.py`, `creao.py`, `prepare_demo.py`, `test_paintings.py`, `check.py`, `cache/` - Austin. Painting
  lookup (Wikipedia + one Gemini call + cache), the live Creao tour writer, and the one-time
  Browser Use / Creao script. Brief: `docs/austin.md`
- `board.py`, `send_frame.py`, `sim.py` - Teammate 3. Serial link to the board (+ optional simulation).
- `firmware/` - hardware partner.
- Change the contract below only after telling the whole team.

## Contract

### Python functions
- `paintings.load_painting(name: str) -> dict | None` - painting data (below), or None if not found.
- `paintings.save_painting(p: dict) -> None` - writes `cache/<slug of title>.json`.
- `board.show_grid(grid) -> None` - raises the pattern; returns once the balls have settled.
- `board.to_ascii(grid) -> str` - 10 lines of `#` (ball up) and `.` (flat).

### Client tools (ElevenLabs dashboard: type Client, "Wait for response" ticked)
- `open_painting(name)` -> `{found: false}` or
  `{found, title, artist, year, summary, sections: [{number, name, location}], now_showing, description, shape, guide_notes, museum_facts}`
  (it also raises section 1, so the tour can start immediately)
- `show_section(section)` where section is `"next"`, `"previous"` or a section number ->
  `{now_showing, description, shape, guide_notes, museum_facts}`

### Painting data (`cache/<id>.json`)
```json
{
  "title": "Mona Lisa", "artist": "Leonardo da Vinci", "year": "c. 1503-1519",
  "summary": "From Wikipedia.", "image": "cache/mona-lisa.jpg",
  "sections": [
    {"number": 1, "name": "her face", "bbox": [0.38, 0.12, 0.62, 0.38], "location": "top center",
     "description": "One or two sentences.", "grid": [[0,0,0,1,1,1,1,0,0,0], "...10 rows of 10..."]}
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

### Board serial protocol (115200 baud, one line per message)
- `F` + 100 digits (row by row) + newline -> board replies `OK` once the balls have settled
- `Z` + newline -> all balls down, replies `OK`

## Environment (`.env`, never commit)
`AGENT_ID`, `ELEVENLABS_API_KEY`, `GEMINI_API_KEY`, `BROWSER_USE_API_KEY`, `CREAO_API_KEY`,
`CREAO_AGENT_ID`, `SENTRY_DSN`, `BOARD=sim|serial`, `SERIAL_PORT`

## Run
- Setup once: `brew install portaudio`, `python3 -m venv .venv`, `source .venv/bin/activate`,
  `pip install -r requirements.txt`
- Demo: `source .venv/bin/activate && python main.py` (Ctrl+C ends the conversation)
- Tests are plain scripts, no pytest: `python test_main.py`, `python test_paintings.py`

## Rules
- Demo paintings (must load instantly from cache): Mona Lisa, The Starry Night,
  The Great Wave off Kanagawa, Girl with a Pearl Earring.
- Wikimedia requests need a descriptive User-Agent header.
- Tool responses are read aloud by the agent's LLM: keep them short and plain.
- Submissions close Oct 18 at noon Pacific. Feature freeze at 10:00 AM that day.