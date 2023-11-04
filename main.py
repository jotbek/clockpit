from machine import Pin
from time import sleep
from neopixel import NeoPixel
from mod_raybouncer import Bounce
from mod_clock import Clock

# 0 - 255
intense = 8

internal_pin = Pin("LED", Pin.OUT)
internal_pin.on()

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

# mod = Bounce(xres, yres, 10, [[0, 0, 128], [128, 0, 0]])
mod = Clock()

while True:
    changes = mod.get(4)
    print(changes)
    
    for ch in changes:
        light(ch[0], ch[1], ch[2][0], ch[2][1], ch[2][2])

    wall.write()
    sleep(0.08)

sleep(1)
internal_pin.off()
print("Finished.")