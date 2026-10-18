# Quick Prizes (Sentry + GoDaddy) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify for the Sentry and MLH GoDaddy prizes. Any tool error during the demo shows up in Sentry, and the project has a registered domain for the Devpost link.

**Architecture:** `main.py` already calls `sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))`, but tool errors never reach Sentry, because the ElevenLabs SDK catches every exception a tool raises and sends it to the agent as `is_error` without logging it (`elevenlabs/conversational_ai/conversation.py:319-325`, SDK 2.73.1). Task 1 reports the exception to Sentry inside the existing tool wrapper in `build_tools()`, then re-raises it so the agent still gets the error. Tasks 2 and 3 are dashboard work only Harvey can do (accounts, payment, DNS).

**Tech Stack:** Python 3 in `.venv`, `sentry-sdk` 2.72.0, `elevenlabs` 2.73.1. Tests are plain `assert` scripts run with `python test_main.py` (pytest is not installed).

**Spec:** `docs/harvey.md`, "What to work on" item 8: "Quick prizes: create a Sentry project and put its DSN in `.env` as `SENTRY_DSN`. Register a GoDaddy domain for the Devpost link." Also the reference `main.py` comment: "Sentry prize: catches any tool error during the demo". The plan's prize table lists Sentry as "Two lines in `main.py`" and "MLH: Best domain name from GoDaddy | A domain for the project page or Devpost link".

## Global Constraints

- Only edit Harvey's files: `main.py`, `test_main.py`.
- Don't add features that aren't in `docs/harvey.md`.
- Tool results sent to ElevenLabs must be strings (JSON text). This is commit `5791bad`. Don't regress it.
- A tool error must still reach the agent as a tool error, so it can say something went wrong. Report it to Sentry and re-raise; never swallow it.
- Never commit `.env`. `SENTRY_DSN` goes only in `.env`.
- Always run Python from the venv: `source .venv/bin/activate`.
- Work on branch `feat/main-with-stubs`. Push is blocked (SSH permission on Austin's repo), so commit locally only.

## File Structure

| File | Status | Responsibility |
| --- | --- | --- |
| `main.py` | Modify `build_tools()` (around lines 76-83) | Wrap each tool so it returns JSON text and reports any exception to Sentry before re-raising |
| `test_main.py` | Modify (add one test above the `if __name__` block) | Prove a tool exception reaches `sentry_sdk.capture_exception` and still propagates |
| `.env` | Harvey edits by hand (never committed) | `SENTRY_DSN=...` |

---

### Task 1: Report tool errors to Sentry

**Files:**
- Modify: `main.py`, the `build_tools()` function
- Test: `test_main.py`

**Interfaces:**
- Consumes: the existing `main.open_painting(params) -> dict`, `main.show_section(params) -> dict`, `main.build_tools() -> ClientTools`, and the test helper `fresh_main()` in `test_main.py`.
- Produces: `main.as_tool(fn) -> Callable[[dict], str]`, which wraps a tool function. It returns `json.dumps(fn(params))`. On any exception it calls `sentry_sdk.capture_exception(e)` and re-raises. `build_tools()` registers `as_tool(open_painting)` and `as_tool(show_section)`.

- [ ] **Step 1: Write the failing test**

Add this to `test_main.py` directly above `if __name__ == "__main__":`:

```python
def test_tool_errors_reach_sentry():
    # The ElevenLabs SDK swallows tool exceptions, so main.py must report them itself.
    import asyncio
    m = fresh_main()
    captured = []
    original = m.sentry_sdk.capture_exception
    m.sentry_sdk.capture_exception = captured.append
    def broken_lookup(name):
        raise RuntimeError("wikipedia down")
    m.load_painting = broken_lookup
    try:
        asyncio.run(m.build_tools().handle("open_painting", {"name": "Mona Lisa"}))
        raise AssertionError("the error must still reach ElevenLabs as a tool error")
    except RuntimeError as e:
        assert str(e) == "wikipedia down"
    finally:
        m.sentry_sdk.capture_exception = original
    assert [str(e) for e in captured] == ["wikipedia down"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python test_main.py`
Expected: the first 9 tests print `PASS`, then `test_tool_errors_reach_sentry` fails with `AssertionError` on the last line, because `captured` is `[]`. The exception propagates, but nothing reports it.

- [ ] **Step 3: Write the minimal implementation**

In `main.py`, replace the current `build_tools` function:

```python
def build_tools():
    # ElevenLabs only accepts a string tool result, so send the dicts as JSON text.
    tools = ClientTools()
    tools.register("open_painting", lambda params: json.dumps(open_painting(params)))
    tools.register("show_section", lambda params: json.dumps(show_section(params)))
    return tools
```

with:

```python
def as_tool(fn):
    # ElevenLabs only accepts a string tool result, so send the dict as JSON text.
    # The SDK swallows tool exceptions without logging them, so report them to Sentry here.
    def handler(params):
        try:
            return json.dumps(fn(params))
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise
    return handler

def build_tools():
    tools = ClientTools()
    tools.register("open_painting", as_tool(open_painting))
    tools.register("show_section", as_tool(show_section))
    return tools
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python test_main.py`
Expected: 10 lines, each starting with `PASS` (including `test_registered_tools_return_json_text` and `test_tool_errors_reach_sentry`), and no traceback.

- [ ] **Step 5: Commit**

```bash
git add main.py test_main.py
git commit -m "fix: report tool errors to Sentry since the ElevenLabs SDK swallows them"
```

---

### Task 2: Sentry project and DSN (manual, done by Harvey)

There is no code in this task. An agentic executor stops after Task 1 and hands over to Harvey.

**Files:** `.env`, edited by hand and never committed.

**Interfaces:**
- Consumes: `sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))` in `main.py` and `as_tool` from Task 1.

- [ ] **Step 1: Create the project**

Go to https://sentry.io and sign up or log in. If the hackathon gives Sentry credits or a promo, use the sponsor's link. Click **Create Project**, pick the **Python** platform, and name it `tactile-art`.

- [ ] **Step 2: Copy the DSN into `.env`**

The DSN appears on the setup page, and later under Project Settings → Client Keys (DSN). It looks like `https://<key>@o<org>.ingest.us.sentry.io/<id>`. Add this line to `.env`:

```text
SENTRY_DSN=https://...your DSN...
```

- [ ] **Step 3: Send a test message**

Run:

```bash
source .venv/bin/activate
python -c "import os, sentry_sdk; from dotenv import load_dotenv; load_dotenv(); sentry_sdk.init(dsn=os.getenv('SENTRY_DSN')); sentry_sdk.capture_message('ArtForAll: Sentry test'); sentry_sdk.flush(); print('sent')"
```

Expected: it prints `sent`, and within a minute an issue titled "ArtForAll: Sentry test" appears under Issues in Sentry.

- [ ] **Step 4: Send a real tool error through `main.py`**

Run:

```bash
python -c "
import asyncio, main, sentry_sdk
def broken_lookup(name): raise RuntimeError('Sentry check: painting lookup failed')
main.load_painting = broken_lookup
try:
    asyncio.run(main.build_tools().handle('open_painting', {'name': 'Mona Lisa'}))
except RuntimeError as e:
    print('tool error:', e)
sentry_sdk.flush()
"
```

Expected: it prints `tool error: Sentry check: painting lookup failed`, and an issue `RuntimeError: Sentry check: painting lookup failed` appears in Sentry with a stack trace through `main.py` (`handler` → `open_painting`). This is the evidence for the Sentry prize: take a screenshot for Devpost.

- [ ] **Step 5: Resolve the test issues**

In Sentry, select both test issues and click **Resolve**, so the dashboard is clean before the demo.

---

### Task 3: GoDaddy domain (manual, done by Harvey)

**Files:** none.

- [ ] **Step 1: Get the MLH domain offer**

The MLH "Best domain name from GoDaddy" prize usually comes with a free-domain code from MLH. Check the LA Hacks Discord and MLH announcements, or ask at the MLH table. Don't pay before checking.

- [ ] **Step 2: Pick and register a name**

The name should be short, easy to say aloud, and about the project. Check availability on GoDaddy. Some ideas:
- `artforall` or `touchthepainting`
- `feeltheart` or `artbytouch`
- `paintingsbytouch`

Register it with the code from Step 1.

- [ ] **Step 3: Point it somewhere**

In GoDaddy, open My Products, then the domain, then **Forwarding**. Forward it (permanent 301) to the Devpost project page. If that page doesn't exist yet, forward to the GitHub repo `https://github.com/AustinCLieu/LAHACKSAI_NEED_A_NAME_LMAO` for now and switch to Devpost once the page is up.

- [ ] **Step 4: Verify**

Open `http://<your-domain>` in a browser. Forwarding can take a few minutes to an hour to work. Then tell the team the domain, so it goes in the Devpost submission's links and the README.
