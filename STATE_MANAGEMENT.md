# HYPERDRONE State Management System

## Overview

The HYPERDRONE game uses a centralized state management system based on the State Design Pattern. This document explains how the state system works and how to use it effectively.

## Key Components

### 1. State Registry

The `StateRegistry` class in `hyperdrone_core/state_registry.py` serves as a central registry for all game states and their allowed transitions. It:

- Maintains a registry of all state classes
- Defines allowed transitions between states
- Records state transition history
- Validates state transitions

### 2. State Manager

The `StateManager` class in `hyperdrone_core/state_manager.py` handles the actual state transitions and manages the current state. It:

- Creates and initializes state objects
- Handles state transitions
- Updates music based on the current state
- Notifies the game controller about state changes

### 3. State Base Class

The `State` class in `hyperdrone_core/state.py` is the base class for all game states. It defines the interface that all states must implement:

- `enter()`: Called when entering the state
- `exit()`: Called when exiting the state
- `handle_events()`: Handles input events
- `update()`: Updates the state logic
- `draw()`: Renders the state

## State Transition Flow

1. A state transition is requested via `StateManager.set_state(state_id)`
2. The state manager checks if the transition is allowed using the registry
3. If allowed, the current state's `exit()` method is called
4. The new state is created and its `enter()` method is called
5. The transition is recorded in the registry's history
6. The game controller is notified about the state change

## Adding a New State

To add a new state:

1. Create a new class that inherits from `State`
2. Implement the required methods (`enter`, `exit`, `handle_events`, `update`, `draw`)
3. Register the state in `StateManager._register_state_classes()`
4. Define allowed transitions to/from the state in `StateManager._register_allowed_transitions()`

Example:

```python
# 1. Create the state class
class MyNewState(State):
    def enter(self, previous_state=None, **kwargs):
        # Initialize state
        pass
        
    def exit(self, next_state=None):
        # Clean up
        pass
        
    def handle_events(self, events):
        # Handle input
        pass
        
    def update(self, delta_time):
        # Update logic
        pass
        
    def draw(self, surface):
        # Render
        pass
```

Then in `state_manager.py`:

```python
# 2. Register the state class
def _register_state_classes(self):
    state_classes = {
        # ... existing states ...
        "MyNewState": MyNewState,
    }
    
# 3. Define allowed transitions
def _register_allowed_transitions(self):
    # ... existing transitions ...
    self.registry.register_transition("MainMenuState", "MyNewState")
    self.registry.register_transition("MyNewState", "MainMenuState")
```

## Debugging State Transitions

The `StateTransitionViewer` class in `hyperdrone_core/state_transition_viewer.py` provides a visual tool for debugging state transitions. To use it:

```python
from hyperdrone_core.state_transition_viewer import show_transition_viewer

# Call this from a debug menu or key press
show_transition_viewer()
```

This will open a window showing:
- The history of state transitions
- A graph of allowed transitions

## Best Practices

1. **Define Clear Transitions**: Only register transitions that make logical sense in the game flow
2. **Keep States Focused**: Each state should have a single responsibility
3. **Clean Up Resources**: Always clean up resources in the `exit()` method
4. **Use Kwargs for Parameters**: Pass additional parameters to states using kwargs
5. **Check Transition History**: Use the registry's history for debugging state flow issues