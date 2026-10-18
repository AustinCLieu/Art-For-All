# Board firmware

The board is a BigTreeTech SKR Pico V1.0 running stock Marlin (`bugfix-2.1.x`), configured with these
two files. Two belt-driven steppers (X, Y) move a 12 V solenoid under the 10x10 pins; the solenoid is on
FAN0, so `M106 S255` fires it and `M107` releases it. There are no endstops. `board.py` sends G-code
over USB.

## Build and flash
1. Download Marlin `bugfix-2.1.x` from github.com/MarlinFirmware/Marlin into `Marlin-bugfix-2.1.x/`
   (ignored by git) and copy these two files into its `Marlin/` folder.
2. In its `platformio.ini`, set `default_envs = SKR_Pico`. Build with PlatformIO (VS Code, the check mark).
3. Power off, hold BOOT, plug in USB, copy `.pio/build/SKR_Pico/firmware.uf2` onto the RPI-RP2 drive.

Changes from Marlin's defaults: `MOTHERBOARD BOARD_BTT_SKR_PICO`, `SERIAL_PORT -1` (USB), `BAUDRATE 115200`,
`EXTRUDERS 0`, no thermistors, TMC2209 drivers, 3-value steps/feedrate/acceleration arrays, and
`AXIS_RELATIVE_MODES` with 3 values. The fan-voltage jumper must be on 12 V.

## Before every demo
1. Power off. Push the head by hand to the zero corner. Marlin boots believing it is there.
2. Power on (the motors need the main supply, not just USB). Never send `G28`: there are no endstops.
3. Press all pins down.

## Calibrate once (fills in `board.py`)
Open a serial monitor (`python -m serial.tools.miniterm <SERIAL_PORT> 115200 -e`, Ctrl+] quits) and
send `G91` (relative moves).
1. **Steps per mm:** `G0 X100 F1500`, measure how far it went, and set new = 80 x 100 / measured in
   `STEPS_PER_MM` in `board.py` (sent with `M92` on connect, so no reflash; in the monitor, try it with
   `M92 X..`). Same for Y.
2. **Zero corner:** pick the corner from which `G0 X5` and `G0 Y5` both move into the grid. Then no
   direction needs flipping in the firmware.
3. **Cell positions:** move the head under cell row 0 col 0 (far left, from the user's side) with small
   `G0 X.. Y..` steps and send `M114`, which prints the head's position. Repeat for row 0 col 9 (far
   right) and row 9 col 0 (near left). Put the three X/Y pairs into `CELL_0_0`, `CELL_0_9`, `CELL_9_0`.
4. Check: with `BOARD=serial` and `SERIAL_PORT` in `.env`, run `python board.py corners`, then `border`. It prints how long the shape took;
   the voice agent waits 23 s per shape.
