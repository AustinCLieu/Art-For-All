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
