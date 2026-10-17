import os, re, json, time, threading, requests
from dotenv import load_dotenv
from paintings import save_painting

load_dotenv()
API = "https://developer.creao.ai/v1"  # docs.creao.ai/developer-api: Account API key (cr_sk_...), personal agent runs
MAX_WAIT = 300  # seconds; prepare_demo.py waits on this, so a stuck run can't hang forever

def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)  # agents sometimes wrap JSON in prose
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}

def run_tour_writer(p):
    """Blocking. Runs the Creao agent for painting p, saves its notes into p, returns the run_id."""
    h = {"Authorization": f"Bearer {os.environ['CREAO_API_KEY']}"}
    res = requests.post(f"{API}/runs", headers=h, timeout=30, json={
        "agent_id": os.environ["CREAO_AGENT_ID"],
        # match these input names to what the Developer Console shows for your agent
        "input": {"painting": f"{p['title']} by {p['artist']}",
                  "sections": [s["name"] for s in p["sections"]]}})
    res.raise_for_status()  # 202 on success; 401 bad key, 402 no credits, 404 agent not found
    run_id = res.json()["run_id"]
    print(f"Creao run started: {run_id} for {p['title']}")
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        time.sleep(3)
        try:
            r = requests.get(f"{API}/runs/{run_id}", headers=h, timeout=30).json()
        except (requests.RequestException, ValueError):
            continue  # flaky Wi-Fi: try again next poll
        if r.get("status") in ("completed", "failed", "cancelled"):  # else pending / running
            break
    else:
        r = {"status": "timed out"}
    notes = parse_json((r.get("result") or {}).get("text")).get("sections", [])
    if r.get("status") == "completed" and notes:
        p["guide_notes"] = {n["name"]: n["guide_notes"] for n in notes}
        save_painting(p)
    err = (r.get("error") or {}).get("code", "")
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
