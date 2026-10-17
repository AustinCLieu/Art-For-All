# main.py with Stubs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harvey can hold a full guided Mona Lisa tour by voice, before the real board exists, by running `python main.py`.

**Architecture:** `main.py` is the reference code from `docs/harvey.md`. It starts an ElevenLabs conversation and registers two client tools, `open_painting` and `show_section`, which track the current painting and section in a module-level `state` dict. It imports `load_painting` from Austin's `paintings.py`, `show_grid`/`to_ascii` from Teammate 3's `board.py`, and `start_tour_writer` from `creao.py`. When any of those imports fails, it falls back to `stubs.py` (or a no-op), so the voice loop works on fake data.

**Tech Stack:** Python 3 in `.venv`, `elevenlabs[pyaudio]` 2.73.1, `sentry-sdk` 2.72.0, `python-dotenv` 1.2.4. Tests are plain `assert` scripts run with `python`, matching the team's `test_paintings.py` (pytest is not installed).

**Spec:** `docs/harvey.md` (the reference `main.py`, the client tool table, and the Claude Code kickoff prompt), plus the contract in `CLAUDE.md`.

## Global Constraints

- Only edit Harvey's files: `main.py`, `stubs.py`, `test_main.py`. The shared files `requirements.txt`, `.env.example` and `CLAUDE.md` may get additions only.
- Don't add features that aren't in `docs/harvey.md`.
- Tool names are exactly `open_painting` and `show_section`. Parameters are exactly `name` and `section`.
- `open_painting` returns `{found: false}` or `{found, title, artist, year, summary, sections: [{number, name, location}], now_showing, description, shape, guide_notes, museum_facts}`.
- `show_section` returns `{now_showing, description, shape, guide_notes, museum_facts}`.
- `grid` is 10 rows of 10. Row 0 is the top, 1 means ball up. `to_ascii` gives 10 lines of `#` and `.`.
- `location` is one of: top left, top center, top right, center left, center, center right, bottom left, bottom center, bottom right.
- Tool responses are read aloud: keep them short and plain.
- Never commit `.env`. It is already in `.gitignore`.
- Always run Python from the venv: `source .venv/bin/activate`.

## Notes for the executor

- **Austin's code is already in the repo** (`paintings.py`, `creao.py`, `cache/*.json`). Harvey's venv does not have `google-genai` or `requests` yet, so `from paintings import load_painting` raises `ModuleNotFoundError` (a subclass of `ImportError`), and `main.py` falls back to stubs. That is the intended state for this plan. If someone later runs `pip install -r requirements.txt`, `main.py` switches to the real paintings automatically. Tests never depend on which one loaded: they patch the stubs in.
- **`board.py` does not exist yet**, so `show_grid` and `to_ascii` always come from `stubs.py` for now.
- **The only deviation from the reference `main.py`** is wrapping the conversation startup in `if __name__ == "__main__":`. Without it, `import main` in the tests would open a microphone session. Behavior when you run `python main.py` is unchanged.
- **Push is currently blocked:** `git push` fails with `Permission denied (publickey)` on Austin's repo. Commit locally after each task and don't try to fix the push. Harvey is sorting out access separately.

## File Structure

| File | Status | Responsibility |
| --- | --- | --- |
| `stubs.py` | Create | Fake `load_painting` (a hand-written Mona Lisa), plus a print-only `show_grid` and `to_ascii` |
| `main.py` | Create | ElevenLabs conversation, the two client tools, and which section is showing |
| `test_main.py` | Create | Plain-assert tests for the stubs and both tools, with no audio or network |
| `requirements.txt` | Modify (append) | Add Harvey's packages |
| `.env.example` | Create | Every env var name from `CLAUDE.md`, with no values |
| `CLAUDE.md` | Modify | List the files that now exist and add the run and test commands. The contract does not change. |

---

### Task 1: `stubs.py`, a fake Mona Lisa and a print-only board

**Files:**
- Create: `stubs.py`
- Test: `test_main.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `stubs.load_painting(name: str) -> dict | None`: a painting dict matching the `CLAUDE.md` contract when `"mona lisa"` is in `name.lower()`, otherwise `None`.
  - `stubs.show_grid(grid: list[list[int]]) -> None`: prints `to_ascii(grid)`.
  - `stubs.to_ascii(grid: list[list[int]]) -> str`: 10 lines joined by `"\n"`, using `#` for 1 and `.` for 0.

- [ ] **Step 1: Write the failing test**

Create `test_main.py`:

```python
# Run: python test_main.py   (no audio, no network)
import stubs

LOCATIONS = {"top left", "top center", "top right", "center left", "center",
             "center right", "bottom left", "bottom center", "bottom right"}

def test_stub_painting():
    p = stubs.load_painting("Mona Lisa by Leonardo da Vinci")
    assert p["title"] == "Mona Lisa"
    for key in ("artist", "year", "summary", "image", "sections"):
        assert key in p, key
    assert [s["number"] for s in p["sections"]] == [1, 2, 3]
    assert [s["name"] for s in p["sections"]] == ["her face", "her hands", "the landscape"]
    for s in p["sections"]:
        assert s["location"] in LOCATIONS, s["location"]
        assert len(s["bbox"]) == 4
        assert s["description"]
        assert len(s["grid"]) == 10 and all(len(row) == 10 for row in s["grid"]), s["name"]
        assert all(v in (0, 1) for row in s["grid"] for v in row), s["name"]
        assert any(v for row in s["grid"] for v in row), s["name"] + " grid is empty"

def test_stub_not_found():
    assert stubs.load_painting("The Starry Night") is None
    assert stubs.load_painting("asdfgh") is None

def test_to_ascii():
    grid = [[1, 0] * 5] + [[0] * 10] * 9
    lines = stubs.to_ascii(grid).split("\n")
    assert len(lines) == 10
    assert lines[0] == "#.#.#.#.#."
    assert lines[1] == ".........."

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python test_main.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'stubs'`.

- [ ] **Step 3: Write `stubs.py`**

The section names and locations match Austin's `cache/mona-lisa.json`, so the voice flow sounds the same once the real data is plugged in.

```python
# Stand-ins until paintings.py (Austin) and board.py (Teammate 3) are ready.

def to_ascii(grid):
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)

def show_grid(grid):
    print(to_ascii(grid))

def _grid(rows):
    return [[int(c) for c in row] for row in rows]

MONA_LISA = {
    "title": "Mona Lisa",
    "artist": "Leonardo da Vinci",
    "year": "c. 1503-1519",
    "summary": "A half-length portrait of a seated woman, painted by Leonardo da Vinci "
               "and famous for her faint smile. It hangs in the Louvre in Paris.",
    "image": "cache/mona-lisa.jpg",
    "sections": [
        {"number": 1, "name": "her face", "bbox": [0.38, 0.12, 0.62, 0.38], "location": "top center",
         "description": "Her calm face with the famous faint smile, framed by dark hair.",
         "grid": _grid(["0001111000",
                        "0011111100",
                        "0110000110",
                        "0100000010",
                        "0100000010",
                        "0100000010",
                        "0110000110",
                        "0011001100",
                        "0001111000",
                        "0000110000"])},
        {"number": 2, "name": "her hands", "bbox": [0.30, 0.70, 0.75, 0.92], "location": "bottom center",
         "description": "Her right hand rests lightly on her left wrist, relaxed and soft.",
         "grid": _grid(["0000000000",
                        "0000000000",
                        "0011110000",
                        "0111111000",
                        "0111111110",
                        "0001111111",
                        "0000011110",
                        "0000000000",
                        "0000000000",
                        "0000000000"])},
        {"number": 3, "name": "the landscape", "bbox": [0.00, 0.10, 1.00, 0.70], "location": "center",
         "description": "A misty, dreamlike landscape of winding roads and water behind her.",
         "grid": _grid(["0000000000",
                        "1100000011",
                        "0011000110",
                        "0000111000",
                        "0000010000",
                        "0000100000",
                        "0001000000",
                        "0000100000",
                        "0000010000",
                        "0000000000"])},
    ],
}

def load_painting(name):
    return MONA_LISA if "mona lisa" in name.lower() else None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python test_main.py`
Expected: `PASS test_stub_painting`, `PASS test_stub_not_found`, `PASS test_to_ascii`.

- [ ] **Step 5: Commit**

```bash
git add stubs.py test_main.py
git commit -m "feat: add stub painting and print-only board"
```

---

### Task 2: `main.py`, the conversation and the two client tools

**Files:**
- Create: `main.py`
- Modify: `test_main.py` (add tool tests above the `if __name__` block)

**Interfaces:**
- Consumes: `stubs.load_painting`, `stubs.show_grid` and `stubs.to_ascii` from Task 1.
- Produces, used by the ElevenLabs agent:
  - `main.open_painting(params: dict) -> dict`, where `params = {"name": str}`.
  - `main.show_section(params: dict) -> dict`, where `params = {"section": "next" | "previous" | "<number>"}`.
  - `main.state: dict` with keys `painting` (dict or None) and `index` (0-based int).

- [ ] **Step 1: Write the failing tests**

Add these to `test_main.py`, after `test_to_ascii` and before `if __name__ == "__main__":`:

```python
def fresh_main():
    import main
    main.load_painting = stubs.load_painting  # don't depend on which paintings.py loaded
    main.show_grid = lambda grid: None        # keep test output quiet
    main.to_ascii = stubs.to_ascii
    main.start_tour_writer = lambda p: None   # never start Creao from tests
    main.state.update(painting=None, index=0)
    return main

def test_open_not_found():
    m = fresh_main()
    assert m.open_painting({"name": "A Painting That Does Not Exist"}) == {"found": False}

def test_show_before_open():
    m = fresh_main()
    assert "error" in m.show_section({"section": "next"})

def test_open_mona_lisa():
    m = fresh_main()
    r = m.open_painting({"name": "Mona Lisa by Leonardo da Vinci"})
    assert r["found"] is True
    assert r["title"] == "Mona Lisa" and r["artist"] and r["year"] and r["summary"]
    assert r["sections"][0] == {"number": 1, "name": "her face", "location": "top center"}
    assert all(set(s) == {"number", "name", "location"} for s in r["sections"])  # no grids sent to the LLM
    assert r["now_showing"] == "Now showing section 1 of 3, the main subject: her face, at the top center."
    assert len(r["shape"].split("\n")) == 10
    assert r["description"]
    assert "guide_notes" in r and "museum_facts" in r
    assert m.state["index"] == 0

def test_navigation():
    m = fresh_main()
    m.open_painting({"name": "Mona Lisa"})
    assert m.show_section({"section": "previous"}) == {"now_showing": "This is already the first section."}
    r = m.show_section({"section": "next"})
    assert r["now_showing"] == "Now showing section 2 of 3, her hands, at the bottom center."
    assert set(r) == {"now_showing", "description", "shape", "guide_notes", "museum_facts"}
    assert m.show_section({"section": "Previous "})["now_showing"].startswith("Now showing section 1 of 3")
    assert m.show_section({"section": "3"})["now_showing"].startswith("Now showing section 3 of 3")
    assert m.show_section({"section": "next"}) == {"now_showing": "That was the last section."}
    assert m.state["index"] == 2
    assert m.show_section({"section": "99"})["now_showing"].startswith("Now showing section 3 of 3")
    assert m.show_section({"section": "0"})["now_showing"].startswith("Now showing section 1 of 3")
    assert "error" in m.show_section({"section": "her hands"})

def test_switch_painting_resets_tour():
    m = fresh_main()
    m.open_painting({"name": "Mona Lisa"})
    m.show_section({"section": "3"})
    m.open_painting({"name": "Mona Lisa"})
    assert m.state["index"] == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python test_main.py`
Expected: the three Task 1 tests pass, then `test_open_not_found` fails with `ModuleNotFoundError: No module named 'main'`.

- [ ] **Step 3: Write `main.py`**

This is the reference code from `docs/harvey.md`. The only change is that the last block sits under `if __name__ == "__main__":`.

```python
# Env: AGENT_ID, ELEVENLABS_API_KEY, BOARD, SERIAL_PORT, SENTRY_DSN
import os, signal
from dotenv import load_dotenv
import sentry_sdk  # Sentry prize: catches any tool error during the demo
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

load_dotenv()
try:
    from paintings import load_painting  # Austin
except ImportError:
    from stubs import load_painting
try:
    from board import show_grid, to_ascii  # Teammate 3
except ImportError:
    from stubs import show_grid, to_ascii
try:
    from creao import start_tour_writer  # Austin: Creao agent writes guide notes in the background
except ImportError:
    def start_tour_writer(p):
        pass

sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))
state = {"painting": None, "index": 0}

def section_payload(i):
    p = state["painting"]
    s = p["sections"][i]
    state["index"] = i
    show_grid(s["grid"])  # returns once the balls settle
    lead = "the main subject: " if i == 0 else ""
    return {
        "now_showing": f"Now showing section {i + 1} of {len(p['sections'])}, {lead}{s['name']}, at the {s['location']}.",
        "description": s["description"],
        "shape": to_ascii(s["grid"]),
        "guide_notes": (p.get("guide_notes") or {}).get(s["name"]),  # from Creao, demo paintings only
        "museum_facts": p.get("museum_facts"),                       # from Browser Use, demo paintings only
    }

def open_painting(params):
    p = load_painting(params["name"])
    if not p:
        return {"found": False}
    state["painting"] = p
    start_tour_writer(p)  # no-op if the painting already has guide notes
    sections = [{"number": s["number"], "name": s["name"], "location": s["location"]} for s in p["sections"]]
    return {"found": True, "title": p["title"], "artist": p["artist"], "year": p["year"],
            "summary": p["summary"], "sections": sections, **section_payload(0)}

def show_section(params):
    p = state["painting"]
    if not p:
        return {"error": "No painting is open yet."}
    n, last = state["index"], len(p["sections"]) - 1
    want = str(params.get("section", "")).strip().lower()
    if want == "next":
        if n == last:
            return {"now_showing": "That was the last section."}
        n += 1
    elif want == "previous":
        if n == 0:
            return {"now_showing": "This is already the first section."}
        n -= 1
    else:
        try:
            n = max(0, min(last, int(want) - 1))
        except ValueError:
            return {"error": "Pass next, previous, or a section number."}
    return section_payload(n)

if __name__ == "__main__":
    tools = ClientTools()
    tools.register("open_painting", open_painting)
    tools.register("show_section", show_section)

    api_key = os.getenv("ELEVENLABS_API_KEY")
    conversation = Conversation(
        ElevenLabs(api_key=api_key),
        os.getenv("AGENT_ID"),
        requires_auth=bool(api_key),
        audio_interface=DefaultAudioInterface(),
        client_tools=tools,
        callback_agent_response=lambda r: print(f"Agent: {r}"),
        callback_user_transcript=lambda t: print(f"User: {t}"),
    )
    conversation.start_session()
    signal.signal(signal.SIGINT, lambda *_: conversation.end_session())
    print(conversation.wait_for_session_end())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python test_main.py`
Expected: 8 lines, each starting with `PASS`, and no traceback.

- [ ] **Step 5: Check which painting source `main.py` picked up**

Run: `python -c "import main; print(main.load_painting.__module__, main.show_grid.__module__)"`
Expected: `stubs stubs`. Seeing `paintings stubs` is also fine: it means Austin's dependencies are installed and the real lookup is active.

- [ ] **Step 6: Commit**

```bash
git add main.py test_main.py
git commit -m "feat: add ElevenLabs conversation with open_painting and show_section tools"
```

---

### Task 3: Requirements, `.env.example` and `CLAUDE.md`

**Files:**
- Modify: `requirements.txt` (append two lines; the file belongs to the whole team)
- Create: `.env.example`
- Modify: `CLAUDE.md` (the "Files and owners" section, plus a new "Run" section; the contract is untouched)

**Interfaces:**
- Consumes: the file names created in Tasks 1 and 2.
- Produces: docs only. No code depends on this task.

- [ ] **Step 1: Append Harvey's packages to `requirements.txt`**

The file currently contains `requests`, `google-genai`, `python-dotenv`, `pillow` and `browser-use-sdk`. Add these two lines at the end. `python-dotenv` is already listed, so don't duplicate it.

```text
elevenlabs[pyaudio]
sentry-sdk
```

- [ ] **Step 2: Create `.env.example`**

```text
AGENT_ID=
ELEVENLABS_API_KEY=
GEMINI_API_KEY=
BROWSER_USE_API_KEY=
CREAO_API_KEY=
CREAO_AGENT_ID=
SENTRY_DSN=
BOARD=sim
SERIAL_PORT=
```

- [ ] **Step 3: Update `CLAUDE.md` "Files and owners"**

Replace these two bullets:

```markdown
- `main.py` - Harvey. ElevenLabs conversation + the two client tools. Brief: `docs/harvey.md`
- `paintings.py`, `prepare_demo.py` - Austin. Painting lookup (Wikipedia + one Gemini call + cache) and the
  one-time Browser Use / Creao script. Brief: `docs/austin.md`
```

with:

```markdown
- `main.py`, `stubs.py`, `test_main.py` - Harvey. ElevenLabs conversation + the two client tools; `stubs.py`
  is a fake Mona Lisa + print-only board that `main.py` falls back to until the real parts import.
  Brief: `docs/harvey.md`
- `paintings.py`, `creao.py`, `prepare_demo.py`, `test_paintings.py`, `check.py`, `cache/` - Austin. Painting
  lookup (Wikipedia + one Gemini call + cache), the live Creao tour writer, and the one-time
  Browser Use / Creao script. Brief: `docs/austin.md`
```

- [ ] **Step 4: Add a "Run" section to `CLAUDE.md`**

Insert it directly above `## Rules`:

```markdown
## Run
- Setup once: `brew install portaudio`, `python3 -m venv .venv`, `source .venv/bin/activate`,
  `pip install -r requirements.txt`
- Demo: `source .venv/bin/activate && python main.py` (Ctrl+C ends the conversation)
- Tests are plain scripts, no pytest: `python test_main.py`, `python test_paintings.py`
```

- [ ] **Step 5: Verify nothing broke and no secrets are staged**

Run: `python test_main.py && git status --short`
Expected: 8 lines starting with `PASS`. The status shows only `requirements.txt`, `.env.example` and `CLAUDE.md`, and `.env` does **not** appear.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example CLAUDE.md
git commit -m "docs: add env example, Harvey deps, and run instructions"
```

---

### Task 4: Voice smoke test (manual, done by Harvey)

There is no code in this task. It confirms the real ElevenLabs agent works end to end with the stubs. An agentic executor stops here and hands over to Harvey.

**Files:** none.

**Interfaces:**
- Consumes: `python main.py` from Task 2, and the dashboard agent from Batch 1, whose tools are named exactly `open_painting(name)` and `show_section(section)`.

- [ ] **Step 1: Start the conversation**

Run: `source .venv/bin/activate && python main.py`
Expected: the agent says "Hi! I can show you famous paintings through touch..." If macOS asks for microphone access for Terminal or VS Code, allow it.

- [ ] **Step 2: Open the stub painting**

Say: "The Mona Lisa."
Expected: the agent says "One moment while I find it". The terminal prints the face grid, and the agent reads "Now showing section 1 of 3..." and walks you through the shape.

- [ ] **Step 3: Navigate**

Say each of these in turn: "I'm ready for the next part", "go back", "show me the landscape", then "next" twice.
Expected: a new grid prints for each move. The final "next" makes the agent say the tour is over.

- [ ] **Step 4: Not found**

Say: "Show me The Starry Night."
Expected: with stubs active, the agent says it couldn't find it and asks for another painting.

- [ ] **Step 5: End**

Press Ctrl+C. The conversation should end cleanly.

If something fails:

| Symptom | Likely cause |
| --- | --- |
| Auth or 401 error at start | `AGENT_ID` or `ELEVENLABS_API_KEY` in `.env` is wrong |
| Agent talks but the grid never prints | The tool name or parameter name in the dashboard doesn't exactly match `open_painting`/`name` or `show_section`/`section` |
| Agent says the result before the grid prints | "Wait for response" isn't ticked on that tool |
| No sound, or the agent can't hear you | Microphone permission, or the wrong default input/output device in macOS Sound settings |
