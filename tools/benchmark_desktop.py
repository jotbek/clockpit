r"""Compare desktop CPU time and Python heap allocations, not Pico FPS/RAM.

python tools/benchmark_desktop.py
python tools/benchmark_desktop.py --baseline C:\path\to\original\sources
"""
import argparse
import gc
import importlib
import json
from pathlib import Path
import random
import sys
import time
import tracemalloc
import types


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    source = args.baseline or Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(source))
    sys.modules.setdefault('machine', types.SimpleNamespace(RTC=object))

    class Pixels:
        ORDER = (1, 0, 2, 3)
        bpp = 3

        def __init__(self):
            self.buf = bytearray(768)

        def __setitem__(self, index, color):
            i = index * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = color[1], color[0], color[2]

    pixels = Pixels()
    if args.baseline:
        def light(x, y, color):
            i = y * 16 + (x if y % 2 else 15 - x)
            pixels[i] = (int(color[0] * (96 / 255)), int(color[1] * (96 / 255)),
                         int(color[2] * (96 / 255)))

        def render(full, changes):
            if full:
                for y in range(16):
                    for x in range(16):
                        light(x, y, changes[x][y])
            else:
                for x, y, color in changes:
                    light(x, y, color)
    else:
        from core.display import MatrixDisplay
        display = MatrixDisplay(pixels, 16, 16)

        def render(full, changes):
            display.apply(full, changes, 96)

    specs = (
        ('animations.mod_mandelbrot', 'Mandelbrot'), ('animations.mod_clock', 'Clock'),
        ('animations.mod_fireplasma', 'FirePlasma'), ('animations.mod_gameoflife', 'GameOfLife'),
        ('animations.mod_spiral', 'Spiral'), ('animations.mod_matrixrain', 'MatrixRain'),
        ('animations.mod_raybouncer', 'Bounce'), ('animations.mod_vortex', 'ColorVortex'),
        ('animations.mod_lava', 'Lava'), ('animations.mod_fireplace', 'Fireplace'),
        ('animations.mod_rainbow', 'Rainbow'), ('animations.mod_maze', 'Maze'),
        ('animations.mod_santatree_16x16', 'Santree'),
    )
    results = {}
    for module_name, name in specs:
        # Module imports are excluded from the per-animation heap measurement.
        if args.baseline:
            module_name = module_name.rsplit('.', 1)[-1]
        module = importlib.import_module(module_name)
        random.seed(123)
        animation = getattr(module, name)(16, 16)
        start = time.perf_counter()
        for _ in range(500):
            full, _, changes = animation.get()
            render(full, changes)
            changes = None
        elapsed = (time.perf_counter() - start) * 2
        animation = None
        gc.collect()
        random.seed(123)
        tracemalloc.start()
        animation = getattr(module, name)(16, 16)
        for _ in range(100):
            full, _, changes = animation.get()
            render(full, changes)
            changes = None
        retained, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results[name] = {'ms_per_frame': round(elapsed, 3),
                         'retained_bytes': retained, 'peak_bytes': peak}
        animation = None
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    run()
