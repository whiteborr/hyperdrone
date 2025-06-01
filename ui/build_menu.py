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
        self.ui_manager = ui_manager_ref # May not be strictly needed if fonts are passed
        self.fonts = fonts

        self.is_active = False # Menu is active only during build phase
        self.panel_rect = pygame.Rect(20, gs.HEIGHT - 100 - BOTTOM_PANEL_HEIGHT, 250, 90) # Example position and size
        self.selected_turret_on_map = None # Stores a turret sprite selected on the map for upgrade
        
        # For tile hover effect
        self.hover_tile_rect = None # pygame.Rect for the tile currently under the mouse
        self.hover_tile_color = (*GREEN[:3], 100) # Semi-transparent green for valid placement
        self.invalid_hover_tile_color = (*RED[:3], 100) # Semi-transparent red for invalid

        # UI elements / buttons (more complex UI would use dedicated button classes)
        self.place_turret_button_text = f"Place Turret ({Turret.TURRET_COST}c)"
        self.upgrade_turret_button_text = f"Upgrade Turret ({Turret.UPGRADE_COST}c)"
        # These could become rects for click detection later

    def activate(self):
        """Activates the build menu display."""
        self.is_active = True
        self.selected_turret_on_map = None # Clear selection when menu becomes active

    def deactivate(self):
        """Deactivates the build menu display."""
        self.is_active = False
        self.selected_turret_on_map = None
        self.hover_tile_rect = None # Clear hover when deactivated

    def update(self, mouse_pos, current_game_state):
        """
        Updates the build menu state, like hover effects.
        Called by UIManager or GameController during the build phase.
        Args:
            mouse_pos (tuple): Current (x, y) position of the mouse.
            current_game_state (str): The current game state.
        """
        if not self.is_active or current_game_state != gs.GAME_STATE_MAZE_DEFENSE or \
           not self.game_controller.is_build_phase:
            self.hover_tile_rect = None
            return

        # Update hover tile indicator based on mouse position over the game world
        # (not over the build menu panel itself)
        if not self.is_mouse_over_build_menu(mouse_pos):
            if self.game_controller.maze:
                # Convert mouse position to grid coordinates
                grid_col = (mouse_pos[0] - self.game_controller.maze.game_area_x_offset) // TILE_SIZE
                grid_row = mouse_pos[1] // TILE_SIZE

                if 0 <= grid_row < self.game_controller.maze.actual_maze_rows and \
                   0 <= grid_col < self.game_controller.maze.actual_maze_cols:
                    
                    tile_screen_x = grid_col * TILE_SIZE + self.game_controller.maze.game_area_x_offset
                    tile_screen_y = grid_row * TILE_SIZE
                    self.hover_tile_rect = pygame.Rect(tile_screen_x, tile_screen_y, TILE_SIZE, TILE_SIZE)
                    
                    # Check if placement is valid (path, no existing turret, etc.)
                    # This is a visual check; actual placement validation is in GameController.try_place_turret
                    is_valid_spot = True # Assume valid for now
                    if self.game_controller.maze.grid[grid_row][grid_col] != 0: # Is it a wall?
                        is_valid_spot = False
                    else: # Check for existing turrets or reactor
                        temp_check_rect = pygame.Rect(0,0,TILE_SIZE//2, TILE_SIZE//2)
                        temp_check_rect.center = (tile_screen_x + TILE_SIZE//2, tile_screen_y + TILE_SIZE//2)
                        for t in self.game_controller.turrets:
                            if t.rect.colliderect(temp_check_rect):
                                is_valid_spot = False; break
                        if self.game_controller.core_reactor and self.game_controller.core_reactor.rect.colliderect(temp_check_rect):
                            is_valid_spot = False
                    
                    self.current_hover_color = self.hover_tile_color if is_valid_spot else self.invalid_hover_tile_color

                else:
                    self.hover_tile_rect = None # Mouse is outside grid
            else:
                self.hover_tile_rect = None # No maze
        else:
            self.hover_tile_rect = None # Mouse is over the build menu panel

    def draw(self, surface):
        """Draws the build menu UI elements."""
        if not self.is_active:
            return

        # Draw the main panel background
        pygame.draw.rect(surface, (*DARK_GREY[:3], 200), self.panel_rect, border_radius=10) # Semi-transparent
        pygame.draw.rect(surface, CYAN, self.panel_rect, 2, border_radius=10) # Border

        # --- UI Text and Buttons ---
        font_small = self.fonts.get("small_text", pygame.font.Font(None, 24))
        font_ui = self.fonts.get("ui_text", pygame.font.Font(None, 28))
        
        y_offset = self.panel_rect.top + 10

        # Title
        title_surf = font_ui.render("Build Mode", True, WHITE)
        surface.blit(title_surf, (self.panel_rect.left + 10, y_offset))
        y_offset += title_surf.get_height() + 10

        # Place Turret Option
        # Update text with current cost from Turret class if available
        self.place_turret_button_text = f"Place Turret (T): {Turret.TURRET_COST}c"
        place_surf = font_small.render(self.place_turret_button_text, True, GREEN)
        self.place_turret_rect = place_surf.get_rect(topleft=(self.panel_rect.left + 10, y_offset)) # Store rect for clicking
        surface.blit(place_surf, self.place_turret_rect)
        y_offset += place_surf.get_height() + 5

        # Upgrade Turret Option (Contextual)
        if self.selected_turret_on_map:
            if self.selected_turret_on_map.upgrade_level < Turret.MAX_UPGRADE_LEVEL:
                upgrade_cost = Turret.UPGRADE_COST # Could be dynamic based on level
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
        y_offset += upgrade_surf.get_height() + 5

        # Draw hover indicator on the game grid
        if self.hover_tile_rect:
            # Create a temporary surface for the hover effect for alpha blending
            hover_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            hover_surface.fill(self.current_hover_color)
            surface.blit(hover_surface, self.hover_tile_rect.topleft)
            pygame.draw.rect(surface, WHITE, self.hover_tile_rect, 1) # Thin white border for clarity


    def handle_input(self, event, mouse_pos):
        """
        Handles mouse clicks for placing or upgrading turrets.
        This will be called by EventManager.
        Returns True if the input was consumed by the build menu, False otherwise.
        """
        if not self.is_active:
            return False

        # Check if click is on one of the build menu "buttons" (simple rect collision for now)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                # Check if click is on "Place Turret" (conceptual, actual placement is by 'T' key + mouse pos)
                # if hasattr(self, 'place_turret_rect') and self.place_turret_rect.collidepoint(mouse_pos):
                #     print("BuildMenu: Clicked Place Turret button (action via 'T' key).")
                #     return True # Consumed by UI

                if hasattr(self, 'upgrade_turret_rect') and self.upgrade_turret_rect.collidepoint(mouse_pos):
                    if self.selected_turret_on_map:
                        print(f"BuildMenu: Clicked Upgrade for turret at {self.selected_turret_on_map.rect.center}")
                        if hasattr(self.game_controller, 'try_upgrade_turret'):
                            self.game_controller.try_upgrade_turret(self.selected_turret_on_map)
                        return True # Consumed by UI
                    else:
                        print("BuildMenu: Clicked Upgrade, but no turret selected.")
                        if hasattr(self.game_controller, 'play_sound'):
                            self.game_controller.play_sound('ui_denied', 0.5)
                        return True # Consumed by UI
            
            elif event.button == 3: # Right-click to select/deselect turret on map
                if not self.is_mouse_over_build_menu(mouse_pos): # Click is on game world
                    clicked_turret = None
                    for t in self.game_controller.turrets:
                        if t.rect.collidepoint(mouse_pos):
                            clicked_turret = t
                            break
                    if clicked_turret:
                        self.set_selected_turret(clicked_turret)
                        print(f"BuildMenu: Selected turret at {clicked_turret.rect.center}")
                    else:
                        self.clear_selected_turret()
                        print("BuildMenu: Deselected turret.")
                    return True # Consumed by UI (map interaction)


        # Key presses for build actions are handled by EventManager directly
        # (e.g., 'T' for place, 'U' for upgrade selected)
        # This method primarily handles clicks on the UI panel itself.

        if self.is_mouse_over_build_menu(mouse_pos) and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
            return True # Consume mouse events over the panel to prevent game world interaction

        return False # Input not consumed by this menu's panel elements


    def set_selected_turret(self, turret_sprite):
        """Sets the currently selected turret on the map to display upgrade info."""
        self.selected_turret_on_map = turret_sprite
        if turret_sprite:
            turret_sprite.show_range_indicator = True # Show range for selected turret
            # Deselect range for other turrets
            for t in self.game_controller.turrets:
                if t != turret_sprite:
                    t.show_range_indicator = False
        else: # Clear selection
            for t in self.game_controller.turrets:
                t.show_range_indicator = False


    def clear_selected_turret(self):
        if self.selected_turret_on_map:
            self.selected_turret_on_map.show_range_indicator = False
        self.selected_turret_on_map = None

    def is_mouse_over_build_menu(self, mouse_pos):
        """Checks if the mouse is currently over the build menu panel."""
        if self.is_active and self.panel_rect.collidepoint(mouse_pos):
            return True
        return False

