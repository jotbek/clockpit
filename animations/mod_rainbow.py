from core.colors import rainbow_palette
from core.native import micropython, ptr8


class Rainbow:
    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.counter = 0
        self.frame = bytearray(xres * yres * 3)
        self.palette = rainbow_palette()

    def get(self):
        self._render()
        self.counter = (self.counter + 1) % 360
        return True, 0.0, self.frame

    @micropython.viper
    def _render(self):
        frame = ptr8(self.frame)
        palette = ptr8(self.palette)
        height = int(self.yres)
        width = int(self.xres)
        counter = int(self.counter)
        for x in range(width):
            offset = x * height * 3
            start = ((x + counter) % 360) * 3
            end = ((x + counter + 100) % 360) * 3
            r = int(palette[start])
            g = int(palette[start + 1])
            b = int(palette[start + 2])
            nr = int(palette[end])
            ng = int(palette[end + 1])
            nb = int(palette[end + 2])
            frame[offset] = r
            frame[offset + 1] = g
            frame[offset + 2] = b
            for y in range(1, height):
                offset += 3
                frame[offset] = (r * (height - y) + nr * y) // height
                frame[offset + 1] = (g * (height - y) + ng * y) // height
                frame[offset + 2] = (b * (height - y) + nb * y) // height
