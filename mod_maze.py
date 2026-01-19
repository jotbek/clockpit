import random
import time
import helpers


class Maze:
    def __init__(self, xres, yres, delay=0.06):
        self.xres = xres
        self.yres = yres
        self.delay = delay

        # inner area excludes outer border (row/col 0 and xres-1/yres-1)
        self.min_x = 1
        self.min_y = 1
        self.max_x = xres - 1
        self.max_y = yres - 1

        # full pixel grid: True = wall, False = open
        self.grid = [[True for _ in range(xres)] for _ in range(yres)]

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
        # precompute per-wall index for color consistency
        self.wall_index = {coord: i for i, coord in enumerate(self.walls)}

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
        visited = [[False for _ in range(w)] for _ in range(h)]

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
                # remove wall between (cx,cy) and (nx,ny) — compute pixels directly
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

            # compute wall list and index
            self.walls = [(x, y) for y in range(self.yres) for x in range(self.xres) if self.grid[y][x]]
            self.wall_index = {coord: i for i, coord in enumerate(self.walls)}

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
            self.walls = [(x, y) for y in range(self.yres) for x in range(self.xres) if self.grid[y][x]]
            self.wall_index = {coord: i for i, coord in enumerate(self.walls)}

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
                self.walls = [(x, y) for y in range(self.yres) for x in range(self.xres) if self.grid[y][x]]
                self.wall_index = {coord: i for i, coord in enumerate(self.walls)}
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

    def _heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _astar(self, start, goal):
        # simple A* implementation
        open_set = {start}
        came_from = {}
        gscore = {start: 0}
        fscore = {start: self._heuristic(start, goal)}

        while open_set:
            current = min(open_set, key=lambda n: fscore.get(n, 1e9))
            if current == goal:
                # reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            open_set.remove(current)
            for neighbor in self._neighbors(current):
                tentative_g = gscore[current] + 1
                if tentative_g < gscore.get(neighbor, 1e9):
                    came_from[neighbor] = current
                    gscore[neighbor] = tentative_g
                    fscore[neighbor] = tentative_g + self._heuristic(neighbor, goal)
                    open_set.add(neighbor)
        return None

    def hsv_to_rgb(self, h, s, v):
        # same conversion as other modules
        h = h / 60.0
        hi = int(h) % 6
        f = h - int(h)
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        if hi == 0:
            return [int(v * 255), int(t * 255), int(p * 255)]
        elif hi == 1:
            return [int(q * 255), int(v * 255), int(p * 255)]
        elif hi == 2:
            return [int(p * 255), int(v * 255), int(t * 255)]
        elif hi == 3:
            return [int(p * 255), int(q * 255), int(v * 255)]
        elif hi == 4:
            return [int(t * 255), int(p * 255), int(v * 255)]
        else:
            return [int(v * 255), int(p * 255), int(q * 255)]

    def get(self):
        changes = []

        # on first call, return full frame (matrix)
        if self._first:
            # generate full frame with wall colors and open as black
            frame = [[helpers.colors_rgb['black'] for _ in range(self.yres)] for _ in range(self.xres)]
            # color walls using cycling hues
            palette_len = max(6, len(self.walls))
            for idx, (x, y) in enumerate(self.walls):
                hue = ((idx + self.hue_offset) % palette_len) * (360.0 / palette_len)
                rgb = self.hsv_to_rgb(hue, 0.7, 0.6)
                frame[x][y] = rgb
            # mark entrance and exit with dim colors so they are visible
            frame[self.entrance[0]][self.entrance[1]] = helpers.colors_rgb['green']
            frame[self.exit[0]][self.exit[1]] = helpers.colors_rgb['blue']

            self._first = False
            self.hue_offset = (self.hue_offset + 1) % 360
            return True, self.delay, frame

        # update hue offset and recolor walls (we will emit color updates)
        palette_len = max(6, len(self.walls))
        self.hue_offset = (self.hue_offset + 1) % palette_len
        for coord, i in self.wall_index.items():
            x, y = coord
            hue = ((i + self.hue_offset) % palette_len) * (360.0 / palette_len)
            rgb = self.hsv_to_rgb(hue, 0.7, 0.6)
            changes.append([x, y, rgb])

        # decay existing glows (red halos left behind)
        for coord in list(self.glows.keys()):
            x, y = coord
            intensity = self.glows[coord] - self.glow_step
            if intensity <= 0:
                del self.glows[coord]
                # restore base color (wall / entrance/exit / black)
                if coord in self.wall_index:
                    i = self.wall_index[coord]
                    hue = ((i + self.hue_offset) % palette_len) * (360.0 / palette_len)
                    base = self.hsv_to_rgb(hue, 0.7, 0.6)
                elif coord == self.entrance:
                    base = helpers.colors_rgb['green']
                elif coord == self.exit:
                    base = helpers.colors_rgb['blue']
                else:
                    base = helpers.colors_rgb['black']
                changes.append([x, y, base])
            else:
                self.glows[coord] = intensity
                glow_rgb = [int(intensity), 0, 0]
                changes.append([x, y, glow_rgb])

        # If we are at the end and pausing, keep the red pixel at the exit until pause expires
        if getattr(self, 'at_end', False):
            now = time.time()
            if now < self.pause_until:
                # ensure red pixel remains visible at end
                endx, endy = self.path[-1]
                changes.append([endx, endy, helpers.colors_rgb['red']])
                return False, self.delay, changes
            else:
                # pause expired -> create new solvable maze and return full frame
                self._create_solvable_maze()
                # build full frame like on first draw
                frame = [[helpers.colors_rgb['black'] for _ in range(self.yres)] for _ in range(self.xres)]
                palette_len2 = max(6, len(self.walls))
                for idx, (x, y) in enumerate(self.walls):
                    hue = ((idx + self.hue_offset) % palette_len2) * (360.0 / palette_len2)
                    rgb = self.hsv_to_rgb(hue, 0.7, 0.6)
                    frame[x][y] = rgb
                sx, sy = self.entrance
                ex, ey = self.exit
                frame[sx][sy] = helpers.colors_rgb['green']
                frame[ex][ey] = helpers.colors_rgb['blue']
                return True, self.delay, frame

        # move the red pixel along the path
        if self.path:
            prev_idx = max(0, self.head_idx - 1)
            prev = self.path[prev_idx]
            # set a new glow at the previous pixel (it will fade over frames)
            self.glows[prev] = self.glow_start
            changes.append([prev[0], prev[1], [self.glow_start, 0, 0]])

            # current head position
            cur = self.path[self.head_idx]
            changes.append([cur[0], cur[1], helpers.colors_rgb['red']])

            # advance head only if not in end state
            self.head_idx += 1
            if self.head_idx >= len(self.path):
                # reached the end -> set pause, keep red pixel for a moment
                self.head_idx = len(self.path) - 1
                self.at_end = True
                self.pause_until = time.time() + self.pause_duration
                return False, self.delay, changes

        return False, self.delay, changes
