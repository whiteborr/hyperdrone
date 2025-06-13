# HYPERDRONE Refactoring

## Overview

The HYPERDRONE game has undergone several refactoring efforts to improve code organization, maintainability, and extensibility. This document explains the major refactoring changes made to the codebase.

## Major Refactoring Efforts

### 1. Settings Management System

The settings and configuration management system has been refactored to centralize all configurable parameters into a single source of truth.

- **Centralized Settings**: All configurable parameters are now stored in `data/settings.json`
- **Updated settings_manager.py**: Made it the single source of truth for all settings
- **Refactored constants.py**: Transformed to import settings from settings_manager
- **Created a Compatibility Layer**: Preserved game_settings.py as a compatibility layer
- **Updated Code**: All files now use get_setting() instead of accessing game_settings directly

### 2. Data-Driven Enemy Configuration System

The enemy creation and management system has been refactored to use a data-driven approach, making it easier to add and modify enemy types.

- **Centralized Enemy Configs**: All enemy definitions are now stored in `data/enemy_configs.json`
- **Refactored Enemy Classes**: Updated to initialize from configuration dictionaries
- **Enhanced EnemyManager**: Now loads enemy definitions from JSON and spawns enemies by ID
- **Simplified Enemy Creation**: New enemies can be added by updating the JSON file
- **Consistent Properties**: All enemy properties are now defined in a standardized format

## How to Use the Refactored Systems

### Settings Management System

```python
from settings_manager import get_setting, set_setting, save_settings

# Get a setting with a default value if not found
tile_size = get_setting("gameplay", "TILE_SIZE", 80)

# Change a setting
set_setting("gameplay", "PLAYER_LIVES", 5)

# Save changes to disk
save_settings()
```

### Enemy Configuration System

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

## Benefits of the Refactored Systems

### Settings Management
1. **Single Source of Truth**: All settings in one place (settings.json)
2. **Better Organization**: Settings grouped by category
3. **Easier Maintenance**: Adding or modifying settings is simpler
4. **Backward Compatibility**: Existing code continues to work

### Enemy Configuration
1. **Centralized Configuration**: All enemy definitions in one file
2. **Easy Balancing**: Adjust enemy properties without code changes
3. **Simple Expansion**: Add new enemy types by updating JSON
4. **Consistent Structure**: Standardized format for all enemy types
5. **Reduced Code Duplication**: Common properties defined once

## Documentation

For more detailed information about specific refactoring efforts:

- Settings System: See this document
- Enemy Configuration System: See `README_ENEMY_CONFIG.md`