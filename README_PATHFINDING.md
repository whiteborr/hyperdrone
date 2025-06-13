# Pathfinding Module

This document explains the pathfinding module and its integration with the enemy AI system.

## Overview

The pathfinding functionality has been extracted from `entities/enemy.py` into a dedicated module `hyperdrone_core/pathfinding.py`. This follows the Single Responsibility Principle, where:

- `pathfinding.py` is responsible for finding paths
- `enemy.py` is responsible for enemy behavior

## Integration with State Manager

The pathfinding system now works with the new State Design Pattern implementation:

- Enemy pathfinding is aware of the current game state through the state manager
- Different states (like PlayingState vs MazeDefenseState) can have different pathfinding behaviors
- The state manager ensures pathfinding is only active in appropriate game states

## Key Components

### A* Pathfinding Algorithm

The core pathfinding algorithm uses A* search to find the shortest path between two points in a grid:

```python
def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    # Implementation of A* search algorithm
```

### Wall Following

When an enemy gets stuck or can't find a direct path to its target, it can use wall following to navigate around obstacles:

```python
def find_wall_follow_target(maze, current_grid_pos, maze_rows, maze_cols):
    # Find a target position along a wall to follow
```

### Dynamic Goal Adjustment

If the path to the primary target (player or core) is blocked, the AI can now choose a nearby, reachable tile as an intermediate goal:

```python
def find_alternative_target(maze, current_grid_pos, primary_target_grid, maze_rows, maze_cols, max_distance=10):
    # Find an alternative target when the primary target is unreachable
```

## Improvements to Enemy AI

The enemy AI has been enhanced with the following features:

1. **Re-path Trigger**: If an enemy hasn't significantly changed its position for a certain amount of time (2.5 seconds), it forces a full recalculation of its path.

2. **Dynamic Goal Adjustment**: If the path to the primary target is blocked, the AI will temporarily choose a nearby, reachable tile as an intermediate goal before trying to path to the primary target again.

3. **Wall Following**: When stuck, enemies can now follow walls to find a way around obstacles.

## Usage

To use the pathfinding module in your code:

```python
from hyperdrone_core.pathfinding import a_star_search, find_wall_follow_target, find_alternative_target

# Find a path from start to end
path = a_star_search(maze.grid, start_pos, end_pos, maze.rows, maze.cols)

# Find a wall-following target when stuck
wall_target = find_wall_follow_target(maze, current_pos, maze.rows, maze.cols)

# Find an alternative target when primary target is unreachable
alt_target = find_alternative_target(maze, current_pos, primary_target, maze.rows, maze.cols)
```

## Benefits

- **Cleaner code**: Each module has a single responsibility
- **Better maintainability**: Pathfinding algorithms can be improved without affecting enemy behavior
- **Improved AI**: Enemies are less likely to get stuck and can find alternative paths
- **Reusability**: Pathfinding functions can be used by other entities besides enemies