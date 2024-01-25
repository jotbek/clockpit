import math
import _thread


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
        self.done_1 = self.done_2 = False
        _thread.start_new_thread(self.invoke_1, [])        
        self.invoke_2()
                        
        return True, 0, self.frame


    delta1 = 0
    delta2 = 1
    done_1 = False
    def invoke_1(self):
        self.delta1 += 0.2
        self.delta2 += 0.28   
        
        for y in range(0, int(self.yres / 2)):
            for x in range(0, self.xres):
                r = 128 + math.floor((math.sin(self.delta1 + x * 0.4) + math.cos(self.delta2 + y * 0.4)) * 63)
                g = 128 + math.floor((math.sin(self.delta1 + y * 0.4) + math.cos(self.delta2 + x * 0.4)) * 63)
                b = 255 - r
                
                #changes.append([x, y, [int(r / 2), int(g / 2), int(b / 2)]])
                self.frame[x][y] = [int(r / 2), int(g / 2), int(b / 2)]
                
        self.done_1 = True
    

    delta3 = 0
    delta4 = 1
    done_2 = False
    def invoke_2(self):       
        self.delta3 += 0.2
        self.delta4 += 0.28   
        
        for y in range(8, 16):
            for x in range(0, 16):
                r = 128 + math.floor((math.sin(self.delta3 + x * 0.4) + math.cos(self.delta4 + y * 0.4)) * 63)
                g = 128 + math.floor((math.sin(self.delta3 + y * 0.4) + math.cos(self.delta4 + x * 0.4)) * 63)
                b = 255 - r
                
                #changes.append([x, y, [int(r / 2), int(g / 2), int(b / 2)]])
                self.frame[x][y] = [int(r / 2), int(g / 2), int(b / 2)]
        
        self.done_2 = True