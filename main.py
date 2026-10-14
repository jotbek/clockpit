#
# To work you should provide credentials to selected WiFi network you want to connect
# Put them to the secrets.py file as strings:
# wifi_name = 'ssid_of_network'
# wifi_pass = 'password'
#
from machine import Pin
import machine
from neopixel import NeoPixel
from core import init
import time
import gc
import sys
from core.display import MatrixDisplay
from core.loading import create_module, unload_module

from core import helpers

# LED matrix configuration
intense = 96  # 0 - 255
intense_step = 4
xres = 16
yres = 16
ledControlPin = 22
frame = NeoPixel(Pin(ledControlPin), xres * yres)
frame.write()
display = MatrixDisplay(frame, xres, yres)
pending_module = None
current_module = None
clock_module = None
control_hook = None
ui_sleep = getattr(time, 'ui_sleep', time.sleep)
button_mask = 0
plus_repeat_at = 0
minus_repeat_at = 0
ticks_us = getattr(time, 'ticks_us', lambda: int(time.time() * 1000000))
ticks_diff = getattr(time, 'ticks_diff', lambda end, start: end - start)
ticks_add = getattr(time, 'ticks_add', lambda current, delta: current + delta)
stats_ticks_us = getattr(time, 'stats_ticks_us', ticks_us)
stats_ticks_diff = getattr(time, 'stats_ticks_diff', ticks_diff)
SIMULATOR = sys.implementation.name != 'micropython'

# MODULES:
modules = [
    ('animations.mod_clock', 'Clock', xres, yres),
    ('animations.mod_fireplasma', 'FirePlasma', xres, yres),
    ('animations.mod_gameoflife', 'GameOfLife', xres, yres),
    ('animations.mod_donut', 'Donut', xres, yres),
    ('animations.mod_spiral', 'Spiral', xres, yres),
    ('animations.mod_matrixrain', 'MatrixRain', xres, yres),
    ('animations.mod_raybouncer', 'Bounce', xres, yres),
    ('animations.mod_vortex', 'ColorVortex', xres, yres),
    ('animations.mod_lava', 'Lava', xres, yres),
    ('animations.mod_fireplace', 'Fireplace', xres, yres),
    ('animations.mod_rainbow', 'Rainbow', xres, yres),
    ('animations.mod_maze', 'Maze', xres, yres),
    ('animations.mod_santatree_16x16', 'Santree', xres, yres),
    ('animations.mod_mandelbrot', 'Mandelbrot', xres, yres),
]

# BUTTONS PIN configuration:
plusButton = Pin(13, Pin.IN, Pin.PULL_UP)
minusButton = Pin(9, Pin.IN, Pin.PULL_UP)
modeButton = Pin(5, Pin.IN, Pin.PULL_UP)


def request_module(index):
    # Simulator/UI requests are consumed by the rendering thread.
    global pending_module
    pending_module = index


def select_module(index):
    global selected_module, current_module, clock_module
    if not 0 <= index < len(modules):
        return
    previous_name = modules[selected_module][0]
    current_module = None
    if modules[index][1] == 'Clock':
        clock_module = None
        display.overlay_backup = None
    if previous_name != 'animations.mod_clock' or clock_module is None:
        unload_module(previous_name)
    gc.collect()
    selected_module = index
    current_module = create_module(*modules[index])
    clear_board()
    reset_stats()
    print_log()


def mapPixel(x, y):
    return display.map_pixel(x, y)


def light(x, y, r, g, b, intense_override=None):
    brightness = intense if intense_override is None else intense_override
    display.light(x, y, r, g, b, brightness, remember=False)


def clear_board():
    display.clear()


def display_symbol16x16(symbol_name, color, duration):
    symbol = helpers.symbols_16x16.get(symbol_name)
    if symbol is None:
        return

    previous = bytes(frame.buf)
    # Display the symbol starting from (0, 0)
    for y in range(yres):
        for x in range(xres):
            if symbol[y][x]:
                light(x, y, *color)
            else:
                light(x, y, 0, 0, 0)
    frame.write()
    ui_sleep(duration)
    frame.buf[:] = previous
    frame.write()


def display_percentage(percent, color, duration=0.1):
    # Render percentage (digits + '%') centered as an overlay, then restore background
    s = str(int(max(0, min(100, percent))))
    digit_map = helpers.digits_5x3
    percent_map = helpers.letters_5x3.get('%')

    # compute width: digits + spaces + 1 space + percent
    digits_width = len(s) * 3 + (len(s) - 1) * 1
    total_width = digits_width + 1 + 3  # one column gap and percent glyph
    start_x = (xres - total_width) // 2
    start_y = (yres - 5) // 2

    # Bounded packed backup instead of a dict of coordinate/color tuples.
    prev = bytearray(total_width * 5 * 3)
    saved = 0
    for x in range(start_x, start_x + total_width):
        for y in range(start_y, start_y + 5):
            offset = mapPixel(x, y) * 3
            prev[saved] = frame.buf[offset]
            prev[saved + 1] = frame.buf[offset + 1]
            prev[saved + 2] = frame.buf[offset + 2]
            saved += 3

    # draw digits
    x_cursor = start_x
    for ch in s:
        glyph = digit_map.get(int(ch))
        if glyph is None:
            x_cursor += 4
            continue
        for gy in range(5):
            for gx in range(3):
                if glyph[gy][gx]:
                    light(x_cursor + gx, start_y + gy, *color, intense_override=128)
        x_cursor += 4  # 3 width + 1 spacing

    # draw percent glyph
    for gy in range(5):
        for gx in range(3):
            if percent_map[gy][gx]:
                light(x_cursor + gx, start_y + gy, *color, intense_override=128)

    frame.write()
    ui_sleep(duration)

    saved = 0
    for x in range(start_x, start_x + total_width):
        for y in range(start_y, start_y + 5):
            offset = mapPixel(x, y) * 3
            frame.buf[offset] = prev[saved]
            frame.buf[offset + 1] = prev[saved + 1]
            frame.buf[offset + 2] = prev[saved + 2]
            saved += 3
    frame.write()


def print_system_info():
    if SIMULATOR:
        print('runtime: {} {} | Pico firmware: unavailable in simulator'.format(
            sys.implementation.name, sys.version.replace('\n', ' ')))
    else:
        import os
        info = os.uname()
        print('firmware: MicroPython {} | board: {}'.format(info.version, info.machine))


def print_log(elapsed_us=0):
    # Read the current heap without forcing a collection or changing frame timing.
    used = gc.mem_alloc()
    free = gc.mem_free()
    total = used + free
    percent = used * 100 / total if total > 0 else 0
    memory_label = 'RAM (heap, simulated)' if SIMULATOR else 'RAM (Python heap)'
    cpu_freq = getattr(machine, 'freq', None)
    frequency = '{:.0f} MHz'.format(cpu_freq() / 1000000) if cpu_freq else 'n/a'
    log = ('mode: {} | module: {} ({}) | intense: {} | delay: {:.3f} s'
           ' | {}: {:.1f}/{:.1f} KiB used ({:.1f}%), {:.1f} KiB free | CPU: {}').format(
        mode, selected_module, modules[selected_module][1], intense, delay_ms,
        memory_label, used / 1024, total / 1024, percent, free / 1024, frequency)
    if elapsed_us > 0 and counter:
        log += (' | FPS (updates): {:.1f} | render avg/max: {:.2f}/{:.2f} ms'
                ' | render share: {:.1f}%').format(
            counter * 1000000 / elapsed_us, render_time_us / counter / 1000,
            peak_render_time_us / 1000, render_time_us * 100 / elapsed_us)
    print(log)


def reset_stats():
    global counter, start_time, render_time_us, peak_render_time_us
    counter = render_time_us = peak_render_time_us = 0
    start_time = stats_ticks_us() if DEBUG_STATS else 0


def set_mode(value):
    global mode, clock_module
    if value not in (0, 1, 2):
        raise ValueError('Mode must be 0, 1, or 2')
    if value == mode:
        return
    mode = value
    if mode != 2:
        clock_module = None
        if modules[selected_module][0] != 'animations.mod_clock' and 'animations.mod_clock' in sys.modules:
            unload_module('animations.mod_clock')
        display.overlay_backup = None
        gc.collect()
    symbol = ('triangle_up_down', 'sun', 'clock')[mode]
    color = (helpers.colors_rgb['green'], helpers.colors_rgb['yellow'],
             helpers.colors_rgb['blue'])[mode]
    display_symbol16x16(symbol, color, 0.5)
    print_log()


def set_brightness(value):
    global intense
    value = max(0, min(255, int(value)))
    if value == intense:
        return
    intense = value
    display.set_brightness(intense)
    display_percentage(intense * 100 // 255, helpers.colors_rgb['yellow'])
    print_log()


def handle_control(action):
    if action == 'mode':
        set_mode((mode + 1) % 3)
    elif action in ('plus', 'minus'):
        direction = 1 if action == 'plus' else -1
        if mode == 1:
            set_brightness(intense + direction * intense_step)
        else:
            index = max(0, min(len(modules) - 1, selected_module + direction))
            if index != selected_module:
                select_module(index)
    else:
        raise ValueError('Unknown control action')


def handle_buttons():
    global pending_module, button_mask, plus_repeat_at, minus_repeat_at
    # Desktop commands run on the same thread that owns the active module.
    if control_hook is not None:
        control_hook()
    if pending_module is not None:
        index = pending_module
        pending_module = None
        if index != selected_module:
            select_module(index)
    pressed = ((plusButton.value() == 0) | ((minusButton.value() == 0) << 1)
               | ((modeButton.value() == 0) << 2))
    edges = pressed & ~button_mask
    now = ticks_us()
    # Opposite buttons cancel each other. Mode advances once per press.
    if pressed & 3 == 1:
        new_press = edges & 1 or button_mask & 3 == 3
        if new_press or ticks_diff(now, plus_repeat_at) >= 0:
            handle_control('plus')
            plus_repeat_at = ticks_add(now, 350000 if new_press else 120000)
    elif pressed & 3 == 2:
        new_press = edges & 2 or button_mask & 3 == 3
        if new_press or ticks_diff(now, minus_repeat_at) >= 0:
            handle_control('minus')
            minus_repeat_at = ticks_add(now, 350000 if new_press else 120000)
    if edges & 4:
        handle_control('mode')
    button_mask = pressed


def free_memory():
    b_F = gc.mem_free()
    b_A = gc.mem_alloc()
    b_T = b_F + b_A
    b_P = '{0:.2f}%'.format(b_F / b_T * 100)

    gc.collect()

    F = gc.mem_free()
    P = '{0:.2f}%'.format(F / b_T * 100)

    print('Memory usage [prev/now] => Total: [{0}]  Free: [{1}|{2}] ({3}|{4})'.format(b_T, b_F, F, b_P, P))

# Setup actual time from NTP server and overclocking
try:
    init.run()
except RuntimeError:
    print("Could not initialize the program... Exit.")

selected_module = 0
mode = 0
current_module = create_module(*modules[selected_module])
# The overlay clock is allocated only while mode 2 is active.
delay_ms = 0.0
DEBUG_STATS = True
STATS_INTERVAL_US = 5000000
counter = 0
render_time_us = peak_render_time_us = 0
start_time = 0

def run():
    global counter, render_time_us, peak_render_time_us, delay_ms, clock_module
    print_system_info()
    print_log()
    reset_stats()
    while True:
        handle_buttons()
        if DEBUG_STATS:
            render_started = stats_ticks_us()
        is_full_frame, delay_ms, changes = current_module.get()
        changed = display.apply(is_full_frame, changes, intense)
        # Drop output references before a later module switch and its allocation.
        changes = None

        if mode == 2 and modules[selected_module][1] != 'Clock':
            if clock_module is None:
                clock_module = create_module('animations.mod_clock', 'Clock', xres, yres)
            _, _, clock_frame = clock_module.get()
            display.show_overlay(clock_frame, intense)
            clock_frame = None
        elif changed:
            frame.write()
        if DEBUG_STATS:
            duration = stats_ticks_diff(stats_ticks_us(), render_started)
            counter += 1
            render_time_us += duration
            peak_render_time_us = max(peak_render_time_us, duration)
        time.sleep(delay_ms)

        if DEBUG_STATS:
            elapsed = stats_ticks_diff(stats_ticks_us(), start_time)
            if elapsed >= STATS_INTERVAL_US:
                print_log(elapsed)
                reset_stats()


if __name__ == '__main__':
    run()
