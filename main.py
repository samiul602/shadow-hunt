import pygame
from pathlib import Path
from game.world import World, TILE

from ai.hunter import Hunter
from game.renderer import (draw_world, draw_player, draw_stamina_bar,
                           draw_keys, draw_key_counter, draw_message,
                           draw_hunter, draw_debug, draw_vision_cone, draw_alert_mark)

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
    won = False
    hunter = Hunter(PATROL_POINTS[0], PATROL_POINTS, TILE)
    show_debug = True

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
                     show_debug = not show_debug  #eikhane shomossha ase
                running = False

        # 2. update 
        keys = pygame.key.get_pressed()
        player.update(dt, keys, world)  
        if not won:
            hunter.update(dt, world.is_walkable)
            hunter.perceive((player.pos.x, player.pos.y), world.blocks_vision)
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