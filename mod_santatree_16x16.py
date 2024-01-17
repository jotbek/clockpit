import random

class Santree:
    
	# this module is intended for 16x16 displays
	tree = [
		[0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,0],
		[0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0],
		[0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,0],
		[0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0],
		[0,0,0,0,0,0,1,1,9,0,0,0,0,0,0,0],
		[0,0,0,0,0,9,1,1,1,1,0,0,0,0,0,0],
		[0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
		[0,0,0,0,9,1,1,1,1,1,1,9,0,0,0,0],
		[0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0],
		[0,9,1,1,1,1,9,1,1,9,1,1,1,1,9,0],
		[0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
		[0,3,3,4,3,3,0,2,2,0,0,0,0,0,0,0],
		[0,3,3,4,3,3,0,2,2,0,0,0,0,0,0,0],
		[0,4,4,4,4,4,0,2,2,0,3,4,3,5,6,5],
		[0,3,3,4,3,3,0,2,2,0,4,4,4,6,6,6],
		[0,3,3,4,3,3,0,2,2,0,3,4,3,5,6,5]
	]

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
		

	def get(self):
		changes = []
	
		for x in range(self.xres):
			for y in range(self.yres):
    			# if there is only one color under color list (not like e.g. in sparkles) draw it once
				no_colors = len(self.colors[self.tree[x][y]])
    
				# inverted y <==> x axis to map correctly tree matrix
				if no_colors > 1:
					changes.append([y, x, self.colors[self.tree[x][y]][random.randrange(0, no_colors)]])
				else:
					changes.append([y, x, self.colors[self.tree[x][y]][0]])
		
		# set initialization flag
		#self.initialized = True
		return False, 0.1, changes