# Audience Screen (React + TypeScript) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A browser page the judges can watch during the demo. It shows the conversation (visitor and
guide), a 10x10 board of balls rising and falling with each section (mirroring the real board, or
standing in for it if the hardware fails), the painting with the current part boxed, and what each
sponsor's piece is doing (ElevenLabs, Gemini, Creao, Browser Use). **The voice tour must work exactly as it
does today whether or not the screen works.**

**Architecture:** `main.py` stays the only program. A new stdlib-only module, `screen.py`, keeps a small
in-memory state (transcript, current painting/section, background activity) and serves it from a
background thread at `http://127.0.0.1:8000`: `GET /api/state` returns JSON, `GET /cache/<image>` returns
painting images, and everything else serves the built React app from `screen/dist/`. The React app polls
`/api/state` every 300 ms. `main.py`, `paintings.py`, `creao.py` and `museum.py` report to the screen
through a few one-line calls, each imported with a no-op fallback. Audio stays in Python; the page only
displays. The built `screen/dist/` is committed, so the demo laptop needs no Node.

**Tech Stack:** Python 3 standard library (`http.server`, `threading`, `json`). React 18.3.1,
TypeScript 5.6.3 and Vite 5.4.11 (Node 22 for building only). Plain CSS, system fonts, no CDN. Tests
are plain `assert` scripts run with `python <file>.py` (no pytest).

**Spec:** Agreed in chat on 2026-10-17 (Austin). Problem: the hardware may not be ready, and even if it is,
only one judge can touch it at a time; the background agents (Creao, Browser Use) are invisible. `plan.md`
already lists a simulation page (`sim.html`) as a stretch goal; this replaces it with one page that also
shows the conversation and the sponsor activity.

## Global Constraints

- **The tour never depends on the screen.** This is the most important rule in this plan.
  - The ElevenLabs SDK **ends the conversation** if a callback raises
    (`elevenlabs/conversational_ai/conversation.py:955-957`, SDK 2.73.1: `logger.error(...)` then
    `self.end_session()`). So every public function in `screen.py` catches all exceptions itself.
  - Every file that uses the screen imports it inside `try/except Exception` with a no-op fallback, so
    deleting `screen.py` changes nothing (tested in Task 5).
  - If port 8000 is busy, `start_screen()` prints `Audience screen off: ...` and returns `None`; the tour
    carries on (tested in Task 2).
  - If `screen/dist/` is missing, the page answers 503 with a build hint; nothing else is affected.
- **Don't change the contract** in `CLAUDE.md` (tools, painting JSON, serial protocol). Tool responses
  sent to ElevenLabs must not change: `test_main.py` must pass unmodified.
- **Don't touch Teammate 3's or Harvey's stubs:** `board.py`, `send_frame.py`, `sim.py`, `stubs.py`,
  `firmware/` and `test_main.py` are not edited. The screen mirrors the frames `main.py` sends to the
  board; it does not replace or wrap `show_grid`.
- `main.py` is Harvey's file: the edits in Task 5 are small and additive. Tell Harvey before merging.
- No new Python packages. No changes to `requirements.txt`.
- Never commit `.env`. Never commit `screen/node_modules/`.
- No API calls from any test (no ElevenLabs, Gemini, Creao or Browser Use credits).
- Keep the code style: short functions, few comments, no classes in the Python except the two the
  standard library's HTTP server requires.
- Run everything from the repo root. Use the venv if there is one (`source .venv/bin/activate`); on
  Austin's Windows laptop the packages are installed in the global Python.
- Work on branch `feat/audience-screen`. Commit after each task. Don't push or merge until Austin says so.
  Feature freeze: Oct 18, 10:00 AM Pacific. If the branch isn't solid by about 8:00 AM, don't merge it.
- Commit messages follow the repo style (`file: what changed`) and have **no** `Co-Authored-By` trailer.

## File Structure

| File | Status | Responsibility |
| --- | --- | --- |
| `screen.py` | Create | In-memory state, `snapshot()`, HTTP server, `python screen.py --demo` |
| `test_screen.py` | Create | Offline tests: state, never-raises, HTTP, port in use, integration with `main.py` and `paintings.py` |
| `screen/package.json`, `screen/package-lock.json` | Create | Pinned front-end dependencies |
| `screen/tsconfig.json`, `screen/vite.config.ts`, `screen/index.html` | Create | Build config |
| `screen/src/types.ts` | Create | TypeScript types for `/api/state` |
| `screen/src/useScreenState.ts` | Create | Polling hook |
| `screen/src/main.tsx`, `screen/src/App.tsx` | Create | Entry point and layout |
| `screen/src/components/{PaintingView,Board,Transcript,ActivityBar}.tsx` | Create | The four parts of the page |
| `screen/src/styles.css` | Create | All styling |
| `screen/dist/` | Create (built, committed) | What `screen.py` serves |
| `paintings.py` | Modify (Austin's) | Report Gemini steps: 1 import block + 6 calls |
| `creao.py` | Modify (Austin's) | Report Creao run status: 1 import block + 4 calls |
| `museum.py` | Modify (Austin's) | Report Browser Use run status: 1 import block + 3 calls |
| `main.py` | Modify (Harvey's) | Start the screen, mirror sections and transcript: about 15 lines |
| `.gitignore` | Modify (append) | `screen/node_modules/` |
| `CLAUDE.md`, `README.md` | Modify | List the new files and commands. The contract is unchanged |

### `/api/state` (the interface between Python and React)

```json
{
  "hardware": false,
  "transcript": [{"role": "user", "text": "Show me the Mona Lisa."}, {"role": "agent", "text": "..."}],
  "painting": {"title": "Mona Lisa", "artist": "Leonardo da Vinci", "year": "c. 1503-1519",
               "image": "/cache/mona-lisa.jpg",
               "sections": [{"number": 1, "name": "her face", "location": "top center"}]},
  "section": {"index": 0, "number": 1, "name": "her face", "location": "top center",
              "bbox": [0.38, 0.12, 0.62, 0.38], "grid": [[0,0,0,1,1,1,1,0,0,0], "...10 rows"],
              "frame": "F0001111000..."},
  "activity": {
    "elevenlabs":  {"status": "done", "detail": "In conversation"},
    "gemini":      {"status": "working", "detail": "Drawing 6 shapes in parallel"},
    "creao":       {"status": "done", "detail": "5 guide notes"},
    "browser_use": {"status": "idle", "detail": ""}
  }
}
```

- `status` is one of `idle`, `working`, `done`, `failed`.
- `painting` and `section` are `null` until a painting opens. `transcript` keeps the last 50 lines.
- `hardware` is `true` when `BOARD=serial`.
- `frame` is exactly the line the board receives (`F` + 100 digits, row by row).
- Creao and Browser Use chips are for the **current** painting: a status reported for that title wins;
  otherwise `done` if the painting already has `guide_notes` / `museum_facts`; otherwise `idle`.

## Order and parallel work

Task 0 first. Then Tasks 1 → 2 (Python) and Task 3 (React) can run in parallel, because `/api/state` above
is the whole interface between them. Tasks 4 and 5 need Task 1. Task 6 needs all of them. Task 7 is
for a human with a microphone.

---

### Task 0: Branch

- [ ] **Step 1: Create the branch from an up-to-date main**

```bash
git checkout main
git pull --ff-only
git checkout -b feat/audience-screen
```

Expected: `Switched to a new branch 'feat/audience-screen'`. `git status` is clean.

- [ ] **Step 2: Record the baseline**

Run: `python test_main.py && python test_pipeline.py`
Expected: 10 `PASS` lines, then 7 `ok` lines (plus the expected `draw failed for 'her eye'` and
`skipped bad section` lines). These must still pass, unchanged, at the end of every task.

---

### Task 1: `screen.py` state, and its tests

**Files:**
- Create: `screen.py` (state part)
- Create: `test_screen.py`

**Interfaces:**
- Consumes: `stubs.MONA_LISA` (test data only).
- Produces (all never raise):
  - `say(role: str, text) -> None`: appends `{"role": "user" | "agent", "text": str}`; keeps the last 50.
  - `correct(original: str, corrected: str) -> None`: replaces the newest agent line equal to `original`.
    Its signature matches the SDK's `callback_agent_response_correction(original, corrected)`.
  - `show_on_screen(painting: dict, index: int) -> None`: remembers the painting dict (by reference) and
    the 0-based section index.
  - `activity(source: str, status: str, detail="", title: str | None = None) -> None`: `source` is
    `gemini` (title `None`), `creao` or `browser_use` (title = painting title).
  - `snapshot() -> dict`: the `/api/state` JSON above. On any internal error it returns the defaults.

- [ ] **Step 1: Write the failing tests**

Create `test_screen.py`:

```python
# Run: python test_screen.py   (no audio, no network, no API keys)
import copy, json, os, subprocess, sys, tempfile, urllib.request, urllib.error
import screen, stubs

def reset():
    with screen._lock:
        screen._transcript.clear()
        screen._activity.clear()
        screen._live.update(painting=None, index=0)

def mona():
    return copy.deepcopy(stubs.MONA_LISA)

def test_empty_snapshot():
    reset()
    s = screen.snapshot()
    assert s["painting"] is None and s["section"] is None and s["transcript"] == []
    assert set(s["activity"]) == {"elevenlabs", "gemini", "creao", "browser_use"}
    assert all(a["status"] == "idle" for a in s["activity"].values())
    json.dumps(s)

def test_say_and_correct():
    reset()
    screen.say("user", "Show me the Mona Lisa")
    screen.say("agent", "One moment while I find it. Here she is.")
    screen.correct("One moment while I find it. Here she is.", "One moment while I find it.")
    screen.correct("text that was never said", "ignored")
    assert screen.snapshot()["transcript"] == [
        {"role": "user", "text": "Show me the Mona Lisa"},
        {"role": "agent", "text": "One moment while I find it."}]
    assert screen.snapshot()["activity"]["elevenlabs"]["status"] == "done"
    for n in range(60):
        screen.say("user", str(n))
    lines = screen.snapshot()["transcript"]
    assert len(lines) == 50 and lines[-1]["text"] == "59"

def test_show_on_screen():
    reset()
    screen.show_on_screen(mona(), 1)
    s = screen.snapshot()
    assert s["painting"]["title"] == "Mona Lisa" and s["painting"]["image"] == "/cache/mona-lisa.jpg"
    assert all(set(x) == {"number", "name", "location"} for x in s["painting"]["sections"])
    sec = s["section"]
    assert sec["number"] == 2 and sec["name"] == "her hands" and sec["location"] == "bottom center"
    assert len(sec["grid"]) == 10 and sec["bbox"] == [0.30, 0.70, 0.75, 0.92]
    assert sec["frame"][0] == "F" and len(sec["frame"]) == 101 and set(sec["frame"][1:]) <= {"0", "1"}
    assert sec["frame"][1:11] == "0000000000" and sec["frame"][21:31] == "0011110000"

def test_agent_chips():
    reset()
    p = mona()
    screen.show_on_screen(p, 0)
    a = screen.snapshot()["activity"]
    assert a["creao"]["status"] == "idle" and a["browser_use"]["status"] == "idle"
    screen.activity("creao", "working", "Writing guide notes", "Mona Lisa")
    screen.activity("browser_use", "failed", "No museum facts this time", "Some Other Painting")
    a = screen.snapshot()["activity"]
    assert a["creao"] == {"status": "working", "detail": "Writing guide notes"}
    assert a["browser_use"]["status"] == "idle"  # that run was for another painting
    p["museum_facts"] = ["one", "two"]  # Browser Use fills in the same dict main.py holds
    assert screen.snapshot()["activity"]["browser_use"] == {"status": "done", "detail": "2 museum facts"}
    screen.activity("gemini", "working", "Searching Wikipedia for X")
    assert screen.snapshot()["activity"]["gemini"]["status"] == "working"

def test_never_raises():
    reset()
    class Bad:
        def __str__(self):
            raise RuntimeError("bad text")
    screen.say("agent", Bad())
    screen.say("agent", "fine")
    screen.correct("fine", Bad())
    screen.activity("creao", "working", Bad(), "Mona Lisa")
    screen.show_on_screen({"sections": []}, 5)  # a broken painting
    s = screen.snapshot()
    assert s["painting"] is None and s["section"] is None
    json.dumps(s)
    screen.show_on_screen(None, 0)

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python test_screen.py`
Expected: `ModuleNotFoundError: No module named 'screen'`.

- [ ] **Step 3: Write the state part of `screen.py`**

Create `screen.py`:

```python
# Audience screen: mirrors the tour in a browser (React app in screen/, built into screen/dist/).
# Optional by design. Every public function catches its own errors, because an exception inside an
# ElevenLabs callback ends the conversation. The tour must work the same with or without this file.
import os, sys, json, glob, time, threading, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "screen", "dist")
CACHE = os.path.join(ROOT, "cache")
PORT = 8000
MAX_LINES = 50
IDLE = {"status": "idle", "detail": ""}
IMAGES = {".jpg", ".jpeg", ".png"}
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
         ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".ico": "image/x-icon", ".json": "application/json", ".woff2": "font/woff2"}  # not mimetypes: Windows' registry can get .js wrong

_lock = threading.Lock()
_transcript = []                        # [{"role": "user" | "agent", "text": str}]
_live = {"painting": None, "index": 0}  # the same dict main.py holds, so Creao and Browser Use results show up
_activity = {}                          # (source, painting title or None) -> {"status", "detail"}

def say(role, text):
    """Add a line to the conversation. Never raises."""
    try:
        line = {"role": "user" if role == "user" else "agent", "text": str(text)}
        with _lock:
            _transcript.append(line)
            del _transcript[:-MAX_LINES]
    except Exception as e:
        print(f"screen.say failed: {e!r}")

def correct(original, corrected):
    """The visitor interrupted the guide: keep only what the guide actually said. Never raises."""
    try:
        with _lock:
            for line in reversed(_transcript):
                if line["role"] == "agent" and line["text"] == original:
                    line["text"] = str(corrected)
                    break
    except Exception as e:
        print(f"screen.correct failed: {e!r}")

def show_on_screen(painting, index):
    """Mirror the section that is on the board. Never raises."""
    try:
        with _lock:
            _live.update(painting=painting, index=index)
    except Exception as e:
        print(f"screen.show_on_screen failed: {e!r}")

def activity(source, status, detail="", title=None):
    """A background step: source is gemini, creao or browser_use; status is working, done or failed. Never raises."""
    try:
        entry = {"status": str(status), "detail": str(detail)[:120]}
        with _lock:
            _activity[(source, title)] = entry
    except Exception as e:
        print(f"screen.activity failed: {e!r}")

def _agent_chip(p, source, key, noun):
    a = _activity.get((source, p.get("title")))
    if a:
        return dict(a)
    if p.get(key):  # done earlier (demo paintings) or by a run that has finished
        return {"status": "done", "detail": f"{len(p[key])} {noun}"}
    return dict(IDLE)

def _views(p, i):
    s = p["sections"][i]
    image = p.get("image")
    painting = {"title": p["title"], "artist": p.get("artist", ""), "year": p.get("year", ""),
                "image": f"/cache/{os.path.basename(image)}" if image else None,
                "sections": [{"number": x["number"], "name": x["name"], "location": x["location"]}
                             for x in p["sections"]]}
    section = {"index": i, "number": s["number"], "name": s["name"], "location": s["location"],
               "bbox": s["bbox"], "grid": s["grid"],
               "frame": "F" + "".join("1" if v else "0" for row in s["grid"] for v in row)}
    return painting, section

def snapshot():
    """Everything the page draws, as JSON-ready data. Never raises."""
    out = {"hardware": os.getenv("BOARD", "sim") == "serial", "transcript": [], "painting": None,
           "section": None, "activity": {k: dict(IDLE) for k in ("elevenlabs", "gemini", "creao", "browser_use")}}
    try:
        with _lock:
            p, i = _live["painting"], _live["index"]
            out["transcript"] = [dict(line) for line in _transcript]
            out["activity"]["elevenlabs"] = ({"status": "done", "detail": "In conversation"} if _transcript
                                             else {"status": "idle", "detail": "Waiting for the visitor"})
            out["activity"]["gemini"] = dict(_activity.get(("gemini", None), IDLE))
            if isinstance(p, dict):
                out["activity"]["creao"] = _agent_chip(p, "creao", "guide_notes", "guide notes")
                out["activity"]["browser_use"] = _agent_chip(p, "browser_use", "museum_facts", "museum facts")
                out["painting"], out["section"] = _views(p, i)
    except Exception as e:
        print(f"screen.snapshot failed: {e!r}")
    return out
```

(The imports for the server and demo are already at the top; Task 2 appends the rest.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python test_screen.py`
Expected: 5 `PASS` lines. Between them, these lines are expected (the never-raises test triggers them
on purpose):

```text
screen.say failed: RuntimeError('bad text')
screen.correct failed: RuntimeError('bad text')
screen.activity failed: RuntimeError('bad text')
screen.snapshot failed: IndexError('list index out of range')
```

- [ ] **Step 5: Commit**

```bash
git add screen.py test_screen.py
git commit -m "screen.py: audience screen state that never raises into the tour"
```

---

### Task 2: `screen.py` web server and demo mode

**Files:**
- Modify: `screen.py` (append)
- Modify: `test_screen.py` (add tests above `if __name__ == "__main__":`)

**Interfaces:**
- Consumes: `snapshot()`, `say`, `show_on_screen`, `activity` from Task 1.
- Produces:
  - `start_screen(port: int = 8000) -> str | None`: starts a daemon-thread server on `127.0.0.1`;
    returns `"http://127.0.0.1:<port>"` (the real port when `port=0`), or `None` if it can't start.
    Never raises. Prints `Audience screen: <url>` or `Audience screen off: <error>`.
  - Routes: `GET /api/state` (JSON, `no-store`); `GET /cache/<file>` (only `.jpg/.jpeg/.png` directly
    inside `cache/`, else 404); anything else serves a file from `screen/dist/`, falling back to
    `index.html`, never serving outside `screen/dist/`; 503 with a build hint if `index.html` is missing.
  - `python screen.py --demo`: replays all cached paintings with no API calls.

- [ ] **Step 1: Write the failing tests**

Add to `test_screen.py`, above `if __name__ == "__main__":`:

```python
def get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.headers["Content-Type"], r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers["Content-Type"], e.read()

def test_http():
    reset()
    screen.show_on_screen(mona(), 0)
    old = screen.DIST
    with tempfile.TemporaryDirectory() as dist:
        os.makedirs(os.path.join(dist, "assets"))
        with open(os.path.join(dist, "index.html"), "w") as f:
            f.write("<div id=root></div>")
        with open(os.path.join(dist, "assets", "app.js"), "w") as f:
            f.write("console.log(1)")
        screen.DIST = dist
        try:
            url = screen.start_screen(port=0)
            code, ctype, body = get(url + "/api/state")
            assert code == 200 and ctype == "application/json"
            assert json.loads(body)["section"]["name"] == "her face"
            assert get(url + "/")[:2] == (200, "text/html; charset=utf-8")
            assert get(url + "/assets/app.js")[1] == "text/javascript"
            assert get(url + "/some/page")[2] == b"<div id=root></div>"  # single-page app fallback
            code, ctype, _ = get(url + "/cache/mona-lisa.jpg")
            assert code == 200 and ctype == "image/jpeg"
            assert get(url + "/cache/mona-lisa.json")[0] == 404  # images only
            assert get(url + "/cache/..%2F.env")[0] == 404
            assert get(url + "/..%2F.env")[2] == b"<div id=root></div>"  # never serves outside dist
            screen.DIST = os.path.join(dist, "missing")
            assert get(url + "/")[0] == 503  # not built yet: a message, not a crash
        finally:
            screen.DIST = old

def test_port_in_use():
    url = screen.start_screen(port=0)
    port = int(url.rsplit(":", 1)[1])
    assert screen.start_screen(port=port) is None  # prints "Audience screen off"; the tour goes on
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python test_screen.py`
Expected: the 5 Task 1 tests pass, then `test_http` fails with
`AttributeError: module 'screen' has no attribute 'start_screen'`.

- [ ] **Step 3: Append the server and demo to `screen.py`**

Add to the end of `screen.py`:

```python
class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # the terminal belongs to the conversation

    def do_GET(self):
        try:
            path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
            if path == "/api/state":
                self._send(200, json.dumps(snapshot()).encode(), TYPES[".json"])
            elif path.startswith("/cache/"):
                self._file(os.path.join(CACHE, os.path.basename(path)), IMAGES)
            else:
                self._app(path)
        except Exception as e:
            print(f"screen: {self.path} failed: {e!r}")
            try:
                self._send(500, b"error", "text/plain")
            except Exception:
                pass

    def _app(self, path):
        dist = os.path.realpath(DIST)
        full = os.path.realpath(os.path.join(dist, path.lstrip("/")))
        if not (full.startswith(dist + os.sep) and os.path.isfile(full)):
            full = os.path.join(dist, "index.html")  # unknown paths get the app; nothing outside dist is served
        if not os.path.isfile(full):
            return self._send(503, b"Screen not built: cd screen && npm install && npm run build", "text/plain")
        self._file(full)

    def _file(self, path, allowed=None):
        ext = os.path.splitext(path)[1].lower()
        if (allowed and ext not in allowed) or not os.path.isfile(path):
            return self._send(404, b"not found", "text/plain")
        with open(path, "rb") as f:
            self._send(200, f.read(), TYPES.get(ext, "application/octet-stream"))

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = sys.platform != "win32"  # on Windows it would let a second server share the port

    def handle_error(self, request, client_address):
        pass  # a closed browser tab must not print tracebacks over the conversation

def start_screen(port=PORT):
    """Serve the page in a background thread. Returns its URL, or None if it can't start. Never raises."""
    try:
        server = _Server(("127.0.0.1", port), _Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}"
        print(f"Audience screen: {url}")
        return url
    except Exception as e:
        print(f"Audience screen off: {e!r}")
        return None

def demo():
    """Replays a tour of the cached paintings with no API calls, to build and rehearse the page."""
    if not start_screen():
        return
    for path in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        with open(path) as f:
            p = json.load(f)
        say("user", f"Show me {p['title']}.")
        activity("gemini", "working", f"Looking up {p['title']}")
        time.sleep(2)
        activity("gemini", "done", f"{p['title']}: ready from cache")
        for i, s in enumerate(p["sections"]):
            show_on_screen(p, i)
            say("agent", f"Now showing section {i + 1} of {len(p['sections'])}, {s['name']}, "
                         f"at the {s['location']}. {s['description']}")
            time.sleep(6)
            say("user", "I'm ready for the next part.")
    print("Demo finished.")

if __name__ == "__main__":
    if "--demo" in sys.argv:
        try:
            demo()
        except KeyboardInterrupt:
            pass
    else:
        print("Usage: python screen.py --demo   (main.py starts the screen by itself)")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python test_screen.py`
Expected: 7 `PASS` lines. Also expected: two `Audience screen: http://127.0.0.1:<port>` lines and one
`Audience screen off: OSError(...)` line (Windows: `10048 ... Only one usage of each socket address`;
macOS: `[Errno 48] Address already in use`).

- [ ] **Step 5: Commit**

```bash
git add screen.py test_screen.py
git commit -m "screen.py: serve the audience screen and a no-API demo mode"
```

---

### Task 3: The React app (can run in parallel with Tasks 1-2)

**Files:** everything under `screen/` (see File Structure).

**Interfaces:**
- Consumes: `GET /api/state` (shape above) and `/cache/<image>`.
- Produces: `screen/dist/index.html` + `screen/dist/assets/*`, served by `screen.py`.

- [ ] **Step 1: Create the config files**

`screen/package.json`:

```json
{
  "name": "tactile-art-screen",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/react": "18.3.12",
    "@types/react-dom": "18.3.1",
    "@vitejs/plugin-react": "4.3.4",
    "typescript": "5.6.3",
    "vite": "5.4.11"
  }
}
```

`screen/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "types": ["vite/client"]
  },
  "include": ["src", "vite.config.ts"]
}
```

`screen/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` serves the page with hot reload and forwards data requests to screen.py.
// 127.0.0.1, not localhost: Node may resolve localhost to IPv6, where screen.py isn't listening.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/cache": "http://127.0.0.1:8000",
    },
  },
});
```

`screen/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Tactile Art Guide</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Then run: `cd screen && npm install --no-audit --no-fund && cd ..`
Expected: `node_modules/` and `package-lock.json` appear in `screen/`. Use exactly these versions; don't
upgrade.

- [ ] **Step 2: Types and the polling hook**

`screen/src/types.ts`:

```ts
// The JSON that screen.py serves at /api/state. Keep in sync with screen.snapshot().

export type Role = "user" | "agent";

export interface Line {
  role: Role;
  text: string;
}

export interface SectionSummary {
  number: number;
  name: string;
  location: string;
}

export interface Painting {
  title: string;
  artist: string;
  year: string;
  image: string | null;
  sections: SectionSummary[];
}

export interface Section extends SectionSummary {
  index: number;
  bbox: [number, number, number, number];
  grid: number[][];
  frame: string;
}

export type Status = "idle" | "working" | "done" | "failed";

export interface Activity {
  status: Status;
  detail: string;
}

export interface State {
  hardware: boolean;
  transcript: Line[];
  painting: Painting | null;
  section: Section | null;
  activity: {
    elevenlabs: Activity;
    gemini: Activity;
    creao: Activity;
    browser_use: Activity;
  };
}
```

`screen/src/useScreenState.ts`:

```ts
import { useEffect, useRef, useState } from "react";
import type { State } from "./types";

// Asks screen.py for the state a few times a second. `online` is false while main.py isn't running.
export function useScreenState(intervalMs = 300) {
  const [state, setState] = useState<State | null>(null);
  const [online, setOnline] = useState(false);
  const last = useRef("");

  useEffect(() => {
    let alive = true;
    let timer = 0;
    const poll = async () => {
      try {
        const res = await fetch("/api/state", { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        if (alive && text !== last.current) {
          last.current = text; // only re-render when something changed
          setState(JSON.parse(text) as State);
        }
        if (alive) setOnline(true);
      } catch {
        if (alive) setOnline(false);
      }
      if (alive) timer = window.setTimeout(poll, intervalMs);
    };
    poll();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [intervalMs]);

  return { state, online };
}
```

- [ ] **Step 3: Entry point and layout**

`screen/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`screen/src/App.tsx`:

```tsx
import { ActivityBar } from "./components/ActivityBar";
import { Board } from "./components/Board";
import { PaintingView } from "./components/PaintingView";
import { Transcript } from "./components/Transcript";
import { useScreenState } from "./useScreenState";

export function App() {
  const { state, online } = useScreenState();
  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>Tactile Art Guide</h1>
          <p className="tagline">Audience view: what the visitor hears and feels, live.</p>
        </div>
        <span className={`pill ${online ? "on" : "off"}`}>{online ? "Live" : "Waiting for main.py"}</span>
      </header>
      <main className="stage">
        <PaintingView painting={state?.painting ?? null} section={state?.section ?? null} />
        <Board section={state?.section ?? null} hardware={state?.hardware ?? false} />
        <Transcript lines={state?.transcript ?? []} />
      </main>
      {state && <ActivityBar activity={state.activity} />}
    </div>
  );
}
```

- [ ] **Step 4: The four components**

`screen/src/components/Board.tsx`:

```tsx
import type { CSSProperties } from "react";
import type { Section } from "../types";

const FLAT: number[][] = Array.from({ length: 10 }, () => Array<number>(10).fill(0));

// Row 0 is the edge farthest from the visitor, as on the real board. Balls move one row at a time.
export function Board({ section, hardware }: { section: Section | null; hardware: boolean }) {
  const grid = section?.grid ?? FLAT;
  const raised = grid.flat().filter(Boolean).length;
  return (
    <section className="panel board-panel">
      <h2>{hardware ? "Touch board, mirrored live" : "Touch board, simulated"}</h2>
      <p className="now">{section ? section.name : "All balls down"}</p>
      <div className="board" role="img" aria-label={`${raised} of 100 balls raised`}>
        {grid.map((row, r) =>
          row.map((v, c) => (
            <span key={`${r}-${c}`} className={v ? "pin up" : "pin"} style={{ "--row": r } as CSSProperties} />
          )),
        )}
      </div>
      <p className="caption">
        {hardware ? "The same frame the physical board is showing" : "The same frames the physical board receives over serial"}
      </p>
      <code className="frame">{section?.frame ?? "Z"}</code>
    </section>
  );
}
```

`screen/src/components/PaintingView.tsx`:

```tsx
import type { Painting, Section } from "../types";

export function PaintingView({ painting, section }: { painting: Painting | null; section: Section | null }) {
  if (!painting) {
    return (
      <section className="panel painting-panel empty">
        <p>No painting yet. Ask the guide for one.</p>
      </section>
    );
  }
  const [x0, y0, x1, y1] = section?.bbox ?? [0, 0, 0, 0];
  return (
    <section className="panel painting-panel">
      <h2>The painting</h2>
      <div className="frame-wrap">
        {painting.image && <img src={painting.image} alt={painting.title} />}
        {section && (
          <div
            className="bbox"
            style={{
              left: `${x0 * 100}%`,
              top: `${y0 * 100}%`,
              width: `${(x1 - x0) * 100}%`,
              height: `${(y1 - y0) * 100}%`,
            }}
          />
        )}
      </div>
      <h3>{painting.title}</h3>
      <p className="meta">
        {painting.artist}
        {painting.year ? `, ${painting.year}` : ""}
      </p>
      <ol className="parts">
        {painting.sections.map((s) => (
          <li key={s.number} className={s.number === section?.number ? "current" : undefined}>
            {s.name}
          </li>
        ))}
      </ol>
    </section>
  );
}
```

`screen/src/components/Transcript.tsx`:

```tsx
import { useEffect, useRef } from "react";
import type { Line } from "../types";

export function Transcript({ lines }: { lines: Line[] }) {
  const box = useRef<HTMLDivElement>(null);
  const last = lines[lines.length - 1]?.text;
  useEffect(() => {
    const el = box.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [lines.length, last]);

  return (
    <section className="panel transcript-panel">
      <h2>Conversation</h2>
      <div className="lines" ref={box}>
        {lines.length === 0 && <p className="hint">Say "Show me the Mona Lisa."</p>}
        {lines.map((l, i) => (
          <p key={i} className={`line ${l.role}`}>
            <span className="who">{l.role === "user" ? "Visitor" : "Guide"}</span>
            {l.text}
          </p>
        ))}
      </div>
    </section>
  );
}
```

`screen/src/components/ActivityBar.tsx`:

```tsx
import type { State, Status } from "../types";

const CHIPS: { key: keyof State["activity"]; name: string; job: string }[] = [
  { key: "elevenlabs", name: "ElevenLabs", job: "Voice guide" },
  { key: "gemini", name: "Gemini", job: "Finds the parts, draws each shape" },
  { key: "creao", name: "Creao", job: "Tactile Tour Writer agent" },
  { key: "browser_use", name: "Browser Use", job: "Reads the museum's website" },
];

const WORDS: Record<Status, string> = { idle: "Waiting", working: "Working...", done: "Done", failed: "Failed" };

export function ActivityBar({ activity }: { activity: State["activity"] }) {
  return (
    <footer className="activity">
      {CHIPS.map(({ key, name, job }) => {
        const a = activity[key];
        return (
          <div key={key} className={`chip ${a.status}`}>
            <span className="dot" aria-hidden />
            <div>
              <strong>{name}</strong> <span className="job">{job}</span>
              <p className="detail">{a.detail || WORDS[a.status]}</p>
            </div>
          </div>
        );
      })}
    </footer>
  );
}
```

- [ ] **Step 5: Styles**

`screen/src/styles.css`:

```css
/* Dark gallery look, sized for a projector. System fonts only: the venue Wi-Fi can't break it. */
:root {
  --bg: #0f0e0d;
  --panel: #181715;
  --line: #2c2a27;
  --text: #f4f0e8;
  --muted: #a39d93;
  --accent: #e9b85f;
  --user: #1f3347;
  --agent: #2a251f;
  --ok: #72d08f;
  --work: #e9b85f;
  --fail: #f07070;
  --idle: #625d55;
  color-scheme: dark;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

* { box-sizing: border-box; }
html, body, #root { margin: 0; height: 100%; }
body { background: var(--bg); color: var(--text); font-size: clamp(14px, 1.1vw, 20px); line-height: 1.4; }

.app { height: 100vh; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; gap: 1rem; padding: 1.25rem 1.5rem; }
.top { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
.top h1 { margin: 0; font-size: 1.6rem; }
.tagline { margin: .15rem 0 0; color: var(--muted); }
.pill { padding: .35rem .8rem; border-radius: 999px; border: 1px solid var(--line); font-size: .85rem; font-weight: 600; white-space: nowrap; }
.pill.on { color: var(--ok); }
.pill.off { color: var(--fail); }

.stage { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr) minmax(0, 1fr); gap: 1rem; min-height: 0; }
.panel { display: flex; flex-direction: column; min-height: 0; padding: 1rem 1.25rem; background: var(--panel); border: 1px solid var(--line); border-radius: 16px; }
.panel h2 { margin: 0 0 .5rem; color: var(--muted); font-size: .75rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.empty { justify-content: center; align-items: center; color: var(--muted); text-align: center; }

/* The painting, with the part on the board lit and the rest dimmed */
.frame-wrap { position: relative; width: fit-content; max-width: 100%; margin: 0 auto; overflow: hidden; border-radius: 8px; }
.frame-wrap img { display: block; max-width: 100%; max-height: 46vh; }
.bbox { position: absolute; border: 3px solid var(--accent); border-radius: 4px; box-shadow: 0 0 0 100vmax rgba(0, 0, 0, .55); transition: left .5s ease, top .5s ease, width .5s ease, height .5s ease; }
.painting-panel h3 { margin: .9rem 0 0; font-size: 1.35rem; }
.meta { margin: .1rem 0 .6rem; color: var(--muted); }
.parts { margin: 0; padding-left: 1.4rem; overflow-y: auto; color: var(--muted); }
.parts li.current { color: var(--accent); font-weight: 700; }

/* The 10x10 board */
.board-panel { align-items: center; }
.now { margin: 0 0 .8rem; color: var(--accent); font-size: 1.3rem; font-weight: 700; text-align: center; }
.board {
  width: min(100%, 52vh); aspect-ratio: 1; display: grid;
  grid-template-columns: repeat(10, 1fr); grid-template-rows: repeat(10, 1fr); gap: 2.2%; padding: 4%;
  border-radius: 18px; background: linear-gradient(145deg, #2a2723, #1a1816);
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, .7), 0 10px 30px rgba(0, 0, 0, .5);
}
.pin {
  border-radius: 50%; background: radial-gradient(circle at 50% 45%, #121110, #050505 70%);
  box-shadow: inset 0 3px 5px rgba(0, 0, 0, .9); transform: scale(.78);
  transition: transform .4s cubic-bezier(.34, 1.56, .64, 1), box-shadow .4s ease;
  transition-delay: calc(var(--row) * 70ms);
}
.pin.up {
  background: radial-gradient(circle at 35% 30%, #fff, #e2d7c3 45%, #8e826d 100%);
  transform: scale(1) translateY(-6%);
  box-shadow: 0 6px 10px rgba(0, 0, 0, .65), 0 0 14px rgba(233, 184, 95, .25);
}
.caption { margin: .8rem 0 .3rem; color: var(--muted); font-size: .85rem; text-align: center; }
.frame { max-width: 100%; color: var(--muted); font-size: .7rem; text-align: center; word-break: break-all; opacity: .8; }

/* The conversation */
.lines { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: .6rem; padding-right: .3rem; }
.line { max-width: 92%; margin: 0; padding: .6rem .85rem; border-radius: 12px; }
.line.user { align-self: flex-end; background: var(--user); }
.line.agent { align-self: flex-start; background: var(--agent); }
.who { display: block; margin-bottom: .15rem; color: var(--muted); font-size: .7rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.hint { color: var(--muted); }

/* What each sponsor's piece is doing */
.activity { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; }
.chip { display: flex; align-items: flex-start; gap: .7rem; padding: .7rem .9rem; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; }
.chip .dot { flex: none; width: .7rem; height: .7rem; margin-top: .35rem; border-radius: 50%; background: var(--idle); }
.chip.working .dot { background: var(--work); animation: pulse 1.2s ease-in-out infinite; }
.chip.done .dot { background: var(--ok); }
.chip.failed .dot { background: var(--fail); }
.job { color: var(--muted); font-size: .85rem; }
.detail { margin: .15rem 0 0; font-size: .9rem; }
@keyframes pulse { 50% { opacity: .3; transform: scale(.8); } }

@media (max-width: 900px) {
  .app { height: auto; }
  .stage, .activity { grid-template-columns: 1fr; }
  .board { width: min(100%, 420px); }
}

@media (prefers-reduced-motion: reduce) {
  .pin, .bbox { transition: none; }
  .chip.working .dot { animation: none; }
}
```

- [ ] **Step 6: Build**

Run: `cd screen && npm run build && cd ..`
Expected: `tsc` reports no errors, then Vite prints `✓ built in ...` with `dist/index.html`, one
`dist/assets/index-*.css` (about 4 kB) and one `dist/assets/index-*.js` (about 147 kB).

- [ ] **Step 7: Ignore `node_modules`, commit the source and the build**

Append this line to `.gitignore`:

```text
screen/node_modules/
```

```bash
git add .gitignore screen
git status --short   # must list screen/src, screen/dist, package.json, package-lock.json; no node_modules
git commit -m "screen/: React audience screen (conversation, simulated board, painting, sponsor activity)"
```

---

### Task 4: Report background steps from `paintings.py`, `creao.py` and `museum.py`

**Files:**
- Modify: `paintings.py`, `creao.py`, `museum.py` (Austin's)
- Modify: `test_screen.py` (add one test)

**Interfaces:**
- Consumes: `screen.activity(source, status, detail="", title=None)` from Task 1.
- Produces: no new public functions. Return values and printed lines are unchanged; only `activity`
  calls are added.

Each edit below is an exact find-and-replace: the "find" text occurs exactly once in the file.

- [ ] **Step 1: Write the failing test**

Add to `test_screen.py`, above `if __name__ == "__main__":`:

```python
def test_paintings_report_to_screen():
    import paintings
    reset()
    assert paintings.load_painting("Mona Lisa")["title"] == "Mona Lisa"
    assert screen.snapshot()["activity"]["gemini"] == {"status": "done", "detail": "Mona Lisa: ready from cache"}
    old = paintings.fetch_painting
    def offline(name):
        raise RuntimeError("no Wi-Fi")
    paintings.fetch_painting = offline
    try:
        assert paintings.load_painting("zz no such painting") is None
    finally:
        paintings.fetch_painting = old
    assert screen.snapshot()["activity"]["gemini"]["status"] == "failed"
```

Run: `python test_screen.py`
Expected: 7 `PASS` lines, then `test_paintings_report_to_screen` fails with `AssertionError` (Gemini is
still `idle`).

- [ ] **Step 2: `paintings.py`**

Find:

```python
from google.genai import types
```

Replace with:

```python
from google.genai import types
try:
    from screen import activity  # audience screen; optional
except Exception:  # nothing here depends on the screen
    def activity(*args, **kwargs):
        pass
```

Find (in `load_painting`):

```python
    p = from_cache(name)
    if p:
        return p
    try:
        return fetch_painting(name)
    except Exception as e:  # network stall, Gemini error, bad JSON: the agent says it couldn't find it
        print(f"load_painting failed for {name!r}: {e!r}")
        return None
```

Replace with:

```python
    p = from_cache(name)
    if p:
        activity("gemini", "done", f"{p['title']}: ready from cache")
        return p
    try:
        p = fetch_painting(name)
    except Exception as e:  # network stall, Gemini error, bad JSON: the agent says it couldn't find it
        print(f"load_painting failed for {name!r}: {e!r}")
        p = None
    if p:
        activity("gemini", "done", f"{p['title']}: {len(p['sections'])} parts ready")
    else:
        activity("gemini", "failed", f"Couldn't find {name}")
    return p
```

Find (first line of `fetch_painting`'s body):

```python
    wiki = find_on_wikipedia(name)
```

Replace with:

```python
    activity("gemini", "working", f"Searching Wikipedia for {name}")
    wiki = find_on_wikipedia(name)
```

Find:

```python
    data = analyze(resp.content, mime, wiki["title"], wiki["summary"])
```

Replace with:

```python
    activity("gemini", "working", f"Picking the parts of {wiki['title']}")
    data = analyze(resp.content, mime, wiki["title"], wiki["summary"])
```

Find:

```python
    crops = [jpeg(crop_square(img, s["bbox"])) for s in sections]
```

Replace with:

```python
    crops = [jpeg(crop_square(img, s["bbox"])) for s in sections]
    activity("gemini", "working", f"Drawing {len(sections)} shapes in parallel")
```

- [ ] **Step 3: `creao.py`**

Find:

```python
from paintings import save_painting
```

Replace with:

```python
from paintings import save_painting
try:
    from screen import activity  # audience screen; optional
except Exception:  # nothing here depends on the screen
    def activity(*args, **kwargs):
        pass
```

Find:

```python
    print(f"Creao run started: {run_id} for {p['title']}")
```

Replace with:

```python
    print(f"Creao run started: {run_id} for {p['title']}")
    activity("creao", "working", "Writing guide notes", p["title"])
```

Find:

```python
        p["guide_notes"] = {n["name"]: n["guide_notes"] for n in notes}
        save_painting(p)
```

Replace with:

```python
        p["guide_notes"] = {n["name"]: n["guide_notes"] for n in notes}
        save_painting(p)
        activity("creao", "done", f"{len(notes)} guide notes", p["title"])
    else:
        activity("creao", "failed", f"Run {r.get('status')}", p["title"])
```

Find:

```python
            print(f"Creao failed: {e}")  # never break the tour
```

Replace with:

```python
            print(f"Creao failed: {e}")  # never break the tour
            activity("creao", "failed", "Couldn't run", p.get("title"))
```

- [ ] **Step 4: `museum.py`**

Find:

```python
from creao import parse_json
```

Replace with:

```python
from creao import parse_json
try:
    from screen import activity  # audience screen; optional
except Exception:  # nothing here depends on the screen
    def activity(*args, **kwargs):
        pass
```

Find:

```python
        print(f"Browser Use run started: {run.id} for {p['title']}")
```

Replace with:

```python
        print(f"Browser Use run started: {run.id} for {p['title']}")
        activity("browser_use", "working", "Reading the museum's website", p["title"])
```

Find:

```python
            print(f"Browser Use done: {len(p['museum_facts'])} facts for {p['title']}")
```

Replace with:

```python
            print(f"Browser Use done: {len(p['museum_facts'])} facts for {p['title']}")
            activity("browser_use", "done", f"{len(p['museum_facts'])} facts from the museum's website", p["title"])
```

Find:

```python
            print(f"Browser Use failed: {e}")  # never break the tour
```

Replace with:

```python
            print(f"Browser Use failed: {e}")  # never break the tour
            activity("browser_use", "failed", "No museum facts this time", p.get("title"))
```

- [ ] **Step 5: Run all the tests**

Run: `python test_screen.py && python test_pipeline.py && python test_main.py`
Expected: 8 `PASS` lines from `test_screen.py` (with a `load_painting failed for 'zz no such painting':
RuntimeError('no Wi-Fi')` line, expected), 7 `ok` lines from `test_pipeline.py`, 10 `PASS` lines from
`test_main.py`. Then run `python -c "import creao, museum; print('ok')"`; expected: `ok`.
**Never import or run `prepare_demo.py` here:** it calls the paid Browser Use and Creao APIs as soon as
it is imported.

- [ ] **Step 6: Commit**

```bash
git add paintings.py creao.py museum.py test_screen.py
git commit -m "paintings, creao, museum: report Gemini, Creao and Browser Use progress to the audience screen"
```

---

### Task 5: Mirror the tour from `main.py` (Harvey's file: tell Harvey)

**Files:**
- Modify: `main.py`
- Modify: `test_screen.py` (add three tests)

**Interfaces:**
- Consumes: `start_screen`, `say`, `correct`, `show_on_screen` from Tasks 1-2.
- Produces: `main.on_agent(text)` and `main.on_user(text)`, which print exactly what `main.py` prints
  today (`Agent: ...` / `User: ...`) and also send the line to the screen. Tool return values are
  unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `test_screen.py`, above `if __name__ == "__main__":`:

```python
def fresh_main():
    import main
    main.load_painting = stubs.load_painting
    main.show_grid = lambda grid: None
    main.to_ascii = stubs.to_ascii
    main.start_tour_writer = main.start_museum_facts = lambda p: None  # no paid API calls from tests
    main.state.update(painting=None, index=0)
    return main

def test_main_mirrors_the_board():
    reset()
    m = fresh_main()
    m.open_painting({"name": "Mona Lisa"})
    assert screen.snapshot()["section"]["name"] == "her face"
    m.show_section({"section": "next"})
    assert screen.snapshot()["section"]["name"] == "her hands"

def test_broken_screen_keeps_the_tour():
    reset()
    m = fresh_main()
    lock = screen._lock
    screen._lock = None  # every screen call now fails inside
    try:
        r = m.open_painting({"name": "Mona Lisa"})
        assert r["found"] is True and r["now_showing"].startswith("Now showing section 1 of 3")
        assert m.show_section({"section": "next"})["now_showing"].startswith("Now showing section 2 of 3")
        screen.say("agent", "still fine")
    finally:
        screen._lock = lock

def test_main_without_screen_file():
    # As if screen.py were deleted: main.py, paintings.py, creao.py and museum.py fall back to no-ops.
    code = ("import sys; sys.modules['screen'] = None\n"
            "import main, stubs\n"
            "main.load_painting = stubs.load_painting\n"
            "main.show_grid = lambda g: None\n"
            "main.start_tour_writer = main.start_museum_facts = lambda p: None\n"
            "r = main.open_painting({'name': 'Mona Lisa'})\n"
            "assert r['found'] and main.show_section({'section': 'next'})['now_showing']\n"
            "print('ok')\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and out.stdout.strip().endswith("ok"), out.stderr
```

Run: `python test_screen.py`
Expected: 8 `PASS` lines, then `test_main_mirrors_the_board` fails with
`TypeError: 'NoneType' object is not subscriptable` (the screen never heard about the section).

- [ ] **Step 2: Import the screen with a no-op fallback**

Find:

```python
    def start_museum_facts(p):
        pass
```

Replace with:

```python
    def start_museum_facts(p):
        pass
try:
    from screen import start_screen, say, correct, show_on_screen  # audience screen in the browser
except Exception:  # the tour never depends on the screen
    start_screen = say = correct = show_on_screen = lambda *args, **kwargs: None
```

- [ ] **Step 3: Mirror each section**

Find (in `section_payload`):

```python
    show_grid(s["grid"])  # returns once the balls settle
```

Replace with:

```python
    show_grid(s["grid"])  # returns once the balls settle
    show_on_screen(p, i)  # mirrors the board in the browser; never raises
```

- [ ] **Step 4: Transcript callbacks**

Find:

```python
def build_tools():
```

Replace with:

```python
def on_agent(text):
    print(f"Agent: {text}")
    say("agent", text)

def on_user(text):
    print(f"User: {text}")
    say("user", text)

def build_tools():
```

- [ ] **Step 5: Start the screen and wire the callbacks**

Find (in the `if __name__ == "__main__":` block; note the blank line):

```python
    tools = build_tools()

```

Replace with:

```python
    tools = build_tools()
    start_screen()

```

Find:

```python
        callback_agent_response=lambda r: print(f"Agent: {r}"),
        callback_user_transcript=lambda t: print(f"User: {t}"),
```

Replace with:

```python
        callback_agent_response=on_agent,
        callback_agent_response_correction=correct,
        callback_user_transcript=on_user,
```

- [ ] **Step 6: Run every test**

Run: `python test_screen.py && python test_main.py && python test_pipeline.py`
Expected: 11 `PASS` lines from `test_screen.py`, 10 `PASS` from `test_main.py` (**unmodified**), 7 `ok`
from `test_pipeline.py`. Expected noise in `test_broken_screen_keeps_the_tour`: three lines like
`screen.show_on_screen failed: TypeError(...)` / `screen.say failed: TypeError(...)`.

- [ ] **Step 7: Commit**

```bash
git add main.py test_screen.py
git commit -m "main.py: mirror the tour on the audience screen (never blocks the conversation)"
```

---

### Task 6: Check it in a browser, then docs

**Files:**
- Modify: `CLAUDE.md`, `README.md`

- [ ] **Step 1: Run the no-API demo and look at it**

Run: `python screen.py --demo` (leave it running), then open `http://127.0.0.1:8000` in Chrome.
Expected:
- Header: "Tactile Art Guide" and a green `Live` pill.
- Left: the painting with a gold box on the current part and the rest dimmed; the parts list with the
  current one highlighted.
- Center: "Touch board, simulated", the section name, balls rising one row at a time when the section
  changes, and the `F...` frame line underneath.
- Right: visitor (blue, right) and guide (brown, left) bubbles, auto-scrolling.
- Bottom: four chips. ElevenLabs "In conversation", Gemini "...: ready from cache", Creao "N guide
  notes", Browser Use "N museum facts", all green.
- No errors in the browser console.
Then stop the demo (Ctrl+C) and check the pill turns red, "Waiting for main.py", within a second.

- [ ] **Step 2: Kill-switch check (the tour without the screen)**

Run: `python test_screen.py` and confirm `PASS test_main_without_screen_file`. This proves deleting
`screen.py` leaves the tour working. Optionally also delete `screen/dist/` temporarily, run
`python screen.py --demo`, and check the page shows the "Screen not built" message; then restore it with
`git checkout screen/dist`.

- [ ] **Step 3: `CLAUDE.md`**

Find:

```text
- `board.py`, `send_frame.py`, `sim.py` - Teammate 3. Serial link to the board (+ optional simulation).
```

Replace with:

```text
- `board.py`, `send_frame.py`, `sim.py` - Teammate 3. Serial link to the board (+ optional simulation).
- `screen.py`, `screen/`, `test_screen.py` - Austin. Optional audience screen at http://127.0.0.1:8000:
  the conversation, the board (mirrored or simulated) and what each sponsor's agent is doing. The tour
  never depends on it. `screen/dist/` is built and committed; after UI changes run
  `cd screen && npm install && npm run build`.
```

Find:

```text
- Tests are plain scripts, no pytest: `python test_main.py`, `python test_paintings.py`
```

Replace with:

```text
- Tests are plain scripts, no pytest: `python test_main.py`, `python test_pipeline.py`,
  `python test_screen.py`, `python test_paintings.py` (live, uses Gemini)
- Audience screen: `python main.py` starts it; open http://127.0.0.1:8000. Without any API:
  `python screen.py --demo`
```

- [ ] **Step 4: `README.md`**

Find:

```text
| `stubs.py`, `test_main.py`, `test_paintings.py`, `check.py` | Stubs, tests, and a script that draws each part's box on the painting |
```

Replace with:

```text
| `screen.py`, `screen/` | Audience screen (React + TypeScript) at http://127.0.0.1:8000: the conversation, the board (mirrored, or simulated without hardware), the painting with the current part boxed, and what Gemini, Creao and Browser Use are doing. Optional: the tour runs the same without it |
| `stubs.py`, `test_main.py`, `test_paintings.py`, `check.py` | Stubs, tests, and a script that draws each part's box on the painting |
```

Find:

```text
python main.py          # talk to it; Ctrl+C ends the conversation
```

Replace with:

```text
python main.py          # talk to it; Ctrl+C ends the conversation
                        # audience screen: http://127.0.0.1:8000 (python screen.py --demo runs it without APIs)
```

Find:

```text
Tests: `python test_main.py` and `python test_paintings.py`.
```

Replace with:

```text
Tests: `python test_main.py`, `python test_pipeline.py` and `python test_screen.py` (offline), and
`python test_paintings.py` (live).
```

- [ ] **Step 5: Final regression run and commit**

Run: `python test_main.py && python test_pipeline.py && python test_screen.py && git status --short`
Expected: 10 + 7 + 11 passing, and `git status` shows only `CLAUDE.md` and `README.md` modified (no
`cache/zz-test-painting.*`, no `node_modules`).

```bash
git add CLAUDE.md README.md
git commit -m "docs: audience screen files and commands"
```

Then stop and report to Austin. Don't push or merge.

---

### Task 7: Live rehearsal (a human with a microphone)

Needs `pyaudio` (`pip install pyaudio`; on macOS `brew install portaudio` first) and the `.env` keys.

- [ ] **Step 1:** `python main.py`. The terminal prints `Audience screen: http://127.0.0.1:8000` before
  the conversation starts. Open it on the projector / second screen.
- [ ] **Step 2:** Say "Show me the Mona Lisa". Visitor and guide lines appear; the board and painting box
  change with each section; the terminal shows the same `User:` / `Agent:` lines as before.
- [ ] **Step 3:** Interrupt the guide mid-sentence. Its bubble is trimmed to what it actually said.
- [ ] **Step 4:** Ask for "The Birth of Venus" (not cached). Gemini chip steps through Searching →
  Picking the parts → Drawing N shapes → N parts ready; Creao and Browser Use chips go amber, then green
  when they finish (about 70 s and 40 s).
- [ ] **Step 5:** Close the browser tab and reopen it mid-tour: nothing prints in the terminal, and the
  conversation keeps going.
- [ ] **Step 6:** With another program on port 8000 (e.g. `python -m http.server 8000` in a second
  terminal), start `main.py`: it prints `Audience screen off: ...` and the voice tour works normally.
- [ ] **Step 7:** If all good, tell Harvey about the `main.py` change, then merge
  `feat/audience-screen` into `main` before the 10:00 AM freeze. If anything misbehaves, don't merge:
  `main` is untouched.
