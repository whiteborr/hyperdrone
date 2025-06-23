# hyperdrone_core/enter_name_state.py
from pygame import KEYDOWN
from .state import State

class EnterNameState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_enter_name()
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                self.game.ui_flow_controller.handle_key_input(event.key, "enter_name")
    
    def draw(self, surface):
        # Drawing is now handled by the UIManager.
        pass
