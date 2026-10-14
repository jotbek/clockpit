import random
import time
from core import helpers
from array import array
from core.colors import hsv_into


class Maze:
    def __init__(self, xres, yres, delay=0.06):
        self.xres = xres
        self.yres = yres
        self.delay = delay

        # inner area excludes outer border (row/col 0 and xres-1/yres-1)
        self.min_x = 1
        self.min_y = 1
        self.max_x = xres - 2
        self.max_y = yres - 2

        # full pixel grid: True = wall, False = open
        self.grid = [bytearray(b'\x01' * xres) for _ in range(yres)]
        self.frame = bytearray(xres * yres * 3)

        # compute cell grid size and set entrance/exit to actual cell pixels (diagonal inside inner area)
        w = (self.max_x - self.min_x + 1) // 2
        h = (self.max_y - self.min_y + 1) // 2
        if w < 1:
            w = 1
        if h < 1:
            h = 1
        self.entrance = (self.min_x, self.min_y)
        self.exit = (self.min_x + (w - 1) * 2 + 1, self.min_y + (h - 1) * 2 + 1)

        # create solvable maze (try several times, fallback to carving direct corridor)
        self._create_solvable_maze()

        # moving pixel index along path
        self.head_idx = 0

        # hue cycling offset
        self.hue_offset = 0

        # first frame should be full (render entire board)
        self._first = True

        # glow map: coords -> intensity (0-255)
        self.glows = {}
        self.glow_start = 180
        self.glow_step = 40
        # end-of-path pause control
        self.at_end = False
        self.pause_until = 0
        self.pause_duration = 0.5

    def _generate_maze(self):
        w = (self.max_x - self.min_x + 1) // 2
        h = (self.max_y - self.min_y + 1) // 2
        if w < 1:
            w = 1
        if h < 1:
            h = 1

        # cell visited map
        visited = [bytearray(w) for _ in range(h)]

        def cell_to_pixel(cx, cy):
            return (self.min_x + cx * 2, self.min_y + cy * 2)

        # initialize all inner pixels as walls
        for y in range(self.min_y, self.max_y + 1):
            for x in range(self.min_x, self.max_x + 1):
                self.grid[y][x] = True

        stack = [(0, 0)]
        visited[0][0] = True

        while stack:
            cx, cy = stack[-1]
            # map current cell to pixel and mark open
            px, py = cell_to_pixel(cx, cy)
            self.grid[py][px] = False

            # neighbors in cardinal directions
            neighbors = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                    neighbors.append((nx, ny))
            if neighbors:
                nx, ny = random.choice(neighbors)
                # remove wall between (cx,cy) and (nx,ny); compute pixels directly
                px, py = cell_to_pixel(cx, cy)
                nxp, nyp = cell_to_pixel(nx, ny)
                mx = (px + nxp) // 2
                my = (py + nyp) // 2
                self.grid[my][mx] = False
                visited[ny][nx] = True
                stack.append((nx, ny))
            else:
                stack.pop()

        # ensure exit is reachable: carve to the exit pixel if needed
        ex, ey = self.exit
        if self.grid[ey][ex]:
            # connect to nearest cell pixel (which are located at odd coordinates)
            tx = ex - 1 if (ex - 1) >= self.min_x else ex + 1
            ty = ey - 1 if (ey - 1) >= self.min_y else ey + 1
            # open the cell pixel
            self.grid[ty][tx] = False
            # carve a proper connector (L-shaped 2-step) so diagonal exit is reachable
            # choose vertical then horizontal connector (tx, ey) which connects (tx,ty)->(tx,ey)->(ex,ey)
            connx, conny = tx, ey
            self.grid[conny][connx] = False
            # finally ensure exit pixel is open
            self.grid[ey][ex] = False

    def _create_solvable_maze(self, max_attempts=20):
        # Attempt to generate until a path is found
        for attempt in range(max_attempts):
            # reset inner area to walls
            for y in range(self.min_y, self.max_y + 1):
                for x in range(self.min_x, self.max_x + 1):
                    self.grid[y][x] = True
            self._generate_maze()

            # ensure entrance and exit are open
            sx, sy = self.entrance
            ex, ey = self.exit
            self.grid[sy][sx] = False
            self.grid[ey][ex] = False

            # compute wall list
            self.walls = [(x, y) for y in range(self.min_y, self.max_y + 1) for x in range(self.min_x, self.max_x + 1) if self.grid[y][x]]

            # try to find a path
            p = self._astar(self.entrance, self.exit)
            if p:
                self.path = p
                break
        else:
            # fallback: carve a narrow path through the cell grid (avoid clearing an entire column)
            sx, sy = self.entrance
            ex, ey = self.exit
            # convert to cell coordinates
            cell_sx = (sx - self.min_x) // 2
            cell_sy = (sy - self.min_y) // 2
            cell_ex = (ex - self.min_x) // 2
            cell_ey = (ey - self.min_y) // 2

            # walk from start cell to end cell, carving cells and walls between
            cx, cy = cell_sx, cell_sy
            def cell_to_pixel(cx, cy):
                return (self.min_x + cx * 2, self.min_y + cy * 2)

            # carve starting cell
            px, py = cell_to_pixel(cx, cy)
            self.grid[py][px] = False

            while (cx, cy) != (cell_ex, cell_ey):
                # choose direction towards goal (prefer one axis randomly to make path less straight)
                dx = 0
                dy = 0
                if cx != cell_ex and cy != cell_ey:
                    if random.choice([True, False]):
                        dx = 1 if cell_ex > cx else -1
                    else:
                        dy = 1 if cell_ey > cy else -1
                elif cx != cell_ex:
                    dx = 1 if cell_ex > cx else -1
                else:
                    dy = 1 if cell_ey > cy else -1

                ncx, ncy = cx + dx, cy + dy
                # carve wall between current cell and next cell
                cpx, cpy = cell_to_pixel(cx, cy)
                npx, npy = cell_to_pixel(ncx, ncy)
                midx = (cpx + npx) // 2
                midy = (cpy + npy) // 2
                self.grid[midy][midx] = False
                # carve next cell pixel
                self.grid[npy][npx] = False
                cx, cy = ncx, ncy

            # connect final cell to exit (make sure exit isn't isolated) - carve L-shaped connector
            cpx, cpy = cell_to_pixel(cell_ex, cell_ey)
            # carve connector at (cpx, ey) and ensure exit pixel is open
            self.grid[ey][cpx] = False
            self.grid[ey][ex] = False

            # update walls and path
            self.walls = [(x, y) for y in range(self.min_y, self.max_y + 1) for x in range(self.min_x, self.max_x + 1) if self.grid[y][x]]

            # try to find a path; if still missing, carve a minimal pixel corridor directly to exit
            p = self._astar(self.entrance, self.exit)
            if not p:
                sx, sy = self.entrance
                ex2, ey2 = self.exit
                for x in range(min(sx, ex2), max(sx, ex2) + 1):
                    self.grid[sy][x] = False
                for y in range(min(sy, ey2), max(sy, ey2) + 1):
                    self.grid[y][ex2] = False
                # recompute walls and path
                self.walls = [(x, y) for y in range(self.min_y, self.max_y + 1) for x in range(self.min_x, self.max_x + 1) if self.grid[y][x]]
                p = self._astar(self.entrance, self.exit)

            self.path = p or [self.entrance, self.exit]

        # reset head and animation state
        self.head_idx = 0
        self.hue_offset = 0
        self._first = True
        # reset glow and pause state
        self.glows = {}
        self.at_end = False
        self.pause_until = 0

    def _neighbors(self, node):
        x, y = node
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.xres and 0 <= ny < self.yres and not self.grid[ny][nx]:
                yield (nx, ny)

    def _astar(self, start, goal):
        # All moves cost one: BFS finds a shortest path without A*'s 3 dicts/set.
        width = self.xres
        size = width * self.yres
        parents = array('h', b'\xff\xff' * size)
        start_id = start[1] * width + start[0]
        goal_id = goal[1] * width + goal[0]
        parents[start_id] = start_id
        queue = array('H', [start_id])
        head = 0
        while head < len(queue):
            current = queue[head]
            head += 1
            if current == goal_id:
                path = []
                while current != start_id:
                    path.append((current % width, current // width))
                    current = parents[current]
                path.append(start)
                path.reverse()
                return path
            x, y = current % width, current // width
            for nx, ny in self._neighbors((x, y)):
                index = ny * width + nx
                if parents[index] == -1:
                    parents[index] = current
                    queue.append(index)
        return None

    def _set(self, x, y, color):
        offset = (x * self.yres + y) * 3
        self.frame[offset] = color[0]
        self.frame[offset + 1] = color[1]
        self.frame[offset + 2] = color[2]

    def _base(self, coord):
        if coord == self.entrance:
            return helpers.colors_rgb['green']
        if coord == self.exit:
            return helpers.colors_rgb['blue']
        return helpers.colors_rgb['black']

    def get(self):
        if self.at_end and time.time() >= self.pause_until:
            self._create_solvable_maze()
        frame = self.frame
        if self._first:
            for i in range(len(frame)):
                frame[i] = 0
            self._set(*self.entrance, helpers.colors_rgb['green'])
            self._set(*self.exit, helpers.colors_rgb['blue'])
        palette_len = max(6, len(self.walls))
        for idx, (x, y) in enumerate(self.walls):
            hue = ((idx + self.hue_offset) % palette_len) * 360 // palette_len
            hsv_into(frame, (x * self.yres + y) * 3, hue, 179, 153)
        self.hue_offset = (self.hue_offset + 1) % palette_len
        if self._first:
            self._first = False
            return True, self.delay, frame
        # Only the small tail dictionary needs a temporary key snapshot.
        for coord in tuple(self.glows):
            intensity = self.glows[coord] - self.glow_step
            if intensity <= 0:
                del self.glows[coord]
                self._set(*coord, self._base(coord))
            else:
                self.glows[coord] = intensity
                self._set(*coord, (intensity, 0, 0))
        if self.at_end:
            self._set(*self.path[-1], helpers.colors_rgb['red'])
            return True, self.delay, frame
        if self.path:
            previous = self.path[max(0, self.head_idx - 1)]
            self.glows[previous] = self.glow_start
            self._set(*previous, (self.glow_start, 0, 0))
            self._set(*self.path[self.head_idx], helpers.colors_rgb['red'])
            self.head_idx += 1
            if self.head_idx >= len(self.path):
                self.head_idx = len(self.path) - 1
                self.at_end = True
                self.pause_until = time.time() + self.pause_duration
        return True, self.delay, frame
