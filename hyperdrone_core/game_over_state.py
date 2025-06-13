# hyperdrone_core/game_over_state.py
import pygame
from .state import State
from settings_manager import get_setting

class GameOverState(State):
    def enter(self, previous_state=None, **kwargs):
        # Nothing to initialize for game over state
        pass
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Restart the game
                    self.game.level_manager.reset()
                    self.game.lives = 3
                    self.game.score = 0
                    self.game.state_manager.set_state("PlayingState")
                elif event.key == pygame.K_m:
                    # Return to main menu
                    self.game.state_manager.set_state("MainMenuState")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Let the UI manager handle drawing the game over screen
        pass