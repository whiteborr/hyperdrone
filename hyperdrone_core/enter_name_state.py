# hyperdrone_core/enter_name_state.py
import pygame
from .state import State

class EnterNameState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_enter_name()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.game.ui_flow_controller.handle_key_input(event.key, "enter_name")
    
    def draw(self, surface):
        surface.fill(self.game.gs.BLACK)
        
        # Draw stars background
        if hasattr(self.game.ui_flow_controller, 'menu_stars') and self.game.ui_flow_controller.menu_stars:
            for star_params in self.game.ui_flow_controller.menu_stars:
                pygame.draw.circle(surface, self.game.gs.WHITE, 
                                  (int(star_params[0]), int(star_params[1])), star_params[3])
        
        # Draw title
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        title_surf = font.render("High Score!", True, self.game.gs.GOLD)
        surface.blit(title_surf, title_surf.get_rect(center=(self.game.gs.WIDTH // 2, self.game.gs.HEIGHT//2 - 100)))
        
        # Draw prompt
        font = self.game.asset_manager.get_font("medium_text", 48) or pygame.font.Font(None, 48)
        prompt_surf = font.render("Enter Your Name:", True, self.game.gs.WHITE)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(self.game.gs.WIDTH // 2, self.game.gs.HEIGHT//2)))
        
        # Draw name input
        name_input = self.game.ui_flow_controller.player_name_input_cache
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        name_surf = font.render(f"{name_input}_", True, self.game.gs.CYAN)
        surface.blit(name_surf, name_surf.get_rect(center=(self.game.gs.WIDTH//2, self.game.gs.HEIGHT//2 + 80)))