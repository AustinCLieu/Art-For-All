# Env: AGENT_ID, ELEVENLABS_API_KEY, BOARD, SERIAL_PORT, SENTRY_DSN
import os, signal, json
from dotenv import load_dotenv
import sentry_sdk  # Sentry prize: catches any tool error during the demo
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

load_dotenv()
try:
    from paintings import load_painting  # Austin
except ImportError:
    from stubs import load_painting
try:
    from board import show_grid, to_ascii  # Teammate 3
except ImportError:
    from stubs import show_grid, to_ascii
try:
    from creao import start_tour_writer  # Austin: Creao agent writes guide notes in the background
except ImportError:
    def start_tour_writer(p):
        pass

sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))
state = {"painting": None, "index": 0}

def section_payload(i):
    p = state["painting"]
    s = p["sections"][i]
    state["index"] = i
    show_grid(s["grid"])  # returns once the balls settle
    lead = "the main subject: " if i == 0 else ""
    return {
        "now_showing": f"Now showing section {i + 1} of {len(p['sections'])}, {lead}{s['name']}, at the {s['location']}.",
        "description": s["description"],
        "shape": to_ascii(s["grid"]),
        "guide_notes": (p.get("guide_notes") or {}).get(s["name"]),  # from Creao, demo paintings only
        "museum_facts": p.get("museum_facts"),                       # from Browser Use, demo paintings only
    }

def open_painting(params):
    p = load_painting(params["name"])
    if not p:
        return {"found": False}
    state["painting"] = p
    start_tour_writer(p)  # no-op if the painting already has guide notes
    sections = [{"number": s["number"], "name": s["name"], "location": s["location"]} for s in p["sections"]]
    return {"found": True, "title": p["title"], "artist": p["artist"], "year": p["year"],
            "summary": p["summary"], "sections": sections, **section_payload(0)}

def show_section(params):
    p = state["painting"]
    if not p:
        return {"error": "No painting is open yet."}
    n, last = state["index"], len(p["sections"]) - 1
    want = str(params.get("section", "")).strip().lower()
    if want == "next":
        if n == last:
            return {"now_showing": "That was the last section."}
        n += 1
    elif want == "previous":
        if n == 0:
            return {"now_showing": "This is already the first section."}
        n -= 1
    else:
        try:
            n = max(0, min(last, int(want) - 1))
        except ValueError:
            return {"error": "Pass next, previous, or a section number."}
    return section_payload(n)

def build_tools():
    # ElevenLabs only accepts a string tool result, so send the dicts as JSON text.
    tools = ClientTools()
    tools.register("open_painting", lambda params: json.dumps(open_painting(params)))
    tools.register("show_section", lambda params: json.dumps(show_section(params)))
    return tools

if __name__ == "__main__":
    tools = build_tools()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    conversation = Conversation(
        ElevenLabs(api_key=api_key),
        os.getenv("AGENT_ID"),
        requires_auth=bool(api_key),
        audio_interface=DefaultAudioInterface(),
        client_tools=tools,
        callback_agent_response=lambda r: print(f"Agent: {r}"),
        callback_user_transcript=lambda t: print(f"User: {t}"),
    )
    conversation.start_session()
    signal.signal(signal.SIGINT, lambda *_: conversation.end_session())
    print(conversation.wait_for_session_end())
