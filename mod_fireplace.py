import random


class Fireplace:
    xres = 0
    yres = 0
    spark_fq = 5 # chance is (100 / spark_fq)%

    min_ignite = 3
    max_ignite = 13
    black_rgb = [0, 0, 0]
    white_rgb = [255, 255, 255]
    colors_arr = [
        white_rgb,
        [255, 255, 204],
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
    frame = []
    frame_rgb = []


    def __init__(self, xres, yres):        
        self.xres = xres
        self.yres = yres

        i = 0
        for col in self.colors_arr:
            self.colors_dict[len(self.colors_arr) - i - 1] = col
            i += 1

        self.frame = [[0 for x in range(self.xres)] for y in range(self.yres)]
        self.frame_rgb = [[[0, 0, 0] for x in range(self.xres)] for y in range(self.yres)]

    
    def get(self):
        self.ignite()
        self.animate()

        return True, 0.0, self.apply_filters_convert2rgb()

    
    def animate(self):
        self.animate_delta(0, self.yres)
        
        if random.randint(0, self.spark_fq) == 0:   # spark
            self.frame[random.randint(0, self.xres - 1)][random.randint(0, int(self.yres / 2))] = len(self.colors_dict) - 1
    
    
    def animate_delta(self, ymin, ymax):
        # perfomance: reference locally
        _frame = self.frame
        
        for y in range(ymin, ymax):
            for x in range(self.xres):
                x_direction = random.randint(-1, 1)
                
                color = min(_frame[x][y], _frame[x][y] - random.randint(1, 2))
                if _frame[max(x - 1, 0)][y] == 0 or x - 1 < 3:
                    color = max(color - 3, 0)

                if (_frame[min(x + 1, self.xres - 1)]) == 0 or x + 1 > self.xres - 4:
                    color = max(color - 3, 0)    
                self.light(x, y, x + x_direction, y - 1, color)
            

    def apply_filters_convert2rgb(self):
        self.apply_filter(0, self.yres)
        
        return self.frame_rgb


    def apply_filter(self, ymin, ymax):
        # perfomance: reference locally
        _frame_rgb = self.frame_rgb
        
        for y in range(ymin, ymax):
            for x in range(self.xres):
                _frame_rgb[x][y] = self.apply_low_pass_filter(x, y)


    def apply_low_pass_filter(self, x, y):
        # perfomance: reference locally
        _colors_dict = self.colors_dict
        _frame = self.frame
        
        r, g, b = 0, 0, 0
        
        if self.frame[x][y] == 0:
            return [r, g, b]
                            
        # sum rgb values of colors from surrounding pixels
        for dy in range(-1, 1):
            for dx in range(-1, 1):  
                fx = x + dx
                fy = y + dy        
                if fx > 0 and fx < self.xres and fy > 0 and fy < self.yres:
                    r += _colors_dict[_frame[fx][fy]][0]
                    g += _colors_dict[_frame[fx][fy]][1]
                    b += _colors_dict[_frame[fx][fy]][2]

        return [int(r / 9), int(g / 9), int(b / 9)]


    def light(self, x, y, x_new, y_new, color):
        # perfomance: reference locally
        _frame = self.frame
        
        if y_new >= 0 and y_new < self.yres:
            if x_new >= 0 and x_new < self.xres :
                _frame[x_new][y_new] = max(color, 0)
        
        # replace old pixel            
        _frame[x][y] = max(_frame[x][y] - 1, 0)


    def ignite(self):
        for x in range(self.min_ignite, self.max_ignite):
            self.frame[x][self.yres - 1] = len(self.colors_dict) - 1