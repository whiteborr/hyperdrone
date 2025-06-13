# HYPERDRONE Settings Refactoring

## Overview

The HYPERDRONE game's settings and configuration management system has been refactored to centralize all configurable parameters into a single source of truth. This document explains the changes made and how to use the new system.

## Changes Made

1. **Centralized Settings**
   - All configurable parameters are now stored in `data/settings.json`
   - Settings are organized into logical categories (display, gameplay, weapons, colors, etc.)

2. **Updated settings_manager.py**
   - Made settings_manager the single source of truth for all settings
   - Removed circular import dependency with constants.py
   - Added convenience functions for accessing settings

3. **Refactored constants.py**
   - Transformed constants.py to import settings from settings_manager
   - Kept only true constants (like dictionary keys and enum-like values)
   - Maintained backward compatibility for existing code

4. **Created a Compatibility Layer**
   - Preserved game_settings.py as a compatibility layer
   - Created a backup of the original game_settings.py as game_settings.py.bak
   - Simplified game_settings.py to forward requests to settings_manager

5. **Updated Code to Use settings_manager**
   - Updated all state files to use get_setting() instead of accessing game_settings
   - Removed direct imports from game_settings.py
   - Updated color usage to get colors from settings

## How to Use the New System

### Accessing Settings

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

```python
from settings_manager import set_setting, save_settings

# Change a setting
set_setting("gameplay", "PLAYER_LIVES", 5)

# Save changes to disk
save_settings()
```

## Benefits of the New System

1. **Single Source of Truth**: All settings are now in one place (settings.json)
2. **Better Organization**: Settings are grouped by category
3. **Easier Maintenance**: Adding or modifying settings is simpler
4. **Backward Compatibility**: Existing code continues to work
5. **Clear Separation**: True constants are separated from configurable settings

## Refactoring Complete

The refactoring has been successfully completed. All files in the codebase now import directly from settings_manager instead of game_settings.py. The compatibility layer in game_settings.py remains in place to ensure backward compatibility if needed, but it is no longer being used by any files in the project.

## Files Updated

All files in the project have been updated to use the new settings system. The refactoring is now complete across the entire codebase, with every file importing directly from settings_manager instead of game_settings.py.