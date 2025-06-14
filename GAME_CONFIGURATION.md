# HYPERDRONE Game Configuration

This document consolidates technical information about HYPERDRONE's game systems and architecture.

## Table of Contents
1. [AI Behavior System](#ai-behavior-system)
2. [Collision Optimization](#collision-optimization)
3. [Constants Update](#constants-update)
4. [Enemy Configuration System](#enemy-configuration-system)
5. [Event Batching System](#event-batching-system)
6. [Event Bus System](#event-bus-system)
7. [Pathfinding Module](#pathfinding-module)
8. [Refactoring](#refactoring)
9. [Settings System](#settings-system)
10. [State Management System](#state-management-system)
11. [Weapon System](#weapon-system)

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

## Event Batching System

### Overview

The event batching system optimizes performance by combining similar events that occur in rapid succession. This reduces overhead during intense gameplay when many events are triggered simultaneously.

### Key Components

#### 1. EventBatch Class

The `EventBatch` class in `hyperdrone_core/event_batch.py` manages batches of similar events:

- Collects events of the same type within a time window
- Dispatches batched events when the time window expires or batch size limit is reached
- Maintains timing information for efficient processing

#### 2. BatchedEvent Base Class

The `BatchedEvent` class in `hyperdrone_core/event_batch.py` defines the interface for batchable events:

- `batchable` flag indicates if an event type can be batched
- `batch_window_ms` defines the time window for batching
- `max_batch_size` sets the maximum number of events in a batch
- `create_batch_event()` method creates a combined event from multiple individual events

#### 3. Enhanced EventManager

The `EventManager` class in `hyperdrone_core/event_manager.py` has been updated to:

- Detect and batch batchable events
- Manage event batches for different event types
- Dispatch batched events when appropriate
- Fall back to individual event dispatch when batching fails

### Batchable Event Types

The following event types are configured for batching:

1. **EnemyDefeatedEvent**
   - Batched when multiple enemies are defeated within 50ms
   - Combines score values and positions
   - Creates a single `BatchedEnemyDefeatedEvent`

2. **BulletHitEvent**
   - Batched when multiple bullets hit targets within 30ms
   - Combines hit positions and target information
   - Creates a single `BatchedBulletHitEvent`

3. **ParticleEmitEvent**
   - Batched when multiple particle emissions occur within 20ms
   - Combines particle types, positions, and counts
   - Creates a single `BatchedParticleEmitEvent`

### How to Create a Batchable Event

1. Create your event class inheriting from both `GameEvent` and `BatchedEvent`:

```python
class MyEvent(GameEvent, BatchedEvent):
    batchable = True
    batch_window_ms = 50  # Batch within 50ms
    max_batch_size = 20   # Or when we reach 20 events
    
    def __init__(self, data):
        self.data = data
    
    @classmethod
    def create_batch_event(cls, events):
        # Combine data from all events
        combined_data = [event.data for event in events]
        return BatchedMyEvent(combined_data)
```

2. Create a corresponding batched event class:

```python
class BatchedMyEvent(GameEvent):
    def __init__(self, combined_data):
        self.combined_data = combined_data
        self.count = len(combined_data)
```

3. Register listeners for both individual and batched events:

```python
event_manager.register_listener(MyEvent, handle_my_event)
event_manager.register_listener(BatchedMyEvent, handle_batched_my_event)
```

### Performance Considerations

- Event batching is most effective during intense gameplay with many similar events
- The batch window should be short enough to maintain responsiveness but long enough to catch event bursts
- Batch size limits prevent memory issues during sustained event bursts
- Batching can be disabled via settings for debugging or if it causes issues

### Configuration

Event batching can be configured in the settings:

```json
{
  "gameplay": {
    "EVENT_BATCHING_ENABLED": true
  }
}
```

Individual event types can also have custom batch settings:

```python
class MyEvent(GameEvent, BatchedEvent):
    batchable = True
    batch_window_ms = 100  # Custom window
    max_batch_size = 50    # Custom batch size
```

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

## State Management System

### Overview

The HYPERDRONE game uses a centralized state management system based on the State Design Pattern. This document explains how the state system works and how to use it effectively.

### Key Components

#### 1. State Registry

The `StateRegistry` class in `hyperdrone_core/state_registry.py` serves as a central registry for all game states and their allowed transitions. It:

- Maintains a registry of all state classes
- Defines allowed transitions between states
- Records state transition history
- Validates state transitions

#### 2. State Manager

The `StateManager` class in `hyperdrone_core/state_manager.py` handles the actual state transitions and manages the current state. It:

- Creates and initializes state objects
- Handles state transitions
- Updates music based on the current state
- Notifies the game controller about state changes

#### 3. State Base Class

The `State` class in `hyperdrone_core/state.py` is the base class for all game states. It defines the interface that all states must implement:

- `enter()`: Called when entering the state
- `exit()`: Called when exiting the state
- `handle_events()`: Handles input events
- `update()`: Updates the state logic
- `draw()`: Renders the state

### State Transition Flow

1. A state transition is requested via `StateManager.set_state(state_id)`
2. The state manager checks if the transition is allowed using the registry
3. If allowed, the current state's `exit()` method is called
4. The new state is created and its `enter()` method is called
5. The transition is recorded in the registry's history
6. The game controller is notified about the state change

### Adding a New State

To add a new state:

1. Create a new class that inherits from `State`
2. Implement the required methods (`enter`, `exit`, `handle_events`, `update`, `draw`)
3. Register the state in `StateManager._register_state_classes()`
4. Define allowed transitions to/from the state in `StateManager._register_allowed_transitions()`

Example:

```python
# 1. Create the state class
class MyNewState(State):
    def enter(self, previous_state=None, **kwargs):
        # Initialize state
        pass
        
    def exit(self, next_state=None):
        # Clean up
        pass
        
    def handle_events(self, events):
        # Handle input
        pass
        
    def update(self, delta_time):
        # Update logic
        pass
        
    def draw(self, surface):
        # Render
        pass
```

Then in `state_manager.py`:

```python
# 2. Register the state class
def _register_state_classes(self):
    state_classes = {
        # ... existing states ...
        "MyNewState": MyNewState,
    }
    
# 3. Define allowed transitions
def _register_allowed_transitions(self):
    # ... existing transitions ...
    self.registry.register_transition("MainMenuState", "MyNewState")
    self.registry.register_transition("MyNewState", "MainMenuState")
```

### Debugging State Transitions

The `StateTransitionViewer` class in `hyperdrone_core/state_transition_viewer.py` provides a visual tool for debugging state transitions. To use it:

```python
from hyperdrone_core.state_transition_viewer import show_transition_viewer

# Call this from a debug menu or key press
show_transition_viewer()
```

This will open a window showing:
- The history of state transitions
- A graph of allowed transitions

### Best Practices

1. **Define Clear Transitions**: Only register transitions that make logical sense in the game flow
2. **Keep States Focused**: Each state should have a single responsibility
3. **Clean Up Resources**: Always clean up resources in the `exit()` method
4. **Use Kwargs for Parameters**: Pass additional parameters to states using kwargs
5. **Check Transition History**: Use the registry's history for debugging state flow issues

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