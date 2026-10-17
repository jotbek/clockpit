"""Compare Viper's desktop fallback with the original column-grid algorithm."""
import random
import unittest
from unittest.mock import patch

from animations.mod_fireplasma import FirePlasma


COLOURS = ((0, 0, 0), (15, 0, 0), (30, 0, 0), (180, 0, 0),
           (220, 100, 0), (252, 210, 60), (252, 220, 100), (255, 255, 180))
THRESHOLDS = (1556, 1638, 1843, 2048, 2211, 2375, 2580)


class FirePlasmaTests(unittest.TestCase):
    def test_frames_match_original_algorithm(self):
        for width, height in ((16, 16), (7, 5), (2, 1)):
            for damping in (0.5, 0.97, 1.0):
                with self.subTest(size=(width, height), damping=damping):
                    plasma = FirePlasma(width, height)
                    plasma.damping_factor = damping
                    rng = random.Random(412)
                    columns, rows = width + 2, height + 4
                    reference = [[rng.randrange(4096) for _ in range(rows)]
                                 for _ in range(columns)]
                    for x in range(columns):
                        for y in range(rows):
                            plasma.heat[x * rows + y] = reference[x][y]
                    frame, heat, palette = plasma.frame, plasma.heat, plasma.palette
                    factor = int(damping * 4096 / 5)
                    for _ in range(80):
                        seeds = [rng.randint(0, columns - 4)
                                 for _ in range(plasma.fire_spawns)]
                        for column in reference:
                            column[-1] = column[-2] = 0
                        for seed in seeds:
                            for x in (seed + 1, seed + 2, seed + 3):
                                reference[x][-1] = reference[x][-2] = 4095
                        for y in range(rows - 2):
                            for x in range(1, columns - 1):
                                reference[x][y] = (
                                    (reference[x][y] + reference[x][y + 1]
                                     + reference[x][y + 2] + reference[x - 1][y + 1]
                                     + reference[x + 1][y + 1]) * factor) >> 12
                        expected = bytearray()
                        for x in range(width):
                            for y in range(height):
                                value = reference[x + 1][y]
                                expected.extend(COLOURS[sum(value >= t for t in THRESHOLDS)])
                        with patch('animations.mod_fireplasma.random.randint', side_effect=seeds):
                            full, delay, actual = plasma.get()
                        self.assertTrue(full)
                        self.assertEqual(delay, 0.0)
                        self.assertEqual(actual, expected)
                        self.assertEqual(list(plasma.heat),
                                         [v for column in reference for v in column])
                        self.assertIs(plasma.frame, frame)
                        self.assertIs(plasma.heat, heat)
                        self.assertIs(plasma.palette, palette)

    def test_palette_boundaries_and_pixel_order(self):
        values = (0, 4095) + tuple(v for t in THRESHOLDS for v in (t - 1, t))
        plasma = FirePlasma(4, 4)
        for index, value in enumerate(values):
            x, y = divmod(index, plasma.yres)
            plasma.heat[(x + 1) * plasma.height + y] = value
        plasma.draw()
        expected = bytes(channel for value in values
                         for channel in COLOURS[sum(value >= t for t in THRESHOLDS)])
        self.assertEqual(plasma.frame, expected)


if __name__ == '__main__':
    unittest.main()
