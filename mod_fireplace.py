import random


class Fireplace:
    xres = 0
    yres = 0

    min_ignite = 3
    max_ignite = 13

    frame = []

    black_rgb = [0, 0, 0]
    white_rgb = [255, 255, 255]
    colors_arr = [
        white_rgb,
        [255, 255, 204],
#        [255, 250, 180],
#        [255, 240, 150],
#        [252, 230, 120],
        [252, 220, 90],
        [252, 210, 60],
        [252, 200, 30],
        [252, 190, 20],
        [252, 180, 10],
        [252, 170, 5],
        [252, 160, 3],
        [252, 150, 3],
        [255, 120, 3],
        [252, 100, 3],
        [204, 80, 3],
        [204, 0, 3],
        [150, 60, 0],
        [120, 30, 0],
        [90, 20, 0],
        [140, 0, 0],
        [120, 0, 0],
        [100, 0, 0],
        [80, 0, 0],
        [60, 0, 0],
        [40, 0, 0],
        [25, 0, 0],
        [10, 3, 0],
        black_rgb   
    ]

    colors_dict = {}


    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres

        i = 0
        for col in self.colors_arr:
            self.colors_dict[len(self.colors_arr) - i - 1] = col
            i += 1

        self.frame = [[0 for x in range(self.xres)] for y in range(self.yres)]

    
    def get(self):
        self.ignite()
        self.animate()

        return True, 0.0, self.translate2rgb()

    
    def animate(self):
        for y in range(self.yres):
            for x in range(self.xres):
                x_direction = random.randint(-1, 1)
                x_horiz = random.randint(0, 2) * x_direction
                y_up = 1 #random.randint(1, 2)
                
                color = min(self.frame[x][y], self.frame[x][y] - random.randint(1, 2))
                if self.frame[max(x - 1, 0)][y] == 0 or x - 1 < 3:
                    color = max(color - 2, 0)

                if (self.frame[min(x + 1, self.xres - 1)]) == 0 or x + 1 > self.xres - 4:
                    color = max(color - 2, 0)    
                self.light(x, y, x + x_direction, y - y_up, color)


    def translate2rgb(self):
        frame = [[[0, 0, 0] for x in range(self.xres)] for y in range(self.yres)]
        for y in range(self.yres):
            for x in range(self.xres):
                frame[x][y] = self.colors_dict[self.frame[x][y]]
        
        return frame


    def light(self, x, y, x_new, y_new, color):
        if y_new >= 0 and y_new < self.yres:
            if x_new >= 0 and x_new < self.xres :
                self.frame[x_new][y_new] = max(color, 0)
        
        # replace old pixel            
        self.frame[x][y] = max(self.frame[x][y] - 1, 0)


    def ignite(self):
        for x in range(self.min_ignite, self.max_ignite):
            self.frame[x][self.yres - 1] = len(self.colors_dict) - 1