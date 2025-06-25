# hyperdrone_core/state_registry.py
from logging import getLogger, warning, info

logger = getLogger(__name__)

class StateRegistry:
    """
    Central registry for game states and their transitions.
    Makes state transitions explicit and easier to track.
    """
    def __init__(self):
        # Dictionary of registered states: {state_id: state_class}
        self.states = {}
        
        # Dictionary of allowed transitions: {from_state: [to_state1, to_state2, ...]}
        self.allowed_transitions = {}
        
        # Dictionary to track transition history: [(from_state, to_state, timestamp), ...]
        self.transition_history = []
        
        # Maximum history entries to keep
        self.max_history = 100
    
    def register_state(self, state_id, state_class):
        """
        Register a state class with the registry.
        
        Args:
            state_id: Unique identifier for the state
            state_class: The state class to register
        """
        if state_id in self.states:
            warning(f"State '{state_id}' already registered, overwriting")
        
        self.states[state_id] = state_class
        
        # Initialize empty allowed transitions list if not exists
        if state_id not in self.allowed_transitions:
            self.allowed_transitions[state_id] = []
            
        info(f"Registered state: {state_id}")
    
    def register_transition(self, from_state, to_state):
        """
        Register an allowed transition between states.
        
        Args:
            from_state: Source state ID
            to_state: Destination state ID
        """
        # Ensure both states are registered
        if from_state not in self.states:
            warning(f"Cannot register transition: Source state '{from_state}' not registered")
            return False
            
        if to_state not in self.states:
            warning(f"Cannot register transition: Destination state '{to_state}' not registered")
            return False
        
        # Add the allowed transition
        if to_state not in self.allowed_transitions.get(from_state, []):
            if from_state not in self.allowed_transitions:
                self.allowed_transitions[from_state] = []
            
            self.allowed_transitions[from_state].append(to_state)
            info(f"Registered transition: {from_state} -> {to_state}")
        
        return True
    
    def is_transition_allowed(self, from_state, to_state):
        """
        Check if a transition between states is allowed.
        
        Args:
            from_state: Source state ID
            to_state: Destination state ID
            
        Returns:
            bool: True if transition is allowed, False otherwise
        """
        # Special case: Any state can transition to itself
        if from_state == to_state:
            return True
            
        # Check if the transition is explicitly allowed
        return to_state in self.allowed_transitions.get(from_state, [])
    
    def record_transition(self, from_state, to_state, timestamp):
        """
        Record a state transition in the history.
        
        Args:
            from_state: Source state ID
            to_state: Destination state ID
            timestamp: Time when the transition occurred
        """
        self.transition_history.append((from_state, to_state, timestamp))
        
        # Trim history if it exceeds max size
        if len(self.transition_history) > self.max_history:
            self.transition_history = self.transition_history[-self.max_history:]
    
    def get_state_class(self, state_id):
        """
        Get the class for a registered state.
        
        Args:
            state_id: The state identifier
            
        Returns:
            The state class or None if not found
        """
        return self.states.get(state_id)
    
    def get_allowed_transitions(self, from_state):
        """
        Get all allowed transitions from a state.
        
        Args:
            from_state: Source state ID
            
        Returns:
            list: List of allowed destination states
        """
        return self.allowed_transitions.get(from_state, [])
    
    def get_transition_history(self, limit=None):
        """
        Get the transition history.
        
        Args:
            limit: Maximum number of entries to return (newest first)
            
        Returns:
            list: List of (from_state, to_state, timestamp) tuples
        """
        if limit is None:
            return self.transition_history
        
        return self.transition_history[-limit:]

# Create a global instance for easy access
state_registry = StateRegistry()
