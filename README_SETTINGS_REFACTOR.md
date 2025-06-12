# Settings Refactoring Guide

This document explains the refactored settings system for HYPERDRONE.

## Overview

The monolithic `game_settings.py` has been split into multiple files:

1. `constants.py`: Contains unchanging constants (colors, state names, etc.)
2. `data/settings.json`: Contains gameplay parameters that can be tweaked
3. `data/asset_manifest.json`: Contains all asset paths
4. `settings_manager.py`: Handles loading and accessing settings
5. `game_settings.py`: Compatibility layer for existing code

## Benefits

- **Better organization**: Settings are grouped by purpose
- **Easier maintenance**: Changes to one type of setting don't affect others
- **Modding support**: JSON files can be easily modified without touching code
- **Cleaner code**: Asset paths are centralized in one file

## How to Use

### For New Code

Use the `settings_manager` module:

```python
from settings_manager import get_setting, set_setting, get_asset_path

# Get a setting
player_health = get_setting("gameplay", "PLAYER_MAX_HEALTH", 100)

# Set a setting
set_setting("gameplay", "PLAYER_MAX_HEALTH", 150)

# Get an asset path
sound_path = get_asset_path("sounds", "SHOOT_SOUND")
```

### For Existing Code

The compatibility layer in `game_settings.py` allows existing code to work without changes:

```python
import game_settings as gs

# Access settings as before
health = gs.PLAYER_MAX_HEALTH
gs.set_game_setting("PLAYER_MAX_HEALTH", 150)
```

## File Structure

### constants.py

Contains truly unchanging constants:
- Colors (WHITE, RED, etc.)
- Game state names (GAME_STATE_MAIN_MENU, etc.)
- Fixed identifiers (ARCHITECT_REWARD_BLUEPRINT_ID, etc.)

### settings.json

Contains gameplay parameters organized by category:
- display: Screen resolution, volume, etc.
- gameplay: Basic player stats, etc.
- weapons: Weapon parameters
- enemies: Enemy stats
- etc.

### asset_manifest.json

Contains all asset paths organized by type:
- sounds: Sound effect paths
- music: Music track paths
- images: UI and game image paths
- sprites: Character sprite paths
- etc.

## Modding

To mod the game:
1. Edit `data/settings.json` to change gameplay parameters
2. Edit `data/asset_manifest.json` to change assets

No code changes required!