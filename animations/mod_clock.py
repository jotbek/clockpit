import random
import time
from core import helpers
from array import array


class Clock:
    hh_color = helpers.colors_rgb['blue']
    mm_color = helpers.colors_rgb['green']
    fading = 2
    r_frame = g_frame = b_frame = 120
    r_delta = g_delta = b_delta = -1

    def __init__(self, xres, yres):
        self.xres = xres
        self.yres = yres
        self.frame = bytearray(xres * yres * 3)
        self.pointer_colors = bytearray(60 * 3)
        self.pointer = array('H')
        for x in range(7, 16):
            self.pointer.append(x * yres)
        for y in range(1, 16):
            self.pointer.append(15 * yres + y)
        for x in range(14, -1, -1):
            self.pointer.append(x * yres + 15)
        for y in range(14, -1, -1):
            self.pointer.append(y)
        for x in range(1, 7):
            self.pointer.append(x * yres)
        self.time_h = self.time_m = -1
        self.time_s = 0
        self.dst_date = None
        self.utc_offset = 1

    def is_dst_poland(self, year, month, day, hour):
        # Checks if daylight saving time (DST) is in effect in Poland for the given date and time.
        # DST in Poland starts on the last Sunday of March at 2:00 AM
        # and ends on the last Sunday of October at 3:00 AM.

        # Find the last Sunday of March
        last_sunday_march = 31
        for d in range(31, 24, -1):
            if self.day_of_week(year, 3, d) == 6:  # Sunday
                last_sunday_march = d
                break
        # Find the last Sunday of October
        last_sunday_october = 31
        for d in range(31, 24, -1):
            if self.day_of_week(year, 10, d) == 6:  # Sunday
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

    def _number(self, number, color, x_shift, y_shift):
        for n in range(2):
            digit = number // 10 if n == 0 else number % 10
            glyph = helpers.digits_5x3[digit]
            for x in range(3):
                for y in range(5):
                    offset = ((x_shift + n * 4 + x) * self.yres + y_shift + y) * 3
                    if glyph[y][x]:
                        self.frame[offset] = color[0]
                        self.frame[offset + 1] = color[1]
                        self.frame[offset + 2] = color[2]
                    else:
                        self.frame[offset] = self.frame[offset + 1] = self.frame[offset + 2] = 0

    def get(self):
        lt = time.localtime()
        # Cache DST calculation, but refresh at the transition hour too.
        date = (lt[0], lt[1], lt[2], lt[3])
        if date != self.dst_date:
            self.utc_offset = 2 if self.is_dst_poland(*date) else 1
            self.dst_date = date
        hour = (lt[3] + self.utc_offset) % 24
        minute = lt[4]
        self.time_s = lt[5]
        if hour != self.time_h:
            self._number(hour, self.hh_color, 2, 2)
            self.time_h = hour
        if minute != self.time_m:
            self._number(minute, self.mm_color, 7, 9)
            self.time_m = minute
        self.draw_seconds_pointer()
        return True, 0.25, self.frame

    def draw_seconds_pointer(self):
        colors = self.pointer_colors
        self.r_frame, self.r_delta = self.phase_colors(self.r_frame, self.r_delta)
        self.g_frame, self.g_delta = self.phase_colors(self.g_frame, self.g_delta)
        self.b_frame, self.b_delta = self.phase_colors(self.b_frame, self.b_delta)
        for i in range(len(colors)):
            colors[i] = max(colors[i] - self.fading, 0)
        previous = ((self.time_s - 1) % 60) * 3
        colors[previous] = self.r_frame
        colors[previous + 1] = self.g_frame
        colors[previous + 2] = self.b_frame
        current = self.time_s * 3
        colors[current] = colors[current + 1] = colors[current + 2] = 255
        for i in range(60):
            offset = self.pointer[i] * 3
            color = i * 3
            self.frame[offset] = colors[color]
            self.frame[offset + 1] = colors[color + 1]
            self.frame[offset + 2] = colors[color + 2]

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
