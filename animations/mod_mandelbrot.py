from array import array
from core.colors import rainbow_palette
from core.native import micropython, ptr8, ptr16, ptr32


class Mandelbrot:
    """Follow a visible boundary using a native, overflow-safe Q26 kernel."""
    targets = (
        (-0.7436439, 0.1318259),
        (0.2745290, 0.4822550),
        (-0.1010964, 0.9562865),
        (-1.7687788, -0.0017390),
    )

    def __init__(self, xres=16, yres=16):
        self.xres = xres
        self.yres = yres
        self.target_idx = 0
        self.cx, self.cy = self.targets[0]
        self.init_w = 2.8
        self.width = self.init_w
        self.zoom_speed = 0.965
        # At 16x16 the pixel step stays well above float32 epsilon.
        self.min_width = 0.00025
        self.color_shift = 0
        self.frame = bytearray(xres * yres * 3)
        self.iterations = bytearray(xres * yres)
        self.real = array('i', bytes(xres * 4))
        self.imag = array('i', bytes(yres * 4))
        self.stats = array('H', bytes(6))
        self.palette = rainbow_palette()

    def _reset(self):
        self.target_idx = (self.target_idx + 1) % len(self.targets)
        self.cx, self.cy = self.targets[self.target_idx]
        self.width = self.init_w

    def _render(self):
        width = self.width
        height = width * self.yres / self.xres
        dx = width / self.xres
        xmin = self.cx - width * 0.5 + dx * 0.5
        ymin = self.cy - height * 0.5 + dx * 0.5
        max_iter = 24 + 8 * (width < 1.0) + 8 * (width < 0.1) + 8 * (width < 0.01)
        # Quantise each coordinate independently, avoiding accumulated step error.
        # Q26 has a 1.49e-8 step, well below the deepest 16x16 pixel spacing.
        for x in range(self.xres):
            self.real[x] = int((xmin + x * dx) * 67108864)
        for y in range(self.yres):
            self.imag[y] = int((ymin + y * dx) * 67108864)
        self._render_native(max_iter)
        return self.stats[0], self.stats[1], self.stats[2]

    @micropython.viper
    def _render_native(self, max_iter: int):
        frame = ptr8(self.frame)
        iterations = ptr8(self.iterations)
        real = ptr32(self.real)
        imag = ptr32(self.imag)
        palette = ptr8(self.palette)
        stats = ptr16(self.stats)
        width = int(self.xres)
        height = int(self.yres)
        phase = int(self.color_shift)
        lit = 0
        low = max_iter
        high = 0
        idx = 0
        for x in range(width):
            cr = int(real[x])
            for y in range(height):
                ci = int(imag[y])
                zr = 0
                zi = 0
                i = 0
                escaped = False
                while True:
                    # Check components before squaring: every product below fits
                    # signed 32 bits. A component outside [-2, 2] has escaped.
                    if zr < -134217728 or zr > 134217728 or zi < -134217728 or zi > 134217728:
                        escaped = True
                        break
                    rh = zr >> 13
                    rl = zr & 8191
                    ih = zi >> 13
                    il = zi & 8191
                    # Exact (a*b)>>26 using 13-bit limbs, without 64-bit products.
                    zr2 = rh * rh + ((2 * rh * rl + ((rl * rl) >> 13)) >> 13)
                    zi2 = ih * ih + ((2 * ih * il + ((il * il) >> 13)) >> 13)
                    if zr2 + zi2 > 268435456:
                        escaped = True
                        break
                    if i >= max_iter:
                        break
                    product = rh * ih + ((rh * il + rl * ih + ((rl * il) >> 13)) >> 13)
                    zi = 2 * product + ci
                    zr = zr2 - zi2 + cr
                    i += 1
                offset = idx * 3
                # An escape on the final iteration is still an escape.
                if escaped:
                    iterations[idx] = i
                    colour = ((i * 22 + phase) % 360) * 3
                    frame[offset] = palette[colour]
                    frame[offset + 1] = palette[colour + 1]
                    frame[offset + 2] = palette[colour + 2]
                    lit += 1
                    if i < low:
                        low = i
                    if i > high:
                        high = i
                else:
                    iterations[idx] = 0
                    frame[offset] = frame[offset + 1] = frame[offset + 2] = 0
                idx += 1
        stats[0] = lit
        stats[1] = low
        stats[2] = high

    def _follow_boundary(self):
        values = self.iterations
        height = self.yres
        best_score = 1 << 30
        best_x = best_y = 0.0
        found = False
        # Prefer a nearby lit/black edge. Work on the existing iteration buffer.
        for x in range(self.xres):
            for y in range(height):
                idx = x * height + y
                if not values[idx]:
                    continue
                edge_x = edge_y = 0
                if x + 1 < self.xres and not values[idx + height]:
                    edge_x = 1
                elif x > 0 and not values[idx - height]:
                    edge_x = -1
                elif y + 1 < height and not values[idx + 1]:
                    edge_y = 1
                elif y > 0 and not values[idx - 1]:
                    edge_y = -1
                else:
                    continue
                # Doubled coordinates locate the midpoint between the two samples.
                px = 2 * x + 1 + edge_x - self.xres
                py = 2 * y + 1 + edge_y - height
                score = px * px + py * py
                if score < best_score:
                    best_score = score
                    best_x, best_y = px, py
                    found = True
        if not found:
            # No interior sample yet: follow the slowest visible escape.
            best_iter = -1
            for x in range(self.xres):
                for y in range(height):
                    value = values[x * height + y]
                    px, py = 2 * x + 1 - self.xres, 2 * y + 1 - height
                    score = px * px + py * py
                    if value > best_iter or (value == best_iter and score < best_score):
                        best_iter, best_score = value, score
                        best_x, best_y = px, py
        step = self.width / self.xres * 0.5
        self.cx += best_x * step * 0.3
        self.cy += best_y * step * 0.3

    def get(self):
        # Bounded recovery: never spend an unlimited loop probing an empty area.
        for attempt in range(3):
            lit, low, high = self._render()
            if lit and (lit < len(self.iterations) or high > low):
                break
            if attempt == 0 and self.width < self.init_w * 0.5:
                self.width = min(self.width * 2.0, self.init_w)
            else:
                self._reset()
        self._follow_boundary()
        self.width *= self.zoom_speed
        if self.width <= self.min_width:
            self._reset()
        self.color_shift = (self.color_shift + 3) % 360
        return True, 0.0, self.frame
