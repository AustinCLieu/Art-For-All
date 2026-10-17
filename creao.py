import os, re, json, time, threading, requests
from dotenv import load_dotenv
from paintings import save_painting

load_dotenv()
API = "https://developer.creao.ai/v1"

def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)  # agents sometimes wrap JSON in prose
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}

def run_tour_writer(p):
    """Blocking. Runs the Creao agent for painting p, saves its notes into p, returns the run_id."""
    h = {"Authorization": f"Bearer {os.environ['CREAO_API_KEY']}"}
    run = requests.post(f"{API}/runs", headers=h, json={
        "agent_id": os.environ["CREAO_AGENT_ID"],
        # match these input names to what the Developer Console shows for your agent
        "input": {"painting": f"{p['title']} by {p['artist']}",
                  "sections": [s["name"] for s in p["sections"]]}}).json()
    print(f"Creao run started: {run['run_id']} for {p['title']}")
    while True:
        r = requests.get(f"{API}/runs/{run['run_id']}", headers=h).json()
        if r["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(3)
    notes = parse_json((r.get("result") or {}).get("text")).get("sections", [])
    if notes:
        p["guide_notes"] = {n["name"]: n["guide_notes"] for n in notes}
        save_painting(p)
    print(f"Creao run {r['status']}: {run['run_id']} ({len(notes)} notes)")
    return run["run_id"]

def start_tour_writer(p):
    """Non-blocking. Starts the Creao agent in the background unless p already has notes."""
    if p.get("guide_notes") or not os.getenv("CREAO_AGENT_ID"):
        return
    def safe():
        try:
            run_tour_writer(p)  # writes into the same dict main.py holds, so later parts see the notes
        except Exception as e:
            print(f"Creao failed: {e}")  # never break the tour
    threading.Thread(target=safe, daemon=True).start()
