# hyperdrone_core/enter_name_state.py
import pygame
from .state import State
from settings_manager import get_setting

class EnterNameState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_enter_name()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.game.ui_flow_controller.handle_key_input(event.key, "enter_name")
    
    def draw(self, surface):
        # Get settings
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        white_color = get_setting("colors", "WHITE", (255, 255, 255))
        gold_color = get_setting("colors", "GOLD", (255, 215, 0))
        cyan_color = get_setting("colors", "CYAN", (0, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        surface.fill(black_color)
        
        # Draw stars background
        if hasattr(self.game.ui_flow_controller, 'menu_stars') and self.game.ui_flow_controller.menu_stars:
            for star_params in self.game.ui_flow_controller.menu_stars:
                pygame.draw.circle(surface, white_color, 
                                  (int(star_params[0]), int(star_params[1])), star_params[3])
        
        # Draw title
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        title_surf = font.render("High Score!", True, gold_color)
        surface.blit(title_surf, title_surf.get_rect(center=(width // 2, height//2 - 100)))
        
        # Draw prompt
        font = self.game.asset_manager.get_font("medium_text", 48) or pygame.font.Font(None, 48)
        prompt_surf = font.render("Enter Your Name:", True, white_color)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(width // 2, height//2)))
        
        # Draw name input
        name_input = self.game.ui_flow_controller.player_name_input_cache
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        name_surf = font.render(f"{name_input}_", True, cyan_color)
        surface.blit(name_surf, name_surf.get_rect(center=(width//2, height//2 + 80)))