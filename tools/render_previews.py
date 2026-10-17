"""Render README GIFs without hardware or Tk. Requires Pillow.

python tools/render_previews.py             # all registered modules
python tools/render_previews.py Fireplace   # selected class names
"""
import argparse
import ast
from contextlib import ExitStack
import importlib
from pathlib import Path
import random
import sys
import time
import types
from unittest.mock import patch

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.display import MatrixDisplay
from core import timing


class PreviewClock:
    # 2026-07-01 00:00 UTC: Clock starts at 02:00 Polish local time.
    EPOCH = 1782864000

    def __init__(self):
        self.elapsed = 0.0

    def localtime(self, seconds=None):
        return time.gmtime(self.EPOCH + self.elapsed if seconds is None else seconds)

    def ticks_ms(self):
        return round(self.elapsed * 1000) % (1 << 30)


class Pixels:
    ORDER = (1, 0, 2, 3)
    bpp = 3

    def __init__(self, width, height):
        self.buf = bytearray(width * height * 3)


def registered_modules():
    # Read the actual selection order without starting the hardware application.
    tree = ast.parse((ROOT / 'main.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == 'modules' for target in node.targets):
            return [tuple(ast.literal_eval(value) for value in spec.elts[:2])
                    for spec in node.value.elts]
    raise RuntimeError('No module list found in main.py')


def capture(module_name, class_name):
    module = importlib.import_module(module_name)
    clock = PreviewClock()
    fake_time = types.SimpleNamespace(localtime=clock.localtime)
    width = height = 16
    pixels = Pixels(width, height)
    display = MatrixDisplay(pixels, width, height)
    duration = 12 if class_name in ('DayCycle', 'Mandelbrot') else 8
    speed = 86400 / duration if class_name == 'DayCycle' else (8 if class_name == 'Clock' else 1)
    random.seed(20261015)
    frames = []
    with ExitStack() as context:
        context.enter_context(patch.object(timing, 'ticks_ms', clock.ticks_ms))
        if hasattr(module, 'time'):
            context.enter_context(patch.object(module, 'time', fake_time))
        animation = getattr(module, class_name)(width, height)
        next_update = 0.0
        for index in range(duration * 12):
            target = index / 12 * speed
            while next_update <= target + 1e-8:
                clock.elapsed = next_update
                full, delay, changes = animation.get()
                # Use the same renderer as Pico/simulator, including sparse frames.
                display.apply(full, changes, 255)
                # Zero-delay modules have hardware-dependent rates; use 25 Hz.
                next_update += max(float(delay), 0.04)
                # DayCycle samples one sky per GIF frame rather than every RTC second.
                if class_name == 'DayCycle':
                    next_update = target + speed / 12
            image = Image.new('RGB', (width, height))
            rgb = []
            for y in range(height):
                for x in range(width):
                    offset = display.map_pixel(x, y) * 3
                    rgb.append(tuple(pixels.buf[offset + channel] for channel in pixels.ORDER[:3]))
            image.putdata(rgb)
            frames.append(image)
    return frames


def save_gif(frames, path):
    # One palette across the clip avoids flickering from per-frame quantization.
    samples = Image.new('RGB', (16 * len(frames), 16))
    for index, frame in enumerate(frames):
        samples.paste(frame, (index * 16, 0))
    palette = samples.quantize(colors=127, dither=Image.Dither.NONE)
    colors = palette.getpalette()
    colors[127 * 3:128 * 3] = [0, 0, 0]
    palette.putpalette(colors)
    scaled = []
    for frame in frames:
        small = frame.quantize(palette=palette, dither=Image.Dither.NONE)
        image = small.resize((160, 160), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(image)
        for edge in range(0, 160, 10):
            draw.line((edge, 0, edge, 159), fill=127)
            draw.line((0, edge, 159, edge), fill=127)
        scaled.append(image)
    # Alternate 80/90 ms to approximate 12 FPS at GIF's 10 ms precision.
    durations = [90 if index % 3 == 2 else 80 for index in range(len(scaled))]
    scaled[0].save(path, save_all=True, append_images=scaled[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names', nargs='*', help='Class names; omit to render all')
    args = parser.parse_args()
    specs = registered_modules()
    unknown = set(args.names) - {name for _, name in specs}
    if unknown:
        parser.error('Unknown module(s): ' + ', '.join(sorted(unknown)))
    output = ROOT / 'docs' / 'animations'
    output.mkdir(parents=True, exist_ok=True)
    for module_name, class_name in specs:
        if args.names and class_name not in args.names:
            continue
        frames = capture(module_name, class_name)
        path = output / (class_name + '.gif')
        save_gif(frames, path)
        print('{}: {} frames, {:.0f} KiB'.format(class_name, len(frames), path.stat().st_size / 1024), flush=True)


if __name__ == '__main__':
    main()
