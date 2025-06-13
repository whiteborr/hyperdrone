# hyperdrone_core/settings_state.py
import pygame
from .state import State
from settings_manager import get_setting

class SettingsState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_settings(self.game._get_settings_menu_items_data_structure())
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("MainMenuState")
                else:
                    self.game.ui_flow_controller.handle_key_input(event.key, "settings_menu")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Let the UI manager handle drawing the settings menu
        # The UI manager already has all the necessary code to draw the settings
        pass