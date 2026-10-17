# Long-running stability review

Reviewed on 2026-10-15 after a reported freeze while Donut was active. The board's firmware build, final serial output, overlay state, and reset cause at the time of that incident were unavailable. The specific cause of that freeze remains unconfirmed.

## Scope and findings

The review covered the firmware loop, controls, initialization, imports/unloading, display buffers, all 14 animation modules, simulator lifecycle/GUI ownership, and profiling tools. Existing uncommitted Viper changes were retained.

| Area | Finding | Change |
| --- | --- | --- |
| CPU clock | Startup requested 250 MHz. Acceptance by `machine.freq()` does not demonstrate sustained hardware stability. | Default clock is now nominal 125 MHz. In `core/init.py`, `OVERCLOCK_ENABLED = False` keeps the optional 250 MHz target disabled. Its involvement in the reported freeze is a hypothesis. |
| Spiral scheduling | Adding fractional intervals to a large RTC timestamp loses short intervals with float32. Wall-clock correction also changes deadlines. | Use monotonic millisecond deadlines and `ticks_add`/`ticks_diff`. |
| Maze pause | `time.time() + 0.5` can round by many seconds with float32. | Use a 500 ms monotonic deadline. |
| Game of Life reset | Reset timing depended on wall-clock time. | Use monotonic milliseconds, including tick rollover. |
| Clock DST | Transition hours were local-time values compared with a UTC RTC. | Both transitions now use 01:00 UTC on the relevant last Sunday. |
| Donut projection | Viper pointer reads have no bounds checks. Valid poses in testing stayed inside the reciprocal table, but the read itself was unguarded. | Check the projection index against the actual table length before dereferencing. This is defensive hardening, not a reproduced cause of the incident. |
| Runtime exceptions | A stopped Python loop leaves addressable LEDs displaying their last frame, resembling a hardware hang when serial output is unavailable. | Save one overwritten crash report with stage/module/uptime/free heap and traceback before propagating the exception. |
| Heap observability | Current free heap includes temporary garbage and cannot alone identify retained allocations. | Collect every 30 seconds and report latest/minimum post-GC free heap, plus monotonic uptime. |
| Network startup | Initialization called `sys.exit()` after connection/NTP failure, so the caller's `RuntimeError` handler could not continue. Wi-Fi was left active although unused after startup. | Continue with the current RTC on failure, and deactivate Wi-Fi after the NTP attempt. |
| Simulator ownership | Two runtimes could replace each other's process-wide firmware stubs and GC state. A thread-start failure could leave GC disabled. | Reject overlapping runtimes and release ownership/restore GC on startup failure and completed shutdown. |
| Pico profiler | One `ticks_us` difference over an arbitrarily long run can exceed the tick half-period. | Sum short per-frame differences; reject a non-positive frame count. |

## Donut arithmetic and memory

- `angle_x` and `angle_y` are reduced modulo `2*pi` after every frame. They do not grow with uptime. Floating-point rotation may accumulate small phase differences, but it does not approach floating overflow during normal execution.
- Ring/tube geometry, coefficients and depth state use fixed-size arrays. RGB is a reused byte buffer. No frame history, growing actor list, or accumulated geometry is retained.
- Surface and rotation coefficients use Q12. For the 16x16 configuration, products in projection, geometry and lighting fit signed 32-bit arithmetic. Checked-pointer tests exercise 576 combinations of two rotation axes; an additional set executes the actual kernel with signed 32-bit intermediate wrapping and compares output with the desktop algorithm.
- A shortened/empty reciprocal table is now handled without an out-of-range native read.
- Repeated desktop frames did not show retained allocation growth above the test's 1024-byte allowance after collection. A separate 400-frame traced check during review observed a zero-byte retained delta. These are CPython measurements, not Pico heap measurements.

## Other long-run state

- Rainbow hue counters, Vortex phase, Lava sine phases, Maze hue offsets and Spiral marker hues are bounded by explicit modulo operations.
- Fire Plasma's normal damping keeps its 16-bit heat field bounded; its Q12 sums/products fit 32 bits. Fireplace's later visual revision uses two bounded heat fields, coherent fuel controls, a fixed palette and at most four fading particles. Its tests cover buffer reuse, edge interpolation and signed 32-bit execution; the old visual-parity test was replaced when its appearance was intentionally changed. Mandelbrot's Q26 kernel is checked against arbitrary-precision multiplication and signed 32-bit arithmetic.
- Game of Life uses two fixed grids. Matrix Rain uses one fixed RGB buffer. Santa Tree retains a fixed list of sparkle pixels. Ray Bouncer tracks bounded active pixels and removes extinguished trails.
- Maze regeneration and Spiral/Ray Bouncer change lists allocate temporary Python objects, but their retained state is bounded by the matrix size/actor limits. Allocation churn and fragmentation remain device-level concerns; no growing retained container was found in these paths.
- Module switching drops frame references and releases both the `sys.modules` entry and parent package attribute. Regression tests verify that old animation instances/modules can be collected.
- Frame statistics reset every five seconds and already use `ticks_diff`. Button-repeat deadlines already use `ticks_add`/`ticks_diff`. No simple uptime counter overflow was identified in these paths.
- The GUI keeps one newest frame and fixed canvas items. Worker commands have a 128-entry limit, and Tk garbage collection remains on the GUI thread. Python integers used for desktop frame/command counters grow in precision rather than wrapping at 32 bits.

## Validation and device follow-up

Host checks include full firmware/simulator regression tests, monotonic deadline rollover, more than one full millisecond tick period of accumulated uptime, crash-report overwrite/write failure, initialization without a network, watchdog feed ordering, and simulator ownership/startup failure. Changed firmware sources also compile with `mpy-cross` for `armv6m`.

At the original review checkpoint, all 63 tests passed (54.375 seconds), and all 11 firmware/tool sources changed in the audit compiled for ARMv6-M. The desktop retention test additionally renders 5000 frames after its traced comparison to check bounded phases and buffer reuse.

For a physical reproduction, copy the updated firmware (including `core/native.py`, `core/timing.py`, and `core/health.py`), then stop `main.py` and copy `tools/soak_pico.py` to `/soak_pico.py`:

```python
import soak_pico
soak_pico.run(hours=8)
```

This exercises Donut, rendering and real LED writes at 125 MHz. Repeat with `overlay=True` if applicable. Capture serial output, including firmware build from normal startup and post-GC heap measurements. A persistent fall in post-GC heap on the same animation warrants investigation; temporary decreases before collection do not establish a leak. The soak tool itself keeps all reports in the terminal rather than appending to flash.

If Python raises, inspect `/clockpit-crash.log`. A hard CPU/firmware lock cannot execute the exception logger. Optional unattended recovery is available through `main.py:WATCHDOG_TIMEOUT_MS = 8000`; its default remains `0` for interactive debugging. It starts after network initialization and is fed after a successful frame. Once enabled, stopping at the REPL also leads to a watchdog reset.

No multi-hour physical test was run during this review, so sustained hardware/firmware stability, supply behaviour, and the original freeze mechanism remain unverified.

References: [MicroPython time and tick arithmetic](https://docs.micropython.org/en/latest/library/time.html), [Viper pointer restrictions](https://docs.micropython.org/en/latest/reference/speed_python.html#the-viper-code-emitter), [RP2040 specifications](https://www.raspberrypi.com/products/rp2040/specifications/), [MicroPython watchdog](https://docs.micropython.org/en/latest/library/machine.WDT.html).
