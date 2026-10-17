"""A local-time sky: east-to-west sun, twilight, crescent moon and stars."""
import time
from core.localtime import local_seconds


class DayCycle:
    # Fixed local hours, not astronomical sunrise/sunset (no location required).
    SUNRISE = 6 * 3600
    SUNSET = 18 * 3600
    # Seconds, zenith RGB, horizon RGB, foreground RGB. Midnight closes the loop.
    SKY = (
        (0, (2, 3, 16), (13, 12, 34), (1, 3, 5)),
        (5 * 3600, (8, 7, 30), (42, 23, 50), (3, 5, 9)),
        (6 * 3600, (49, 29, 91), (239, 98, 47), (13, 15, 18)),
        (8 * 3600, (18, 87, 174), (127, 180, 197), (15, 35, 28)),
        (12 * 3600, (14, 106, 204), (114, 192, 225), (16, 43, 30)),
        (16 * 3600, (32, 84, 167), (178, 166, 157), (19, 32, 26)),
        (18 * 3600, (61, 23, 82), (245, 88, 37), (15, 13, 18)),
        (19 * 3600, (15, 8, 38), (80, 30, 61), (5, 5, 10)),
        (20 * 3600, (3, 4, 19), (19, 13, 39), (1, 3, 5)),
        (24 * 3600, (2, 3, 16), (13, 12, 34), (1, 3, 5)),
    )
    STARS = ((1, 2), (5, 1), (10, 2), (14, 1), (3, 5), (8, 4),
             (13, 6), (1, 8), (6, 7), (11, 9))

    def __init__(self, xres, yres):
        if xres < 1 or yres < 1:
            raise ValueError('resolution must be positive')
        if not 0 <= self.SUNRISE < self.SUNSET < 86400:
            raise ValueError('expected 0 <= SUNRISE < SUNSET < 86400')
        self.xres, self.yres = xres, yres
        self.frame = bytearray(xres * yres * 3)
        self.last_second = -1
        # Retain only one frame plus a small, static landscape silhouette.
        self.ridge = bytearray(xres)
        for x in range(xres):
            hill = abs(x * 30 // max(1, xres - 1) - 10)
            self.ridge[x] = min(yres - 1, max(0, yres * 13 // 16 + hill // 9))

    def _sky(self, second):
        for i in range(1, len(self.SKY)):
            right = self.SKY[i]
            if second < right[0]:
                left = self.SKY[i - 1]
                mix = (second - left[0]) * 256 // (right[0] - left[0])
                return tuple(left[group][c] + (right[group][c] - left[group][c]) * mix // 256
                             for group in range(1, 4) for c in range(3))

    def _position(self, second):
        day = self.SUNRISE <= second < self.SUNSET
        if day:
            elapsed, duration = second - self.SUNRISE, self.SUNSET - self.SUNRISE
        else:
            elapsed = (second - self.SUNSET) % 86400
            duration = 86400 - (self.SUNSET - self.SUNRISE)
        # Q8 pixel coordinates and a bounded parabolic arc, no RTC floats.
        progress = elapsed * 1024 // duration
        arc = progress * (1024 - progress) // 256
        cx = (self.xres - 1) * 256 * progress // 1024
        horizon = (self.yres - 1) * 218
        cy = horizon - (self.yres - 1) * 175 * arc // 1024
        fade = min(255, elapsed * 255 // 1200, (duration - elapsed) * 255 // 1200)
        return day, cx, cy, fade

    def _render(self, second):
        day, cx, cy, fade = self._position(second)
        # Stretch the colour cycle along with configurable sunrise/sunset hours.
        daylight = self.SUNSET - self.SUNRISE
        sky_second = (21600 + (second - self.SUNRISE) * 43200 // daylight) if day else (
            (64800 + (second - self.SUNSET) % 86400 * 43200 // (86400 - daylight)) % 86400)
        sky = self._sky(sky_second)
        height = max(1, self.yres - 1)
        radius = max(128, min(self.xres, self.yres) * 26)
        inner2 = (radius - 100) ** 2
        outer2 = (radius + 100) ** 2
        halo2 = (radius * 3) ** 2
        # Stars fade through an hour of twilight, independently of the body.
        night = 0 if day else min(255, (self.SUNRISE - second if second < self.SUNRISE
                                      else second - self.SUNSET) * 255 // 3600)
        warm = max(0, 255 - min(abs(second - self.SUNRISE), abs(second - self.SUNSET)) * 255 // 7200)
        body = (255, 238 - warm // 3, 162 - warm // 2) if day else (205, 221, 239)
        frame = self.frame
        for x in range(self.xres):
            dx = x * 256 - cx
            for y in range(self.yres):
                offset = (x * self.yres + y) * 3
                if y >= self.ridge[x]:
                    # A second, darker hill adds depth at the bottom.
                    shade = 180 if y > self.ridge[x] else 256
                    for c in range(3):
                        frame[offset + c] = sky[6 + c] * shade // 256
                    continue
                dy = y * 256 - cy
                distance = dx * dx + dy * dy
                halo = max(0, halo2 - distance) * fade // halo2
                cover = max(0, min(255, (outer2 - distance) * 255 // (outer2 - inner2)))
                if not day:
                    # Offset cutout turns the softly sampled disc into a crescent.
                    cut = (dx - radius * 3 // 5) ** 2 + (dy + radius // 4) ** 2
                    cut_cover = max(0, min(255, (outer2 - cut) * 255 // (outer2 - inner2)))
                    cover = max(0, cover - cut_cover)
                cover = cover * fade // 255
                for c in range(3):
                    value = sky[c] + (sky[3 + c] - sky[c]) * y // height
                    glow = (32, 19, 5)[c] if day else (5, 7, 14)[c]
                    value = min(255, value + glow * halo // 255)
                    frame[offset + c] = value + (body[c] - value) * cover // 255
        if night:
            for i in range(len(self.STARS)):
                sx, sy = self.STARS[i]
                x, y = sx * (self.xres - 1) // 15, sy * height // 15
                if y >= self.ridge[x]:
                    continue
                dx, dy = x * 256 - cx, y * 256 - cy
                if dx * dx + dy * dy < outer2:
                    continue
                twinkle = abs((second + i * 11) % 48 - 24)
                light = (48 + twinkle * 3) * night // 255
                offset = (x * self.yres + y) * 3
                for c in range(3):
                    frame[offset + c] = min(255, frame[offset + c] + light)

    def get(self):
        second = local_seconds(time.localtime())
        if second != self.last_second:
            self._render(second)
            self.last_second = second
        return True, 0.25, self.frame
