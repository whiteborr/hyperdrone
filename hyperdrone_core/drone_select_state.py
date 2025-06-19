# hyperdrone_core/drone_select_state.py
import pygame
from .state import State
from settings_manager import get_setting

class DroneSelectState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_drone_select()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("MainMenuState")
                else:
                    self.game.ui_flow_controller.handle_key_input(event.key, "drone_select")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Drawing is now handled by the UIManager.
        pass