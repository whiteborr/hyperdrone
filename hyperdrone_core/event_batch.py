# hyperdrone_core/event_batch.py
import time
from collections import defaultdict

class EventBatch:
    """
    A class to batch similar events together to reduce processing overhead.
    """
    def __init__(self, event_type, batch_window_ms=50, max_batch_size=100):
        """
        Initialize an event batch.
        
        Args:
            event_type: The type of events this batch will handle
            batch_window_ms: Time window in milliseconds for batching events
            max_batch_size: Maximum number of events to batch before forcing dispatch
        """
        self.event_type = event_type
        self.batch_window_ms = batch_window_ms
        self.max_batch_size = max_batch_size
        self.events = []
        self.last_dispatch_time = 0
        
    def add(self, event):
        """
        Add an event to the batch.
        
        Args:
            event: The event to add
            
        Returns:
            bool: True if the batch should be dispatched, False otherwise
        """
        self.events.append(event)
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check if we should dispatch based on time window or batch size
        if (current_time - self.last_dispatch_time >= self.batch_window_ms or 
                len(self.events) >= self.max_batch_size):
            return True
        return False
        
    def clear(self):
        """Clear the batch and update the last dispatch time."""
        self.events = []
        self.last_dispatch_time = time.time() * 1000  # Convert to milliseconds
        
    def get_events(self):
        """Get all events in the batch."""
        return self.events
        
    def is_empty(self):
        """Check if the batch is empty."""
        return len(self.events) == 0


class BatchedEvent:
    """
    Base class for events that can be batched.
    """
    # Class attribute to indicate if this event type should be batched
    batchable = True
    
    # Class attribute to specify the batch window in milliseconds
    batch_window_ms = 50
    
    # Class attribute to specify the maximum batch size
    max_batch_size = 100
    
    @classmethod
    def create_batch_event(cls, events):
        """
        Create a batched event from multiple individual events.
        
        Args:
            events: List of events to batch
            
        Returns:
            A new event representing the batch
        """
        raise NotImplementedError("Subclasses must implement this method")