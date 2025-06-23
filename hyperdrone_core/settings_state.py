# hyperdrone_core/settings_state.py
from pygame import KEYDOWN, K_ESCAPE
from .state import State

class SettingsState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_settings(self.game._get_settings_menu_items_data_structure())
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    settings_index = 4  # "Settings" is at index 4 in menu_options
                    self.game.state_manager.set_state("MainMenuState", selected_option=settings_index)
                else:
                    self.game.ui_flow_controller.handle_key_input(event.key, "SettingsState")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Let the UI manager handle drawing the settings menu
        # The UI manager already has all the necessary code to draw the settingsAdd commentMore actions
        pass
