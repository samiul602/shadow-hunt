import math
from ai.astar import astar
from ai.perception import check_vision, hear_noises

PATROL, ALERT, CHASE, SEARCH, RETURN = "PATROL", "ALERT", "CHASE", "SEARCH", "RETURN"


class Hunter:
    # perception
    VISION_RANGE = 160    # pixels (5 tiles)
    FOV_DEG = 90          # total field of view in degrees

    # speed per state (pixels / second)
    SPEEDS = {PATROL: 90, ALERT: 100, CHASE: 140, SEARCH: 100, RETURN: 100}

    # timers (seconds)
    WAIT_AT_POINT = 1.0       # pause at each patrol point
    LOOK_AROUND_TIME = 1.5    # pause while investigating a spot
    LOSE_SIGHT_TIME = 1.0     # keep chasing this long after losing sight
    SEARCH_TIME = 8.0         # how long to search before giving up
    REPATH_TIME = 0.4         # how often CHASE recomputes A*
    NEW_NOISE_DIST = 40       # a noise this far from the current target retargets ALERT

    def __init__(self, start_tile, patrol_points, tile_size):
        self.tile = tile_size
        self.x = start_tile[0] * tile_size + tile_size / 2   # pixel position
        self.y = start_tile[1] * tile_size + tile_size / 2
        self.speed = self.SPEEDS[PATROL]
        self.patrol_points = patrol_points
        self.patrol_index = 0

        # movement
        self.path = []             # tiles still to walk (next tile first)
        self.wait_timer = 0.0
        self.facing = 0.0          # radians, 0 = east

        # FSM
        self.state = PATROL
        self.reason = "Patrolling"   # why we are in this state (for the AI panel later)

        # perception + memory
        self.vision = None
        self.sees_player = False
        self.last_known_pos = None   # where the player was last SEEN
        self.heard = None            # loudest noise heard this frame (or None)
        self.last_heard_pos = None   # where the last noise came from

        # state-specific data
        self.lost_sight_timer = 0.0
        self.repath_timer = 0.0
        self.alert_target = None
        self.alert_arrived = False
        self.search_timer = 0.0
        self.search_points = []
        self.search_index = 0

    # ------------------------------------------------------------ helpers
    def tile_pos(self):
        return (int(self.x // self.tile), int(self.y // self.tile))

    def _tile_of(self, pos):
        return (int(pos[0] // self.tile), int(pos[1] // self.tile))

    def _far(self, a, b, dist):
        return math.hypot(a[0] - b[0], a[1] - b[1]) > dist

    def has_caught(self, player_pos, radius=22):
        return math.hypot(self.x - player_pos[0], self.y - player_pos[1]) < radius

    # ------------------------------------------------------------ perception
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

    # ------------------------------------------------------------ main update
    def update(self, dt, walkable):
        self._check_transitions(dt, walkable)      # 1. FSM: should we change state?
        self.speed = self.SPEEDS[self.state]
        handlers = {PATROL: self._patrol, ALERT: self._alert, CHASE: self._chase,
                    SEARCH: self._search, RETURN: self._return}
        handlers[self.state](dt, walkable)         # 2. do what the current state says

    # ------------------------------------------------------------ transitions
    def _set_state(self, state, reason):
        self.state = state
        self.reason = reason
        self.path = []
        self.wait_timer = 0.0
        self.repath_timer = 0.0

    def _check_transitions(self, dt, walkable):
        # 1. seeing the player always means CHASE
        if self.sees_player:
            self.lost_sight_timer = 0.0
            if self.state != CHASE:
                self._set_state(CHASE, "Player spotted")
            return

        # 2. in CHASE, keep going a moment after losing sight, then SEARCH
        if self.state == CHASE:
            self.lost_sight_timer += dt
            if self.lost_sight_timer >= self.LOSE_SIGHT_TIME:
                self._enter_search(walkable)
            return

        # 3. a noise means ALERT (unless we're already heading to that spot)
        if self.heard:
            pos = self.heard["pos"]
            if self.state != ALERT or self._far(pos, self.alert_target, self.NEW_NOISE_DIST):
                self._start_alert(pos, walkable)

    def _start_alert(self, pos, walkable):
        self._set_state(ALERT, "Heard a noise")
        self.alert_target = pos
        self.alert_arrived = False
        self._plan_to(self._tile_of(pos), walkable)

    def _enter_search(self, walkable):
        self._set_state(SEARCH, "Lost sight of the player")
        self.search_timer = self.SEARCH_TIME
        bx, by = self._tile_of(self.last_known_pos)
        # last known tile first, then 4 spots around it
        self.search_points = [(bx, by), (bx + 3, by), (bx, by + 3), (bx - 3, by), (bx, by - 3)]
        self.search_index = 0
        self._plan_to(self.search_points[0], walkable)

    def _start_return(self, walkable, reason):
        self._set_state(RETURN, reason)
        # go back to the nearest patrol point and continue the route from there
        def dist_to(i):
            px = self.patrol_points[i][0] * self.tile + self.tile / 2
            py = self.patrol_points[i][1] * self.tile + self.tile / 2
            return math.hypot(px - self.x, py - self.y)
        self.patrol_index = min(range(len(self.patrol_points)), key=dist_to)
        self._plan_to(self.patrol_points[self.patrol_index], walkable)

    # ------------------------------------------------------------ state behaviors
    def _patrol(self, dt, walkable):
        if self.wait_timer > 0:
            self.wait_timer -= dt
            return
        if self.path:
            self._follow_path(dt)
            return
        target = self.patrol_points[self.patrol_index]
        if self.tile_pos() == target:
            # arrived: pause, then aim for the next patrol point
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
            self.wait_timer = self.WAIT_AT_POINT
        elif not self._plan_to(target, walkable):
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)

    def _alert(self, dt, walkable):
        if self.alert_arrived:
            # look around at the noise spot, then give up
            self.wait_timer -= dt
            self.facing += 2.0 * dt
            if self.wait_timer <= 0:
                self._start_return(walkable, "Nothing found at the noise")
            return
        if self.path:
            self._follow_path(dt)
            return
        self.alert_arrived = True
        self.wait_timer = self.LOOK_AROUND_TIME

    def _chase(self, dt, walkable):
        self.repath_timer -= dt
        if self.repath_timer <= 0 and self.last_known_pos:
            self._plan_to(self._tile_of(self.last_known_pos), walkable)
            self.repath_timer = self.REPATH_TIME
        if self.path:
            self._follow_path(dt)

    def _search(self, dt, walkable):
        self.search_timer -= dt
        if self.search_timer <= 0:
            self._start_return(walkable, "Search timed out")
            return
        if self.wait_timer > 0:            # looking around at a search point
            self.wait_timer -= dt
            self.facing += 2.0 * dt
            return
        if self.path:
            self._follow_path(dt)
            return
        # reached a search point: look around, then plan the next one
        self.wait_timer = self.LOOK_AROUND_TIME
        self.search_index = (self.search_index + 1) % len(self.search_points)
        self._plan_to(self.search_points[self.search_index], walkable)

    def _return(self, dt, walkable):
        if self.path:
            self._follow_path(dt)
        else:
            self._set_state(PATROL, "Back on patrol route")

    # ------------------------------------------------------------ movement
    def _nearest_walkable(self, tile, walkable, max_r=6):
        """If the wanted tile is blocked (e.g. a stone landed on a tree), find the closest free one."""
        for r in range(max_r + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) == r and walkable(tile[0] + dx, tile[1] + dy):
                        return (tile[0] + dx, tile[1] + dy)
        return None

    def _plan_to(self, tile, walkable):
        """Ask A* for a route; drop the first tile because we're already standing on it."""
        goal = self._nearest_walkable(tile, walkable)
        if goal is None:
            self.path = []
            return False
        path, _ = astar(walkable, self.tile_pos(), goal)
        self.path = path[1:] if path else []
        return bool(path)

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