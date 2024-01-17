import math


class Lava:
    xres = 0
    yres = 0


    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres

    #
    # returns Tuple (bool: direct_draw, float: delay_ms, array: changes)
    #
    def get(self):
        return True, 0, self.invoke()


    b1_a0 = 0
    b1_a1 = 1
    def invoke(self):
        frame = [[[0, 0, 0] for x in range(self.xres)] for y in range(self.yres)]

        self.b1_a0 += 0.12
        self.b1_a1 += 0.24   
        
        for y in range(self.yres):
            for x in range(self.xres):
                r = 128 + math.floor((math.sin(self.b1_a0 + x * 0.4) + math.cos(self.b1_a1 + y * 0.4)) * 63)
                g = 128 + math.floor((math.sin(self.b1_a0 + y * 0.4) + math.cos(self.b1_a1 + x * 0.4)) * 63)
                b = 255 - r
                
                #changes.append([x, y, [int(r / 2), int(g / 2), int(b / 2)]])
                frame[x][y] = [int(r / 2), int(g / 2), int(b / 2)]
                
        return frame