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

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
