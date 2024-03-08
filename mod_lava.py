import math

class Lava:
    xres = 0
    yres = 0
    frame = []

    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.frame = [[[0, 0, 0] for x in range(xres)] for y in range(yres)]


    #
    # returns Tuple (bool: direct_draw, float: delay_ms, array: changes)
    #
    def get(self):
        self.animate()
                        
        return True, 0.0, self.frame
  

    delta3 = 0
    delta4 = 1
    done_2 = False
    def animate(self):       
        self.delta3 += 0.2
        self.delta4 += 0.28   
        
        for y in range(0, 16):
            for x in range(0, 16):
                r = 128 + math.floor((math.sin(self.delta3 + x * 0.4) + math.cos(self.delta4 + y * 0.4)) * 63)
                g = 128 + math.floor((math.sin(self.delta3 + y * 0.4) + math.cos(self.delta4 + x * 0.4)) * 63)
                b = 255 - r
                
                #changes.append([x, y, [int(r / 2), int(g / 2), int(b / 2)]])
                self.frame[x][y] = [int(r / 2), int(g / 2), int(b / 2)]
        
        self.done_2 = True