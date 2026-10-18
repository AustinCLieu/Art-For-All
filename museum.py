import os, threading
from dotenv import load_dotenv
from browser_use_sdk.v4 import BrowserUse  # pip install browser-use-sdk
from paintings import save_painting
from creao import parse_json

load_dotenv()

def museum_facts(p):
    """Blocking. Browser Use finds the painting's museum page and returns 3-5 facts, or raises."""
    with BrowserUse() as client:  # reads BROWSER_USE_API_KEY
        run = client.runs.create(f"Find the official museum page for {p['title']} by {p['artist']}. "
                                 'Return only JSON: {"facts": ["..."]} with 3-5 facts a guide would point out, '
                                 'as plain sentences to be read aloud (no links).')
        print(f"Browser Use run started: {run.id} for {p['title']}")
        for attempt in range(3):  # flaky Wi-Fi: a dropped poll shouldn't lose the run
            try:
                done = client.runs.wait_for_completion(run.id, timeout=600)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                print(f"Browser Use poll failed ({e}), retrying")
    facts = parse_json(done.result).get("facts")
    if not facts:
        raise RuntimeError(f"run {run.id} {done.status.value}: {done.error or done.result}")
    return facts

def start_museum_facts(p):
    """Non-blocking. Fetches museum facts in the background unless p already has them."""
    if p.get("museum_facts") or not os.getenv("BROWSER_USE_API_KEY"):
        return
    def safe():
        try:
            p["museum_facts"] = museum_facts(p)  # same dict main.py holds, so later parts see the facts
            save_painting(p)
            print(f"Browser Use done: {len(p['museum_facts'])} facts for {p['title']}")
        except Exception as e:
            print(f"Browser Use failed: {e}")  # never break the tour
    threading.Thread(target=safe, daemon=True).start()
