"""Rendering parity and fixed-point arithmetic checks for native animations."""
import ast
import math
import operator
from pathlib import Path
import unittest

from animations.mod_mandelbrot import Mandelbrot
from animations.mod_rainbow import Rainbow
from animations.mod_vortex import ColorVortex
from core.colors import rainbow_into
from core.native import ptr8, ptr16, ptr32


def escape_q26(cr, ci, maximum):
    """Independent arbitrary-precision reference; no limb multiplication."""
    zr = zi = count = 0
    while count < maximum:
        rr, ii = (zr * zr) >> 26, (zi * zi) >> 26
        if rr + ii > 4 * (1 << 26):
            return count
        zr, zi = rr - ii + cr, 2 * ((zr * zi) >> 26) + ci
        count += 1
    return count if ((zr * zr) >> 26) + ((zi * zi) >> 26) > 4 * (1 << 26) else 0


class Int32(int):
    """Model Viper signed word arithmetic, including intermediate overflow."""
    def __new__(cls, value=0):
        return super().__new__(cls, (int(value) + (1 << 31)) % (1 << 32) - (1 << 31))


def _word_operation(operation, reverse=False):
    def method(self, other):
        left, right = (int(other), int(self)) if reverse else (int(self), int(other))
        return Int32(operation(left, right))
    return method


for _name, _operation in (('add', operator.add), ('sub', operator.sub),
                           ('mul', operator.mul), ('rshift', operator.rshift),
                           ('and', operator.and_), ('xor', operator.xor),
                           ('lshift', operator.lshift), ('mod', operator.mod),
                           ('floordiv', operator.floordiv)):
    setattr(Int32, '__' + _name + '__', _word_operation(_operation))
    setattr(Int32, '__r' + _name + '__', _word_operation(_operation, True))


class NativeAnimationTests(unittest.TestCase):
    def test_rainbow_matches_original_for_entire_hue_cycle(self):
        for width, height in ((16, 16), (7, 5), (2, 1)):
            animation = Rainbow(width, height)
            frame, palette = animation.frame, animation.palette
            for phase in range(360):
                expected = bytearray(width * height * 3)
                end = bytearray(3)
                for x in range(width):
                    offset = x * height * 3
                    rainbow_into(expected, offset, x + phase)
                    rainbow_into(end, 0, x + phase + 100)
                    start = expected[offset:offset + 3]
                    for y in range(1, height):
                        for channel in range(3):
                            expected[offset + y * 3 + channel] = (
                                start[channel] * (height - y) + end[channel] * y) // height
                full, delay, actual = animation.get()
                self.assertTrue(full)
                self.assertEqual(delay, 0.0)
                self.assertEqual(actual, expected)
                self.assertIs(actual, frame)
                self.assertIs(animation.palette, palette)
            self.assertEqual(animation.counter, 0)

    def test_vortex_matches_original_phase_and_geometry(self):
        for width, height in ((16, 16), (7, 5)):
            for speed in (0, 0.2, -0.35):
                animation = ColorVortex(width, height, speed=speed, delay=0.17)
                frame, angles, palette = animation.frame, animation.angles, animation.palette
                # Include both sides of the phase wrap.
                animation.angle = 46079.75
                for _ in range(100):
                    expected = bytearray(width * height * 3)
                    for x in range(width):
                        for y in range(height):
                            angle = math.atan2(y - height // 2, x - width // 2)
                            base = int((angle * 180 / math.pi) % 360 * 128)
                            hue = ((base + int(animation.angle)) % 46080) // 128
                            rainbow_into(expected, (x * height + y) * 3, hue)
                    phase = (animation.angle + speed * 180 / math.pi * 128) % 46080
                    full, delay, actual = animation.get()
                    self.assertTrue(full)
                    self.assertEqual(delay, 0.17)
                    self.assertEqual(actual, expected)
                    self.assertEqual(animation.angle, phase)
                    self.assertIs(actual, frame)
                    self.assertIs(animation.angles, angles)
                    self.assertIs(animation.palette, palette)

    def test_mandelbrot_matches_big_integer_reference(self):
        for width, height in ((16, 16), (7, 5)):
            fractal = Mandelbrot(width, height)
            buffers = (fractal.frame, fractal.iterations, fractal.real,
                       fractal.imag, fractal.stats, fractal.palette)
            for cx, cy in fractal.targets + ((0, 0), (5, 5)):
                for span in (2.8, 0.5, 0.05, 0.005, 0.00025):
                    with self.subTest(size=(width, height), centre=(cx, cy), span=span):
                        fractal.cx, fractal.cy, fractal.width = cx, cy, span
                        fractal.color_shift = 357
                        actual_stats = fractal._render()
                        maximum = 24 + 8 * (span < 1) + 8 * (span < 0.1) + 8 * (span < 0.01)
                        expected = [escape_q26(cr, ci, maximum)
                                    for cr in fractal.real for ci in fractal.imag]
                        self.assertEqual(list(fractal.iterations), expected)
                        lit = [value for value in expected if value]
                        self.assertEqual(actual_stats,
                                         (len(lit), min(lit) if lit else maximum, max(lit) if lit else 0))
                        expected_rgb = bytearray(width * height * 3)
                        for index, value in enumerate(expected):
                            if value:
                                rainbow_into(expected_rgb, index * 3, value * 22 + 357)
                        self.assertEqual(fractal.frame, expected_rgb)
            for name, buffer in zip(('frame', 'iterations', 'real', 'imag', 'stats', 'palette'), buffers):
                self.assertIs(getattr(fractal, name), buffer)

    def test_mandelbrot_agrees_with_float_reference_at_all_zoom_scales(self):
        fractal = Mandelbrot()
        for cx, cy in fractal.targets:
            for span in (2.8, 0.5, 0.05, 0.005, 0.00025):
                fractal.cx, fractal.cy, fractal.width = cx, cy, span
                fractal._render()
                maximum = 24 + 8 * (span < 1) + 8 * (span < 0.1) + 8 * (span < 0.01)
                for x in range(16):
                    for y in range(16):
                        cr = cx - span / 2 + (x + 0.5) * span / 16
                        ci = cy - span / 2 + (y + 0.5) * span / 16
                        zr = zi = 0.0
                        count = 0
                        while zr * zr + zi * zi <= 4 and count < maximum:
                            zr, zi = zr * zr - zi * zi + cr, 2 * zr * zi + ci
                            count += 1
                        expected = count if zr * zr + zi * zi > 4 else 0
                        self.assertEqual(fractal.iterations[x * 16 + y], expected,
                                         (cx, cy, span, x, y))

    def test_mandelbrot_detects_escape_on_last_iteration(self):
        fractal = Mandelbrot(1, 1)
        for cr, ci, maximum, expected in ((3, 0, 1, 1), (2, 0, 1, 0),
                                           (2, 0, 2, 2), (-2, 0, 48, 0), (0, 0, 48, 0)):
            fractal.real[0], fractal.imag[0] = cr << 26, ci << 26
            fractal._render_native(maximum)
            self.assertEqual(fractal.iterations[0], expected)

    def test_mandelbrot_kernel_with_signed_32_bit_intermediates(self):
        source = Path(__file__).resolve().parents[1] / 'animations/mod_mandelbrot.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        kernel = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == '_render_native')
        kernel.decorator_list = []
        namespace = {'int': Int32, 'ptr8': ptr8, 'ptr16': ptr16, 'ptr32': ptr32}
        exec(compile(ast.Module(body=[kernel], type_ignores=[]), str(source), 'exec'), namespace)
        fractal = Mandelbrot()
        for cx, cy, span in ((-0.7436439, 0.1318259, 2.8),
                             (-1.7687788, -0.0017390, 0.00025),
                             (0.2745290, 0.4822550, 0.00025), (5, 5, 2.8)):
            fractal.cx, fractal.cy, fractal.width = cx, cy, span
            fractal._render()
            expected, stats = bytes(fractal.frame), list(fractal.stats)
            maximum = 24 + 8 * (span < 1) + 8 * (span < 0.1) + 8 * (span < 0.01)
            namespace['_render_native'](fractal, maximum)
            self.assertEqual(fractal.frame, expected)
            self.assertEqual(list(fractal.stats), stats)


if __name__ == '__main__':
    unittest.main()
