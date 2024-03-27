import math


class ColorVortex:
    def __init__(self, xres, yres, speed=0.05):
        self.xres = xres
        self.yres = yres
        self.radius = min(xres, yres) // 2
        self.center_x = xres // 2
        self.center_y = yres // 2
        self.angle = 0
        self.speed = speed  # Initialize speed parameter


    def get(self):
        changes = []
        # Generate vortex animation
        for x in range(self.xres):
            for y in range(self.yres):
                distance = math.sqrt((x - self.center_x) ** 2 + (y - self.center_y) ** 2)
                if distance < self.radius:
                    angle_offset = math.atan2(y - self.center_y, x - self.center_x)
                    angle_offset += self.angle
                    color_offset = int((angle_offset * 180 / math.pi) % 360)
                    rgb = self.hsv_to_rgb(color_offset, 1, 1)
                    changes.append([x, y, rgb])
                else:
                    changes.append([x, y, [0, 0, 0]])  # Black for background
        # Update angle for next frame
        self.angle += self.speed
        return False, 0.0, changes  # Full frame changes
    

    def hsv_to_rgb(self, h, s, v):
        h = h / 60
        s = s
        v = v
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
