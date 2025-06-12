# hyperdrone_core/settings_state.py
import pygame
from .state import State

class SettingsState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_settings(self.game._get_settings_menu_items_data_structure())
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("MainMenuState")
                else:
                    self.game.ui_flow_controller.handle_key_input(event.key, "settings_menu")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        surface.fill(self.game.gs.BLACK)
        
        # Draw stars background if available
        if hasattr(self.game.ui_flow_controller, 'menu_stars') and self.game.ui_flow_controller.menu_stars:
            for star_params in self.game.ui_flow_controller.menu_stars:
                pygame.draw.circle(surface, self.game.gs.WHITE, 
                                  (int(star_params[0]), int(star_params[1])), star_params[3])
        
        # Draw title
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        title_surf = font.render("Settings", True, self.game.gs.GOLD)
        surface.blit(title_surf, title_surf.get_rect(center=(self.game.gs.WIDTH // 2, 80)))
        
        # Draw settings items
        settings_items = self.game.ui_flow_controller.settings_items_data
        selected_index = self.game.ui_flow_controller.selected_setting_index
        font_setting = self.game.asset_manager.get_font("ui_text", 28) or pygame.font.Font(None, 28)
        
        start_y = 200
        for i, item in enumerate(settings_items):
            y_pos = start_y + i * 50
            color = self.game.gs.YELLOW if i == selected_index else self.game.gs.WHITE
            
            # Draw label
            label_surf = font_setting.render(item['label'], True, color)
            surface.blit(label_surf, (200, y_pos))
            
            # Draw value
            val_text = ""
            if item['type'] != 'action':
                current_val = self.game.gs.get_game_setting(item['key'])
                val_to_format = current_val
                if item.get("is_ms_to_sec"): 
                    val_to_format /= 1000
                
                if 'display_format' in item:
                    val_text = item['display_format'].format(val_to_format)
                elif 'get_display' in item:
                    val_text = item['get_display'](current_val)
                else:
                    val_text = str(current_val)
                    
                if item['type'] in ["numeric", "choice"]: 
                    val_text = f"< {val_text} >"
            else: 
                val_text = "[PRESS ENTER]"
            
            val_surf = font_setting.render(val_text, True, color)
            surface.blit(val_surf, (self.game.gs.WIDTH - 200 - val_surf.get_width(), y_pos))