"""Run separately on Pico via REPL, with main.py stopped. Does not light LEDs.

Copy this file alongside the project modules and run:
    import profile_pico
    profile_pico.run()
Times include generation + rendering, exclude intentional delay and LED transfer.
"""
import gc
import sys
import time


def run(frames=100):
    if frames < 1:
        raise ValueError('frames must be positive')
    from machine import Pin
    from neopixel import NeoPixel
    from core.display import MatrixDisplay
    from core.loading import create_module, unload_module

    display = MatrixDisplay(NeoPixel(Pin(22), 256), 16, 16)
    specs = (
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
    print('module, us/frame, free at start, free with state, minimum free')
    for module_name, class_name in specs:
        gc.collect()
        before = gc.mem_free()
        animation = create_module(module_name, class_name, 16, 16)
        gc.collect()
        with_state = gc.mem_free()
        minimum = with_state
        elapsed = 0
        for _ in range(frames):
            start = time.ticks_us()
            full, _, changes = animation.get()
            display.apply(full, changes, 96)
            elapsed += time.ticks_diff(time.ticks_us(), start)
            minimum = min(minimum, gc.mem_free())
            changes = None
        print(class_name, elapsed // frames, before, with_state, minimum)
        animation = None
        unload_module(module_name)
        gc.collect()
