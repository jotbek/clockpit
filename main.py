#
# To work you should provide credentials to selected WiFi network you want to connect
# Put them to the secrets.py file as strings:
# wifi_name = 'ssid_of_network'
# wifi_pass = 'password'
#
from machine import Pin
from neopixel import NeoPixel
import init
import time
import gc

from mod_raybouncer import Bounce
from mod_clock import Clock
from mod_santatree_16x16 import Santree
from mod_matrixrain import MatrixRain
from mod_lava import Lava
from mod_fireplace import Fireplace
from mod_fireplasma import FirePlasma
from mod_gameoflife import GameOfLife
from mod_rainbow import Rainbow
from mod_vortex import ColorVortex
import helpers

# LED matrix configuration
intense = 96  # 0 - 255
intense_step = 4
xres = 16
yres = 16
ledControlPin = 22
frame = NeoPixel(Pin(ledControlPin), xres * yres)
frame.write()
current_module = None
clock_module = None

# MODULES:
modules = [
    (Clock, xres, yres),
    (FirePlasma, xres, yres),
    (ColorVortex, xres, yres),
    (GameOfLife, xres, yres),
    (Lava, xres, yres),
    (Fireplace, xres, yres),
    (Bounce, xres, yres),
    (MatrixRain, xres, yres),
    (Rainbow, xres, yres),
    (Santree, xres, yres),
]

# BUTTONS PIN configuration:
plusButton = Pin(13, Pin.IN, Pin.PULL_UP)
minusButton = Pin(9, Pin.IN, Pin.PULL_UP)
modeButton = Pin(5, Pin.IN, Pin.PULL_UP)


def delete_module(module):
    del module
    gc.collect()


def create_module(module_class, xres, yres):
    new_module = module_class(xres, yres)
    gc.collect()
    return new_module


def mapPixel(x, y):
    if y % 2 == 1:
        return xres * y + x
    else:
        return xres * y + xres - 1 - x


def light(x, y, r, g, b):
    frame[mapPixel(x, y)] = (int(r*(intense/255)), int(g*(intense/255)), int(b*(intense/255)))


def clear_board():
    for y in range(yres):
        for x in range(xres):
            if frame[mapPixel(x, y)] != (0, 0, 0):
                light(x, y, 0, 0, 0)


def display_symbol16x16(symbol_name, color, duration):
    symbol = helpers.symbols_16x16.get(symbol_name)
    if symbol is None:
        return

    # Display the symbol starting from (0, 0)
    for y in range(yres):
        for x in range(xres):
            if symbol[y][x]:
                light(x, y, *color)
            else:
                light(x, y, 0, 0, 0)
    frame.write()
    time.sleep(duration)
    clear_board()


def print_log():
    print("mode: ", mode, " | selected module: ", selected_module, " | intense: ", intense, " | delay: ", delay_ms)


def handle_buttons():
    global mode, selected_module, intense, intense_step, current_module
    if plusButton.value() == 0:
        if mode == 0 or mode == 2:
            selected_module += 1 if selected_module < len(modules) - 1 else 0
            delete_module(current_module)
            current_module = create_module(*modules[selected_module])
            clear_board()
            print_log()
        elif mode == 1:
            intense = min(255, intense + intense_step)
            print_log()

    if minusButton.value() == 0:
        if mode == 0 or mode == 2:
            selected_module -= 1 if selected_module > 0 else 0
            delete_module(current_module)
            current_module = create_module(*modules[selected_module])
            clear_board()
            print_log()
        elif mode == 1:
            intense = max(0, intense - intense_step)
            print_log()

    if modeButton.value() == 0:
        mode = (mode + 1) % 3  # Cycle through modes 0, 1, 2
        print("mode: ", mode, " | selected module: ", selected_module, " | intense", intense)

        if mode == 0:
            # Display the triangle symbol in green color
            display_symbol16x16('triangle_up_down', helpers.colors_rgb['green'], 0.5)
        elif mode == 1:
            # Display the sun symbol in yellow color
            display_symbol16x16('sun', helpers.colors_rgb['yellow'], 0.5)
        elif mode == 2:
            # Display the clock symbol in blue color
            display_symbol16x16('clock', helpers.colors_rgb['blue'], 0.5)


def free_memory():
    b_F = gc.mem_free()
    b_A = gc.mem_alloc()
    b_T = b_F + b_A
    b_P = '{0:.2f}%'.format(b_F / b_T * 100)

    gc.collect()

    F = gc.mem_free()
    P = '{0:.2f}%'.format(F / b_T * 100)

    print('Memory usage [prev/now] => Total: [{0}]  Free: [{1}|{2}] ({3}|{4})'.format(b_T, b_F, F, b_P, P))

# Setup actual time from NTP server
try:
    init.run()
except RuntimeError:
    print("Could not connect to Wi-Fi network")

selected_module = 0
mode = 0
current_module = create_module(*modules[selected_module])
clock_module = create_module(Clock, xres, yres)  # Create the clock module once

# To print out the number of fps module use every 'max_counter' rounds (should not impact performance)
counter = 0
max_counter = 25
start_time = time.time_ns()

while True:
    if counter == max_counter:
        counter = 0
        print('fps: ', "{:.2f}".format(max_counter / ((time.time_ns() - start_time) / 1e9)))
        start_time = time.time_ns()
        free_memory()

    handle_buttons()

    is_full_frame, delay_ms, changes = current_module.get()

    if mode == 2:
        # Overlay clock on top of current module
        clock_is_full_frame, clock_delay_ms, clock_changes = clock_module.get()
        # Apply the current module's changes
        if is_full_frame:
            for y in range(yres):
                for x in range(xres):
                    light(x, y, changes[x][y][0], changes[x][y][1], changes[x][y][2])
        else:
            for ch in changes:
                light(ch[0], ch[1], ch[2][0], ch[2][1], ch[2][2])
        # Then, apply the clock's changes, overwriting any overlapping pixels
        if clock_is_full_frame:
            for y in range(yres):
                for x in range(xres):
                    light(x, y, clock_changes[x][y][0], clock_changes[x][y][1], clock_changes[x][y][2])
        else:
            for ch in clock_changes:
                light(ch[0], ch[1], ch[2][0], ch[2][1], ch[2][2])
    else:
        # Display current module normally
        if is_full_frame:
            for y in range(yres):
                for x in range(xres):
                    light(x, y, changes[x][y][0], changes[x][y][1], changes[x][y][2])
        else:
            for ch in changes:
                light(ch[0], ch[1], ch[2][0], ch[2][1], ch[2][2])

    frame.write()
    time.sleep(delay_ms)

    counter += 1
