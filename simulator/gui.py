"""Tkinter simulator. Run with: python -m simulator.gui."""
import tkinter as tk
from tkinter import ttk
import time

from simulator.runtime import SimulatorRuntime


class SimulatorWindow:
    def __init__(self, root, runtime):
        self.root = root
        self.runtime = runtime
        self.closed = False
        self.pending_selection = None
        self.repeat_jobs = {}
        self.poll_job = None
        self.preview_frames = 0
        self.last_collection = time.monotonic()
        self.root.title('Clockpit GUI Simulator')
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<FocusOut>', self.cancel_repeats)
        width, height = runtime.app.xres, runtime.app.yres
        self.width, self.height = width, height
        cell, padding = 24, 1
        self.canvas = tk.Canvas(root, width=width * (cell + padding) + padding,
                                height=height * (cell + padding) + padding,
                                bg='black', highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=3)
        self.rectangles = []
        self.last_colors = [None] * (width * height)
        for y in range(height):
            for x in range(width):
                left, top = padding + x * (cell + padding), padding + y * (cell + padding)
                self.rectangles.append(self.canvas.create_rectangle(
                    left, top, left + cell, top + cell, fill='#000000', outline='#101010'))
        self.buttons = {}
        for action, label, row, column in (('plus', 'Up', 1, 0), ('minus', 'Down', 2, 0),
                                           ('mode', 'Mode', 1, 1)):
            button = tk.Button(root, text=label, width=12,
                               command=lambda action=action: self.submit('button', action))
            button.grid(row=row, column=column, padx=5, pady=4)
            button.bind('<ButtonPress-1>', lambda event, action=action: self.press(action))
            button.bind('<ButtonRelease-1>', lambda event, action=action: self.release(action))
            button.bind('<Leave>', lambda event, action=action: self.release(action))
            self.buttons[action] = button
        self.module_names = [spec[1] for spec in runtime.app.modules]
        self.module_combo = ttk.Combobox(root, values=self.module_names, state='readonly', width=20)
        self.module_combo.current(runtime.snapshot()['module'])
        self.module_combo.grid(row=1, column=2, padx=5, pady=5)
        self.module_combo.bind('<<ComboboxSelected>>', self.select_module)
        self.speed_label = tk.StringVar(root)
        tk.Label(root, textvariable=self.speed_label).grid(row=2, column=1)
        self.speed_down = tk.Button(root, text='Speed -', width=12, command=lambda: self.change_speed(-1))
        self.speed_down.grid(row=2, column=2, padx=5, pady=4)
        self.speed_up = tk.Button(root, text='Speed +', width=12, command=lambda: self.change_speed(1))
        self.speed_up.grid(row=3, column=2, padx=5, pady=4)
        tk.Button(root, text='Exit', width=12, command=self.close).grid(row=3, column=0, padx=5, pady=4)
        self.status = tk.StringVar(root, value='Starting simulator...')
        tk.Label(root, textvariable=self.status, anchor='w', width=60).grid(
            row=4, column=0, columnspan=3, sticky='we', padx=5, pady=4)
        self.refresh_speed()
        self.poll()

    def submit(self, command, value):
        try:
            return self.runtime.post(command, value)
        except (ValueError, RuntimeError) as error:
            self.status.set(str(error))
            return None

    def press(self, action):
        if action in self.repeat_jobs:
            return 'break'
        self.submit('button', action)
        if action != 'mode':
            self.repeat_jobs[action] = self.root.after(350, self.repeat, action)
        return 'break'

    def repeat(self, action):
        if action not in self.repeat_jobs or self.closed:
            return
        self.submit('button', action)
        self.repeat_jobs[action] = self.root.after(120, self.repeat, action)

    def release(self, action):
        job = self.repeat_jobs.pop(action, None)
        if job is not None:
            self.root.after_cancel(job)
        return 'break'

    def cancel_repeats(self, event=None):
        for action in tuple(self.repeat_jobs):
            self.release(action)

    def select_module(self, event=None):
        index = self.module_combo.current()
        if index >= 0:
            serial = self.submit('module', index)
            if serial is not None:
                self.pending_selection = serial

    def change_speed(self, direction):
        self.runtime.step_speed(direction)
        self.refresh_speed()

    def refresh_speed(self):
        speed = self.runtime.snapshot()['speed']
        self.speed_label.set('Speed: x{:.2f}'.format(speed))
        self.speed_down.configure(state='disabled' if speed <= 0.01 else 'normal')
        self.speed_up.configure(state='disabled' if speed >= 50 else 'normal')

    def draw(self, frame):
        commands = []
        for y in range(self.height):
            for x in range(self.width):
                index = y * self.width + x
                physical = y * self.width + (x if y & 1 else self.width - 1 - x)
                offset = physical * 3
                color = '#{:02x}{:02x}{:02x}'.format(frame[offset + 1], frame[offset], frame[offset + 2])
                if color != self.last_colors[index]:
                    commands.append('{} itemconfigure {} -fill {}'.format(
                        self.canvas._w, self.rectangles[index], color))
                    self.last_colors[index] = color
        # Tk calls stay on the GUI thread, with a single batched Canvas update.
        if commands:
            self.canvas.tk.eval(';'.join(commands))
        self.preview_frames += 1

    def poll(self):
        if self.closed:
            return
        now = time.monotonic()
        if now - self.last_collection >= 1:
            self.runtime.collect_garbage()
            self.last_collection = now
        frame = self.runtime.take_frame()
        if frame is not None:
            self.draw(frame)
        state = self.runtime.snapshot()
        if self.pending_selection is not None and state['acknowledged'] >= self.pending_selection:
            self.pending_selection = None
        if self.pending_selection is None and self.module_combo.current() != state['module']:
            self.module_combo.current(state['module'])
        self.refresh_speed()
        if state['error']:
            self.status.set('Worker stopped: ' + state['error'])
            self.cancel_repeats()
            for button in self.buttons.values():
                button.configure(state='disabled')
            self.module_combo.configure(state='disabled')
        elif state['stopped']:
            self.status.set('Simulator stopped')
        else:
            modes = ('Select module', 'Brightness', 'Clock overlay')
            pending = ' | Applying controls...' if state['requested'] > state['acknowledged'] else ''
            self.status.set('{} | {} | Brightness: {}%{}'.format(
                self.module_names[state['module']], modes[state['mode']],
                state['brightness'] * 100 // 255, pending))
        self.poll_job = self.root.after(33, self.poll)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel_repeats()
        if self.poll_job is not None:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None
        self.runtime.stop()
        self.root.destroy()


def run():
    runtime = SimulatorRuntime().start()
    root = None
    try:
        root = tk.Tk()
        window = SimulatorWindow(root, runtime)
        print('[simulator] ready: 16x16, {} modules'.format(len(window.module_names)), flush=True)
        root.mainloop()
    finally:
        runtime.stop()
        if root is not None:
            try:
                if root.winfo_exists():
                    root.destroy()
            except tk.TclError:
                pass


if __name__ == '__main__':
    run()
