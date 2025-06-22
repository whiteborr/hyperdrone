# HYPERDRONE Weapon System Documentation

## Overview

The HYPERDRONE weapon system implements the Strategy design pattern to provide a flexible, extensible framework for different weapon types. Each weapon mode is encapsulated in its own strategy class, making it easy to add new weapons without modifying existing code.

## Architecture

### Strategy Pattern Implementation

#### Core Components

1. **BaseWeaponStrategy**: Abstract base class defining the weapon interface
2. **Concrete Strategies**: Individual weapon implementations
3. **PlayerDrone**: Context class that uses weapon strategies
4. **Factory Method**: Creates appropriate strategy instances

```python
# Factory pattern for weapon creation
def create_weapon_strategy(weapon_mode, player_drone):
    strategy_map = {
        WEAPON_MODE_DEFAULT: DefaultWeaponStrategy,
        WEAPON_MODE_TRI_SHOT: TriShotWeaponStrategy,
        # ... other weapons
    }
    return strategy_map[weapon_mode](player_drone)
```

### Benefits of Strategy Pattern

- **Decoupling**: PlayerDrone doesn't need to know weapon implementation details
- **Extensibility**: New weapons added by creating new strategy classes
- **Maintainability**: Each weapon's logic is self-contained
- **Testability**: Individual weapon behaviors can be tested in isolation

## Weapon Types

### 1. DefaultWeaponStrategy
- **Description**: Single forward-firing projectile
- **Use Case**: Balanced, reliable weapon for general combat
- **Properties**: Standard damage, moderate fire rate

### 2. TriShotWeaponStrategy
- **Description**: Three projectiles fired in a spread pattern
- **Use Case**: Area coverage, multiple target engagement
- **Properties**: 15-degree spread, same damage per projectile

### 3. RapidSingleWeaponStrategy
- **Description**: High rate of fire single projectiles
- **Use Case**: Sustained damage output, fast-moving targets
- **Properties**: Reduced cooldown, standard damage

### 4. RapidTriShotWeaponStrategy
- **Description**: Rapid-fire tri-shot combination
- **Use Case**: Maximum area coverage with high DPS
- **Properties**: Fast firing tri-shot spread

### 5. BigShotWeaponStrategy
- **Description**: Large, high-damage projectiles
- **Use Case**: Heavy armor penetration, boss encounters
- **Properties**: Increased size and damage, slower fire rate

### 6. BounceWeaponStrategy
- **Description**: Projectiles that bounce off walls
- **Use Case**: Confined spaces, indirect fire
- **Properties**: Configurable bounce count, ricochet physics

### 7. PierceWeaponStrategy
- **Description**: Projectiles that pass through enemies and walls
- **Use Case**: Multiple enemy engagement, obstacle bypass
- **Properties**: Piercing capability, reduced damage per hit

### 8. HeatseekerWeaponStrategy
- **Description**: Homing missiles that track enemies
- **Use Case**: Mobile targets, guaranteed hits
- **Properties**: Target acquisition, curved flight paths

### 9. HeatseekerPlusBulletsWeaponStrategy
- **Description**: Combination of homing missiles and rapid bullets
- **Use Case**: Versatile combat, multiple engagement types
- **Properties**: Dual cooldown system, mixed projectile types

### 10. LightningWeaponStrategy
- **Description**: Chain lightning that arcs between enemies
- **Use Case**: Crowd control, electrical damage
- **Properties**: Multi-target damage, visual lightning effects

## Implementation Details

### BaseWeaponStrategy Interface

```python
class BaseWeaponStrategy:
    def __init__(self, player_drone):
        # Initialize common properties
        self.player = player_drone
        self.bullet_speed = get_setting("weapons", "PLAYER_BULLET_SPEED", 8)
        self.shoot_cooldown = get_setting("weapons", "PLAYER_BASE_SHOOT_COOLDOWN", 500)
        
    def fire(self, sound_asset_key=None, missile_sound_asset_key=None):
        # Template method handling common firing logic
        # Delegates to _create_projectile for weapon-specific behavior
        
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Abstract method implemented by each weapon strategy
        raise NotImplementedError("Subclasses must implement this method")
```

### Template Method Pattern

The `fire()` method uses the Template Method pattern:

1. **Cooldown Check**: Ensures weapon isn't fired too frequently
2. **Position Calculation**: Determines projectile spawn location
3. **Sound Effects**: Plays appropriate audio feedback
4. **Projectile Creation**: Delegates to weapon-specific implementation
5. **Sprite Update**: Updates drone appearance to match weapon

### Projectile Management

Each weapon strategy manages its projectiles through sprite groups:

```python
# Different projectile types
self.player.bullets_group.add(new_bullet)      # Standard bullets
self.player.missiles_group.add(new_missile)    # Homing missiles
self.player.lightning_zaps_group.add(new_zap)  # Lightning effects
```

## Configuration System

### Settings-Driven Parameters

All weapon properties are configurable through the settings system:

```json
{
  "weapons": {
    "PLAYER_BULLET_SPEED": 7,
    "PLAYER_BULLET_DAMAGE": 15,
    "PLAYER_BASE_SHOOT_COOLDOWN": 500,
    "MISSILE_DAMAGE": 50,
    "LIGHTNING_DAMAGE": 25,
    "BOUNCING_BULLET_MAX_BOUNCES": 2
  }
}
```

### Weapon Mode Sequence

Weapon upgrade progression is configurable:

```json
{
  "weapon_modes": {
    "WEAPON_MODES_SEQUENCE": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    "WEAPON_MODE_NAMES": {
      "0": "Single Shot",
      "1": "Tri-Shot",
      "9": "Chain Lightning"
    }
  }
}
```

## Advanced Features

### Dual Cooldown System

Some weapons (like HeatseekerPlusBulletsWeaponStrategy) implement dual cooldowns:

```python
def fire(self, sound_asset_key=None, missile_sound_asset_key=None):
    # Check missile cooldown for full firing sequence
    if can_fire_missile:
        return super().fire(sound_asset_key, missile_sound_asset_key)
    # Check bullet cooldown for rapid fire component
    elif can_fire_bullet:
        self._fire_bullet_only()
        return True
    return False
```

### Smart Targeting

Advanced weapons use intelligent targeting:

```python
# Lightning weapon finds closest enemy
closest_enemy = None
min_distance = float('inf')
for enemy in self.enemies_group:
    distance = math.sqrt(dx*dx + dy*dy)
    if distance < min_distance and distance < lightning_range:
        closest_enemy = enemy
```

### Physics Integration

Weapons integrate with the game's physics system:

- **Collision Detection**: Projectiles interact with maze walls and enemies
- **Bounce Physics**: Realistic ricochet calculations
- **Homing Behavior**: Missile guidance and target tracking
- **Piercing Logic**: Multi-target damage calculations

## Adding New Weapons

### Step 1: Create Strategy Class

```python
class NewWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone):
        super().__init__(player_drone)
        # Set weapon-specific properties
        self.shoot_cooldown = 400
        self.bullet_size = 6
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Implement weapon-specific projectile creation
        new_projectile = CustomProjectile(spawn_x, spawn_y, self.player.angle)
        self.player.custom_projectiles_group.add(new_projectile)
```

### Step 2: Register in Factory

```python
# Add to strategy_map in create_weapon_strategy()
WEAPON_MODE_NEW_WEAPON: NewWeaponStrategy
```

### Step 3: Configure Settings

```json
{
  "weapon_modes": {
    "WEAPON_MODE_NEW_WEAPON": 10,
    "WEAPON_MODES_SEQUENCE": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  }
}
```

### Step 4: Add Assets

- Weapon-specific drone sprites
- Projectile graphics
- Sound effects
- UI icons

## Performance Considerations

### Optimization Strategies

1. **Object Pooling**: Reuse projectile objects to reduce garbage collection
2. **Culling**: Remove off-screen projectiles
3. **Batch Processing**: Group similar projectiles for efficient updates
4. **LOD System**: Simplified projectiles for distant combat

### Memory Management

```python
# Automatic cleanup of expired projectiles
self.bullets_group.update(maze, game_area_x_offset)
# Projectiles remove themselves when lifetime expires
```

## Visual Effects

### Sprite Management

Weapons automatically update drone sprites:

```python
def _update_drone_sprite(self):
    # Map weapon modes to sprite names
    weapon_sprite_names = {
        WEAPON_MODE_DEFAULT: "default",
        WEAPON_MODE_TRI_SHOT: "tri_shot",
        # ...
    }
    # Load appropriate sprite for current weapon
```

### Particle Effects

Advanced weapons create visual effects:

- **Muzzle Flash**: Brief flash at projectile spawn
- **Trail Effects**: Particle trails for missiles
- **Impact Effects**: Explosion particles on hit
- **Lightning Arcs**: Animated electrical effects

## Testing and Debugging

### Debug Features

- Projectile trajectory visualization
- Cooldown timers display
- Damage number feedback
- Hit detection debugging

### Common Issues

1. **Projectile Clipping**: Ensure proper collision detection
2. **Performance Drops**: Monitor projectile count and cleanup
3. **Audio Overlap**: Manage sound effect layering
4. **Visual Artifacts**: Handle sprite rotation and scaling

## Future Enhancements

### Planned Features

- **Weapon Modifications**: Attachments that modify weapon behavior
- **Elemental Damage**: Fire, ice, electric damage types
- **Charge Weapons**: Hold-to-charge firing mechanics
- **Weapon Combos**: Combining multiple weapon effects

### Extension Points

- **Custom Projectiles**: New projectile types with unique behaviors
- **Weapon Upgrades**: Progressive enhancement system
- **Environmental Interactions**: Weapons that affect the environment
- **Multiplayer Balancing**: Weapon balance for competitive play