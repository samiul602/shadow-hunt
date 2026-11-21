import pygame
from pathlib import Path
from game.world import World, TILE

from ai.hunter import Hunter
from game.renderer import (draw_world, draw_player, draw_stamina_bar,
                           draw_keys, draw_key_counter, draw_message,
                           draw_hunter, draw_debug, draw_vision_cone,
                             draw_alert_mark, draw_noise)

from game.player import Player

WIDTH, HEIGHT = 1280, 720
FPS = 60


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Shadow Hunt")
    clock = pygame.time.Clock()
    map_path = Path(__file__).parent / "maps" / "forest.txt"
    world = World(map_path)
    player = Player(world.spawn)
    PATROL_POINTS = [(8, 5), (20, 5), (19, 11), (8, 13)]
    STONE_RANGE = 200          # max throw distance (pixels)
    STONE_NOISE_RADIUS = 220   # how far a stone's noise carries
    won = False
    hunter = Hunter(PATROL_POINTS[0], PATROL_POINTS, TILE)
    show_debug = True
    stone_noises = []

    running = True
    while running:
        dt = clock.tick(FPS) / 1000  # seconds since last frame

        # 1. events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r and won:
                    world = World(map_path)   # restart
                    player = Player(world.spawn)
                    hunter = Hunter(PATROL_POINTS[0], PATROL_POINTS, TILE)
                    won = False
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                     show_debug = not show_debug  

                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not won:
                        target = pygame.Vector2(event.pos)
                        offset = target - player.pos
                        if offset.length() > STONE_RANGE:
                            target = player.pos + offset.normalize() * STONE_RANGE
                        stone_noises.append({"pos": (target.x, target.y),
                                            "radius": STONE_NOISE_RADIUS, "ttl": 0.5})
                running = False

        # 2. update 
        keys = pygame.key.get_pressed()
        player.update(dt, keys, world)  
        if not won:
            hunter.update(dt, world.is_walkable)
            hunter.perceive((player.pos.x, player.pos.y), world.blocks_vision)
            player_noise = []
            if player.noise_radius > 0:
                player_noise.append({"pos": (player.pos.x, player.pos.y),
                                    "radius": player.noise_radius})
            for s in stone_noises:
                s["ttl"] -= dt
            stone_noises[:] = [s for s in stone_noises if s["ttl"] > 0]
            hunter.hear(player_noise + stone_noises)
            keys = pygame.key.get_pressed()
            player.update(dt, keys, world)
            world.collect_keys(player.rect)
            tile = world.tile_at(player.rect.centerx // TILE, player.rect.centery // TILE)
            if world.gate_open and tile == "E":
                won = True

        # 3. draw
        screen.fill((30, 60, 30))  # dark forest green
        draw_world(screen, world)
        draw_vision_cone(screen, hunter, world)
        draw_noise(screen, player, stone_noises)
        draw_player(screen, player)
        if show_debug:
             draw_debug(screen, hunter)
        draw_hunter(screen, hunter)
        draw_alert_mark(screen, hunter)
        draw_stamina_bar(screen, player)
        draw_keys(screen, world)
        draw_key_counter(screen, world)
        if won:
            draw_message(screen, "YOU ESCAPED!", "Press R to play again", (120, 255, 140))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()