import random
import helpers

class Bounce:
    def __init__(self, max_x, max_y):
        self.bouncers = []
        colors = [helpers.colors_rgb['red'], helpers.colors_rgb['blue']]
        for color in colors:
            self.bouncers.append(BounceOne(max_x, max_y, 30, color))

    def get(self):
        changes = []
        for b in self.bouncers:
            changes.extend(b.get())
        return False, 0.1, changes

class BounceOne:
    def __init__(self, max_x, max_y, fading, rgb):
        self.boom_blast = [255, 204, 102]
        self.max_x = max_x
        self.max_y = max_y
        # Correctly initialize the map to avoid shared references
        self.map = [[[0, 0, 0] for _ in range(max_y)] for _ in range(max_x)]
        self.x, self.y = 1, 1
        self.step_x, self.step_y = 1, 1
        self.fading = fading
        self.active_rgb = rgb

    def boom(self, x, y):
        if random.randint(0, 100) >= 10:
            return

        # Use .copy() to prevent shared references
        self.map[max(0, x - 1)][max(0, y - 1)] = self.boom_blast.copy()
        self.map[max(0, x - 1)][y] = self.boom_blast.copy()
        self.map[max(0, x - 1)][min(self.max_y - 1, y + 1)] = self.boom_blast.copy()
        self.map[x][max(0, y - 1)] = self.boom_blast.copy()
        self.map[x][min(self.max_y - 1, y + 1)] = self.boom_blast.copy()
        self.map[min(self.max_x - 1, x + 1)][max(0, y - 1)] = self.boom_blast.copy()
        self.map[min(self.max_x - 1, x + 1)][y] = self.boom_blast.copy()
        self.map[min(self.max_x - 1, x + 1)][min(self.max_y - 1, y + 1)] = self.boom_blast.copy()

    def get(self):
        changes = []

        if self.x + self.step_x > self.max_x - 1:
            self.step_x = -random.randint(1, 2)
            self.boom(self.x, self.y)
        elif self.x + self.step_x < 0:
            self.step_x = random.randint(1, 2)
            self.boom(self.x, self.y)

        if self.y == self.max_y - 1 or self.y == 0:
            self.step_y *= -1
            self.boom(self.x, self.y)

        for iy in range(self.max_y):
            for ix in range(self.max_x):
                if self.map[ix][iy] != [0, 0, 0]:
                    self.map[ix][iy] = [max(0, self.map[ix][iy][0] - self.fading), max(0, self.map[ix][iy][1] - self.fading), max(0, self.map[ix][iy][2] - self.fading)]
                    changes.append((ix, iy, self.map[ix][iy]))

        self.x += self.step_x
        self.y += self.step_y

        self.map[self.x][self.y] = self.active_rgb
        changes.append((self.x, self.y, self.active_rgb))

        return changes
