# ArtForAll — LA Hacks Build Plan

Oct 17, 2026 · Austin Lieu

> Source of truth for code: `CLAUDE.md`, `docs/harvey.md`, `docs/austin.md`. If this plan and those
> files ever disagree, the files win.

## How it works

Everything runs as one Python program on one laptop, with the mic, speaker and board plugged in. There is no web app, no server and no WebSocket.

1. The user talks. ElevenLabs hears them, thinks with Claude Sonnet 5.5, and talks back.
2. When the user names a painting, the agent calls `open_painting`. Our code finds it on Wikipedia, has Gemini split it into sections ranked by importance, each with a location and a 10 × 10 ball pattern, and raises section 1.
3. **The agent leads a guided tour.** It announces the section, walks the user's fingers through the shape, explains it, then waits. When the user says "I'm ready for the next part," it calls `show_section("next")` and does the same again.
4. **The user can interrupt any time:** "go back to her face", "top right", a question, or a new painting. After a jump, the tour carries on from there.
5. Questions need no tool. The agent answers from what the tools returned plus what Claude already knows about the painting, the artist and its history.

If Wikipedia has no matching painting or no image, `open_painting` returns `found: false` and the agent says it couldn't find that painting.

## Repo and files

Keep everything flat in the root so the imports in `main.py` work with no package setup, and commit the four demo paintings in `cache/`.

```text
artforall/
├── CLAUDE.md            # shared contract
├── .env / .env.example  # keys (never commit .env)
├── requirements.txt
├── docs/                # PLAN.md, harvey.md, austin.md, teammate3.md (not written yet)
├── main.py              # Harvey: ElevenLabs agent + the two tools (run this for the demo)
├── stubs.py             # Harvey: fake Mona Lisa + print-only board until the real parts land
├── paintings.py         # Austin: Wikipedia + Gemini + cache
├── creao.py             # Austin: Creao tour writer, runs live in the background
├── prepare_demo.py      # Austin: run once tonight (Browser Use + Creao for the demo paintings)
├── test_paintings.py    # Austin
├── check.py             # Austin: draws the boxes on each image to eyeball
├── cache/               # Austin: one .json + .jpg per painting
├── board.py             # Teammate 3: show_grid, to_ascii, serial to the board
├── send_frame.py        # Teammate 3: test patterns for the hardware
├── sim.py, sim.html     # Teammate 3: stretch, high-resolution simulation
└── firmware/            # hardware partner
```

## The contract

Two tools and one data shape are all the three of you need to agree on. Add both tools in the ElevenLabs dashboard as **Client** tools with these exact names, and tick **Wait for response** on each.

### Tool 1: `open_painting`

- Parameter `name` (string): the painting the user asked for, as specific as possible, such as "Mona Lisa by Leonardo da Vinci".
- Does: find it, split it, make the shapes, rank them, raise section 1. Cached paintings answer instantly; new ones take roughly 10–30 seconds. If the painting has no Creao notes yet, it also starts the Creao tour writer in the background.
- Returns the painting info, plus everything `show_section` returns for section 1 (description, shape, notes), so the tour can start right away:

```json
{
  "found": true,
  "title": "Mona Lisa",
  "artist": "Leonardo da Vinci",
  "year": "c. 1503-1519",
  "summary": "Two or three sentences from Wikipedia.",
  "sections": [
    {"number": 1, "name": "her face", "location": "top center"},
    {"number": 2, "name": "her hands", "location": "bottom center"},
    {"number": 3, "name": "the landscape", "location": "top right"}
  ],
  "now_showing": "Now showing section 1 of 3, the main subject: her face, at the top center."
}
```

### Tool 2: `show_section`

- Parameter `section` (string): `next`, `previous`, or a section number. The agent turns "top right" or "her hands" into a number using the names and locations it already has.
- Returns the sentence to announce, what is in the section, and the shape as text (`#` = ball up). Past the last section, `now_showing` says it was the last one.

```json
{
  "now_showing": "Now showing section 2 of 3: her hands, at the bottom center.",
  "description": "Her right hand rests lightly on her left wrist.",
  "shape": "..........\n..........\n...####...\n..######..\n..........",
  "guide_notes": "What a museum guide would say about this part (Creao); null until it arrives.",
  "museum_facts": ["Facts from the museum's own page (Browser Use); null until they arrive."]
}
```

### Painting data

`open_painting` saves each painting to `cache/<id>.json`; the values below are illustrative.

```json
{
  "title": "Mona Lisa",
  "artist": "Leonardo da Vinci",
  "year": "c. 1503-1519",
  "summary": "...",
  "image": "cache/mona-lisa.jpg",
  "sections": [
    {
      "number": 1,
      "name": "her face",
      "bbox": [0.38, 0.12, 0.62, 0.38],
      "location": "top center",
      "description": "One or two sentences on what is here and why it matters.",
      "grid": [[0,0,0,1,1,1,1,0,0,0], "...10 rows of 10..."]
    }
  ],
  "museum_facts": ["optional, from Browser Use"],
  "guide_notes": {"her face": "optional, from Creao"}
}
```

- `number` is the rank: 1 is the most famous part.
- `bbox` is `[x0, y0, x1, y1]` as fractions of the image. Code, not the model, sets `location` from the box's center on a 3 × 3 grid: top left, top center, top right, center left, center, center right, bottom left, bottom center, bottom right.
- `grid` is 10 rows of 10. Row 0 is the top of the section (the edge farthest from the user), column 0 is the user's left, 1 = ball up.

## Harvey: the conversation (ElevenLabs)

You own `main.py`: the ElevenLabs agent, the two tools, and which section is on the board. It is the program you run for the demo. You also own the two quick prizes: Sentry and the domain. **Full code, system prompt, tool setup and Claude Code prompt: `docs/harvey.md`.**

1. In the [ElevenLabs dashboard](https://elevenlabs.io/app/agents), create an agent with Claude Sonnet 5.5 as the LLM, a calm and clear voice, the first message and system prompt from `docs/harvey.md`, and both client tools from the contract.
2. Raise the turn timeout and the silence end-call timeout, so the agent doesn't nag or hang up while the user quietly feels the board.
3. Install: `brew install portaudio`, then `pip install "elevenlabs[pyaudio]" sentry-sdk python-dotenv`.
4. Start with stubs: a fake `load_painting` that returns a hand-written Mona Lisa, and a `show_grid` that prints. Swap in the real ones as teammates finish.
5. Test an uncached painting: the terminal should print `Creao run started`, the tour should start without waiting, and Creao's notes should reach later parts.
6. **Quick prizes:** a Sentry project for `SENTRY_DSN`, and a GoDaddy domain for the Devpost link.

**Done when:** by voice alone you can open a painting, say next, go back, "top right", "show me her hands", ask a question, and switch to another painting.

## Austin: the paintings, Gemini, Browser Use and Creao

You own `paintings.py` (`load_painting(name)` returns the painting data from the contract, or `None` when the painting can't be found), `creao.py` (the Creao tour writer, live in the background) and `prepare_demo.py` (adds Browser Use and Creao extras to the demo paintings). **Full code, Creao agent prompt and Claude Code prompt: `docs/austin.md`.**

1. **Cache first, by title.** If any cached painting's title appears in the requested name ("Mona Lisa by Leonardo da Vinci" contains "Mona Lisa"), return it. The demo paintings then open instantly however the agent words the name.
2. **Find it on Wikipedia.** No search result or no image means return `None`, and the agent says it couldn't find it.
3. **One Gemini call** with the image and the Wikipedia summary. It returns the artist, year and ranked sections, each with a box, a description and a 10 × 10 grid. No sections back (the image wasn't the painting) means return `None`.
4. **Convert and save:** turn each `box_2d` into `bbox` fractions, set `location` from the box's center on a 3 × 3 grid, number the sections 1, 2, 3 in Gemini's order, and save with `save_painting(p)` to `cache/<id>.json`.
5. **Cache the four demo paintings** (Mona Lisa, The Starry Night, The Great Wave off Kanagawa, Girl with a Pearl Earring) by calling `load_painting` on each. Open each image and fix any bad box in the JSON.
6. **This evening: the Creao agent and `creao.py`.** Create the agent at agent.creao.ai and run it once from the website too, so you have a run to share. Then build `creao.py`. Harvey's `main.py` already calls `start_tour_writer(p)` when a painting opens, so Creao runs live as soon as your file lands.
7. **Tonight: run `prepare_demo.py`** to add Browser Use museum facts and Creao guide notes to the demo paintings. It prints each Creao run ID; keep one.
8. **Creao prize checklist:** the agent is built on agent.creao.ai; the Devpost README has its agent ID and a share link to one of its runs (ask the booth how to share an API run, or share the one you started on the website); the demo shows it running.

**Done when:** the four demo paintings load instantly with sensible parts, boxes, facts and notes; a new painting loads in well under 30 seconds; and opening it starts a Creao run whose notes reach the tour.

## Teammate 3: shapes and the board

You own `board.py` (`show_grid`, `to_ascii`), the link to the hardware, and making the shapes feel right under a hand.

1. **Agree the serial protocol** with the hardware partner in the first 15 minutes (below).
2. **`board.py`** (code below): with `BOARD=sim` it prints the grid in the terminal; with `BOARD=serial` it sends the frame and waits for `OK`, so the agent speaks after the balls settle.
3. **`send_frame.py`** for the hardware partner: all up, all down, checkerboard, and the smile pattern below. Hand it over within the first hour.
4. **Tune the demo shapes by hand.** Once the board works, feel every section of the four demo paintings blindfolded and fix any weak `grid` directly in its cache JSON.
5. **Stretch, only with spare time: the high-resolution simulation** (below). A page beside the real board showing the painting with the current section boxed, the real 10 × 10, and a simulated 48 × 48 board of the same section.

**Done when:** every demo section is recognizable blindfolded on the real board.

```python
# board.py
import os, time, serial  # pip install pyserial

SIM = os.getenv("BOARD", "sim") == "sim"
port = None
if not SIM:
    port = serial.Serial(os.getenv("SERIAL_PORT"), 115200, timeout=3)
    time.sleep(2)  # many Arduinos reset when the port opens

def to_ascii(grid):
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)

def show_grid(grid):
    print(to_ascii(grid))
    if SIM:
        return
    port.reset_input_buffer()
    bits = "".join("1" if v else "0" for row in grid for v in row)
    port.write(("F" + bits + "\n").encode())
    port.readline()  # waits for "OK", or gives up after 3 s
```

### Stretch: high-resolution simulation

Pitch it straight: "Our prototype has 100 balls because that's what we could build this weekend. The software doesn't care about resolution; here is the same section on a 48 × 48 board, simulated." Label the page clearly as a simulation. It needs no model: it crops the painting to the section's box, finds the edges and shrinks them to 48 × 48. Call `render_sim(p, s)` inside `section_payload` in `main.py`, wrapped in a try so it can never break the tour, and open `sim.html` in a browser.

```python
# sim.py  (pip install pillow numpy)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RES = 48  # simulated pins per side

def high_res_grid(image_path, bbox, res=RES):
    img = Image.open(image_path).convert("L")
    w, h = img.size
    x0, y0, x1, y1 = bbox
    crop = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    edges = crop.filter(ImageFilter.FIND_EDGES).resize((res, res), Image.Resampling.BOX)
    a = np.asarray(edges, dtype=float)
    return (a > np.percentile(a, 75)).astype(int)  # strongest 25% of edges = raised pins

def draw_pins(grid, size=480):
    cell = size // len(grid)
    out = Image.new("RGB", (cell * len(grid),) * 2, (20, 20, 20))
    d = ImageDraw.Draw(out)
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            d.ellipse([c * cell + 1, r * cell + 1, (c + 1) * cell - 1, (r + 1) * cell - 1],
                      fill=(240, 240, 240) if v else (60, 60, 60))
    return out

def render_sim(painting, section):
    img = Image.open(painting["image"]).convert("RGB")
    img.thumbnail((480, 480))
    w, h = img.size
    x0, y0, x1, y1 = section["bbox"]
    ImageDraw.Draw(img).rectangle([x0 * w, y0 * h, x1 * w, y1 * h], outline=(255, 200, 0), width=4)
    panels = [img, draw_pins(section["grid"]), draw_pins(high_res_grid(painting["image"], section["bbox"]))]
    sheet = Image.new("RGB", (sum(p.width for p in panels) + 40, 480), (0, 0, 0))
    x = 0
    for p in panels:
        sheet.paste(p, (x, 0))
        x += p.width + 20
    sheet.save("sim.png")
```

```html
<!-- sim.html: reloads sim.png every second -->
<p>Painting · Real board (10 × 10) · Simulated 48 × 48 board</p>
<img id="s" src="sim.png" style="width: 100%">
<script>setInterval(() => s.src = "sim.png?" + Date.now(), 1000)</script>
```

### Serial protocol (with the hardware partner)

- 115200 baud, one line per message.
- `F` + 100 digits (`1` = ball up), row by row, then a newline: set every ball, reply `OK` once they have settled.
- `Z`: lower every ball, reply `OK`.
- Row 0 is the edge farthest from the user; column 0 is the user's left.
- Hardware tips: move a row at a time to limit current spikes, aim for under 2 seconds per frame, and put a fixed bump on the frame's top-left corner so the user always knows which way is up.

Smile test pattern:

```text
0000000000
0000000000
0000000000
1000000001
0110000110
0001111000
0000000000
0000000000
0000000000
0000000000
```

## Order of work

Submissions close tomorrow, Oct 18, at noon Pacific (3:00 PM Eastern on Devpost), and you must be there in person for judging. Get the voice loop working on fake data first, then swap in the real pieces one at a time.

- [ ] **Today, first 30 minutes:** one repo with `main.py`, `paintings.py`, `board.py`; the agent created in ElevenLabs; the serial protocol agreed. Stubs everywhere.
- [ ] **Today by about 3:00 PM:** Harvey drives a fake Mona Lisa tour by voice. Austin's `load_painting` works on its own. `send_frame.py` moves the real balls.
- [ ] **Today by about 6:00 PM:** the real `load_painting` plugged into `main.py`. Any painting works end to end by voice.
- [ ] **Tonight:** the real board plugged in. Austin finishes `creao.py` and runs `prepare_demo.py`; Teammate 3 hand-tunes the demo shapes.
- [ ] **Tomorrow, 10:00 AM:** no new features. Rehearse with a teammate blindfolded, record a backup video, and submit on Devpost well before noon.

If you fall behind, cut Browser Use first, then Creao; the tour works on Wikipedia and Gemini alone. Never cut the cached demo paintings. The high-resolution simulation is only for spare time, after everything else works.

## Sponsors

Each sponsor is used in its simplest form. Browser Use runs once ahead of time through `prepare_demo.py`. Creao's tour writer runs live whenever a painting without notes opens, so judges can watch it work.

- **ElevenLabs:** the agent, the voice, turn-taking and both tools. Core.
- **Gemini:** the one call that splits a painting into ranked sections and draws their shapes.
- **Browser Use:** finds each demo painting's museum page and pulls 3–5 facts the guide weaves into the tour.
- **Creao (part of the live product):** the "Tactile Tour Writer" agent writes what a guide would say about each part of a painting. When a painting with no notes opens, `main.py` starts it in the background; the tour begins right away and the notes reach the later parts. The four demo paintings get their notes ahead of time through `prepare_demo.py`.
  - **Their prize requirements:** build the agent on agent.creao.ai; put its agent ID and a share link to one of its runs in the Devpost README; show it running in the demo. For the demo, after the Mona Lisa tour, ask for The Birth of Venus (not cached) and keep the agent's run open at agent.creao.ai while the tour starts.
  - **Credits:** the free plan has 30 one-time credits and the docs' example run used 12, and every live run costs some. Ask the Creao booth for credits early. Check the input names your agent actually got in the Developer Console and match them in `creao.py`.
- **Sentry:** two lines at the top of `main.py`.
- **Espressif:** the board's controller is an ESP32, if your hardware partner can use one.

### Which prizes to enter

Seven prizes fit with real, visible uses. Check whether the hackathon caps how many prizes one project can enter.

| Prize | How you qualify | Owner | Extra work |
| --- | --- | --- | --- |
| MLH: Best use of ElevenLabs | The whole conversation and tour | Harvey | None, it's the core |
| MLH: Best use of Gemini API | Splits each painting and draws its touch shapes | Austin | None, it's the core |
| Best use of Browser Use | Museum facts in the demo tours | Austin | About 30 minutes |
| Creao | Tour-writer agent runs live when a new painting opens; agent ID and run link in the Devpost README | Austin | About an hour |
| Espressif | The board's controller is an ESP32 | Hardware | None if he uses one |
| Sentry | Two lines in `main.py` | Harvey | 5 minutes |
| MLH: Best domain name from GoDaddy | A domain for the project page or Devpost link | Anyone | 10 minutes |

The rest don't fit a blind user at a touch board without bolting on something unrelated: Fetch.ai, Paper, Cognition, Base44, QNX, Workday, Even Realities, StepFun, Photon, Visa, Intuit, Snowflake, Vultr, Solana, Tiger Data. veri.studio's open-source model prize would only fit if you swapped Claude out for an open model, which would cost quality and time.

## Risks

| Risk | Fallback |
| --- | --- |
| A section is unrecognizable at 10 × 10 | Each section fills the whole board, shapes are bold outlines, the agent's words carry the rest; hand-fix demo grids in the JSON |
| A new painting takes 10–30 seconds to open | The agent says "one moment" first; the demo paintings are cached |
| Gemini's boxes, ranking or shapes are off | Check and fix the four demo paintings by hand |
| The agent nags during silent touching | Raise the turn and silence timeouts |
| The board isn't ready | `BOARD=sim` prints the grid, so the demo still runs on screen |
| Wi-Fi fails at judging | Phone hotspot, cached paintings, backup video |
| Image rights | Demo only public-domain paintings; all four are |

## Sources

- [ElevenLabs Python SDK](https://elevenlabs.io/docs/eleven-agents/libraries/python)
- [ElevenLabs client tools](https://elevenlabs.io/docs/eleven-agents/customization/tools/client-tools)
- [Gemini image understanding](https://ai.google.dev/gemini-api/docs/image-understanding)
- [Browser Use: run a task](https://docs.browser-use.com/cloud/agent/quickstart)
- [Browser Use: choosing an agent](https://docs.browser-use.com/cloud/choosing-an-agent)
- [CREAO developer API](https://docs.creao.ai/developer-api/quickstart)