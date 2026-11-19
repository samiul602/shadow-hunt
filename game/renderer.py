import pygame
from game.world import TILE

# Placeholder colors, we'll swap in real sprites later
COLORS = {
    ".": (60, 110, 55),    # grass
    "S": (60, 110, 55),    # spawn (looks like grass)
    "T": (20, 70, 30),     # tree
    "R": (110, 110, 115),  # rock
    "B": (40, 150, 60),    # bush
    "C": (120, 80, 45),    # cabin
    "E": (230, 200, 50),   # exit gate
    "D": (80, 50, 25),     # cabin door
}


def draw_world(screen, world):
    for r in range(world.rows):
        for c in range(world.cols):
            ch = world.grid[r][c]
            rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
            color = COLORS[ch]
            if ch == "E" and world.gate_open:
                color = (80, 220, 90)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 1)  # faint grid line

def draw_player(screen, player):
    color = (255, 220, 120) if player.sprinting else (240, 240, 240)
    pygame.draw.rect(screen, color, player.rect)
    pygame.draw.rect(screen, (0, 0, 0), player.rect, 2)


def draw_stamina_bar(screen, player, x=990, y=20, w=240, h=18):
    pygame.draw.rect(screen, (50, 50, 50), (x, y, w, h))
    ratio = player.stamina / player.MAX_STAMINA
    color = (200, 60, 60) if player.exhausted else (80, 200, 255)
    pygame.draw.rect(screen, color, (x, y, int(w * ratio), h))
    pygame.draw.rect(screen, (255, 255, 255), (x, y, w, h), 2)

_fonts = {}


def get_font(size):
    """Fonts can only be created after pygame.init(), so create lazily and cache."""
    if size not in _fonts:
        _fonts[size] = pygame.font.Font(None, size)
    return _fonts[size]


def draw_keys(screen, world):
    for (c, r) in world.keys:
        center = (c * TILE + TILE // 2, r * TILE + TILE // 2)
        pygame.draw.circle(screen, (255, 215, 0), center, 9)
        pygame.draw.circle(screen, (0, 0, 0), center, 9, 2)


def draw_key_counter(screen, world, x=990, y=48):
    text = f"Keys: {world.keys_collected} / {world.total_keys}"
    screen.blit(get_font(32).render(text, True, (255, 215, 0)), (x, y))


def draw_message(screen, title, subtitle, color=(255, 255, 255)):
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))
    cx, cy = screen.get_width() // 2, screen.get_height() // 2
    t = get_font(96).render(title, True, color)
    s = get_font(36).render(subtitle, True, (220, 220, 220))
    screen.blit(t, t.get_rect(center=(cx, cy - 20)))
    screen.blit(s, s.get_rect(center=(cx, cy + 50)))    