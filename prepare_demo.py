import os
from dotenv import load_dotenv
from paintings import load_painting, save_painting
from creao import run_tour_writer
from museum import museum_facts  # Browser Use

load_dotenv()
DEMO = ["Mona Lisa", "The Starry Night", "The Great Wave off Kanagawa", "Girl with a Pearl Earring"]

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
