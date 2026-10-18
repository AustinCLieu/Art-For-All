# Board: hardware and software handoff

Status on Oct 18: firmware flashed and answering; `board.py` written and tested offline, but never run on
the moving machine. Next: hand test and calibration on Harvey's Mac, then a real tour.

## The machine
- **A plotter for pins.** Two stepper motors (X, Y) on GT2 belts move a head under a 10x10 grid of pins.
  At each cell that should be up, a solenoid on the head fires and pushes that pin up.
- **Pins go back down by hand.** The board can only raise pins: a new shape lands on top of the old one
  unless someone presses the board flat first.
- **Controller:** BigTreeTech SKR Pico V1.0 (RP2040 chip, 4 built-in TMC2209 drivers in UART mode).
  Manual and diagrams: github.com/bigtreetech/SKR-Pico.
- **Solenoids:** three, 12 V DC, 210 mA each, under one bar that pushes a single pin (about 3x the force).
  They are on the FAN1, FAN2 and FAN3 connectors and always fire together. Marlin numbers fans from 0:
  FAN1 = `M106 P0`, FAN2 = `P1`, FAN3 = `P2` (to be confirmed on the board).
  The fan ports pass through the supply voltage and have flyback protection, so no extra diode is needed.
- **Power:** 12 V supply into the screw terminals. USB alone powers only the chip, not motors or solenoid.
- **No endstops.** Marlin boots believing the head is at X0 Y0, so the head must sit in the zero corner
  at power-on.

## Firmware (`firmware/`)
- Stock Marlin `bugfix-2.1.x`, PlatformIO env `SKR_Pico`. Our changes are listed in `firmware/README.md`;
  the two config files there are the full source of truth.
- Flashed from Austin's Windows laptop on Oct 18. `M115` answered `FIRMWARE_NAME:Marlin bugfix-2.1.x`,
  `EXTRUDER_COUNT:0`. It stays on the board: **don't reflash unless a setting can't be fixed from Python.**
- Rebuilding needs Marlin + PlatformIO, which only Austin's laptop has (`Marlin-bugfix-2.1.x/`, ignored by
  git). Flashing: jumper cap on the BOOT pins (below the BIGTREETECH logo, right of the RP2040), a cap on
  USB Power (next to USB-C) if the 12 V supply is off, press Reset, copy `firmware.uf2` onto the RPI-RP2
  drive. Then remove the BOOT cap and press Reset. If the BOOT cap stays on, the board never runs Marlin.

## Software (`board.py`, `test_board.py`)
- Same contract as before: `show_grid(grid)` and `to_ascii(grid)`. `main.py` needs no changes.
- `BOARD=sim` prints the shape. `BOARD=serial` talks G-code to Marlin on `SERIAL_PORT` at 115200 baud.
- On connect: `M84 S0` (motors keep holding; Marlin releases them after 2 idle minutes otherwise),
  `M92 X.. Y..` from `STEPS_PER_MM`, `G90`, `G0 X0 Y0` (back to the corner if main.py restarted mid-shape).
- Per raised cell, in snake order: `G0 X.. Y..`, `M400`, then `PRESSES` (3) times: `M106 P0 S255`,
  `M106 P1 S255`, `M106 P2 S255`, `G4 P50`, `M107 P0`, `M107 P1`, `M107 P2`, `G4 P30`. `M400` matters:
  Marlin only loosely syncs the fan output with moves, so without it the solenoids fire early.
  Afterwards the head parks at `X0 Y0`.
- Every line waits for Marlin's `ok`, skipping `echo:busy` lines. Silence for 5 s or an `Error` raises;
  the port is dropped and the next shape reconnects. `main.py` catches the error, so the voice tour goes on.
- `CELL_0_0`, `CELL_0_9`, `CELL_9_0` are `None` until measured. `show_grid` refuses to move until they are
  set, so it never drives the head on a guess.
- `python board.py corners|border|checker` raises a test pattern and prints how long it took.
- `python test_board.py` runs offline against a fake Marlin.

## Mac setup and calibration
1. `git pull`. Board: BOOT pins empty, USB Power cap off. Push the head by hand to a corner.
2. 12 V on, USB into the Mac. Port: `ls /dev/cu.usbmodem*`.
3. Monitor: `python -m serial.tools.miniterm /dev/cu.usbmodemXXXX 115200 -e` (Ctrl+] quits).
   Send `M115` (Marlin answers), `G91` (relative moves), then small steps: `G0 X5 F1500`, `G0 Y5 F1500`.
4. **Zero corner:** use the corner from which `+X` and `+Y` both move into the grid. Then no firmware
   direction flip is needed. Move there, power-cycle, or send `G92 X0 Y0`.
5. **Steps per mm:** `G0 X100`, measure the distance with a ruler. New value = 80 x 100 / measured. Try it
   live with `M92 X..`, then put it in `STEPS_PER_MM`. Same for Y. 80 = 20-tooth pulley, 100 = 16-tooth.
6. **Solenoid:** `M106 S255`, `G4 P50`, `M107`. Check that the pin goes fully up; if not, raise `PULSE_MS`.
7. **Cell positions:** with `G90` and `G0 X.. Y..`, move under cell row 0 col 0 (far left, seen from the
   user), send `M114` and note X/Y. Repeat for row 0 col 9 (far right) and row 9 col 0 (near left).
   Put them in `CELL_0_0`, `CELL_0_9`, `CELL_9_0`. Row 0 = edge farthest from the user, col 0 = user's left.
8. `.env`: `BOARD=serial`, `SERIAL_PORT=/dev/cu.usbmodemXXXX`. Press the board flat, run
   `python board.py corners`, then `border`, then `python main.py`.

## Rules
- **Never send `G28`.** There are no endstops, so homing drives the motors into the end of the rails.
- Wire only with the power off; never plug or unplug a motor while the board is powered.
- Keep the first moves small (5 mm). A move toward the zero corner crashes into the frame.
- If the board was power-cycled with the head elsewhere, push it back to the corner first.

## Timing
The voice agent waits 23 s for `show_section`. Expect about 0.25 s per raised cell, so 40-60 cells take
10-15 s. Measure with `python board.py checker` (50 cells). Too slow: raise acceleration
(live with `M201 X.. Y..` for the limit and `M204 T..` for travel moves; add them to `_connect` to keep them). Skipping or wobbling: lower `SPEED`.

## Troubleshooting
- No `/dev/cu.usbmodem*`: try another cable (some only charge); check that the BOOT pins are empty.
- `TMC CONNECTION ERROR` or motors dead: the 12 V supply is off.
- Wrong direction: pick another zero corner (step 4).
- Shapes stretched or shifted: re-measure `STEPS_PER_MM` and the three cells.
- Head drifts after a pause: check that `M84 S0` was sent (it is part of connect).

## Open questions
- Who presses the pins down between shapes, and when? (a) The guide asks the visitor ("press the board
  flat, then say next"): a change to the ElevenLabs agent prompt. (b) A teammate does it on stage.
- Does the head need to park out of the way so that pins can be pressed down? It parks at `X0 Y0` now.
- Pulse length: is 50 ms enough? Speed: is 300 mm/s at 3000 mm/s² OK for the frame?
