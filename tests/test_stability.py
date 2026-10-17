"""Long-run bounds, 32-bit native math, monotonic time and failure diagnosis."""
import ast
from array import array
import contextlib
import gc
import io
import math
from pathlib import Path
import tempfile
import sys
import tracemalloc
import types
import unittest
from unittest.mock import Mock, patch

from animations.mod_clock import Clock
from animations.mod_donut import Donut
from animations.mod_gameoflife import GameOfLife
from animations.mod_maze import Maze
from animations.mod_spiral import Spiral
from core import health, timing
from simulator.runtime import SimulatorRuntime
from test_viper_animations import Int32
from test_diagnostics import diagnostics_namespace


PERIOD = 1 << 30


def tick_diff(end, start):
    return (end - start + PERIOD // 2) % PERIOD - PERIOD // 2


class CheckedPointer:
    def __init__(self, buffer, bits):
        self.view = memoryview(buffer).cast('B')
        if bits == 16:
            self.view = self.view.cast('H')
        self.maximum = (1 << bits) - 1

    def __getitem__(self, index):
        if not 0 <= index < len(self.view):
            raise AssertionError('Native pointer read outside buffer: {}'.format(index))
        return self.view[index]

    def __setitem__(self, index, value):
        if not 0 <= index < len(self.view) or not 0 <= value <= self.maximum:
            raise AssertionError('Native pointer write outside buffer or channel range')
        self.view[index] = value


class MonotonicTests(unittest.TestCase):
    def setUp(self):
        self.now = PERIOD - 100
        self.clock_patches = [
            patch.object(timing, 'ticks_ms', lambda: self.now),
            patch.object(timing, 'ticks_add', lambda now, delta: (now + delta) % PERIOD),
            patch.object(timing, 'ticks_diff', tick_diff),
        ]
        for item in self.clock_patches:
            item.start()
            self.addCleanup(item.stop)

    def test_spiral_event_survives_wrap_and_ignores_wall_clock(self):
        spiral = Spiral(16, 16)
        spiral.next_event_time = timing.ticks_add(self.now, 1000)
        spiral.spawn_erase = Mock()
        self.now = (self.now + 999) % PERIOD
        spiral.get()
        spiral.spawn_erase.assert_not_called()
        self.now = (self.now + 1) % PERIOD
        spiral.get()
        spiral.spawn_erase.assert_called_once()
        self.assertGreater(tick_diff(spiral.next_event_time, self.now), 0)

    def test_maze_half_second_pause_survives_wrap(self):
        maze = Maze(16, 16)
        maze._first = False
        maze.path = [maze.entrance]
        maze.get()
        self.assertTrue(maze.at_end)
        self.assertEqual(maze.pause_until, 400)
        maze._create_solvable_maze = Mock()
        self.now = 399
        maze.get()
        maze._create_solvable_maze.assert_not_called()
        self.now = 400
        maze.get()
        maze._create_solvable_maze.assert_called_once()

    def test_life_reset_survives_wrap(self):
        life = GameOfLife(16, 16)
        self.now = (self.now + 20001) % PERIOD
        self.assertEqual(life.get()[1], 0.5)
        self.assertEqual(life.timestamp, self.now)

    def test_health_tracks_days_and_collects_periodically_across_wrap(self):
        fake_gc = types.SimpleNamespace(collect=Mock(), mem_free=Mock(return_value=200000))
        with patch.object(health, 'gc', fake_gc):
            monitor = health.RuntimeHealth()
            # More than two days, crossing the 2**30 millisecond period.
            for _ in range(40000):
                self.now = (self.now + 30000) % PERIOD
                monitor.poll()
            self.assertEqual(monitor.uptime_ms, 1200000000)
            self.assertEqual(monitor.free_after_gc, 200000)
            self.assertEqual(fake_gc.collect.call_count, 40000)
            self.assertEqual(monitor.minimum_free_after_gc, 200000)


class DonutStabilityTests(unittest.TestCase):
    def test_all_native_accesses_stay_inside_buffers_for_many_orientations(self):
        donut = Donut(16, 16)
        helpers = {'ptr8': lambda buf: CheckedPointer(buf, 8),
                   'ptr16': lambda buf: CheckedPointer(buf, 16)}
        with patch.dict(donut._render.__globals__, helpers):
            for x in range(24):
                for y in range(24):
                    donut.angle_x = x * 2 * math.pi / 24
                    donut.angle_y = y * 2 * math.pi / 24
                    donut.get()

    def test_short_projection_table_is_never_read_outside_its_bounds(self):
        donut = Donut(16, 16)
        donut.reciprocal = array('H')
        donut.get()
        self.assertFalse(any(donut.frame))

    def test_native_signed_32_bit_math_matches_desktop(self):
        source = Path(__file__).resolve().parents[1] / 'animations/mod_donut.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == 'Donut')
        kernel = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == '_render')
        kernel.decorator_list = []
        namespace = {'int': Int32, 'ptr8': lambda buf: CheckedPointer(buf, 8),
                     'ptr16': lambda buf: CheckedPointer(buf, 16)}
        exec(compile(ast.Module(body=[kernel], type_ignores=[]), str(source), 'exec'), namespace)
        donut = Donut(16, 16)
        for x in range(6):
            for y in range(6):
                donut.angle_x, donut.angle_y = x * math.pi / 3, y * math.pi / 3
                expected = bytes(donut.get()[2])
                namespace['_render'](donut)
                self.assertEqual(donut.frame, expected)

    def test_repeated_frames_do_not_retain_desktop_allocations(self):
        donut = Donut(16, 16)
        buffers = tuple(getattr(donut, name) for name in
                        ('frame', 'depth', 'rotation', 'ring', 'tube', 'reciprocal'))
        for _ in range(300):
            donut.get()
        tracemalloc.start()
        try:
            for _ in range(100):
                donut.get()
            gc.collect()
            before = tracemalloc.get_traced_memory()[0]
            for _ in range(100):
                donut.get()
            gc.collect()
            after = tracemalloc.get_traced_memory()[0]
            self.assertLessEqual(after - before, 1024)
        finally:
            tracemalloc.stop()
        for _ in range(5000):
            donut.get()
            self.assertTrue(0 <= donut.angle_x < 2 * math.pi)
            self.assertTrue(0 <= donut.angle_y < 2 * math.pi)
        for name, buffer in zip(('frame', 'depth', 'rotation', 'ring', 'tube', 'reciprocal'), buffers):
            self.assertIs(getattr(donut, name), buffer)


class FailureAndClockTests(unittest.TestCase):
    def test_european_dst_uses_utc_transition_hour(self):
        clock = Clock(16, 16)
        for date, expected in (((2026, 3, 29, 0), False), ((2026, 3, 29, 1), True),
                               ((2026, 10, 25, 0), True), ((2026, 10, 25, 1), False)):
            self.assertEqual(clock.is_dst_poland(*date), expected)

    def test_crash_report_overwrites_one_file_and_handles_write_failure(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            output = Path(directory) / 'crash.log'
            for message in ('first problem', 'second problem'):
                try:
                    raise RuntimeError(message)
                except RuntimeError as error:
                    self.assertTrue(health.save_failure(error, 'module=Donut stage=animation', str(output)))
            text = output.read_text()
            self.assertIn('second problem', text)
            self.assertNotIn('first problem', text)
            self.assertIn('module=Donut stage=animation', text)
            self.assertFalse(health.save_failure(RuntimeError('test'), 'test', str(output / 'invalid')))

    def test_two_simulators_cannot_replace_each_others_modules(self):
        first = SimulatorRuntime(quiet=True).start()
        try:
            with self.assertRaisesRegex(RuntimeError, 'Only one simulator'):
                SimulatorRuntime(quiet=True).start()
            self.assertIsNone(first.snapshot()['error'])
        finally:
            self.assertTrue(first.stop())
        second = SimulatorRuntime(quiet=True).start()
        self.assertTrue(second.stop())

    def test_failed_worker_start_releases_gc_and_runtime_ownership(self):
        was_enabled = gc.isenabled()
        runtime = SimulatorRuntime(quiet=True)
        with patch('simulator.runtime.threading.Thread.start', side_effect=RuntimeError('start failed')):
            with self.assertRaisesRegex(RuntimeError, 'start failed'):
                runtime.start()
        self.assertEqual(gc.isenabled(), was_enabled)
        self.assertFalse(runtime.owns_runtime)

    def test_startup_uses_nominal_cpu_and_continues_without_network(self):
        source = Path(__file__).resolve().parents[1] / 'core/init.py'
        for connected in (True, False):
            wlan = Mock()
            wlan.scan.return_value = []
            wlan.status.return_value = 3 if connected else -1
            wlan.ifconfig.return_value = ('127.0.0.1', '', '', '')
            machine = types.SimpleNamespace(freq=Mock(return_value=125000000))
            stubs = {
                'machine': machine,
                'network': types.SimpleNamespace(STA_IF=0, WLAN=Mock(return_value=wlan)),
                'ntptime': types.SimpleNamespace(settime=Mock()),
                'secrets': types.SimpleNamespace(wifi_name='test', wifi_pass='test'),
            }
            namespace = {}
            with patch.dict(sys.modules, stubs), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), namespace)
                self.assertEqual(namespace['run'](), connected)
            machine.freq.assert_any_call(125000000)
            self.assertEqual(wlan.active.call_args.args, (False,))

    def test_watchdog_is_fed_after_successful_output_only(self):
        for failed_output in (False, True):
            app = diagnostics_namespace()
            watchdog = Mock()
            machine = types.SimpleNamespace(WDT=Mock(return_value=watchdog))
            monitor = Mock()
            events = []

            class Finished(Exception):
                pass

            def write():
                events.append('write')
                if failed_output:
                    raise Finished()

            watchdog.feed.side_effect = lambda: events.append('feed')
            app.update(
                SIMULATOR=False, DEBUG_STATS=False, WATCHDOG_TIMEOUT_MS=8000,
                RuntimeHealth=Mock(return_value=monitor), machine=machine,
                print_system_info=Mock(), print_log=Mock(),
                handle_buttons=Mock(side_effect=[None, Finished()]),
                current_module=types.SimpleNamespace(get=lambda: (True, 0, bytearray(768))),
                display=types.SimpleNamespace(apply=lambda *args: True),
                frame=types.SimpleNamespace(write=write), time=types.SimpleNamespace(sleep=Mock()),
            )
            with self.assertRaises(Finished):
                app['run']()
            self.assertEqual(events, ['write'] if failed_output else ['write', 'feed'])
            machine.WDT.assert_called_once_with(timeout=8000)


if __name__ == '__main__':
    unittest.main()
