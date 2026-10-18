import os, time, threading
from dotenv import load_dotenv
from browser_use_sdk.v4 import BrowserUse  # pip install browser-use-sdk
from paintings import save_painting
from creao import parse_json
try:
    from screen import activity  # audience screen; optional
except Exception:  # nothing here depends on the screen
    def activity(*args, **kwargs):
        pass

load_dotenv()
MAX_WAIT = 300  # seconds for one run, all retries included
_running, _running_lock = set(), threading.Lock()  # titles with a run in progress: one paid run each

def museum_facts(p):
    """Blocking. Browser Use finds the painting's museum page and returns 3-5 facts, or raises."""
    with BrowserUse() as client:  # reads BROWSER_USE_API_KEY
        run = client.runs.create(f"Find the official museum page for {p['title']} by {p['artist']}. "
                                 'Return only JSON: {"facts": ["..."]} with 3-5 facts a guide would point out, '
                                 'as plain sentences to be read aloud (no links, no markdown).')
        print(f"Browser Use run started: {run.id} for {p['title']}")
        deadline = time.monotonic() + MAX_WAIT
        for attempt in range(3):  # flaky Wi-Fi: a dropped poll shouldn't lose the run
            try:
                done = client.runs.wait_for_completion(run.id, timeout=max(1, deadline - time.monotonic()))
                break
            except TimeoutError:  # out of time: stop paying for it
                try:
                    client.runs.cancel(run.id)
                except Exception as e:
                    print(f"Browser Use cancel failed for {run.id}: {e!r}")
                raise
            except Exception as e:
                if attempt == 2 or time.monotonic() >= deadline:
                    raise
                print(f"Browser Use poll failed ({e}), retrying")
    facts = parse_json(done.result).get("facts")
    if not (facts and isinstance(facts, list) and all(isinstance(f, str) for f in facts)):
        raise RuntimeError(f"run {run.id} {done.status.value}: {done.error or done.result}")
    return facts

def start_museum_facts(p):
    """Non-blocking. Fetches museum facts in the background unless p already has them."""
    if p.get("museum_facts") or not os.getenv("BROWSER_USE_API_KEY"):
        return
    with _running_lock:  # reopening the same new painting must not start a second paid run
        if p["title"] in _running:
            return
        _running.add(p["title"])
    def safe():
        try:
            try:
                activity("browser_use", "working", "Reading the museum's website", p["title"])
                p["museum_facts"] = museum_facts(p)  # same dict main.py holds, so later parts see the facts
                print(f"Browser Use done: {len(p['museum_facts'])} facts for {p['title']}")
                activity("browser_use", "done", f"{len(p['museum_facts'])} facts from the museum's website", p["title"])
            except Exception as e:
                print(f"Browser Use failed: {e}")  # never break the tour
                activity("browser_use", "failed", "No museum facts this time", p.get("title"))
                return
            try:
                save_painting(p)  # the tour already has the facts; this only keeps them for next time
            except Exception as e:
                print(f"Browser Use facts not saved: {e!r}")
        finally:
            with _running_lock:
                _running.discard(p["title"])
    threading.Thread(target=safe, daemon=True).start()
