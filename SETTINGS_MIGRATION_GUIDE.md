# HYPERDRONE Settings Migration Guide

This guide explains how to migrate from the old `game_settings.py` approach to the new `settings_manager` system.

## Quick Reference

| Old Approach | New Approach |
|-------------|-------------|
| `import game_settings as gs` | `from settings_manager import get_setting, set_setting` |
| `gs.PLAYER_MAX_HEALTH` | `get_setting("gameplay", "PLAYER_MAX_HEALTH", 100)` |
| `gs.set_game_setting("PLAYER_MAX_HEALTH", 150)` | `set_setting("gameplay", "PLAYER_MAX_HEALTH", 150)` |
| `gs.ASSET_PATHS["SHOOT_SOUND"]` | `get_asset_path("sounds", "SHOOT_SOUND")` |

## Step-by-Step Migration

### 1. Update Imports

```python
# Old
import game_settings as gs

# New
from settings_manager import get_setting, set_setting, get_asset_path
```

### 2. Reading Settings

```python
# Old
player_health = gs.PLAYER_MAX_HEALTH
enemy_speed = gs.ENEMY_SPEED
fps = gs.FPS

# New
player_health = get_setting("gameplay", "PLAYER_MAX_HEALTH", 100)
enemy_speed = get_setting("enemies", "ENEMY_SPEED", 1.5)
fps = get_setting("display", "FPS", 60)
```

### 3. Writing Settings

```python
# Old
gs.set_game_setting("PLAYER_MAX_HEALTH", 150)
gs.PLAYER_MAX_HEALTH = 150  # Direct assignment (not recommended)

# New
set_setting("gameplay", "PLAYER_MAX_HEALTH", 150)
save_settings()  # Call after making changes to persist them
```

### 4. Asset Paths

```python
# Old
shoot_sound_path = gs.ASSET_PATHS["SHOOT_SOUND"]
player_sprite = gs.REGULAR_ENEMY_SPRITE_PATH

# New
shoot_sound_path = get_asset_path("sounds", "SHOOT_SOUND")
player_sprite = get_asset_path("sprites", "REGULAR_ENEMY_SPRITE_PATH")
```

### 5. Handling Missing Settings

```python
# Old - might cause errors if setting doesn't exist
value = gs.SOME_SETTING

# New - provides default value if setting doesn't exist
value = get_setting("category", "SOME_SETTING", default_value)
```

## Settings Categories

When migrating, use these categories for different types of settings:

- `display`: Screen resolution, FPS, volume settings
- `gameplay`: Player stats, game world settings
- `weapons`: Bullet properties, weapon cooldowns
- `enemies`: Enemy stats, attack properties
- `bosses`: Boss stats, attack properties
- `powerups`: Powerup properties, effects
- `collectibles`: Collectible properties, goals
- `progression`: Level timers, rewards, leaderboard

## Asset Categories

Use these categories for different types of assets:

- `sounds`: Sound effects
- `music`: Music tracks
- `images`: UI elements and game objects
- `sprites`: Character and enemy sprites
- `fonts`: Text fonts for UI

## Transition Tips

1. **Gradual Migration**: Update one module at a time, starting with core modules
2. **Keep Compatibility**: The `game_settings.py` compatibility layer allows for gradual migration
3. **Test Thoroughly**: After migrating each module, test to ensure settings are correctly accessed
4. **Add Missing Settings**: If a setting is missing in JSON files, add it to the appropriate category
5. **Use Default Values**: Always provide default values to handle missing settings gracefully

## Common Patterns

### Screen Setup

```python
# Old
screen = pygame.display.set_mode((gs.WIDTH, gs.HEIGHT), 
                               pygame.FULLSCREEN if gs.FULLSCREEN_MODE else 0)

# New
width = get_setting("display", "WIDTH", 1920)
height = get_setting("display", "HEIGHT", 1080)
fullscreen = get_setting("display", "FULLSCREEN_MODE", False)
screen = pygame.display.set_mode((width, height), 
                               pygame.FULLSCREEN if fullscreen else 0)
```

### Sound Volume

```python
# Old
sound.set_volume(volume * gs.SFX_VOLUME_MULTIPLIER)

# New
sound.set_volume(volume * get_setting("display", "SFX_VOLUME_MULTIPLIER", 0.7))
```

### Enemy Creation

```python
# Old
enemy = Enemy(x, y, gs.ENEMY_HEALTH, gs.ENEMY_SPEED)

# New
health = get_setting("enemies", "ENEMY_HEALTH", 100)
speed = get_setting("enemies", "ENEMY_SPEED", 1.5)
enemy = Enemy(x, y, health, speed)
```