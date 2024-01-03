from machine import Pin
from time import sleep
from neopixel import NeoPixel
import settime

from mod_raybouncer import Bounce
from mod_clock import Clock
from mod_santatree_16x16 import Santree
from mod_matrixrain import MatrixRain


# LED matrix configuration
intense = 255 # 0 - 255
intense_step = 5
xres = 16
yres = 16
ledControlPin = 22
wall = NeoPixel(Pin(ledControlPin), xres * yres)
wall.write()

# MODULES:
modules = [Clock(xres, yres), Bounce(xres, yres), Santree(xres, yres), MatrixRain(xres, yres)]

# BUTTONS PIN configuration:
plusButton = Pin(13, Pin.IN, Pin.PULL_UP)
minusButton = Pin(9, Pin.IN, Pin.PULL_UP)
modeButton = Pin(5, Pin.IN, Pin.PULL_UP)


def mapPixel(x, y):
    if y % 2 == 1:
        return xres * y + x
    else:
        return xres * y + xres - 1 - x


def light(x, y, r, g, b):
    wall[mapPixel(x, y)] = (int(r*(intense/255)), int(g*(intense/255)), int(b*(intense/255)))


def clear_board():
    for y in range(yres):
        for x in range(xres):
            if wall[mapPixel(x, y)] != (0, 0 ,0):
                light(x, y, 0, 0, 0)

def blink(r, g, b, s):
    for y in range(yres):
        for x in range(xres):
            light(x, y, r, g, b)
    
    wall.write()                
    print("blink")
    sleep(s)
    clear_board()


# setup actual time from NTP server
try:
    settime.run()
except RuntimeError:
    print("Could not connect to wifi network")

print('test1')
selected_module = 0
mode = 0

while True:
    if plusButton.value() is 0:
        if mode == 0:
            selected_module += 0 if selected_module == len(modules) - 1 else 1
            clear_board()
            print("mode: ", mode, " | selected module: ", selected_module, " | intense", intense)
        elif mode == 1:
            intense = min(255, intense + intense_step)
            print("mode: ", mode, " | selected module: ", selected_module, " | intense", intense)
    
    if minusButton.value() is 0:
        if mode == 0:
            selected_module -= 0 if selected_module <= 0 else 1
            clear_board()
            print("mode: ", mode, " | selected module: ", selected_module, " | intense", intense)
        elif mode == 1:
            intense = max(0, intense - intense_step)
            print("mode: ", mode, " | selected module: ", selected_module, " | intense", intense)
        
    if modeButton.value() is 0:
        mode = 0 if mode == 1 else 1
        print("mode: ", mode, " | selected module: ", selected_module, " | intense", intense)
        
        if mode == 0:
            blink(0, 255, 0, 0.05)
        elif mode == 1:
            blink(0, 0, 255, 0.05)

    changes = modules[selected_module].get()
    
    for ch in changes:
        light(ch[0], ch[1], ch[2][0], ch[2][1], ch[2][2])

    wall.write()
    sleep(0.1)

