import random

class Santree:

	# this module is intended for 16x16 displays
	tree = (
		b'\x00\x00\x00\x00\x00\x00\x00\t\x00\x00\x00\x00\x00\x00\x00\x00',
		b'\x00\x00\x00\x00\x00\x00\t\t\t\x00\x00\x00\x00\x00\x00\x00',
		b'\x00\x00\x00\x00\x00\x00\x00\t\x00\x00\x00\x00\x00\x00\x00\x00',
		b'\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00',
		b'\x00\x00\x00\x00\x00\x00\x01\x01\t\x00\x00\x00\x00\x00\x00\x00',
		b'\x00\x00\x00\x00\x00\t\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00',
		b'\x00\x00\x00\x00\x00\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00',
		b'\x00\x00\x00\x00\t\x01\x01\x01\x01\x01\x01\t\x00\x00\x00\x00',
		b'\x00\x00\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00',
		b'\x00\t\x01\x01\x01\x01\t\x01\x01\t\x01\x01\x01\x01\t\x00',
		b'\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00',
		b'\x00\x03\x03\x04\x03\x03\x00\x02\x02\x00\x00\x00\x00\x00\x00\x00',
		b'\x00\x03\x03\x04\x03\x03\x00\x02\x02\x00\x00\x00\x00\x00\x00\x00',
		b'\x00\x04\x04\x04\x04\x04\x00\x02\x02\x00\x03\x04\x03\x05\x06\x05',
		b'\x00\x03\x03\x04\x03\x03\x00\x02\x02\x00\x04\x04\x04\x06\x06\x06',
		b'\x00\x03\x03\x04\x03\x03\x00\x02\x02\x00\x03\x04\x03\x05\x06\x05',
	)

	initialized = False

	xres = 0
	yres = 0

	col_black = 0
	col_green = 1
	col_brown = 2
	col_red = 3
	col_yellow = 4
	col_blue = 5
	col_white = 6
	col_sparkles = 9

	colors = {
		col_black : [[0, 0, 0]],
		col_green : [[0, 204, 0]],
		col_brown : [[204, 101, 0]],
		col_red : [[255, 0, 0]],
		col_yellow : [[240, 232, 10]],
		col_blue : [[0, 0, 204]],
		col_white : [[255, 255, 255]],
		col_sparkles : [[252, 100, 3], [252, 110, 3], [252, 120, 3], [252, 130, 3], [252, 140, 3], [252, 150, 3], [252, 160, 3], [252, 170, 3], [252, 180, 3]]
	}


	def __init__(self, xres, yres):
		self.xres = 16
		self.yres = 16
		self.frame = bytearray(16 * 16 * 3)
		self.sparkles = []
		for y in range(16):
			for x in range(16):
				kind = self.tree[y][x]
				change = [x, y, self.colors[kind][0]]
				offset = (x * 16 + y) * 3
				color = change[2]
				self.frame[offset] = color[0]
				self.frame[offset + 1] = color[1]
				self.frame[offset + 2] = color[2]
				if kind == self.col_sparkles:
					self.sparkles.append(change)
		self.initialized = False

	def get(self):
		palette = self.colors[self.col_sparkles]
		for change in self.sparkles:
			change[2] = palette[random.randrange(len(palette))]
		if not self.initialized:
			for x, y, color in self.sparkles:
				offset = (x * 16 + y) * 3
				self.frame[offset] = color[0]
				self.frame[offset + 1] = color[1]
				self.frame[offset + 2] = color[2]
			frame = self.frame
			self.frame = None
			self.initialized = True
			return True, 0.1, frame
		return False, 0.1, self.sparkles
