# Three Solenoids Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The head carries three solenoids in a row along X, one column apart; at each stop every solenoid under a raised cell fires at the same time, so a 10-column row takes at most 4 stops instead of up to 10.

**Architecture:** Only `board.py`'s G-code generation changes. `FAN = 0` becomes `FANS = (0, 1, 2)`: Marlin fan numbers of the solenoids from the user's left to right. Solenoid 0 is the head's reference point, so the measured cell positions (`CELL_0_0` etc.) mean "solenoid 0 under that cell". Each row is split into stops at columns 0, 3, 6 and 7: the stop at column 7 only covers column 9 (solenoid 2), so the head never travels past column 7 and the outer solenoids never hang past the grid. At a stop, `M106` goes out for each solenoid that should fire, then one shared pulse wait, then `M107` for each. `show_grid`, `to_ascii`, `main.py` and the firmware don't change (no reflash).

**Tech Stack:** Python 3, pyserial, Marlin `bugfix-2.1.x` on a BigTreeTech SKR Pico.

**Spec:** No separate spec file. Decisions from chat on Oct 18:
- Solenoids are added on the board's FAN2 and FAN3 connectors, next to the existing one on FAN1.
- They sit in a row along X, one column apart (assumed to be exactly one cell pitch; verified in Task 2).
- All solenoids that have a raised cell under them fire together at each stop.
- Board connector labels are one higher than Marlin's fan numbers: the solenoid on FAN1 answered to `M106 P0`. So FAN2 = `P1`, FAN3 = `P2` (verified in Task 2).

## Global Constraints

- `board.py`, `test_board.py`, `docs/board.md` are Austin's: tell Austin about the change.
- The board section of the `CLAUDE.md` contract changes: tell the whole team (`CLAUDE.md` rule).
- Contract functions keep their signatures: `board.show_grid(grid) -> None`, `board.to_ascii(grid) -> str`.
- Rails: `MAX_X = 130`, `MAX_Y = 150`; every head position stays inside them.
- Tests are plain scripts, no pytest: `python test_board.py`. Keep testing minimal: the tests below plus one run of `test_board.py` and `test_main.py`.
- Never send `G28`. `.env` is never committed.
- Feature freeze 10:00 AM Oct 18, submissions close at noon Pacific.

---

### Task 1: Fire up to three solenoids per stop

**Files:**
- Modify: `board.py` (`FAN` constant, new `stops()`, `gcode()`, failure path in `show_grid`, header comment)
- Test: `test_board.py`

**Interfaces:**
- Consumes: `cell_xy(row, col) -> (x, y)` (unchanged), `PULSE_MS`, `RELEASE_MS`, `SPEED` (unchanged).
- Produces: `board.FANS: tuple[int, ...]` (Marlin fan number per solenoid, left to right); `board.stops(row: list[int]) -> list[tuple[int, list[int]]]`, one entry per stop in left-to-right order: (column under solenoid 0, indexes into `FANS` to fire). `board.gcode(grid) -> list[str]` keeps its signature.

- [ ] **Step 1: Write the failing tests**

In `test_board.py`, replace the whole `test_gcode_fires_after_each_move_in_snake_order` function and the whole `test_failure_releases_the_solenoid` function with:

```python
def test_stops_cover_three_columns_each():
    # Solenoid 0 is under the stop's column; solenoids 1 and 2 are one and two columns to its right.
    assert board.stops([1, 1, 0, 0, 0, 1, 0, 0, 0, 1]) == [(0, [0, 1]), (3, [2]), (7, [2])]
    assert board.stops([0] * 10) == []
    assert board.stops([1] * 10) == [(0, [0, 1, 2]), (3, [0, 1, 2]), (6, [0, 1, 2]), (7, [2])]

def test_gcode_fires_solenoids_together_in_snake_order():
    grid = [[0] * 10 for _ in range(10)]
    grid[0][0] = grid[0][1] = grid[0][2] = 1  # one stop, all three fire
    grid[1][0] = grid[1][9] = 1               # odd row: right stop first
    lines = board.gcode(grid)
    on = [f"M106 P{f} S255" for f in board.FANS]
    off = [f"M107 P{f}" for f in board.FANS]
    assert lines[:10] == [f"G0 X10 Y10 F{board.SPEED}", "M400", *on, f"G4 P{board.PULSE_MS}", *off,
                          f"G4 P{board.RELEASE_MS}"]
    moves = [l for l in lines if l.startswith("G0")]
    assert moves == [f"G0 X{x} Y{y} F{board.SPEED}" for x, y in ((10, 10), (80, 20), (10, 20), (0, 0))]
    assert lines.count(f"G4 P{board.PULSE_MS}") == 3  # one shared pulse per stop

def test_failure_releases_every_solenoid():
    os.environ["BOARD"] = "serial"
    fake = FakeMarlin([])
    board._port = fake
    try:
        board.show_grid(board.PATTERNS["corners"])
    except TimeoutError:
        pass
    assert fake.sent[-len(board.FANS):] == [f"M107 P{f}" for f in board.FANS]
```

(The test cells are `(10, 10)`, `(100, 10)`, `(10, 100)`, so row 1 column 7 is at X `10 + 90 * 7 / 9 = 80`, Y `20`.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `source .venv/bin/activate && python test_board.py`
Expected: FAIL with `AttributeError: module 'board' has no attribute 'stops'`

- [ ] **Step 3: Implement in `board.py`**

Replace the header comment's first two lines:

```python
# The 10x10 pin board: an SKR Pico running Marlin (firmware/) moves a solenoid under the grid on two
# belts and fires it under each cell that should be up. Pins go back down by hand.
```

with:

```python
# The 10x10 pin board: an SKR Pico running Marlin (firmware/) moves a head with three solenoids in a row
# (one column apart) under the grid on two belts, and fires those under cells that should be up.
# Pins go back down by hand.
```

Replace:

```python
FAN = 0          # the solenoid answers to fan 0 (tested on the board): M106 P0 / M107 P0
```

with:

```python
FANS = (0, 1, 2) # Marlin fan of each solenoid, user's left to right (board FAN1, FAN2, FAN3 connectors).
                 # Solenoid 0 is the reference: CELL_* positions are measured with it under the cell.
```

Replace the whole `gcode` function with:

```python
def stops(row):
    """[(column under solenoid 0, [solenoids to fire])] left to right; never past the last full stop."""
    last = 10 - len(FANS)  # 7: the head never goes further right, so no solenoid hangs past the grid
    groups = {}
    for c in range(10):
        if row[c]:
            s = min(c - c % len(FANS), last)
            groups.setdefault(s, []).append(c - s)
    return sorted(groups.items())

def gcode(grid):
    lines = []
    for r, row in enumerate(grid):
        row_stops = stops(row)
        for c, fire in (row_stops if r % 2 == 0 else reversed(row_stops)):  # snake order: shortest path
            x, y = cell_xy(r, c)
            lines += [f"G0 X{x:g} Y{y:g} F{SPEED}",
                      "M400",  # Marlin only loosely syncs the fan output with moves: wait for the head
                      *[f"M106 P{FANS[i]} S255" for i in fire],  # together: one line each, milliseconds apart
                      f"G4 P{PULSE_MS}",
                      *[f"M107 P{FANS[i]}" for i in fire],
                      f"G4 P{RELEASE_MS}"]
    return lines + [f"G0 X0 Y0 F{SPEED}"]  # park in the zero corner; Marlin boots believing it is there
```

In `show_grid`'s `except` block, replace:

```python
            try:
                _port.write(f"M107 P{FAN}\n".encode())  # never leave the solenoid energized after a failure
            except Exception:
                pass
```

with:

```python
            try:
                for f in FANS:  # never leave a solenoid energized after a failure
                    _port.write(f"M107 P{f}\n".encode())
            except Exception:
                pass
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `source .venv/bin/activate && python test_board.py && python test_main.py`
Expected: every line `PASS ...`, including the three new tests; no traceback.

- [ ] **Step 5: Commit**

```bash
git add board.py test_board.py
git commit -m "feat(board): three solenoids in a row fire together, up to 4 stops per row"
```

---

### Task 2: Contract and docs

**Files:**
- Modify: `CLAUDE.md` (the "Board (Marlin G-code over USB, 115200 baud)" section)
- Modify: `docs/board.md` (the Solenoid bullet and the per-cell G-code bullet)

**Interfaces:**
- Consumes: Task 1's `FANS` and stop rule.
- Produces: nothing used by code.

- [ ] **Step 1: Update the contract in `CLAUDE.md`**

Replace these two bullets:

```markdown
- An SKR Pico running Marlin moves a solenoid (on FAN0) under the 10x10 pins on two belts; no endstops.
- Per raised cell, in snake order: `G0 X.. Y..`, `M400`, `M106 S255`, `G4 P50`, `M107`; each line waits
  for Marlin's `ok`. Afterwards the head parks at `X0 Y0`.
```

with:

```markdown
- An SKR Pico running Marlin moves a head with three solenoids in a row (one column apart, on the FAN1,
  FAN2, FAN3 connectors = Marlin fans 0, 1, 2) under the 10x10 pins on two belts; no endstops.
- Each row is split into stops at columns 0, 3, 6, 7, in snake order. Per stop: `G0 X.. Y..`, `M400`,
  `M106 P<fan> S255` for each solenoid under a raised cell, `G4 P50`, `M107 P<fan>` for each; each line
  waits for Marlin's `ok`. Afterwards the head parks at `X0 Y0`.
```

- [ ] **Step 2: Update `docs/board.md`**

Replace the line starting `- **Solenoid:** 12 V DC, 210 mA, wired to **FAN0** (GPIO 17).` and its continuation line with:

```markdown
- **Solenoids:** three, 12 V DC, 210 mA each, in a row along X, one column apart, on the FAN1, FAN2 and
  FAN3 connectors. Marlin numbers fans from 0: FAN1 = `M106 P0`, FAN2 = `P1`, FAN3 = `P2` (tested Oct 18).
  The fan ports pass through the supply voltage and have flyback protection, so no extra diode is needed.
```

Replace the line starting `- Per raised cell, in snake order:` and its two continuation lines with:

```markdown
- Each row is split into stops at columns 0, 3, 6, 7 (the stop at 7 only fires solenoid 2, for column 9),
  in snake order. Per stop: `G0 X.. Y..`, `M400`, `M106 P<fan> S255` for each solenoid under a raised cell,
  `G4 P50`, then `M107 P<fan>` for each, `G4 P30`. `M400` matters: Marlin only loosely syncs the fan
  output with moves, so without it the solenoids fire early. Afterwards the head parks at `X0 Y0`.
```

- [ ] **Step 3: Commit and tell the team**

```bash
git add CLAUDE.md docs/board.md
git commit -m "docs: board contract for three solenoids firing together"
```

Tell the whole team the board contract changed, and Austin that `board.py`, `test_board.py` and `docs/board.md` changed.

---

### Task 3: Check the wiring and layout on the board (hands-on)

**Files:**
- Modify: `board.py` `FANS` line, only if the order on the board differs

**Interfaces:**
- Consumes: Task 1's `FANS`.
- Produces: a `FANS` tuple that matches the board, left to right.

- [ ] **Step 1: Power up**

Power off. Head in the zero corner, pins flat. USB Power cap off, 12 V on, then USB. Check: `ls /dev/cu.usbmodem*`.

- [ ] **Step 2: Fire each solenoid alone**

```bash
source .venv/bin/activate
python -m serial.tools.miniterm /dev/cu.usbmodem2101 115200 -e
```

Send each group and note which solenoid moves (leftmost, middle, rightmost, seen from the user):

```
M106 P0 S255
G4 P100
M107 P0
```

Repeat with `P1`, then `P2`.

- [ ] **Step 3: Set the order**

If P0 is leftmost, P1 middle, P2 rightmost: no change. Otherwise write the fan numbers left to right into `FANS` in `board.py`; for example if P2 is leftmost and P0 rightmost: `FANS = (2, 1, 0)`.

- [ ] **Step 4: Fire all three together**

```
M106 P0 S255
M106 P1 S255
M106 P2 S255
G4 P100
M107 P0
M107 P1
M107 P2
```

Expected: all three push out together. If the board browns out (resets, `M115` banner reappears) the 12 V supply is too weak for three at once (3 x 210 mA): stop and tell the team.

- [ ] **Step 5: Check the spacing**

With the head under any cell, check by eye that the middle and right solenoids sit under the next two columns' pins. If they don't line up with the pins, stop: the stop rule assumes exactly one column apart.

- [ ] **Step 6: Commit if `FANS` changed**

```bash
git add board.py
git commit -m "chore(board): solenoid order left to right as wired"
```

Calibration (`CELL_0_0`, `CELL_0_9`, `CELL_9_0` with solenoid 0 under each cell, steps per mm, pulse length) and the end-to-end test follow Tasks 3 and 4 of `docs/superpowers/plans/2026-10-18-hardware-demo.md` unchanged; `python board.py corners` then fires solenoid 0 at column 0 and solenoid 2 at column 9 on rows 0 and 9.
