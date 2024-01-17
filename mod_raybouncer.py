import random

class Bounce:
    bouncers = []
    def __init__(self, max_x, max_y):
        bouncers = [[0, 0, 255], [255, 0, 0]]
        for b in bouncers:
            self.bouncers.append(BounceOne(max_x, max_y, 30, b))


    def get(self):
        changes = []
        for b in self.bouncers:
            changes.extend(b.get())
        return False, 0.1, changes


class BounceOne:
    boom_blast = [255, 204, 102]
    max_x, max_y = 0, 0
    map = []
    x, y = 1, 1
    step_x, step_y = 1, 1
    fading = 0
    active_rgb = []


    def __init__(self, max_x, max_y, fading, rgb):
        self.map = [[[0] * 3] * max_x for _ in range(max_y)]
        self.max_x = max_x
        self.max_y = max_y
        self.fading = fading
        self.active_rgb = rgb


    def boom(self, x, y):
        if random.randint(0, 100) >= 10: return

        self.map[max(0, x - 1)][max(0, y - 1)] = self.boom_blast
        self.map[max(0, x - 1)][y] = self.boom_blast
        self.map[max(0, x - 1)][min(self.max_y - 1, y + 1)] = self.boom_blast
        self.map[x][max(0, y - 1)] = self.boom_blast
        self.map[x][min(self.max_y - 1, y + 1)] = self.boom_blast
        self.map[min(self.max_x - 1, x + 1)][max(0, y - 1)] = self.boom_blast
        self.map[min(self.max_x - 1, x + 1)][y] = self.boom_blast
        self.map[min(self.max_x - 1, x + 1)][min(self.max_y - 1, y + 1)] = self.boom_blast


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