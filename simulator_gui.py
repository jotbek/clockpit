"""
GUI simulator for Clockpit project
- Buttons: Up, Down, Mode
- LED matrix rendered with tkinter Canvas using `main.mapPixel` for correct serpentine layout
Run with: python simulator_gui.py
"""
import sys
import types
import threading
import time
import os
import subprocess

# --- Minimal gc stub ---
fake_gc = types.ModuleType('gc')
fake_gc._mem_total = 1024 * 1024
fake_gc.mem_free = lambda: fake_gc._mem_total // 2
fake_gc.mem_alloc = lambda: fake_gc._mem_total - fake_gc.mem_free()
fake_gc.collect = lambda: None
sys.modules['gc'] = fake_gc

# --- init stub ---
init = types.ModuleType('init')
def init_run():
    print('[simulator_gui] init.run() called (noop)')
init.run = init_run
sys.modules['init'] = init

# --- machine.Pin and RTC stubs that integrate with the GUI ---
class Pin:
    IN = 0
    PULL_UP = 1
    _states = {}  # pin -> pressed(bool)

    def __init__(self, pin, mode=None, pull=None):
        self.pin = pin
        Pin._states.setdefault(pin, False)

    def value(self):
        # Active-low: 0 when pressed, 1 when released
        return 0 if Pin._states.get(self.pin, False) else 1

    # GUI will call this to set press/release
    @classmethod
    def set_state(cls, pin, pressed: bool):
        cls._states[pin] = bool(pressed)

class RTC:
    def datetime(self):
        return time.localtime()

machine = types.ModuleType('machine')
machine.Pin = Pin
machine.RTC = RTC
sys.modules['machine'] = machine

# --- neopixel stub that can call a GUI callback ---
class NeoPixel:
    _frame_callback = None

    def __init__(self, pin, n):
        self.n = n
        self.buf = [(0, 0, 0)] * n

    def __setitem__(self, idx, val):
        self.buf[idx] = tuple(val)

    def __getitem__(self, idx):
        return self.buf[idx]

    def write(self):
        # Store snapshot and notify GUI (if any)
        if NeoPixel._frame_callback:
            # pass a copy to avoid races
            NeoPixel._frame_callback(list(self.buf))

    @classmethod
    def register_frame_callback(cls, cb):
        cls._frame_callback = cb

neopixel = types.ModuleType('neopixel')
neopixel.NeoPixel = NeoPixel
sys.modules['neopixel'] = neopixel

# --- Tkinter GUI ---
import tkinter as tk
from tkinter import messagebox

# Worker: import `main` (runs the app) in a background thread
# Simulation speed controls: discrete SPEED_OPTIONS list (choose values explicitly)
real_time = __import__('time')
SPEED_OPTIONS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 20.0, 50.0]
simulation_state = {'speed': 1.0}
_orig_sleep = real_time.sleep

def _sim_sleep(s):
    # Protect against zero/negative speed and keep behavior stable
    sp = max(simulation_state.get('speed', 1.0), 0.0001)
    return _orig_sleep(s / sp)

# Override global sleep so the application respects GUI speed control
real_time.sleep = _sim_sleep


def set_speed(value):
    # Snap to the nearest option from SPEED_OPTIONS
    try:
        v = float(value)
    except Exception:
        v = simulation_state.get('speed', 1.0)
    closest = min(SPEED_OPTIONS, key=lambda x: abs(x - v))
    simulation_state['speed'] = closest


def step_speed(delta):
    # delta = +1 (increase) or -1 (decrease)
    cur = simulation_state.get('speed', 1.0)
    try:
        idx = SPEED_OPTIONS.index(cur)
    except ValueError:
        # find nearest index
        idx = min(range(len(SPEED_OPTIONS)), key=lambda i: abs(SPEED_OPTIONS[i] - cur))
    idx = max(0, min(len(SPEED_OPTIONS) - 1, idx + int(delta)))
    simulation_state['speed'] = SPEED_OPTIONS[idx]


def get_speed():
    return simulation_state['speed']


def run_main_module():
    try:
        import importlib
        importlib.import_module('main')
    except Exception as e:
        print('[simulator_gui] Error while importing/running main:', e)

worker = threading.Thread(target=run_main_module, daemon=True)
worker.start()

# Wait for main to appear in sys.modules (it will be present early during import)
waited = 0
while 'main' not in sys.modules and waited < 5.0:
    time.sleep(0.01)
    waited += 0.01

if 'main' not in sys.modules:
    print('[simulator_gui] main module not found within timeout. Aborting GUI.')
    sys.exit(1)

main = sys.modules['main']

# Read xres/yres from main
xres = getattr(main, 'xres', 16)
yres = getattr(main, 'yres', 16)

CELL = 24  # pixels per virtual LED
PAD = 1
WIDTH = xres * CELL + (xres + 1) * PAD
HEIGHT = yres * CELL + (yres + 1) * PAD

root = tk.Tk()
root.title('Clockpit GUI Simulator')
# Prevent window resizing to keep pixel layout stable
root.resizable(False, False)

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg='black')
canvas.grid(row=0, column=0, columnspan=3)

# Create rectangles representing pixels and keep their ids
rect_ids = [[None for _ in range(xres)] for _ in range(yres)]
for y in range(yres):
    for x in range(xres):
        x0 = PAD + x * (CELL + PAD)
        y0 = PAD + y * (CELL + PAD)
        x1 = x0 + CELL
        y1 = y0 + CELL
        rect_ids[y][x] = canvas.create_rectangle(x0, y0, x1, y1, fill='#000000', outline='#101010')

# Update function called from NeoPixel.write
def rgb_to_hex(rgb):
    r, g, b = rgb
    return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))

# Use main.mapPixel for serpentine mapping
def update_frame(buf):
    try:
        mapper = getattr(main, 'mapPixel')
    except Exception:
        mapper = None

    for y in range(yres):
        for x in range(xres):
            idx = mapper(x, y) if mapper is not None else (y * xres + x)
            col = buf[idx]
            canvas.itemconfig(rect_ids[y][x], fill=rgb_to_hex(col))

# Register callback
NeoPixel.register_frame_callback(lambda buf: root.after(0, update_frame, buf))

# Buttons: 'Up' -> pin 13, 'Down' -> pin 9, 'Mode' -> pin 5
BUTTON_MAP = {
    '1': 13,
    '2': 9,
    '3': 5,
} 

def press_pin(pin):
    Pin.set_state(pin, True)

def release_pin(pin):
    Pin.set_state(pin, False)

def on_button_press(pin):
    # simulate momentary press while mouse button is held
    press_pin(pin)

def on_button_release(pin):
    release_pin(pin)

# Create GUI Buttons
# Create GUI Buttons (Up above Down)
btn1 = tk.Button(root, text='Up', width=12)
btn1.grid(row=1, column=0, padx=5, pady=(5,2))
btn1.bind('<ButtonPress-1>', lambda e: on_button_press(BUTTON_MAP['1']))
btn1.bind('<ButtonRelease-1>', lambda e: on_button_release(BUTTON_MAP['1']))

btn2 = tk.Button(root, text='Down', width=12)
btn2.grid(row=2, column=0, padx=5, pady=(2,5))
btn2.bind('<ButtonPress-1>', lambda e: on_button_press(BUTTON_MAP['2']))
btn2.bind('<ButtonRelease-1>', lambda e: on_button_release(BUTTON_MAP['2']))

# Mode button stays to the right of the Up/Down column
btn3 = tk.Button(root, text='Mode', width=12)
btn3.grid(row=1, column=1, padx=5, pady=5)
btn3.bind('<ButtonPress-1>', lambda e: on_button_press(BUTTON_MAP['3']))
btn3.bind('<ButtonRelease-1>', lambda e: on_button_release(BUTTON_MAP['3']))

# Module selection combobox (centered)
from tkinter import ttk
module_names = [m[0].__name__ for m in getattr(main, 'modules', [])]
module_combo = ttk.Combobox(root, values=module_names, state='readonly', width=20)
try:
    module_combo.current(getattr(main, 'selected_module', 0))
except Exception:
    pass
module_combo.grid(row=1, column=2, padx=5, pady=5)

# When user selects a module from the combobox, switch module immediately
def on_module_selected(event=None):
    idx = module_combo.current()
    if idx < 0:
        return
    try:
        # Only change if different
        if getattr(main, 'selected_module', None) != idx:
            # delete and recreate module safely
            if getattr(main, 'current_module', None) is not None:
                try:
                    main.delete_module(main.current_module)
                except Exception:
                    pass
            main.selected_module = idx
            main.current_module = main.create_module(*main.modules[idx])
            try:
                main.clear_board()
            except Exception:
                pass
            try:
                main.print_log()
            except Exception:
                pass
    except Exception as e:
        print('[simulator_gui] Error switching module from combobox:', e)

module_combo.bind('<<ComboboxSelected>>', on_module_selected)

# Speed controls and Reset / Exit buttons
# Speed display and controls
speed_label = tk.Label(root, text=f'Speed: x{get_speed():.2f}')
speed_label.grid(row=2, column=1)

def update_speed_label():
    speed_label.config(text=f'Speed: x{get_speed():.2f}')

# Place speed controls in the right column to avoid overlapping the Up/Down column
btn_speed_down = tk.Button(root, text='Speed -', width=12, command=lambda: (step_speed(-1), update_speed_label()))
btn_speed_down.grid(row=2, column=2, padx=5, pady=(4,2))

btn_speed_up = tk.Button(root, text='Speed +', width=12, command=lambda: (step_speed(1), update_speed_label()))
btn_speed_up.grid(row=3, column=2, padx=5, pady=(2,6))

# Exit button only (Reset removed)
def on_exit():
    if messagebox.askokcancel('Exit', 'Stop simulator and exit?'):
        os._exit(0)

exit_btn = tk.Button(root, text='Exit', width=12, command=on_exit)
exit_btn.grid(row=3, column=0, padx=5, pady=6)


# Initial paint: if main.frame exists, use its buffer
try:
    frame = getattr(main, 'frame', None)
    if frame:
        update_frame(list(frame.buf))
except Exception:
    pass

# Periodic sync: update combobox selection to reflect main.selected_module
def poll_selected_module():
    try:
        idx = getattr(main, 'selected_module', None)
        if idx is not None and module_combo.current() != idx:
            module_combo.current(idx)
    except Exception:
        pass
    # schedule next poll
    root.after(150, poll_selected_module)

# Start polling
root.after(150, poll_selected_module)

root.mainloop()
