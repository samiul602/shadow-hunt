import pygame
import math
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
    if player.hidden:
        color = (30, 90, 45)   # blends into the bush
    else:
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


def draw_hunter(screen, hunter):
    rect = pygame.Rect(0, 0, 22, 22)
    rect.center = (round(hunter.x), round(hunter.y))
    pygame.draw.rect(screen, (200, 40, 40), rect)
    pygame.draw.rect(screen, (0, 0, 0), rect, 2)


def draw_debug(screen, hunter):
    """Patrol points (blue rings) and the hunter's current A* path (orange line)."""
    for (c, r) in hunter.patrol_points:
        center = (c * TILE + TILE // 2, r * TILE + TILE // 2)
        pygame.draw.circle(screen, (80, 160, 255), center, 6, 2)
    if hunter.path:
        pts = [(round(hunter.x), round(hunter.y))]
        pts += [(c * TILE + TILE // 2, r * TILE + TILE // 2) for c, r in hunter.path]
        if len(pts) > 1:
            pygame.draw.lines(screen, (255, 140, 0), False, pts, 2)

    if hunter.last_known_pos:
        x, y = (round(v) for v in hunter.last_known_pos)
        pygame.draw.line(screen, (255, 0, 255), (x - 6, y - 6), (x + 6, y + 6), 2)
        pygame.draw.line(screen, (255, 0, 255), (x - 6, y + 6), (x + 6, y - 6), 2) 

    if hunter.last_heard_pos:
        x, y = (round(v) for v in hunter.last_heard_pos)
        pygame.draw.line(screen, (0, 255, 255), (x - 6, y - 6), (x + 6, y + 6), 2)
        pygame.draw.line(screen, (0, 255, 255), (x - 6, y + 6), (x + 6, y - 6), 2)      

def draw_vision_cone(screen, hunter, world):
    """Cone of rays, each one stopping at the first vision-blocking tile."""
    cx, cy = hunter.x, hunter.y
    half = math.radians(hunter.FOV_DEG) / 2
    rays = 24
    points = [(cx, cy)]
    for i in range(rays + 1):
        angle = hunter.facing - half + (2 * half) * i / rays
        dist = 0
        while dist < hunter.VISION_RANGE:
            nd = dist + 4
            px = cx + math.cos(angle) * nd
            py = cy + math.sin(angle) * nd
            if world.blocks_vision(int(px // TILE), int(py // TILE)):
                break
            dist = nd
        points.append((cx + math.cos(angle) * dist, cy + math.sin(angle) * dist))

    color = (255, 60, 60, 80) if hunter.sees_player else (255, 255, 120, 55)
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(overlay, color, points)
    screen.blit(overlay, (0, 0))


def draw_alert_mark(screen, hunter):
    if hunter.sees_player:
        symbol, color = "!", (255, 50, 50)
    elif hunter.heard:
        symbol, color = "?", (255, 190, 40)
    else:
        return
    t = get_font(40).render(symbol, True, color)
    screen.blit(t, t.get_rect(center=(round(hunter.x), round(hunter.y) - 24)))    
    
            
def draw_noise(screen, player, stone_noises):
    """Rings showing how far the player's footsteps and thrown stones carry."""
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    if player.noise_radius > 0:
        center = (round(player.pos.x), round(player.pos.y))
        pygame.draw.circle(overlay, (255, 255, 255, 70), center, player.noise_radius, 2)
    for s in stone_noises:
        center = (round(s["pos"][0]), round(s["pos"][1]))
        pygame.draw.circle(overlay, (120, 200, 255, 170), center, s["radius"], 2)
        pygame.draw.circle(overlay, (120, 200, 255, 230), center, 5)
    screen.blit(overlay, (0, 0))



STATE_COLORS = {
    "PATROL": (120, 200, 255),
    "ALERT": (255, 190, 40),
    "CHASE": (255, 60, 60),
    "SEARCH": (255, 140, 0),
    "RETURN": (160, 255, 160),
}


def draw_state_label(screen, hunter):
    t = get_font(22).render(hunter.state, True, STATE_COLORS[hunter.state])
    screen.blit(t, t.get_rect(center=(round(hunter.x), round(hunter.y) + 24)))


ACTION_ORDER = ["CHASE", "INVESTIGATE", "SEARCH", "PATROL"]


def draw_ai_panel(screen, hunter, x=990, y=90):
    white, grey = (255, 255, 255), (190, 190, 190)

    screen.blit(get_font(30).render("HUNTER AI", True, white), (x, y))
    y += 36
    screen.blit(get_font(28).render(f"State: {hunter.state}", True, STATE_COLORS[hunter.state]), (x, y))
    y += 28
    screen.blit(get_font(22).render(hunter.reason, True, grey), (x, y))
    y += 34

    # suspicion bar
    screen.blit(get_font(22).render("Suspicion", True, grey), (x, y))
    pygame.draw.rect(screen, (50, 50, 50), (x + 110, y + 2, 120, 14))
    pygame.draw.rect(screen, (230, 120, 60), (x + 110, y + 2, int(120 * hunter.suspicion), 14))
    y += 36

    # utility scores: the chosen action is highlighted
    screen.blit(get_font(24).render("Utility scores", True, white), (x, y))
    y += 28
    for action in ACTION_ORDER:
        score = hunter.scores[action]
        picked = action == hunter.action
        screen.blit(get_font(22).render(action, True, white if picked else grey), (x, y))
        pygame.draw.rect(screen, (50, 50, 50), (x + 110, y + 2, 120, 14))
        bar_color = (255, 220, 80) if picked else (110, 150, 200)
        pygame.draw.rect(screen, bar_color, (x + 110, y + 2, int(120 * min(score, 1.0)), 14))
        screen.blit(get_font(20).render(f"{score:.2f}", True, white), (x + 238, y))
        y += 26    

def draw_hint(screen, player, world):
    col, row = int(player.pos.x // TILE), int(player.pos.y // TILE)
    if player.hidden:
        text = "Hidden - press E to come out"
    elif world.tile_at(col, row) == "B":
        text = "Press E to hide"
    else:
        return
    t = get_font(24).render(text, True, (255, 255, 255))
    screen.blit(t, (20, 650))        