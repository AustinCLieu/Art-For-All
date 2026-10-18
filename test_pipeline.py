# Offline tests for the two-step painting pipeline. No network or API key needed.
from io import BytesIO
from PIL import Image
import paintings

def test_fix_grid_strings():
    g = paintings.fix_grid(["#.#", "..#"])
    assert len(g) == 10 and all(len(r) == 10 for r in g)
    assert g[0][:4] == [1, 0, 1, 0]
    assert g[1][:4] == [0, 0, 1, 0]
    assert g[2] == [0] * 10

def test_fix_grid_numbers():
    g = paintings.fix_grid([[1, 0, 1]] * 12)
    assert len(g) == 10 and g[9][:3] == [1, 0, 1]

def test_crop_square():
    img = Image.new("RGB", (100, 200))
    c = paintings.crop_square(img, [0.2, 0.1, 0.4, 0.2])  # 20x20 px box at (20, 20)
    assert c.size[0] == c.size[1] == 26  # 20 * (1 + 2 * 0.15)
    tall = paintings.crop_square(img, [0.0, 0.0, 0.1, 0.5])  # 10x100 px box
    assert tall.size[0] == tall.size[1] == 130

def test_jpeg():
    data = paintings.jpeg(Image.new("RGB", (8, 8)))
    assert Image.open(BytesIO(data)).format == "JPEG"

import os

def test_fetch_painting():
    """fetch_painting crops each section, draws them in parallel, drops failures and renumbers."""
    buf = BytesIO()
    Image.new("RGB", (200, 100), "white").save(buf, "PNG")
    image = buf.getvalue()

    class Resp:
        content = image
        headers = {"Content-Type": "image/png"}

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

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
