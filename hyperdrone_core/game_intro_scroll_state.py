# hyperdrone_core/game_intro_scroll_state.py
import pygame
from .state import State
from settings_manager import get_setting

class GameIntroScrollState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_game_intro(self.game._load_intro_data_from_json_internal())
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.game.ui_flow_controller.advance_intro_screen()
                elif event.key == pygame.K_ESCAPE:
                    self.game.ui_flow_controller.skip_intro()
    
    def update(self, delta_time):
        if self.game.ui_flow_controller.intro_sequence_finished:
            self.game.state_manager.set_state("StoryMapState")
    
    def draw(self, surface):
        # Let the UI manager handle drawing the game intro screen
        # The UI manager already has all the necessary code to draw the intro
        pass