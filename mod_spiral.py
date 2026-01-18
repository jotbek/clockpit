class Spiral:
    def __init__(self, xres, yres, delay=0.01):
        self.xres = xres
        self.yres = yres
        self.path = self._compute_spiral_path(xres, yres)
        self.index = 0
        self.delay = delay
        self.hue = 0

    def _compute_spiral_path(self, w, h):
        # Generate coordinates following a clockwise spiral from outer frame to center
        left, top = 0, 0
        right, bottom = w - 1, h - 1
        path = []
        while left <= right and top <= bottom:
            # top row (left->right)
            for x in range(left, right + 1):
                path.append((x, top))
            # right column (top+1->bottom)
            for y in range(top + 1, bottom + 1):
                path.append((right, y))
            if top < bottom:
                # bottom row (right-1->left)
                for x in range(right - 1, left - 1, -1):
                    path.append((x, bottom))
            if left < right:
                # left column (bottom-1->top+1)
                for y in range(bottom - 1, top, -1):
                    path.append((left, y))
            left += 1
            right -= 1
            top += 1
            bottom -= 1
        return path

    def get(self):
        # Return a single pixel update following spiral path
        if not self.path:
            return False, self.delay, []

        x, y = self.path[self.index]
        # Use limited hue range (warm tones and magenta) to avoid blue/green
        raw = self.hue % 120
        if raw < 60:
            hue = (raw * (60.0 / 60.0))  # map 0..59 -> 0..59 (reds->yellows)
        else:
            hue = 300 + ((raw - 60) * (60.0 / 60.0))  # map 60..119 -> 300..359 (magenta)

        # Slightly reduced saturation and value to make colors darker/subtler
        rgb = self.hsv_to_rgb(hue, 0.9, 0.6)

        # Move to next pixel and hue
        self.index = (self.index + 1) % len(self.path)
        self.hue = (self.hue + 1) % 120

        # Do not clear the frame; return a single pixel change to be added/overwritten
        return False, self.delay, [[x, y, rgb]]

    def hsv_to_rgb(self, h, s, v):
        # Same conversion used in other modules
        h = h / 60.0
        hi = int(h) % 6
        f = h - int(h)
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        if hi == 0:
            return [int(v * 255), int(t * 255), int(p * 255)]
        elif hi == 1:
            return [int(q * 255), int(v * 255), int(p * 255)]
        elif hi == 2:
            return [int(p * 255), int(v * 255), int(t * 255)]
        elif hi == 3:
            return [int(p * 255), int(q * 255), int(v * 255)]
        elif hi == 4:
            return [int(t * 255), int(p * 255), int(v * 255)]
        else:
            return [int(v * 255), int(p * 255), int(q * 255)]
