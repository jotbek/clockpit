# Development

## Layout

| Path | Purpose |
| --- | --- |
| `main.py` | Application loop, controls and configuration |
| `core/` | Hardware setup, display, colours, fonts, loading and diagnostics |
| `animations/` | Modules loaded on demand |
| `simulator/` | Tkinter GUI and desktop hardware/time stubs |
| `tests/` | Firmware, native arithmetic and simulator regression tests |
| `tools/` | Desktop benchmark, Pico profiler, Donut soak test and animation preview renderer |
| `models/enclosure/` | Bambu Studio enclosure projects, standalone STL meshes and geometry validation |
| `docs/enclosure.md` | Enclosure versions, printing settings, material assignment and assembly |
| `docs/wiring.md` | Hardware connections, both power-switch variants and USB supply procedure |

## Animation API

Create `animations/mod_example.py` with a class accepting `(xres, yres)`. Its `get()` returns:

```python
(is_full_frame, delay_seconds, changes)
```

- Full frame: reusable RGB `bytearray`, length `xres * yres * 3`; pixel offset `(x * yres + y) * 3`. Legacy `frame[x][y]` matrices also work.
- Incremental frame: sequence of `(x, y, (r, g, b))`; omitted pixels retain their colour.
- Delays are in **seconds**, including the legacy `delay_ms` variable in `main.py`.

Register `('animations.mod_example', 'Example', xres, yres)` in `main.py`. The loader currently forwards only the resolution, so configure other parameters through constructor defaults or extend `create_module()`. On switches it releases the module cache entry and parent package attribute. Reuse buffers and keep retained state bounded.

| Module | Default delay | Other timing controls |
| --- | --- | --- |
| Donut | 0 s | `speed=0.04` radians/frame; second axis runs at 65% |
| Fireplace | 0.02 s | Fuel changes gradually; at most four fading sparks |
| Color Vortex | 0.1 s | `speed=0.2` radians/frame |
| Game of Life | 0.1 s | Separate 0.5 s reset pause |
| Day Cycle | 0.25 s | Rebuilds the sky once per local RTC second; sunrise 06:00, sunset 18:00 |

Frame preparation and LED output add to these delays. Spiral, Maze and Game of Life use monotonic, wrap-safe deadlines rather than RTC timestamps.

Clock and Day Cycle share Polish DST rules in `core/localtime.py`. Day Cycle uses fixed, configurable local daylight hours rather than astronomical times; the moon is a decorative crescent. Its RGB frame and ridge use 784 buffer bytes at 16x16, excluding object overhead. The simulator's virtual clock controls the sky too.

## Native rendering

[Viper](https://docs.micropython.org/en/latest/reference/speed_python.html#the-viper-code-emitter) compiles selected integer loops to machine code on Pico. `core/native.py` supplies desktop buffer views; the simulator runs the same algorithms without native acceleration.

| Module | Native work |
| --- | --- |
| Donut | Q12 geometry, lighting, depth buffer and projection through a reciprocal table |
| Fire Plasma | Q12 heat propagation and palette mapping |
| Fireplace | Double-buffered heat flow, spatial/temporal smoothing and subpixel spark rendering |
| Rainbow / Color Vortex | RGB interpolation or angle lookup using a precomputed hue palette |
| Mandelbrot | Q26 escape iterations and palette lookup; 13-bit multiplication limbs keep intermediates within 32 bits |

Donut uses 48 ring × 24 tube samples, a 192-entry reciprocal table and reused buffers totalling 2066 bytes at 16x16. Mandelbrot's buffers total 2238 bytes. These figures exclude object overhead, compiled code and application display buffers. Donut follows the [original torus derivation](https://www.a1k0n.net/2011/07/20/donut-math.html) and [fixed-point optimisation](https://www.a1k0n.net/2021/01/13/optimizing-donut.html).

## Diagnostics and profiling

Regenerate the README previews with `python tools/render_previews.py` (desktop only; requires Pillow). Pass class names to update selected GIFs, for example `python tools/render_previews.py Fireplace DayCycle`. The exporter uses animation code and the shared display renderer with a deterministic virtual clock. Zero-delay modules use a nominal 25 updates/s; output is 160x160 at about 12 FPS.

`DEBUG_STATS` and `STATS_INTERVAL_US` in `main.py` control periodic logs (default: every 5 seconds).

- **FPS (updates):** generated animation frames per second, including updates without LED writes.
- **render avg/max:** preparation time including generation, rendering, overlay and LED output.
- **render share:** preparation time divided by elapsed time; excludes controls, feedback banners and deliberate delays. It is not total CPU utilization.
- **free after GC/min:** latest/minimum free Python heap after 30-second memory maintenance. Collection runs independently of periodic logging.

The simulator's heap figures are synthetic; its diagnostic timing uses real time regardless of simulation speed. Only one runtime can own the process-wide firmware stubs. GUI updates and garbage collection stay on the GUI thread. Tk tests use a hidden window and skip if no display is available.

Desktop benchmark (not a Pico performance measurement):

```bash
python tools/benchmark_desktop.py
```

For Pico timing and RAM, stop `main.py`, copy `tools/profile_pico.py` to `/profile_pico.py`, then run in the REPL:

```python
import profile_pico
profile_pico.run(1000)
```

The profiler measures frame generation and rendering, excluding deliberate delays and LED transfer; it does not light the LEDs. It reports free heap before loading, with animation state allocated, and the minimum observed during the run.

See the [stability review](stability-review.md#validation-and-device-follow-up) for crash-report interpretation, watchdog behaviour and the physical 8-hour Donut test. Desktop tests do not certify Pico FPS or long-running hardware stability.
