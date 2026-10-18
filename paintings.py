import os, re, json, glob, threading, requests
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw
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
Gray bars at the edges are padding, not painting.
A blind person will feel it on a 10x10 board of raised balls. Draw only {name}, nothing around it,
and make it fill the board. Don't trace the pixels. First decide what this is and the clearest way
fingers could recognize it, then draw that.
- Outlines and key features, not solid blobs: a filled shape feels like a flat block.
- About 15-50 raised balls, reaching across at least 7 rows or 7 columns.
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

JUDGE_PROMPT = """Left: "{name}" from {title}. Right: {n} drawings of it for a 10x10 board of raised
balls (white = raised), numbered 1 to {n} from left to right. Which drawing would a blind person most
easily recognize as {name} by touch? Return JSON: {{"best": 1}}"""

DRAFTS = 3  # drawings per section; a judge call picks the best of the ones that pass grid_problems

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def core(text):
    """'The Starry Night by Van Gogh' -> 'starry night'; 'Girl with the Pearl Earring' -> 'girl with pearl earring'"""
    text = re.sub(r"\s+by\s+.*$", "", text.lower().strip())
    text = re.sub(r"\b(the|a|an)\b", " ", text)
    return " ".join(text.split())

def save_painting(p):
    path = f"{CACHE}/{slug(p['title'])}.json"
    with _lock:
        data = json.loads(json.dumps(p))  # deep copy: Creao and Browser Use threads may add keys meanwhile
        with open(path + ".tmp", "w") as f:
            json.dump(data, f, indent=1)
        os.replace(path + ".tmp", path)  # atomic: a reader sees the old file or the new one, never half

def from_cache(name):
    want = core(name)
    if not want:
        return None
    for path in glob.glob(f"{CACHE}/*.json"):
        try:
            with open(path) as f:
                p = json.load(f)
            title = core(p["title"])
        except Exception as e:  # one bad file must not break every lookup
            print(f"skipped bad cache file {path}: {e!r}")
            continue
        if title in want or want in title:
            return p
    return None

def find_on_wikipedia(name):
    hits = http.get("https://en.wikipedia.org/w/rest.php/v1/search/page",
                    params={"q": f"{name} painting", "limit": 1}, timeout=T).json()
    if not hits.get("pages"):
        return None
    key = hits["pages"][0]["key"]
    summary = http.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(key, safe=""),
                       timeout=T).json()
    img = http.get("https://en.wikipedia.org/w/api.php", timeout=T, params={
        "action": "query", "titles": key, "prop": "pageimages",
        "piprop": "thumbnail", "pithumbsize": 1600, "format": "json"}).json()
    page = next(iter(img["query"]["pages"].values()))
    url = page.get("thumbnail", {}).get("source")
    if not url:
        return None
    return {"title": summary["title"], "summary": summary.get("extract", ""), "image_url": url}

def ask_gemini(image_bytes, mime, prompt, thinking):
    client = genai.Client(http_options=types.HttpOptions(timeout=45_000))  # reads GEMINI_API_KEY; ms, so a stall can't hang open_painting
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

def board_image(grid, cell=24):
    """The grid as the board looks: white balls raised, gray flat."""
    img = Image.new("RGB", (cell * 10, cell * 10), "black")
    d = ImageDraw.Draw(img)
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            d.ellipse([c * cell + 3, r * cell + 3, (c + 1) * cell - 3, (r + 1) * cell - 3],
                      fill="white" if v else (60, 60, 60))
    return img

def contact_sheet(crop_bytes, grids):
    """The crop, then each grid as a board, side by side: what the judge call looks at."""
    crop = Image.open(BytesIO(crop_bytes)).convert("RGB").resize((240, 240))
    sheet = Image.new("RGB", (240 + 260 * len(grids), 240), "white")
    sheet.paste(crop, (0, 0))
    for i, g in enumerate(grids, start=1):
        sheet.paste(board_image(g), (260 * i, 0))
    return jpeg(sheet)

def draft(crop_bytes, title, s):
    """One drawing of a section from its crop. None if the call fails."""
    try:
        data = ask_gemini(crop_bytes, "image/jpeg", GRID_PROMPT.format(
            name=s["name"], title=title, description=s["description"]), "medium")
        if isinstance(data, list):
            data = data[0]
        return fix_grid(data["grid"])
    except Exception as e:  # one draft fewer, the others may still work
        print(f"draw failed for {s['name']!r}: {e!r}")
        return None

def pick(crop_bytes, title, s, grids):
    """Call 3: Gemini compares the drawings next to the crop. The first one if that call fails."""
    try:
        data = ask_gemini(contact_sheet(crop_bytes, grids), "image/jpeg", JUDGE_PROMPT.format(
            name=s["name"], title=title, n=len(grids)), "low")
        if isinstance(data, list):
            data = data[0]
        best = int(data["best"])
        return grids[best - 1] if 1 <= best <= len(grids) else grids[0]
    except Exception as e:
        print(f"judge failed for {s['name']!r}: {e!r}")
        return grids[0]

def draw(crop_bytes, title, s):
    """Call 2, once per section: DRAFTS drawings in parallel, cheap checks, then a judge call if more
    than one passes. None if every drawing failed or came back empty."""
    with ThreadPoolExecutor(DRAFTS) as pool:
        drafts = [g for g in pool.map(lambda _: draft(crop_bytes, title, s), range(DRAFTS))
                  if g and any(map(any, g))]
    if not drafts:
        return None
    good = [g for g in drafts if not grid_problems(g)]
    good = [g for i, g in enumerate(good) if g not in good[:i]]  # identical drafts count once
    if not good:
        return min(drafts, key=lambda g: len(grid_problems(g)))
    return good[0] if len(good) == 1 else pick(crop_bytes, title, s, good)

def fix_grid(grid):
    """Force exactly 10x10 of 0/1, whatever the model returned (numbers or '#'/'.' strings)."""
    if isinstance(grid, str):  # one newline-joined string instead of a list of rows
        grid = grid.split()
    rows = [[1 if v in (1, "1", "#") else 0 for v in list(row)[:10]] for row in list(grid)[:10]]
    rows = [r + [0] * (10 - len(r)) for r in rows]
    return rows + [[0] * 10 for _ in range(10 - len(rows))]

def grid_problems(grid):
    """What would make this grid hard to feel; [] if it looks fine. Code only, no Gemini.
    A ball is 'interior' when all 4 neighbours are raised: blobs are mostly interior, outlines aren't."""
    n = sum(map(sum, grid))
    if not n:
        return ["empty"]
    rows = [r for r in range(10) if any(grid[r])]
    cols = [c for c in range(10) if any(row[c] for row in grid)]
    inner = sum(1 for r in range(1, 9) for c in range(1, 9) if grid[r][c] and grid[r - 1][c]
                and grid[r + 1][c] and grid[r][c - 1] and grid[r][c + 1])
    problems = []
    if n < 12:
        problems.append("too few balls")
    if n > 60:
        problems.append("too many balls")
    if max(rows[-1] - rows[0], cols[-1] - cols[0]) + 1 < 7:
        problems.append("too small")
    if inner > 0.3 * n:
        problems.append("solid block")
    return problems

def crop_square(img, bbox, pad=0.05):
    """Cut bbox out of img with a little padding and center it on a gray square: the shape isn't
    stretched on the board, and neighboring parts of the painting stay out of the drawing."""
    w, h = img.size
    x0, x1 = sorted((bbox[0] * w, bbox[2] * w))
    y0, y1 = sorted((bbox[1] * h, bbox[3] * h))
    bw, bh = max(x1 - x0, 1) * (1 + 2 * pad), max(y1 - y0, 1) * (1 + 2 * pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    part = img.crop([max(0, round(cx - bw / 2)), max(0, round(cy - bh / 2)),
                     min(w, round(cx + bw / 2)), min(h, round(cy + bh / 2))]).convert("RGB")
    side = max(part.width, part.height, 8)
    out = Image.new("RGB", (side, side), (128, 128, 128))
    out.paste(part, ((side - part.width) // 2, (side - part.height) // 2))
    return out

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
    resp.raise_for_status()  # a 403/429 page is not an image
    mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    activity("gemini", "working", f"Picking the parts of {wiki['title']}")
    data = analyze(resp.content, mime, wiki["title"], wiki["summary"])
    if not data.get("sections"):
        return None  # the image wasn't the painting
    image_path = f"{CACHE}/{slug(wiki['title'])}.jpg"
    sections = []
    for s in data["sections"][:10]:  # caps parallel Gemini calls and tour length
        try:
            y0, x0, y1, x1 = [max(0, min(1000, v)) / 1000 for v in s["box_2d"]]  # clamp: off-image boxes
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
