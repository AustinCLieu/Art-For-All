# Austin: the paintings, Gemini, Browser Use and Creao

You own `paintings.py`: `load_painting(name)` turns "Mona Lisa" into the painting data in `CLAUDE.md`
(the right painting, its image, a summary, and its parts ranked with boxes, descriptions and 10x10 grids).
You also own `prepare_demo.py`, a one-time script that adds Browser Use museum facts and Creao guide
notes to the four demo paintings. Prizes you cover: Gemini, Browser Use, Creao.

## What to work on, in order
1. **Keys:** `GEMINI_API_KEY` (Google AI Studio), `BROWSER_USE_API_KEY` (cloud.browser-use.com),
   Creao Account API key (developer.creao.ai). Ask the Creao booth for hackathon credits: the free
   plan has 30 one-time credits and a typical run uses about 12.
2. **Build `paintings.py`** from the reference code below (Claude Code prompt at the bottom).
   Install: `pip install requests google-genai python-dotenv`.
3. **Test it:** `load_painting("Mona Lisa")` returns full data; `load_painting("asdfgh")` returns None;
   "Mona Lisa by Leonardo da Vinci" and "the starry night" both hit the cache once cached.
4. **Cache the four demo paintings** and check them by eye: draw each section's box on the image
   (`check.py`) and fix bad boxes or names directly in the JSON. **Hand `paintings.py` to Harvey by 6:00 PM.**
5. **Tonight: Creao agent.** Create it at https://agent.creao.ai with the prompt below. Copy its
   `agent_id` into `.env` as `CREAO_AGENT_ID`. In the Developer Console, check what its two inputs are
   actually called and match them in `prepare_demo.py`.
6. **Tonight: run `prepare_demo.py`** once with all keys set. Browser Use runs take a few minutes each.
7. **If you fall behind:** drop Creao first, then Browser Use. The tour works without them.

**Done when:** the four demo paintings load instantly with sensible parts, boxes, facts and notes, and a
new painting loads in well under 30 seconds.

## Reference `paintings.py`
```python
import os, re, json, glob, threading, requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
UA = {"User-Agent": "TactileArt/0.1 (LA Hacks hackathon; your-email)"}  # Wikimedia blocks generic agents
CACHE = "cache"
os.makedirs(CACHE, exist_ok=True)
_lock = threading.Lock()

PROMPT = """This is {title}. Wikipedia says: {summary}
A blind person will explore it section by section on a 10x10 board of raised balls.
Split it into 3-6 sections, one subject each (a face, hands, the sky, a tree).
Order them from most to least famous: the part people know best comes first.
Return JSON: {{"artist": "...", "year": "...", "sections": [...]}} where each section has
- name: short, the way a museum guide would say it ("her face")
- box_2d: [y0, x0, y1, x1] on a 0-1000 scale
- description: one or two sentences on what is there and why it matters
- grid: 10 rows of 10 numbers, 1 = raised ball, a bold simple outline or silhouette
  of that subject that fingers can recognize; row 0 is the top
If the image is not this painting, return {{"sections": []}}."""

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def core(text):
    """'The Starry Night by Van Gogh' -> 'starry night'"""
    text = re.sub(r"\s+by\s+.*$", "", text.lower().strip())
    return re.sub(r"^the\s+", "", text)

def save_painting(p):
    with _lock:
        with open(f"{CACHE}/{slug(p['title'])}.json", "w") as f:
            json.dump(p, f, indent=1)

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
    hits = requests.get("https://en.wikipedia.org/w/rest.php/v1/search/page",
                        params={"q": f"{name} painting", "limit": 1}, headers=UA).json()
    if not hits.get("pages"):
        return None
    key = hits["pages"][0]["key"]
    summary = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{key}", headers=UA).json()
    img = requests.get("https://en.wikipedia.org/w/api.php", headers=UA, params={
        "action": "query", "titles": key, "prop": "pageimages",
        "piprop": "thumbnail", "pithumbsize": 1600, "format": "json"}).json()
    page = next(iter(img["query"]["pages"].values()))
    url = page.get("thumbnail", {}).get("source")
    if not url:
        return None
    return {"title": summary["title"], "summary": summary.get("extract", ""), "image_url": url}

def analyze(image_bytes, mime, title, summary):
    client = genai.Client()  # reads GEMINI_API_KEY
    resp = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime),
                  PROMPT.format(title=title, summary=summary)],
        config=types.GenerateContentConfig(response_mime_type="application/json"))
    return json.loads(resp.text)

def fix_grid(grid):
    """Force exactly 10x10 of 0/1, whatever the model returned."""
    rows = [[1 if v else 0 for v in list(row)[:10]] for row in list(grid)[:10]]
    rows = [r + [0] * (10 - len(r)) for r in rows]
    return rows + [[0] * 10 for _ in range(10 - len(rows))]

def to_location(bbox):
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    row = ["top", "center", "bottom"][min(2, int(cy * 3))]
    col = ["left", "center", "right"][min(2, int(cx * 3))]
    return "center" if row == col == "center" else f"{row} {col}"

def load_painting(name):
    p = from_cache(name)
    if p:
        return p
    wiki = find_on_wikipedia(name)
    if not wiki:
        return None
    path = f"{CACHE}/{slug(wiki['title'])}.json"
    if os.path.exists(path):  # cached under its Wikipedia title
        with open(path) as f:
            return json.load(f)
    resp = requests.get(wiki["image_url"], headers=UA)
    mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    data = analyze(resp.content, mime, wiki["title"], wiki["summary"])
    if not data.get("sections"):
        return None  # the image wasn't the painting
    image_path = f"{CACHE}/{slug(wiki['title'])}.jpg"
    with open(image_path, "wb") as f:
        f.write(resp.content)
    sections = []
    for i, s in enumerate(data["sections"], start=1):
        y0, x0, y1, x1 = [v / 1000 for v in s["box_2d"]]
        bbox = [x0, y0, x1, y1]
        sections.append({"number": i, "name": s["name"], "bbox": bbox, "location": to_location(bbox),
                         "description": s["description"], "grid": fix_grid(s["grid"])})
    p = {"title": wiki["title"], "artist": data.get("artist", ""), "year": data.get("year", ""),
         "summary": wiki["summary"], "image": image_path, "sections": sections}
    save_painting(p)
    return p
```

## Reference `prepare_demo.py`
```python
import os, re, json, time, requests
from dotenv import load_dotenv
from browser_use_sdk.v4 import BrowserUse  # pip install browser-use-sdk
from paintings import load_painting, save_painting

load_dotenv()
DEMO = ["Mona Lisa", "The Starry Night", "The Great Wave off Kanagawa", "Girl with a Pearl Earring"]

def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)  # agents sometimes wrap JSON in prose
    return json.loads(m.group(0)) if m else {}

def museum_facts(p):  # Browser Use
    client = BrowserUse()  # reads BROWSER_USE_API_KEY
    run = client.runs.create(f"Find the official museum page for {p['title']} by {p['artist']}. "
                             'Return only JSON: {"facts": ["..."]} with 3-5 facts a guide would point out.')
    return parse_json(client.runs.wait_for_completion(run.id).result).get("facts")

def guide_notes(p):  # Creao
    api = "https://developer.creao.ai/v1"
    h = {"Authorization": f"Bearer {os.environ['CREAO_API_KEY']}"}
    run = requests.post(f"{api}/runs", headers=h, json={
        "agent_id": os.environ["CREAO_AGENT_ID"],
        # match these input names to what the Developer Console shows for your agent
        "input": {"painting": f"{p['title']} by {p['artist']}",
                  "sections": [s["name"] for s in p["sections"]]}}).json()
    while True:
        r = requests.get(f"{api}/runs/{run['run_id']}", headers=h).json()
        if r["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(3)
    notes = parse_json((r.get("result") or {}).get("text")).get("sections", [])
    return {n["name"]: n["guide_notes"] for n in notes}

for name in DEMO:
    p = load_painting(name)
    p["museum_facts"] = museum_facts(p)
    p["guide_notes"] = guide_notes(p)
    save_painting(p)
    print(p["title"], "done:", len(p["museum_facts"] or []), "facts,", len(p["guide_notes"]), "notes")
```

## Creao agent prompt (paste at agent.creao.ai)
```text
Create an agent named "Tactile Tour Writer" with two inputs: painting (title and artist)
and sections (a list of section names, most important first). For each section, research
the painting and write what a museum guide would tell a blind visitor whose fingers are on
that part: two or three concrete sentences plus one surprising fact. Return only JSON:
{"sections": [{"name": "...", "guide_notes": "..."}]}
```

## Claude Code kickoff prompt
```text
Read CLAUDE.md and docs/austin.md. Then:
1. Create paintings.py from the reference code in docs/austin.md, unchanged unless something doesn't run.
2. Create test_paintings.py that calls load_painting on "Mona Lisa", "mona lisa by leonardo da vinci"
   and "asdfgh", and prints each section's number, name, location and to-ascii grid (# and .).
3. Create check.py that draws every section's bbox and name on each cached painting's image and
   saves cache/<id>_check.png, so I can eyeball the boxes.
4. Create prepare_demo.py from the reference code, but don't run it yet.
5. Add the packages to requirements.txt. Don't add features that aren't in docs/austin.md.
```