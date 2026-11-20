from pathlib import Path
from game.world import World
from ai.astar import astar

world = World(Path(__file__).parent / "maps" / "forest.txt")


def show(path):
    """Print the map as text with the path marked by '*'."""
    cells = set(path) if path else set()
    for r in range(world.rows):
        line = ""
        for c in range(world.cols):
            line += "*" if (c, r) in cells else world.grid[r][c]
        print(line)


# Test 1: spawn -> tile just west of the gate
start, goal = world.spawn, (28, 9)
path, expanded = astar(world.is_walkable, start, goal)
print(f"Test 1: {start} -> {goal}")
print(f"  path length: {len(path)} tiles, A* examined {expanded} tiles")
show(path)

# Test 2: goal is a tree -> should return None
path, _ = astar(world.is_walkable, world.spawn, (0, 0))
print("\nTest 2 (goal inside a tree):", path)

# Test 3: closed gate is not walkable -> should return None
path, _ = astar(world.is_walkable, world.spawn, (29, 9))
print("Test 3 (closed gate):", path)