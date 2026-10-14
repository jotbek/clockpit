import math
from array import array


class Lava:
    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.frame = bytearray(xres * yres * 3)
        self.sines = array('f', bytes(max(xres, yres) * 4))
        self.cosines = array('f', bytes(max(xres, yres) * 4))
        self.delta3 = 0.0
        self.delta4 = 1.0

    def get(self):
        self.animate()
        return True, 0.0, self.frame

    def animate(self):
        frame = self.frame
        sines, cosines = self.sines, self.cosines
        self.delta3 = (self.delta3 + 0.2) % (2 * math.pi)
        self.delta4 = (self.delta4 + 0.28) % (2 * math.pi)
        # 32 trig evaluations for 16x16, instead of 1024.
        for i in range(len(sines)):
            sines[i] = math.sin(self.delta3 + i * 0.4)
            cosines[i] = math.cos(self.delta4 + i * 0.4)
        offset = 0
        for x in range(self.xres):
            for y in range(self.yres):
                r = 128 + math.floor((sines[x] + cosines[y]) * 63)
                g = 128 + math.floor((sines[y] + cosines[x]) * 63)
                frame[offset] = r // 2
                frame[offset + 1] = g // 2
                frame[offset + 2] = (255 - r) // 2
                offset += 3
