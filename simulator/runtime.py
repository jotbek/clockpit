"""Desktop worker, virtual clock, and synchronized simulator controls."""
from collections import deque
import gc
import math
from pathlib import Path
import sys
import threading
import time
import traceback
import types


SPEED_OPTIONS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0,
                 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 20.0, 50.0)
TICK_PERIOD = 1 << 30


class SimulatorStopped(BaseException):
    """Unwind the worker without treating a requested shutdown as an error."""


class SimulatorRuntime:
    def __init__(self, source=None, quiet=False):
        self.source = Path(source or Path(__file__).resolve().parents[1] / 'main.py')
        self.quiet = quiet
        self.condition = threading.Condition()
        self.ready = threading.Event()
        self.stopped = False
        self.error = None
        self.worker = None
        self.app = None
        self.module_count = 14
        self.commands = deque()
        self.serial = 0
        self.acknowledged = 0
        self.state = {'module': 0, 'mode': 0, 'brightness': 96}
        self.speed = 1.0
        self.elapsed = 0.0
        self.anchor = time.monotonic()
        self.epoch = time.time()
        self.frame = None
        self.frame_count = 0
        self.saved_modules = {}
        self.gc_was_enabled = None

    def _virtual_now(self):
        return self.elapsed + (time.monotonic() - self.anchor) * self.speed

    def simulation_time(self):
        with self.condition:
            return self._virtual_now()

    def set_speed(self, value):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError('Speed must be finite')
        selected = min(SPEED_OPTIONS, key=lambda option: abs(option - value))
        with self.condition:
            self.elapsed = self._virtual_now()
            self.anchor = time.monotonic()
            self.speed = selected
            self.condition.notify_all()
        return selected

    def step_speed(self, direction):
        with self.condition:
            index = SPEED_OPTIONS.index(self.speed)
            index = max(0, min(len(SPEED_OPTIONS) - 1, index + int(direction)))
            return self.set_speed(SPEED_OPTIONS[index])

    def post(self, command, value):
        if command not in ('module', 'mode', 'brightness', 'button'):
            raise ValueError('Unknown simulator command')
        if command == 'button' and value not in ('plus', 'minus', 'mode'):
            raise ValueError('Unknown button')
        if command == 'mode' and value not in (0, 1, 2):
            raise ValueError('Mode must be 0, 1, or 2')
        if command in ('module', 'brightness') and not isinstance(value, int):
            raise ValueError('Module and brightness must be integers')
        if command == 'module' and not 0 <= value < self.module_count:
            raise ValueError('Module index is out of range')
        with self.condition:
            if self.stopped or self.error:
                raise RuntimeError('Simulator worker is not running')
            if len(self.commands) >= 128:
                raise RuntimeError('Too many pending simulator controls')
            self.serial += 1
            self.commands.append((self.serial, command, value))
            self.condition.notify_all()
            return self.serial

    def snapshot(self):
        with self.condition:
            return dict(self.state, speed=self.speed, acknowledged=self.acknowledged,
                        requested=self.serial, error=self.error, frames=self.frame_count,
                        stopped=self.stopped)

    def wait_for(self, serial, timeout=2.0):
        with self.condition:
            completed = self.condition.wait_for(
                lambda: self.acknowledged >= serial or self.error or self.stopped, timeout)
            if self.error:
                raise RuntimeError(self.error)
            return bool(completed and self.acknowledged >= serial)

    def _wait(self, duration, virtual):
        duration = float(duration)
        if duration < 0 or not math.isfinite(duration):
            raise ValueError('Sleep duration must be finite and nonnegative')
        with self.condition:
            now = self._virtual_now if virtual else time.monotonic
            deadline = now() + duration
            if duration == 0:
                self.condition.wait(0.001)
            while True:
                if self.stopped:
                    raise SimulatorStopped()
                # A pending control cancels an animation delay or UI banner.
                if self.commands:
                    return
                remaining = deadline - now()
                if remaining <= 0:
                    return
                self.condition.wait(min(remaining / self.speed if virtual else remaining, 0.05))

    def sleep(self, duration):
        self._wait(duration, virtual=True)

    def ui_sleep(self, duration):
        self._wait(duration, virtual=False)

    def publish_frame(self, pixels):
        with self.condition:
            self.frame_count += 1
            # Always retain the last write, including restoration after a banner.
            # Tk polls this single replaceable snapshot at 30 FPS.
            self.frame = bytes(pixels.buf)

    def take_frame(self):
        with self.condition:
            frame, self.frame = self.frame, None
            return frame

    def _capture_state(self):
        with self.condition:
            self.state = {'module': self.app.selected_module, 'mode': self.app.mode,
                          'brightness': self.app.intense}

    def _apply_next_command(self):
        with self.condition:
            if self.stopped:
                raise SimulatorStopped()
            command = self.commands.popleft() if self.commands else None
        if command is not None:
            serial, name, value = command
            if name == 'module':
                if value != self.app.selected_module:
                    self.app.select_module(value)
            elif name == 'mode':
                self.app.set_mode(value)
            elif name == 'brightness':
                self.app.set_brightness(value)
            else:
                self.app.handle_control(value)
            self._capture_state()
            with self.condition:
                self.acknowledged = serial
                self.condition.notify_all()

    def _make_stubs(self):
        runtime = self

        class Pin:
            IN = PULL_UP = 0
            states = {}

            def __init__(self, pin, *args):
                self.pin = pin

            def value(self):
                return 0 if self.states.get(self.pin, False) else 1

        class NeoPixel:
            ORDER = (1, 0, 2, 3)

            def __init__(self, pin, n, bpp=3):
                self.n, self.bpp = n, bpp
                self.buf = bytearray(n * bpp)

            def __getitem__(self, index):
                return tuple(self.buf[index * self.bpp + self.ORDER[i]]
                             for i in range(self.bpp))

            def __setitem__(self, index, color):
                for i in range(self.bpp):
                    self.buf[index * self.bpp + self.ORDER[i]] = color[i]

            def write(self):
                runtime.publish_frame(self)

        clock = types.ModuleType('time')
        for name in dir(time):
            setattr(clock, name, getattr(time, name))
        clock.sleep = self.sleep
        clock.ui_sleep = self.ui_sleep
        clock.monotonic = self.simulation_time
        clock.time = lambda: self.epoch + self.simulation_time()
        clock.time_ns = lambda: int(clock.time() * 1000000000)
        # MicroPython's NTP-synchronized RTC supplies UTC to mod_clock.
        clock.localtime = lambda seconds=None: time.gmtime(clock.time() if seconds is None else seconds)
        clock.gmtime = clock.localtime
        clock.ticks_us = lambda: int(self.simulation_time() * 1000000) % TICK_PERIOD
        clock.ticks_ms = lambda: int(self.simulation_time() * 1000) % TICK_PERIOD
        clock.ticks_diff = lambda end, start: (end - start + TICK_PERIOD // 2) % TICK_PERIOD - TICK_PERIOD // 2
        clock.ticks_add = lambda current, delta: (current + delta) % TICK_PERIOD
        # Diagnostic timing uses real time even when animation speed is changed.
        clock.stats_ticks_us = lambda: int(time.monotonic() * 1000000) % TICK_PERIOD
        clock.stats_ticks_diff = clock.ticks_diff
        return {
            'machine': types.SimpleNamespace(Pin=Pin),
            'neopixel': types.SimpleNamespace(NeoPixel=NeoPixel),
            'core.init': types.SimpleNamespace(run=lambda: None),
            'time': clock,
            # Tk objects must be finalized on the GUI thread, never this worker.
            'gc': types.SimpleNamespace(collect=lambda: None, mem_free=lambda: 524288,
                                        mem_alloc=lambda: 524288),
        }

    def _install_stubs(self):
        stubs = self._make_stubs()
        names = set(stubs) | {'main', 'core', 'animations'}
        names.update(name for name in tuple(sys.modules) if name.startswith(('core.', 'animations.')))
        self.saved_modules = {name: sys.modules[name] for name in names if name in sys.modules}
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(stubs)

    def _restore_stubs(self):
        names = {'main', 'machine', 'neopixel', 'core.init', 'time', 'gc', 'core', 'animations'}
        names.update(name for name in tuple(sys.modules) if name.startswith(('core.', 'animations.')))
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(self.saved_modules)
        self.saved_modules.clear()

    def _run(self):
        installed = False
        try:
            self._install_stubs()
            installed = True
            self.app = types.ModuleType('main')
            self.app.__file__ = str(self.source)
            if self.quiet:
                self.app.__dict__['print'] = lambda *args, **kwargs: None
            sys.modules['main'] = self.app
            exec(compile(self.source.read_text(encoding='utf-8'), str(self.source), 'exec'),
                 self.app.__dict__)
            self.app.control_hook = self._apply_next_command
            self.module_count = len(self.app.modules)
            self._capture_state()
            self.ready.set()
            self.app.run()
        except SimulatorStopped:
            pass
        except BaseException as error:
            with self.condition:
                self.error = '{}: {}'.format(type(error).__name__, error)
                self.condition.notify_all()
            if not self.quiet:
                traceback.print_exc()
        finally:
            self.ready.set()
            if installed:
                self._restore_stubs()
            with self.condition:
                self.stopped = True
                self.condition.notify_all()

    def start(self, timeout=5.0):
        if self.worker is not None:
            raise RuntimeError('Simulator runtime has already been started')
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('Start the simulator from the GUI thread')
        gc.collect()
        self.gc_was_enabled = gc.isenabled()
        gc.disable()
        self.worker = threading.Thread(target=self._run, name='clockpit-worker', daemon=True)
        self.worker.start()
        if not self.ready.wait(timeout):
            self.stop()
            raise RuntimeError('Simulator initialization timed out')
        if self.error:
            self.stop()
            raise RuntimeError(self.error)
        return self

    def stop(self, timeout=2.0):
        with self.condition:
            self.stopped = True
            self.condition.notify_all()
        if self.worker is not None and self.worker is not threading.current_thread():
            self.worker.join(timeout)
            stopped = not self.worker.is_alive()
            if stopped and self.gc_was_enabled is not None:
                if self.gc_was_enabled:
                    gc.enable()
                self.gc_was_enabled = None
            return stopped
        return True

    def collect_garbage(self):
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('Collect simulator garbage on the GUI thread')
        gc.collect()
