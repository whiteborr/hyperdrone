# hyperdrone_core/state.py
class State:
    """Base State class for the State Design Pattern"""
    def __init__(self, game_controller):
        self.game = game_controller
        
    def enter(self, previous_state=None, **kwargs):
        """Called when entering this state"""
        pass
        
    def exit(self, next_state=None):
        """Called when exiting this state"""
        pass
        
    def handle_events(self, events):
        """Handle discrete events like key presses"""
        pass
        
    def update(self, delta_time):
        """Handle continuous updates"""
        pass
        
    def draw(self, surface):
        """Draw the scene"""
        pass
        
    def get_state_id(self):
        """Returns a unique identifier for this state"""
        return self.__class__.__name__
