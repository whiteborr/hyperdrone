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

## Implementation Progress

The settings refactoring is being implemented in phases:

1. ✅ Core structure created (constants.py, settings.json, asset_manifest.json, settings_manager.py)
2. ✅ Compatibility layer in game_settings.py to maintain backward compatibility
3. ✅ AssetManager updated to use settings_manager instead of direct game_settings access
4. ⬜ Update remaining modules to use settings_manager directly
5. ⬜ Complete migration of all hardcoded values to settings.json and asset_manifest.json

## Next Steps

1. Update core game modules like game_loop_refactored.py to use settings_manager
2. Add missing settings to settings.json (HUD settings, etc.)
3. Update documentation with more examples
## Implementation Progress

The settings refactoring is being implemented in phases:

1. ✅ Core structure created (constants.py, settings.json, asset_manifest.json, settings_manager.py)
2. ✅ Compatibility layer in game_settings.py to maintain backward compatibility
3. ✅ AssetManager updated to use settings_manager instead of direct game_settings access
4. ✅ Core game modules (game_loop_refactored.py) updated to use settings_manager
5. ⬜ Update remaining modules to use settings_manager directly
6. ⬜ Complete migration of all hardcoded values to settings.json and asset_manifest.json

## Next Steps

1. Update remaining game modules to use settings_manager
2. Add missing settings to settings.json (HUD settings, etc.)
3. Update documentation with more examples
4. Create migration guide for developers

## Completed Updates

### AssetManager
- Now uses get_asset_path() instead of direct access to gs.ASSET_PATHS
- Added get_weapon_icon_paths() helper method to settings_manager
- Maintains compatibility with existing code during transition

### GameController (game_loop_refactored.py)
- Updated screen resolution handling to use settings_manager
- Updated FPS and sound volume settings to use settings_manager
- Updated player lives and timer settings to use settings_manager
- Updated spawn point calculation to use settings_manager
- Maintains compatibility with existing code through self.gs reference
## Extended Usage Examples

### Basic Settings Access

```python
from settings_manager import get_setting, set_setting, save_settings

# Get gameplay settings with default values
player_health = get_setting("gameplay", "PLAYER_MAX_HEALTH", 100)
player_speed = get_setting("gameplay", "PLAYER_SPEED", 3)

# Get display settings
screen_width = get_setting("display", "WIDTH", 1920)
screen_height = get_setting("display", "HEIGHT", 1080)
fullscreen = get_setting("display", "FULLSCREEN_MODE", False)

# Get enemy settings
enemy_health = get_setting("enemies", "ENEMY_HEALTH", 100)
enemy_speed = get_setting("enemies", "ENEMY_SPEED", 1.5)
```

### Modifying Settings

```python
from settings_manager import get_setting, set_setting, save_settings

# Change a setting
set_setting("gameplay", "PLAYER_MAX_HEALTH", 150)

# Change multiple settings
set_setting("display", "FULLSCREEN_MODE", True)
set_setting("display", "FPS", 120)

# Save changes to disk
save_settings()
```

### Asset Path Access

```python
from settings_manager import get_asset_path

# Get sound effect paths
shoot_sound_path = get_asset_path("sounds", "SHOOT_SOUND")
collect_sound_path = get_asset_path("sounds", "COLLECT_RING_SOUND")

# Get image paths
player_sprite_path = get_asset_path("sprites", "PLAYER_SPRITE")
ui_icon_path = get_asset_path("images", "RING_UI_ICON")

# Get font paths
ui_font_path = get_asset_path("fonts", "UI_TEXT_FONT")
```

### Practical Examples

#### Screen Setup
```python
import pygame
from settings_manager import get_setting

# Initialize screen with settings
width = get_setting("display", "WIDTH", 1920)
height = get_setting("display", "HEIGHT", 1080)
fullscreen = get_setting("display", "FULLSCREEN_MODE", False)
flags = pygame.FULLSCREEN if fullscreen else 0
screen = pygame.display.set_mode((width, height), flags)
```

#### Sound System
```python
import pygame
from settings_manager import get_setting, get_asset_path

# Load and play a sound with volume from settings
sound_path = get_asset_path("sounds", "SHOOT_SOUND")
sound = pygame.mixer.Sound(sound_path)
volume = get_setting("display", "SFX_VOLUME_MULTIPLIER", 0.7)
sound.set_volume(volume)
sound.play()
```

#### Enemy Creation
```python
from settings_manager import get_setting

def create_enemy(x, y):
    health = get_setting("enemies", "ENEMY_HEALTH", 100)
    speed = get_setting("enemies", "ENEMY_SPEED", 1.5)
    return Enemy(x, y, health, speed)
```

### Migration from game_settings

```python
# Old code
import game_settings as gs
health = gs.PLAYER_MAX_HEALTH
enemy_speed = gs.ENEMY_SPEED
sound_path = gs.ASSET_PATHS["SHOOT_SOUND"]

# New code
from settings_manager import get_setting, get_asset_path
health = get_setting("gameplay", "PLAYER_MAX_HEALTH", 100)
enemy_speed = get_setting("enemies", "ENEMY_SPEED", 1.5)
sound_path = get_asset_path("sounds", "SHOOT_SOUND")
```
## Settings Categories Reference

The settings are organized into the following categories:

### display
- Screen resolution (`WIDTH`, `HEIGHT`)
- Frame rate (`FPS`)
- Display mode (`FULLSCREEN_MODE`)
- Volume settings (`MUSIC_VOLUME_MULTIPLIER`, `SFX_VOLUME_MULTIPLIER`)
- UI layout (`BOTTOM_PANEL_HEIGHT`, etc.)

### gameplay
- Player stats (`PLAYER_MAX_HEALTH`, `PLAYER_SPEED`, `PLAYER_LIVES`)
- Game world (`TILE_SIZE`)
- Initial settings (`INITIAL_WEAPON_MODE`)
- Special modes (`PLAYER_INVINCIBILITY`)

### weapons
- Bullet properties (`PLAYER_BULLET_SPEED`, `PLAYER_BULLET_LIFETIME`)
- Weapon cooldowns (`PLAYER_BASE_SHOOT_COOLDOWN`, `PLAYER_RAPID_FIRE_COOLDOWN`)
- Special weapon settings (`LIGHTNING_DAMAGE`, `MISSILE_SPEED`, etc.)

### enemies
- Enemy stats (`ENEMY_HEALTH`, `ENEMY_SPEED`)
- Enemy attack properties (`ENEMY_BULLET_SPEED`, `ENEMY_BULLET_COOLDOWN`)
- Special enemy types (`PROTOTYPE_DRONE_HEALTH`, `TR3B_SPEED`, etc.)

### bosses
- Boss stats (`MAZE_GUARDIAN_HEALTH`, `MAZE_GUARDIAN_SPEED`)
- Boss attack properties (`MAZE_GUARDIAN_BULLET_SPEED`, `MAZE_GUARDIAN_LASER_DAMAGE`)
- Boss behavior timings (`MAZE_GUARDIAN_SHIELD_DURATION_MS`, etc.)

### powerups
- Powerup properties (`POWERUP_SIZE`, `POWERUP_SPAWN_CHANCE`)
- Powerup effects (`SHIELD_POWERUP_DURATION`, `SPEED_BOOST_POWERUP_DURATION`)
- Spawn settings (`MAX_POWERUPS_ON_SCREEN`, `POWERUP_SPAWN_INTERVAL`)

### collectibles
- Collectible properties (`CORE_FRAGMENT_VISUAL_SIZE`)
- Collection goals (`TOTAL_CORE_FRAGMENTS_NEEDED`, `MAX_RINGS_PER_LEVEL`)

### progression
- Level timers (`LEVEL_TIMER_DURATION`, `BONUS_LEVEL_DURATION_MS`)
- Rewards (`RING_PUZZLE_CORE_REWARD`)
- Leaderboard settings (`LEADERBOARD_MAX_ENTRIES`, `LEADERBOARD_FILE_NAME`)

### Asset Categories Reference

Assets are organized into the following categories:

- `sounds`: Sound effects (shoot, collect, explosion, etc.)
- `music`: Music tracks (menu theme, gameplay theme, etc.)
- `images`: UI elements and game objects
- `sprites`: Character and enemy sprites
- `fonts`: Text fonts for UI
## Best Practices

1. **Always provide default values** when using `get_setting()` to handle missing settings gracefully:
   ```python
   # Good - provides fallback if setting doesn't exist
   player_speed = get_setting("gameplay", "PLAYER_SPEED", 3)
   
   # Risky - may return None if setting doesn't exist
   player_speed = get_setting("gameplay", "PLAYER_SPEED")
   ```

2. **Use the correct category** for each setting to maintain organization:
   ```python
   # Good - uses appropriate categories
   enemy_health = get_setting("enemies", "ENEMY_HEALTH", 100)
   screen_width = get_setting("display", "WIDTH", 1920)
   
   # Bad - mixes categories
   enemy_health = get_setting("gameplay", "ENEMY_HEALTH", 100)
   ```

3. **Save settings after making changes**:
   ```python
   # Make multiple changes
   set_setting("gameplay", "PLAYER_MAX_HEALTH", 150)
   set_setting("gameplay", "PLAYER_SPEED", 4)
   
   # Save once after all changes
   save_settings()
   ```

4. **Use constants for setting keys** to avoid typos:
   ```python
   # Define constants
   SETTING_PLAYER_HEALTH = "PLAYER_MAX_HEALTH"
   CATEGORY_GAMEPLAY = "gameplay"
   
   # Use constants
   health = get_setting(CATEGORY_GAMEPLAY, SETTING_PLAYER_HEALTH, 100)
   ```

5. **For new code, always use settings_manager** instead of importing game_settings:
   ```python
   # Preferred
   from settings_manager import get_setting
   player_health = get_setting("gameplay", "PLAYER_MAX_HEALTH", 100)
   
   # Avoid in new code
   import game_settings as gs
   player_health = gs.PLAYER_MAX_HEALTH
   ```
## Migration Guide

A detailed migration guide is available in the `SETTINGS_MIGRATION_GUIDE.md` file. This guide provides step-by-step instructions for transitioning from the old `game_settings.py` approach to the new `settings_manager` system.