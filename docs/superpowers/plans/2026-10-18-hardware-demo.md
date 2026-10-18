# Hardware Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A voice tour (`python main.py`) raises each section's shape on the real pin board, with a teammate flattening the board between sections.

**Architecture:** `main.py` already calls `board.show_grid(grid)` for every section. The only software change is a wait before that call: with `BOARD=serial`, `main.py` prints "Press the board flat, then Enter" and blocks until the teammate presses Enter. `board.py` stays a plain hardware driver (G-code over USB, solenoid on fan 0, rails limited to X130 Y150) and the Marlin firmware stays as flashed. The ElevenLabs tool timeout is raised in the dashboard so the wait plus the raise fits. The calibration numbers are measured on the board as the last hands-on task.

**Tech Stack:** Python 3, pyserial, ElevenLabs Conversational AI SDK, Marlin `bugfix-2.1.x` on a BigTreeTech SKR Pico.

**Spec:** No separate spec file. The design was approved in chat on Oct 18 and is summarized in Architecture above and in the decisions below:
- Pins are reset by a teammate pressing the board flat (no hardware reset).
- The teammate confirms with Enter in the `main.py` terminal before each shape is raised (only with `BOARD=serial`).
- The ElevenLabs client-tool response timeout is raised to about 60 s.
- Firmware is not reflashed. Calibration values are measured last.

## Global Constraints

- Only edit your own files (`CLAUDE.md`). Harvey owns `main.py`, `stubs.py`, `test_main.py`, `docs/harvey.md`. `board.py` is Austin's: Task 3 changes only its calibration constants, and Austin is told.
- Tests are plain scripts, no pytest: `python test_main.py`, `python test_board.py`.
- `.env` is never committed.
- Never send `G28`: there are no endstops. The head must sit in the zero corner at power-on.
- Tool responses are read aloud by the agent: no change to the response shapes in the contract.
- Feature freeze 10:00 AM Oct 18, submissions close at noon Pacific.

---

### Task 1: Wait for the board to be flat before raising a shape

**Files:**
- Modify: `main.py:44-55` (add `wait_until_flat`, call it in `section_payload`)
- Test: `test_main.py` (stub the wait in `fresh_main`, add two tests)

**Interfaces:**
- Consumes: `board.show_grid(grid) -> None` (unchanged), env var `BOARD` (`sim` or `serial`, default `sim`).
- Produces: `main.wait_until_flat() -> None`. Blocks on `input()` only when `BOARD=serial`; returns at once otherwise.

- [ ] **Step 1: Stub the wait in the test helper**

`.env` may say `BOARD=serial` on the demo laptop, and `main.py` loads it, so the existing tests would block on `input()`. In `test_main.py`, in `fresh_main()`, add this line after `main.show_grid = lambda grid: None`:

```python
    main.wait_until_flat = lambda: None       # never block on Enter in tests
```

- [ ] **Step 2: Write the failing tests**

Add to `test_main.py`, before the `if __name__ == "__main__":` block:

```python
def test_serial_waits_for_flat_board_before_raising():
    # The board only raises pins: a teammate flattens it and presses Enter before each new shape.
    import builtins, os
    m = fresh_main()
    m.wait_until_flat = m._real_wait_until_flat  # use the real one, not the fresh_main stub
    events = []
    m.show_grid = lambda grid: events.append("raise")
    original_input, original_board = builtins.input, os.environ.get("BOARD")
    builtins.input = lambda prompt="": events.append("enter")
    os.environ["BOARD"] = "serial"
    try:
        m.open_painting({"name": "Mona Lisa"})
        m.show_section({"section": "next"})
    finally:
        builtins.input = original_input
        os.environ["BOARD"] = original_board or "sim"
    assert events == ["enter", "raise", "enter", "raise"]

def test_sim_never_waits():
    import builtins, os
    m = fresh_main()
    m.wait_until_flat = m._real_wait_until_flat
    original_input, original_board = builtins.input, os.environ.get("BOARD")
    def no_input(prompt=""):
        raise AssertionError("sim mode must not wait for Enter")
    builtins.input = no_input
    os.environ["BOARD"] = "sim"
    try:
        assert m.open_painting({"name": "Mona Lisa"})["found"] is True
    finally:
        builtins.input = original_input
        os.environ["BOARD"] = original_board or "sim"
```

`fresh_main` reuses the same imported module and replaces `wait_until_flat` with a stub, so these tests put the real function back from `main._real_wait_until_flat` (added in Step 4).

- [ ] **Step 3: Run the tests to verify they fail**

Run: `source .venv/bin/activate && python test_main.py`
Expected: FAIL with `AttributeError: module 'main' has no attribute '_real_wait_until_flat'`

- [ ] **Step 4: Implement the wait in `main.py`**

After the line `_tour = threading.Lock()  # the SDK runs tools on a thread pool; one board move at a time`, add:

```python
def wait_until_flat():
    # The board can only raise pins: a teammate presses it flat and hits Enter before each new shape.
    if os.getenv("BOARD", "sim") == "serial":
        input("Press the board flat, then Enter... ")
_real_wait_until_flat = wait_until_flat  # tests stub wait_until_flat and restore it from here
```

In `section_payload`, change:

```python
    try:
        show_grid(s["grid"])  # returns once the balls settle
```

to:

```python
    try:
        wait_until_flat()
        show_grid(s["grid"])  # returns once the last pin is up
```

`wait_until_flat()` sits inside the existing `try`, so an error there (for example stdin closed) is reported to Sentry and the voice tour goes on, like any board failure.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `source .venv/bin/activate && python test_main.py && python test_board.py`
Expected: every line `PASS ...`, including `PASS test_serial_waits_for_flat_board_before_raising` and `PASS test_sim_never_waits`; no traceback.

- [ ] **Step 6: Commit**

```bash
git add main.py test_main.py
git commit -m "feat(main): wait for Enter (board pressed flat) before raising each shape on the real board"
```

---

### Task 2: ElevenLabs dashboard and demo notes

No code. The dashboard changes are what make Task 1 work live: without them, the agent gives up on `show_section` while the teammate is still flattening.

**Files:**
- Modify: `docs/harvey.md` (append a "Demo with the real board" section)

**Interfaces:**
- Consumes: Task 1's terminal prompt text, `Press the board flat, then Enter... `.
- Produces: nothing used by code.

- [ ] **Step 1: Raise the tool timeout**

At https://elevenlabs.io/app/agents, open the agent, then Tools. For both `open_painting` and `show_section`, set the response timeout to 60 seconds. Keep "Wait for response" ticked. Save.

- [ ] **Step 2: Add one line to the system prompt**

Append to the agent's system prompt and save:

```
Before you call show_section or open_painting, say "One moment while the board changes." The board takes up to a minute.
```

- [ ] **Step 3: Write it down in `docs/harvey.md`**

Append:

```markdown
## Demo with the real board
- `.env`: `BOARD=serial`, `SERIAL_PORT=/dev/cu.usbmodem2101` (check with `ls /dev/cu.usbmodem*`).
- Before each shape `main.py` prints `Press the board flat, then Enter...`. The teammate at the laptop
  presses all pins down, then hits Enter. The board then raises the new shape.
- Dashboard: both tools have a 60 s response timeout, and the prompt tells the guide to say
  "One moment while the board changes." before each tool call.
- Before the demo: power off, head in the zero corner, pins flat, USB Power cap off, 12 V on, then USB.
  Never send `G28`. Unplugging 12 V is the emergency stop.
```

- [ ] **Step 4: Commit**

```bash
git add docs/harvey.md
git commit -m "docs(harvey): real-board demo steps, dashboard timeout and flatten cue"
```

---

### Task 3: Calibrate the board (hands-on, on the Mac)

The three cell positions, steps per mm and pulse length are measured here. `show_grid` refuses to move until the cells are set, so nothing moves on a guess.

**Files:**
- Modify: `board.py:10-12` (`CELL_0_0`, `CELL_0_9`, `CELL_9_0`), `board.py` `STEPS_PER_MM` and `PULSE_MS` lines (only if measurements differ)

**Interfaces:**
- Consumes: the board on `/dev/cu.usbmodem2101`, zero corner reference, `MAX_X = 130`, `MAX_Y = 150`.
- Produces: three `(x, y)` tuples in mm, each with `0 <= x <= 130` and `0 <= y <= 150`.

- [ ] **Step 1: Power up**

Power off. Push the head to the zero corner. USB Power cap off, BOOT pins empty. 12 V on, then USB. Check: `ls /dev/cu.usbmodem*`.

- [ ] **Step 2: Open a monitor**

```bash
source .venv/bin/activate
python -m serial.tools.miniterm /dev/cu.usbmodem2101 115200 -e
```

Send `M115` (expect `FIRMWARE_NAME:Marlin`), then `M84 S0`, then `G92 X0 Y0`.

- [ ] **Step 3: Steps per mm**

Send `G91`, then `G0 X100 F1500`. Measure the real distance with a ruler. If it isn't 100 mm, new X value = `80 * 100 / measured`. Send `G0 X-100 F1500` to return. Repeat with Y. Put the values in `STEPS_PER_MM = (x, y)` in `board.py`.

- [ ] **Step 4: Pulse length**

Send ten times: `M106 P0 S255`, `G4 P50`, `M107 P0`. Count full extensions. Fewer than 10 of 10: repeat with `G4 P100`, then `G4 P150`, and set `PULSE_MS` in `board.py` to the first value that gives 10 of 10.

- [ ] **Step 5: Cell positions**

Send `G90`. With `G0 X.. Y.. F1500`, move under cell row 0, col 0 (far left, seen from the user). Send `M114` and note X and Y. Repeat for row 0, col 9 (far right) and row 9, col 0 (near left). Every value must be within X 0-130 and Y 0-150. Quit miniterm with Ctrl+].

- [ ] **Step 6: Write them into `board.py`**

Replace the three `None` lines with the measured values, for example:

```python
CELL_0_0 = (12.0, 8.0)    # measured with M114, Oct 18
CELL_0_9 = (118.0, 8.0)
CELL_9_0 = (12.0, 140.0)
```

- [ ] **Step 7: Run the offline tests**

Run: `python test_board.py`
Expected: every line `PASS ...` (the tests set their own cell values, so they don't depend on these).

- [ ] **Step 8: Commit and tell Austin**

```bash
git add board.py
git commit -m "chore(board): measured cell positions, steps per mm and pulse length"
```

Tell Austin `board.py` changed (his file).

---

### Task 4: End-to-end test on the real board

**Files:**
- Modify: `.env` (not committed): `BOARD=serial`, `SERIAL_PORT=/dev/cu.usbmodem2101`

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: a working demo.

- [ ] **Step 1: Switch `.env` to the real board**

```
BOARD=serial
SERIAL_PORT=/dev/cu.usbmodem2101
```

Close any miniterm first: only one program can hold the port.

- [ ] **Step 2: Test patterns**

Press the board flat and put the head in the zero corner before each run.

```bash
python board.py corners
python board.py border
python board.py checker
```

Expected: the right pins go up, the head parks at the zero corner, and `checker` prints `Raised in N s` with N under about 30 s (it is the densest test, 50 cells; the densest demo section has 48).

- [ ] **Step 3: Voice tour**

```bash
python main.py
```

Say "Mona Lisa". Expected: the terminal prints `Press the board flat, then Enter...`; after Enter, section 1 rises and the guide describes it. Say "next", flatten, press Enter: section 2 rises. The terminal must never print `Board failed`.

- [ ] **Step 4: Timing check**

For each of the four demo paintings, run through all sections once. If the guide ever says the tool failed or goes silent mid-raise, raise the dashboard response timeout (Task 2 Step 1) to 90 s and retest. If a shape lands shifted or stretched, re-measure in Task 3.
