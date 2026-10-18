import os, re, json, glob, threading, requests
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types
try:
    from screen import activity  # audience screen; optional
except Exception:  # nothing here depends on the screen
    def activity(*args, **kwargs):
        pass

load_dotenv()
UA = {"User-Agent": "TactileArt/0.1 (LA Hacks hackathon; https://github.com/AustinCLieu/LAHACKSAI_NEED_A_NAME_LMAO)"}  # Wikimedia blocks generic agents
CACHE = "cache"
os.makedirs(CACHE, exist_ok=True)
_lock = threading.Lock()
http = requests.Session()  # reuses connections; retries stalled connects (hackathon Wi-Fi)
http.headers.update(UA)
http.mount("https://", requests.adapters.HTTPAdapter(max_retries=requests.adapters.Retry(connect=2, read=1)))
T = (5, 30)  # connect, read timeouts in seconds

SECTIONS_PROMPT = """This is {title}. Wikipedia says: {summary}
A blind person will explore it part by part on a 10x10 board of raised balls. Each part fills the
whole board, so small, specific parts (an eye, a hand, an earring) come through clearly.
Split it into 5-10 sections in tour order: the most famous subject as a whole first, then its key
features one at a time (eyes, mouth, hands, jewelry), then the next subject and its features.
Return JSON: {{"artist": "...", "year": "...", "sections": [...]}} where each section has
- name: short, the way a museum guide would say it ("her left eye")
- box_2d: [y0, x0, y1, x1] on a 0-1000 scale, tight around that part
- description: one or two sentences on what is there and why it matters
If the image is not this painting, return {{"sections": []}}."""

GRID_PROMPT = """This crop is "{name}" from {title}: {description}
A blind person will feel it on a 10x10 board of raised balls. Don't trace the pixels. First decide
what this is and the clearest way fingers could recognize it, then draw that.
- Outlines and key features, not solid blobs: a filled shape feels like a flat block.
- About 15-50 raised balls, using most of the board.
- A person is a head on shoulders and a body, never a triangle. A face shows its eyes and mouth.
- Row 0 is the top, column 0 is the left.
Examples (# raised, . flat):
a face          a person, head and shoulders   an eye          a hand
...####...      ...####...                     ..........      ..#.#.#...
.##....##.      ..#....#..                     ..........      ..#.#.#.#.
#........#      ..#....#..                     ...####...      ..#.#.#.#.
#.##..##.#      ...#..#...                     .##....##.      #.#.#.#.#.
#........#      ....##....                     #...##...#      ##.......#
#...##...#      ..######..                     #...##...#      .#.......#
#........#      .#......#.                     .##....##.      .#......#.
#..####..#      #........#                     ...####...      ..#....#..
.#......#.      #........#                     ..........      ..#....#..
..######..      #........#                     ..........      ..######..
Return JSON: {{"idea": "one sentence on what you drew", "grid": ["10 strings of 10 # or ."]}}"""

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def core(text):
    """'The Starry Night by Van Gogh' -> 'starry night'"""
    text = re.sub(r"\s+by\s+.*$", "", text.lower().strip())
    return re.sub(r"^the\s+", "", text)

def save_painting(p):
    with _lock:
        with open(f"{CACHE}/{slug(p['title'])}.json", "w") as f:
            json.dump(dict(p), f, indent=1)  # copy: Creao and Browser Use threads may add keys meanwhile

def from_cache(name):
    want = core(name)
    for path in glob.glob(f"{CACHE}/*.json"):
        with open(path) as f:
            p = json.load(f)
        title = core(p["title"])
        if title in want or want in title:
            return p
    return None

def find_on_wikipedia(name):
    hits = http.get("https://en.wikipedia.org/w/rest.php/v1/search/page",
                    params={"q": f"{name} painting", "limit": 1}, timeout=T).json()
    if not hits.get("pages"):
        return None
    key = hits["pages"][0]["key"]
    summary = http.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{key}", timeout=T).json()
    img = http.get("https://en.wikipedia.org/w/api.php", timeout=T, params={
        "action": "query", "titles": key, "prop": "pageimages",
        "piprop": "thumbnail", "pithumbsize": 1600, "format": "json"}).json()
    page = next(iter(img["query"]["pages"].values()))
    url = page.get("thumbnail", {}).get("source")
    if not url:
        return None
    return {"title": summary["title"], "summary": summary.get("extract", ""), "image_url": url}

def ask_gemini(image_bytes, mime, prompt, thinking):
    client = genai.Client()  # reads GEMINI_API_KEY
    resp = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json",
                                           thinking_config=types.ThinkingConfig(thinking_level=thinking)))
    return json.loads(resp.text)

def analyze(image_bytes, mime, title, summary):
    """Call 1: the parts of the painting, in tour order, without grids."""
    data = ask_gemini(image_bytes, mime, SECTIONS_PROMPT.format(title=title, summary=summary), "low")
    if isinstance(data, list):  # sometimes it returns [{...}] or the bare sections list
        data = data[0] if data and "sections" in data[0] else {"sections": data}
    return data

def draw(crop_bytes, title, s):
    """Call 2, once per section: design a grid from just that crop. None if it fails."""
    try:
        data = ask_gemini(crop_bytes, "image/jpeg", GRID_PROMPT.format(
            name=s["name"], title=title, description=s["description"]), "medium")
        if isinstance(data, list):
            data = data[0]
        return fix_grid(data["grid"])
    except Exception as e:  # drop this section, keep the tour
        print(f"draw failed for {s['name']!r}: {e!r}")
        return None

def fix_grid(grid):
    """Force exactly 10x10 of 0/1, whatever the model returned (numbers or '#'/'.' strings)."""
    rows = [[1 if v in (1, "1", "#") else 0 for v in list(row)[:10]] for row in list(grid)[:10]]
    rows = [r + [0] * (10 - len(r)) for r in rows]
    return rows + [[0] * 10 for _ in range(10 - len(rows))]

def crop_square(img, bbox, pad=0.15):
    """Cut bbox out of img, padded and widened to a square so shapes aren't stretched on the board."""
    w, h = img.size
    x0, x1 = sorted((bbox[0] * w, bbox[2] * w))
    y0, y1 = sorted((bbox[1] * h, bbox[3] * h))
    side = max(max(x1 - x0, y1 - y0) * (1 + 2 * pad), 8)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return img.crop([round(cx - side / 2), round(cy - side / 2), round(cx + side / 2), round(cy + side / 2)])

def jpeg(img):
    buf = BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()

def to_location(bbox):
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    row = ["top", "center", "bottom"][min(2, int(cy * 3))]
    col = ["left", "center", "right"][min(2, int(cx * 3))]
    return "center" if row == col == "center" else f"{row} {col}"

def load_painting(name):
    p = from_cache(name)
    if p:
        activity("gemini", "done", f"{p['title']}: ready from cache")
        return p
    try:
        p = fetch_painting(name)
    except Exception as e:  # network stall, Gemini error, bad JSON: the agent says it couldn't find it
        print(f"load_painting failed for {name!r}: {e!r}")
        p = None
    if p:
        activity("gemini", "done", f"{p['title']}: {len(p['sections'])} parts ready")
    else:
        activity("gemini", "failed", f"Couldn't find {name}")
    return p

def fetch_painting(name):
    activity("gemini", "working", f"Searching Wikipedia for {name}")
    wiki = find_on_wikipedia(name)
    if not wiki:
        return None
    path = f"{CACHE}/{slug(wiki['title'])}.json"
    if os.path.exists(path):  # cached under its Wikipedia title
        with open(path) as f:
            return json.load(f)
    resp = http.get(wiki["image_url"], timeout=T)
    mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    activity("gemini", "working", f"Picking the parts of {wiki['title']}")
    data = analyze(resp.content, mime, wiki["title"], wiki["summary"])
    if not data.get("sections"):
        return None  # the image wasn't the painting
    image_path = f"{CACHE}/{slug(wiki['title'])}.jpg"
    sections = []
    for s in data["sections"][:10]:  # caps parallel Gemini calls and tour length
        try:
            y0, x0, y1, x1 = [v / 1000 for v in s["box_2d"]]
            bbox = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
            sections.append({"name": s["name"], "bbox": bbox, "location": to_location(bbox),
                             "description": s["description"]})
        except Exception as e:  # one bad section must not sink the painting
            print(f"skipped bad section {s!r}: {e!r}")
    if not sections:
        return None
    img = Image.open(BytesIO(resp.content))
    crops = [jpeg(crop_square(img, s["bbox"])) for s in sections]
    activity("gemini", "working", f"Drawing {len(sections)} shapes in parallel")
    with ThreadPoolExecutor(len(sections)) as pool:  # all drawings at once: load time = slowest one
        grids = list(pool.map(lambda c, s: draw(c, wiki["title"], s), crops, sections))
    kept = [(s, g) for s, g in zip(sections, grids) if g and any(map(any, g))]
    if not kept:
        return None
    sections = [{"number": i, **s, "grid": g} for i, (s, g) in enumerate(kept, start=1)]
    with open(image_path, "wb") as f:  # only after parsing worked, so a failure leaves no stray files
        f.write(resp.content)
    p = {"title": wiki["title"], "artist": data.get("artist", ""), "year": data.get("year", ""),
         "summary": wiki["summary"], "image": image_path, "sections": sections}
    save_painting(p)
    return p
