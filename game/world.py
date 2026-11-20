import pygame

TILE = 32  # pixels per grid cell

# Tiles the player/hunter can always walk on (the gate 'E' is conditional)
WALKABLE = {".", "B", "S", "D"}
VISION_BLOCKERS = {"T", "R", "C"}   # trees, rocks, cabin walls


class World:
    def __init__(self, map_path):
        self.grid = []
        self.spawn = (1, 1)       # (col, row), overwritten if 'S' is found
        self.keys = []            # (col, row) of keys not yet collected
        self.keys_collected = 0
        self.gate_open = False
        self._load(map_path)
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.total_keys = len(self.keys)

    def _load(self, map_path):
        """Read the text map into a list of rows (each row is a list of chars)."""
        with open(map_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip().replace(" ", "")
                if line:
                    self.grid.append(list(line))

        # sanity check: every row must have the same width
        width = len(self.grid[0])
        for r, row in enumerate(self.grid):
            if len(row) != width:
                raise ValueError(f"Map row {r} has {len(row)} cells, expected {width}")

        # find the spawn tile and key spots
        for r, row in enumerate(self.grid):
            for c, ch in enumerate(row):
                if ch == "S":
                    self.spawn = (c, r)
                elif ch == "K":
                    self.keys.append((c, r))
                    row[c] = "."  # keys are objects; the tile underneath is grass

    def tile_at(self, col, row):
        """Return the tile character, or 'T' (blocked) if outside the map."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col]
        return "T"

    def is_walkable(self, col, row):
        tile = self.tile_at(col, row)
        if tile == "E":
            return self.gate_open  # gate only passable once all keys are collected
        return tile in WALKABLE

    
    def blocks_vision(self, col, row):
        return self.tile_at(col, row) in VISION_BLOCKERS

    
    def collect_keys(self, player_rect):
        """Pick up any key the player is touching. Opens the gate at the last one."""
        for (c, r) in self.keys[:]:
            key_rect = pygame.Rect(c * TILE + 8, r * TILE + 8, TILE - 16, TILE - 16)
            if player_rect.colliderect(key_rect):
                self.keys.remove((c, r))
                self.keys_collected += 1
        if self.keys_collected == self.total_keys:
            self.gate_open = True