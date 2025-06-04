# ui/build_menu.py
import pygame
import game_settings as gs
from game_settings import (
    WHITE, BLACK, CYAN, YELLOW, GREEN, RED, DARK_GREY, GOLD, GREY, TILE_SIZE, BOTTOM_PANEL_HEIGHT
)
# We'll need access to the Turret class for its cost constants
try:
    from entities.turret import Turret # Assuming Turret class is in entities
except ImportError:
    print("BuildMenu: Could not import Turret class. Costs will be placeholders.")
    # Define placeholders if Turret class isn't available during isolated development
    class Turret:
        TURRET_COST = 50
        UPGRADE_COST = 100
        MAX_UPGRADE_LEVEL = 3


class BuildMenu:
    def __init__(self, game_controller_ref, ui_manager_ref, fonts):
        """
        Initializes the Build Menu.
        Args:
            game_controller_ref: Reference to the main GameController.
            ui_manager_ref: Reference to the UIManager (for shared resources like fonts).
            fonts (dict): A dictionary of pre-loaded fonts from UIManager.
        """
        self.game_controller = game_controller_ref
        self.ui_manager = ui_manager_ref 
        self.fonts = fonts

        self.is_active = False 
        self.panel_height = 90
        self.panel_width = 280 
        self.panel_rect = pygame.Rect(
            20, 
            gs.HEIGHT - BOTTOM_PANEL_HEIGHT - self.panel_height - 10, 
            self.panel_width, 
            self.panel_height
        )
        self.selected_turret_on_map = None 
        
        self.hover_tile_rect = None 
        self.hover_tile_color = (*GREEN[:3], 100) 
        self.invalid_hover_tile_color = (*RED[:3], 100) 
        self.current_hover_color = self.hover_tile_color 

        self.place_turret_button_text = "" 
        self.upgrade_turret_button_text = ""
        self.place_turret_rect = None
        self.upgrade_turret_rect = None


    def activate(self):
        """Activates the build menu display."""
        self.is_active = True
        self.selected_turret_on_map = None 
        print("BuildMenu: Activated.")

    def deactivate(self):
        """Deactivates the build menu display."""
        self.is_active = False
        self.selected_turret_on_map = None
        self.hover_tile_rect = None 
        print("BuildMenu: Deactivated.")

    def update(self, mouse_pos, current_game_state):
        """
        Updates the build menu state, like hover effects.
        """
        if not self.is_active or \
           current_game_state != gs.GAME_STATE_MAZE_DEFENSE or \
           not hasattr(self.game_controller, 'is_build_phase') or \
           not self.game_controller.is_build_phase:
            self.hover_tile_rect = None
            return

        if not self.is_mouse_over_build_menu(mouse_pos):
            if self.game_controller.maze: 
                current_maze_x_offset = getattr(self.game_controller.maze, 'game_area_x_offset', 0)
                
                grid_col = (mouse_pos[0] - current_maze_x_offset) // TILE_SIZE
                grid_row = mouse_pos[1] // TILE_SIZE

                if 0 <= grid_row < self.game_controller.maze.actual_maze_rows and \
                   0 <= grid_col < self.game_controller.maze.actual_maze_cols:
                    
                    tile_screen_x = grid_col * TILE_SIZE + current_maze_x_offset
                    tile_screen_y = grid_row * TILE_SIZE
                    self.hover_tile_rect = pygame.Rect(tile_screen_x, tile_screen_y, TILE_SIZE, TILE_SIZE)
                    
                    is_valid_spot = True 
                    tile_value = self.game_controller.maze.grid[grid_row][grid_col]
                    
                    if tile_value != 0: 
                        is_valid_spot = False
                    else: 
                        temp_check_rect = pygame.Rect(0,0,TILE_SIZE//2, TILE_SIZE//2)
                        temp_check_rect.center = (tile_screen_x + TILE_SIZE//2, tile_screen_y + TILE_SIZE//2)
                        
                        # Access turrets via self.game_controller.turrets_group
                        for t in self.game_controller.turrets_group:
                            if t.rect.colliderect(temp_check_rect):
                                is_valid_spot = False; break
                        if self.game_controller.player and hasattr(self.game_controller.player, 'rect') and self.game_controller.player.rect.colliderect(temp_check_rect):
                            is_valid_spot = False
                    
                    self.current_hover_color = self.hover_tile_color if is_valid_spot else self.invalid_hover_tile_color
                else:
                    self.hover_tile_rect = None 
            else:
                self.hover_tile_rect = None 
        else:
            self.hover_tile_rect = None 

    def draw(self, surface):
        """Draws the build menu UI elements."""
        if not self.is_active:
            return

        pygame.draw.rect(surface, (*DARK_GREY[:3], 200), self.panel_rect, border_radius=10) 
        pygame.draw.rect(surface, CYAN, self.panel_rect, 2, border_radius=10) 

        font_small = self.fonts.get("small_text", pygame.font.Font(None, 24))
        font_ui = self.fonts.get("ui_text", pygame.font.Font(None, 28))
        
        y_offset = self.panel_rect.top + 10

        title_surf = font_ui.render("Build Mode", True, WHITE)
        surface.blit(title_surf, (self.panel_rect.left + 10, y_offset))
        y_offset += title_surf.get_height() + 10

        self.place_turret_button_text = f"Place Turret (T): {Turret.TURRET_COST}c"
        place_surf = font_small.render(self.place_turret_button_text, True, GREEN)
        self.place_turret_rect = place_surf.get_rect(topleft=(self.panel_rect.left + 10, y_offset)) 
        surface.blit(place_surf, self.place_turret_rect)
        y_offset += place_surf.get_height() + 5

        if self.selected_turret_on_map:
            if self.selected_turret_on_map.upgrade_level < Turret.MAX_UPGRADE_LEVEL:
                upgrade_cost = Turret.UPGRADE_COST 
                self.upgrade_turret_button_text = f"Upgrade Lvl {self.selected_turret_on_map.upgrade_level + 1} ({upgrade_cost}c) (U)"
                upgrade_color = YELLOW
            else:
                self.upgrade_turret_button_text = "Turret Max Level"
                upgrade_color = GREY
        else:
            self.upgrade_turret_button_text = "Select Turret to Upgrade (U)"
            upgrade_color = WHITE
        
        upgrade_surf = font_small.render(self.upgrade_turret_button_text, True, upgrade_color)
        self.upgrade_turret_rect = upgrade_surf.get_rect(topleft=(self.panel_rect.left + 10, y_offset))
        surface.blit(upgrade_surf, self.upgrade_turret_rect)

        if self.hover_tile_rect:
            hover_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            hover_surface.fill(self.current_hover_color) 
            surface.blit(hover_surface, self.hover_tile_rect.topleft)
            pygame.draw.rect(surface, WHITE, self.hover_tile_rect, 1) 


    def handle_input(self, event, mouse_pos):
        """
        Handles mouse clicks for build menu UI interactions.
        """
        if not self.is_active:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.place_turret_rect and self.place_turret_rect.collidepoint(mouse_pos):
                print("BuildMenu: Clicked 'Place Turret' button area (Action via 'T' key).")
                if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select', 0.5)
                return True 

            if self.upgrade_turret_rect and self.upgrade_turret_rect.collidepoint(mouse_pos):
                print("BuildMenu: Clicked 'Upgrade Turret' button area (Action via 'U' key if turret selected).")
                if self.selected_turret_on_map:
                     if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select', 0.5)
                else:
                     if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_denied', 0.5)
                return True 
            
            if event.button == 3: # Right mouse button
                if not self.is_mouse_over_build_menu(mouse_pos): # Click is on game world
                    clicked_turret = None
                    # CORRECTED: Access turrets via self.game_controller.turrets_group
                    for t in self.game_controller.turrets_group: 
                        if t.rect.collidepoint(mouse_pos):
                            clicked_turret = t
                            break
                    
                    if clicked_turret:
                        if self.selected_turret_on_map == clicked_turret: 
                            self.clear_selected_turret()
                            print("BuildMenu: Deselected turret.")
                            if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select', 0.4)
                        else:
                            self.set_selected_turret(clicked_turret)
                            print(f"BuildMenu: Selected turret at {clicked_turret.rect.center} for upgrade info.")
                            if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_confirm', 0.6)
                    else: # Clicked on empty map space
                        self.clear_selected_turret()
                        print("BuildMenu: Clicked empty map space, deselected turret.")
                    return True # Consumed by map interaction (selecting/deselecting turret)

        if self.is_mouse_over_build_menu(mouse_pos) and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
            return True 

        return False 


    def set_selected_turret(self, turret_sprite):
        """Sets the currently selected turret on the map to display upgrade info and its range."""
        if self.selected_turret_on_map and self.selected_turret_on_map != turret_sprite:
            self.selected_turret_on_map.show_range_indicator = False 

        self.selected_turret_on_map = turret_sprite
        if turret_sprite:
            turret_sprite.show_range_indicator = True 

    def clear_selected_turret(self):
        """Clears the selected turret and hides its range indicator."""
        if self.selected_turret_on_map:
            self.selected_turret_on_map.show_range_indicator = False
        self.selected_turret_on_map = None

    def is_mouse_over_build_menu(self, mouse_pos):
        """Checks if the mouse is currently over the build menu panel."""
        if self.is_active and self.panel_rect.collidepoint(mouse_pos):
            return True
        return False
