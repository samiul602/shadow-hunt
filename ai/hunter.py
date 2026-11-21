import math
from ai import utility
from ai.astar import astar
from ai.perception import check_vision, hear_noises

PATROL, ALERT, CHASE, SEARCH, RETURN = "PATROL", "ALERT", "CHASE", "SEARCH", "RETURN"

# which utility action each FSM state is carrying out
STATE_ACTION = {PATROL: utility.PATROL, RETURN: utility.PATROL, ALERT: utility.INVESTIGATE,
                CHASE: utility.CHASE, SEARCH: utility.SEARCH}


class Hunter:
    # perception
    VISION_RANGE = 160    # pixels (5 tiles)
    FOV_DEG = 90          # total field of view in degrees

    # speed per state (pixels / second)
    SPEEDS = {PATROL: 90, ALERT: 100, CHASE: 140, SEARCH: 100, RETURN: 100}

    # timers (seconds)
    WAIT_AT_POINT = 1.0       # pause at each patrol point
    LOOK_AROUND_TIME = 1.5    # pause while investigating a spot
    LOSE_SIGHT_TIME = 1.0     # "recent contact" window after losing sight
    SEARCH_TIME = 8.0         # hard limit for one search
    REPATH_TIME = 0.4         # how often CHASE recomputes A*
    MEMORY_TIME = 12.0        # memory of the player's position fades over this long
    SUSPICION_DECAY = 0.1     # suspicion lost per second
    NEW_NOISE_DIST = 40       # a noise this far from the current target retargets ALERT
    # HIDE_DETECT_DIST = 40     # a hidden player is only noticed this close (pixels)
    HIDE_DETECT_DIST = 24     # a hidden player is only noticed this close (pixels)
    def __init__(self, start_tile, patrol_points, tile_size, hiding_spots=()):
        self.hiding_spots = list(hiding_spots)
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
        self.reason = "Patrolling"

        # utility AI
        self.scores = {utility.CHASE: 0.0, utility.INVESTIGATE: 0.0,
                       utility.SEARCH: 0.0, utility.PATROL: 0.0}
        self.action = utility.PATROL
        self.suspicion = 0.0          # 0..1

        # perception + memory
        self.vision = None
        self.sees_player = False
        self.last_known_pos = None    # where the player was last SEEN
        self.time_since_seen = 999.0
        self.memory_consumed = False  # True once we've already searched that memory
        self.heard = None             # loudest noise heard this frame (or None)
        self.last_heard_pos = None

        # state-specific data
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
    def perceive(self, player_pos, blocks_vision, player_hidden=False):
        """Look for the player. Remembers where they were last seen."""
        self.vision = check_vision((self.x, self.y), self.facing, player_pos,
                                   self.FOV_DEG, self.VISION_RANGE, self.tile, blocks_vision)
        self.vision["hidden"] = player_hidden
        if player_hidden:
            # a hidden player is only found by a hunter standing right next to them
            self.vision["visible"] = self.vision["distance"] < self.HIDE_DETECT_DIST
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
        self._update_memory_and_suspicion(dt)
        self._decide(walkable)                     # utility picks an action -> FSM changes state
        self.speed = self.SPEEDS[self.state]
        handlers = {PATROL: self._patrol, ALERT: self._alert, CHASE: self._chase,
                    SEARCH: self._search, RETURN: self._return}
        handlers[self.state](dt, walkable)         # do what the current state says

    # ------------------------------------------------------------ decision making
    def _update_memory_and_suspicion(self, dt):
        if self.sees_player:
            self.time_since_seen = 0.0
            self.memory_consumed = False
        else:
            self.time_since_seen += dt

        gain = 0.0
        if self.sees_player:
            gain += 1.5
        if self.heard:
            gain += 0.6 * self.heard["intensity"]
        self.suspicion += (gain - self.SUSPICION_DECAY) * dt
        self.suspicion = max(0.0, min(1.0, self.suspicion))

    def _gather_inputs(self):
        """Turn what the hunter knows into the 0..1 inputs the utility system expects."""
        proximity = 0.0
        if self.sees_player and self.vision:
            proximity = max(0.0, 1.0 - self.vision["distance"] / self.VISION_RANGE)

        memory = 0.0
        if self.last_known_pos is not None and not self.memory_consumed:
            memory = max(0.0, 1.0 - self.time_since_seen / self.MEMORY_TIME)

        recent = 1.0 if (self.last_known_pos is not None
                         and self.time_since_seen < self.LOSE_SIGHT_TIME) else 0.0

        return {
            "visible": self.sees_player,
            "proximity": proximity,
            "sound": self.heard["intensity"] if self.heard else 0.0,
            "memory": memory,
            "recent_contact": recent,
            "suspicion": self.suspicion,
            "pending_investigation": self.state == ALERT,
        }

    def _decide(self, walkable):
        current = STATE_ACTION[self.state]
        self.scores = utility.score_actions(self._gather_inputs(), current)
        best = utility.choose_action(self.scores)
        self.action = best

        if best == current:
            # same action, but a new and distant noise retargets the investigation
            if (best == utility.INVESTIGATE and self.heard
                    and self._far(self.heard["pos"], self.alert_target, self.NEW_NOISE_DIST)):
                self._start_alert(self.heard["pos"], walkable)
            return

        if best == utility.CHASE:
            self._set_state(CHASE, "Player visible")
        elif best == utility.INVESTIGATE:
            self._start_alert(self.heard["pos"], walkable)
        elif best == utility.SEARCH:
            self._enter_search(walkable)
        else:
            self._start_return(walkable, "Nothing to follow up")

    # ------------------------------------------------------------ state changes
    def _set_state(self, state, reason):
        if self.state == SEARCH and state not in (SEARCH, CHASE):
            self.memory_consumed = True    # we already acted on that memory
        self.state = state
        self.reason = reason
        self.path = []
        self.wait_timer = 0.0
        self.repath_timer = 0.0

    def _start_alert(self, pos, walkable):
        self._set_state(ALERT, "Heard a noise")
        self.alert_target = pos
        self.alert_arrived = False
        self._plan_to(self._tile_of(pos), walkable)

    def _enter_search(self, walkable):
        self._set_state(SEARCH, "Lost sight of the player")
        self.search_timer = self.SEARCH_TIME
        base = self._tile_of(self.last_known_pos)

        # check the last known tile first, then the nearest hiding places around it
        bushes = [b for b in self.hiding_spots
                  if b != base and math.hypot(b[0] - base[0], b[1] - base[1]) <= 6]
        bushes.sort(key=lambda b: math.hypot(b[0] - base[0], b[1] - base[1]))
        self.search_points = [base] + bushes[:3]

        # fill up with spots around the last known tile if there aren't enough bushes
        for dx, dy in ((3, 0), (0, 3), (-3, 0), (0, -3)):
            if len(self.search_points) >= 5:
                break
            self.search_points.append((base[0] + dx, base[1] + dy))

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