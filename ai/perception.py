import math


def tiles_on_line(a, b):
    """Bresenham's line: every tile on the straight line from tile a to tile b."""
    x0, y0 = a
    x1, y1 = b
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    tiles = []
    while True:
        tiles.append((x0, y0))
        if (x0, y0) == (x1, y1):
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return tiles


def has_line_of_sight(a_tile, b_tile, blocks_vision):
    """True if no tile strictly between a and b blocks vision."""
    for tile in tiles_on_line(a_tile, b_tile)[1:-1]:
        if blocks_vision(*tile):
            return False
    return True


def check_vision(viewer_pos, facing, target_pos, fov_deg, view_range, tile_size, blocks_vision):
    """
    viewer_pos, target_pos : (x, y) in pixels
    facing                 : viewer direction in radians (0 = east)
    Returns a dict describing what the viewer can see.
    """
    dx = target_pos[0] - viewer_pos[0]
    dy = target_pos[1] - viewer_pos[1]
    dist = math.hypot(dx, dy)

    in_range = dist <= view_range

    # angle between facing direction and direction to target, wrapped to [-pi, pi]
    diff = math.atan2(dy, dx) - facing
    diff = (diff + math.pi) % (2 * math.pi) - math.pi
    in_fov = abs(diff) <= math.radians(fov_deg) / 2

    blocked = False
    if in_range and in_fov:
        a = (int(viewer_pos[0] // tile_size), int(viewer_pos[1] // tile_size))
        b = (int(target_pos[0] // tile_size), int(target_pos[1] // tile_size))
        blocked = not has_line_of_sight(a, b, blocks_vision)

    return {
        "distance": dist,
        "in_range": in_range,
        "in_fov": in_fov,
        "blocked": blocked,
        "visible": in_range and in_fov and not blocked,
    }