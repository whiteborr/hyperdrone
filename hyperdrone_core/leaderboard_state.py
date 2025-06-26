# hyperdrone_core/leaderboard_state.py
from pygame import KEYDOWN, K_ESCAPE
from .state import State

class LeaderboardState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_leaderboard()
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    leaderboard_index = 5  # "Leaderboard" is at index 5 in menu_options
                    self.game.state_manager.set_state("MainMenuState", selected_option=leaderboard_index)
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Drawing is now handled by the UIManager.
        pass
