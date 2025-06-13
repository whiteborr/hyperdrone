# Collision Handling Optimization

This document explains the optimization of collision handling in the combat controller using pygame's `groupcollide` function.

## Overview

The original collision handling code in `hyperdrone_core/combat_controller.py` used nested loops to check for collisions between sprites. This approach works but can be inefficient, especially with many sprites.

The optimized version now uses pygame's `groupcollide` function to improve performance.

## Integration with State Manager

The collision system now works with the new State Design Pattern implementation:

- Collision handling is aware of the current game state through the state manager
- Different states (like PlayingState vs MazeDefenseState) can have different collision behaviors
- The state manager ensures collision detection is only active in appropriate game states

## Benefits

- **Better performance**: `groupcollide` uses spatial hashing for faster collision detection
- **Cleaner code**: Reduces nested loops and complex logic
- **More maintainable**: Easier to understand and modify

## Key Changes

### Before:
```python
for projectile in list(player_projectiles):
    hit_enemies = pygame.sprite.spritecollide(
        projectile, enemies_to_check, False, 
        lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
    )
    for enemy in hit_enemies:
        # ... damage logic
```

### After:
```python
collision_func = lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
hits = pygame.sprite.groupcollide(player_projectiles, enemies_to_check, False, False, collision_func)

for projectile, enemies_hit in hits.items():
    for enemy in enemies_hit:
        # ... damage logic
```

## Implementation

The refactored code maintains all the original functionality while using `groupcollide` for:

1. Player projectile collisions with enemies
2. Enemy projectile collisions with player, turrets, and reactor
3. Turret projectile collisions with enemies
4. Physical collisions between entities

## How to Use

To use the refactored version:

1. Review `combat_controller_refactored.py` to ensure it meets your requirements
2. Replace the collision handling methods in `combat_controller.py` with the optimized versions
3. Test thoroughly to ensure all collision behavior works as expected

## Notes

- The refactored code preserves special handling for:
  - Piercing projectiles
  - Lightning zaps
  - Boss corner collisions
  - Wall collisions
- The optimization focuses on the collision detection, not the collision response logic