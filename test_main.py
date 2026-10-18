# Run: python test_main.py   (no audio, no network)
import stubs

LOCATIONS = {"top left", "top center", "top right", "center left", "center",
             "center right", "bottom left", "bottom center", "bottom right"}

def test_stub_painting():
    p = stubs.load_painting("Mona Lisa by Leonardo da Vinci")
    assert p["title"] == "Mona Lisa"
    for key in ("artist", "year", "summary", "image", "sections"):
        assert key in p, key
    assert [s["number"] for s in p["sections"]] == [1, 2, 3]
    assert [s["name"] for s in p["sections"]] == ["her face", "her hands", "the landscape"]
    for s in p["sections"]:
        assert s["location"] in LOCATIONS, s["location"]
        assert len(s["bbox"]) == 4
        assert s["description"]
        assert len(s["grid"]) == 10 and all(len(row) == 10 for row in s["grid"]), s["name"]
        assert all(v in (0, 1) for row in s["grid"] for v in row), s["name"]
        assert any(v for row in s["grid"] for v in row), s["name"] + " grid is empty"

def test_stub_not_found():
    assert stubs.load_painting("The Starry Night") is None
    assert stubs.load_painting("asdfgh") is None

def test_to_ascii():
    grid = [[1, 0] * 5] + [[0] * 10] * 9
    lines = stubs.to_ascii(grid).split("\n")
    assert len(lines) == 10
    assert lines[0] == "#.#.#.#.#."
    assert lines[1] == ".........."

def fresh_main():
    import main
    main.load_painting = stubs.load_painting  # don't depend on which paintings.py loaded
    main.show_grid = lambda grid: None        # keep test output quiet
    main.to_ascii = stubs.to_ascii
    main.start_tour_writer = lambda p: None   # never start Creao from tests
    main.start_museum_facts = lambda p: None  # never start Browser Use either (paid, and it saves to cache/)
    main.state.update(painting=None, index=0)
    return main

def test_open_not_found():
    m = fresh_main()
    assert m.open_painting({"name": "A Painting That Does Not Exist"}) == {"found": False}

def test_show_before_open():
    m = fresh_main()
    assert "error" in m.show_section({"section": "next"})

def test_open_mona_lisa():
    m = fresh_main()
    r = m.open_painting({"name": "Mona Lisa by Leonardo da Vinci"})
    assert r["found"] is True
    assert r["title"] == "Mona Lisa" and r["artist"] and r["year"] and r["summary"]
    assert r["sections"][0] == {"number": 1, "name": "her face", "location": "top center"}
    assert all(set(s) == {"number", "name", "location"} for s in r["sections"])  # no grids sent to the LLM
    assert r["now_showing"] == "Now showing section 1 of 3, the main subject: her face, at the top center."
    assert len(r["shape"].split("\n")) == 10
    assert r["description"]
    assert "guide_notes" in r and "museum_facts" in r
    assert m.state["index"] == 0

def test_navigation():
    m = fresh_main()
    m.open_painting({"name": "Mona Lisa"})
    assert m.show_section({"section": "previous"}) == {"now_showing": "This is already the first section."}
    r = m.show_section({"section": "next"})
    assert r["now_showing"] == "Now showing section 2 of 3, her hands, at the bottom center."
    assert set(r) == {"now_showing", "description", "shape", "guide_notes", "museum_facts"}
    assert m.show_section({"section": "Previous "})["now_showing"].startswith("Now showing section 1 of 3")
    assert m.show_section({"section": "3"})["now_showing"].startswith("Now showing section 3 of 3")
    assert m.show_section({"section": "next"}) == {"now_showing": "That was the last section."}
    assert m.state["index"] == 2
    assert m.show_section({"section": "99"})["now_showing"].startswith("Now showing section 3 of 3")
    assert m.show_section({"section": "0"})["now_showing"].startswith("Now showing section 1 of 3")
    assert "error" in m.show_section({"section": "her hands"})
    assert m.show_section({"section": "section 2"})["now_showing"].startswith("Now showing section 2 of 3")
    assert m.show_section({"section": "1.0"})["now_showing"].startswith("Now showing section 1 of 3")

def test_board_failure_keeps_talking():
    # A serial error must cost the touch part only: the agent still gets the words, and Sentry the error.
    m = fresh_main()
    captured = []
    original = m.sentry_sdk.capture_exception
    m.sentry_sdk.capture_exception = captured.append
    def unplugged(grid):
        raise OSError("board unplugged")
    m.show_grid = unplugged
    try:
        r = m.open_painting({"name": "Mona Lisa"})
        assert r["found"] is True and r["description"] and r["shape"]
        assert m.show_section({"section": "next"})["now_showing"].startswith("Now showing section 2 of 3")
    finally:
        m.sentry_sdk.capture_exception = original
    assert [str(e) for e in captured] == ["board unplugged", "board unplugged"]

def test_missing_dependency_is_not_hidden():
    # paintings.py failing on its own import (here: no google-genai) must stop main.py, not swap in the stub.
    import subprocess, sys
    code = ("import sys; sys.modules['google.genai'] = None\n"
            "try:\n    import main\nexcept ImportError:\n    print('raised')\nelse:\n    print(main.load_painting.__module__)\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert out.stdout.strip().endswith("raised"), out.stdout + out.stderr

def test_switch_painting_resets_tour():
    m = fresh_main()
    m.open_painting({"name": "Mona Lisa"})
    m.show_section({"section": "3"})
    m.open_painting({"name": "Mona Lisa"})
    assert m.state["index"] == 0

def test_registered_tools_return_json_text():
    # ElevenLabs rejects a non-string tool result (1008 policy violation), so the
    # registered handlers must return JSON text even though the functions return dicts.
    import asyncio, json
    m = fresh_main()
    tools = m.build_tools()
    out = asyncio.run(tools.handle("open_painting", {"name": "Mona Lisa"}))
    assert isinstance(out, str), type(out)
    assert json.loads(out)["found"] is True
    out = asyncio.run(tools.handle("show_section", {"section": "next"}))
    assert isinstance(out, str), type(out)
    assert json.loads(out)["now_showing"].startswith("Now showing section 2 of 3")

def test_tool_errors_reach_sentry():
    # The ElevenLabs SDK swallows tool exceptions, so main.py must report them itself.
    import asyncio
    m = fresh_main()
    captured = []
    original = m.sentry_sdk.capture_exception
    m.sentry_sdk.capture_exception = captured.append
    def broken_lookup(name):
        raise RuntimeError("wikipedia down")
    m.load_painting = broken_lookup
    try:
        asyncio.run(m.build_tools().handle("open_painting", {"name": "Mona Lisa"}))
        raise AssertionError("the error must still reach ElevenLabs as a tool error")
    except RuntimeError as e:
        assert str(e) == "wikipedia down"
    finally:
        m.sentry_sdk.capture_exception = original
    assert [str(e) for e in captured] == ["wikipedia down"]

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
