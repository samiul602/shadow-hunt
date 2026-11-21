import math
from ai.perception import check_vision
from ai.astar import astar
from ai.perception import check_vision, hear_noises


class Hunter:
    WAIT_AT_POINT = 1.0   # seconds to pause at each patrol point
    VISION_RANGE = 160    # pixels (5 tiles)
    FOV_DEG = 90          # total field of view in degrees

    def __init__(self, start_tile, patrol_points, tile_size, speed=90):
        self.tile = tile_size
        self.x = start_tile[0] * tile_size + tile_size / 2   # pixel position
        self.y = start_tile[1] * tile_size + tile_size / 2
        self.speed = speed                                   # pixels / second
        self.patrol_points = patrol_points
        self.patrol_index = 0
        self.path = []          # tiles still to walk (next tile first)
        self.wait_timer = 0.0
        self.state = "PATROL"   # the FSM will take over this later
        self.facing = 0.0            # radians, 0 = east
        self.vision = None           # latest check_vision() result
        self.sees_player = False
        self.last_known_pos = None   # memory: where the player was last seen
        self.heard = None            # loudest noise heard this frame (or None)
        self.last_heard_pos = None   # memory: where the last noise came from


    def tile_pos(self):
        return (int(self.x // self.tile), int(self.y // self.tile))
  
  
    def perceive(self, player_pos, blocks_vision):
        """Look for the player. Remembers where they were last seen."""
        self.vision = check_vision((self.x, self.y), self.facing, player_pos,
                                   self.FOV_DEG, self.VISION_RANGE, self.tile, blocks_vision)
        self.sees_player = self.vision["visible"]
        if self.sees_player:
            self.last_known_pos = player_pos
    def hear(self, noises):
        """Listen for noises. Remembers where the last one came from."""
        self.heard = hear_noises((self.x, self.y), noises)
        if self.heard:
            self.last_heard_pos = self.heard["pos"]


    def update(self, dt, walkable):
        if self.wait_timer > 0:
            self.wait_timer -= dt
            return

        if not self.path:
            target = self.patrol_points[self.patrol_index]
            if self.tile_pos() == target:
                # arrived: pause, then aim for the next patrol point
                self._next_patrol_point()
                self.wait_timer = self.WAIT_AT_POINT
            else:
                self._plan_path(target, walkable)
            return

        self._follow_path(dt)

    def _next_patrol_point(self):
        self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)

    def _plan_path(self, goal, walkable):
        """Ask A* for a route; drop the first tile because we're already standing on it."""
        path, _ = astar(walkable, self.tile_pos(), goal)
        if path:
            self.path = path[1:]
        else:
            self._next_patrol_point()   # unreachable point: skip it

    def _follow_path(self, dt):
        """Walk toward the center of the next tile; carry leftover movement to the following one."""
        step = self.speed * dt
        while step > 0 and self.path:
            tx = self.path[0][0] * self.tile + self.tile / 2
            ty = self.path[0][1] * self.tile + self.tile / 2
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.facing = math.atan2(dy, dx)   # face the direction of travel
            if dist <= step:
                self.x, self.y = tx, ty
                self.path.pop(0)
                step -= dist
            else:
                self.x += dx / dist * step
                self.y += dy / dist * step
                step = 0