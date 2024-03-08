import random
import time

class GameOfLife:
    xres = 0
    yres = 0
    grid = []
    time_max_s = 20
    timestamp = time.time()
    
    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.init()


    def init(self):
        self.grid = [[random.randint(0, 1) for _ in range(self.xres)] for _ in range(self.yres)]
        self.frame = [[[0, 0, 0] for _ in range(self.xres)] for _ in range(self.yres)]                    


    def get_neighbours(self, x, y):
        neighbours = []
        for i in range(-1, 2):
            for j in range(-1, 2):
                if i == 0 and j == 0:
                    continue
                neighbour_x = x + i
                neighbour_y = y + j
                if 0 <= neighbour_x < self.xres and 0 <= neighbour_y < self.yres:
                    neighbours.append(self.grid[neighbour_y][neighbour_x])
        return neighbours


    def update(self):
        new_grid = [[0 for _ in range(self.xres)] for _ in range(self.yres)]
        for y in range(self.yres):
            for x in range(self.xres):
                neighbours = self.get_neighbours(x, y)
                live_neighbours = sum(neighbours)
                # Zasady gry w życie
                if self.grid[y][x] == 1 and (live_neighbours < 2 or live_neighbours > 3):
                    new_grid[y][x] = 0
                elif self.grid[y][x] == 0 and live_neighbours == 3:
                    new_grid[y][x] = 1
                else:
                    new_grid[y][x] = self.grid[y][x]
        self.grid = new_grid


    c_delta = 5
    c_max = 128
    def phase_colors(self, col, delta):
        result_delta = delta 
        result_c = col
        if random.randint(0, 100) < 5:
            if random.randint(0, 100) < 50:
                result_delta = self.c_delta
            else:
                result_delta = -self.c_delta
        
        res_c = result_c + result_delta
        if res_c > self.c_max - self.c_delta:
            result_delta = -self.c_delta
        elif res_c < 0:
          result_delta = self.c_delta
          
        return result_c + result_delta, result_delta
    

    r_frame = g_frame = b_frame = 120
    r_delta = -1
    g_delta = -1
    b_delta = -1
    frame = []
    def get(self):        
        # reset every N sec
        if (time.time() - self.timestamp > self.time_max_s):
            self.init()            
            self.frame = [[[0, 255, 0] for _ in range(self.xres)] for _ in range(self.yres)]
            self.time_max_s = time.time()
            return True, 0.5, self.frame
        else:           
            self.update()
            
            self.r_frame, self.r_delta = self.phase_colors(self.r_frame, self.r_delta)
            self.g_frame, self.g_delta = self.phase_colors(self.g_frame, self.g_delta)
            self.b_frame, self.b_delta = self.phase_colors(self.b_frame, self.b_delta)
            for y in range(self.yres):
                for x in range(self.xres):
                    if self.grid[y][x] == 1:
                        self.frame[y][x] = [self.r_frame, self.g_frame, self.b_frame]
                    else:
                        self.frame[y][x] = [0, 0, 0]
                    
        return True, 0.0, self.frame
