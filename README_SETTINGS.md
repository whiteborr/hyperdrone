# HYPERDRONE Settings System

## Overview

The HYPERDRONE game uses a centralized settings system to manage all configurable parameters. This document explains how the settings system works and how to modify game settings.

## Settings Structure

All game settings are stored in `data/settings.json`. This file is organized into categories, each containing related settings:

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

## Accessing Settings in Code

The settings system provides a simple API for accessing settings:

```python
from settings_manager import get_setting

# Get a setting with a default value if not found
tile_size = get_setting("gameplay", "TILE_SIZE", 80)

# Get a color setting
red_color = get_setting("colors", "RED", (255, 0, 0))

# Get a game state identifier
game_state_playing = get_setting("game_states", "GAME_STATE_PLAYING", "playing")
```

## Modifying Settings

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

## Constants vs. Settings

The game distinguishes between true constants and configurable settings:

- **Constants**: Unchanging values like dictionary keys, enum-like values, and internal identifiers. These are defined in `constants.py`.
- **Settings**: Configurable parameters that affect gameplay, visuals, or behavior. These are stored in `data/settings.json`.

The `constants.py` file now imports settings from `settings_manager` to provide backward compatibility for code that still references constants directly.

## Adding New Settings

To add a new setting:

1. Decide which category it belongs to (or create a new one if needed)
2. Add the setting to `data/settings.json` with an appropriate default value
3. Access it in code using `get_setting("category", "SETTING_NAME", default_value)`

## Best Practices

- Always provide a sensible default value when using `get_setting()`
- Group related settings in the same category
- Use descriptive names for settings (all caps for consistency)
- Document any new settings you add
- Consider adding important gameplay settings to the in-game settings menu