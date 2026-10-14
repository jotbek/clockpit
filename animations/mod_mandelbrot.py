from core.colors import rainbow_into


class Mandelbrot:
    """Follow a visible escape-time boundary, within RP2040 float precision."""
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
        frame, iterations = self.frame, self.iterations
        lit = 0
        low, high = max_iter, 0
        idx = 0
        for x in range(self.xres):
            cr = xmin + x * dx
            cr_off = cr - 0.25
            cr_off2 = cr_off * cr_off
            cr_plus1_2 = (cr + 1.0) * (cr + 1.0)
            for y in range(self.yres):
                ci = ymin + y * dx
                ci2 = ci * ci
                q = cr_off2 + ci2
                i = max_iter
                escaped = False
                if not (q * (q + cr_off) <= 0.25 * ci2 or cr_plus1_2 + ci2 <= 0.0625):
                    zr = zi = zr2 = zi2 = 0.0
                    i = 0
                    while zr2 + zi2 <= 4.0 and i < max_iter:
                        zi = 2.0 * zr * zi + ci
                        zr = zr2 - zi2 + cr
                        zr2 = zr * zr
                        zi2 = zi * zi
                        i += 1
                    escaped = zr2 + zi2 > 4.0
                offset = idx * 3
                # An escape on the final iteration is still an escape.
                if escaped:
                    iterations[idx] = i
                    rainbow_into(frame, offset, i * 22 + self.color_shift)
                    lit += 1
                    low = min(low, i)
                    high = max(high, i)
                else:
                    iterations[idx] = 0
                    frame[offset] = frame[offset + 1] = frame[offset + 2] = 0
                idx += 1
        return lit, low, high

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
