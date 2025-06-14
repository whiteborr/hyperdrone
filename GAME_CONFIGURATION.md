# HYPERDRONE Game Configuration

This document consolidates technical information about HYPERDRONE's game systems and architecture.

## Table of Contents
1. [AI Behavior System](#ai-behavior-system)
2. [Collision Optimization](#collision-optimization)
3. [Constants Update](#constants-update)
4. [Enemy Configuration System](#enemy-configuration-system)
5. [Event Bus System](#event-bus-system)
6. [Pathfinding Module](#pathfinding-module)
7. [Refactoring](#refactoring)
8. [Settings System](#settings-system)
9. [Weapon System](#weapon-system)

## AI Behavior System

### Overview
HYPERDRONE uses a behavior-based design pattern for enemy AI, separating different AI behaviors into self-contained classes for modularity and extensibility.

### Architecture

#### Base Components
- `BaseBehavior`: Abstract base class for all behaviors
- `Enemy`: Context class that holds a reference to the current behavior

#### Behavior Classes
Located in `ai/behaviors.py`:

- `ChasePlayerBehavior`: Implements A* pathfinding to chase the player
- `TRBPatrolBehavior`: Handles patrol movement within a defined radius
- `TRBDashBehavior`: Manages quick dash movements toward or away from the player

### How It Works

1. Each enemy has a `behavior` attribute that references its current behavior object
2. The enemy's `update()` method delegates AI logic to the current behavior's `execute()` method
3. Behaviors can transition between each other by calling `enemy.set_behavior(new_behavior)`

### Creating New Behaviors

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

### Creating New Enemy Types

To create a new enemy type with custom behaviors:

1. Subclass `Enemy`
2. Set specific attributes in `__init__`
3. Set the default behavior
4. Override `update()` if needed for behavior transitions

## Collision Optimization

### Overview
The collision handling in `hyperdrone_core/combat_controller.py` has been optimized using pygame's `groupcollide` function to improve performance.

### Key Changes

#### Before:
```python
for projectile in list(player_projectiles):
    hit_enemies = pygame.sprite.spritecollide(
        projectile, enemies_to_check, False, 
        lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
    )
    for enemy in hit_enemies:
        # ... damage logic
```

#### After:
```python
collision_func = lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
hits = pygame.sprite.groupcollide(player_projectiles, enemies_to_check, False, False, collision_func)

for projectile, enemies_hit in hits.items():
    for enemy in enemies_hit:
        # ... damage logic
```

### Implementation

The refactored code maintains all the original functionality while using `groupcollide` for:

1. Player projectile collisions with enemies
2. Enemy projectile collisions with player, turrets, and reactor
3. Turret projectile collisions with enemies
4. Physical collisions between entities

### Benefits

- **Better performance**: `groupcollide` uses spatial hashing for faster collision detection
- **Cleaner code**: Reduces nested loops and complex logic
- **More maintainable**: Easier to understand and modify

## Constants Update

### Overview
The `hyperdrone_core/constants.py` file has been deprecated in favor of importing directly from the root `constants.py` file.

### Changes Made

1. Updated imports across the codebase to point directly to the root constants file:
   - Changed `from hyperdrone_core.constants import ...` to `from constants import ...`
   - Changed `from .constants import ...` to `from constants import ...` in hyperdrone_core files

2. Modified `hyperdrone_core/constants.py` to:
   - Include a deprecation notice
   - Still import from the root constants file for backward compatibility
   - Log a warning when used

### Future Steps

In a future update, the `hyperdrone_core/constants.py` file will be completely removed. All code should import constants directly from the root file:

```python
from constants import GAME_STATE_PLAYING, GAME_STATE_MAIN_MENU
```

## Enemy Configuration System

### Overview
The enemy configuration system allows for easy creation, modification, and balancing of enemy types without changing code. All enemy properties are defined in a single JSON configuration file.

### Configuration File
Enemy configurations are stored in `data/enemy_configs.json`. The file contains a dictionary of enemy types, each with its own set of properties.

#### Structure
```json
{
  "enemies": {
    "enemy_id": {
      "name": "Display Name",
      "class_name": "PythonClassName",
      "stats": {
        "health": 100,
        "speed": 1.5,
        ...
      },
      "ai": {
        "initial_behavior": "BehaviorClassName",
        ...
      },
      "assets": {
        "sprite_asset_key": "sprite_key",
        "shoot_sound_key": "sound_key"
      },
      "weapon": {
        "shoot_cooldown": 1500,
        "bullet_damage": 10,
        ...
      }
    }
  }
}
```

### Usage

#### Spawning Enemies
Use the `EnemyManager.spawn_enemy_by_id` method to spawn enemies:

```python
# Spawn an enemy by ID
enemy_manager.spawn_enemy_by_id("sentinel", x, y)

# Spawn a defense drone with a path
enemy_manager.spawn_enemy_by_id("defense_drone_1", x, y, path_to_core=path)
```

#### Adding New Enemy Types
1. Add a new entry to `data/enemy_configs.json`
2. If needed, create a new enemy class that extends the base `Enemy` class
3. Use `spawn_enemy_by_id` to spawn the new enemy type

#### Modifying Existing Enemies
Simply edit the values in `data/enemy_configs.json` to adjust enemy properties.

## Event Bus System

### Overview
The Event Bus system decouples components in the game by allowing them to communicate without direct dependencies. Components can publish events to the bus, and other components can subscribe to those events.

### Key Components

#### 1. Event Classes (`hyperdrone_core/game_events.py`)
- `GameEvent`: Base class for all events
- `EnemyDefeatedEvent`: Triggered when an enemy is defeated

#### 2. Event Manager (`hyperdrone_core/event_manager.py`)
- `register_listener(event_type, listener_callback)`: Registers a callback function
- `dispatch(event)`: Sends an event to all registered listeners

### Usage Example

#### Publishing Events
```python
# In CombatController when an enemy is defeated
from hyperdrone_core.game_events import EnemyDefeatedEvent

event = EnemyDefeatedEvent(
    score_value=50,
    position=enemy.rect.center,
    enemy_id=id(enemy)
)
self.game_controller.event_manager.dispatch(event)
```

#### Subscribing to Events
```python
# In LevelManager constructor
from hyperdrone_core.game_events import EnemyDefeatedEvent
game_controller_ref.event_manager.register_listener(EnemyDefeatedEvent, self.on_enemy_defeated)

# Event handler method
def on_enemy_defeated(self, event):
    self.add_score(event.score_value)
```

### Benefits
1. **Decoupling**: Components don't need direct references to each other
2. **Extensibility**: New listeners can be added without modifying existing code
3. **Maintainability**: Easier to understand and debug component interactions
4. **Flexibility**: Multiple components can react to the same event independently

## Pathfinding Module

### Overview
The pathfinding functionality has been extracted from `entities/enemy.py` into a dedicated module `hyperdrone_core/pathfinding.py`.

### Key Components

#### A* Pathfinding Algorithm
The core pathfinding algorithm uses A* search to find the shortest path between two points in a grid:

```python
def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    # Implementation of A* search algorithm
```

#### Wall Following
When an enemy gets stuck or can't find a direct path to its target, it can use wall following to navigate around obstacles:

```python
def find_wall_follow_target(maze, current_grid_pos, maze_rows, maze_cols):
    # Find a target position along a wall to follow
```

#### Dynamic Goal Adjustment
If the path to the primary target (player or core) is blocked, the AI can now choose a nearby, reachable tile as an intermediate goal:

```python
def find_alternative_target(maze, current_grid_pos, primary_target_grid, maze_rows, maze_cols, max_distance=10):
    # Find an alternative target when the primary target is unreachable
```

### Improvements to Enemy AI

1. **Re-path Trigger**: If an enemy hasn't significantly changed its position for a certain amount of time (2.5 seconds), it forces a full recalculation of its path.

2. **Dynamic Goal Adjustment**: If the path to the primary target is blocked, the AI will temporarily choose a nearby, reachable tile as an intermediate goal.

3. **Wall Following**: When stuck, enemies can now follow walls to find a way around obstacles.

### Usage
```python
from hyperdrone_core.pathfinding import a_star_search, find_wall_follow_target, find_alternative_target

# Find a path from start to end
path = a_star_search(maze.grid, start_pos, end_pos, maze.rows, maze.cols)

# Find a wall-following target when stuck
wall_target = find_wall_follow_target(maze, current_pos, maze.rows, maze.cols)

# Find an alternative target when primary target is unreachable
alt_target = find_alternative_target(maze, current_pos, primary_target, maze.rows, maze.cols)
```

## Refactoring

### Overview
HYPERDRONE has undergone several refactoring efforts to improve code organization, maintainability, and extensibility.

### Major Refactoring Efforts

#### 1. Settings Management System
- **Centralized Settings**: All configurable parameters are now stored in `data/settings.json`
- **Updated settings_manager.py**: Made it the single source of truth for all settings
- **Refactored constants.py**: Transformed to import settings from settings_manager
- **Created a Compatibility Layer**: Preserved game_settings.py as a compatibility layer
- **Updated Code**: All files now use get_setting() instead of accessing game_settings directly

#### 2. Data-Driven Enemy Configuration System
- **Centralized Enemy Configs**: All enemy definitions are now stored in `data/enemy_configs.json`
- **Refactored Enemy Classes**: Updated to initialize from configuration dictionaries
- **Enhanced EnemyManager**: Now loads enemy definitions from JSON and spawns enemies by ID
- **Simplified Enemy Creation**: New enemies can be added by updating the JSON file
- **Consistent Properties**: All enemy properties are now defined in a standardized format

### How to Use the Refactored Systems

#### Settings Management System
```python
from settings_manager import get_setting, set_setting, save_settings

# Get a setting with a default value if not found
tile_size = get_setting("gameplay", "TILE_SIZE", 80)

# Change a setting
set_setting("gameplay", "PLAYER_LIVES", 5)

# Save changes to disk
save_settings()
```

#### Enemy Configuration System
```python
# In EnemyManager
# Load enemy configurations
with open("data/enemy_configs.json", 'r') as f:
    self.enemy_configs = json.load(f)["enemies"]

# Spawn an enemy by ID
enemy_manager.spawn_enemy_by_id("sentinel", x, y)

# Spawn a defense drone with a path
enemy_manager.spawn_enemy_by_id("defense_drone_1", x, y, path_to_core=path)
```

## Settings System

### Overview
HYPERDRONE uses a centralized settings system to manage all configurable parameters.

### Settings Structure
All game settings are stored in `data/settings.json`. This file is organized into categories:

- `display`: Screen resolution, UI positions, etc.
- `colors`: Color definitions used throughout the game
- `gameplay`: Core gameplay parameters like player health, speed, etc.
- `weapons`: Weapon-related settings like bullet speed, damage, etc.
- `abilities`: Special ability parameters
- `enemies`: Enemy-related settings
- `bosses`: Boss-specific parameters
- `powerups`: Powerup settings
- `collectibles`: Settings for collectible items
- `architect_vault`: Settings for the Architect's Vault special level
- `defense_mode`: Tower defense mode settings
- `progression`: Level progression settings
- `assets`: Asset file paths
- `game_states`: Game state identifiers
- `weapon_modes`: Weapon mode definitions and names

### Accessing Settings in Code
```python
from settings_manager import get_setting

# Get a setting with a default value if not found
tile_size = get_setting("gameplay", "TILE_SIZE", 80)

# Get a color setting
red_color = get_setting("colors", "RED", (255, 0, 0))

# Get a game state identifier
game_state_playing = get_setting("game_states", "GAME_STATE_PLAYING", "playing")
```

### Modifying Settings
Settings can be modified in two ways:

1. **Directly editing `data/settings.json`**: This is useful for permanent changes or adding new settings.

2. **Using the in-game settings menu**: Some settings can be modified through the game's settings menu.

3. **Programmatically**:
   ```python
   from settings_manager import set_setting, save_settings
   
   # Change a setting
   set_setting("gameplay", "PLAYER_LIVES", 5)
   
   # Save changes to disk
   save_settings()
   ```

### Constants vs. Settings
The game distinguishes between true constants and configurable settings:

- **Constants**: Unchanging values like dictionary keys, enum-like values, and internal identifiers. These are defined in `constants.py`.
- **Settings**: Configurable parameters that affect gameplay, visuals, or behavior. These are stored in `data/settings.json`.

### Adding New Settings
To add a new setting:

1. Decide which category it belongs to (or create a new one if needed)
2. Add the setting to `data/settings.json` with an appropriate default value
3. Access it in code using `get_setting("category", "SETTING_NAME", default_value)`

## Weapon System

### Overview
The weapon system in HYPERDRONE has been refactored to use the Strategy design pattern.

### Weapon Strategy Structure
```
BaseWeaponStrategy
├── DefaultWeaponStrategy
├── TriShotWeaponStrategy
├── RapidSingleWeaponStrategy
├── RapidTriShotWeaponStrategy
├── BigShotWeaponStrategy
├── BounceWeaponStrategy
├── PierceWeaponStrategy
├── HeatseekerWeaponStrategy
├── HeatseekerPlusBulletsWeaponStrategy
└── LightningWeaponStrategy
```

### Using the Weapon System
```python
# PlayerDrone now delegates to weapon strategies
def shoot(self, sound_asset_key=None, missile_sound_asset_key=None, maze=None, enemies_group=None):
    # Update references if provided
    if enemies_group is not None:
        self.enemies_group = enemies_group
        if self.current_weapon_strategy:
            self.current_weapon_strategy.update_enemies_group(enemies_group)
    
    if maze is not None and self.current_weapon_strategy:
        self.current_weapon_strategy.update_maze(maze)
    
    # Delegate firing logic to the current weapon strategy
    if self.current_weapon_strategy:
        if self.current_weapon_strategy.fire(sound_asset_key, missile_sound_asset_key):
            # Ensure the drone sprite matches the current weapon mode
            self._update_drone_sprite()
```

### Adding a New Weapon
To add a new weapon type:

1. Create a new strategy class in `entities/weapon_strategies.py`:
```python
class NewWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone):
        super().__init__(player_drone)
        # Set weapon-specific properties
        self.shoot_cooldown = 400
        self.bullet_size = 6
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Implement weapon-specific projectile creation
        # ...
```

2. Add the weapon mode constant in `constants.py`:
```python
WEAPON_MODE_NEW_WEAPON = get_setting("weapon_modes", "WEAPON_MODE_NEW_WEAPON", 10)
```

3. Register the strategy in `PlayerDrone.__init__()`:
```python
self.weapon_strategies = {
    # ... existing weapons ...
    WEAPON_MODE_NEW_WEAPON: NewWeaponStrategy,
}
```

4. Add the weapon to the sequence in `settings.json`:
```json
"WEAPON_MODES_SEQUENCE": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
```

### Benefits
1. **Decoupling**: The `PlayerDrone` class no longer needs to know the details of how each weapon works
2. **Encapsulation**: Each weapon's behavior is now fully contained in its own strategy class
3. **Extensibility**: Adding new weapons is now much easier - just create a new strategy class
4. **Maintainability**: The code is more modular and easier to understand