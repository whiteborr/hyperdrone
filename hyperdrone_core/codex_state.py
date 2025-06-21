# hyperdrone_core/codex_state.py
import pygame
from .state import State
from settings_manager import get_setting

class CodexState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_codex()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("MainMenuState")
                else:
                    self.game.ui_flow_controller.handle_key_input(event.key, "codex_screen")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Let the UI manager handle drawing the codex screen
        # The UI manager already has all the necessary code to draw the codex
        pass