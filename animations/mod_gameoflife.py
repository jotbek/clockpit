import random
from core import timing


class GameOfLife:
    time_max_s = 20
    r_frame = g_frame = b_frame = 120
    r_delta = g_delta = b_delta = -1

    def __init__(self, xres, yres, delay=0.1):
        self.xres = xres
        self.yres = yres
        self.delay = delay
        self.stride = xres + 2
        size = (xres + 2) * (yres + 2)
        self.grid = bytearray(size)
        self.next_grid = bytearray(size)
        self.frame = bytearray(xres * yres * 3)
        self.init()

    def init(self):
        for y in range(1, self.yres + 1):
            for x in range(1, self.xres + 1):
                self.grid[y * self.stride + x] = random.randint(0, 1)
        self.timestamp = timing.ticks_ms()

    def update(self):
        grid, new_grid = self.grid, self.next_grid
        stride = self.stride
        # Zero border removes eight bounds checks and a neighbour list per cell.
        for y in range(1, self.yres + 1):
            for x in range(1, self.xres + 1):
                i = y * stride + x
                n = (grid[i - stride - 1] + grid[i - stride] + grid[i - stride + 1]
                     + grid[i - 1] + grid[i + 1]
                     + grid[i + stride - 1] + grid[i + stride] + grid[i + stride + 1])
                new_grid[i] = n == 3 or (grid[i] and n == 2)
        self.grid, self.next_grid = new_grid, grid

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


    def get(self):
        frame = self.frame
        if timing.ticks_diff(timing.ticks_ms(), self.timestamp) > self.time_max_s * 1000:
            self.init()
            for i in range(0, len(frame), 3):
                frame[i], frame[i + 1], frame[i + 2] = self.r_frame, self.g_frame, self.b_frame
            return True, 0.5, frame
        self.update()
        self.r_frame, self.r_delta = self.phase_colors(self.r_frame, self.r_delta)
        self.g_frame, self.g_delta = self.phase_colors(self.g_frame, self.g_delta)
        self.b_frame, self.b_delta = self.phase_colors(self.b_frame, self.b_delta)
        offset = 0
        for x in range(1, self.xres + 1):
            for y in range(1, self.yres + 1):
                alive = self.grid[y * self.stride + x]
                frame[offset] = self.r_frame if alive else 0
                frame[offset + 1] = self.g_frame if alive else 0
                frame[offset + 2] = self.b_frame if alive else 0
                offset += 3
        return True, self.delay, frame
