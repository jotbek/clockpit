"""Monotonic millisecond deadlines; independent of RTC changes and float32."""
import time


ticks_ms = getattr(time, 'ticks_ms', lambda: int(time.monotonic() * 1000))
ticks_add = getattr(time, 'ticks_add', lambda current, delta: current + delta)
ticks_diff = getattr(time, 'ticks_diff', lambda end, start: end - start)
