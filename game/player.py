import pygame
from game.world import TILE
from config import CFG

_P = CFG["player"]

class Player:
    SIZE = 20             # hitbox in pixels (smaller than a tile so gaps are passable)
    WALK_SPEED = _P["walk_speed"]
    SPRINT_SPEED = _P["sprint_speed"]
    MAX_STAMINA = _P["max_stamina"]
    DRAIN = _P["stamina_drain"]
    REGEN = _P["stamina_regen"]
    RECOVER_AT = _P["recover_at"]

    def __init__(self, spawn_tile):
        col, row = spawn_tile
        self.pos = pygame.Vector2(col * TILE + TILE / 2, row * TILE + TILE / 2)
        self.rect = pygame.Rect(0, 0, self.SIZE, self.SIZE)
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.stamina = self.MAX_STAMINA
        self.exhausted = False
        self.sprinting = False
        self.moving = False
        self.hidden = False

    def update(self, dt, keys, world):

               # 1. read input -> direction vector
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        if self.hidden:
            dx = dy = 0   # can't move (or sprint) while hiding

        direction = pygame.Vector2(dx, dy)
        moving = direction.length() > 0
        self.moving = moving
        if moving:
            direction = direction.normalize()  # so diagonals aren't faster

                  # 2. sprint / stamina
        wants_sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        self.sprinting = bool(wants_sprint and moving and not self.exhausted and self.stamina > 0)
        if self.sprinting:
            self.stamina = max(0, self.stamina - self.DRAIN * dt)
            if self.stamina == 0:
                self.exhausted = True
        else:
            self.stamina = min(self.MAX_STAMINA, self.stamina + self.REGEN * dt)
            if self.exhausted and self.stamina >= self.RECOVER_AT:
                self.exhausted = False

                   # 3. move one axis at a time, resolving collisions after each
        speed = self.SPRINT_SPEED if self.sprinting else self.WALK_SPEED
        self._move_axis(0, direction.x * speed * dt, world)
        self._move_axis(1, direction.y * speed * dt, world)

    def toggle_hide(self, world):
        """E key: hide in the bush you're standing on, or come out of it."""
        if self.hidden:
            self.hidden = False
            return
        col, row = int(self.pos.x // TILE), int(self.pos.y // TILE)
        if world.tile_at(col, row) == "B":
            self.hidden = True



    
    @property
    def noise_radius(self):
        """How far the player's footsteps carry right now (pixels)."""
        if not self.moving:
            return 0
        return _P["noise_sprint"] if self.sprinting else _P["noise_walk"]

    
    def _move_axis(self, axis, amount, world):
        if amount == 0:
            return
        if axis == 0:
            self.pos.x += amount
        else:
            self.pos.y += amount
        self.rect.center = (round(self.pos.x), round(self.pos.y))

        # check every tile the hitbox overlaps
        for c in range(self.rect.left // TILE, (self.rect.right - 1) // TILE + 1):
            for r in range(self.rect.top // TILE, (self.rect.bottom - 1) // TILE + 1):
                if world.is_walkable(c, r):
                    continue
                tile = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                if axis == 0:
                    if amount > 0:
                        self.rect.right = tile.left
                    else:
                        self.rect.left = tile.right
                    self.pos.x = self.rect.centerx
                else:
                    if amount > 0:
                        self.rect.bottom = tile.top
                    else:
                        self.rect.top = tile.bottom
                    self.pos.y = self.rect.centery