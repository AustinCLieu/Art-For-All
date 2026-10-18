# Run: python test_sponsors.py   (offline: Creao and Browser Use are faked, no credits used)
import os, threading, time
import creao, museum

SECTIONS = [{"name": "her face"}, {"name": "her hands"}]

def test_parse_json():
    assert creao.parse_json('Sure! {"sections": [1]} Hope that helps.') == {"sections": [1]}
    assert creao.parse_json("no json here") == {} and creao.parse_json(None) == {}

def test_match_notes():
    notes = [{"name": "Her Face ", "guide_notes": "a"}, {"name": "her hands", "guide_notes": "b"}]
    assert creao.match_notes(notes, SECTIONS) == {"her face": "a", "her hands": "b"}
    renamed = [{"name": "the face", "guide_notes": "a"}, {"name": "the hands", "guide_notes": "b"}]
    assert creao.match_notes(renamed, SECTIONS) == {"her face": "a", "her hands": "b"}  # by order
    assert creao.match_notes(renamed[:1], SECTIONS) == {}

def test_key_only_goes_to_creao():
    sent = []
    class Resp:
        def json(self):
            return {"sections": [{"name": "her face", "guide_notes": "a"}]}
    old = creao.requests.get
    creao.requests.get = lambda url, headers, timeout: sent.append((url, headers)) or Resp()
    try:
        for url in ("https://files.creao.ai/x.json", "https://bucket.s3.amazonaws.com/x.json"):
            run = {"result": {"artifacts": [{"type": "application/json", "url": url}]}}
            assert creao.fetch_notes(run, {"Authorization": "Bearer capi_x"})[0]["guide_notes"] == "a"
    finally:
        creao.requests.get = old
    assert sent[0][1] == {"Authorization": "Bearer capi_x"} and sent[1][1] == {}

def run_twice(module, start, slow_name):
    """Open the same new painting twice while the first run is still going: only one run may start."""
    calls, release = [], threading.Event()
    def slow(p):
        calls.append(p["title"])
        release.wait(5)
        return ["A fact."]
    old_slow, old_save = getattr(module, slow_name), module.save_painting
    setattr(module, slow_name, slow)
    module.save_painting = lambda p: None
    try:
        start({"title": "Zz New Painting", "artist": "X", "sections": SECTIONS})
        start({"title": "Zz New Painting", "artist": "X", "sections": SECTIONS})
        time.sleep(0.2)
        release.set()
        time.sleep(0.2)
    finally:
        setattr(module, slow_name, old_slow)
        module.save_painting = old_save
    return calls

def test_one_creao_run_per_painting():
    env = {k: os.environ.get(k) for k in ("CREAO_AGENT_ID", "CREAO_API_KEY")}
    os.environ.update(CREAO_AGENT_ID="app", CREAO_API_KEY="capi_x")
    try:
        assert run_twice(creao, creao.start_tour_writer, "run_tour_writer") == ["Zz New Painting"]
        assert "Zz New Painting" not in creao._running
    finally:
        for k, v in env.items():
            os.environ.pop(k, None) if v is None else os.environ.update({k: v})

def test_one_browser_use_run_per_painting():
    env = os.environ.get("BROWSER_USE_API_KEY")
    os.environ["BROWSER_USE_API_KEY"] = "bu_x"
    try:
        assert run_twice(museum, museum.start_museum_facts, "museum_facts") == ["Zz New Painting"]
        assert "Zz New Painting" not in museum._running
    finally:
        os.environ.pop("BROWSER_USE_API_KEY") if env is None else os.environ.update(BROWSER_USE_API_KEY=env)

def test_creao_needs_both_keys():
    started = []
    old = creao.run_tour_writer
    creao.run_tour_writer = started.append
    env = {k: os.environ.pop(k, None) for k in ("CREAO_AGENT_ID", "CREAO_API_KEY")}
    os.environ["CREAO_AGENT_ID"] = "app"  # key missing: skip quietly, don't show "failed" on the screen
    try:
        creao.start_tour_writer({"title": "Zz", "sections": SECTIONS})
        time.sleep(0.1)
    finally:
        creao.run_tour_writer = old
        os.environ.pop("CREAO_AGENT_ID")
        os.environ.update({k: v for k, v in env.items() if v is not None})
    assert started == []

def test_browser_use_timeout_cancels_the_run():
    cancelled = []
    class Runs:
        def create(self, task):
            return type("Run", (), {"id": "run1"})()
        def wait_for_completion(self, run_id, timeout):
            raise TimeoutError(f"Run {run_id} did not complete within {timeout}s")
        def cancel(self, run_id):
            cancelled.append(run_id)
    class Client:
        runs = Runs()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
    old = museum.BrowserUse
    museum.BrowserUse = Client
    try:
        museum.museum_facts({"title": "Zz", "artist": "X"})
        raise AssertionError("a timed-out run must raise")
    except TimeoutError:
        pass
    finally:
        museum.BrowserUse = old
    assert cancelled == ["run1"]

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
