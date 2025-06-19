# HYPERDRONE AI System Documentation

## Overview

The HYPERDRONE AI system uses a behavior-based architecture that provides flexible, modular, and extensible enemy intelligence. The system separates AI logic into discrete behaviors that can be combined and transitioned between dynamically.

## Architecture

### Core Components

#### 1. BaseBehavior
- **Purpose**: Abstract base class defining the behavior interface
- **Key Method**: `execute()` - called every frame to update enemy state
- **Responsibilities**: Provides common interface for all AI behaviors

#### 2. Behavior Implementations
Each behavior encapsulates specific AI logic:

- **ChasePlayerBehavior**: Aggressive pursuit using A* pathfinding
- **TRBPatrolBehavior**: Patrol movement within defined radius
- **TRBDashBehavior**: High-speed dash attacks toward/away from player
- **WallFollowBehavior**: Wall-following navigation for stuck entities
- **RetreatBehavior**: Tactical withdrawal when health is low

#### 3. Pathfinding Component
- **A* Algorithm**: Optimal pathfinding with Manhattan distance heuristic
- **Dynamic Goal Adjustment**: Finds alternative targets when primary goal unreachable
- **Wall Following**: Navigation assistance when pathfinding fails
- **Stuck Detection**: Automatic re-pathing when entity doesn't make progress

## Behavior Details

### ChasePlayerBehavior
```python
# Features:
- A* pathfinding for optimal route calculation
- Dynamic target updating based on player movement
- Range-based shooting for armed enemies
- Speed boosts for close-range attacks (SentinelDrones)
- Automatic transitions based on aggro range
```

**Use Cases**: Primary combat AI, boss encounters, aggressive enemies

### TRBPatrolBehavior
```python
# Features:
- Patrol point selection within defined radius
- Wait periods at patrol points for realistic behavior
- Smooth transitions to chase behavior when player detected
- Stuck detection and recovery
- Hover movement while waiting
```

**Use Cases**: Area defense, ambient AI, guard patterns

### TRBDashBehavior
```python
# Features:
- High-speed movement toward or away from player
- Dynamic direction calculation based on player distance
- Wall collision detection and early termination
- Automatic transition back to patrol/chase
- Visual rotation to match dash direction
```

**Use Cases**: Hit-and-run attacks, evasive maneuvers, special attacks

### RetreatBehavior
```python
# Features:
- Health threshold-based activation
- Pathfinding to distant safe positions
- Increased movement speed during retreat
- Fallback to direct movement if no path found
- Automatic return to combat when healed
```

**Use Cases**: Tactical AI, boss phase transitions, survival instincts

## Pathfinding System

### A* Implementation
The pathfinding system uses a sophisticated A* implementation:

```python
def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    # Priority queue for efficient node selection
    # Manhattan distance heuristic
    # 4-directional movement
    # Path reconstruction via parent pointers
```

**Key Features**:
- **Optimal Paths**: Guarantees shortest path when one exists
- **Efficient**: Uses priority queue for O(log n) node selection
- **Robust**: Handles edge cases and invalid inputs gracefully
- **Flexible**: Works with any grid-based maze representation

### Dynamic Goal Adjustment
When direct pathfinding fails:

1. **Alternative Target Selection**: Finds nearby reachable positions
2. **Intermediate Goals**: Uses stepping stones to reach final destination
3. **Wall Following**: Navigates around obstacles using wall-following
4. **Stuck Recovery**: Detects and resolves pathfinding deadlocks

## Behavior Transitions

### State Machine Logic
Behaviors can transition between each other based on game conditions:

```python
# Example transition logic
if player_distance > aggro_radius:
    enemy.set_behavior(WallFollowBehavior(enemy))
elif enemy.health < max_health * 0.3:
    enemy.set_behavior(RetreatBehavior(enemy))
else:
    enemy.set_behavior(ChasePlayerBehavior(enemy))
```

### Transition Triggers
- **Distance-based**: Player proximity/distance
- **Health-based**: Low health triggers retreat
- **Time-based**: Patrol duration, dash duration
- **Event-based**: Player actions, environmental changes

## Performance Considerations

### Optimization Strategies
1. **Pathfinding Caching**: Reuse paths when targets haven't moved significantly
2. **Update Intervals**: Different behaviors update at different frequencies
3. **Early Termination**: Stop expensive calculations when conditions change
4. **Spatial Partitioning**: Limit pathfinding search radius

### Scalability
- **Behavior Pooling**: Reuse behavior instances to reduce garbage collection
- **Selective Updates**: Only update active/visible enemies
- **LOD System**: Simplified AI for distant enemies

## Adding New Behaviors

### Step 1: Create Behavior Class
```python
class NewBehavior(BaseBehavior):
    def __init__(self, enemy):
        super().__init__(enemy)
        # Initialize behavior-specific state
        
    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        # Implement behavior logic
        # Handle transitions to other behaviors
```

### Step 2: Register with Enemy
```python
# In enemy initialization or behavior transition
enemy.set_behavior(NewBehavior(enemy))
```

### Step 3: Configure Transitions
```python
# Add transition logic in existing behaviors
if some_condition:
    self.enemy.set_behavior(NewBehavior(self.enemy))
```

## Configuration

### Enemy AI Settings
AI behaviors are configurable through the settings system:

```json
{
  "enemies": {
    "RETREAT_HEALTH_THRESHOLD": 0.3,
    "MIN_RETREAT_DISTANCE_TILES": 8,
    "RETREAT_SPEED_MULTIPLIER": 1.2
  }
}
```

### Behavior Parameters
Each behavior can be tuned via settings:
- Movement speeds and ranges
- Transition thresholds
- Timing parameters
- Pathfinding constraints

## Debugging and Visualization

### Debug Information
- Path visualization for pathfinding debugging
- Behavior state display
- Transition history tracking
- Performance metrics

### Common Issues and Solutions
1. **Stuck Enemies**: Implement stuck detection and recovery
2. **Erratic Movement**: Add smoothing and interpolation
3. **Performance Issues**: Optimize pathfinding frequency
4. **Unrealistic Behavior**: Add randomization and delays

## Future Enhancements

### Planned Features
- **Group Behaviors**: Coordinated multi-enemy tactics
- **Learning AI**: Adaptive behaviors based on player patterns
- **Hierarchical AI**: Complex behavior trees and state machines
- **Predictive Pathfinding**: Anticipate player movement

### Extension Points
- **Custom Behaviors**: Easy integration of new behavior types
- **Behavior Modifiers**: Stackable effects that modify existing behaviors
- **Dynamic Parameters**: Runtime adjustment of behavior parameters
- **Scripted Sequences**: Predefined behavior sequences for special events