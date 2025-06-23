# hyperdrone_core/codex_state.py
from pygame import KEYDOWN, K_ESCAPE
from .state import State
from settings_manager import get_setting

class CodexState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_codex()
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    codex_index = 3  # "Codex" is at index 3 in menu_options
                    self.game.state_manager.set_state("MainMenuState", selected_option=codex_index)
                else:
                    self.game.ui_flow_controller.handle_key_input(event.key, "codex_screen")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Drawing is now handled by the UIManager.
        pass
