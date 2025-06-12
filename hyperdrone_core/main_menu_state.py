# hyperdrone_core/main_menu_state.py
import pygame
from .state import State
from settings_manager import get_setting
from constants import *

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
        surface.fill(BLACK)
        
        # Draw stars background if available
        if hasattr(self.game.ui_flow_controller, 'menu_stars') and self.game.ui_flow_controller.menu_stars:
            for star_params in self.game.ui_flow_controller.menu_stars:
                pygame.draw.circle(surface, WHITE, 
                                  (int(star_params[0]), int(star_params[1])), star_params[3])
        
        # Draw menu logo if available
        if self.game.ui_manager.ui_asset_surfaces["menu_background"]:
            logo_surf = self.game.ui_manager.ui_asset_surfaces["menu_background"]
            screen_width = get_setting("display", "WIDTH", 1920)
            screen_height = get_setting("display", "HEIGHT", 1080)
            scaled_bg_surf = pygame.transform.scale(logo_surf, (screen_width, screen_height))
            surface.blit(scaled_bg_surf, (0, 0))
        
        # Draw menu options
        options = self.game.ui_flow_controller.menu_options
        selected_index = self.game.ui_flow_controller.selected_menu_option
        screen_height = get_setting("display", "HEIGHT", 1080)
        start_y = screen_height * 0.55
        option_height = 60
        font_menu = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        
        for i, option_text in enumerate(options):
            color = GOLD if i == selected_index else WHITE
            text_surf = font_menu.render(option_text, True, color)
            screen_width = get_setting("display", "WIDTH", 1920)
            text_rect = text_surf.get_rect(center=(screen_width // 2, 
                                                  start_y + i * option_height))
            surface.blit(text_surf, text_rect)