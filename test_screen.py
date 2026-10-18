# Run: python test_screen.py   (no audio, no network, no API keys)
import copy, json, os, subprocess, sys, tempfile, urllib.request, urllib.error
import screen, stubs

def reset():
    with screen._lock:
        screen._transcript.clear()
        screen._activity.clear()
        screen._live.update(painting=None, index=0)
        screen._render.update(phase="idle", done=0, total=0)

def mona():
    return copy.deepcopy(stubs.MONA_LISA)

def test_empty_snapshot():
    reset()
    s = screen.snapshot()
    assert s["painting"] is None and s["section"] is None and s["transcript"] == []
    assert set(s["activity"]) == {"elevenlabs", "gemini", "creao", "browser_use"}
    assert all(a["status"] == "idle" for a in s["activity"].values())
    assert s["render"] == {"phase": "idle", "done": 0, "total": 0}
    json.dumps(s)

def test_say_and_correct():
    reset()
    screen.say("user", "Show me the Mona Lisa")
    screen.say("agent", "One moment while I find it. Here she is.")
    screen.correct("One moment while I find it. Here she is.", "One moment while I find it.")
    screen.correct("text that was never said", "ignored")
    assert screen.snapshot()["transcript"] == [
        {"role": "user", "text": "Show me the Mona Lisa"},
        {"role": "agent", "text": "One moment while I find it."}]
    assert screen.snapshot()["activity"]["elevenlabs"]["status"] == "done"
    for n in range(60):
        screen.say("user", str(n))
    lines = screen.snapshot()["transcript"]
    assert len(lines) == 50 and lines[-1]["text"] == "59"

def test_show_on_screen():
    reset()
    screen.show_on_screen(mona(), 1)
    s = screen.snapshot()
    assert s["painting"]["title"] == "Mona Lisa" and s["painting"]["image"] == "/cache/mona-lisa.jpg"
    assert all(set(x) == {"number", "name", "location"} for x in s["painting"]["sections"])
    sec = s["section"]
    assert sec["number"] == 2 and sec["name"] == "her hands" and sec["location"] == "bottom center"
    assert len(sec["grid"]) == 10 and sec["bbox"] == [0.30, 0.70, 0.75, 0.92]
    assert sec["frame"][0] == "F" and len(sec["frame"]) == 101 and set(sec["frame"][1:]) <= {"0", "1"}
    assert sec["frame"][1:11] == "0000000000" and sec["frame"][21:31] == "0011110000"
    assert sec["relief"] is None and sec["relief_color"] is None  # the stub has no 10,000-pin reliefs

def test_relief_urls():
    reset()
    p = mona()
    p["sections"][0].update(relief="cache/mona-lisa.jpg", relief_color="cache/missing.png")
    screen.show_on_screen(p, 0)
    sec = screen.snapshot()["section"]
    assert sec["relief"].startswith("/cache/mona-lisa.jpg?v=")  # versioned: a remade relief skips the browser cache
    assert sec["relief_color"] is None  # a missing file is no relief, not a broken image

def test_agent_chips():
    reset()
    p = mona()
    screen.show_on_screen(p, 0)
    a = screen.snapshot()["activity"]
    assert a["creao"]["status"] == "idle" and a["browser_use"]["status"] == "idle"
    screen.activity("creao", "working", "Writing guide notes", "Mona Lisa")
    screen.activity("browser_use", "failed", "No museum facts this time", "Some Other Painting")
    a = screen.snapshot()["activity"]
    assert a["creao"] == {"status": "working", "detail": "Writing guide notes"}
    assert a["browser_use"]["status"] == "idle"  # that run was for another painting
    p["museum_facts"] = ["one", "two"]  # Browser Use fills in the same dict main.py holds
    assert screen.snapshot()["activity"]["browser_use"] == {"status": "done", "detail": "2 museum facts"}
    screen.activity("gemini", "working", "Searching Wikipedia for X")
    assert screen.snapshot()["activity"]["gemini"]["status"] == "working"

def test_render_progress():
    reset()
    assert screen.snapshot()["render"] == {"phase": "idle", "done": 0, "total": 0}
    screen.render("preparing", 0, 4)
    assert screen.snapshot()["render"] == {"phase": "preparing", "done": 0, "total": 4}
    screen.render("rendering", 2, 4)
    assert screen.snapshot()["render"] == {"phase": "rendering", "done": 2, "total": 4}
    screen.render("done", 4, 4)
    assert screen.snapshot()["render"] == {"phase": "done", "done": 4, "total": 4}

def test_never_raises():
    reset()
    class Bad:
        def __str__(self):
            raise RuntimeError("bad text")
    screen.say("agent", Bad())
    screen.say("agent", "fine")
    screen.correct("fine", Bad())
    screen.activity("creao", "working", Bad(), "Mona Lisa")
    screen.render("rendering", "not a number", 4)  # int("not a number") raises inside, must be swallowed
    screen.show_on_screen({"sections": []}, 5)  # a broken painting
    s = screen.snapshot()
    assert s["painting"] is None and s["section"] is None
    json.dumps(s)
    screen.show_on_screen(None, 0)

def test_snapshot_error_prints_once():
    import contextlib, io
    reset()
    screen.show_on_screen({"title": "Broken", "sections": [{"number": 1, "name": "x", "location": "center"}]}, 0)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for _ in range(5):
            assert screen.snapshot()["painting"] is None
    assert out.getvalue().count("screen.snapshot failed") <= 1, out.getvalue()
    reset()

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.headers["Content-Type"], r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers["Content-Type"], e.read()

def test_http():
    reset()
    screen.show_on_screen(mona(), 0)
    old = screen.DIST
    with tempfile.TemporaryDirectory() as dist:
        os.makedirs(os.path.join(dist, "assets"))
        with open(os.path.join(dist, "index.html"), "w") as f:
            f.write("<div id=root></div>")
        with open(os.path.join(dist, "assets", "app.js"), "w") as f:
            f.write("console.log(1)")
        screen.DIST = dist
        try:
            url = screen.start_screen(port=0)
            code, ctype, body = get(url + "/api/state")
            assert code == 200 and ctype == "application/json"
            assert json.loads(body)["section"]["name"] == "her face"
            assert get(url + "/")[:2] == (200, "text/html; charset=utf-8")
            assert get(url + "/assets/app.js")[1] == "text/javascript"
            assert get(url + "/some/page")[2] == b"<div id=root></div>"  # single-page app fallback
            code, ctype, _ = get(url + "/cache/mona-lisa.jpg")
            assert code == 200 and ctype == "image/jpeg"
            with urllib.request.urlopen(url + "/cache/mona-lisa.jpg", timeout=5) as r:
                assert r.headers["Cache-Control"] == "max-age=3600" and r.read()
            with urllib.request.urlopen(url + "/api/state", timeout=5) as r:
                assert r.headers["Cache-Control"] == "no-store" and r.read()
            assert get(url + "/cache/mona-lisa.json")[0] == 404  # images only
            assert get(url + "/cache/..%2F.env")[0] == 404
            assert get(url + "/..%2F.env")[2] == b"<div id=root></div>"  # never serves outside dist
            screen.DIST = os.path.join(dist, "missing")
            assert get(url + "/")[0] == 503  # not built yet: a message, not a crash
        finally:
            screen.DIST = old

def test_port_in_use():
    url = screen.start_screen(port=0)
    port = int(url.rsplit(":", 1)[1])
    assert screen.start_screen(port=port) is None  # prints "Audience screen off"; the tour goes on

def test_paintings_report_to_screen():
    import paintings
    reset()
    old = paintings.fetch_painting, paintings.start_reliefs
    paintings.start_reliefs = lambda p: None  # never write reliefs into cache/ from a test
    def offline(name):
        raise RuntimeError("no Wi-Fi")
    try:
        assert paintings.load_painting("Mona Lisa")["title"] == "Mona Lisa"
        assert screen.snapshot()["activity"]["gemini"] == {"status": "done", "detail": "Mona Lisa: ready from cache"}
        paintings.fetch_painting = offline
        assert paintings.load_painting("zz no such painting") is None
    finally:
        paintings.fetch_painting, paintings.start_reliefs = old
    assert screen.snapshot()["activity"]["gemini"]["status"] == "failed"

def fresh_main():
    import main
    main.load_painting = stubs.load_painting
    main.show_grid = lambda grid: None
    main.to_ascii = stubs.to_ascii
    main.start_tour_writer = main.start_museum_facts = lambda p: None  # no paid API calls from tests
    main.state.update(painting=None, index=0)
    return main

def test_main_mirrors_the_board():
    reset()
    m = fresh_main()
    m.open_painting({"name": "Mona Lisa"})
    assert screen.snapshot()["section"]["name"] == "her face"
    m.show_section({"section": "next"})
    assert screen.snapshot()["section"]["name"] == "her hands"

def test_broken_screen_keeps_the_tour():
    reset()
    m = fresh_main()
    lock = screen._lock
    screen._lock = None  # every screen call now fails inside
    try:
        r = m.open_painting({"name": "Mona Lisa"})
        assert r["found"] is True and r["now_showing"].startswith("Now showing section 1 of 3")
        assert m.show_section({"section": "next"})["now_showing"].startswith("Now showing section 2 of 3")
        screen.say("agent", "still fine")
    finally:
        screen._lock = lock

def test_main_without_screen_file():
    # As if screen.py were deleted: main.py, paintings.py, creao.py and museum.py fall back to no-ops.
    code = ("import sys; sys.modules['screen'] = None\n"
            "import main, stubs\n"
            "main.load_painting = stubs.load_painting\n"
            "main.show_grid = lambda g: None\n"
            "main.start_tour_writer = main.start_museum_facts = lambda p: None\n"
            "r = main.open_painting({'name': 'Mona Lisa'})\n"
            "assert r['found'] and main.show_section({'section': 'next'})['now_showing']\n"
            "print('ok')\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and out.stdout.strip().endswith("ok"), out.stderr

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
