# HYPERDRONE Weapon System Refactoring

## Overview

The weapon system in HYPERDRONE has been refactored to use the Strategy design pattern. This document explains the changes made and how the new system works.

## Changes Made

1. **Implemented Strategy Design Pattern**
   - Created a base `BaseWeaponStrategy` class in `entities/weapon_strategies.py`
   - Implemented concrete strategy classes for each weapon type
   - Decoupled weapon firing logic from the `PlayerDrone` class

2. **Refactored PlayerDrone Class**
   - Removed weapon-specific properties from `PlayerDrone`
   - Simplified the `shoot()` method to delegate to the current weapon strategy
   - Removed redundant code and duplicate update methods

3. **Enhanced Weapon Strategies**
   - Each strategy now fully encapsulates its specific weapon behavior
   - Weapon-specific properties (cooldown, bullet size, etc.) are contained in the strategy classes
   - Added methods to update the weapon strategy with current maze and enemies references

## How the New System Works

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

## Benefits of the New System

1. **Decoupling**: The `PlayerDrone` class no longer needs to know the details of how each weapon works
2. **Encapsulation**: Each weapon's behavior is now fully contained in its own strategy class
3. **Extensibility**: Adding new weapons is now much easier - just create a new strategy class
4. **Maintainability**: The code is more modular and easier to understand
5. **Single Responsibility**: Each class now has a clearer, more focused purpose