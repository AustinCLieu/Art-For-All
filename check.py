import glob, json
from PIL import Image, ImageDraw  # pip install pillow

for path in glob.glob("cache/*.json"):
    with open(path) as f:
        p = json.load(f)
    img = Image.open(p["image"]).convert("RGB")
    w, h = img.size
    d = ImageDraw.Draw(img)
    for s in p["sections"]:
        x0, y0, x1, y1 = s["bbox"]
        d.rectangle([x0 * w, y0 * h, x1 * w, y1 * h], outline=(255, 0, 0), width=max(2, w // 300))
        d.text((x0 * w + 6, y0 * h + 6), f"{s['number']}. {s['name']}", fill=(255, 255, 0),
               font_size=max(14, w // 40))
    out = path[:-5] + "_check.png"
    img.save(out)
    print("saved", out)
