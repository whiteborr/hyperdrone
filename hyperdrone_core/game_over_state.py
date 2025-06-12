# hyperdrone_core/game_over_state.py
import pygame
from .state import State

class GameOverState(State):
    def enter(self, previous_state=None, **kwargs):
        pass
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Restart game
                    self.game.lives = self.game.gs.get_game_setting("PLAYER_LIVES")
                    self.game.state_manager.set_state("PlayingState")
                elif event.key == pygame.K_m:
                    # Return to main menu
                    self.game.state_manager.set_state("MainMenuState")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Draw background overlay
        overlay = pygame.Surface((self.game.gs.WIDTH, self.game.gs.HEIGHT), pygame.SRCALPHA)
        overlay.fill((50, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Draw game over text
        font = self.game.asset_manager.get_font("title_text", 90) or pygame.font.Font(None, 90)
        title_surf = font.render("DRONE DESTROYED", True, self.game.gs.RED)
        surface.blit(title_surf, title_surf.get_rect(center=(self.game.gs.WIDTH // 2, 
                                                           self.game.gs.HEIGHT // 2 - 100)))
        
        # Draw prompt
        font = self.game.asset_manager.get_font("medium_text", 48) or pygame.font.Font(None, 48)
        prompt_surf = font.render("Press 'R' to Restart or 'M' for Menu", True, self.game.gs.WHITE)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(self.game.gs.WIDTH // 2, 
                                                             self.game.gs.HEIGHT // 2 + 50)))