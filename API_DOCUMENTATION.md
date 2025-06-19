# HYPERDRONE API Documentation

## Core Classes

### GameController

Main game controller that orchestrates all game systems.

#### Methods

```python
def __init__(self)
```
Initializes the game controller with all necessary systems and managers.

```python
def run(self)
```
Main game loop that handles events, updates, and rendering.

```python
def handle_state_transition(self, new_state, old_state, **kwargs)
```
Handles transitions between game states with cleanup and initialization.

```python
def toggle_pause(self)
```
Toggles game pause state and updates music accordingly.

```python
def play_sound(self, key, vol=0.7)
```
Plays a sound effect with volume control.

---

### StateManager

Manages game states using the State Design Pattern.

#### Methods

```python
def __init__(self, game_controller_ref)
```
Initializes state manager with game controller reference.

```python
def set_state(self, state_id, **kwargs)
```
Transitions to a new game state with validation and parameter passing.

```python
def get_current_state(self)
```
Returns the currently active state object.

```python
def get_current_state_id(self)
```
Returns the identifier of the current state.

---

### PlayerDrone

Player-controlled drone with weapons and abilities.

#### Methods

```python
def __init__(self, x, y, drone_id, drone_stats, asset_manager, sprite_asset_key, crash_sound_key, drone_system)
```
Initializes player drone with position, stats, and systems.

```python
def shoot(self, sound_asset_key=None, missile_sound_asset_key=None, maze=None, enemies_group=None)
```
Fires current weapon using active weapon strategy.

```python
def cycle_weapon_state(self)
```
Advances to the next weapon in the upgrade sequence.

```python
def set_weapon_mode(self, mode)
```
Sets specific weapon mode and updates strategy.

```python
def activate_ability(self, ability_id, game_controller_ref)
```
Activates an unlocked active ability if not on cooldown.

```python
def take_damage(self, amount, sound_key_on_hit=None)
```
Applies damage to the drone with invincibility and shield checks.

---

## AI System

### BaseBehavior

Abstract base class for all enemy AI behaviors.

#### Methods

```python
def __init__(self, enemy)
```
Initializes behavior with enemy reference.

```python
def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0)
```
**Abstract method** - Executes behavior logic for current frame.

### ChasePlayerBehavior

Aggressive pursuit behavior using A* pathfinding.

#### Methods

```python
def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0)
```
Implements player chasing with pathfinding and shooting logic.

### TRBPatrolBehavior

Patrol movement within defined radius.

#### Methods

```python
def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0)
```
Implements patrol movement with wait periods and transitions.

---

## Weapon System

### BaseWeaponStrategy

Base class for all weapon strategies.

#### Methods

```python
def __init__(self, player_drone)
```
Initializes weapon strategy with player reference and common properties.

```python
def fire(self, sound_asset_key=None, missile_sound_asset_key=None)
```
Template method handling common firing logic and delegating to subclasses.

```python
def can_shoot(self, current_time_ms=None)
```
Checks if weapon is off cooldown and ready to fire.

```python
def get_cooldown(self)
```
Returns the cooldown time for this weapon type.

```python
def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None)
```
**Abstract method** - Creates weapon-specific projectiles.

### Factory Function

```python
def create_weapon_strategy(weapon_mode, player_drone)
```
Factory method that creates appropriate weapon strategy based on mode.

**Parameters:**
- `weapon_mode` (int): Weapon mode constant
- `player_drone` (PlayerDrone): Player drone instance

**Returns:** BaseWeaponStrategy instance

---

## Pathfinding System

### Core Functions

```python
def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols)
```
A* pathfinding algorithm implementation.

**Parameters:**
- `maze_grid` (list): 2D grid where 1=wall, 0=walkable
- `start_pos_grid` (tuple): Starting position (row, col)
- `end_pos_grid` (tuple): Target position (row, col)
- `maze_rows` (int): Number of grid rows
- `maze_cols` (int): Number of grid columns

**Returns:** List of path positions or None if no path exists

```python
def find_wall_follow_target(maze, current_grid_pos, maze_rows, maze_cols)
```
Finds target for wall-following behavior.

**Returns:** Target position tuple or None

```python
def find_alternative_target(maze, current_grid_pos, primary_target_grid, maze_rows, maze_cols, max_distance=10)
```
Finds alternative target when primary target is unreachable.

**Returns:** Alternative target position or None

---

## Settings System

### SettingsManager

Centralized settings management with JSON persistence.

#### Methods

```python
def __init__(self)
```
Loads settings from JSON files and initializes manager.

```python
def get_setting(self, category, key, default=None)
```
Retrieves setting value with fallback to default.

**Parameters:**
- `category` (str): Settings category (e.g., 'display', 'gameplay')
- `key` (str): Setting key within category
- `default` (Any): Default value if setting not found

**Returns:** Setting value or default

```python
def set_setting(self, category, key, value)
```
Sets setting value and marks for saving.

```python
def save_settings(self)
```
Persists modified settings to JSON file.

```python
def get_asset_path(self, category, key)
```
Retrieves asset file path from manifest.

### Convenience Functions

```python
def get_setting(category, key, default=None)
```
Global function for easy settings access.

```python
def set_setting(category, key, value)
```
Global function for setting modification.

```python
def save_settings()
```
Global function for settings persistence.

---

## Event System

### EventManager

Manages game events and communication between systems.

#### Methods

```python
def register_listener(self, event_type, listener_callback)
```
Registers callback function for specific event type.

```python
def dispatch(self, event)
```
Sends event to all registered listeners.

### Event Classes

#### GameEvent
Base class for all game events.

#### EnemyDefeatedEvent
Triggered when an enemy is defeated.

**Attributes:**
- `score_value` (int): Points awarded
- `position` (tuple): Enemy position when defeated
- `enemy_id` (int): Unique enemy identifier

---

## Asset Management

### AssetManager

Handles loading and caching of game assets.

#### Methods

```python
def get_image(self, key)
```
Retrieves cached image asset by key.

```python
def get_sound(self, key)
```
Retrieves cached sound asset by key.

```python
def get_music_path(self, key)
```
Gets file path for music asset.

---

## Drone System

### DroneSystem

Manages drone unlocks and progression.

#### Methods

```python
def get_selected_drone_id(self)
```
Returns currently selected drone identifier.

```python
def get_drone_stats(self, drone_id)
```
Retrieves stats dictionary for specified drone.

```python
def collect_core_fragment(self, fragment_id)
```
Marks core fragment as collected and updates progression.

```python
def has_ability_unlocked(self, ability_id)
```
Checks if specific ability is unlocked for player.

---

## Configuration Constants

### Weapon Modes
```python
WEAPON_MODE_DEFAULT = 0
WEAPON_MODE_TRI_SHOT = 1
WEAPON_MODE_RAPID_SINGLE = 2
WEAPON_MODE_RAPID_TRI = 3
WEAPON_MODE_BIG_SHOT = 4
WEAPON_MODE_BOUNCE = 5
WEAPON_MODE_PIERCE = 6
WEAPON_MODE_HEATSEEKER = 7
WEAPON_MODE_HEATSEEKER_PLUS_BULLETS = 8
WEAPON_MODE_LIGHTNING = 9
```

### Game States
```python
GAME_STATE_MAIN_MENU = "main_menu"
GAME_STATE_PLAYING = "playing"
GAME_STATE_GAME_OVER = "game_over"
GAME_STATE_LEADERBOARD = "leaderboard_display"
# ... additional states
```

### Colors
```python
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
CYAN = (0, 255, 255)
# ... additional colors
```

---

## Usage Examples

### Creating a New Weapon

```python
class CustomWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone):
        super().__init__(player_drone)
        self.shoot_cooldown = 300  # Custom cooldown
        
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create custom projectile
        projectile = CustomBullet(spawn_x, spawn_y, self.player.angle)
        self.player.bullets_group.add(projectile)

# Register in factory
strategy_map[WEAPON_MODE_CUSTOM] = CustomWeaponStrategy
```

### Adding New AI Behavior

```python
class CustomBehavior(BaseBehavior):
    def __init__(self, enemy):
        super().__init__(enemy)
        self.custom_state = 0
        
    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        # Implement custom AI logic
        if some_condition:
            self.enemy.set_behavior(ChasePlayerBehavior(self.enemy))

# Use in enemy
enemy.set_behavior(CustomBehavior(enemy))
```

### Accessing Settings

```python
# Get setting with default
player_speed = get_setting("gameplay", "PLAYER_SPEED", 3.0)

# Modify setting
set_setting("display", "FPS", 120)

# Save changes
save_settings()
```

### Event Handling

```python
# Register event listener
def on_enemy_defeated(event):
    print(f"Enemy defeated at {event.position} for {event.score_value} points")

event_manager.register_listener(EnemyDefeatedEvent, on_enemy_defeated)

# Dispatch event
event = EnemyDefeatedEvent(score_value=100, position=(x, y), enemy_id=id)
event_manager.dispatch(event)
```