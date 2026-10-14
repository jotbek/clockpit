"""Interaction, timing, lifecycle, and brightness regression tests."""
import contextlib
import io
import sys
import threading
import time
import unittest
from unittest.mock import patch

from core.display import MatrixDisplay
from simulator.runtime import SimulatorRuntime, SPEED_OPTIONS, TICK_PERIOD


class Pixels:
    ORDER = (1, 0, 2, 3)
    bpp = 3

    def __init__(self):
        self.buf = bytearray(768)

    def write(self):
        pass


class BrightnessTests(unittest.TestCase):
    def test_sparse_pixels_survive_zero_and_full_brightness(self):
        pixels = Pixels()
        display = MatrixDisplay(pixels, 16, 16)
        display.apply(False, [(1, 1, (17, 93, 255)), (4, 7, (255, 32, 9))], 96)
        original = bytes(display.base)
        for brightness in (0, 1, 255, 128, 0, 255):
            display.set_brightness(brightness)
            self.assertEqual(bytes(display.base), original)
            self.assertEqual(bytes(pixels.buf), bytes(c * brightness // 255 for c in original))

    def test_temporary_overlay_never_enters_unscaled_base(self):
        pixels = Pixels()
        display = MatrixDisplay(pixels, 16, 16)
        display.apply(True, bytearray([63, 87, 103] * 256), 96)
        base = bytes(display.base)
        display.light(1, 1, 255, 255, 0, 128, remember=False)
        self.assertEqual(bytes(display.base), base)
        display.set_brightness(255)
        self.assertEqual(bytes(pixels.buf), base)


class RuntimeClockTests(unittest.TestCase):
    def test_diagnostic_clock_uses_real_time_at_high_simulation_speed(self):
        with patch('simulator.runtime.time.monotonic') as monotonic:
            monotonic.return_value = 1.0
            runtime = SimulatorRuntime()
            runtime.set_speed(50)
            clock = runtime._make_stubs()['time']
            stats_start, animation_start = clock.stats_ticks_us(), clock.ticks_us()
            monotonic.return_value = 1.01
            self.assertEqual(clock.stats_ticks_diff(clock.stats_ticks_us(), stats_start), 10000)
            self.assertEqual(clock.ticks_diff(clock.ticks_us(), animation_start), 500000)

    def test_extreme_speed_limits_and_invalid_values(self):
        runtime = SimulatorRuntime()
        for value in (-100, 0, 0.01):
            self.assertEqual(runtime.set_speed(value), 0.01)
        for _ in range(100):
            runtime.step_speed(-1)
        self.assertEqual(runtime.snapshot()['speed'], 0.01)
        for _ in range(100):
            runtime.step_speed(1)
        self.assertEqual(runtime.snapshot()['speed'], 50)
        self.assertEqual(runtime.set_speed(1000), 50)
        for value in (float('nan'), float('inf'), -float('inf'), 'invalid'):
            with self.assertRaises((ValueError, TypeError)):
                runtime.set_speed(value)
        self.assertEqual(runtime.snapshot()['speed'], 50)

    def test_speed_change_interrupts_existing_slow_sleep(self):
        runtime = SimulatorRuntime()
        runtime.set_speed(0.01)
        finished = threading.Event()
        thread = threading.Thread(target=lambda: (runtime.sleep(0.25), finished.set()))
        thread.start()
        try:
            self.assertFalse(finished.wait(0.03))
            runtime.set_speed(50)
            self.assertTrue(finished.wait(0.5))
        finally:
            runtime.stop()
            thread.join(1)

    def test_control_interrupts_slow_sleep_and_click_is_retained(self):
        runtime = SimulatorRuntime()
        runtime.set_speed(0.01)
        finished = threading.Event()
        thread = threading.Thread(target=lambda: (runtime.sleep(0.25), finished.set()))
        thread.start()
        try:
            self.assertFalse(finished.wait(0.03))
            serial = runtime.post('button', 'mode')
            self.assertTrue(finished.wait(0.5))
            self.assertEqual(tuple(runtime.commands), ((serial, 'button', 'mode'),))
        finally:
            runtime.stop()
            thread.join(1)

    def test_virtual_clock_is_continuous_and_ui_sleep_is_real_time(self):
        runtime = SimulatorRuntime()
        runtime.set_speed(0.01)
        before = runtime.simulation_time()
        start = time.monotonic()
        runtime.ui_sleep(0.03)
        self.assertLess(time.monotonic() - start, 0.3)
        self.assertLess(runtime.simulation_time() - before, 0.01)
        before = runtime.simulation_time()
        runtime.set_speed(50)
        after = runtime.simulation_time()
        self.assertGreaterEqual(after, before)
        self.assertLess(after - before, 0.05)
        clock = runtime._make_stubs()['time']
        self.assertEqual(clock.ticks_diff(5, TICK_PERIOD - 5), 10)

    def test_last_write_is_retained_even_without_another_animation_frame(self):
        runtime = SimulatorRuntime()
        pixels = Pixels()
        for value in (1, 2, 3, 0):
            pixels.buf[:] = bytes([value]) * 768
            runtime.publish_frame(pixels)
        self.assertEqual(runtime.take_frame(), bytes(768))
        self.assertIsNone(runtime.take_frame())


class RuntimeInteractionTests(unittest.TestCase):
    def setUp(self):
        self.real_time = sys.modules['time']
        self.runtime = SimulatorRuntime(quiet=True).start()

    def tearDown(self):
        self.assertTrue(self.runtime.stop())
        self.assertIs(sys.modules['time'], self.real_time)

    def send_batch(self, commands):
        serial = 0
        for command, value in commands:
            serial = self.runtime.post(command, value)
        self.assertTrue(self.runtime.wait_for(serial, 2), self.runtime.snapshot())
        self.assertIsNone(self.runtime.snapshot()['error'])

    def test_all_modules_modes_brightness_extremes_and_speed_extremes(self):
        configurations = 0
        for speed in (SPEED_OPTIONS[0], 1.0, SPEED_OPTIONS[-1]):
            self.runtime.set_speed(speed)
            for index in range(self.runtime.module_count):
                for mode in range(3):
                    for brightness in (0, 255):
                        with self.subTest(speed=speed, module=index, mode=mode, brightness=brightness):
                            # A trailing no-op interrupts feedback banners just like a new input.
                            self.send_batch((('module', index), ('mode', mode),
                                             ('brightness', brightness), ('module', index)))
                            state = self.runtime.snapshot()
                            self.assertEqual((state['module'], state['mode'], state['brightness']),
                                             (index, mode, brightness))
                            configurations += 1
        self.assertEqual(configurations, self.runtime.module_count * 18)
        self.assertGreater(self.runtime.snapshot()['frames'], configurations)

    def test_minimum_speed_commands_do_not_wait_for_clock_delay(self):
        self.runtime.set_speed(0.01)
        self.send_batch((('module', 1),))
        time.sleep(0.04)
        serial = self.runtime.post('module', 0)
        self.assertTrue(self.runtime.wait_for(serial, 0.5), self.runtime.snapshot())

    def test_rapid_clicks_are_ordered_without_loss(self):
        self.runtime.set_speed(0.01)
        commands = [('module', 5)]
        for _ in range(10):
            commands.extend((('button', 'mode'), ('button', 'plus'), ('button', 'minus')))
        commands.append(('module', 5))
        self.send_batch(commands)
        state = self.runtime.snapshot()
        self.assertEqual((state['module'], state['mode'], state['brightness']), (5, 1, 96))

    def test_invalid_commands_cannot_crash_worker(self):
        for command, value in (('module', -1), ('module', self.runtime.module_count), ('module', 'one'),
                               ('mode', 3), ('button', 'unknown'), ('unknown', 0)):
            with self.assertRaises(ValueError):
                self.runtime.post(command, value)
        self.send_batch((('module', 0),))
        self.assertTrue(self.runtime.worker.is_alive())

    def test_worker_error_is_reported_and_does_not_leave_waiters_blocked(self):
        def fail():
            raise RuntimeError('Injected worker failure')
        self.runtime.app.control_hook = fail
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'Injected worker failure'):
                self.runtime.wait_for(self.runtime.post('module', 1), 1)

    def test_shutdown_interrupts_minimum_speed_sleep(self):
        self.runtime.set_speed(0.01)
        self.send_batch((('module', 1),))
        time.sleep(0.03)
        start = time.monotonic()
        self.assertTrue(self.runtime.stop(0.5))
        self.assertLess(time.monotonic() - start, 0.5)

    def test_hardware_mode_edge_and_opposite_buttons(self):
        # Pause the worker so GPIO polling can be exercised deterministically.
        self.assertTrue(self.runtime.stop())
        app = self.runtime.app
        app.control_hook = None
        app.ui_sleep = lambda _: None
        pin_type = type(app.modeButton)
        pin_type.states[5] = True
        app.handle_buttons()
        self.assertEqual(app.mode, 1)
        for _ in range(10):
            app.handle_buttons()
        self.assertEqual(app.mode, 1)
        pin_type.states[5] = False
        app.handle_buttons()
        pin_type.states[5] = True
        app.handle_buttons()
        self.assertEqual(app.mode, 2)
        pin_type.states[5] = False
        pin_type.states[13] = pin_type.states[9] = True
        previous = app.selected_module
        for _ in range(10):
            app.handle_buttons()
        self.assertEqual(app.selected_module, previous)

    def test_hardware_repeat_deadline_survives_tick_wrap(self):
        self.assertTrue(self.runtime.stop())
        app = self.runtime.app
        app.control_hook = None
        pin_type = type(app.plusButton)
        pin_type.states.clear()
        tick = [TICK_PERIOD - 1000]
        app.ticks_us = lambda: tick[0]
        pin_type.states[13] = True
        app.handle_buttons()
        self.assertEqual(app.selected_module, 1)
        self.assertEqual(app.plus_repeat_at, 349000)
        tick[0] = 199000
        app.handle_buttons()
        self.assertEqual(app.selected_module, 1)
        tick[0] = 349000
        app.handle_buttons()
        self.assertEqual(app.selected_module, 2)


if __name__ == '__main__':
    unittest.main()
