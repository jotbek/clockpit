import random
from core import helpers
from array import array


class Bounce:
    def __init__(self, max_x, max_y):
        self.bouncers = [BounceOne(max_x, max_y, 30, helpers.colors_rgb['red']),
                         BounceOne(max_x, max_y, 30, helpers.colors_rgb['blue'])]

    def get(self):
        changes = []
        for bouncer in self.bouncers:
            bouncer.get_into(changes)
        return False, 0.1, changes


class BounceOne:
    boom_blast = (255, 204, 102)

    def __init__(self, max_x, max_y, fading, rgb):
        self.max_x = max_x
        self.max_y = max_y
        self.map = bytearray(max_x * max_y * 3)
        # Bounded active-pixel list: fade trails instead of scanning all 256 LEDs.
        self.active = array('H', bytes(max_x * max_y * 2))
        self.active_count = 0
        self.x, self.y = 1, 1
        self.step_x, self.step_y = 1, 1
        self.fading = fading
        self.active_rgb = rgb

    def _set(self, x, y, color):
        offset = (x * self.max_y + y) * 3
        if not (self.map[offset] or self.map[offset + 1] or self.map[offset + 2]):
            self.active[self.active_count] = offset // 3
            self.active_count += 1
        self.map[offset] = color[0]
        self.map[offset + 1] = color[1]
        self.map[offset + 2] = color[2]

    def boom(self, x, y):
        if random.randint(0, 100) >= 10:
            return
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if dx or dy:
                    self._set(max(0, min(self.max_x - 1, x + dx)),
                              max(0, min(self.max_y - 1, y + dy)), self.boom_blast)

    def get_into(self, changes):
        if self.x + self.step_x > self.max_x - 1:
            self.step_x = -random.randint(1, 2)
            self.boom(self.x, self.y)
        elif self.x + self.step_x < 0:
            self.step_x = random.randint(1, 2)
            self.boom(self.x, self.y)
        if self.y == self.max_y - 1 or self.y == 0:
            self.step_y *= -1
            self.boom(self.x, self.y)
        frame = self.map
        height = self.max_y
        # Only emit changed trail pixels, including their final transition to black.
        remaining = 0
        active = self.active
        for index in range(self.active_count):
            pixel = active[index]
            i = pixel * 3
            r, g, b = frame[i], frame[i + 1], frame[i + 2]
            r, g, b = max(0, r - self.fading), max(0, g - self.fading), max(0, b - self.fading)
            frame[i], frame[i + 1], frame[i + 2] = r, g, b
            changes.append((pixel // height, pixel % height, (r, g, b)))
            if r or g or b:
                active[remaining] = pixel
                remaining += 1
        self.active_count = remaining
        self.x += self.step_x
        self.y += self.step_y
        self._set(self.x, self.y, self.active_rgb)
        changes.append((self.x, self.y, self.active_rgb))
