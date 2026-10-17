import math
from array import array
from core.colors import rainbow_palette
from core.native import micropython, ptr8, ptr16


class ColorVortex:
    def __init__(self, xres, yres, speed=0.2, delay=0.1):
        self.xres = xres
        self.yres = yres
        self.delay = delay
        self.angle = 0.0
        self.speed = speed * 180 / math.pi * 128
        self.frame = bytearray(xres * yres * 3)
        self.palette = rainbow_palette()
        # Fixed geometry: 1/128 degree resolution, two bytes per pixel.
        self.angles = array('H')
        for x in range(xres):
            for y in range(yres):
                angle = math.atan2(y - yres // 2, x - xres // 2)
                self.angles.append(int((angle * 180 / math.pi) % 360 * 128))

    def get(self):
        self._render(int(self.angle))
        self.angle = (self.angle + self.speed) % 46080
        return True, self.delay, self.frame

    @micropython.viper
    def _render(self, phase: int):
        frame = ptr8(self.frame)
        angles = ptr16(self.angles)
        palette = ptr8(self.palette)
        size = int(len(self.angles))
        for i in range(size):
            colour = (((int(angles[i]) + phase) % 46080) // 128) * 3
            offset = i * 3
            frame[offset] = palette[colour]
            frame[offset + 1] = palette[colour + 1]
            frame[offset + 2] = palette[colour + 2]
