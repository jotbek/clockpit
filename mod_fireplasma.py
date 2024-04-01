import time
import random


class FirePlasma:   
    xres = 0
    yres = 0
    width = 0
    height = 0
    heat = []
    fire_spawns = 5
    damping_factor = 0.97
    fire_colours = [[0, 0, 0],
                    [15, 0, 0],
                    [30, 0, 0],
                    [180, 0, 0],
                    [220, 100, 0],
                    [252, 210, 60],
                    [252, 220, 100],
                    [255, 255, 180]]


    def __init__(self, xres, yres):
        self.xres = xres        
        self.yres = yres
        self.width = xres + 2
        self.height = yres + 4
        self.frame = [[[0, 0, 0] for x in range(xres)] for y in range(yres)]
        self.heat = [[0.0 for y in range(self.height)] for x in range(self.width)]


    def get(self):
        self.update()
        self.draw()
        return True, 0.0, self.frame
    
    
    def update(self):
        # take local references as it's quicker than accessing the global
        # and we access it a lot in this method
        _heat = self.heat

        # clear the bottom row and then add a new fire seed to it
        for x in range(self.width):
            _heat[x][self.height - 1] = 0.0
            _heat[x][self.height - 2] = 0.0

        for c in range(self.fire_spawns):
            x = random.randint(0, self.width - 4) + 2
            _heat[x + 0][self.height - 1] = 1.0
            _heat[x + 1][self.height - 1] = 1.0
            _heat[x - 1][self.height - 1] = 1.0
            _heat[x + 0][self.height - 2] = 1.0
            _heat[x + 1][self.height - 2] = 1.0
            _heat[x - 1][self.height - 2] = 1.0

        factor = self.damping_factor / 5.0
        for y in range(0, self.height - 2):
            for x in range(1, self.width - 1):
                _heat[x][y] += _heat[x][y + 1] + _heat[x][y + 2] + _heat[x - 1][y + 1] + _heat[x + 1][y + 1]
                _heat[x][y] *= factor


    def draw(self):
        # take local references as it's quicker than accessing the global
        # and we access it a lot in this method
        _heat = self.heat
        _fire_colours = self.fire_colours
        _frame = self.frame
        col = _fire_colours[0]
        
        for y in range(self.yres):
            for x in range(self.xres):
                value = _heat[x + 1][y]
                if value < 0.38:
                    col = _fire_colours[0]
                elif value < 0.4:
                    col = _fire_colours[1]
                elif value < 0.45:
                    col = _fire_colours[2]                    
                elif value < 0.50:
                    col = _fire_colours[3]
                elif value < 0.54:
                    col = _fire_colours[4]
                elif value < 0.58:
                    col = _fire_colours[5]
                elif value < 0.63:
                    col = _fire_colours[6]                    
                else:
                    col = _fire_colours[7]
                
                _frame[x][y] = col