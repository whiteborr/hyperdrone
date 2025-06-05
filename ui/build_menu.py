# ui/build_menu.py
import pygame
import game_settings as gs
from game_settings import (
    WHITE, BLACK, CYAN, YELLOW, GREEN, RED, DARK_GREY, GOLD, GREY, TILE_SIZE, BOTTOM_PANEL_HEIGHT
)
# We'll need access to the Turret class for its cost constants
try:
    from entities.turret import Turret 
except ImportError:
    print("BuildMenu: Could not import Turret class. Costs will be placeholders.")
    # Define placeholders if Turret class isn't available during isolated development
    class Turret:
        TURRET_COST = 50
        UPGRADE_COST = 100
        MAX_UPGRADE_LEVEL = 3
        MAX_TURRETS = 5 # Default if not found in actual Turret class

# Import MazeChapter2 to check its type
try:
    from entities.maze_chapter2 import MazeChapter2
except ImportError:
    MazeChapter2 = None # Define as None if not found, to avoid runtime errors in type checks


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
        self.panel_height = 90  # Adjusted height to fit content
        self.panel_width = 280 # Adjusted width for potentially longer text
        self.panel_rect = pygame.Rect(
            20, # X position
            gs.HEIGHT - BOTTOM_PANEL_HEIGHT - self.panel_height - 10, # Y position (above bottom panel)
            self.panel_width, 
            self.panel_height
        )
        self.selected_turret_on_map = None # Stores the turret sprite selected on the map
        
        self.hover_tile_rect = None # Rect for highlighting the tile under the mouse
        self.hover_tile_color = (*GREEN[:3], 100) # Semi-transparent green for valid placement
        self.invalid_hover_tile_color = (*RED[:3], 100) # Semi-transparent red for invalid placement
        self.current_hover_color = self.hover_tile_color # Color to use for hover based on validity

        # Button texts and rects for UI interaction (primarily for display, actions via keys)
        self.place_turret_button_text = "" 
        self.upgrade_turret_button_text = ""
        self.place_turret_rect = None
        self.upgrade_turret_rect = None


    def activate(self):
        """Activates the build menu display."""
        self.is_active = True
        self.selected_turret_on_map = None # Clear any previously selected turret
        print("BuildMenu: Activated.")

    def deactivate(self):
        """Deactivates the build menu display."""
        self.is_active = False
        self.selected_turret_on_map = None
        self.hover_tile_rect = None # Clear hover effect
        print("BuildMenu: Deactivated.")

    def update(self, mouse_pos, current_game_state):
        """
        Updates the build menu state, like hover effects for tile placement.
        Args:
            mouse_pos (tuple): Current (x, y) position of the mouse.
            current_game_state (str): The current game state.
        """
        if not self.is_active or \
           current_game_state != gs.GAME_STATE_MAZE_DEFENSE or \
           not hasattr(self.game_controller, 'is_build_phase') or \
           not self.game_controller.is_build_phase:
            self.hover_tile_rect = None # No hover if menu not active or not in build phase
            return

        # Check if mouse is over the game world (not the build menu panel itself)
        if not self.is_mouse_over_build_menu(mouse_pos):
            if self.game_controller.maze: # Ensure maze exists
                current_maze_x_offset = getattr(self.game_controller.maze, 'game_area_x_offset', 0)
                
                # Convert mouse position to grid coordinates
                grid_col = (mouse_pos[0] - current_maze_x_offset) // TILE_SIZE
                grid_row = mouse_pos[1] // TILE_SIZE

                # Check if grid coordinates are within maze bounds
                if 0 <= grid_row < self.game_controller.maze.actual_maze_rows and \
                   0 <= grid_col < self.game_controller.maze.actual_maze_cols:
                    
                    # Calculate screen position of the tile for drawing hover rect
                    tile_screen_x = grid_col * TILE_SIZE + current_maze_x_offset
                    tile_screen_y = grid_row * TILE_SIZE
                    self.hover_tile_rect = pygame.Rect(tile_screen_x, tile_screen_y, TILE_SIZE, TILE_SIZE)
                    
                    is_valid_spot = True # Assume valid initially
                    
                    # Specific validation for MazeChapter2
                    if MazeChapter2 and isinstance(self.game_controller.maze, MazeChapter2):
                        tile_value = self.game_controller.maze.grid[grid_row][grid_col]
                        if tile_value != 'T': # Must be a designated turret spot
                            is_valid_spot = False
                        else:
                            # Check if a turret already exists at this grid location
                            for t in self.game_controller.turrets_group:
                                # Convert turret's pixel center to grid to compare
                                turret_grid_col = int((t.rect.centerx - current_maze_x_offset) / TILE_SIZE)
                                turret_grid_row = int(t.rect.centery / TILE_SIZE)
                                if turret_grid_row == grid_row and turret_grid_col == grid_col:
                                    is_valid_spot = False
                                    break
                    else: # Validation for original procedural Maze (or other types)
                        tile_value = self.game_controller.maze.grid[grid_row][grid_col]
                        if tile_value != 0: # Must be an empty path tile (0)
                            is_valid_spot = False
                        else: 
                            # Check for collision with existing turrets or player (if applicable)
                            # Create a small rect at the center of the tile for collision check
                            temp_check_rect = pygame.Rect(0,0,TILE_SIZE//2, TILE_SIZE//2)
                            temp_check_rect.center = (tile_screen_x + TILE_SIZE//2, tile_screen_y + TILE_SIZE//2)
                            
                            for t in self.game_controller.turrets_group: # Turrets group from GameController
                                if t.rect.colliderect(temp_check_rect):
                                    is_valid_spot = False; break
                            # Player collision check might be relevant for other game modes, not typically Maze Defense build phase
                            # if self.game_controller.player and hasattr(self.game_controller.player, 'rect') and self.game_controller.player.rect.colliderect(temp_check_rect):
                            #     is_valid_spot = False
                    
                    self.current_hover_color = self.hover_tile_color if is_valid_spot else self.invalid_hover_tile_color
                else:
                    self.hover_tile_rect = None # Mouse is outside valid grid
            else:
                self.hover_tile_rect = None # No maze loaded
        else:
            self.hover_tile_rect = None # Mouse is over the build menu panel

    def draw(self, surface):
        """Draws the build menu UI elements."""
        if not self.is_active:
            return

        # Draw panel background
        pygame.draw.rect(surface, (*DARK_GREY[:3], 200), self.panel_rect, border_radius=10) 
        pygame.draw.rect(surface, CYAN, self.panel_rect, 2, border_radius=10) # Border

        # Get fonts (with fallbacks if not found)
        font_small = self.fonts.get("small_text", pygame.font.Font(None, 24))
        font_ui = self.fonts.get("ui_text", pygame.font.Font(None, 28))
        
        y_offset = self.panel_rect.top + 10 # Initial Y position for text

        # Draw Title
        title_surf = font_ui.render("Build Mode", True, WHITE)
        surface.blit(title_surf, (self.panel_rect.left + 10, y_offset))
        y_offset += title_surf.get_height() + 10

        # Draw "Place Turret" button/text
        turret_cost = Turret.TURRET_COST if hasattr(Turret, 'TURRET_COST') else 50
        self.place_turret_button_text = f"Place Turret (T): {turret_cost}c"
        place_surf = font_small.render(self.place_turret_button_text, True, GREEN)
        self.place_turret_rect = place_surf.get_rect(topleft=(self.panel_rect.left + 10, y_offset)) 
        surface.blit(place_surf, self.place_turret_rect)
        y_offset += place_surf.get_height() + 5

        # Draw "Upgrade Turret" button/text
        upgrade_color = WHITE
        if self.selected_turret_on_map:
            max_level = Turret.MAX_UPGRADE_LEVEL if hasattr(Turret, 'MAX_UPGRADE_LEVEL') else 3
            if self.selected_turret_on_map.upgrade_level < max_level:
                upgrade_cost = Turret.UPGRADE_COST if hasattr(Turret, 'UPGRADE_COST') else 100
                self.upgrade_turret_button_text = f"Upgrade Lvl {self.selected_turret_on_map.upgrade_level + 1} ({upgrade_cost}c) (U)"
                upgrade_color = YELLOW
            else:
                self.upgrade_turret_button_text = "Turret Max Level"
                upgrade_color = GREY
        else:
            self.upgrade_turret_button_text = "Select Turret to Upgrade (U)"
            # upgrade_color remains WHITE
        
        upgrade_surf = font_small.render(self.upgrade_turret_button_text, True, upgrade_color)
        self.upgrade_turret_rect = upgrade_surf.get_rect(topleft=(self.panel_rect.left + 10, y_offset))
        surface.blit(upgrade_surf, self.upgrade_turret_rect)

        # Draw hover tile highlight if applicable
        if self.hover_tile_rect:
            hover_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            hover_surface.fill(self.current_hover_color) 
            surface.blit(hover_surface, self.hover_tile_rect.topleft)
            pygame.draw.rect(surface, WHITE, self.hover_tile_rect, 1) # Outline for the hover


    def handle_input(self, event, mouse_pos):
        """
        Handles mouse clicks for build menu UI interactions.
        Note: Primary actions (place/upgrade) are typically triggered by keyboard shortcuts ('T', 'U').
        This method mainly handles clicks on the panel for potential future buttons or to consume clicks
        so they don't interact with the game world when the menu is active.
        Right-click on the map for selecting/deselecting turrets is also handled here.
        Returns:
            bool: True if the event was consumed by the build menu, False otherwise.
        """
        if not self.is_active:
            return False # Menu not active, input not consumed by it

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check if click is on the "Place Turret" text area (visual feedback, action by 'T')
            if self.place_turret_rect and self.place_turret_rect.collidepoint(mouse_pos):
                print("BuildMenu: Clicked 'Place Turret' button area (Action via 'T' key).")
                if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select', 0.5)
                return True # Consumed click

            # Check if click is on the "Upgrade Turret" text area (visual feedback, action by 'U')
            if self.upgrade_turret_rect and self.upgrade_turret_rect.collidepoint(mouse_pos):
                print("BuildMenu: Clicked 'Upgrade Turret' button area (Action via 'U' key if turret selected).")
                if self.selected_turret_on_map:
                     if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select', 0.5)
                else:
                     if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_denied', 0.5)
                return True # Consumed click
            
            # Handle right-click on the game map for selecting/deselecting turrets
            if event.button == 3: # Right mouse button
                if not self.is_mouse_over_build_menu(mouse_pos): # Click is on game world, not the panel
                    clicked_turret = None
                    # Access turrets via self.game_controller.turrets_group (managed by CombatController)
                    for t in self.game_controller.turrets_group: 
                        if t.rect.collidepoint(mouse_pos):
                            clicked_turret = t
                            break
                    
                    if clicked_turret:
                        if self.selected_turret_on_map == clicked_turret: 
                            self.clear_selected_turret() # Deselect if clicking the same turret
                            print("BuildMenu: Deselected turret.")
                            if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select', 0.4)
                        else:
                            self.set_selected_turret(clicked_turret) # Select new turret
                            print(f"BuildMenu: Selected turret at {clicked_turret.rect.center} for upgrade info.")
                            if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_confirm', 0.6)
                    else: # Clicked on empty map space
                        self.clear_selected_turret() # Deselect any current turret
                        print("BuildMenu: Clicked empty map space, deselected turret.")
                    return True # Right-click on map is consumed for turret selection logic
        
        # If mouse is over the build menu panel, consume mouse events to prevent interaction with game world
        if self.is_mouse_over_build_menu(mouse_pos) and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
            return True 

        return False # Event not consumed by build menu UI interactions


    def set_selected_turret(self, turret_sprite):
        """Sets the currently selected turret on the map to display upgrade info and its range."""
        # Deselect previous turret's range indicator if a different one is now selected
        if self.selected_turret_on_map and self.selected_turret_on_map != turret_sprite:
            if hasattr(self.selected_turret_on_map, 'show_range_indicator'):
                self.selected_turret_on_map.show_range_indicator = False 
        
        self.selected_turret_on_map = turret_sprite
        if turret_sprite and hasattr(turret_sprite, 'show_range_indicator'):
            turret_sprite.show_range_indicator = True # Show range for the newly selected turret

    def clear_selected_turret(self):
        """Clears the selected turret and hides its range indicator."""
        if self.selected_turret_on_map and hasattr(self.selected_turret_on_map, 'show_range_indicator'):
            self.selected_turret_on_map.show_range_indicator = False
        self.selected_turret_on_map = None

    def is_mouse_over_build_menu(self, mouse_pos):
        """Checks if the mouse is currently over the build menu panel."""
        if self.is_active and self.panel_rect.collidepoint(mouse_pos):
            return True
        return False
