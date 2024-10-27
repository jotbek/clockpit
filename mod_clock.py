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

    def is_dst_poland(self, year, month, day, hour):
        # Checks if daylight saving time (DST) is in effect in Poland for the given date and time.
        # DST in Poland starts on the last Sunday of March at 2:00 AM
        # and ends on the last Sunday of October at 3:00 AM.

        # Find the last Sunday of March
        last_sunday_march = 31
        for d in range(31, 24, -1):
            if self.day_of_week(year, 3, d) == 6:  # Niedziela
                last_sunday_march = d
                break
        # Find the last Sunday of October
        last_sunday_october = 31
        for d in range(31, 24, -1):
            if self.day_of_week(year, 10, d) == 6:  # Niedziela
                last_sunday_october = d
                break

        if (month > 3 and month < 10):
            return True
        elif month == 3:
            if day > last_sunday_march:
                return True
            elif day < last_sunday_march:
                return False
            else:  # day == last_sunday_march
                if hour >= 2:
                    return True
                else:
                    return False
        elif month == 10:
            if day < last_sunday_october:
                return True
            elif day > last_sunday_october:
                return False
            else:  # day == last_sunday_october
                if hour < 3:
                    return True
                else:
                    return False
        else:
            return False

    def day_of_week(self, y, m, d):
        # Zeller's Congruence algorithm for the Gregorian calendar
        if m < 3:
            m += 12
            y -= 1
        K = y % 100
        J = y // 100
        h = (d + ((13*(m + 1)) // 5) + K + (K // 4) + (J // 4) - 2*J) % 7
        # h = 0: Saturday
        # h = 1: Sunday
        # h = 2: Monday
        # h = 3: Tuesday
        # h = 4: Wednesday
        # h = 5: Thursday
        # h = 6: Friday
        # Adjust to week numbering where Monday=0, Sunday=6
        weekday = (h + 5) % 7
        return weekday  # 0=Monday, ..., 6=Sunday

    def get(self):
        changes = []
            
        changes.extend(self.get_number(self.time_h, rgb=self.clear_color, x_shift=2, y_shift=2, min_forced_lenght=2))
        changes.extend(self.get_number(self.time_m, rgb=self.clear_color, x_shift=7, y_shift=9, min_forced_lenght=2))
           
        lt = time.localtime()
        year = lt[0]
        month = lt[1]
        day = lt[2]
        hour = lt[3]
        minute = lt[4]
        second = lt[5]

        if self.is_dst_poland(year, month, day, hour):
            h = hour + 2  # CEST (UTC+2)
        else:
            h = hour + 1  # CET (UTC+1)

        if h >= 24:
            h -= 24

        self.time_h = h
        self.time_m = minute
        self.time_s = second              

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
    # Simple moving lines
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
    

    # Fading second borders
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