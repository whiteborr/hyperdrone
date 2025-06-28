# hyperdrone_core/game_intro_scroll_state.py
from pygame import KEYDOWN, K_SPACE, K_ESCAPE
from .state import State

class GameIntroScrollState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_game_intro(self.game._load_intro_data())
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_SPACE:
                    self.game.ui_flow_controller.advance_intro_screen()
                elif event.key == K_ESCAPE:
                    self.game.ui_flow_controller.skip_intro()
    
    def update(self, delta_time):
        if self.game.ui_flow_controller.intro_sequence_finished:
            self.game.state_manager.set_state("StoryMapState")
    
    def draw(self, surface):
        # Let the UI manager handle drawing the game intro screen
        # The UI manager already has all the necessary code to draw the introAdd commentMore actions
        pass
