# Clockpit

Clockpit runs a digital clock and 12 animations on a 16x16 RGB LED matrix driven by a Raspberry Pi Pico W and MicroPython. The primary target is efficient execution on RP2040: small reusable buffers, bounded animation state, and loading only the selected animation into RAM.

## Project layout

```text
main.py                     Pico startup entry point and application loop
core/                       Device initialization, rendering, colors, fonts, loading
animations/                 Individual animation modules; imported on demand
simulator/                  Desktop Tkinter GUI and simulation runtime
tests/                     Firmware and simulator regression tests
tools/                     Desktop benchmark and optional Pico profiler
docs/screenshots/          Animation previews
secrets.py                  Local Wi-Fi credentials; ignored by Git
```

MicroPython supports directories and Python packages. Keep `main.py` at the device filesystem root and preserve `core/` and `animations/`, including their `__init__.py` files. Package markers do not import every animation. The desktop simulator, tests, tools, and documentation are not firmware dependencies.

## Hardware and deployment

- Raspberry Pi Pico W running MicroPython.
- A 16x16 RGB NeoPixel matrix on GPIO 22, with serpentine wiring.
- Active-low buttons on GPIO 13 (Up), GPIO 9 (Down), and GPIO 5 (Mode), using pull-ups.
- Wi-Fi credentials for the current startup sequence, which connects and synchronizes the RTC using NTP.

Copy these files and directories to the Pico filesystem:

```text
/main.py
/core/__init__.py
/core/init.py
/core/loading.py
/core/display.py
/core/colors.py
/core/helpers.py
/animations/__init__.py
/animations/mod_*.py
/secrets.py
```

Do not copy `simulator/`, `tests/`, `docs/`, or the desktop benchmark to the device. Create `secrets.py` locally:

```python
wifi_name = 'your_ssid'
wifi_pass = 'your_password'
```

Reset the board after updating the package layout. MicroPython runs `main.py` automatically. The default brightness is 96/255, the display is 16x16, and initialization requests a 250 MHz CPU clock; configure these values in `main.py` and `core/init.py`. Clock rendering converts the NTP-synchronized UTC RTC to Polish local time.

## Controls

Mode cycles through three settings:

| Mode | Up / Down | Display |
| --- | --- | --- |
| 0 | Select the next/previous animation | Selected animation |
| 1 | Adjust brightness in steps of 4, clamped to 0..255 | Selected animation with temporary percentage feedback |
| 2 | Select the next/previous animation | Selected animation with a transparent clock overlay |

A Mode press advances once. Up/Down repeat after an initial hold delay; opposite hardware buttons cancel each other. Selection stays at the first or last module at the corresponding boundary. Temporary symbols and percentages restore the background instead of erasing incremental animations. Brightness changes also update retained pixels, including recovery from brightness zero.

## Terminal diagnostics

At startup, the board reports its installed MicroPython firmware build and board identifier. Configuration logs include current Python heap allocation (used/total/free and percentage), CPU frequency, the selected module, brightness, and the last frame's delay in seconds. Heap allocation covers Python-managed memory, not all physical RAM, and logging does not force garbage collection.

With `DEBUG_STATS = True` in `main.py` (the default), periodic logs also show:

- `FPS (updates)`: animation frames generated per second, including updates that do not write new pixels.
- `render avg/max`: average and maximum frame preparation time in milliseconds, including generation, rendering, clock overlay, and LED output.
- `render share`: percentage of elapsed time spent preparing frames. This measures animation activity, not total CPU utilization; controls, feedback banners, and intentional delays are excluded from preparation time.

`STATS_INTERVAL_US = 5000000` sets a five-second reporting interval; reports are emitted after a frame's delay completes. Changing the animation resets the timing window. Set `DEBUG_STATS = False` to disable periodic timing reports; startup and configuration logs remain enabled.

In the simulator, heap values are synthetic and explicitly labeled, CPU frequency and board firmware are unavailable, and the host Python version is reported instead. Timing statistics use real elapsed time independently of simulation speed. Logs also appear at startup and when controls change the configuration.

## Desktop simulator

Requirements: Python 3.8 or later and Tkinter. No Wi-Fi or Pico hardware is needed. Run from the repository root:

```bash
python -m simulator.gui
```

- Use Up, Down, and Mode for the same actions as the physical buttons. Short clicks are queued reliably; holding Up/Down repeats the action. Keyboard activation works as well.
- The module combobox selects an animation directly in any mode. Pending selections stay visible until the worker acknowledges them.
- Speed - / Speed + select values from **0.01x to 50x**, clamped at both ends. Buttons are disabled at their respective limits.
- Speed scales both animation delays and its virtual clock, including timed events and the clock display. CPU-heavy animations still depend on available desktop CPU time.
- Changing speed or submitting a control wakes the worker immediately, including while it waits at 0.01x. Feedback banners use real time, rather than taking 50 seconds at minimum speed.
- Tkinter displays the newest immutable frame at approximately 30 FPS. Older previews are replaced, not queued indefinitely. All widget updates and Tk object garbage collection stay on the GUI thread.
- Worker errors appear in the status line. Exit or the window close button interrupts waiting, joins the worker, and closes the window cleanly.

Importing `simulator.gui` does not start the application. Simulation stubs are installed only while the runtime is active and are restored on shutdown. Synthetic desktop heap figures are not measurements of Pico RAM.

## Animations

The table matches the selection order in `main.py`.

| Module | Source | Behavior | Preview |
| --- | --- | --- | --- |
| Clock | [source](animations/mod_clock.py) | Hours/minutes, a fading seconds border, local time conversion | [image](docs/screenshots/Simulator_Clock.png) |
| Fire Plasma | [source](animations/mod_fireplasma.py) | Fire propagation using a compact fixed-point heat map | [image](docs/screenshots/Simulator_FirePlasma.png) |
| Game of Life | [source](animations/mod_gameoflife.py) | Conway's cellular automaton with periodic resets | [image](docs/screenshots/Simulator_GameOfLife.png) |
| Spiral | [source](animations/mod_spiral.py) | Colored and erasing markers following a spiral path | [image](docs/screenshots/Simulator_Spiral.png) |
| Matrix Rain | [source](animations/mod_matrixrain.py) | Falling green trails with fading highlights | [image](docs/screenshots/Simulator_MatrixRain.png) |
| Ray Bouncer | [source](animations/mod_raybouncer.py) | Bouncing markers, short fading trails, occasional bursts | [image](docs/screenshots/Simulator_Bounce.png) |
| Color Vortex | [source](animations/mod_vortex.py) | Rotating colors with precomputed angular geometry | [image](docs/screenshots/Simulator_Vortex.png) |
| Lava | [source](animations/mod_lava.py) | Sinusoidal red/green patterns and complementary blue | [image](docs/screenshots/Simulator_Lava.png) |
| Fireplace | [source](animations/mod_fireplace.py) | Sparks and filtered flame colors | [image](docs/screenshots/Simulator_FirePlace.png) |
| Rainbow | [source](animations/mod_rainbow.py) | Moving hue gradients with integer interpolation | [image](docs/screenshots/Simulator_Rainbow.png) |
| Maze | [source](animations/mod_maze.py) | Solvable mazes, color-cycling walls, a moving red trail | [image](docs/screenshots/Simulator_Maze.png) |
| Santa Tree | [source](animations/mod_santatree_16x16.py) | Static tree with incrementally updated sparkling lights | [image](docs/screenshots/Simulator_SanTree.png) |
| Mandelbrot | [source](animations/mod_mandelbrot.py) | Tracks visible fractal boundaries, cycles four starting targets, recovers from empty areas | [image](docs/screenshots/Simulator_Mandelbrot.png) |

Game of Life and Color Vortex both accept a constructor parameter `delay=0.1`, in seconds, giving at most approximately 10 updates per second at normal simulation speed. Increase it to slow frame generation:

```python
GameOfLife(16, 16, delay=0.2)
ColorVortex(16, 16, speed=0.2, delay=0.2)
```

Vortex's `speed` controls rotation per frame; `delay` controls the time between frames. The current loader passes only `(xres, yres)`, so `main.py` uses constructor defaults. To change delays with this loader, edit the defaults in the animation files; explicit overrides in `main.py` require extending `create_module()` to forward constructor parameters. Game of Life retains its separate 0.5-second reset pause.

## Verification and profiling

Run the complete regression suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests cover firmware rendering and animation state, float32 Mandelbrot zoom, diagnostic memory/firmware output and frame timing across tick rollover, 234 worker configurations, minimum/maximum speed, short/held inputs, failure reporting, shutdown, and 78 combinations using actual Tk widgets. GUI tests use a withdrawn test window and close it automatically; they skip when no Tk display is available. Tests do not leave the simulator running.

Desktop CPU/heap comparison:

```bash
python tools/benchmark_desktop.py
python tools/benchmark_desktop.py --baseline PATH_TO_ORIGINAL_FLAT_SOURCES
```

For actual Pico RAM and timing, stop the running firmware, copy `tools/profile_pico.py` as `/profile_pico.py`, and use the REPL:

```python
import profile_pico
profile_pico.run(1000)
```

The profiler generates and renders frames without lighting the LEDs. It reports microseconds per frame and available heap before loading an animation, with its state allocated, and the minimum observed during the run. Desktop measurements cannot certify Pico FPS or the absence of OOM.

## Adding an animation

Create `animations/mod_yourmodule.py` with a class accepting `(xres, yres)`. Its `get()` method returns `(is_full_frame, delay_seconds, changes)`.

- Full frame: a reusable RGB `bytearray` of `xres * yres * 3` bytes, with channel offset `(x * yres + y) * 3`. Legacy `frame[x][y]` matrices are also supported.
- Incremental frame: a sequence of `(x, y, (r, g, b))` entries. Omitted pixels keep their previous values.
- The existing `delay_ms` variable name represents **seconds**, matching `time.sleep()`.

Register `('animations.mod_yourmodule', 'YourModule', xres, yres)` in `main.py`. Keep state and output buffers bounded. On switches, the loader releases both the module cache entry and its parent package attribute before allocating another animation.

## License

This project uses the [MIT License](https://opensource.org/licenses/MIT).
