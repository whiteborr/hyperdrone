# Enemy AI Behavior System

## Overview
The HYPERDRONE game now uses a behavior-based design pattern for enemy AI. This pattern separates different AI behaviors into self-contained classes, making the system more modular and extensible.

## Architecture

### Base Components
- `BaseBehavior`: Abstract base class for all behaviors
- `Enemy`: Context class that holds a reference to the current behavior

### Behavior Classes
Located in `ai/behaviors.py`:

- `ChasePlayerBehavior`: Implements A* pathfinding to chase the player
- `TRBPatrolBehavior`: Handles patrol movement within a defined radius
- `TRBDashBehavior`: Manages quick dash movements toward or away from the player

## How It Works

1. Each enemy has a `behavior` attribute that references its current behavior object
2. The enemy's `update()` method delegates AI logic to the current behavior's `execute()` method
3. Behaviors can transition between each other by calling `enemy.set_behavior(new_behavior)`

## Example Usage

```python
# Creating a standard enemy that chases the player
enemy = Enemy(x, y, bullet_size, asset_manager, "enemy_sprite")
enemy.set_behavior(ChasePlayerBehavior(enemy))

# Creating a TR3B enemy with patrol behavior
tr3b = TR3BEnemy(x, y, bullet_size, asset_manager, "tr3b_sprite")
# TR3B automatically sets TRBPatrolBehavior in its __init__
```

## Creating New Behaviors

To create a new behavior:

1. Subclass `BaseBehavior`
2. Implement the `execute(maze, current_time_ms, delta_time_ms, game_area_x_offset)` method
3. Add any behavior-specific attributes and helper methods

```python
class NewBehavior(BaseBehavior):
    def __init__(self, enemy):
        super().__init__(enemy)
        # Add behavior-specific attributes
        
    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        # Implement behavior logic
```

## Creating New Enemy Types

To create a new enemy type with custom behaviors:

1. Subclass `Enemy`
2. Set specific attributes in `__init__`
3. Set the default behavior
4. Override `update()` if needed for behavior transitions

## Benefits

- Cleaner, more maintainable code
- Easier to create new enemy types with different behaviors
- Behaviors can be reused across different enemy types
- Dynamic behavior switching at runtime