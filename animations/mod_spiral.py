import random
import time
from array import array


min_delay = 1
max_delay = 4

class Spiral:
    def __init__(self, xres, yres, delay=0.01):
        self.xres = xres
        self.yres = yres
        self.path = self._compute_spiral_path(xres, yres)
        self.delay = delay

        # Actors: multiple simultaneous "heads" that either draw (color) or erase (black)
        # Each actor: {'type': 'draw'|'erase', 'idx': int, 'hue': int(only for draw)}
        self.actors = []

        # Start with one drawing marker
        self.spawn_draw()

        # Schedule alternating events (erase / new marker) every random interval
        self.next_event_time = time.time() + random.uniform(min_delay, max_delay)
        self.next_is_erase = True  # alternate between erase and spawn draw

        # Event guard: prevent re-entrant handling and rapid retriggers
        self._in_event = False
        self.last_event_time = 0.0

    def _compute_spiral_path(self, w, h):
        # Generate coordinates following a clockwise spiral from outer frame to center
        left, top = 0, 0
        right, bottom = w - 1, h - 1
        path = array('H')
        while left <= right and top <= bottom:
            # top row (left->right)
            for x in range(left, right + 1):
                path.append(x * h + top)
            # right column (top+1->bottom)
            for y in range(top + 1, bottom + 1):
                path.append(right * h + y)
            if top < bottom:
                # bottom row (right-1->left)
                for x in range(right - 1, left - 1, -1):
                    path.append(x * h + bottom)
            if left < right:
                # left column (bottom-1->top+1)
                for y in range(bottom - 1, top, -1):
                    path.append(left * h + y)
            left += 1
            right -= 1
            top += 1
            bottom -= 1
        return path

    def spawn_draw(self):
        if len(self.actors) >= 4:
            return
        actor = {'type': 'draw', 'idx': 0, 'hue': random.randint(0, 119)}
        self.actors.append(actor)

    def spawn_erase(self):
        if len(self.actors) >= 4:
            return
        actor = {'type': 'erase', 'idx': 0}
        self.actors.append(actor)

    def get(self):
        # Manage timed events: alternate spawn erase / spawn draw every 2..8 seconds
        now = time.time()
        if now >= self.next_event_time:
            # Debounce: skip if we just fired an event very recently
            if now - self.last_event_time < 0.05:
                # Too soon after previous event; skip
                pass
            elif self._in_event:
                # Re-entrant; skip
                pass
            else:
                self._in_event = True
                try:
                    # Use an integer interval and reserve next event time
                    interval = random.randint(min_delay, max_delay)
                    self.next_event_time = now + interval
                    self.last_event_time = now
                    if self.next_is_erase:
                        self.spawn_erase()
                    else:
                        self.spawn_draw()
                    self.next_is_erase = not self.next_is_erase
                finally:
                    self._in_event = False

        changes = []
        if not self.path:
            return False, self.delay, []

        # Compact completed actors in place.
        for i in range(len(self.actors) - 1, -1, -1):
            if self.actors[i]['idx'] >= len(self.path):
                del self.actors[i]
        # Emit draw updates first, erasures last, without sorting/copying lists.
        for kind in ('draw', 'erase'):
            for actor in self.actors:
                if actor['type'] != kind:
                    continue
                pixel = self.path[actor['idx']]
                x, y = pixel // self.yres, pixel % self.yres
                if kind == 'draw':
                    raw = actor['hue'] % 120
                    hue = raw if raw < 60 else raw + 240
                    rgb = self.hsv_to_rgb(hue, 0.9, 0.6)
                    actor['hue'] = (actor['hue'] + 1) % 120
                else:
                    rgb = (0, 0, 0)
                changes.append((x, y, rgb))
                actor['idx'] += 1
        return False, self.delay, changes

    def hsv_to_rgb(self, h, s, v):
        # Same conversion used in other modules
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
