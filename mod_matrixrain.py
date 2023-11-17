import random


class MatrixRain:
    xres = 0
    yres = 0
    r = 115
    g = 128
    b = 115
    map = []
    rb_reduction = 30
    g_reduction = 10
    
    
    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        
        # 2d array of black color
        self.map = [ [[0, 0, 0]] * yres for _ in range(xres) ]

        
    def get(self):
        changes = []

        if random.randrange(0, 100) < 70:
            rnd_x = random.randrange(0, self.xres)
            self.map[rnd_x][0] = [self.r, self.g, self.b]
        
        for y in reversed(range(self.yres)):
            for x in range(self.xres):
                # copy pixel lower if not last line
                if y < self.yres - 1:
                    self.map[x][y + 1] = self.map[x][y]
                    
                if self.map[x][y] != [0, 0, 0] and self.map[x][y][0] != 0 and self.map[x][y][2] != 0:
                    # reduce the r, b colors
                    self.map[x][y] = [max(self.map[x][y][0] - self.rb_reduction, 0), self.g, max(self.map[x][y][2] - self.rb_reduction, 0)]  
                elif self.map[x][y][1] != 0:
                    # if only green color left reduce it
                    self.map[x][y] = [0, max(self.map[x][y][1] - self.g_reduction, 0), 0]
                
                changes.append([x, y, self.map[x][y]])
        
        # print(changes)
        return changes
                

# class Fly:
#     body = []
#     min_fly_len = 3
#     max_fly_len = 10
#     r = 115
#     g = 128
#     b = 115
#     head_xy = []
    
#     def __init__(self):
#         self.body = self.generate_body(random.randrange(self.min_fly_len, self.max_fly_len + 1))
        
#     def generate_body(self, fly_len):
#         body = [0, 0, 0] * fly_len
#         for i in range(0, fly_len):
#             body[i] = [int(max(self.r - i * (self.r / fly_len), 0)), self.g, int(max(self.b - i * (self.b / fly_len), 0))]        
#         return body
    
    