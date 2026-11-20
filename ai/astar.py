import heapq
import math

SQRT2 = math.sqrt(2)

# (dx, dy, step cost): 4 straight moves, then 4 diagonal moves
NEIGHBORS = [
    (1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1),
    (1, 1, SQRT2), (1, -1, SQRT2), (-1, 1, SQRT2), (-1, -1, SQRT2),
]


def heuristic(a, b):
    """h(n): octile distance. Exact cost on an empty 8-direction grid, so it never overestimates."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return (dx + dy) + (SQRT2 - 2) * min(dx, dy)


def astar(walkable, start, goal):
    """
    Find the shortest path from start to goal.

    walkable : function (col, row) -> bool
    start, goal : (col, row) tuples

    Returns (path, expanded):
      path     = list of (col, row) from start to goal, or None if unreachable
      expanded = number of tiles A* examined (useful for evaluation later)
    """
    if not walkable(*goal):
        return None, 0

    counter = 0  # tie-breaker so the heap never compares tuples of nodes
    open_heap = [(heuristic(start, goal), counter, start)]
    g = {start: 0.0}          # best known cost from start to each tile
    came_from = {}            # for rebuilding the path
    closed = set()
    expanded = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)  # lowest f first
        if current in closed:
            continue
        closed.add(current)
        expanded += 1

        if current == goal:
            return _reconstruct(came_from, current), expanded

        c, r = current
        for dx, dy, cost in NEIGHBORS:
            nb = (c + dx, r + dy)
            if nb in closed or not walkable(*nb):
                continue
            # no corner cutting on diagonals
            if dx != 0 and dy != 0:
                if not walkable(c + dx, r) or not walkable(c, r + dy):
                    continue

            new_g = g[current] + cost
            if new_g < g.get(nb, float("inf")):
                g[nb] = new_g
                came_from[nb] = current
                counter += 1
                f = new_g + heuristic(nb, goal)
                heapq.heappush(open_heap, (f, counter, nb))

    return None, expanded  # open list ran out: no path exists


def _reconstruct(came_from, node):
    path = [node]
    while node in came_from:
        node = came_from[node]
        path.append(node)
    path.reverse()
    return path