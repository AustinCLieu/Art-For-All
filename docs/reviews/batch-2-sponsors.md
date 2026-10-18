# Review: Batch 2, sponsor integrations and demo cache data

Scope: `creao.py`, `museum.py`, `prepare_demo.py` (diff `4b825dc..9612a6e`) and `cache/*.json`.
Integration read in `main.py`, `paintings.py`, `screen.py`, and the installed `browser_use_sdk` v4 (`runs.py`, `models.py`).
No live or paid API calls were made.

## Strengths

- **The live tour can't be broken by either sponsor.** `start_tour_writer` and `start_museum_facts` run in daemon threads, wrap everything in `except Exception`, and return at once when the data is already there. All four demo paintings already have `guide_notes` and `museum_facts`, so both functions do nothing for them. `main.py:18-27` falls back to no-ops if either module fails to import.
- **The Creao polling loop can't run forever.** `creao.py:46-56` has a 300 s deadline, a 30 s timeout on every request, and skips over polls that fail on bad Wi-Fi. The `while ... else` correctly ends with `{"status": "timed out"}` even if every poll failed. `raise_for_status()` turns 401/402/404 into a clear exception.
- **Bad model output is handled defensively.** `parse_json` never raises. `fetch_notes` tries the JSON artifact first and falls back to the reply text. Notes are filtered to dicts that have `name` and `guide_notes` (`creao.py:57`). Notes are only saved when the run has `completed` and returned some.
- **API keys are never printed.** Only run IDs, statuses, `errorCode` and exception text are logged. Request exceptions include the URL (with the agent ID) but not the headers.
- **`prepare_demo.py` keeps going when one painting fails** and keeps the old facts when Browser Use fails. It also skips Creao cleanly when the env vars are missing.
- **Updating the audience screen is optional and can't raise** (it falls back to a no-op `activity`). `save_painting` copies the dict under a lock (`paintings.py:64-67`), so the two background threads can save safely while the other adds keys.
- **The cache data passes every schema check** (see below).

## Cache validation (`cache/*.json`)

I ran a throwaway checker covering: required keys; no unexpected keys; `number` running 1..n; bbox of 4 floats in [0,1] with x0<x1 and y0<y1; `location` equal to the 3x3 cell of the bbox center (same formula as `paintings.to_location`); grid exactly 10x10 of int 0/1, neither empty nor full; `image` file exists; filename equals `slug(title)`; section names unique; `museum_facts` is a list of strings; `guide_notes` keys exactly match section names; no URLs or citation markers in spoken text.

| File | Sections | Facts | Notes | Schema result |
| --- | --- | --- | --- | --- |
| girl-with-a-pearl-earring.json | 4 | 4 | 4 | all pass |
| mona-lisa.json | 5 | 5 | 5 | all pass |
| the-great-wave-off-kanagawa.json | 3 | 4 | 3 | all pass |
| the-starry-night.json | 4 | 4 | 4 | all pass |

No schema mismatches. The content problems are listed under Issues (I-1, M-5, M-6).

## Issues

### Critical (Must Fix)

None. Nothing in this batch can crash or stall the tour for the four cached paintings, and the live (uncached) path is wrapped so it can't throw.

### Important (Should Fix)

**I-1. The cached guide notes describe a sculpted relief, not a 10x10 ball board. They are also long.** (`cache/*.json`, `guide_notes`; root cause is the Creao prompt in `docs/austin.md`)
- What's wrong: the notes talk about "the relief" and "the plate" and describe textures, gloss and colour a ball board can't show. Examples: "a single smooth teardrop hanging free of the relief, its surface the most polished and glossy point on the entire plate" (Pearl Earring); "the blue area feels flatter and drier than the glossier white collar"; "small hooked ridges, each one lifted like a bent finger" (Great Wave). Each note is 650-830 characters, about 45-60 seconds of speech.
- Why it matters: the agent reads these aloud while the user's hands are on the board. A blind user told to feel a glossy teardrop or a dry blue area will find nothing like it, which undercuts the demo. CLAUDE.md also says tool responses should be "short and plain". On top of that, `main.py` resends all `museum_facts` with every section, so each `show_section` reply carries roughly 1.5 KB of text.
- How to fix: before the freeze, hand-trim each of the 15 cached notes to 2-3 sentences and delete the texture, gloss and colour claims. That is a quick JSON edit, with no API calls. Then update the Creao agent prompt to say the user feels "a 10x10 grid of raised balls showing a simple outline", "don't describe texture, colour or gloss", and "at most 3 sentences", so the live Birth of Venus run produces suitable notes too.

**I-2. Opening the same new painting twice starts a second paid run, and the notes never reach the open tour.** (`creao.py:68-78`, `museum.py:35-48`, with `paintings.from_cache` reading a fresh dict from disk each time)
- What's wrong: `start_tour_writer(p)` only checks `p.get("guide_notes")`. While a run is in progress, the cache file has no notes yet. So if `open_painting` is called again for the same painting, a second Creao run starts (about 12 credits of 30 on the free plan), plus a second Browser Use run. This happens if the LLM retries, the user says "open The Birth of Venus" again, or the tour comes back to it. The first thread then writes its notes into the old dict, not the one now in `state["painting"]`, so the open tour never gets them.
- Why it matters: this is exactly the Birth of Venus demo flow. A duplicate open is quite likely with a voice LLM, and it can use up credits or leave the screen showing "Writing guide notes" twice.
- How to fix: keep a module-level `_running = set()` of titles (with a lock) in both modules. Skip if the title is already in the set, and remove it in a `finally`. If you want notes to reach a dict that was reopened, also have `main.py` re-read `guide_notes` from the cache file when it builds the section payload (this needs Harvey). The set alone fixes the cost problem.

**I-3. Browser Use waits can last up to 30 minutes, and a run that times out is never cancelled.** (`museum.py:22-29`)
- What's wrong: the retry loop catches every `Exception`, including the SDK's own `TimeoutError` (`browser_use_sdk/v4/resources/runs.py:323`). Each retry starts a fresh `timeout=600`, so the worst case is 3 x 10 minutes. On the final failure, the run on Browser Use's side keeps going and keeps billing.
- Why it matters: live, the daemon thread just sits there, which is harmless. But in `prepare_demo.py`, which runs tonight for 4 paintings, a slow site can block the script for up to 2 hours. The live demo also doesn't need a 10-minute fact search.
- How to fix: give all attempts one shared deadline, let `TimeoutError` through without retrying (`except TimeoutError: client.runs.cancel(run.id); raise`), and lower the timeout to about 300 s to match Creao's `MAX_WAIT`.

**I-4. The Creao API key is sent to whatever host the artifact URL points at.** (`creao.py:27`)
- What's wrong: `requests.get(a["url"], headers=h, ...)` sends `Authorization: Bearer capi_...` to any URL the agent's result contains. If that is a presigned S3 or CDN URL, the key goes to a third party. S3 also rejects a presigned URL sent with an `Authorization` header ("Only one auth mechanism allowed"). The `except` hides that error, so the code quietly falls back to the reply text and the artifact path never actually works.
- Why it matters: it can leak the key, and the "reads notes from the agent's JSON file" feature might not be doing anything.
- How to fix: only send `h` when `urlparse(a["url"]).hostname` ends with `creao.ai`, and send no headers otherwise. Check once against a real run's artifact URL, which you already have from tonight's run.

### Minor (Nice to Have)

**M-1. Note names must match section names exactly.** (`creao.py:59`; looked up in `main.py:46`)
`p["guide_notes"]` is keyed by whatever name the agent returns. If it says "Her face" or "the face" instead of "her face", the note is silently dropped. The cached files all match, so this only affects live runs. Fix: map notes by case-insensitive name, then by position (the agent receives the sections in order).

**M-2. `start_tour_writer` checks `CREAO_AGENT_ID` but not `CREAO_API_KEY`.** (`creao.py:70`)
If the key is missing, the thread raises `KeyError` and the screen shows "Creao: failed / Couldn't run" during the demo. Fix: `if p.get("guide_notes") or not (os.getenv("CREAO_AGENT_ID") and os.getenv("CREAO_API_KEY")): return`.

**M-3. Museum facts aren't checked to be a list of strings.** (`museum.py:30-33`)
`facts` only has to be truthy. A string or dict would be saved, and `len()` would then count characters or keys. Fix: `if not (isinstance(facts, list) and all(isinstance(f, str) for f in facts)): raise ...`.

**M-4. A Creao run that times out keeps running on Creao's side** (`creao.py:55-56`) and keeps using agent credits. Cancel it if the API has a cancel endpoint, or at least log the run ID as timed out so it can be cancelled by hand. It already logs the ID.

**M-5. Markdown in the spoken facts.** `the-great-wave-off-kanagawa.json` has `*Thirty-six Views of Mount Fuji*` and `*La Mer*`. Some TTS voices read the asterisks or pause oddly. Delete the asterisks, and add "no markdown" to the Browser Use prompt (`museum.py:17-19`).

**M-6. Inconsistent section names.** The Starry Night uses Title Case ("The Swirling Sky", "The Crescent Moon"), but the others use the brief's spoken style ("her face"). Mona Lisa's section 1 is named "Mona Lisa" and its bbox covers almost the whole painting, so the agent says "the main subject: Mona Lisa". Lowercase the Starry Night names; consider "her figure" for Mona Lisa section 1. If you rename sections, rename the matching `guide_notes` keys too, or the notes stop matching.

**M-7. Coupling.** `museum.py:5` imports `parse_json` from `creao.py`, so Browser Use silently depends on Creao's module. That's fine for a hackathon, but if `creao.py` ever fails to import, museum facts disappear too, without any clear error. Optional: copy the 5-line helper instead.

**M-8. `prepare_demo.py:15-19` always reruns Browser Use**, even for paintings whose facts are already cached and checked. That costs credits and can replace good facts with worse ones. Optional: skip when `museum_facts` exists, unless a `--refresh` flag is passed.

## Plan alignment

- **Not in the plan: live Browser Use.** `docs/austin.md` puts Browser Use only in the one-time `prepare_demo.py`. `museum.py` adds a live background fetch for every newly opened painting. CLAUDE.md says "Don't add features that aren't in these docs", and its file/owner list doesn't mention `museum.py`. The change looks well built and worth keeping for the prize, but tell the team and add `museum.py` to the CLAUDE.md owner list.
- **Changes from the reference code, all improvements:** the Creao endpoint (`agent.creao.ai/api/v1/apps/<id>/runs` with `inputs`, not `developer.creao.ai/v1/runs` with `agent_id`/`input`), reading the JSON artifact, the timeouts and run limit, and keeping going per painting. These are documented in commit messages and `docs/devpost.md`.
- **Plan problem:** the requirements list cites `docs/superpowers/plans/2026-10-17-quick-prizes.md`, but that plan only covers Sentry and GoDaddy (`main.py`, `test_main.py`). It says nothing about Creao, Browser Use or the cache. The only specification for this batch is `docs/austin.md`. No written plan covers the live museum facts, the Creao API change, or the screen activity reporting.

## Testing gaps

- None of the tests touch `creao.py` or `museum.py`. `test_main.py`/`test_screen.py` stub them out, which is right for preventing paid calls, but it leaves `parse_json`, `fetch_notes` and the poll/timeout paths untested. A small offline `test_sponsors.py` could cover them by monkeypatching `requests.get/post` and `time.sleep`: prose-wrapped JSON, an artifact that 403s and falls back to the text, the run timing out, a `failed` status, notes with mismatched or missing keys, and a check that `start_tour_writer` returns at once when notes exist.
- There's no automated cache check. The checker used for this review could become `test_cache.py` (no network) and run before the freeze.

## Recommendations

1. Before the 10:00 AM freeze: trim the 15 cached guide notes (I-1), delete the markdown asterisks (M-5), lowercase the Starry Night names along with their note keys (M-6), and rerun the cache checker.
2. Add the in-flight guard (I-2) and the Browser Use deadline and cancel (I-3). Each is under 10 lines.
3. Limit the artifact `Authorization` header to Creao's own hosts (I-4).
4. Update the Creao agent prompt for the ball board and short notes, then do one live dry run of the Birth of Venus flow with the screen open, opening the painting twice to confirm only one run starts.
5. Tell the team about `museum.py` and add it to the CLAUDE.md owner list.

## Assessment

**Ready to merge?** With fixes

**Reasoning:** The code is robust, so a sponsor API can't break the tour, and the cache data passes every schema check. But the cached guide notes describe a tactile relief the board doesn't have, and opening a new painting twice starts duplicate paid runs. Both affect the live demo directly and are cheap to fix before the freeze.
