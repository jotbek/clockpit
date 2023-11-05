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


class Clock:
    digits = [0b00111111, 0b00000110, 0b01011011, 0b01001111, 0b01100110, 0b01101101, 0b01111101, 0b00000111, 0b01111111, 0b01101111]
    bars = [
        [(0, 0), (1, 0), (2, 0)],
        [(2, 0), (2, 1), (2, 2)],
        [(2, 2), (2, 3), (2, 4)],
        [(0, 4), (1, 4), (2, 4)],
        [(0, 4), (0, 3), (0, 2)],
        [(0, 0), (0, 1), (0, 2)],
        [(0, 2), (1, 2), (2, 2)]]
    
    def __init__(self):
        return None


    def get(self, digit):
        changes = []

        digit_def = self.digits[digit]        
        bit_array = [digit_def >> i & 1 for i in range(0, 8)]                  
            
        for i in range(len(bit_array)):
            if bit_array[i] == 1:
                for xycoords in self.bars[i]:
                    changes.append([xycoords[0], xycoords[1], [128 if digit % 2 == 0 else 0, 128 if digit % 3 else 0, 128 if digit % 7 else 0]])
            
        return changes
    

    def get_number(self, number, min_forced_lenght = 0):
        changes = []
        str_number = str(number)
        no_digits = len(str_number)

        if min_forced_lenght != 0 and min_forced_lenght > no_digits:
            str_number = self.insert_str(str_number, "0" * (min_forced_lenght - no_digits), 0)
            no_digits = min_forced_lenght


    def get_digit(self, digit):
        changes = []
        if (digit < 0 or digit > 9):
            return changes

        digit_def = self.digits[digit]        
        bit_array = [digit_def >> i & 1 for i in range(0, 8)]                  
            
        for i in range(len(bit_array)):
            if bit_array[i] == 1:
                for xycoords in self.bars[i]:
                    changes.append([xycoords[0], xycoords[1], [128 if digit % 2 == 0 else 0, 128 if digit % 3 else 0, 128 if digit % 7 else 0]])
            
        return changes
    

    def insert_str(self, source_str, insert_str, pos):
        return source_str[:pos] + insert_str + source_str[pos:]
        


# a = [int(i) for i in "{0:08b}".format(c)]