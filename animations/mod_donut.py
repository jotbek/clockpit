"""A shaded 3D torus, projected onto the LED matrix with a depth buffer."""
import math
from array import array

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


class Donut:
    def __init__(self, xres, yres, delay=0.0, speed=0.04):
        self.xres = xres
        self.yres = yres
        self.delay = delay
        self.speed = speed
        self.angle_x = 0.6
        self.angle_y = 0.3
        self.scale = int(min(xres, yres) * 0.85 * 1024)
        self.frame = bytearray(xres * yres * 3)
        self.depth = array('H', bytes(xres * yres * 2))
        self.rotation = array('h', bytes(18))
        # Q12 geometry fits signed 16-bit tables; no floats in the point loop.
        self.ring = array('h')
        self.tube = array('h')
        # Projection reciprocal at 1/32-unit depth steps, covering camera z=3..9.
        self.reciprocal = array('H')
        for i in range(192):
            self.reciprocal.append(self.scale * 4096 // ((i + 96) * 128 + 64))
        for i in range(48):
            angle = i * 2 * math.pi / 48
            self.ring.append(int(math.cos(angle) * 4096))
            self.ring.append(int(math.sin(angle) * 4096))
        for i in range(24):
            angle = i * 2 * math.pi / 24
            cosine, sine = math.cos(angle), math.sin(angle)
            self.tube.append(int((2.0 + 0.6 * cosine) * 4096))
            self.tube.append(int(0.6 * sine * 4096))
            self.tube.append(int(cosine * 4096))
            self.tube.append(int(sine * 4096))

    def get(self):
        sin_a, cos_a = math.sin(self.angle_x), math.cos(self.angle_x)
        sin_b, cos_b = math.sin(self.angle_y), math.cos(self.angle_y)
        rotation = self.rotation
        rotation[0] = int(cos_b * 4096)
        rotation[1] = int(sin_a * sin_b * 4096)
        rotation[2] = int(cos_a * sin_b * 4096)
        rotation[3] = 0
        rotation[4] = int(cos_a * 4096)
        rotation[5] = int(-sin_a * 4096)
        rotation[6] = int(-sin_b * 4096)
        rotation[7] = int(sin_a * cos_b * 4096)
        rotation[8] = int(cos_a * cos_b * 4096)
        self._render()
        self.angle_x = (self.angle_x + self.speed) % (2 * math.pi)
        self.angle_y = (self.angle_y + self.speed * 0.65) % (2 * math.pi)
        return True, self.delay, self.frame

    @micropython.viper
    def _render(self):
        frame = ptr8(self.frame)
        depth = ptr16(self.depth)
        ring = ptr16(self.ring)
        tube = ptr16(self.tube)
        rotation = ptr16(self.rotation)
        reciprocal = ptr16(self.reciprocal)
        width = int(self.xres)
        height = int(self.yres)
        size = width * height
        ring_length = int(len(self.ring))
        tube_length = int(len(self.tube))
        for i in range(size):
            depth[i] = 0
            frame[i * 3] = 0

        # ptr16 reads unsigned words; restore the sign of each Q12 coefficient.
        xx = (int(rotation[0]) ^ 32768) - 32768
        xy = (int(rotation[1]) ^ 32768) - 32768
        tube_x = (int(rotation[2]) ^ 32768) - 32768
        yy = (int(rotation[4]) ^ 32768) - 32768
        tube_y = (int(rotation[5]) ^ 32768) - 32768
        zx = (int(rotation[6]) ^ 32768) - 32768
        zy = (int(rotation[7]) ^ 32768) - 32768
        tube_z = (int(rotation[8]) ^ 32768) - 32768
        # Fixed light above and to the left of the camera; rotate normals too.
        tube_light = (-1433 * tube_x + 1843 * tube_y - 3358 * tube_z) >> 12
        center_x = width << 9
        center_y = height << 9
        for i in range(0, ring_length, 2):
            cosine = (int(ring[i]) ^ 32768) - 32768
            sine = (int(ring[i + 1]) ^ 32768) - 32768
            ring_x = (cosine * xx + sine * xy) >> 12
            ring_y = (sine * yy) >> 12
            ring_z = (cosine * zx + sine * zy) >> 12
            ring_light = (-1433 * ring_x + 1843 * ring_y - 3358 * ring_z) >> 12
            for j in range(0, tube_length, 4):
                normal_cos = (int(tube[j + 2]) ^ 32768) - 32768
                normal_sin = (int(tube[j + 3]) ^ 32768) - 32768
                normal_z = (normal_cos * ring_z + normal_sin * tube_z) >> 12
                # Dot(normal, point - camera): back-facing samples are hidden.
                if 2 * normal_cos + 2458 + 6 * normal_z >= 0:
                    continue
                radius = int(tube[j])
                tube_height = (int(tube[j + 1]) ^ 32768) - 32768
                x = (radius * ring_x + tube_height * tube_x) >> 12
                y = (radius * ring_y + tube_height * tube_y) >> 12
                z = 24576 + ((radius * ring_z + tube_height * tube_z) >> 12)
                projection = int(reciprocal[(z >> 7) - 96])
                px = (center_x + ((x * projection) >> 12)) >> 10
                py = (center_y - ((y * projection) >> 12)) >> 10
                if not (0 <= px < width and 0 <= py < height):
                    continue
                pixel = px * height + py
                distance = 65535 - z
                if distance < int(depth[pixel]):
                    continue
                light = (normal_cos * ring_light + normal_sin * tube_light) >> 12
                shade = 24 + ((231 * light) >> 12) if light > 0 else 24
                if shade > 255:
                    shade = 255
                offset = pixel * 3
                # Resolve equal quantized depths consistently in either draw order.
                if distance == int(depth[pixel]) and shade <= int(frame[offset]):
                    continue
                depth[pixel] = distance
                frame[offset] = shade

        # Shade each pixel once; expand grayscale to RGB after depth resolution.
        for offset in range(0, size * 3, 3):
            frame[offset + 1] = frame[offset + 2] = frame[offset]
