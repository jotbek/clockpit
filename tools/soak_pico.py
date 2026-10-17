"""Long hardware test: stop main.py, then import soak_pico; soak_pico.run().

Copy this tool to /soak_pico.py. Reports go to the terminal, not to flash.
Uses nominal 125 MHz by default and drives the LEDs to exercise the real path.
"""
import gc
import time


def run(hours=8, cpu_hz=125000000, overlay=False):
    import machine
    from neopixel import NeoPixel
    from animations.mod_donut import Donut
    from core.display import MatrixDisplay
    from core.health import RuntimeHealth, save_failure
    from core import timing

    if hours <= 0:
        raise ValueError('hours must be positive')
    machine.freq(cpu_hz)
    pixels = NeoPixel(machine.Pin(22), 256)
    display = MatrixDisplay(pixels, 16, 16)
    animation = Donut(16, 16)
    clock = None
    if overlay:
        from animations.mod_clock import Clock
        clock = Clock(16, 16)
    health = RuntimeHealth()
    gc.collect()
    baseline = gc.mem_free()
    minimum = baseline
    report_at = timing.ticks_ms()
    frames = 0
    duration_ms = int(hours * 3600000)
    print('Donut soak: CPU={} Hz, overlay={}, start free={} B'.format(cpu_hz, overlay, baseline))
    print('uptime_s, frames/s, free_after_gc, delta_from_start, minimum_free')
    try:
        while health.uptime_ms < duration_ms:
            full, delay, changes = animation.get()
            display.apply(full, changes, 96)
            changes = None
            if clock is not None:
                clock_frame = clock.get()[2]
                display.show_overlay(clock_frame, 96)
                clock_frame = None
            else:
                pixels.write()
            frames += 1
            minimum = min(minimum, gc.mem_free())
            time.sleep(delay)
            health.poll()
            now = timing.ticks_ms()
            elapsed = timing.ticks_diff(now, report_at)
            if elapsed >= 30000:
                free = health.free_after_gc
                print(health.uptime_ms // 1000, frames * 1000 / elapsed,
                      free, free - baseline, minimum)
                frames = 0
                report_at = now
    except Exception as error:
        gc.collect()
        save_failure(error, 'Donut soak uptime_ms={} cpu_hz={} overlay={}'.format(
            health.uptime_ms, cpu_hz, overlay))
        raise
    finally:
        display.clear()
        pixels.write()
    print('Soak completed; uptime={} s, free after GC={} B'.format(
        health.uptime_ms // 1000, health.free_after_gc))
