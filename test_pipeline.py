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

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
