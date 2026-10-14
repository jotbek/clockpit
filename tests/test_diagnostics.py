"""Terminal diagnostics, including controlled frame timing and tick rollover."""
import ast
import contextlib
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


PERIOD = 1 << 30


def diagnostics_namespace():
    source = Path(__file__).resolve().parents[1] / 'main.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    names = {'print_system_info', 'print_log', 'reset_stats', 'run'}
    tree.body = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {
        'SIMULATOR': False, 'DEBUG_STATS': True, 'STATS_INTERVAL_US': 200000,
        'counter': 0, 'start_time': 0, 'render_time_us': 0, 'peak_render_time_us': 0,
        'mode': 0, 'selected_module': 0, 'intense': 96, 'delay_ms': 0.07,
        'modules': [('animations.test', 'TestAnimation', 16, 16)],
        'gc': types.SimpleNamespace(mem_alloc=Mock(return_value=65536),
                                    mem_free=Mock(return_value=196608), collect=Mock()),
        'machine': types.SimpleNamespace(freq=Mock(return_value=250000000)),
        'sys': sys,
    }
    exec(compile(tree, str(source), 'exec'), namespace)
    return namespace


class DiagnosticsTests(unittest.TestCase):
    def test_current_heap_and_frequency_without_forcing_gc(self):
        app = diagnostics_namespace()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            app['print_log']()
        log = output.getvalue()
        self.assertIn('RAM (Python heap): 64.0/256.0 KiB used (25.0%), 192.0 KiB free', log)
        self.assertIn('CPU: 250 MHz', log)
        self.assertNotIn('FPS', log)
        app['gc'].collect.assert_not_called()

    def test_simulator_labels_and_no_cpu_frequency(self):
        app = diagnostics_namespace()
        app.update(SIMULATOR=True, machine=types.SimpleNamespace())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            app['print_system_info']()
            app['print_log']()
        self.assertIn('RAM (heap, simulated)', output.getvalue())
        self.assertIn('CPU: n/a', output.getvalue())
        self.assertIn('Pico firmware: unavailable in simulator', output.getvalue())

    def test_firmware_uses_board_build_information(self):
        app = diagnostics_namespace()
        info = types.SimpleNamespace(version='vTEST on BUILD_DATE', machine='Pico W with RP2040')
        output = io.StringIO()
        with patch.dict(sys.modules, {'os': types.SimpleNamespace(uname=lambda: info)}):
            with contextlib.redirect_stdout(output):
                app['print_system_info']()
        self.assertIn('firmware: MicroPython vTEST on BUILD_DATE', output.getvalue())
        self.assertIn('board: Pico W with RP2040', output.getvalue())

    def test_timing_excludes_frame_delay_and_handles_tick_rollover(self):
        app = diagnostics_namespace()
        now = [PERIOD - 50000]
        calls = [0]

        class Finished(Exception):
            pass

        def controls():
            calls[0] += 1
            if calls[0] > 2:
                raise Finished()

        def generate():
            now[0] += 15000
            return True, 0.07, bytearray(768)

        def apply(*args):
            now[0] += 10000
            return True

        def write():
            now[0] += 5000

        def sleep(seconds):
            now[0] += int(seconds * 1000000)

        app.update(
            SIMULATOR=True, handle_buttons=controls,
            current_module=types.SimpleNamespace(get=generate),
            display=types.SimpleNamespace(apply=apply),
            frame=types.SimpleNamespace(write=write), time=types.SimpleNamespace(sleep=sleep),
            stats_ticks_us=lambda: now[0] % PERIOD,
            stats_ticks_diff=lambda end, start: (end - start + PERIOD // 2) % PERIOD - PERIOD // 2,
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(Finished):
            app['run']()
        self.assertIn('FPS (updates): 10.0', output.getvalue())
        self.assertIn('render avg/max: 30.00/30.00 ms', output.getvalue())
        self.assertIn('render share: 30.0%', output.getvalue())
        self.assertEqual(app['counter'], 0)
        app['gc'].collect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
