class MatrixDisplay:
    """Keep a bounded unscaled base so brightness changes preserve sparse pixels."""

    def __init__(self, pixels, xres, yres):
        if pixels.bpp != 3:
            raise ValueError('Clockpit requires RGB NeoPixels')
        self.pixels = pixels
        self.buf = pixels.buf
        self.base = bytearray(len(self.buf))
        self.xres = xres
        self.yres = yres
        self.red, self.green, self.blue = pixels.ORDER[:3]
        self.overlay_backup = None

    def map_pixel(self, x, y):
        return y * self.xres + (x if y & 1 else self.xres - 1 - x)

    def light(self, x, y, r, g, b, brightness, remember=True):
        if not (0 <= x < self.xres and 0 <= y < self.yres):
            return
        offset = self.map_pixel(x, y) * 3
        buf = self.buf
        if remember:
            self.base[offset + self.red] = r
            self.base[offset + self.green] = g
            self.base[offset + self.blue] = b
        buf[offset + self.red] = r * brightness // 255
        buf[offset + self.green] = g * brightness // 255
        buf[offset + self.blue] = b * brightness // 255

    def clear(self):
        buf = self.buf
        for i in range(len(buf)):
            buf[i] = 0
            self.base[i] = 0

    def set_brightness(self, brightness):
        for i in range(len(self.buf)):
            self.buf[i] = self.base[i] * brightness // 255

    def apply(self, full_frame, changes, brightness):
        if not full_frame:
            for x, y, color in changes:
                self.light(x, y, color[0], color[1], color[2], brightness)
            return bool(changes)
        buf = self.buf
        red, green, blue = self.red, self.green, self.blue
        width, height = self.xres, self.yres
        packed = isinstance(changes, (bytes, bytearray))
        for y in range(height):
            target = (y * width + (0 if y & 1 else width - 1)) * 3
            step = 3 if y & 1 else -3
            source = y * 3
            for x in range(width):
                if packed:
                    r, g, b = changes[source], changes[source + 1], changes[source + 2]
                    source += height * 3
                else:
                    r, g, b = changes[x][y]
                buf[target + red] = r * brightness // 255
                buf[target + green] = g * brightness // 255
                buf[target + blue] = b * brightness // 255
                self.base[target + red] = r
                self.base[target + green] = g
                self.base[target + blue] = b
                target += step
        return True

    def show_overlay(self, clock_frame, brightness):
        # The clock lights at most 60 border + 60 digit pixels. Save only these.
        if self.overlay_backup is None:
            self.overlay_backup = bytearray(120 * 3)
        backup, buf = self.overlay_backup, self.buf
        saved = 0
        height = self.yres
        for i in range(0, len(clock_frame), 3):
            r, g, b = clock_frame[i], clock_frame[i + 1], clock_frame[i + 2]
            if r or g or b:
                pixel = i // 3
                x, y = pixel // height, pixel % height
                offset = self.map_pixel(x, y) * 3
                backup[saved] = buf[offset]
                backup[saved + 1] = buf[offset + 1]
                backup[saved + 2] = buf[offset + 2]
                saved += 3
                self.light(x, y, r, g, b, brightness, remember=False)
        try:
            self.pixels.write()
        finally:
            # Keep the base image intact for modules that only emit deltas.
            saved = 0
            for i in range(0, len(clock_frame), 3):
                if clock_frame[i] or clock_frame[i + 1] or clock_frame[i + 2]:
                    pixel = i // 3
                    offset = self.map_pixel(pixel // height, pixel % height) * 3
                    buf[offset] = backup[saved]
                    buf[offset + 1] = backup[saved + 1]
                    buf[offset + 2] = backup[saved + 2]
                    saved += 3
