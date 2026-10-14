"""Geometry, depth occlusion, grayscale output, and bounded torus state."""
from array import array
import unittest

from animations.mod_donut import Donut


class DonutTests(unittest.TestCase):
    def test_front_view_has_a_hole_background_and_shading(self):
        donut = Donut(16, 16, speed=0)
        donut.angle_x = donut.angle_y = 0
        frame = donut.get()[2]
        for x in (7, 8):
            for y in (7, 8):
                self.assertEqual(frame[(x * 16 + y) * 3], 0)
        for edge in (0, 15):
            for position in range(16):
                self.assertEqual(frame[(edge * 16 + position) * 3], 0)
                self.assertEqual(frame[(position * 16 + edge) * 3], 0)
        shades = set(frame[::3])
        self.assertGreater(len(shades), 10)
        self.assertGreater(max(shades), 200)
        self.assertGreater(sum(bool(frame[i]) for i in range(0, len(frame), 3)), 60)

    def test_depth_occlusion_is_independent_of_surface_sample_order(self):
        normal = Donut(16, 16, speed=0, delay=0.12)
        reversed_samples = Donut(16, 16, speed=0)
        tube = reversed_samples.tube
        reversed_samples.tube = array(tube.typecode, (
            value for i in reversed(range(0, len(tube), 4)) for value in tube[i:i + 4]))
        for angle_x, angle_y in ((0, 0), (0.6, 0.3), (1.2, 0.7)):
            normal.angle_x = reversed_samples.angle_x = angle_x
            normal.angle_y = reversed_samples.angle_y = angle_y
            full, delay, frame = normal.get()
            self.assertTrue(full)
            self.assertEqual(delay, 0.12)
            self.assertEqual(frame, reversed_samples.get()[2])

    def test_rotation_reuses_buffers_and_stays_grayscale(self):
        for width, height in ((16, 16), (7, 5)):
            with self.subTest(size=(width, height)):
                donut = Donut(width, height)
                frame, depth = donut.frame, donut.depth
                poses = set()
                for _ in range(240):
                    full, delay, pixels = donut.get()
                    self.assertTrue(full)
                    self.assertEqual(delay, 0.0)
                    self.assertIs(pixels, frame)
                    self.assertIs(donut.depth, depth)
                    self.assertEqual(len(pixels), width * height * 3)
                    self.assertEqual(len(depth), width * height)
                    self.assertTrue(any(pixels))
                    for i in range(0, len(pixels), 3):
                        self.assertEqual(pixels[i], pixels[i + 1])
                        self.assertEqual(pixels[i], pixels[i + 2])
                    poses.add(bytes(pixels))
                self.assertGreater(len(poses), 100)


if __name__ == '__main__':
    unittest.main()
