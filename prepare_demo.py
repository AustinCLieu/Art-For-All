import os
from dotenv import load_dotenv
from browser_use_sdk.v4 import BrowserUse  # pip install browser-use-sdk
from paintings import load_painting, save_painting
from creao import parse_json, run_tour_writer

load_dotenv()
DEMO = ["Mona Lisa", "The Starry Night", "The Great Wave off Kanagawa", "Girl with a Pearl Earring"]

def museum_facts(p):  # Browser Use
    with BrowserUse() as client:  # reads BROWSER_USE_API_KEY
        run = client.runs.create(f"Find the official museum page for {p['title']} by {p['artist']}. "
                                 'Return only JSON: {"facts": ["..."]} with 3-5 facts a guide would point out.')
        done = client.runs.wait_for_completion(run.id)
    facts = parse_json(done.result).get("facts")
    if not facts:
        raise RuntimeError(f"run {run.id} {done.status.value}: {done.error or done.result}")
    return facts

for name in DEMO:
    p = load_painting(name)
    if not p:
        print(name, "not found, skipped")
        continue
    try:
        p["museum_facts"] = museum_facts(p)
        save_painting(p)
    except Exception as e:  # keep the old facts
        print(f"Browser Use failed for {name}: {e}")
    if not p.get("guide_notes"):
        if os.getenv("CREAO_API_KEY") and os.getenv("CREAO_AGENT_ID"):
            try:
                run_tour_writer(p)  # Creao; prints the run ID for the Devpost README
            except Exception as e:
                print(f"Creao failed for {name}: {e}")
        else:
            print("Creao skipped: CREAO_API_KEY / CREAO_AGENT_ID not set")
    print(p["title"], "done:", len(p.get("museum_facts") or []), "facts,", len(p.get("guide_notes") or {}), "notes")
