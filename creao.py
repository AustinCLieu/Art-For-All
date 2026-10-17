import os, re, json, time, threading, requests
from dotenv import load_dotenv
from paintings import save_painting

load_dotenv()
API = "https://agent.creao.ai/api/v1/apps"  # docs.creao.ai/pro/api-trigger: agent key (capi_...), uses the agent account's credits
MAX_WAIT = 300  # seconds; prepare_demo.py waits on this, so a stuck run can't hang forever

def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)  # agents sometimes wrap JSON in prose
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}

def fetch_notes(r, h):
    """The agent saves its JSON as a file (artifact); fall back to the reply text."""
    res = r.get("result") or {}
    for a in res.get("artifacts") or []:
        if a.get("type") == "application/json":
            try:
                notes = requests.get(a["url"], headers=h, timeout=30).json().get("sections")
            except (requests.RequestException, ValueError, AttributeError):
                continue
            if isinstance(notes, list):
                return notes
    notes = parse_json(res.get("text")).get("sections")
    return notes if isinstance(notes, list) else []

def run_tour_writer(p):
    """Blocking. Runs the Creao agent for painting p, saves its notes into p, returns the run_id."""
    h = {"Authorization": f"Bearer {os.environ['CREAO_API_KEY']}"}
    runs = f"{API}/{os.environ['CREAO_AGENT_ID']}/runs"  # CREAO_AGENT_ID holds the agent's app ID
    res = requests.post(runs, headers=h, timeout=30, json={
        "inputs": {"painting": f"{p['title']} by {p['artist']}",
                   "sections": [s["name"] for s in p["sections"]]}})
    res.raise_for_status()  # 401 bad key, 402 no credits, 404 wrong app ID
    run_id = res.json()["id"]
    print(f"Creao run started: {run_id} for {p['title']}")
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        time.sleep(3)
        try:
            r = requests.get(f"{runs}/{run_id}", headers=h, timeout=30).json()
        except (requests.RequestException, ValueError):
            continue  # flaky Wi-Fi: try again next poll
        if r.get("status") in ("completed", "failed", "cancelled"):  # else pending / running
            break
    else:
        r = {"status": "timed out"}
    notes = [n for n in fetch_notes(r, h) if isinstance(n, dict) and "name" in n and "guide_notes" in n]
    if r.get("status") == "completed" and notes:
        p["guide_notes"] = {n["name"]: n["guide_notes"] for n in notes}
        save_painting(p)
    err = r.get("errorCode") or ""
    print(f"Creao run {r.get('status')}: {run_id} ({len(notes)} notes) {err}".rstrip())
    return run_id

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
