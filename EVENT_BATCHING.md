# Event Batching System

## Overview

The event batching system optimizes performance by combining similar events that occur in rapid succession. This reduces overhead during intense gameplay when many events are triggered simultaneously.

## Key Components

### 1. EventBatch Class

The `EventBatch` class in `hyperdrone_core/event_batch.py` manages batches of similar events:

- Collects events of the same type within a time window
- Dispatches batched events when the time window expires or batch size limit is reached
- Maintains timing information for efficient processing

### 2. BatchedEvent Base Class

The `BatchedEvent` class in `hyperdrone_core/event_batch.py` defines the interface for batchable events:

- `batchable` flag indicates if an event type can be batched
- `batch_window_ms` defines the time window for batching
- `max_batch_size` sets the maximum number of events in a batch
- `create_batch_event()` method creates a combined event from multiple individual events

### 3. Enhanced EventManager

The `EventManager` class in `hyperdrone_core/event_manager.py` has been updated to:

- Detect and batch batchable events
- Manage event batches for different event types
- Dispatch batched events when appropriate
- Fall back to individual event dispatch when batching fails

## Batchable Event Types

The following event types are configured for batching:

1. **EnemyDefeatedEvent**
   - Batched when multiple enemies are defeated within 50ms
   - Combines score values and positions
   - Creates a single `BatchedEnemyDefeatedEvent`

2. **BulletHitEvent**
   - Batched when multiple bullets hit targets within 30ms
   - Combines hit positions and target information
   - Creates a single `BatchedBulletHitEvent`

3. **ParticleEmitEvent**
   - Batched when multiple particle emissions occur within 20ms
   - Combines particle types, positions, and counts
   - Creates a single `BatchedParticleEmitEvent`

## How to Create a Batchable Event

1. Create your event class inheriting from both `GameEvent` and `BatchedEvent`:

```python
class MyEvent(GameEvent, BatchedEvent):
    batchable = True
    batch_window_ms = 50  # Batch within 50ms
    max_batch_size = 20   # Or when we reach 20 events
    
    def __init__(self, data):
        self.data = data
    
    @classmethod
    def create_batch_event(cls, events):
        # Combine data from all events
        combined_data = [event.data for event in events]
        return BatchedMyEvent(combined_data)
```

2. Create a corresponding batched event class:

```python
class BatchedMyEvent(GameEvent):
    def __init__(self, combined_data):
        self.combined_data = combined_data
        self.count = len(combined_data)
```

3. Register listeners for both individual and batched events:

```python
event_manager.register_listener(MyEvent, handle_my_event)
event_manager.register_listener(BatchedMyEvent, handle_batched_my_event)
```

## Performance Considerations

- Event batching is most effective during intense gameplay with many similar events
- The batch window should be short enough to maintain responsiveness but long enough to catch event bursts
- Batch size limits prevent memory issues during sustained event bursts
- Batching can be disabled via settings for debugging or if it causes issues

## Configuration

Event batching can be configured in the settings:

```json
{
  "gameplay": {
    "EVENT_BATCHING_ENABLED": true
  }
}
```

Individual event types can also have custom batch settings:

```python
class MyEvent(GameEvent, BatchedEvent):
    batchable = True
    batch_window_ms = 100  # Custom window
    max_batch_size = 50    # Custom batch size
```