# hyperdrone_core/drone_select_state.py
import pygame
from .state import State

class DroneSelectState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_drone_select()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("MainMenuState")
                else:
                    self.game.ui_flow_controller.handle_key_input(event.key, "drone_select_menu")
    
    def draw(self, surface):
        surface.fill(self.game.gs.BLACK)
        
        # Draw stars background
        if hasattr(self.game.ui_flow_controller, 'menu_stars') and self.game.ui_flow_controller.menu_stars:
            for star_params in self.game.ui_flow_controller.menu_stars:
                pygame.draw.circle(surface, self.game.gs.WHITE, 
                                  (int(star_params[0]), int(star_params[1])), star_params[3])
        
        # Draw title
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        title_surf = font.render("Select Drone", True, self.game.gs.GOLD)
        surface.blit(title_surf, title_surf.get_rect(center=(self.game.gs.WIDTH // 2, 80)))
        
        # Draw drone preview
        ui_flow = self.game.ui_flow_controller
        if not ui_flow.drone_select_options:
            return
            
        selected_drone_id = ui_flow.drone_select_options[ui_flow.selected_drone_preview_index]
        drone_config = self.game.drone_system.get_drone_config(selected_drone_id)
        is_unlocked = self.game.drone_system.is_drone_unlocked(selected_drone_id)
        
        # Draw drone sprite
        sprite_asset_key = drone_config.get("sprite_path", "").replace("assets/", "")
        sprite_surf = self.game.asset_manager.get_image(sprite_asset_key, scale_to_size=(256, 256))
        if sprite_surf:
            surface.blit(sprite_surf, sprite_surf.get_rect(center=(self.game.gs.WIDTH/2, self.game.gs.HEIGHT/2 - 100)))
        
        # Draw drone name
        font = self.game.asset_manager.get_font("medium_text", 48) or pygame.font.Font(None, 48)
        name_surf = font.render(drone_config.get("name"), True, 
                               self.game.gs.WHITE if is_unlocked else self.game.gs.GREY)
        surface.blit(name_surf, name_surf.get_rect(center=(self.game.gs.WIDTH/2, self.game.gs.HEIGHT/2 + 100)))
        
        # Draw drone description
        font = self.game.asset_manager.get_font("ui_text", 24) or pygame.font.Font(None, 24)
        desc_surf = font.render(drone_config.get("description"), True, self.game.gs.CYAN)
        surface.blit(desc_surf, desc_surf.get_rect(center=(self.game.gs.WIDTH/2, self.game.gs.HEIGHT/2 + 150)))
        
        # Draw unlock condition if locked
        if not is_unlocked:
            unlock_cond = drone_config.get("unlock_condition", {})
            unlock_desc = unlock_cond.get("description", "Locked")
            font = self.game.asset_manager.get_font("ui_text", 28) or pygame.font.Font(None, 28)
            unlock_surf = font.render(unlock_desc, True, self.game.gs.RED)
            surface.blit(unlock_surf, unlock_surf.get_rect(center=(self.game.gs.WIDTH/2, self.game.gs.HEIGHT/2 + 200)))