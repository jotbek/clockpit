"""Desktop regression tests. Run: python -m unittest discover -s tests -v."""
import ast
from array import array
import contextlib
import gc
import importlib
import io
import operator
from pathlib import Path
import random
import struct
import sys
import time
import types
import unittest
from unittest.mock import patch
import weakref

from core.display import MatrixDisplay
from animations.mod_mandelbrot import Mandelbrot
from animations.mod_gameoflife import GameOfLife

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    ('animations.mod_mandelbrot', 'Mandelbrot'), ('animations.mod_clock', 'Clock'),
    ('animations.mod_fireplasma', 'FirePlasma'), ('animations.mod_gameoflife', 'GameOfLife'),
    ('animations.mod_spiral', 'Spiral'), ('animations.mod_matrixrain', 'MatrixRain'),
    ('animations.mod_raybouncer', 'Bounce'), ('animations.mod_vortex', 'ColorVortex'),
    ('animations.mod_lava', 'Lava'), ('animations.mod_fireplace', 'Fireplace'),
    ('animations.mod_rainbow', 'Rainbow'), ('animations.mod_maze', 'Maze'),
    ('animations.mod_santatree_16x16', 'Santree'),
    ('animations.mod_donut', 'Donut'),
    ('animations.mod_daycycle', 'DayCycle'),
)


class Pixels:
    ORDER = (1, 0, 2, 3)
    bpp = 3

    def __init__(self, pin=None, n=256):
        self.n = n
        self.buf = bytearray(n * 3)
        self.last_write = None

    def write(self):
        self.last_write = bytes(self.buf)


class Pin:
    IN = PULL_UP = 0

    def __init__(self, *args):
        pass

    def value(self):
        return 1


class Float32(float):
    """Round every floating arithmetic result, like the default rp2 build."""
    def __new__(cls, value):
        return float.__new__(cls, struct.unpack('f', struct.pack('f', value))[0])


def _float_op(op, reverse=False):
    def method(self, other):
        value = op(float(other), float(self)) if reverse else op(float(self), float(other))
        return Float32(value)
    return method


for _name, _op in (('add', operator.add), ('sub', operator.sub),
                   ('mul', operator.mul), ('truediv', operator.truediv)):
    setattr(Float32, '__' + _name + '__', _float_op(_op))
    setattr(Float32, '__r' + _name + '__', _float_op(_op, True))


class FloatConstants(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, float):
            return ast.copy_location(ast.Call(ast.Name('Float32', ast.Load()), [node], []), node)
        return node


def load_app_without_loop():
    tree = ast.parse((ROOT / 'main.py').read_text(encoding='utf-8'))
    tree.body = [node for node in tree.body if not isinstance(node, ast.While)]
    machine = types.SimpleNamespace(Pin=Pin)
    fake_gc = types.SimpleNamespace(collect=gc.collect, mem_free=lambda: 1, mem_alloc=lambda: 1)
    stubs = {'machine': machine, 'neopixel': types.SimpleNamespace(NeoPixel=Pixels),
             'core.init': types.SimpleNamespace(run=lambda: None), 'gc': fake_gc}
    namespace = {'__name__': 'clockpit_test'}
    with patch.dict(sys.modules, stubs):
        exec(compile(tree, str(ROOT / 'main.py'), 'exec'), namespace)
    return namespace


class DisplayTests(unittest.TestCase):
    def test_mapping_scaling_full_and_delta_agree(self):
        for width, height in ((16, 16), (7, 5)):
            pixels = Pixels(n=width * height)
            display = MatrixDisplay(pixels, width, height)
            packed = bytearray(random.randrange(256) for _ in range(width * height * 3))
            legacy = [[tuple(packed[(x * height + y) * 3:(x * height + y + 1) * 3])
                       for y in range(height)] for x in range(width)]
            for brightness in (0, 1, 96, 128, 255):
                display.apply(True, packed, brightness)
                expected = bytearray(len(packed))
                for x in range(width):
                    for y in range(height):
                        index = y * width + (x if y % 2 else width - 1 - x)
                        for channel, value in enumerate(legacy[x][y]):
                            expected[index * 3 + pixels.ORDER[channel]] = value * brightness // 255
                self.assertEqual(pixels.buf, expected)
                display.clear()
                display.apply(True, legacy, brightness)
                self.assertEqual(pixels.buf, expected)
                display.clear()
                display.apply(False, [(x, y, legacy[x][y]) for x in range(width)
                                      for y in range(height)], brightness)
                self.assertEqual(pixels.buf, expected)

    def test_overlay_restores_delta_background_and_transparent_pixels(self):
        from animations.mod_clock import Clock
        pixels = Pixels()
        display = MatrixDisplay(pixels, 16, 16)
        display.apply(True, bytearray([37, 63, 89] * 256), 255)
        base = bytes(pixels.buf)
        clock = Clock(16, 16)
        for second in (0, 1, 59, 0):
            with patch('animations.mod_clock.time.localtime', return_value=(2026, 10, 13, 10, 34, second, 1, 286)):
                _, _, overlay = clock.get()
            self.assertLessEqual(sum(any(overlay[i:i + 3]) for i in range(0, 768, 3)), 120)
            display.show_overlay(overlay, 96)
            self.assertEqual(bytes(pixels.buf), base)
            self.assertNotEqual(pixels.last_write, base)
        display.apply(False, [(0, 0, (255, 0, 0))], 255)
        self.assertEqual(pixels.buf[display.map_pixel(1, 1) * 3:display.map_pixel(1, 1) * 3 + 3],
                         bytes((63, 37, 89)))

    def test_ui_overlays_restore_and_switch_releases_old_instance(self):
        app = load_app_without_loop()
        with patch.object(time, 'sleep', lambda _: None), contextlib.redirect_stdout(io.StringIO()):
            app['display'].apply(True, bytearray([17, 31, 67] * 256), 255)
            base = bytes(app['frame'].buf)
            for percent in (0, 9, 10, 99, 100):
                app['display_percentage'](percent, (255, 255, 0), 0)
                self.assertEqual(bytes(app['frame'].buf), base)
            app['display_symbol16x16']('sun', (255, 255, 0), 0)
            self.assertEqual(bytes(app['frame'].buf), base)
            for _ in range(2):
                for index in range(len(app['modules'])):
                    old = weakref.ref(app['current_module'])
                    app['select_module'](index)
                    self.assertIsNone(old())
                    self.assertEqual(app['selected_module'], index)

    def test_switch_releases_package_attribute_and_module_cache(self):
        app = load_app_without_loop()
        with contextlib.redirect_stdout(io.StringIO()):
            lava_index = next(i for i, spec in enumerate(app['modules'])
                              if spec[0] == 'animations.mod_lava')
            app['select_module'](lava_index)
            old_module = weakref.ref(sys.modules['animations.mod_lava'])
            package = sys.modules['animations']
            self.assertTrue(hasattr(package, 'mod_lava'))
            app['select_module'](0)
            self.assertNotIn('animations.mod_lava', sys.modules)
            self.assertFalse(hasattr(package, 'mod_lava'))
            gc.collect()
            self.assertIsNone(old_module())


class ModuleTests(unittest.TestCase):
    def test_modules_avoid_unsupported_micropython_buffer_repetition(self):
        # MicroPython array/bytearray omit CPython's multiplication operator.
        def unsupported(*args):
            raise TypeError('buffer repetition is unavailable on MicroPython')

        class PicoArray(array):
            __mul__ = __rmul__ = __imul__ = unsupported

        class PicoBytearray(bytearray):
            __mul__ = __rmul__ = __imul__ = unsupported

        with patch.dict(sys.modules, {'array': types.SimpleNamespace(array=PicoArray)}):
            for module_name, name in MODULES:
                with self.subTest(module=name):
                    namespace = {'bytearray': PicoBytearray}
                    exec(compile((ROOT / (module_name.replace('.', '/') + '.py')).read_text(encoding='utf-8'),
                                 module_name, 'exec'), namespace)
                    animation = namespace[name](16, 16)
                    for _ in range(3):
                        animation.get()

    def test_all_modules_outputs_and_resets(self):
        random.seed(123)
        for module_name, name in MODULES:
            with self.subTest(module=name):
                module = getattr(importlib.import_module(module_name), name)(16, 16)
                for step in range(100):
                    if name == 'Maze' and module.at_end:
                        module.pause_until = 0
                    if name == 'GameOfLife' and step == 50:
                        module.timestamp = 0
                    full, delay, changes = module.get()
                    self.assertGreaterEqual(delay, 0)
                    if full:
                        self.assertIsInstance(changes, bytearray)
                        self.assertEqual(len(changes), 768)
                    else:
                        for x, y, color in changes:
                            self.assertTrue(0 <= x < 16 and 0 <= y < 16)
                            self.assertEqual(len(color), 3)
                            self.assertTrue(all(0 <= c <= 255 for c in color))

    def test_life_matches_independent_reference(self):
        for width, height in ((16, 16), (7, 5)):
            life = GameOfLife(width, height)
            ref = [[random.randint(0, 1) for _ in range(width)] for _ in range(height)]
            for y in range(height):
                for x in range(width):
                    life.grid[(y + 1) * life.stride + x + 1] = ref[y][x]
            for _ in range(40):
                following = []
                for y in range(height):
                    row = []
                    for x in range(width):
                        neighbours = sum(ref[ny][nx] for ny in range(max(0, y - 1), min(height, y + 2))
                                         for nx in range(max(0, x - 1), min(width, x + 2))
                                         if (nx, ny) != (x, y))
                        row.append(int(neighbours == 3 or (ref[y][x] and neighbours == 2)))
                    following.append(row)
                life.update()
                ref = following
                actual = [list(life.grid[(y + 1) * life.stride + 1:(y + 1) * life.stride + width + 1])
                          for y in range(height)]
                self.assertEqual(actual, ref)

    def test_maze_paths_stay_connected_and_inside_border(self):
        from animations.mod_maze import Maze
        for seed in range(50):
            random.seed(seed)
            maze = Maze(16, 16)
            self.assertEqual(maze.path[0], maze.entrance)
            self.assertEqual(maze.path[-1], maze.exit)
            for x, y in maze.path:
                self.assertTrue(1 <= x <= 14 and 1 <= y <= 14)
                self.assertFalse(maze.grid[y][x])
            for a, b in zip(maze.path, maze.path[1:]):
                self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)

    def test_spiral_complete_path_and_bounded_actors(self):
        from animations.mod_spiral import Spiral
        spiral = Spiral(16, 16)
        self.assertEqual(len(set(spiral.path)), 256)
        self.assertEqual(set(spiral.path), set(range(256)))
        for _ in range(100):
            spiral.spawn_draw()
            spiral.spawn_erase()
        self.assertLessEqual(len(spiral.actors), 4)

    def test_bounce_active_pixels_remain_unique_and_bounded(self):
        from animations.mod_raybouncer import Bounce
        animation = Bounce(16, 16)
        for _ in range(1000):
            animation.get()
            for bouncer in animation.bouncers:
                active = bouncer.active[:bouncer.active_count]
                self.assertEqual(len(active), len(set(active)))
                self.assertLessEqual(bouncer.active_count, 256)
                self.assertEqual(set(active),
                                 {i // 3 for i in range(0, 768, 3) if any(bouncer.map[i:i + 3])})

    def test_plasma_fixed_point_state_stays_in_range(self):
        from animations.mod_fireplasma import FirePlasma
        animation = FirePlasma(16, 16)
        for _ in range(300):
            animation.get()
            self.assertTrue(all(0 <= heat <= 4095 for heat in animation.heat))

    def test_mandelbrot_tracks_detail_for_full_cycles_and_recovers(self):
        fractal = Mandelbrot()
        targets = set()
        for _ in range(1100):
            targets.add(fractal.target_idx)
            fractal.get()
            self.assertTrue(any(fractal.frame))
            self.assertGreater(len(set(fractal.iterations)), 1)
        self.assertEqual(targets, set(range(4)))
        for cx, cy in ((0, 0), (5, 5)):
            fractal.cx, fractal.cy, fractal.width = cx, cy, 0.0003
            fractal.get()
            self.assertTrue(any(fractal.frame))

    def test_mandelbrot_float32_full_zoom_cycle(self):
        tree = FloatConstants().visit(ast.parse((ROOT / 'animations/mod_mandelbrot.py').read_text()))
        namespace = {'Float32': Float32}
        exec(compile(ast.fix_missing_locations(tree), 'mandelbrot_float32', 'exec'), namespace)
        fractal = namespace['Mandelbrot']()
        for _ in range(270):
            fractal.get()
            self.assertTrue(any(fractal.frame))
            self.assertGreater(len(set(fractal.iterations)), 1)
        self.assertIsInstance(fractal.cx, Float32)
        self.assertEqual(fractal.target_idx, 1)


if __name__ == '__main__':
    unittest.main()
