import pygame
from pathlib import Path
from config import CFG
from game.world import World, TILE
from game.player import Player
from game.renderer import (draw_world, draw_player, draw_stamina_bar,
                           draw_keys, draw_key_counter, draw_message,
                           draw_hunter, draw_debug, draw_vision_cone,
                           draw_alert_mark, draw_noise, draw_state_label,
                           draw_ai_panel, draw_hint)
from ai.hunter import Hunter

WIDTH, HEIGHT = 1280, 720
FPS = 60

STONE_RANGE = CFG["stone"]["range"]
STONE_NOISE_RADIUS = CFG["stone"]["noise_radius"]
STONE_DURATION = CFG["stone"]["duration"]

HUNTER_ROUTES = [[tuple(p) for p in h["patrol"]] for h in CFG["hunters"]]


def make_hunters(world):
    """One Hunter per route in config.json; each starts at its route's first point."""
    return [Hunter(route[0], route, TILE, world.hiding_spots) for route in HUNTER_ROUTES]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Shadow Hunt")
    clock = pygame.time.Clock()

    map_path = Path(__file__).parent / "maps" / "forest.txt"
    world = World(map_path)
    player = Player(world.spawn)
    won = False
    caught = False
    hunters = make_hunters(world)
    selected = 0          # which hunter the AI panel shows (Tab switches)
    show_debug = True
    stone_noises = []

    running = True
    while running:
        dt = clock.tick(FPS) / 1000  # seconds since last frame

        # 1. events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_r and (won or caught):
                world = World(map_path)
                player = Player(world.spawn)
                hunters = make_hunters(world)
                selected = 0
                won = False
                caught = False
                stone_noises.clear()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                show_debug = not show_debug

            if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                selected = (selected + 1) % len(hunters)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_e and not (won or caught):
                player.toggle_hide(world)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not (won or caught):
                target = pygame.Vector2(event.pos)
                offset = target - player.pos
                if offset.length() > STONE_RANGE:
                    target = player.pos + offset.normalize() * STONE_RANGE
                stone_noises.append({"pos": (target.x, target.y),
                                     "radius": STONE_NOISE_RADIUS, "ttl": STONE_DURATION})

        # 2. update
        if not (won or caught):
            keys = pygame.key.get_pressed()
            player.update(dt, keys, world)
            world.collect_keys(player.rect)
            tile = world.tile_at(player.rect.centerx // TILE, player.rect.centery // TILE)
            if world.gate_open and tile == "E":
                won = True

            # everything the hunters can hear this frame
            player_pos = (player.pos.x, player.pos.y)
            player_noise = []
            if player.noise_radius > 0:
                player_noise.append({"pos": player_pos, "radius": player.noise_radius})
            for s in stone_noises:
                s["ttl"] -= dt
            stone_noises[:] = [s for s in stone_noises if s["ttl"] > 0]
            noises = player_noise + stone_noises

            # each hunter senses and decides on its own
            for h in hunters:
                h.update(dt, world.is_walkable)
                h.perceive(player_pos, world.blocks_vision, player.hidden)
                h.hear(noises)
                if h.has_caught(player_pos):
                    caught = True

        # 3. draw
        screen.fill((30, 60, 30))
        draw_world(screen, world)
        for h in hunters:
            draw_vision_cone(screen, h, world)
        draw_noise(screen, player, stone_noises)
        draw_player(screen, player)
        for i, h in enumerate(hunters):
            if show_debug:
                draw_debug(screen, h)
            draw_hunter(screen, h)
            draw_alert_mark(screen, h)
            draw_state_label(screen, h)
            if i == selected and len(hunters) > 1:
                pygame.draw.circle(screen, (255, 255, 255), (round(h.x), round(h.y)), 18, 1)
        draw_keys(screen, world)
        draw_stamina_bar(screen, player)
        draw_key_counter(screen, world)
        draw_ai_panel(screen, hunters[selected], selected + 1, len(hunters))
        draw_hint(screen, player, world)
        if won:
            draw_message(screen, "YOU ESCAPED!", "Press R to play again", (120, 255, 140))
        if caught:
            draw_message(screen, "CAUGHT!", "Press R to try again", (255, 90, 90))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()