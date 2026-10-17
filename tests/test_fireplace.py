"""Flame continuity, spatial/temporal smoothing, particles and bounded state."""
import ast
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from animations.mod_fireplace import Fireplace
from core.native import ptr8, ptr16
from test_viper_animations import Int32


class FireplaceTests(unittest.TestCase):
    def test_frames_reuse_bounded_buffers_and_vary_over_time(self):
        for width, height in ((16, 16), (7, 5), (2, 1), (1, 3)):
            fire = Fireplace(width, height, delay=0.035)
            fields = {id(fire.frame), id(fire.next_heat)}
            names = ('frame_rgb', 'palette', 'fuel', 'target_fuel', 'profile',
                     'cooling', 'wind', 'burners', 'spark_x', 'spark_y',
                     'spark_velocity', 'spark_heat')
            buffers = tuple(getattr(fire, name) for name in names)
            frames = set()
            with patch.dict(fire.get.__globals__, random=random.Random(902)):
                for step in range(1000):
                    full, delay, frame = fire.get()
                    self.assertTrue(full)
                    self.assertEqual(delay, 0.035)
                    self.assertIs(frame, buffers[0])
                    self.assertEqual(len(frame), width * height * 3)
                    self.assertEqual({id(fire.frame), id(fire.next_heat)}, fields)
                    self.assertTrue(0 <= fire.phase <= 255)
                    for i in range(4):
                        if fire.spark_heat[i]:
                            self.assertLess(fire.spark_x[i], width)
                            self.assertLess(fire.spark_y[i], height << 8)
                    if step % 25 == 0:
                        frames.add(bytes(frame))
            self.assertGreater(len(frames), 10)
            self.assertTrue(any(fire.frame_rgb))
            for name, original in zip(names, buffers):
                self.assertIs(getattr(fire, name), original)

    def test_spatial_smoothing_lights_neighbours_of_a_hot_cell(self):
        fire = Fireplace(7, 5)
        fire.frame[:] = bytes(35)
        fire.frame[3 * 5 + 2] = 255
        fire._draw()
        for x, y in ((2, 2), (4, 2), (3, 1), (3, 3)):
            self.assertGreater(fire.frame_rgb[(x * 5 + y) * 3], 0)
        self.assertGreater(fire.frame_rgb[(3 * 5 + 2) * 3], fire.frame_rgb[(2 * 5 + 2) * 3])
        self.assertEqual(fire.frame_rgb[0], 0)

    def test_temporal_smoothing_converges_without_an_abrupt_colour_jump(self):
        fire = Fireplace(7, 5)
        fire.frame[:] = bytes([200]) * 35
        target = fire.palette[200 * 3:201 * 3]
        fire._draw()
        self.assertTrue(0 < fire.frame_rgb[0] < target[0])
        for _ in range(10):
            fire._draw()
        for offset in range(0, len(fire.frame_rgb), 3):
            for channel in range(3):
                self.assertLessEqual(abs(fire.frame_rgb[offset + channel] - target[channel]), 1)

    def test_propagation_is_symmetric_without_wind_and_cools_upward(self):
        fire = Fireplace(7, 5)
        fire.frame[:] = bytes([200]) * 35
        fire.fuel[:] = bytes([200]) * 7
        fire.wind[:] = bytes([128]) * 64
        fire._propagate()
        for x in range(7):
            self.assertEqual(fire.next_heat[x * 5:(x + 1) * 5],
                             fire.next_heat[(6 - x) * 5:(7 - x) * 5])
        self.assertLess(fire.next_heat[3 * 5], fire.next_heat[3 * 5 + 3])

    def test_sparks_move_fractionally_and_fade_with_checked_edges(self):
        fire = Fireplace(7, 5)
        fire.frame[:] = bytes(35)
        fire.spark_x[0], fire.spark_y[0], fire.spark_heat[0] = 3, (2 << 8) + 128, 200
        fire._draw()
        first = fire.frame_rgb[(3 * 5 + 2) * 3]
        second = fire.frame_rgb[(3 * 5 + 3) * 3]
        self.assertGreater(first, 0)
        self.assertEqual(first, second)
        # Last row interpolation must not access a pixel below the display.
        fire.spark_y[0] = (4 << 8) + 255
        fire._draw()
        fire.spark_y[0] = 20
        fire.spark_velocity[0] = 80
        with patch.dict(fire.get.__globals__, random=random.Random(3)):
            fire._update_sparks()
        self.assertEqual(fire.spark_heat[0], 0)

    def test_native_kernels_match_signed_32_bit_execution(self):
        source = Path(__file__).resolve().parents[1] / 'animations/mod_fireplace.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        kernels = [node for node in cls.body
                   if isinstance(node, ast.FunctionDef) and node.name in ('_draw', '_propagate')]
        for node in kernels:
            node.decorator_list = []
        namespace = {'int': Int32, 'ptr8': ptr8, 'ptr16': ptr16}
        exec(compile(ast.Module(body=kernels, type_ignores=[]), str(source), 'exec'), namespace)
        fire = Fireplace(16, 16)
        for phase in (0, 63, 127, 255):
            fire.phase = phase
            fire.frame[:] = bytes(random.Random(phase + i).randrange(256) for i in range(256))
            fire._propagate()
            expected = bytes(fire.next_heat)
            namespace['_propagate'](fire)
            self.assertEqual(fire.next_heat, expected)
            fire.spark_x[0], fire.spark_y[0], fire.spark_heat[0] = 0, (15 << 8) + 255, 255
            fire.spark_x[1], fire.spark_y[1], fire.spark_heat[1] = 15, 128, 200
            fire.frame_rgb[:] = bytes(768)
            fire._draw()
            expected = bytes(fire.frame_rgb)
            fire.frame_rgb[:] = bytes(768)
            namespace['_draw'](fire)
            self.assertEqual(fire.frame_rgb, expected)


if __name__ == '__main__':
    unittest.main()
