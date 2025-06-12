# hyperdrone_core/main_menu_state.py
import pygame
from .state import State

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
        surface.fill(self.game.gs.BLACK)
        
        # Draw stars background if available
        if hasattr(self.game.ui_flow_controller, 'menu_stars') and self.game.ui_flow_controller.menu_stars:
            for star_params in self.game.ui_flow_controller.menu_stars:
                pygame.draw.circle(surface, self.game.gs.WHITE, 
                                  (int(star_params[0]), int(star_params[1])), star_params[3])
        
        # Draw menu logo if available
        if self.game.ui_manager.ui_asset_surfaces["menu_background"]:
            logo_surf = self.game.ui_manager.ui_asset_surfaces["menu_background"]
            screen_width = self.game.gs.get_game_setting("WIDTH")
            screen_height = self.game.gs.get_game_setting("HEIGHT")
            scaled_bg_surf = pygame.transform.scale(logo_surf, (screen_width, screen_height))
            surface.blit(scaled_bg_surf, (0, 0))
        
        # Draw menu options
        options = self.game.ui_flow_controller.menu_options
        selected_index = self.game.ui_flow_controller.selected_menu_option
        start_y = self.game.gs.get_game_setting("HEIGHT") * 0.55
        option_height = 60
        font_menu = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        
        for i, option_text in enumerate(options):
            color = self.game.gs.GOLD if i == selected_index else self.game.gs.WHITE
            text_surf = font_menu.render(option_text, True, color)
            text_rect = text_surf.get_rect(center=(self.game.gs.get_game_setting("WIDTH") // 2, 
                                                  start_y + i * option_height))
            surface.blit(text_surf, text_rect)