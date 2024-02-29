import math
import random
import time
import helpers
from machine import RTC


class Clock:
    time_h = 0
    time_m = 0
    time_s = 0
    hh_color = helpers.colors_rgb['blue']
    mm_color = helpers.colors_rgb['green']
    clear_color = helpers.colors_rgb['black']
    
    xres = 0
    yres = 0  
   
    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres


    def get(self):
        changes = []
            
        changes.extend(self.get_number(self.time_h, rgb=self.clear_color, x_shift=2, y_shift=2, min_forced_lenght=2))
        changes.extend(self.get_number(self.time_m, rgb=self.clear_color, x_shift=7, y_shift=9, min_forced_lenght=2))
           
        h = time.localtime()[3] + 1      
        self.time_h = 0 if h == 24 else h  # Central Europe timezone
        self.time_m = time.localtime()[4]
        self.time_s = time.localtime()[5]                

        # changes.extend(self.get_background_2())
        
        changes.extend(self.get_number(self.time_h, rgb=self.hh_color, x_shift=2, y_shift=2, min_forced_lenght=2))
        changes.extend(self.get_number(self.time_m, rgb=self.mm_color, x_shift=7, y_shift=9, min_forced_lenght=2))

        changes.extend(self.draw_seconds_pointer())
        
        return False, 0.25, changes
                                  

    def get_number(self, number, rgb, x_shift = 0, y_shift = 0, min_forced_lenght = 0):
        changes = []
        str_number = str(number)
        no_digits = len(str_number)

        if min_forced_lenght != 0 and min_forced_lenght > no_digits:
            str_number = self.insert_str(str_number, "0" * (min_forced_lenght - no_digits), 0)
            no_digits = min_forced_lenght
            
        for i in range(len(str_number)):
            changes.extend(self.get_digit(int(str_number[i]), rgb, x_shift + 3 * i + i, y_shift))
            
        return changes


    def get_digit(self, digit, rgb, x_shift = 0, y_shift = 0):
        changes = []
        if (digit < 0 or digit > 9):
            return changes          
            
        for y in range(5):
            for x in range(3):
                if helpers.digits_5x3[digit][y][x] != 0: 
                    changes.append([x + x_shift, y + y_shift, rgb])
        
        return changes
    

    def insert_str(self, source_str, insert_str, pos):
        return source_str[:pos] + insert_str + source_str[pos:]
    
    
    b2_xy = -1
    b2_direction = 1
    # simple moving lines
    def get_background_2(self):        
        changes = []
        
        if self.b2_xy != -1:
            for y in range(self.yres):
                changes.append([self.b2_xy, y, [0, 0, 0]])
            
            for x in range(self.xres):
                changes.append([x, self.b2_xy, [0, 0, 0]])
        
        if self.b2_xy + self.b2_direction == self.xres or self.b2_xy + self.b2_direction < 0:
            self.b2_direction *= -1

        self.b2_xy += self.b2_direction
        
        for y in range(self.yres):
            changes.append([self.b2_xy, y, [8, 4, 2]])
        
        for x in range(self.xres):
            changes.append([x, self.b2_xy, [8, 4, 2]])
        
        return changes
    

    # fading sec borders
    dots = []
    r_frame = g_frame = b_frame = 120
    r_delta = -1
    g_delta = -1
    b_delta = -1
    fading = 2
    pointer = []
    pointer_initialized = False
    def draw_seconds_pointer(self):
        if not self.pointer_initialized:
            self.pointer = self.init_pointer()
            self.pointer_initialized = True
            
        self.r_frame, self.r_delta = self.phase_colors(self.r_frame, self.r_delta)
        self.g_frame, self.g_delta = self.phase_colors(self.g_frame, self.g_delta)
        self.b_frame, self.b_delta = self.phase_colors(self.b_frame, self.b_delta)
             
        for p in self.pointer:
            if p[2] != helpers.colors_rgb['black']:
                p[2][0] = max(p[2][0] - self.fading, 0)
                p[2][1] = max(p[2][1] - self.fading, 0)
                p[2][2] = max(p[2][2] - self.fading, 0)            
        
        self.pointer[59 if self.time_s - 1 < 0 else self.time_s - 1][2] = [self.r_frame, self.g_frame, self.b_frame]
        self.pointer[self.time_s][2] = [255, 255, 255]
        
        return self.pointer
    
    
    def init_pointer(self):
        changes = [[x, 0, [0,0,0]] for x in range(7, 16)]               
        changes.extend([[15, y, [0,0,0]] for y in range(1, 16)])        
        changes.extend([[x, 15, [0,0,0]] for x in range(14, -1, -1)])   
        changes.extend([[0, y, [0,0,0]] for y in range(14, -1, -1)])    
        changes.extend([[x, 0, [0,0,0]] for x in range(1, 7)])          
        return changes
        
        
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