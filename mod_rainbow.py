class Rainbow:
    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.counter = 0


    def get(self):
        # Generate rainbow colors
        colors = []
        for i in range(self.xres):
            hue = (i + self.counter) % 360  # Shift hue over time
            next_hue = (i + self.counter + 100) % 360  # Next hue for smooth transition
            rgb = self.hsv_to_rgb(hue, 1, 1)
            next_rgb = self.hsv_to_rgb(next_hue, 1, 1)
            colors.append([rgb, next_rgb])
        changes = []
        for x in range(self.xres):
            column = []
            for y in range(self.yres):
                # Calculate interpolated color between current and next color
                current_color = colors[x][0]
                next_color = colors[x][1]
                interp_color = self.interpolate_color(current_color, next_color, y / self.yres)
                column.append(interp_color)
            changes.append(column)
        self.counter += 1
        return True, 0.0, changes


    def hsv_to_rgb(self, h, s, v):
        h = h / 60
        s = min(1.0, s * 3.5)  # Increase saturation
        v = min(1.0, v * 1.5)  # Increase value
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


    def interpolate_color(self, color1, color2, ratio):
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        return r, g, b
