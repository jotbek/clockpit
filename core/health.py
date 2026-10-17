"""Bounded runtime memory observations and one crash report on the device."""
import gc
import sys
from core import timing


class RuntimeHealth:
    def __init__(self, interval_ms=30000):
        self.interval_ms = interval_ms
        self.last_tick = timing.ticks_ms()
        self.next_collection = timing.ticks_add(self.last_tick, interval_ms)
        self.uptime_ms = 0
        self.free_after_gc = None
        self.minimum_free_after_gc = None

    def poll(self):
        now = timing.ticks_ms()
        elapsed = timing.ticks_diff(now, self.last_tick)
        if elapsed >= 0:
            self.uptime_ms += elapsed
        self.last_tick = now
        if timing.ticks_diff(now, self.next_collection) >= 0:
            gc.collect()
            free = gc.mem_free()
            self.free_after_gc = free
            if self.minimum_free_after_gc is None or free < self.minimum_free_after_gc:
                self.minimum_free_after_gc = free
            self.next_collection = timing.ticks_add(now, self.interval_ms)


def save_failure(error, context, path='clockpit-crash.log'):
    """Overwrite a single report only on failure; never replace the exception."""
    try:
        with open(path, 'w') as output:
            output.write(context + '\n')
            print_exception = getattr(sys, 'print_exception', None)
            if print_exception is not None:
                print_exception(error, output)
            else:
                # Desktop only; traceback is not a firmware dependency.
                import traceback
                traceback.print_exception(type(error), error, error.__traceback__, file=output)
        return True
    except Exception:
        return False
