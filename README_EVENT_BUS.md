# Event Bus System

## Overview

The Event Bus system is a communication pattern that decouples components in the game by allowing them to communicate without direct dependencies. Components can publish events to the bus, and other components can subscribe to those events without knowing about each other.

## Key Components

### 1. Event Classes (`hyperdrone_core/game_events.py`)

- `GameEvent`: Base class for all events
- `EnemyDefeatedEvent`: Triggered when an enemy is defeated, containing:
  - `score_value`: Points awarded for defeating the enemy
  - `position`: (x, y) coordinates where the enemy was defeated
  - `enemy_id`: Unique identifier for the defeated enemy

### 2. Event Manager (`hyperdrone_core/event_manager.py`)

- `register_listener(event_type, listener_callback)`: Registers a callback function to be called when an event of the specified type is dispatched
- `dispatch(event)`: Sends an event to all registered listeners

## Usage Example

### Publishing Events

```python
# In CombatController when an enemy is defeated
from hyperdrone_core.game_events import EnemyDefeatedEvent

event = EnemyDefeatedEvent(
    score_value=50,
    position=enemy.rect.center,
    enemy_id=id(enemy)
)
self.game_controller.event_manager.dispatch(event)
```

### Subscribing to Events

```python
# In LevelManager constructor
from hyperdrone_core.game_events import EnemyDefeatedEvent
game_controller_ref.event_manager.register_listener(EnemyDefeatedEvent, self.on_enemy_defeated)

# Event handler method
def on_enemy_defeated(self, event):
    self.add_score(event.score_value)
```

## Benefits

1. **Decoupling**: Components don't need direct references to each other
2. **Extensibility**: New listeners can be added without modifying existing code
3. **Maintainability**: Easier to understand and debug component interactions
4. **Flexibility**: Multiple components can react to the same event independently

## Current Implementation

The Event Bus is currently used for:

- Enemy defeat events: When an enemy is defeated, the `CombatController` dispatches an `EnemyDefeatedEvent`
- Score updates: The `LevelManager` listens for enemy defeat events to update the score
- Visual effects: The `GameController` listens for enemy defeat events to create explosion effects

## Future Extensions

The Event Bus can be extended to handle other game events such as:

- Player damage events
- Power-up collection events
- Level completion events
- Achievement unlocks
- UI notifications

To add a new event type:

1. Create a new event class in `game_events.py` that extends `GameEvent`
2. Dispatch the event when appropriate
3. Register listeners for the event in interested components