# Offline tests for the two-step painting pipeline. No network or API key needed.
import glob, json, os, threading, time
from io import BytesIO
from PIL import Image
import paintings, relief

relief._pipe = False  # offline: reliefs come from brightness, the depth model is never loaded
start_reliefs, paintings.start_reliefs = paintings.start_reliefs, lambda p: None  # loads never write reliefs into cache/

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

DEMO_SLUGS = {"mona-lisa", "the-starry-night", "the-great-wave-off-kanagawa", "girl-with-a-pearl-earring"}

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
            if os.path.basename(path)[:-5] in DEMO_SLUGS:  # a live lookup may cache a least-bad grid on purpose
                assert not paintings.grid_problems(s["grid"]), (path, s["name"], paintings.grid_problems(s["grid"]))
            for key in ("relief", "relief_color"):
                if s.get(key) or os.path.basename(path)[:-5] in DEMO_SLUGS:  # every demo part has its 10,000 pins
                    assert os.path.exists(s[key]), (path, s["name"], key)
                    assert Image.open(s[key]).size == (relief.SIZE, relief.SIZE), (path, s["name"], key)
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
        files = sorted(glob.glob("cache/zz-test-painting*"))
        for path in files:
            os.remove(path)

    assert p["artist"] == "Test Artist" and p["year"] == "2026"
    assert [s["name"] for s in p["sections"]] == ["her face", "the sky"]
    assert [s["number"] for s in p["sections"]] == [1, 2]
    face = p["sections"][0]
    assert list(face) == ["number", "name", "bbox", "location", "description", "grid"]  # reliefs come later
    assert [os.path.basename(f) for f in files] == ["zz-test-painting.jpg", "zz-test-painting.json"]
    assert face["bbox"] == [0.3, 0.1, 0.6, 0.5] and face["location"] == "top center"
    assert face["grid"][0] == [0, 0, 1, 1, 1, 1, 0, 0, 0, 0] and len(face["grid"]) == 10
    first, draws = prompts[0], prompts[1:]
    assert first[0] == "image/png" and first[1] == "low"
    # 3 sections x DRAFTS drafts; every draft is too small to pass grid_problems, so no judge call
    assert len(draws) == 3 * paintings.DRAFTS
    assert all(m == "image/jpeg" and t == "minimal" and "This crop is" in pr for m, t, pr in draws)
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
        files = sorted(glob.glob("cache/zz-test-painting*"))
        for path in files:
            os.remove(path)
    assert [s["name"] for s in p["sections"]] == ["good", "inverted"]
    assert [s["number"] for s in p["sections"]] == [1, 2]
    b = p["sections"][1]["bbox"]
    assert b[0] <= b[2] and b[1] <= b[3]

def fake_draws(answers, judge_says=None):
    """A stand-in for ask_gemini: drafts pop from answers (a grid, or an Exception to raise),
    the judge call returns judge_says. Records (prompt, thinking) for every call."""
    calls = []
    def fake(image_bytes, mime, prompt, thinking):
        calls.append((prompt, thinking))
        if "Which drawing" in prompt:
            return judge_says
        a = answers.pop()  # list.pop is atomic, safe from the draft threads
        if isinstance(a, Exception):
            raise a
        return {"idea": "x", "grid": a}
    return fake, calls

def run_draw(fake):
    old, old_drafts = paintings.ask_gemini, paintings.DRAFTS
    paintings.ask_gemini, paintings.DRAFTS = fake, 3
    try:
        return paintings.draw(paintings.jpeg(Image.new("RGB", (50, 50))), "T",
                              {"name": "her face", "description": "A face."})
    finally:
        paintings.ask_gemini, paintings.DRAFTS = old, old_drafts

def test_draw_judges_between_good_drafts():
    fake, calls = fake_draws([OUTLINE, BLOB, OUTLINE[::-1]], {"best": 2})
    g = run_draw(fake)
    assert g in (paintings.fix_grid(OUTLINE), paintings.fix_grid(OUTLINE[::-1]))
    judge = [(p, t) for p, t in calls if "Which drawing" in p]
    assert len(calls) == 3 + 1 and len(judge) == 1
    assert "2 drawings" in judge[0][0] and judge[0][1] == "low"  # the blob never reaches the judge

def test_draw_skips_judge_for_one_good_draft():
    fake, calls = fake_draws([OUTLINE, OUTLINE, BLOB], {"best": 1})  # duplicates count once
    assert run_draw(fake) == paintings.fix_grid(OUTLINE)
    assert len(calls) == 3

def test_draw_keeps_least_bad_when_none_pass():
    fake, calls = fake_draws([BLOB, CYPRESS, TINY])
    assert run_draw(fake) == paintings.fix_grid(CYPRESS)  # 1 problem beats 2
    assert len(calls) == 3

def test_draw_none_when_all_fail():
    fake, _ = fake_draws([RuntimeError("down"), ["." * 10] * 10, RuntimeError("down")])
    assert run_draw(fake) is None

def test_pick():
    crop = paintings.jpeg(Image.new("RGB", (50, 50)))
    a, b = paintings.fix_grid(OUTLINE), paintings.fix_grid(OUTLINE[::-1])
    old = paintings.ask_gemini
    try:
        for says, want in (({"best": 2}, b), ([{"best": 2}], b), ({"best": 7}, a), ({}, a)):
            paintings.ask_gemini = lambda *args, says=says: says
            assert paintings.pick(crop, "T", {"name": "x"}, [a, b]) == want, says
    finally:
        paintings.ask_gemini = old

def test_contact_sheet():
    crop = paintings.jpeg(Image.new("RGB", (50, 80)))
    sheet = Image.open(BytesIO(paintings.contact_sheet(crop, [paintings.fix_grid(OUTLINE)] * 2)))
    assert sheet.format == "JPEG" and sheet.size == (240 + 260 * 2, 240)

def test_redraw():
    os.makedirs("cache", exist_ok=True)
    Image.new("RGB", (100, 100), "white").save("cache/zz-redraw.jpg")
    old_grid = paintings.fix_grid(TINY)
    p = {"title": "Zz Redraw", "artist": "A", "year": "1", "summary": "S.", "image": "cache/zz-redraw.jpg",
         "guide_notes": {"good": "keep me"},
         "sections": [{"number": 1, "name": "good", "bbox": [0.1, 0.1, 0.5, 0.5], "location": "top left",
                       "description": "Good.", "grid": old_grid},
                      {"number": 2, "name": "broken", "bbox": [0.5, 0.5, 0.9, 0.9], "location": "center",
                       "description": "Broken.", "grid": old_grid}]}
    def fake(image_bytes, mime, prompt, thinking):
        if '"broken"' in prompt:
            raise RuntimeError("down")
        return {"grid": OUTLINE}
    old = paintings.ask_gemini
    paintings.ask_gemini = fake
    try:
        paintings.redraw(p)
        saved = json.load(open("cache/zz-redraw.json"))
    finally:
        paintings.ask_gemini = old
        for ext in ("json", "jpg"):
            if os.path.exists(f"cache/zz-redraw.{ext}"):
                os.remove(f"cache/zz-redraw.{ext}")
    assert saved["sections"][0]["grid"] == paintings.fix_grid(OUTLINE)
    assert saved["sections"][1]["grid"] == old_grid  # failed redraw keeps the old grid
    assert saved["guide_notes"] == {"good": "keep me"}

def test_heightmap():
    img = Image.new("RGB", (200, 100), "black")
    img.paste((255, 255, 255), (40, 20, 80, 60))  # a bright square inside a tall box
    height, color = relief.heightmap(img, [0.25, 0.1, 0.35, 0.9])
    assert height.mode == "L" and height.size == (100, 100)
    assert color.mode == "RGB" and color.size == (100, 100)
    assert height.getpixel((0, 50)) == 0 and color.getpixel((0, 50)) == (0, 0, 0)  # letterbox bar: pin down
    assert height.getpixel((50, 50)) >= relief.FLOOR * 255  # inside the painting: at least the floor
    assert max(height.getdata()) > 200  # the part uses the full height
    flat, _ = relief.heightmap(Image.new("RGB", (50, 50), "gray"), [0.5, 0.5, 0.5, 0.5])  # blank, sub-pixel box
    assert flat.size == (100, 100)

def test_make_all_never_raises():
    img = Image.new("RGB", (100, 100))
    maps = relief.make_all(img, [{"name": "good", "bbox": [0.1, 0.1, 0.5, 0.5]}, {"name": "nobox"}])
    assert maps[0] and maps[1] is None

def test_add_reliefs():
    Image.new("RGB", (100, 100), "white").save("cache/zz-relief.jpg")
    p = {"title": "Zz Relief", "image": "cache/zz-relief.jpg",
         "sections": [{"number": 1, "name": "a", "bbox": [0.1, 0.1, 0.5, 0.5]},
                      {"number": 2, "name": "b", "bbox": [0.5, 0.5, 0.9, 0.9], "relief": "keep.png"}]}
    try:
        paintings.add_reliefs(p)
        saved = json.load(open("cache/zz-relief.json"))
        files = sorted(os.path.basename(f) for f in glob.glob("cache/zz-relief*"))
    finally:
        for f in glob.glob("cache/zz-relief*"):
            os.remove(f)
    assert saved["sections"][0]["relief"] == "cache/zz-relief-1-relief.png"
    assert saved["sections"][0]["relief_color"] == "cache/zz-relief-1-relief-color.png"
    assert saved["sections"][1]["relief"] == "keep.png"  # already had one: left alone without force
    assert files == ["zz-relief-1-relief-color.png", "zz-relief-1-relief.png", "zz-relief.jpg", "zz-relief.json"]

def test_start_reliefs():
    """Background, into the same dict, once per painting even if it is opened twice meanwhile."""
    calls, release = [], threading.Event()
    def slow(img, sections):
        calls.append(sections[0]["name"])
        release.wait(5)
        return [(Image.new("L", (100, 100)), Image.new("RGB", (100, 100)))]
    Image.new("RGB", (100, 100), "white").save("cache/zz-start.jpg")
    p = {"title": "Zz Start", "image": "cache/zz-start.jpg",
         "sections": [{"number": 1, "name": "a", "bbox": [0.1, 0.1, 0.5, 0.5]}]}
    old = paintings.make_reliefs
    paintings.make_reliefs = slow
    try:
        start_reliefs(p)
        start_reliefs(p)
        time.sleep(0.2)
        assert "relief" not in p["sections"][0]  # still working: the caller didn't wait
        release.set()
        for _ in range(50):
            if "Zz Start" not in paintings._reliefs_running:
                break
            time.sleep(0.1)
        start_reliefs(p)  # every section has one now: nothing to do
    finally:
        paintings.make_reliefs = old
        for f in glob.glob("cache/zz-start*"):
            os.remove(f)
    assert calls == ["a"]
    assert p["sections"][0]["relief"] == "cache/zz-start-1-relief.png"

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
