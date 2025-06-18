# ui/build_menu.py
import pygame
from settings_manager import get_setting, set_setting, get_asset_path
from constants import (
    WHITE, BLACK, CYAN, YELLOW, GREEN, RED, DARK_GREY, GOLD, GREY
)
try:
    from entities.turret import Turret 
except ImportError:
    class Turret: TURRET_COST, UPGRADE_COST, MAX_UPGRADE_LEVEL, MAX_TURRETS = 50, 100, 3, 5
try:
    from entities.maze_chapter3 import MazeChapter3
except ImportError:
    MazeChapter3 = None

class BuildMenu:
    def __init__(self, game_controller_ref, ui_manager_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.ui_manager = ui_manager_ref 
        self.asset_manager = asset_manager
        self.is_active = False 
        self.panel_height, self.panel_width = 90, 280
        height = get_setting("display", "HEIGHT", 1080)
        bottom_panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        self.panel_rect = pygame.Rect(20, height - bottom_panel_height - self.panel_height - 10, self.panel_width, self.panel_height)
        self.selected_turret_on_map = None
        self.hover_tile_rect = None
        self.hover_tile_color = (*GREEN[:3], 100)
        self.invalid_hover_tile_color = (*RED[:3], 100)
        self.current_hover_color = self.hover_tile_color
        self.place_turret_button_text, self.upgrade_turret_button_text = "", ""
        self.place_turret_rect, self.upgrade_turret_rect = None, None

    def activate(self):
        self.is_active = True
        self.selected_turret_on_map = None

    def deactivate(self):
        self.is_active = False
        self.selected_turret_on_map = None
        self.hover_tile_rect = None

    def update(self, mouse_pos, current_game_state, camera=None):
        if not self.is_active or current_game_state != "maze_defense_mode" or not getattr(self.game_controller, 'is_build_phase', False):
            self.hover_tile_rect = None; return

        if self.is_mouse_over_build_menu(mouse_pos):
            self.hover_tile_rect = None; return
        
        world_pos = camera.screen_to_world(mouse_pos) if camera else mouse_pos

        if self.game_controller.maze:
            offset = getattr(self.game_controller.maze, 'game_area_x_offset', 0)
            tile_size = get_setting("gameplay", "TILE_SIZE", 80)
            grid_col, grid_row = int((world_pos[0] - offset) / tile_size), int(world_pos[1] / tile_size)

            if 0 <= grid_row < self.game_controller.maze.actual_maze_rows and 0 <= grid_col < self.game_controller.maze.actual_maze_cols:
                tile_world_x, tile_world_y = grid_col * tile_size + offset, grid_row * tile_size
                self.hover_tile_rect = pygame.Rect(tile_world_x, tile_world_y, tile_size, tile_size)
                
                is_valid = isinstance(self.game_controller.maze, MazeChapter3) and self.game_controller.maze.grid[grid_row][grid_col] == 'T'
                self.current_hover_color = self.hover_tile_color if is_valid else self.invalid_hover_tile_color
            else: self.hover_tile_rect = None
        else: self.hover_tile_rect = None

    def draw(self, surface, camera=None):
        if not self.is_active: return

        pygame.draw.rect(surface, (*DARK_GREY[:3], 200), self.panel_rect, border_radius=10) 
        pygame.draw.rect(surface, CYAN, self.panel_rect, 2, border_radius=10)

        font_small = self.asset_manager.get_font("small_text", 24) or pygame.font.Font(None, 24)
        font_ui = self.asset_manager.get_font("ui_text", 28) or pygame.font.Font(None, 28)
        
        y_offset = self.panel_rect.top + 10
        title_surf = font_ui.render("Build Mode", True, WHITE)
        surface.blit(title_surf, (self.panel_rect.left + 10, y_offset)); y_offset += title_surf.get_height() + 10

        turret_cost = Turret.TURRET_COST if hasattr(Turret, 'TURRET_COST') else 50
        self.place_turret_button_text = f"Place Turret (LMB): {turret_cost}c"
        place_surf = font_small.render(self.place_turret_button_text, True, GREEN)
        self.place_turret_rect = place_surf.get_rect(topleft=(self.panel_rect.left + 10, y_offset)) 
        surface.blit(place_surf, self.place_turret_rect); y_offset += place_surf.get_height() + 5

        upgrade_cost = Turret.UPGRADE_COST if hasattr(Turret, 'UPGRADE_COST') else 100
        upgrade_text = "Select Turret to Upgrade"
        color = GREY
        if self.selected_turret_on_map:
            max_level = Turret.MAX_UPGRADE_LEVEL if hasattr(Turret, 'MAX_UPGRADE_LEVEL') else 3
            if self.selected_turret_on_map.upgrade_level < max_level:
                upgrade_text = f"Upgrade Lvl {self.selected_turret_on_map.upgrade_level + 1} ({upgrade_cost}c)"
                color = YELLOW
            else:
                upgrade_text = "Turret Max Level"
        self.upgrade_turret_button_text = f"{upgrade_text} (RMB)"
        upgrade_surf = font_small.render(self.upgrade_turret_button_text, True, color)
        self.upgrade_turret_rect = upgrade_surf.get_rect(topleft=(self.panel_rect.left + 10, y_offset))
        surface.blit(upgrade_surf, self.upgrade_turret_rect)

        if self.hover_tile_rect and camera:
            screen_rect = camera.apply_to_rect(self.hover_tile_rect)
            hover_surface = pygame.Surface(screen_rect.size, pygame.SRCALPHA)
            hover_surface.fill(self.current_hover_color) 
            surface.blit(hover_surface, screen_rect.topleft)
            pygame.draw.rect(surface, WHITE, screen_rect, 1)

    def handle_input(self, event, mouse_pos):
        if not self.is_active: return False
        
        # This now also handles selecting a turret to display its info, separate from upgrading.
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.panel_rect.collidepoint(mouse_pos):
                if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select', 0.5)
                return True
            
            # Use middle click (or another key) to select a turret for info display without upgrading
            if event.button == 2: # Middle mouse button
                world_pos = self.game_controller.camera.screen_to_world(mouse_pos) if self.game_controller.camera else mouse_pos
                clicked_turret = None
                for t in self.game_controller.turrets_group:
                    if t.rect.collidepoint(world_pos):
                        clicked_turret = t; break
                self.set_selected_turret(clicked_turret)
                return True

        return False

    def set_selected_turret(self, turret_sprite):
        """Sets the currently selected turret on the map to display upgrade info and its range."""
        if self.selected_turret_on_map and self.selected_turret_on_map != turret_sprite:
            if hasattr(self.selected_turret_on_map, 'show_range_indicator'):
                self.selected_turret_on_map.show_range_indicator = False 
        
        self.selected_turret_on_map = turret_sprite
        if turret_sprite and hasattr(turret_sprite, 'show_range_indicator'):
            turret_sprite.show_range_indicator = True

    def clear_selected_turret(self):
        """Clears the selected turret and hides its range indicator."""
        if self.selected_turret_on_map and hasattr(self.selected_turret_on_map, 'show_range_indicator'):
            self.selected_turret_on_map.show_range_indicator = False
        self.selected_turret_on_map = None

    def is_mouse_over_build_menu(self, mouse_pos):
        return self.is_active and self.panel_rect.collidepoint(mouse_pos)