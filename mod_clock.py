# 7 segment digits
#
# 05  00  01
# 55      11
# 456 66 126
# 44      22
# 34  33  23  
# 
#
# 0 => 0,1,2,3,4,5 => 00111111 => 63
# 1 => 1,2 => 00000110 => 6
# 2 => 0,1,3,4,6 => 01011011 => 91
# 3 => 0,1,2,3,6 => 01001111 
# 4 => 1,2,5,6 => 01100110
# 5 => 0,2,3,5,6 => 01100110
# 6 => 0,2,3,4,5,6 => 01111101
# 7 => 0,1,2 => 00000111
# 8 => 0,1,2,3,4,5,6 => 01111111
# 9 => 0,1,2,3,5,6 => 01101111

import math
import random
import time
from machine import RTC


class Clock:
    time_h = 0
    time_m = 0
    time_s = 0
    hh_color = [0, 0, 255]
    mm_color = [0, 255, 0]
    clear_color = [0, 0, 0]
    
    xres = 0
    yres = 0
    digits = [0b00111111, 0b00000110, 0b01011011, 0b01001111, 0b01100110, 0b01101101, 0b01111101, 0b00000111, 0b01111111, 0b01101111]
    bars = [
        [(0, 0), (1, 0), (2, 0)],
        [(2, 0), (2, 1), (2, 2)],
        [(2, 2), (2, 3), (2, 4)],
        [(0, 4), (1, 4), (2, 4)],
        [(0, 4), (0, 3), (0, 2)],
        [(0, 0), (0, 1), (0, 2)],
        [(0, 2), (1, 2), (2, 2)]]
    
   
    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres


    def get(self):
        changes = []
            
        changes.extend(self.get_number(self.time_h, rgb=self.clear_color, x_shift=2, y_shift=2, min_forced_lenght=2))
        changes.extend(self.get_number(self.time_m, rgb=self.clear_color, x_shift=7, y_shift=9, min_forced_lenght=2))
                        
        self.time_h = time.localtime()[3] + 1   # Central Europe timezone
        self.time_m = time.localtime()[4]
        self.time_s = time.localtime()[5]                

        changes.extend(self.draw_seconds_pointer())
        changes.extend(self.get_number(self.time_h, rgb=self.hh_color, x_shift=2, y_shift=2, min_forced_lenght=2))
        changes.extend(self.get_number(self.time_m, rgb=self.mm_color, x_shift=7, y_shift=9, min_forced_lenght=2))
        
        return changes
                                  

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

        digit_def = self.digits[digit]        
        bit_array = [digit_def >> i & 1 for i in range(0, 8)]                  
            
        for i in range(len(bit_array)):
            if bit_array[i] == 1:
                for xycoords in self.bars[i]:
                    # changes.append([xycoords[0] + x_shift, xycoords[1] + y_shift, [128 if digit % 2 == 0 else 0, 128 if digit % 3 else 0, 128 if digit % 7 else 0]])
                    changes.append([xycoords[0] + x_shift, xycoords[1] + y_shift, rgb])
            
        return changes
    

    def insert_str(self, source_str, insert_str, pos):
        return source_str[:pos] + insert_str + source_str[pos:]
        

    b1_a0 = 0
    b1_a1 = 1
    # getting out of memory
    def get_background_1(self):
        changes = []        
        self.b1_a0 += 0.1
        self.b1_a1 += 0.2        
        
        for y in range(self.yres):
            for x in range(self.xres):
                r = 128 + math.floor((math.sin(self.b1_a0 + x * 0.4) + math.cos(self.b1_a1 + y * 0.4)) * 63)
                g = 128 + math.floor((math.sin(self.b1_a0 + y * 0.4) + math.cos(self.b1_a1 + x * 0.4)) * 63)
                b = 255 - r
                changes.append([x, y, [int(r / 2), int(g / 2), int(b / 2)]])
                
        return changes
    
    
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
            changes.append([self.b2_xy, y, [64, 64, 32]])
        
        for x in range(self.xres):
            changes.append([x, self.b2_xy, [64, 64, 32]])
        
        return changes
    

    b3_x = -1
    b3_y = -1
    b3_r = 0
    b3_g = 0
    b3_b = 0
    b3_rd = 1
    b3_gd = 1
    b3_bd = 1
    b3_map = {}
    b3_fading = 0.5
    b3_new_pix_rgb = [128, 128, 128]
    # fading sec borders
    def draw_seconds_pointer(self):
        changes = []
                
        # fading clock borders
        step_color = 1
        max_color = 80
        rnd = random.randint(0, 3)
        if rnd == 0:
            if self.b3_r + step_color * self.b3_rd > max_color:
                self.b3_rd = -1                 
            elif self.b3_r + step_color * self.b3_rd < 0:
                self.b3_rd = 1
            self.b3_r += step_color * self.b3_rd       
        elif rnd == 1:
            if self.b3_g + step_color * self.b3_gd > max_color:
                self.b3_gd = -1                 
            elif self.b3_g + step_color * self.b3_gd < 0:
                self.b3_gd = 1
            self.b3_g += step_color * self.b3_gd                        
        elif rnd == 2:
            if self.b3_b + step_color * self.b3_bd > max_color:
                self.b3_bd = -1                 
            elif self.b3_b + step_color * self.b3_bd < 0:
                self.b3_bd = 1
            self.b3_b += step_color * self.b3_bd     
        
        x = int(self.b3_x)
        y = int(self.b3_y)
        
        if (x != -1):
            changes.append([x, y, [self.b3_r, self.b3_g, self.b3_b]])
            self.b3_map[(x, y)] = [self.b3_r, self.b3_g, self.b3_b]
                
        # fade out the colors
        for key, value in self.b3_map.items():
            if value != [0, 0, 0]:
                rgb = self.b3_map[key]
                self.b3_map[key] = [max(rgb[0] - self.b3_fading, 0), max(rgb[1] - self.b3_fading, 0), max(rgb[2] - self.b3_fading, 0)]
                changes.append([key[0], key[1], [int(self.b3_map[key][0]), int(self.b3_map[key][1]), int(self.b3_map[key][2])]])                      
        
        # clean dictionary from 0,0,0 values
        for key in list(self.b3_map.keys()):
            if self.b3_map[key] == [0, 0, 0]:
                del self.b3_map[key]
        
        radius = 12
        sec = self.time_s - 15
        
        i = 2 * math.pi * (sec / 60)
        self.b3_x = (self.xres - 1) / 2 + math.cos(i) * radius
        self.b3_y = (self.yres - 1) / 2 + math.sin(i) * radius
        
        self.b3_x = min(self.b3_x, self.xres - 1) if self.b3_x > self.xres else max(self.b3_x, 0)
        self.b3_y = min(self.b3_y, self.yres - 1) if self.b3_y > self.yres else max(self.b3_y, 0)               
        
        x = int(self.b3_x)
        y = int(self.b3_y)
        
        changes.append([x, y, self.b3_new_pix_rgb])
        self.b3_map[(x, y)] = self.b3_new_pix_rgb
        
        return changes