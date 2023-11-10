from machine import Pin
from time import sleep
from neopixel import NeoPixel
from mod_raybouncer import Bounce
from mod_clock import Clock


# 0 - 255
intense = 16
xres = 16
yres = 16
pin = 22
wall = NeoPixel(Pin(pin), xres * yres)
wall.write()


def mapPixel(x, y):
    if y % 2 == 1:
        return xres * y + x
    else:
        return xres * y + xres - 1 - x


def light(x, y, r, g, b):
    wall[mapPixel(x, y)] = (int(intense*r/255), int(intense*g/255), int(intense*b/255))


def clear_board():
    for y in range(yres):
        for x in range(xres):
            if wall[mapPixel(x, y)] != (0, 0 ,0):
                light(x, y, 0, 0, 0)


# mod = Bounce(xres, yres)
mod = Clock(xres, yres)

i = 0
while True:
    changes = mod.get()
    
    for ch in changes:
        light(ch[0], ch[1], ch[2][0], ch[2][1], ch[2][2])

    wall.write()
    sleep(0.1)
    
    i += 1
    if i == 10:
        i = 0

