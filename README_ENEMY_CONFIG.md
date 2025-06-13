# Data-Driven Enemy Configuration System

## Overview
The enemy configuration system allows for easy creation, modification, and balancing of enemy types without changing code. All enemy properties are defined in a single JSON configuration file, making it simple to add new enemy types or adjust existing ones.

## Configuration File
Enemy configurations are stored in `data/enemy_configs.json`. The file contains a dictionary of enemy types, each with its own set of properties.

### Structure
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

### Configuration Properties

#### Base Properties
- `name`: Display name for the enemy
- `class_name`: Python class to instantiate (e.g., "Enemy", "SentinelDrone", "TR3BEnemy")

#### Stats
- `health`: Enemy health points
- `speed`: Movement speed
- `contact_damage`: Damage dealt on collision with player
- `aggro_radius_tiles`: Detection radius in tiles

#### AI
- `initial_behavior`: Starting behavior class name
- Additional behavior-specific parameters (e.g., `dash_speed_multiplier` for TR3B enemies)

#### Assets
- `sprite_asset_key`: Key for the enemy's sprite in the asset manager
- `shoot_sound_key`: Key for the shooting sound effect

#### Weapon
- `shoot_cooldown`: Time between shots in milliseconds
- `bullet_size_ratio`: Size of bullets relative to player bullets
- `bullet_damage`: Damage dealt by bullets
- `bullet_speed`: Speed of bullets

## Usage

### Spawning Enemies
Use the `EnemyManager.spawn_enemy_by_id` method to spawn enemies:

```python
# Spawn an enemy by ID
enemy_manager.spawn_enemy_by_id("sentinel", x, y)

# Spawn a defense drone with a path
enemy_manager.spawn_enemy_by_id("defense_drone_1", x, y, path_to_core=path)
```

### Adding New Enemy Types
1. Add a new entry to `data/enemy_configs.json`
2. If needed, create a new enemy class that extends the base `Enemy` class
3. Use `spawn_enemy_by_id` to spawn the new enemy type

### Modifying Existing Enemies
Simply edit the values in `data/enemy_configs.json` to adjust enemy properties.

## Implementation Details

### Enemy Classes
- `Enemy`: Base class for all enemies
- `SentinelDrone`: Fast, agile enemy with enhanced shooting
- `TR3BEnemy`: Advanced enemy with patrol and dash behaviors
- `DefenseDrone`: Path-following enemy for defense mode

### Enemy Manager
The `EnemyManager` class handles loading configurations and spawning enemies:
- Loads enemy configs from JSON on initialization
- Provides `spawn_enemy_by_id` method to create enemies from configs
- Handles level-based enemy spawning in `spawn_enemies_for_level`
- Manages defense mode enemies in `spawn_enemy_for_defense`

## Benefits
- Centralized enemy configuration
- Easy balancing and tweaking
- Simple addition of new enemy types
- Consistent property management
- Reduced code duplication