# hyperdrone_core/main_menu_state.py
from pygame import KEYDOWN
from .state import State

class MainMenuState(State):
    def enter(self, previous_state=None, **kwargs):
        selected_option = kwargs.get('selected_option', 0)
        self.game.ui_flow_controller.initialize_main_menu(selected_option)
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                self.game.ui_flow_controller.handle_key_input(event.key, "main_menu")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        """
        Drawing is now handled by the UIManager to centralize UI rendering logic.
        This state's draw method should do nothing.
        """
        pass
