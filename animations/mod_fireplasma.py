from array import array
import random

try:
    import micropython
except ImportError:
    class micropython:
        @staticmethod
        def viper(function):
            return function

    def ptr8(buffer):
        return memoryview(buffer).cast('B')

    def ptr16(buffer):
        return memoryview(buffer).cast('B').cast('H')


class FirePlasma:
    xres = 0
    yres = 0
    width = 0
    height = 0
    fire_spawns = 5
    damping_factor = 0.97
    fire_colours = [[0, 0, 0],
                    [15, 0, 0],
                    [30, 0, 0],
                    [180, 0, 0],
                    [220, 100, 0],
                    [252, 210, 60],
                    [252, 220, 100],
                    [255, 255, 180]]


    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.width = xres + 2
        self.height = yres + 4
        self.frame = bytearray(xres * yres * 3)
        # Contiguous columns let Viper access the whole field through one pointer.
        self.heat = array('H', bytes(self.width * self.height * 2))
        self.palette = bytearray(channel for colour in self.fire_colours for channel in colour)


    def get(self):
        self.update()
        self.draw()
        return True, 0.0, self.frame


    def update(self):
        # take local references as it's quicker than accessing the global
        # and we access it a lot in this method
        _heat = self.heat
        height = self.height

        # clear the bottom row and then add a new fire seed to it
        for x in range(self.width):
            _heat[x * height + height - 1] = 0
            _heat[x * height + height - 2] = 0

        for c in range(self.fire_spawns):
            x = random.randint(0, self.width - 4) + 2
            offset = x * height + height - 1
            _heat[offset] = 4095
            _heat[offset + height] = 4095
            _heat[offset - height] = 4095
            _heat[offset - 1] = 4095
            _heat[offset + height - 1] = 4095
            _heat[offset - height - 1] = 4095

        # Q12 fixed point: sums/products stay within MicroPython small integers.
        factor = int(self.damping_factor * 4096 / 5)
        self._propagate(factor)

    @micropython.viper
    def _propagate(self, factor: int):
        heat = ptr16(self.heat)
        width = int(self.width)
        height = int(self.height)
        # Preserve the original in-place update order (rows, then columns).
        for y in range(height - 2):
            for x in range(1, width - 1):
                offset = x * height + y
                total = (int(heat[offset]) + int(heat[offset + 1])
                         + int(heat[offset + 2]) + int(heat[offset - height + 1])
                         + int(heat[offset + height + 1]))
                heat[offset] = (total * factor) >> 12

    @micropython.viper
    def draw(self):
        heat = ptr16(self.heat)
        colours = ptr8(self.palette)
        frame = ptr8(self.frame)
        width = int(self.xres)
        height = int(self.yres)
        stride = int(self.height)
        # Pixels are column-major, so write RGB sequentially.
        for x in range(width):
            for y in range(height):
                value = int(heat[(x + 1) * stride + y])
                if value < 1556:
                    col = 0
                elif value < 1638:
                    col = 3
                elif value < 1843:
                    col = 6
                elif value < 2048:
                    col = 9
                elif value < 2211:
                    col = 12
                elif value < 2375:
                    col = 15
                elif value < 2580:
                    col = 18
                else:
                    col = 21

                offset = (x * height + y) * 3
                frame[offset] = colours[col]
                frame[offset + 1] = colours[col + 1]
                frame[offset + 2] = colours[col + 2]
