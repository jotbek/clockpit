from core.colors import rainbow_into


class Rainbow:
    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.counter = 0
        self.frame = bytearray(xres * yres * 3)
        self.next_color = bytearray(3)

    def get(self):
        frame = self.frame
        next_color = self.next_color
        height = self.yres
        for x in range(self.xres):
            offset = x * height * 3
            rainbow_into(frame, offset, x + self.counter)
            rainbow_into(next_color, 0, x + self.counter + 100)
            r, g, b = frame[offset], frame[offset + 1], frame[offset + 2]
            for y in range(1, height):
                offset += 3
                frame[offset] = (r * (height - y) + next_color[0] * y) // height
                frame[offset + 1] = (g * (height - y) + next_color[1] * y) // height
                frame[offset + 2] = (b * (height - y) + next_color[2] * y) // height
        self.counter = (self.counter + 1) % 360
        return True, 0.0, frame
