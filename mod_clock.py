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


class Clock:
    dev_hh = 0
    dev_mm = 0
    hh_color = [0, 0, 255]
    mm_color = [0, 255, 0]
    
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
            
        self.dev_mm += 1
        if self.dev_mm == 60:
            self.dev_mm = 0
            self.dev_hh += 1
            if self.dev_hh == 60:
                self.dev_hh = 0

        changes = self.get_background_2()
        changes.extend(self.get_number(self.dev_hh, rgb=self.hh_color, x_shift=1, y_shift=3, min_forced_lenght=2))
        changes.extend(self.get_number(self.dev_mm, rgb=self.mm_color, x_shift=8, y_shift=8, min_forced_lenght=2))
        
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
        

    bckg1_a0 = 0
    bckg1_a1 = 1
    def get_background_1(self):
        changes = []        
        self.bckg1_a0 += 0.1
        self.bckg1_a1 += 0.2        
        
        for y in range(self.yres):
            for x in range(self.xres):
                r = 128 + math.floor((math.sin(self.bckg1_a0 + x * 0.4) + math.cos(self.bckg1_a1 + y * 0.4)) * 63)
                g = 128 + math.floor((math.sin(self.bckg1_a0 + y * 0.4) + math.cos(self.bckg1_a1 + x * 0.4)) * 63)
                b = 255 - r
                changes.append([x, y, [int(r / 2), int(g / 2), int(b / 2)]])
                
        return changes
    
    
    bckg2_x = -1
    bckg2_direction = 1
    def get_background_2(self):        
        changes = []
        if self.bckg2_x + self.bckg2_direction == self.xres or self.bckg2_x + self.bckg2_direction < 0:
            self.bckg2_direction *= -1

        self.bckg2_x += self.bckg2_direction
        
        for y in range(self.yres):
            changes.append([self.bckg2_x, y, [64, 64, 64]])
        
        return changes
            
            

            


# a = [int(i) for i in "{0:08b}".format(c)]