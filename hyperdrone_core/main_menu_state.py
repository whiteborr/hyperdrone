# hyperdrone_core/main_menu_state.pyAdd commentMore actions
import pygame
from .state import State
from settings_manager import get_setting

class MainMenuState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_main_menu()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.game.ui_flow_controller.handle_key_input(event.key, "main_menu")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        """
        Drawing is now handled by the UIManager to centralize UI rendering logic.
        This state's draw method should do nothing.
        """
        pass
