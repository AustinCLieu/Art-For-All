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
_render = {"phase": "idle", "done": 0, "total": 0}  # 10,000-pin reliefs: one global progress bar
_last_error = [""]                      # snapshot runs every 300 ms per tab: print each error once

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

def render(phase, done=0, total=0):
    """Progress of the 10,000-pin reliefs. phase is preparing, rendering, done or idle. Never raises."""
    try:
        entry = {"phase": str(phase), "done": int(done), "total": int(total)}
        with _lock:
            _render.update(entry)
    except Exception as e:
        print(f"screen.render failed: {e!r}")

def _agent_chip(p, source, key, noun):
    a = _activity.get((source, p.get("title")))
    if a:
        return dict(a)
    if p.get(key):  # done earlier (demo paintings) or by a run that has finished
        return {"status": "done", "detail": f"{len(p[key])} {noun}"}
    return dict(IDLE)

def _cache_url(path):
    """/cache/<file>?v=<mtime>, or None: a relief made again under the same name must not come from the browser's cache."""
    if not path:
        return None
    name = os.path.basename(path)
    try:
        return f"/cache/{name}?v={int(os.path.getmtime(os.path.join(CACHE, name)))}"
    except OSError:
        return None

def _views(p, i):
    s = p["sections"][i]
    image = p.get("image")
    painting = {"title": p["title"], "artist": p.get("artist", ""), "year": p.get("year", ""),
                "image": f"/cache/{os.path.basename(image)}" if image else None,
                "sections": [{"number": x["number"], "name": x["name"], "location": x["location"]}
                             for x in p["sections"]]}
    section = {"index": i, "number": s["number"], "name": s["name"], "location": s["location"],
               "bbox": s["bbox"], "grid": s["grid"],
               "relief": _cache_url(s.get("relief")), "relief_color": _cache_url(s.get("relief_color")),
               "frame": "F" + "".join("1" if v else "0" for row in s["grid"] for v in row)}
    return painting, section

def snapshot():
    """Everything the page draws, as JSON-ready data. Never raises."""
    out = {"hardware": os.getenv("BOARD", "sim") == "serial", "transcript": [], "painting": None,
           "section": None, "render": {"phase": "idle", "done": 0, "total": 0},
           "activity": {k: dict(IDLE) for k in ("elevenlabs", "gemini", "creao", "browser_use")}}
    try:
        with _lock:
            p, i = _live["painting"], _live["index"]
            out["render"] = dict(_render)
            out["transcript"] = [dict(line) for line in _transcript]
            out["activity"]["elevenlabs"] = ({"status": "done", "detail": "In conversation"} if _transcript
                                             else {"status": "idle", "detail": "Waiting for the visitor"})
            out["activity"]["gemini"] = dict(_activity.get(("gemini", None), IDLE))
            if isinstance(p, dict):
                out["activity"]["creao"] = _agent_chip(p, "creao", "guide_notes", "guide notes")
                out["activity"]["browser_use"] = _agent_chip(p, "browser_use", "museum_facts", "museum facts")
                out["painting"], out["section"] = _views(p, i)
    except Exception as e:
        if repr(e) != _last_error[0]:
            _last_error[0] = repr(e)
            print(f"screen.snapshot failed: {e!r}")
    return out

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # the terminal belongs to the conversation

    def do_GET(self):
        try:
            path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
            if path == "/api/state":
                self._send(200, json.dumps(snapshot()).encode(), TYPES[".json"])
            elif path.startswith("/cache/"):
                self._file(os.path.join(CACHE, os.path.basename(path)), IMAGES, cache="max-age=3600")
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

    def _file(self, path, allowed=None, cache="no-store"):
        ext = os.path.splitext(path)[1].lower()
        if (allowed and ext not in allowed) or not os.path.isfile(path):
            return self._send(404, b"not found", "text/plain")
        with open(path, "rb") as f:
            self._send(200, f.read(), TYPES.get(ext, "application/octet-stream"), cache)

    def _send(self, code, body, ctype, cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)  # painting images are 1-1.5 MB: fetch them once
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

def demo(port=PORT):
    """Replays a tour of the cached paintings with no API calls, to build and rehearse the page."""
    if not start_screen(port):
        return
    for path in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        with open(path) as f:
            p = json.load(f)
        say("user", f"Show me {p['title']}.")
        activity("gemini", "working", f"Looking up {p['title']}")
        time.sleep(2)
        activity("gemini", "done", f"{p['title']}: ready from cache")
        total = len(p["sections"])
        render("preparing", 0, total)
        time.sleep(1.5)
        for n in range(1, total + 1):
            render("rendering", n, total)
            time.sleep(0.8)
        render("done", total, total)
        for i, s in enumerate(p["sections"]):
            show_on_screen(p, i)
            say("agent", f"Now showing section {i + 1} of {len(p['sections'])}, {s['name']}, "
                         f"at the {s['location']}. {s['description']}")
            time.sleep(6)
            say("user", "I'm ready for the next part.")
    print("Demo finished. The page stays up until Ctrl+C.")
    threading.Event().wait()

if __name__ == "__main__":
    if "--demo" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else PORT
        try:
            demo(port)
        except KeyboardInterrupt:
            pass
    else:
        print("Usage: python screen.py --demo [--port 8001]   (main.py starts the screen by itself)")
