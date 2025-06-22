# hyperdrone_core/enter_name_state.py
import pygame
from .state import State
from settings_manager import get_setting

class EnterNameState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_enter_name()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.game.ui_flow_controller.handle_key_input(event.key, "enter_name")
    
    def draw(self, surface):
        # Drawing is now handled by the UIManager.
        pass
