import re, json
from dotenv import load_dotenv
from browser_use_sdk.v4 import BrowserUse  # pip install browser-use-sdk
from paintings import load_painting, save_painting
from creao import run_tour_writer

load_dotenv()
DEMO = ["Mona Lisa", "The Starry Night", "The Great Wave off Kanagawa", "Girl with a Pearl Earring"]

def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)  # agents sometimes wrap JSON in prose
    return json.loads(m.group(0)) if m else {}

def museum_facts(p):  # Browser Use
    client = BrowserUse()  # reads BROWSER_USE_API_KEY
    run = client.runs.create(f"Find the official museum page for {p['title']} by {p['artist']}. "
                             'Return only JSON: {"facts": ["..."]} with 3-5 facts a guide would point out.')
    return parse_json(client.runs.wait_for_completion(run.id).result).get("facts")

for name in DEMO:
    p = load_painting(name)
    p["museum_facts"] = museum_facts(p)
    save_painting(p)
    if not p.get("guide_notes"):
        run_tour_writer(p)  # Creao; prints the run ID for the Devpost README
    print(p["title"], "done:", len(p["museum_facts"] or []), "facts,", len(p.get("guide_notes") or {}), "notes")
