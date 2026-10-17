"""Smooth rising flames, a warm ember bed and sparse subpixel sparks."""
from array import array
import math
import random
from core.native import micropython, ptr8, ptr16


class Fireplace:
    # Heat -> RGB anchors, interpolated once into a 256-entry palette.
    colours = ((0, (0, 0, 0)), (24, (12, 0, 0)), (64, (100, 5, 0)),
               (112, (230, 38, 0)), (160, (255, 110, 2)),
               (208, (255, 190, 35)), (240, (255, 230, 110)),
               (255, (255, 248, 170)))
    spark_fq = 24

    def __init__(self, xres, yres, delay=0.02):
        if xres < 1 or not 1 <= yres <= 255:
            raise ValueError('Fireplace needs positive width and height in 1..255')
        self.xres = xres
        self.yres = yres
        self.delay = delay
        self.phase = 0
        self.frame = bytearray(xres * yres)
        self.next_heat = bytearray(xres * yres)
        self.frame_rgb = bytearray(xres * yres * 3)
        self.palette = bytearray(256 * 3)
        for index in range(len(self.colours) - 1):
            start, a = self.colours[index]
            end, b = self.colours[index + 1]
            for heat in range(start, end + 1):
                for channel in range(3):
                    self.palette[heat * 3 + channel] = (
                        a[channel] * (end - heat) + b[channel] * (heat - start)) // (end - start)
        self.fuel = bytearray(xres)
        self.target_fuel = bytearray(xres)
        self.burners = bytearray((200, 255, 180, 230))
        self.profile = bytearray(xres)
        self.cooling = bytearray(yres)
        for x in range(xres):
            distance = abs(2 * x + 1 - xres) * 256 // xres
            self.profile[x] = min(255, (256 - distance) * 4)
            self.fuel[x] = random.randint(140, 255)
            self.target_fuel[x] = self.fuel[x]
        for y in range(yres):
            self.cooling[y] = 8 + (yres - 1 - y) * 10 // yres
        self.wind = bytearray(128 + int(80 * math.sin(i * 2 * math.pi / 64)) for i in range(64))
        # Four bounded particles: integer columns, Q8 vertical position, heat.
        self.spark_x = array('H', bytes(8))
        self.spark_y = array('H', bytes(8))
        self.spark_velocity = bytearray(4)
        self.spark_heat = bytearray(4)
        # Start with an ember bed rather than an entirely empty first frame.
        for x in range(xres):
            self.frame[x * yres + yres - 1] = self.fuel[x] * self.profile[x] >> 8

    def get(self):
        self.ignite()
        self._propagate()
        self.frame, self.next_heat = self.next_heat, self.frame
        self._update_sparks()
        self._draw()
        self.phase = (self.phase + 1) & 255
        return True, self.delay, self.frame_rgb

    def ignite(self):
        # Random targets evolve slowly; there is no per-pixel white-noise field.
        if self.phase & 15 == 0:
            for i in range(4):
                self.burners[i] = random.randint(50, 235)
            self.burners[random.randrange(4)] = 255
            for x in range(self.xres):
                position = x * 3 * 256 // max(1, self.xres - 1)
                segment = min(2, position >> 8)
                fraction = position - segment * 256
                self.target_fuel[x] = (
                    self.burners[segment] * (256 - fraction)
                    + self.burners[segment + 1] * fraction) >> 8
        for x in range(self.xres):
            delta = self.target_fuel[x] - self.fuel[x]
            self.fuel[x] += max(-6, min(6, delta))

    @micropython.viper
    def _propagate(self):
        old = ptr8(self.frame)
        new = ptr8(self.next_heat)
        fuel = ptr8(self.fuel)
        profile = ptr8(self.profile)
        cooling = ptr8(self.cooling)
        wind = ptr8(self.wind)
        width = int(self.xres)
        height = int(self.yres)
        phase = int(self.phase)
        for x in range(width):
            left = x - 1 if x > 0 else x
            right = x + 1 if x + 1 < width else x
            for y in range(height - 1):
                offset = x * height + y
                below = y + 1
                flow = int(wind[(phase + y * 3) & 63]) - 128
                neighbour = right
                if flow < 0:
                    neighbour = left
                    flow = -flow
                rising = (int(old[x * height + below]) * (256 - flow)
                          + int(old[neighbour * height + below]) * flow) >> 8
                mixed = (rising * 6 + int(old[left * height + below])
                         + int(old[right * height + below])) >> 3
                value = mixed - int(cooling[y]) - ((255 - int(profile[x])) >> 5)
                if value < 0:
                    value = 0
                # Fractional rise blends the advected heat with the previous cell.
                new[offset] = (int(old[offset]) + value * 3) >> 2
            heat = (int(fuel[left]) + 6 * int(fuel[x]) + int(fuel[right])) >> 3
            new[x * height + height - 1] = (heat * int(profile[x])) >> 8

    def _update_sparks(self):
        for i in range(4):
            if self.spark_heat[i]:
                position = self.spark_y[i] - self.spark_velocity[i]
                strength = self.spark_heat[i] - 5
                if position < 0 or strength <= 0:
                    self.spark_heat[i] = 0
                    self.spark_y[i] = 0
                else:
                    self.spark_y[i] = position
                    self.spark_heat[i] = strength
        if self.yres < 3 or random.randrange(self.spark_fq) != 0:
            return
        for i in range(4):
            if self.spark_heat[i] == 0:
                self.spark_x[i] = random.randrange(self.xres)
                self.spark_y[i] = (self.yres - 2) << 8
                self.spark_velocity[i] = random.randint(80, 160)
                self.spark_heat[i] = random.randint(170, 240)
                break

    @micropython.viper
    def _draw(self):
        heat = ptr8(self.frame)
        out = ptr8(self.frame_rgb)
        palette = ptr8(self.palette)
        width = int(self.xres)
        height = int(self.yres)
        for x in range(width):
            left = x - 1 if x > 0 else x
            right = x + 1 if x + 1 < width else x
            for y in range(height):
                above = y - 1 if y > 0 else y
                below = y + 1 if y + 1 < height else y
                # Symmetric heat blur fills holes without desaturating flame colours.
                value = (4 * int(heat[x * height + y])
                         + int(heat[left * height + y]) + int(heat[right * height + y])
                         + int(heat[x * height + above]) + int(heat[x * height + below])) >> 3
                colour = value * 3
                offset = (x * height + y) * 3
                for channel in range(3):
                    # Half-frame persistence reduces flicker and softens moving tips.
                    out[offset + channel] = (int(out[offset + channel])
                                             + int(palette[colour + channel]) + 1) >> 1
        sx = ptr16(self.spark_x)
        sy = ptr16(self.spark_y)
        strength = ptr8(self.spark_heat)
        for i in range(4):
            power = int(strength[i])
            if power == 0:
                continue
            x = int(sx[i])
            position = int(sy[i])
            row = position >> 8
            fraction = position & 255
            for part in range(2):
                y = row + part
                if not (0 <= x < width and 0 <= y < height):
                    continue
                weight = fraction if part else 256 - fraction
                glow = (power * weight) >> 8
                offset = (x * height + y) * 3
                for channel in range(3):
                    addition = glow
                    if channel == 1:
                        addition = (glow * 3) >> 2
                    elif channel == 2:
                        addition = glow >> 2
                    value = int(out[offset + channel]) + addition
                    out[offset + channel] = 255 if value > 255 else value
