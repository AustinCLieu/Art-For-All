# 10,000-pin simulation: a 100x100 heightmap of each section for the audience screen's 3D pin bed.
# The real board stays 10x10 up/down (`grid`); this shows what a denser board with height levels could do.
# Optional by design: a failure here never stops a painting from loading.
import threading
import numpy as np
from PIL import Image, ImageFilter

SIZE = 100    # pins per side
FLOOR = 0.1   # lowest pin inside the painting, so the part reads apart from the letterbox bars at 0
DETAIL = 0.2  # share of the height from brushwork and edges; the rest is the depth model's shape
PAD = 0.05    # same padding around the bbox as the 10x10 crop
MODEL = "depth-anything/Depth-Anything-V2-Small-hf"  # Apache-2.0, ~100 MB, downloaded once on first use
_pipe, _pipe_lock = None, threading.Lock()

def _model():
    """The depth model, loaded once (~9 s), or False without it. Call with _pipe_lock held."""
    global _pipe
    if _pipe is None:
        try:
            from transformers import pipeline
            _pipe = pipeline("depth-estimation", model=MODEL, device="cpu")
        except Exception as e:  # not installed, or no Wi-Fi for the first download
            print(f"Depth model off, reliefs use brightness: {e!r}")
            _pipe = False
    return _pipe

def warm():
    """Load the depth model ahead of the first relief. Never raises."""
    with _pipe_lock:
        _model()

def _depth(img):
    """How near each pixel looks (brighter = nearer) as an L image, or None without the model."""
    with _pipe_lock:  # one model for every thread
        pipe = _model()
        return pipe(img)["depth"] if pipe else None

def _crop(img, bbox):
    w, h = img.size
    x0, x1 = sorted((bbox[0] * w, bbox[2] * w))
    y0, y1 = sorted((bbox[1] * h, bbox[3] * h))
    px, py = (x1 - x0) * PAD, (y1 - y0) * PAD
    box = [max(0, round(x0 - px)), max(0, round(y0 - py)), min(w, round(x1 + px)), min(h, round(y1 + py))]
    box[2], box[3] = max(box[2], box[0] + 1), max(box[3], box[1] + 1)
    return img.crop(box).convert("RGB")

def _spread(a, lo=2, hi=98):
    """Stretch a to 0..1 between its lo and hi percentiles, so every part uses the full height."""
    a0, a1 = np.percentile(a, [lo, hi])
    return np.clip((a - a0) / max(a1 - a0, 1e-6), 0, 1)

def _square(part, mode, fill):
    """Fit part inside SIZE x SIZE without stretching, centered on fill: the same letterbox as the grid."""
    scale = SIZE / max(part.size)
    fit = part.resize((max(1, round(part.width * scale)), max(1, round(part.height * scale))), Image.Resampling.BOX)
    out = Image.new(mode, (SIZE, SIZE), fill)
    out.paste(fit, ((SIZE - fit.width) // 2, (SIZE - fit.height) // 2))
    return out

def heightmap(img, bbox):
    """(height, color) for the bbox of img: height is an L image, 0 = pin down, 255 = fully up;
    color is the painting under each pin, black in the bars."""
    part = _crop(img, bbox)
    gray = part.convert("L")
    depth = _depth(part)
    pin = max(part.size) / SIZE  # pixels per pin
    blur = lambda r: np.asarray(gray.filter(ImageFilter.GaussianBlur(max(0.5, r * pin))), float)
    shape = np.asarray(depth.resize(part.size), float) if depth else blur(6)
    detail = blur(0.7) - blur(3)  # edges and brushwork a few pins wide; finer craquelure would read as noise
    detail /= max(np.percentile(np.abs(detail), 98), 1e-6)
    h = np.clip((1 - DETAIL) * _spread(shape) + DETAIL * detail, 0, 1)
    h = Image.fromarray((FLOOR + (1 - FLOOR) * h).astype(np.float32), "F")
    height = _square(h, "F", 0).point(lambda v: v * 255).convert("L")
    return height, _square(part, "RGB", (0, 0, 0))

def make_all(img, sections):
    """(height, color) or None for every section, in order. Never raises."""
    out = []
    for s in sections:
        try:
            out.append(heightmap(img, s["bbox"]))
        except Exception as e:
            print(f"relief failed for {s.get('name')!r}: {e!r}")
            out.append(None)
    return out

def save(maps, stem):
    """Writes <stem>-relief.png and <stem>-relief-color.png; returns the section keys that point to them."""
    height, color = maps
    keys = {"relief": f"{stem}-relief.png", "relief_color": f"{stem}-relief-color.png"}
    height.save(keys["relief"])
    color.save(keys["relief_color"])
    return keys

if __name__ == "__main__":  # python relief.py [--force]: heightmaps for every cached painting that lacks them
    import glob, json, sys, time
    from paintings import add_reliefs
    for path in sorted(glob.glob("cache/*.json")):
        with open(path) as f:
            p = json.load(f)
        start = time.time()
        add_reliefs(p, force="--force" in sys.argv)
        done = sum(1 for s in p["sections"] if s.get("relief"))
        print(f"{p['title']}: {done}/{len(p['sections'])} reliefs ({time.time() - start:.1f}s)")
