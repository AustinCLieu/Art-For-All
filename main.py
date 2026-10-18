# Env: AGENT_ID, ELEVENLABS_API_KEY, SENTRY_DSN, BOARD, SERIAL_PORT (+ the keys paintings/creao/museum read)
import os, re, signal, json, threading
from dotenv import load_dotenv
import sentry_sdk  # Sentry prize: catches any tool error during the demo
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

load_dotenv()
# Fall back only when the file itself is missing. A missing dependency inside it (google-genai,
# pyserial) must fail loudly, or the demo silently runs on the fake Mona Lisa / print-only board.
try:
    from paintings import load_painting  # Austin
except ModuleNotFoundError as e:
    if e.name != "paintings":
        raise
    from stubs import load_painting
try:
    from board import show_grid, to_ascii  # Teammate 3
except ModuleNotFoundError as e:
    if e.name != "board":
        raise
    from stubs import show_grid, to_ascii
try:
    from creao import start_tour_writer  # Austin: Creao agent writes guide notes in the background
except ImportError as e:  # optional sponsor step: the tour goes on without it
    print(f"Creao off: {e!r}")
    def start_tour_writer(p):
        pass
try:
    from museum import start_museum_facts  # Austin: Browser Use museum facts in the background
except ImportError as e:  # optional sponsor step: the tour goes on without it
    print(f"Browser Use off: {e!r}")
    def start_museum_facts(p):
        pass
try:
    from screen import start_screen, say, correct, show_on_screen  # audience screen in the browser
except Exception:  # the tour never depends on the screen
    start_screen = say = correct = show_on_screen = lambda *args, **kwargs: None
print(f"Paintings: {load_painting.__module__}, board: {show_grid.__module__}")

sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))
state = {"painting": None, "index": 0}
_tour = threading.Lock()  # the SDK runs tools on a thread pool; one board move at a time

def wait_until_flat():
    # The board can only raise pins: a teammate presses it flat and hits Enter before each new shape.
    if os.getenv("BOARD", "sim") == "serial":
        input("Press the board flat, then Enter... ")
_real_wait_until_flat = wait_until_flat  # tests stub wait_until_flat and restore it from here

def section_payload(i):
    p = state["painting"]
    s = p["sections"][i]
    state["index"] = i
    try:
        wait_until_flat()
        show_grid(s["grid"])  # returns once the last pin is up
    except Exception as e:  # a board failure must not end the voice tour
        sentry_sdk.capture_exception(e)
        print(f"Board failed: {e!r}")
    show_on_screen(p, i)  # mirrors the board in the browser; never raises
    lead = "the main subject: " if i == 0 else ""
    return {
        "now_showing": f"Now showing section {i + 1} of {len(p['sections'])}, {lead}{s['name']}, at the {s['location']}.",
        "description": s["description"],
        "shape": to_ascii(s["grid"]),
        "guide_notes": (p.get("guide_notes") or {}).get(s["name"]),  # from Creao, arrives in the background
        "museum_facts": p.get("museum_facts"),                       # from Browser Use, arrives in the background
    }

def open_painting(params):
    p = load_painting(params["name"])  # outside the lock: an uncached lookup can take a while
    if not p:
        return {"found": False}
    with _tour:
        state["painting"] = p
        start_tour_writer(p)  # no-op if the painting already has guide notes
        start_museum_facts(p)  # no-op if the painting already has museum facts
        sections = [{"number": s["number"], "name": s["name"], "location": s["location"]} for s in p["sections"]]
        return {"found": True, "title": p["title"], "artist": p["artist"], "year": p["year"],
                "summary": p["summary"], "sections": sections, **section_payload(0)}

def show_section(params):
    with _tour:
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
            m = re.search(r"-?\d+", want)  # "2", "2.0", "section 2"
            if not m:
                return {"error": "Pass next, previous, or a section number."}
            n = max(0, min(last, int(m.group(0)) - 1))
        return section_payload(n)

def as_tool(fn):
    # ElevenLabs only accepts a string tool result, so send the dict as JSON text.
    # The SDK swallows tool exceptions without logging them, so report them to Sentry here.
    def handler(params):
        try:
            return json.dumps(fn(params))
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise
    return handler

def on_agent(text):
    print(f"Agent: {text}")
    say("agent", text)

def on_user(text):
    print(f"User: {text}")
    say("user", text)

def build_tools():
    tools = ClientTools()
    tools.register("open_painting", as_tool(open_painting))
    tools.register("show_section", as_tool(show_section))
    return tools

def on_ctrl_c(conversation):
    def handler(*_):
        signal.signal(signal.SIGINT, signal.SIG_DFL)  # a second Ctrl+C kills it, even if the board hangs
        conversation.end_session()
    return handler

if __name__ == "__main__":
    tools = build_tools()
    start_screen()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    conversation = Conversation(
        ElevenLabs(api_key=api_key),
        os.getenv("AGENT_ID"),
        requires_auth=bool(api_key),
        audio_interface=DefaultAudioInterface(),
        client_tools=tools,
        callback_agent_response=on_agent,
        callback_agent_response_correction=correct,
        callback_user_transcript=on_user,
    )
    signal.signal(signal.SIGINT, on_ctrl_c(conversation))
    conversation.start_session()
    print(conversation.wait_for_session_end())
