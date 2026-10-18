# Offline tests for the two-step painting pipeline. No network or API key needed.
import glob, json, os
from io import BytesIO
from PIL import Image
import paintings

DEMO = ["Mona Lisa", "The Starry Night", "The Great Wave off Kanagawa", "Girl with a Pearl Earring"]
OUTLINE = ["...####...", ".##....##.", "#........#", "#.##..##.#", "#........#",
           "#...##...#", "#........#", "#..####..#", ".#......#.", "..######.."]  # the prompt's face
CYPRESS = ["....#.....", "....##....", "...###....", "...###....", "..#####...",
           ".######...", ".#######..", ".#######..", "#########.", "##########"]  # an old cached blob
BLOB = ["##########"] * 10
TINY = ["..####...."]

def test_fix_grid_strings():
    g = paintings.fix_grid(["#.#", "..#"])
    assert len(g) == 10 and all(len(r) == 10 for r in g)
    assert g[0][:4] == [1, 0, 1, 0]
    assert g[1][:4] == [0, 0, 1, 0]
    assert g[2] == [0] * 10

def test_fix_grid_numbers():
    g = paintings.fix_grid([[1, 0, 1]] * 12)
    assert len(g) == 10 and g[9][:3] == [1, 0, 1]

def test_grid_problems():
    g = paintings.fix_grid
    assert paintings.grid_problems(g(OUTLINE)) == []
    assert paintings.grid_problems(g(CYPRESS)) == ["solid block"]
    assert paintings.grid_problems(g(BLOB)) == ["too many balls", "solid block"]
    assert paintings.grid_problems(g(TINY)) == ["too few balls", "too small"]
    assert paintings.grid_problems(g([])) == ["empty"]

def test_crop_square():
    img = Image.new("RGB", (100, 200), "red")
    c = paintings.crop_square(img, [0.2, 0.1, 0.4, 0.2])  # 20x20 px box at (20, 20)
    assert c.size == (22, 22)  # 20 * (1 + 2 * 0.05)
    tall = paintings.crop_square(img, [0.0, 0.0, 0.1, 0.5])  # 10x100 px box at the image's left edge
    assert tall.size == (105, 105)  # clipped to the image, then letterboxed
    assert tall.getpixel((tall.width // 2, 50)) == (255, 0, 0)  # the part, in the middle
    assert tall.getpixel((tall.width - 1, 50)) == (128, 128, 128)  # gray bar, not more painting

def test_crop_square_degenerate():
    img = Image.new("RGB", (200, 100))
    for bbox in ([0.6, 0.6, 0.4, 0.4], [0.5, 0.5, 0.5001, 0.5001]):  # inverted, sub-pixel
        c = paintings.crop_square(img, bbox)
        assert c.size[0] == c.size[1] and c.size[0] >= 8 and c.mode == "RGB"

def test_grid_prompt_asks_for_only_the_part():
    p = paintings.GRID_PROMPT.format(name="her eyes", title="Mona Lisa", description="d")
    assert "Draw only her eyes" in p and "Gray bars" in p

def test_jpeg():
    data = paintings.jpeg(Image.new("RGB", (8, 8)))
    assert Image.open(BytesIO(data)).format == "JPEG"

def test_fix_grid_one_string():
    g = paintings.fix_grid("#.#\n..#")
    assert g[0][:3] == [1, 0, 1] and g[1][:3] == [0, 0, 1] and len(g) == 10

def test_to_location():
    cells = {(0.1, 0.1): "top left", (0.5, 0.1): "top center", (0.9, 0.1): "top right",
             (0.1, 0.5): "center left", (0.5, 0.5): "center", (0.9, 0.5): "center right",
             (0.1, 0.9): "bottom left", (0.5, 0.9): "bottom center", (0.9, 0.9): "bottom right"}
    for (x, y), want in cells.items():
        assert paintings.to_location([x, y, x, y]) == want, (x, y)

def test_core():
    assert paintings.core("The Starry Night by Van Gogh") == "starry night"
    assert paintings.core("girl with the pearl earring") == paintings.core("Girl with a Pearl Earring")

def test_demo_paintings_load_without_network():
    """The four demo paintings must come from cache/ instantly, even with Wi-Fi and Gemini down."""
    def offline(*a, **k):
        raise AssertionError("network used for a demo painting")
    old = paintings.http.get, paintings.ask_gemini
    paintings.http.get = paintings.ask_gemini = offline
    try:
        for name in DEMO + ["mona lisa by leonardo da vinci", "starry night", "the great wave",
                            "girl with the pearl earring"]:
            p = paintings.load_painting(name)
            assert p and p["sections"], name
        assert paintings.from_cache("") is None
    finally:
        paintings.http.get, paintings.ask_gemini = old

def test_bad_cache_file_is_skipped():
    path = "cache/zz-broken.json"
    with open(path, "w") as f:
        f.write('{"title": "Zz Bro')  # as if a save were cut off half way
    try:
        assert paintings.from_cache("Mona Lisa")["title"] == "Mona Lisa"
    finally:
        os.remove(path)

def test_save_painting_is_atomic():
    p = {"title": "Zz Save Test", "sections": [], "guide_notes": {"a": "b"}}
    try:
        paintings.save_painting(p)
        with open("cache/zz-save-test.json") as f:
            assert json.load(f) == p
        assert not os.path.exists("cache/zz-save-test.json.tmp")
    finally:
        os.remove("cache/zz-save-test.json")

def test_demo_cache_is_valid():
    """The schema in CLAUDE.md, checked on every cached painting."""
    for path in glob.glob("cache/*.json"):
        p = json.load(open(path))
        assert os.path.basename(path) == paintings.slug(p["title"]) + ".json", path
        assert os.path.exists(p["image"]), p["image"]
        assert [s["number"] for s in p["sections"]] == list(range(1, len(p["sections"]) + 1)), path
        for s in p["sections"]:
            x0, y0, x1, y1 = s["bbox"]
            assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, (path, s["name"])
            assert s["location"] == paintings.to_location(s["bbox"]), (path, s["name"])
            assert len(s["grid"]) == 10 and all(len(r) == 10 and set(r) <= {0, 1} for r in s["grid"])
            assert any(map(any, s["grid"])), (path, s["name"])
        assert set(p.get("guide_notes") or {}) <= {s["name"] for s in p["sections"]}, path
        facts = p.get("museum_facts") or []
        assert all(isinstance(f, str) and "*" not in f for f in facts), path

def test_fetch_painting():
    """fetch_painting crops each section, draws them in parallel, drops failures and renumbers."""
    buf = BytesIO()
    Image.new("RGB", (200, 100), "white").save(buf, "PNG")
    image = buf.getvalue()

    class Resp:
        content = image
        headers = {"Content-Type": "image/png"}
        def raise_for_status(self):
            pass

    prompts = []
    def fake_gemini(image_bytes, mime, prompt, thinking):
        prompts.append((mime, thinking, prompt))
        if "This crop is" not in prompt:  # call 1: pick sections
            return {"artist": "Test Artist", "year": "2026", "sections": [
                {"name": "her face", "box_2d": [100, 300, 500, 600], "description": "A face."},
                {"name": "her eye", "box_2d": [200, 350, 260, 420], "description": "An eye."},
                {"name": "the sky", "box_2d": [0, 0, 300, 1000], "description": "Sky."}]}
        if '"her eye"' in prompt:
            raise RuntimeError("Gemini hiccup")  # this section must be dropped
        return {"idea": "an outline", "grid": ["..####....", ".#....#..."]}

    old = paintings.find_on_wikipedia, paintings.http.get, paintings.ask_gemini
    paintings.find_on_wikipedia = lambda name: {"title": "Zz Test Painting", "summary": "S.",
                                                "image_url": "https://example.org/x.png"}
    paintings.http.get = lambda *a, **k: Resp()
    paintings.ask_gemini = fake_gemini
    try:
        p = paintings.fetch_painting("zz test painting")
    finally:
        paintings.find_on_wikipedia, paintings.http.get, paintings.ask_gemini = old
        for ext in ("json", "jpg"):
            if os.path.exists(f"cache/zz-test-painting.{ext}"):
                os.remove(f"cache/zz-test-painting.{ext}")

    assert p["artist"] == "Test Artist" and p["year"] == "2026"
    assert [s["name"] for s in p["sections"]] == ["her face", "the sky"]
    assert [s["number"] for s in p["sections"]] == [1, 2]
    face = p["sections"][0]
    assert list(face) == ["number", "name", "bbox", "location", "description", "grid"]
    assert face["bbox"] == [0.3, 0.1, 0.6, 0.5] and face["location"] == "top center"
    assert face["grid"][0] == [0, 0, 1, 1, 1, 1, 0, 0, 0, 0] and len(face["grid"]) == 10
    first, draws = prompts[0], prompts[1:]
    assert first[0] == "image/png" and first[1] == "low"
    assert len(draws) == 3 and all(m == "image/jpeg" and t == "medium" for m, t, _ in draws)
    assert all("Zz Test Painting" in pr for _, _, pr in draws)

def test_fetch_painting_drops_bad_sections():
    buf = BytesIO()
    Image.new("RGB", (200, 100), "white").save(buf, "PNG")

    class Resp:
        content = buf.getvalue()
        headers = {"Content-Type": "image/png"}
        def raise_for_status(self):
            pass

    def fake_gemini(image_bytes, mime, prompt, thinking):
        if "This crop is" not in prompt:
            return {"sections": [
                {"name": "good", "box_2d": [100, 300, 500, 600], "description": "Good."},
                {"name": "inverted", "box_2d": [500, 600, 100, 300], "description": "Inverted."},
                {"name": "nobox", "description": "No box."},
                {"name": "blank", "box_2d": [0, 0, 300, 1000], "description": "Blank."}]}
        if '"blank"' in prompt:
            return {"grid": ["." * 10] * 10}
        return {"grid": ["..####...."]}

    old = paintings.find_on_wikipedia, paintings.http.get, paintings.ask_gemini
    paintings.find_on_wikipedia = lambda name: {"title": "Zz Test Painting", "summary": "S.",
                                                "image_url": "https://example.org/x.png"}
    paintings.http.get = lambda *a, **k: Resp()
    paintings.ask_gemini = fake_gemini
    try:
        p = paintings.fetch_painting("zz test painting")
    finally:
        paintings.find_on_wikipedia, paintings.http.get, paintings.ask_gemini = old
        for ext in ("json", "jpg"):
            if os.path.exists(f"cache/zz-test-painting.{ext}"):
                os.remove(f"cache/zz-test-painting.{ext}")
    assert [s["name"] for s in p["sections"]] == ["good", "inverted"]
    assert [s["number"] for s in p["sections"]] == [1, 2]
    b = p["sections"][1]["bbox"]
    assert b[0] <= b[2] and b[1] <= b[3]

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
