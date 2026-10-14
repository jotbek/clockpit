import math
from array import array
from core.colors import rainbow_into


class ColorVortex:
    def __init__(self, xres, yres, speed=0.2, delay=0.1):
        self.xres = xres
        self.yres = yres
        self.delay = delay
        self.angle = 0.0
        self.speed = speed * 180 / math.pi * 128
        self.frame = bytearray(xres * yres * 3)
        # Fixed geometry: 1/128 degree resolution, two bytes per pixel.
        self.angles = array('H')
        for x in range(xres):
            for y in range(yres):
                angle = math.atan2(y - yres // 2, x - xres // 2)
                self.angles.append(int((angle * 180 / math.pi) % 360 * 128))

    def get(self):
        frame = self.frame
        angles = self.angles
        phase = int(self.angle)
        for i in range(len(angles)):
            rainbow_into(frame, i * 3, ((angles[i] + phase) % 46080) // 128)
        self.angle = (self.angle + self.speed) % 46080
        return True, self.delay, frame
