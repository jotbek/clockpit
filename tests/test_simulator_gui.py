"""Exercise actual Tk widgets and the background worker without a visible window."""
import time
import unittest

from simulator.runtime import SimulatorRuntime


class SimulatorGuiTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from simulator.gui import SimulatorWindow
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest('Tk display is unavailable: {}'.format(error))
        self.root.withdraw()
        self.runtime = SimulatorRuntime(quiet=True).start()
        self.window = SimulatorWindow(self.root, self.runtime)

    def tearDown(self):
        if hasattr(self, 'window'):
            self.window.close()
            self.assertFalse(self.runtime.worker.is_alive())

    def pump_until(self, predicate, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.root.update()
            if predicate():
                return
            time.sleep(0.002)
        self.fail('GUI condition timed out: {}'.format(self.runtime.snapshot()))

    def drain_controls(self):
        serial = self.runtime.post('module', self.runtime.snapshot()['module'])
        self.pump_until(lambda: self.runtime.snapshot()['acknowledged'] >= serial
                        and self.window.pending_selection is None)

    def test_widgets_at_all_modules_modes_and_extreme_speeds(self):
        cases = 0
        for speed in (0.01, 50):
            self.runtime.set_speed(speed)
            self.window.refresh_speed()
            self.assertEqual(str(self.window.speed_down['state']), 'disabled' if speed == 0.01 else 'normal')
            self.assertEqual(str(self.window.speed_up['state']), 'disabled' if speed == 50 else 'normal')
            for index in range(13):
                for mode in range(3):
                    self.window.module_combo.current(index)
                    self.window.module_combo.event_generate('<<ComboboxSelected>>')
                    self.runtime.post('mode', mode)
                    self.runtime.post('brightness', 0 if cases % 2 else 255)
                    self.runtime.post('module', index)
                    self.pump_until(lambda: self.window.pending_selection is None
                                    and self.runtime.snapshot()['acknowledged'] == self.runtime.snapshot()['requested'])
                    self.assertEqual(self.window.module_combo.current(), index)
                    self.assertEqual(self.runtime.snapshot()['mode'], mode)
                    self.assertIsNone(self.runtime.snapshot()['error'])
                    cases += 1
        self.assertEqual(cases, 78)
        self.assertGreater(self.window.preview_frames, 0)

    def test_short_mouse_click_keyboard_activation_and_hold_release(self):
        self.runtime.set_speed(0.01)
        self.runtime.post('module', 1)
        self.drain_controls()
        button = self.window.buttons['plus']
        button.event_generate('<ButtonPress-1>', x=5, y=5)
        button.event_generate('<ButtonRelease-1>', x=5, y=5)
        serial = self.runtime.post('module', 2)
        self.pump_until(lambda: self.runtime.snapshot()['acknowledged'] >= serial)
        self.assertEqual(self.runtime.snapshot()['module'], 2)
        self.assertFalse(self.window.repeat_jobs)
        self.window.buttons['mode'].invoke()
        self.runtime.post('brightness', 96)
        self.drain_controls()
        self.assertEqual(self.runtime.snapshot()['mode'], 1)
        self.window.press('plus')
        self.pump_until(lambda: self.runtime.snapshot()['brightness'] >= 104, timeout=1)
        self.window.release('plus')
        self.drain_controls()
        brightness = self.runtime.snapshot()['brightness']
        self.assertFalse(self.window.repeat_jobs)
        end = time.monotonic() + 0.2
        while time.monotonic() < end:
            self.root.update()
            time.sleep(0.002)
        self.assertEqual(self.runtime.snapshot()['brightness'], brightness)

    def test_gui_heartbeat_and_clean_exit_at_maximum_speed(self):
        self.runtime.set_speed(50)
        timestamps = []

        def heartbeat():
            timestamps.append(time.monotonic())
            if len(timestamps) < 20:
                self.root.after(10, heartbeat)
        self.root.after(10, heartbeat)
        self.pump_until(lambda: len(timestamps) >= 20)
        self.assertLess(max(b - a for a, b in zip(timestamps, timestamps[1:])), 0.5)
        self.assertGreater(self.window.preview_frames, 1)
        self.window.close()
        self.assertFalse(self.runtime.worker.is_alive())

    def test_worker_failure_is_visible_in_gui(self):
        def fail():
            raise RuntimeError('Injected GUI failure')
        self.runtime.app.control_hook = fail
        self.runtime.post('module', 1)
        self.pump_until(lambda: 'Injected GUI failure' in self.window.status.get())
        self.assertEqual(str(self.window.module_combo['state']), 'disabled')


if __name__ == '__main__':
    unittest.main()
