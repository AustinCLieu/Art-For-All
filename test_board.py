# Run: python test_board.py   (no board needed: a fake serial port answers like Marlin)
import os
import board

board.CELL_0_0, board.CELL_0_9, board.CELL_9_0 = (10, 10), (100, 10), (10, 100)

class FakeMarlin:
    def __init__(self, replies=None):
        self.sent, self.replies = [], replies
    def write(self, data):
        self.sent.append(data.decode().strip())
    def readline(self):
        if self.replies is not None:
            return self.replies.pop(0) if self.replies else b""
        return b"ok\n"
    def close(self):
        pass

def test_to_ascii():
    lines = board.to_ascii(board.PATTERNS["corners"]).split("\n")
    assert len(lines) == 10 and lines[0] == "#........#" and lines[1] == ".........."

def test_cell_positions():
    assert board.cell_xy(0, 0) == (10, 10)
    assert board.cell_xy(0, 9) == (100, 10)
    assert board.cell_xy(9, 9) == (100, 100)
    assert board.cell_xy(4, 2) == (30, 50)

def test_gcode_fires_after_each_move_in_snake_order():
    grid = [[0] * 10 for _ in range(10)]
    grid[0][0] = grid[0][9] = grid[1][0] = grid[1][9] = 1
    lines = board.gcode(grid)
    moves = [l for l in lines if l.startswith("G0")]
    assert moves[:4] == [f"G0 X{x} Y{y} F{board.SPEED}" for x, y in ((10, 10), (100, 10), (100, 20), (10, 20))]
    assert moves[-1] == f"G0 X0 Y0 F{board.SPEED}"  # parks in the corner
    assert lines[:6] == [moves[0], "M400", "M106 S255", f"G4 P{board.PULSE_MS}", "M107", f"G4 P{board.RELEASE_MS}"]
    assert lines.count("M106 S255") == 4 and lines.count("M107") == 4

def test_empty_grid_only_parks():
    assert board.gcode([[0] * 10] * 10) == [f"G0 X0 Y0 F{board.SPEED}"]

def test_sim_prints_and_sends_nothing():
    os.environ["BOARD"] = "sim"
    board._port = FakeMarlin()
    board.show_grid(board.PATTERNS["border"])
    assert board._port.sent == []

def test_serial_waits_for_ok_through_busy_lines():
    os.environ["BOARD"] = "serial"
    board._port = FakeMarlin([b"echo:busy: processing\n", b"ok\n"])
    board._send("M400")
    assert board._port.sent == ["M400"]

def test_serial_error_drops_the_port():
    os.environ["BOARD"] = "serial"
    board._port = FakeMarlin([])  # silence: readline timed out
    try:
        board.show_grid(board.PATTERNS["corners"])
        raise AssertionError("a silent board must raise")
    except TimeoutError:
        pass
    assert board._port is None  # the next shape reconnects

def test_connect_sets_up_marlin():
    os.environ["SERIAL_PORT"] = "COM99"
    fake = FakeMarlin()
    fake.reset_input_buffer = lambda: None
    original, board.serial.Serial = board.serial.Serial, lambda *a, **k: fake
    try:
        board._port = None
        board._connect()
    finally:
        board.serial.Serial = original
    assert fake.sent == ["M84 S0", "M92 X{} Y{}".format(*board.STEPS_PER_MM), "G90", f"G0 X0 Y0 F{board.SPEED}"]

def test_unmeasured_board_refuses_to_move():
    os.environ["BOARD"] = "serial"
    saved = board.CELL_0_0
    board.CELL_0_0 = None
    try:
        board.show_grid(board.PATTERNS["corners"])
        raise AssertionError("must refuse")
    except RuntimeError as e:
        assert "Measure" in str(e)
    finally:
        board.CELL_0_0 = saved

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
