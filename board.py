# The 10x10 pin board: an SKR Pico running Marlin (firmware/) moves a head under the grid on two belts.
# The head has three solenoids under one bar: for each cell that should be up, all three fire together,
# PRESSES times, to push that one pin up. Pins go back down by hand.
# Env: BOARD=sim|serial, SERIAL_PORT (e.g. /dev/tty.usbmodem1101 or COM5)
# Test on the real board: python board.py corners|border|checker
import os, time
import serial

# Head position in mm (Marlin's M114) under three cells: row 0 col 0, row 0 col 9 and row 9 col 0.
# Row 0 = edge farthest from the user, col 0 = user's left. Measure them: firmware/README.md.
# Oct 18, +X = user's right, +Y = away from the user, pins 5 mm apart (a 45 x 45 mm grid):
CELL_0_0 = (45, 62)    # top left, derived (same X as the bottom left, same Y as the top right)
CELL_0_9 = (90, 62)    # top right, measured
CELL_9_0 = (45, 17)    # bottom left, measured
MAX_X = 130      # end of the X rail in mm (measured by hand): no endstops, so board.py refuses to go past it
MAX_Y = 150      # end of the Y rail in mm (measured by hand)
STEPS_PER_MM = (80, 80)  # X, Y; sent on connect, so fixing it needs no reflash (firmware/README.md)
SPEED = 18000    # mm/min between cells (Marlin caps it at DEFAULT_MAX_FEEDRATE, 300 mm/s)
FANS = (0, 1, 2) # Marlin fan of each solenoid (board FAN1, FAN2, FAN3 connectors); all push the same pin
PRESSES = 3      # pushes per pin
PULSE_MS = 50    # how long the solenoids stay out
RELEASE_MS = 30  # lets the plungers drop back before the next push or the next cell

_port = None

def to_ascii(grid):
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)

def cell_xy(row, col):
    (x0, y0), (xc, yc), (xr, yr) = CELL_0_0, CELL_0_9, CELL_9_0
    x = x0 + (xc - x0) * col / 9 + (xr - x0) * row / 9
    y = y0 + (yc - y0) * col / 9 + (yr - y0) * row / 9
    if x < 0 or y < 0 or (MAX_X is not None and x > MAX_X) or (MAX_Y is not None and y > MAX_Y):
        raise ValueError(f"Cell {row},{col} is at X{x:g} Y{y:g}, outside the rails (0 to X{MAX_X} Y{MAX_Y})")
    return round(x, 2), round(y, 2)

def gcode(grid):
    lines = []
    push = [*[f"M106 P{f} S255" for f in FANS],  # all three together: one line each, milliseconds apart
            f"G4 P{PULSE_MS}",
            *[f"M107 P{f}" for f in FANS],
            f"G4 P{RELEASE_MS}"] * PRESSES
    for r, row in enumerate(grid):
        for c in (range(10) if r % 2 == 0 else range(9, -1, -1)):  # snake order: shortest path
            if row[c]:
                x, y = cell_xy(r, c)
                lines += [f"G0 X{x:g} Y{y:g} F{SPEED}",
                          "M400",  # Marlin only loosely syncs the fan output with moves: wait for the head
                          *push]
    return lines + [f"G0 X0 Y0 F{SPEED}"]  # park in the zero corner; Marlin boots believing it is there

def _send(line):
    _port.write(f"{line}\n".encode())
    while True:  # skip echo:busy and other chatter until the ok
        reply = _port.readline().decode(errors="replace").strip()
        if reply.startswith("ok"):
            return
        if not reply:
            raise TimeoutError(f"Board did not answer {line!r}")
        if reply.startswith("Error"):
            raise RuntimeError(f"Board: {reply}")

def _connect():
    global _port
    _port = serial.Serial(os.environ["SERIAL_PORT"], 115200, timeout=5)
    _port.reset_input_buffer()
    _send("M84 S0")  # keep the motors holding; Marlin lets go after 2 idle minutes otherwise
    _send(f"M92 X{STEPS_PER_MM[0]} Y{STEPS_PER_MM[1]}")
    _send("G90")
    _send(f"G0 X0 Y0 F{SPEED}")  # back to the corner if main.py restarted mid-shape

def show_grid(grid):
    """Raise the pattern; returns once the last pin is up. Pins already up stay up."""
    global _port
    if os.getenv("BOARD", "sim") != "serial":
        print(to_ascii(grid))
        return
    if None in (CELL_0_0, CELL_0_9, CELL_9_0):
        raise RuntimeError("Measure CELL_0_0, CELL_0_9 and CELL_9_0 in board.py first (firmware/README.md)")
    try:
        if _port is None:
            _connect()
        for line in gcode(grid):
            _send(line)
    except Exception:  # reconnect next time, with a clean input buffer
        if _port:
            try:
                for f in FANS:  # never leave a solenoid energized after a failure
                    _port.write(f"M107 P{f}\n".encode())
            except Exception:
                pass
            _port.close()
        _port = None
        raise

PATTERNS = {
    "corners": [[int(r in (0, 9) and c in (0, 9)) for c in range(10)] for r in range(10)],
    "border": [[int(r in (0, 9) or c in (0, 9)) for c in range(10)] for r in range(10)],
    "checker": [[int((r + c) % 2 == 0) for c in range(10)] for r in range(10)],
}

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    grid = PATTERNS[sys.argv[1] if len(sys.argv) > 1 else "corners"]
    t = time.time()
    show_grid(grid)
    if os.getenv("BOARD", "sim") == "serial":
        print(f"{to_ascii(grid)}\nRaised in {time.time() - t:.1f} s (the voice agent waits 23 s)")
