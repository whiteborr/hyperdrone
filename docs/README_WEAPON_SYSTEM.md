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

## Weapon Mode Trees

### 🔴 BIG SHOT — Elemental Weaponry
- `Level 1`: `WEAPON_MODE_BIG_SHOT_FIRE`
- `Level 2`: `WEAPON_MODE_BIG_SHOT_EARTH`
- `Level 3`: `WEAPON_MODE_BIG_SHOT_WATER`
- `Level 4`: `WEAPON_MODE_BIG_SHOT_AIR`
- `Level 5`: `WEAPON_MODE_BIG_SHOT_CONVERGENCE`

### 🔵 BOUNCE / PIERCE — Vault Disruption Logic
- `Level 1`: `WEAPON_MODE_BOUNCE`
- `Level 2`: `WEAPON_MODE_PIERCE`
- `Level 3`: `WEAPON_MODE_RICOCHET_CHAIN`
- `Level 4`: `WEAPON_MODE_TUNNEL_SHOT`
- `Level 5`: `WEAPON_MODE_DISRUPTOR_CORE`

### 🟣 HEATSEEKER — Autonomous Pursuit Logic
- `Level 1`: `WEAPON_MODE_HEATSEEKER`
- `Level 2`: `WEAPON_MODE_HEATSEEKER_PLUS_BULLETS`
- `Level 3`: `WEAPON_MODE_TRACK_SPIKE`
- `Level 4`: `WEAPON_MODE_GORGON_MARK`
- `Level 5`: `WEAPON_MODE_ORBITAL_ECHO`

### ⚡ LIGHTNING — Cognition Cascade Arc
- `Level 1`: `WEAPON_MODE_ARC_SPARK`
- `Level 2`: `WEAPON_MODE_LIGHTNING`
- `Level 3`: `WEAPON_MODE_CHAIN_BURST`
- `Level 4`: `WEAPON_MODE_MINDLASH`
- `Level 5`: `WEAPON_MODE_QUASINET`

Each set represents a progression from basic to advanced behavior and ties into the game’s story themes like Vault manipulation, AI sentience, and elemental mastery.


⚙️ SET 1: Bounce / Pierce Path – "Vault Disruption Protocol"
This path is ideal for representing the Vault’s physical-world manipulation logic — weapons that bounce, pierce, or disobey normal physics. It reflects the Vault learning to rewrite reality rules.

Level	Mode	Description
1	WEAPON_MODE_BOUNCE	Basic reality-disruptive rounds that rebound off walls
2	WEAPON_MODE_PIERCE	Refined logic — shots now pass through multiple enemies
3	WEAPON_MODE_RICOCHET_CHAIN	(New) Each bounce chains to nearest target
4	WEAPON_MODE_TUNNEL_SHOT	(New) Projectiles phase through all objects and reappear behind targets
5	WEAPON_MODE_DISRUPTOR_CORE	(New) Fires logic-warping shells that destabilize enemy AI, briefly stunning them

🧠 Lore Tie-In: This weapon tree is based on Vault environmental interaction logic — as if the Vault is “rewriting physics” around each shot. Great for puzzle bosses or corrupted sectors.


⚙️ SET 2: Heatseeker Path – "AI Pursuit Logic"
This weapon set is all about adaptive targeting, tying into the Vault’s automated hunter drones and CRUCIBLE surveillance AI.

Level	Mode	Description
1	WEAPON_MODE_HEATSEEKER	Basic homing missile that locks to closest enemy
2	WEAPON_MODE_HEATSEEKER_PLUS_BULLETS	Homing missiles plus low-damage bullet spread
3	WEAPON_MODE_TRACK_SPIKE	(New) Lock-on darts with increasing homing precision over time
4	WEAPON_MODE_GORGON_MARK	(New) Marks enemies, causing all future shots to home in — even non-seeking ones
5	WEAPON_MODE_ORBITAL_ECHO	(New) Fires a slow orb that auto-tracks up to 3 enemies and triggers delayed AoE pulses upon proximity detection

🧠 Lore Tie-In: These are tied to CRUCIBLE’s Gorgon Stare surveillance tech and the Vault’s autonomous guardian orbs. Perfect for Chapter 4+ enemy types or defense scenarios.


⚡ SET 3: Lightning Path – "Cognition Cascade Arc"
This weapon line directly ties into Air Core logic and AI cognition / synapse chaining. It’s cerebral and fast, ideal for countering logic-locked enemies and swarms.

Level	Mode	Description
1	WEAPON_MODE_ARC_SPARK	(New) Fires a straight bolt that arcs to a nearby enemy
2	WEAPON_MODE_LIGHTNING	Upgraded chain lightning with 2 jumps
3	WEAPON_MODE_CHAIN_BURST	(New) Each enemy struck triggers a mini-lightning nova
4	WEAPON_MODE_MINDLASH	(New) Lightning pulses temporarily slow enemy thinking/movement
5	WEAPON_MODE_QUASINET	(New) Creates a lightning web between struck enemies — immobilizes and damages all within

🧠 Lore Tie-In: The Vault’s neural pathways, the Air Core's cognition cascade, and the Architect’s fragmented mind are all echoed in this set. It feels like using AI's own logic pathways as a weapon.


✅ Summary: Weapon Mode Trees (Level 1–5)
🔴 BIG SHOT — Elemental Weaponry
Fire → Earth → Water → Air → Convergence
→ Tied to Vault core fragments

🔵 BOUNCE / PIERCE — Vault Disruption
Bounce → Pierce → Ricochet_Chain → Tunnel_Shot → Disruptor_Core
→ Reality-breaking tech, echoes of Vault structure manipulation

🟣 HEATSEEKER — Autonomous Pursuit Logic
Heatseeker → Heatseeker+Bullets → Track_Spike → Gorgon_Mark → Orbital_Echo
→ Vault's hunter logic + CRUCIBLE interception tech

⚡ LIGHTNING — Synaptic AI Weapons
Arc_Spark → Lightning → Chain_Burst → Mindlash → Quasinet
→ Vault’s cognition cascade logic turned into synaptic warfare

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