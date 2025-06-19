# hyperdrone_core/leaderboard_state.py
import pygame
from .state import State

class LeaderboardState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_leaderboard()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("MainMenuState")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Drawing is now handled by the UIManager.
        pass