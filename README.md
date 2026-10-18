# Tactile Art Guide

**A voice-guided museum tour that blind visitors can feel.** Name any famous painting and a voice guide
walks you through it part by part, while a 10x10 board of raised balls forms the shape of each part
under your fingers.

> LA Hacks 2026 · Main track: TODO · Domain: TODO

## The problem

Museums are visual. A blind visitor at the Louvre gets, at best, an audio description of a painting
they can't see, and the museum's website is no better. Tactile reproductions exist, but each one is
hand-made for a single painting, so almost no art is accessible this way.

## What it does

1. You say **"Show me Girl with a Pearl Earring."**
2. The guide finds the painting, splits it into its most important parts (her face, the pearl earring,
   the turban, her jacket), and **raises the first part on the board**.
3. It tells you where to put your fingers and what you are feeling, explains the part, and then waits.
   Take as long as you like.
4. Say **"next"**, **"go back"**, **"the top right"**, **"show me the earring"**, or ask any question
   ("why is she looking over her shoulder?"). Say another painting's name at any time to switch.

It works for **any painting on Wikipedia**, not only a fixed list. A new painting is ready in about
15 seconds. While the tour runs, two agents work in the background: one gathers facts from the
painting's own museum website and the other writes a guide's script for each part. Their results flow
into the tour as soon as they arrive.

## How we use each sponsor's product

### Browser Use: making museum websites accessible
The Browser Use challenge asks for "a tool that makes websites more accessible." Museum websites hold
the best information about a painting, but they are built for sighted mouse users. In our project, the
**Browser Use agent visits the website on the blind visitor's behalf.** When a painting opens, a Browser
Use run starts in the background. It finds the painting's official museum page and turns it into
facts written to be spoken aloud. The voice guide then weaves them into the tour.

- Code: [`museum.py`](museum.py): `start_museum_facts(p)` starts the run in a background thread, so
  the visitor never waits. The facts reach the tour about 40 seconds later.
- Real results now in the cache come from the **Louvre** (Mona Lisa), **MoMA** (The Starry Night),
  **The Met** (The Great Wave) and the **Mauritshuis** (Girl with a Pearl Earring).
- The four demo paintings are also prepared ahead of time with [`prepare_demo.py`](prepare_demo.py),
  so they open instantly on stage.

### Creao: the "Tactile Tour Writer" agent
We built an agent on agent.creao.ai that writes what a museum guide would say **to someone whose
fingers are on that part of the painting**: concrete shapes and textures to feel, plus one surprising
fact. Gemini decides what the parts are, and Creao writes the narration for each one.

- Code: [`creao.py`](creao.py): `start_tour_writer(p)` runs the agent through Creao's API in a background
  thread whenever a painting without notes opens. A run takes about 70 seconds, and its notes are used
  for the sections that follow.
- Agent ID: `1b936489-00cb-4cc0-9524-914f81ec30d7`
- Example run (The Starry Night): https://agent.creao.ai/share/37a2d8ee78366196f03e63bf0a6c35d9
- Sample output for The Birth of Venus, scallop shell: *"Drop your hands to where the figure's bare
  feet rest: a wide fan-shaped scallop shell, its ribs running in raised flutes that radiate outward
  from a narrow hinge..."*

### ElevenLabs: the guide's voice and conversation
The whole experience is a conversation, with no screen involved. An ElevenLabs Conversational AI agent
(using Claude Sonnet 5.5 as its LLM) handles listening, speaking and turn-taking. We raised its silence
timeouts, so it waits quietly while you explore the board. It calls two **client tools** that run on
our laptop: `open_painting(name)` and `show_section("next" | "previous" | number)`. Code:
[`main.py`](main.py).

### Google Gemini: seeing the painting for you
Gemini works in two steps ([`paintings.py`](paintings.py)). One call takes the painting's image and
Wikipedia summary and returns its parts ranked from most to least famous, each with a bounding box and a
short description. Then one call per part, all in parallel, looks at just that part's crop and draws
**a 10x10 tactile pattern** for it. We use the box to tell the visitor where on the canvas the
part is ("at the top right"), and the pattern is what the board raises.

### Sentry: no silent failures during a live demo
The ElevenLabs SDK swallows exceptions raised inside client tools. [`main.py`](main.py) wraps each tool,
so any error is reported to Sentry with a full stack trace before the agent hears about it.

### GoDaddy
Project domain: TODO

## How it works

```
 Visitor speaks
      │
      ▼
 ElevenLabs agent (voice, turn-taking, Claude Sonnet 5.5)
      │  client tool call: open_painting / show_section
      ▼
 main.py (laptop) ──────────────► board.py ──serial──► 10x10 ball board
      │                              "F" + 100 digits, replies "OK" when settled
      ▼
 paintings.load_painting(name)
      ├─ cache/<painting>.json ── instant for paintings seen before
      └─ Wikipedia (image + summary) ─► Gemini (parts, boxes, 10x10 patterns) ─► saved to cache
      │
      └─ background threads, the tour never waits for them:
           ├─ Creao "Tactile Tour Writer" ─► guide_notes per part   (~70 s)
           └─ Browser Use (museum website) ─► museum_facts           (~40 s)
```

Each painting is stored as one JSON file (format in [`CLAUDE.md`](CLAUDE.md)): title, artist, year,
summary, and the ranked sections, each with its `bbox`, `location`, `description` and 10x10 `grid`,
plus `museum_facts` and `guide_notes`.

## Repository layout

| File | What it does |
| --- | --- |
| `main.py` | ElevenLabs conversation and the two client tools; run this for the demo |
| `paintings.py` | `load_painting(name)`: cache, Wikipedia, Gemini (parts, then one pattern per part) |
| `creao.py` | Creao Tactile Tour Writer, run in the background |
| `museum.py` | Browser Use museum facts, fetched in the background |
| `prepare_demo.py` | One-time script that adds facts and notes to the demo paintings |
| `board.py`, `send_frame.py`, `sim.py` | Serial link to the ball board (falls back to printing with `BOARD=sim`). TODO: not pushed yet |
| `cache/` | The four demo paintings (JSON + image), which load instantly |
| `screen.py`, `screen/` | Audience screen (React + TypeScript) at http://127.0.0.1:8000: the conversation, the board (mirrored, or simulated without hardware), the painting with the current part boxed, and what Gemini, Creao and Browser Use are doing. Optional: the tour runs the same without it |
| `stubs.py`, `test_main.py`, `test_pipeline.py`, `test_screen.py`, `test_sponsors.py`, `test_paintings.py`, `check.py` | Stubs, tests, and a script that draws each part's box on the painting |

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate   # macOS: brew install portaudio first
pip install -r requirements.txt
cp .env.example .env    # then fill in the keys below
python main.py          # talk to it; Ctrl+C ends the conversation
                        # audience screen: http://127.0.0.1:8000 (python screen.py --demo runs it without APIs)
```

`.env` keys: `AGENT_ID`, `ELEVENLABS_API_KEY`, `GEMINI_API_KEY`, `BROWSER_USE_API_KEY`,
`CREAO_API_KEY` (the agent's `capi_` key), `CREAO_AGENT_ID`, `SENTRY_DSN`, `BOARD=sim|serial`,
`SERIAL_PORT`. With `BOARD=sim` the shapes print in the terminal, so you can try it without the
hardware.

Tests: `python test_main.py`, `python test_pipeline.py`, `python test_screen.py` and
`python test_sponsors.py` (offline, no paid calls), and
`python test_paintings.py` (live).

## Limitations and what's next

- **100 balls is coarse.** At most, a face can show its outline, eyes and an earring. The
  software doesn't depend on the resolution, so a denser board would show more with no code changes.
- New paintings rely on Gemini's choice of parts. We checked the four demo paintings by hand.
- Next steps: a higher-resolution board, a museum-visit mode that walks through a museum's highlights,
  and audio descriptions in more languages.

## Team

TODO: names and roles.
