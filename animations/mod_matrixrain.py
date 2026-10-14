import random


class MatrixRain:
    r = 230
    g = 255
    b = 230
    rb_reduction = 30
    g_reduction = 10

    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.frame = bytearray(xres * yres * 3)

    def get(self):
        frame = self.frame
        height = self.yres
        if random.randrange(0, 100) < 70:
            offset = random.randrange(0, self.xres) * height * 3
            frame[offset] = self.r
            frame[offset + 1] = self.g
            frame[offset + 2] = self.b
        for x in range(self.xres):
            for y in range(height - 1, -1, -1):
                offset = (x * height + y) * 3
                r, g, b = frame[offset], frame[offset + 1], frame[offset + 2]
                if y < height - 1:
                    frame[offset + 3] = r
                    frame[offset + 4] = g
                    frame[offset + 5] = b
                if r or b:
                    frame[offset] = max(r - self.rb_reduction, 0)
                    frame[offset + 1] = self.g
                    frame[offset + 2] = max(b - self.rb_reduction, 0)
                elif g:
                    frame[offset + 1] = max(g - self.g_reduction, 0)
        return True, 0.1, frame
