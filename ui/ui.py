# hyperdrone/ui/ui.py

import os
import math
import random
import logging # Import the logging module

import pygame

import game_settings as gs
from game_settings import (
    WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT, BOTTOM_PANEL_HEIGHT, TILE_SIZE,
    BLACK, GOLD, WHITE, GREEN, CYAN, RED, DARK_RED, GREY, YELLOW, LIGHT_BLUE, ORANGE, PURPLE,
    DARK_GREY, DARK_PURPLE, ARCHITECT_VAULT_BG_COLOR,
    WEAPON_MODE_ICONS, PLAYER_BULLET_COLOR, MISSILE_COLOR, LIGHTNING_COLOR, POWERUP_TYPES,
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
    GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, GAME_STATE_CODEX,
    GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_GAME_INTRO_SCROLL, GAME_STATE_RING_PUZZLE, GAME_STATE_MAZE_DEFENSE,
    DEFAULT_SETTINGS,
    TOTAL_CORE_FRAGMENTS_NEEDED, CORE_FRAGMENT_DETAILS,
    get_game_setting
)

# Import BuildMenu
try:
    from .build_menu import BuildMenu
except ImportError:
    logging.warning("UIManager: Could not import BuildMenu. Build UI will not be available.") # Logging
    BuildMenu = None 

from drone_management.drone_configs import DRONE_DATA, DRONE_DISPLAY_ORDER
# Leaderboard functions are now accessed via game_controller.ui_flow_controller or game_controller directly

# Configure basic logging
# In a larger application, this might be configured in main.py or a dedicated logging config file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')


class UIManager:
    def __init__(self, screen, fonts, game_controller_ref, scene_manager_ref, drone_system_ref):
        """
        Initializes the UIManager.
        Args:
            screen: The main Pygame screen surface.
            fonts (dict): A dictionary of pre-loaded Pygame fonts.
            game_controller_ref: Reference to the main GameController (orchestrator).
            scene_manager_ref: Reference to the SceneManager.
            drone_system_ref: Reference to the DroneSystem.
        """
        self.screen = screen
        self.fonts = fonts
        self.game_controller = game_controller_ref 
        self.scene_manager = scene_manager_ref
        self.drone_system = drone_system_ref
        
        # Asset dictionary for UI elements like icons
        self.ui_assets = {
            "ring_icon": None, "ring_icon_empty": None, "menu_background": None,
            "current_drone_life_icon": None, "core_fragment_icons": {},
            "core_fragment_empty_icon": None, "reactor_icon_placeholder": None
        }
        # Standard sizes for UI icons
        self.ui_icon_size_lives = (30, 30)
        self.ui_icon_size_rings = (20, 20)
        self.ui_icon_size_fragments = (28, 28)
        self.ui_icon_size_reactor = (32, 32) # Used for reactor health bar icon

        # Codex screen specific calculation variables
        self.codex_list_item_height = 0
        self.codex_max_visible_items_list = 0
        self.codex_max_visible_lines_content = 0
        self.codex_image_cache = {} # Cache for loaded codex images

        # Instruction text styling for menus and overlays
        self.BOTTOM_INSTRUCTION_CENTER_Y = HEIGHT - 50 # Adjusted for better spacing
        self.SECONDARY_INSTRUCTION_CENTER_Y = HEIGHT - 80 # For secondary instructions
        self.INSTRUCTION_TEXT_COLOR = CYAN
        self.INSTRUCTION_BG_COLOR = (30, 30, 30, 150) # Semi-transparent dark background
        self.INSTRUCTION_PADDING_X = 20
        self.INSTRUCTION_PADDING_Y = 10

        # Initialize BuildMenu if available
        if BuildMenu:
            self.build_menu = BuildMenu(self.game_controller, self, self.fonts)
        else:
            self.build_menu = None

        self._load_ui_assets() # Load all UI images and create fallbacks
        self.update_player_life_icon_surface() # Set initial player life icon
        logging.info("UIManager initialized.")

    def _load_ui_assets(self):
        """Loads UI assets like icons and backgrounds, with fallbacks if files are missing."""
        # Load Ring icons (for collectibles)
        ring_icon_path = os.path.join("assets", "images", "collectibles", "ring_ui_icon.png")
        ring_icon_empty_path = os.path.join("assets", "images", "collectibles", "ring_ui_icon_empty.png")
        try:
            if os.path.exists(ring_icon_path):
                raw_ring_icon = pygame.image.load(ring_icon_path).convert_alpha()
                self.ui_assets["ring_icon"] = pygame.transform.smoothscale(raw_ring_icon, self.ui_icon_size_rings)
            else:
                self.ui_assets["ring_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", GOLD)
            if os.path.exists(ring_icon_empty_path):
                raw_ring_empty_icon = pygame.image.load(ring_icon_empty_path).convert_alpha()
                self.ui_assets["ring_icon_empty"] = pygame.transform.smoothscale(raw_ring_empty_icon, self.ui_icon_size_rings)
            else:
                self.ui_assets["ring_icon_empty"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", GREY)
        except pygame.error as e:
            logging.error(f"UIManager: Error loading ring icons: {e}. Using fallbacks.") # Logging
            self.ui_assets["ring_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "R", GOLD)
            self.ui_assets["ring_icon_empty"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "R", GREY)

        # Load Main Menu background image
        menu_bg_path = os.path.join("assets", "images", "ui", "menu_logo_hyperdrone.png")
        if os.path.exists(menu_bg_path):
            try: 
                self.ui_assets["menu_background"] = pygame.image.load(menu_bg_path).convert_alpha()
            except pygame.error as e: 
                logging.error(f"UIManager: Error loading menu background '{menu_bg_path}': {e}") # Logging
        else: 
            logging.warning(f"UIManager: Menu background not found: {menu_bg_path}") # Logging

        # Load Core Fragment icons (for collectibles and HUD)
        fragment_empty_icon_path = os.path.join("assets", "images", "collectibles", "fragment_ui_icon_empty.png")
        if os.path.exists(fragment_empty_icon_path):
            try:
                raw_frag_empty_icon = pygame.image.load(fragment_empty_icon_path).convert_alpha()
                self.ui_assets["core_fragment_empty_icon"] = pygame.transform.smoothscale(raw_frag_empty_icon, self.ui_icon_size_fragments)
            except pygame.error as e: 
                self.ui_assets["core_fragment_empty_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "F", DARK_GREY, text_color=GREY)
        else: 
            self.ui_assets["core_fragment_empty_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "F", DARK_GREY, text_color=GREY)

        if CORE_FRAGMENT_DETAILS: # Load icons for each defined core fragment
            for frag_key, details in CORE_FRAGMENT_DETAILS.items():
                frag_id = details.get("id")
                icon_filename = details.get("icon_filename")
                if frag_id and icon_filename:
                    icon_path = os.path.join("assets", "images", "collectibles", icon_filename)
                    if os.path.exists(icon_path):
                        try:
                            raw_icon = pygame.image.load(icon_path).convert_alpha()
                            self.ui_assets["core_fragment_icons"][frag_id] = pygame.transform.smoothscale(raw_icon, self.ui_icon_size_fragments)
                        except pygame.error as e: 
                            self.ui_assets["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", PURPLE)
                    else: # Icon file missing
                        self.ui_assets["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, frag_id[:1] if frag_id else "!", PURPLE)
                elif frag_id and frag_id not in self.ui_assets["core_fragment_icons"]: # Config exists but no icon filename
                     self.ui_assets["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "!", DARK_PURPLE)
        
        # Fallback icon for the Core Reactor in Maze Defense HUD
        self.ui_assets["reactor_icon_placeholder"] = self._create_fallback_icon_surface(self.ui_icon_size_reactor, "⚛", (50,50,200), font_key="ui_emoji_general")

    def update_player_life_icon_surface(self):
        """Updates the icon used to display player lives based on the currently selected drone."""
        selected_drone_id = self.drone_system.get_selected_drone_id()
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        icon_path = drone_config.get("icon_path") if drone_config else None # Get icon path from drone config
        
        if icon_path and os.path.exists(icon_path):
            try:
                raw_icon = pygame.image.load(icon_path).convert_alpha()
                self.ui_assets["current_drone_life_icon"] = pygame.transform.smoothscale(raw_icon, self.ui_icon_size_lives)
            except pygame.error as e:
                logging.error(f"UIManager: Error loading life icon '{icon_path}': {e}") # Logging
                self.ui_assets["current_drone_life_icon"] = self._create_fallback_icon_surface(size=self.ui_icon_size_lives, text="♥", color=CYAN, font_key="ui_emoji_small")
        else: # Fallback if no icon path or file not found
            if icon_path: 
                logging.warning(f"UIManager: Life icon path not found: {icon_path}") # Logging
            self.ui_assets["current_drone_life_icon"] = self._create_fallback_icon_surface(size=self.ui_icon_size_lives, text="♥", color=CYAN, font_key="ui_emoji_small")

    def _create_fallback_icon_surface(self, size=(30,30), text="?", color=GREY, text_color=WHITE, font_key="ui_text"):
        """Creates a generic fallback icon surface if an image fails to load."""
        surface = pygame.Surface(size, pygame.SRCALPHA) # Use SRCALPHA for transparency
        surface.fill(color) # Background color of the icon
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 1) # Border
        
        # Use specified font or a default system font
        font_to_use = self.fonts.get(font_key, pygame.font.Font(None, max(10, size[1]-4))) 
        if text and font_to_use:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2))
                surface.blit(text_surf, text_rect)
            except Exception as e: 
                logging.error(f"UIManager: Error rendering fallback icon text '{text}' with font '{font_key}': {e}") # Logging
        return surface

    def _render_text_safe(self, text, font_key, color, fallback_size=24):
        """Renders text using a specified font key, with a fallback if the font is missing."""
        font = self.fonts.get(font_key)
        if not font: 
            font = pygame.font.Font(None, fallback_size) # Use default system font if key not found
        try: 
            return font.render(str(text), True, color) # Ensure text is string
        except Exception as e:
            logging.error(f"UIManager: Error rendering text '{text}' with font '{font_key}': {e}") # Logging
            error_font = pygame.font.Font(None, fallback_size) # Fallback for rendering error
            return error_font.render("ERR", True, RED) # Display "ERR" in red

    def _wrap_text(self, text, font, max_width):
        """Wraps text to fit within a maximum width, preserving words."""
        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] <= max_width: # If word fits on current line
                current_line = test_line
            else: # Word doesn't fit, start new line
                if current_line: # Add previous line if it has content
                    lines.append(current_line.strip())
                current_line = word + " " # Start new line with current word
        lines.append(current_line.strip()) # Add the last line
        return lines

    def draw_current_scene_ui(self):
        """
        Main drawing router for the UI. Called every frame by GameController.
        Determines the current game state and calls the appropriate drawing method.
        """
        current_state = self.scene_manager.get_current_state()
        ui_flow_ctrl = self.game_controller.ui_flow_controller # Reference to UIFlowController

        # Common background for menu-like states (main menu, settings, etc.)
        is_menu_like_state = current_state in [
            GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
            GAME_STATE_LEADERBOARD, GAME_STATE_CODEX,
            GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
            GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME
        ]
        
        if is_menu_like_state: 
            self.screen.fill(BLACK) # Black background
            # Draw starfield if available from UIFlowController
            if ui_flow_ctrl and hasattr(ui_flow_ctrl, 'menu_stars') and ui_flow_ctrl.menu_stars:
                 for star_params in ui_flow_ctrl.menu_stars: # x, y, speed, size
                    pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

        # Route to specific draw methods based on current game state
        if current_state == GAME_STATE_MAIN_MENU: self.draw_main_menu()
        elif current_state == GAME_STATE_DRONE_SELECT: self.draw_drone_select_menu()
        elif current_state == GAME_STATE_SETTINGS: self.draw_settings_menu()
        elif current_state == GAME_STATE_LEADERBOARD: self.draw_leaderboard_overlay()
        elif current_state == GAME_STATE_CODEX: self.draw_codex_screen()
        elif current_state == GAME_STATE_GAME_OVER: self.draw_game_over_overlay()
        elif current_state == GAME_STATE_ENTER_NAME: self.draw_enter_name_overlay()
        elif current_state == GAME_STATE_GAME_INTRO_SCROLL: self.draw_game_intro_scroll() 
        
        elif current_state.startswith("architect_vault"): # Handle all Architect's Vault states
            self.draw_architect_vault_hud_elements() # Draw common HUD for vault
            if self.game_controller.paused: self.draw_pause_overlay() # Show pause if game is paused
            # Specific overlays for vault success/failure
            if current_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS: self.draw_architect_vault_success_overlay()
            elif current_state == GAME_STATE_ARCHITECT_VAULT_FAILURE: self.draw_architect_vault_failure_overlay()
        
        elif current_state == GAME_STATE_PLAYING or current_state == GAME_STATE_BONUS_LEVEL_PLAYING:
            self.draw_gameplay_hud() # Draw standard gameplay HUD
            if self.game_controller.paused: self.draw_pause_overlay()
        
        elif current_state == GAME_STATE_MAZE_DEFENSE: 
            self.draw_maze_defense_hud() # Draw HUD for Maze Defense mode
            if self.game_controller.paused: self.draw_pause_overlay()
            # Draw Build Menu if it's active and in build phase
            if self.build_menu and self.build_menu.is_active and \
               hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase:
                self.build_menu.draw(self.screen)
        
        elif current_state == GAME_STATE_RING_PUZZLE:
            # Draw Ring Puzzle UI (delegated to PuzzleController)
            if self.game_controller.puzzle_controller and self.game_controller.puzzle_controller.ring_puzzle_active_flag:
                self.screen.fill(DARK_GREY) # Background for puzzle
                self.game_controller.puzzle_controller.draw_active_puzzle(self.screen)
            else: # Fallback if puzzle not ready
                self.screen.fill(DARK_GREY)
                fallback_text = self._render_text_safe("Loading Puzzle...", "medium_text", WHITE)
                self.screen.blit(fallback_text, fallback_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        # Draw story message overlay if active (across most states except intro scroll)
        if hasattr(self.game_controller, 'story_message_active') and self.game_controller.story_message_active and \
           hasattr(self.game_controller, 'story_message') and self.game_controller.story_message:
            if current_state != GAME_STATE_GAME_INTRO_SCROLL: # Don't draw over intro scroll
                self.draw_story_message_overlay(self.game_controller.story_message)

    def draw_game_intro_scroll(self):
        """Draws the scrolling introduction screens with text and images."""
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        self.screen.fill(BLACK) # Black background for intro

        # Get current image and text surfaces from GameController (managed by UIFlowController)
        current_image_surface = self.game_controller.current_intro_image_surface 
        current_text_surfaces = self.game_controller.intro_screen_text_surfaces_current

        # Draw background image (scaled to fit)
        if current_image_surface: 
            img_w, img_h = current_image_surface.get_size()
            aspect_ratio = img_h / img_w if img_w > 0 else 1
            # Scale image to fit screen width or height while maintaining aspect ratio
            scaled_w = WIDTH
            scaled_h = int(scaled_w * aspect_ratio)
            pos_y = (HEIGHT - scaled_h) // 2
            pos_x = 0
            if scaled_h > HEIGHT: # If scaled height exceeds screen, scale by height instead
                scaled_h = HEIGHT
                scaled_w = int(scaled_h / aspect_ratio if aspect_ratio > 0 else WIDTH)
                pos_x = (WIDTH - scaled_w) // 2
                pos_y = 0
            try: 
                self.screen.blit(pygame.transform.smoothscale(current_image_surface, (scaled_w, scaled_h)), (pos_x, pos_y))
            except pygame.error as e: # Handle potential errors during scaling/blitting
                logging.error(f"UIManager: Error scaling/blitting intro image: {e}") # Logging
                # Fallback: draw starfield if image fails
                if ui_flow_ctrl and ui_flow_ctrl.menu_stars:
                    for star_params in ui_flow_ctrl.menu_stars: 
                        pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])
        else: # No image, just draw starfield
            if ui_flow_ctrl and ui_flow_ctrl.menu_stars:
                for star_params in ui_flow_ctrl.menu_stars: 
                    pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

        # If no text surfaces (e.g., end of sequence), show continue prompt
        if not current_text_surfaces: 
            if ui_flow_ctrl.intro_sequence_finished:
                prompt_font = self.fonts.get("small_text", pygame.font.Font(None, 24))
                prompt_surf = prompt_font.render("Press SPACE or ENTER to Continue", True, CYAN)
                self.screen.blit(prompt_surf, prompt_surf.get_rect(centerx=WIDTH // 2, bottom=HEIGHT - 30))
            return
        
        # Calculate total height of text block for centering
        total_text_height = 0
        line_spacing = 0
        font_for_spacing = self.fonts.get(self.game_controller.intro_font_key, pygame.font.Font(None, 36))
        line_spacing = int(font_for_spacing.get_linesize() * 0.4) # Spacing between lines
        for i, surf in enumerate(current_text_surfaces):
            total_text_height += surf.get_height()
            if i < len(current_text_surfaces) - 1: 
                total_text_height += line_spacing
        
        start_y = (HEIGHT - total_text_height) // 2 # Starting Y position for the text block
        current_y = start_y
        fade_alpha = 255 # Alpha for fade-in/out effect
        
        # Calculate fade alpha based on screen duration
        if hasattr(ui_flow_ctrl, 'intro_screen_start_time'):
            elapsed_time = pygame.time.get_ticks() - ui_flow_ctrl.intro_screen_start_time
            fade_duration = 1000 # Duration of fade effect in ms
            intro_duration = gs.get_game_setting("INTRO_SCREEN_DURATION_MS", 6000) # Total duration of one screen
            if elapsed_time < fade_duration: # Fade in
                fade_alpha = int(255 * (elapsed_time / fade_duration))
            elif intro_duration - elapsed_time < fade_duration: # Fade out
                fade_alpha = int(255 * ((intro_duration - elapsed_time) / fade_duration))
            fade_alpha = max(0, min(255, fade_alpha)) # Clamp alpha value

        # Draw each line of text
        for i, text_surf in enumerate(current_text_surfaces):
            text_rect = text_surf.get_rect(centerx=WIDTH // 2, top=current_y)
            temp_surf = text_surf.copy()
            temp_surf.set_alpha(fade_alpha) # Apply fade alpha
            self.screen.blit(temp_surf, text_rect)
            current_y += text_surf.get_height() + line_spacing # Move to next line position
        
        # Show continue prompt if intro sequence is finished
        if ui_flow_ctrl.intro_sequence_finished:
            prompt_font = self.fonts.get("small_text", pygame.font.Font(None, 24))
            prompt_surf = prompt_font.render("Press SPACE or ENTER to Continue", True, CYAN)
            self.screen.blit(prompt_surf, prompt_surf.get_rect(centerx=WIDTH // 2, bottom=HEIGHT - 30))

    def draw_story_message_overlay(self, message):
        """Draws a story message overlay at the bottom of the gameplay area."""
        font = self.fonts.get("story_message_font", self.fonts.get("ui_text")) # Use specific story font or fallback
        max_width = WIDTH * 0.7 # Max width for the message box
        padding = 20
        line_spacing_ratio = 0.2 # Relative line spacing

        wrapped_lines_text = self._wrap_text(message, font, max_width - 2 * padding) # Wrap text
        rendered_lines = [font.render(line, True, WHITE) for line in wrapped_lines_text]
        if not rendered_lines: return # No lines to draw

        line_height = font.get_linesize()
        effective_line_spacing = line_height * line_spacing_ratio
        total_text_height = sum(surf.get_height() for surf in rendered_lines) + (len(rendered_lines) - 1) * effective_line_spacing
        max_line_width = max(surf.get_width() for surf in rendered_lines) if rendered_lines else 0
        
        box_width = max_line_width + 2 * padding
        box_height = total_text_height + 2 * padding
        box_x = (WIDTH - box_width) // 2
        box_y = GAME_PLAY_AREA_HEIGHT - box_height - 20 # Position near bottom of game area
        
        # Create overlay surface for the message box
        overlay_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        overlay_surf.fill((10, 20, 40, 220)) # Dark semi-transparent background
        pygame.draw.rect(overlay_surf, GOLD, overlay_surf.get_rect(), 2, border_radius=10) # Gold border
        
        # Blit text lines onto the overlay surface
        current_text_y = padding
        for line_surf in rendered_lines:
            overlay_surf.blit(line_surf, line_surf.get_rect(centerx=box_width // 2, top=current_text_y))
            current_text_y += line_surf.get_height() + effective_line_spacing
            
        self.screen.blit(overlay_surf, (box_x, box_y)) # Draw the message box

    def draw_codex_screen(self):
        """Draws the Lore Codex screen, handling categories, entries, and content display."""
        ui_flow_ctrl = self.game_controller.ui_flow_controller # Access UIFlowController for codex state
        self.screen.fill(BLACK) # Background
        if ui_flow_ctrl.menu_stars: # Dim starfield for codex
            for star_params in ui_flow_ctrl.menu_stars: 
                pygame.draw.circle(self.screen, (50,50,50), (int(star_params[0]), int(star_params[1])), star_params[3])
        
        title_surf = self._render_text_safe("Lore Codex", "codex_title_font", GOLD)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 60))
        self.screen.blit(title_surf, title_rect)
        
        current_view = ui_flow_ctrl.codex_current_view # "categories", "entries", or "content"
        padding = 50
        list_panel_width = WIDTH // 3 - padding * 1.5 # Width for category/entry list
        list_panel_x = padding
        content_panel_x = list_panel_x + list_panel_width + padding / 2 # Start X for content display
        content_panel_width = WIDTH - content_panel_x - padding
        
        top_y_start = title_rect.bottom + 30 # Y position for content start
        bottom_y_end = HEIGHT - 80 # Y position for content end (above nav instructions)

        # Get fonts for codex elements
        category_font = self.fonts.get("codex_category_font")
        entry_font = self.fonts.get("codex_entry_font")
        content_font = self.fonts.get("codex_content_font")

        if not all([category_font, entry_font, content_font]): # Fallback if fonts not loaded
            fallback_surf = self._render_text_safe("Codex fonts loading...", "medium_text", WHITE)
            self.screen.blit(fallback_surf, fallback_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            return

        # Calculate max visible items/lines once
        if self.codex_list_item_height == 0:
             self.codex_list_item_height = entry_font.get_height() + 15 # Height of each list item
             if self.codex_list_item_height > 0: 
                 self.codex_max_visible_items_list = (bottom_y_end - top_y_start) // self.codex_list_item_height
             else: 
                 self.codex_max_visible_items_list = 1 # Avoid division by zero
        
        content_line_height = content_font.get_linesize()
        if self.codex_max_visible_lines_content == 0 and content_line_height > 0:
             available_height_for_content_text_calc = bottom_y_end - (top_y_start + category_font.get_height() + 20)
             self.codex_max_visible_lines_content = available_height_for_content_text_calc // content_line_height if content_line_height > 0 else 1
        
        nav_instr = "" # Navigation instructions text
        current_list_y = top_y_start + 20 

        # --- Draw based on current codex view ---
        if current_view == "categories":
            categories = ui_flow_ctrl.codex_categories_list
            selected_category_idx = ui_flow_ctrl.codex_selected_category_index
            if not categories: 
                self.screen.blit(self._render_text_safe("No lore unlocked.", "medium_text", WHITE), 
                                 self._render_text_safe("No lore unlocked.", "medium_text", WHITE).get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            else: # Display scrollable list of categories
                max_visible = self.codex_max_visible_items_list if self.codex_max_visible_items_list > 0 else 1
                start_idx = max(0, selected_category_idx - max_visible // 2)
                start_idx = min(start_idx, max(0, len(categories) - max_visible)) # Adjust start for scrolling
                end_idx = min(len(categories), start_idx + max_visible)
                for i_display, i_actual in enumerate(range(start_idx, end_idx)):
                    category_name = categories[i_actual]
                    y_pos = current_list_y + i_display * self.codex_list_item_height
                    color = YELLOW if i_actual == selected_category_idx else WHITE
                    self.screen.blit(self._render_text_safe(category_name, "codex_category_font", color), (list_panel_x + 10, y_pos))
            nav_instr = "UP/DOWN: Select | ENTER: View Entries | ESC: Main Menu"

        elif current_view == "entries":
            # Display entries for the selected category
            category_name = ui_flow_ctrl.codex_current_category_name
            entries = ui_flow_ctrl.codex_entries_in_category_list
            selected_entry_idx = ui_flow_ctrl.codex_selected_entry_index_in_category
            
            cat_title_surf = self._render_text_safe(f"{category_name}", "codex_category_font", GOLD)
            self.screen.blit(cat_title_surf, (list_panel_x + 10, top_y_start))
            current_list_y = top_y_start + cat_title_surf.get_height() + 15
            
            if not entries: 
                self.screen.blit(self._render_text_safe("No entries here.", "codex_entry_font", GREY), (list_panel_x + 20, current_list_y))
            else: # Display scrollable list of entries
                max_visible = self.codex_max_visible_items_list if self.codex_max_visible_items_list > 0 else 1
                start_idx = max(0, selected_entry_idx - max_visible // 2)
                start_idx = min(start_idx, max(0, len(entries) - max_visible))
                end_idx = min(len(entries), start_idx + max_visible)
                for i_display, i_actual in enumerate(range(start_idx, end_idx)):
                    entry_data = entries[i_actual]
                    y_pos = current_list_y + i_display * self.codex_list_item_height
                    color = YELLOW if i_actual == selected_entry_idx else WHITE
                    self.screen.blit(self._render_text_safe(entry_data.get("title", "Untitled"), "codex_entry_font", color), (list_panel_x + 20, y_pos))
            nav_instr = "UP/DOWN: Select | ENTER: Read | ESC: Back to Categories"

        elif current_view == "content":
            # Display content of the selected entry
            selected_entry_id = ui_flow_ctrl.codex_selected_entry_id
            entry_data = self.drone_system.get_lore_entry_details(selected_entry_id) if selected_entry_id else None
            category_name_reminder = ui_flow_ctrl.codex_current_category_name
            is_drone_entry = entry_data.get("category") == "Drones" if entry_data else False
            is_race_entry = entry_data.get("category") == "Alien Races" if entry_data else False
            image_path = entry_data.get("image") if entry_data else None
            current_image_y_pos = top_y_start + 20 # Y pos for image if category reminder is shown

            # Display category reminder in the list panel area
            if category_name_reminder:
                cat_reminder_surf = self._render_text_safe(f"{category_name_reminder}", "codex_entry_font", DARK_GREY)
                self.screen.blit(cat_reminder_surf, (list_panel_x +10 , top_y_start ))
                current_image_y_pos = top_y_start + cat_reminder_surf.get_height() + 20 # Adjust image Y if reminder shown
            
            if entry_data:
                content_title_surf = self._render_text_safe(entry_data.get("title", "Untitled"), "codex_category_font", GOLD)
                self.screen.blit(content_title_surf, (content_panel_x, top_y_start))
                
                content_text_render_y = top_y_start + content_title_surf.get_height() + 20
                text_area_width = content_panel_width - 20 # Width for text content

                # Display image for Drone entries in the list panel area
                if is_drone_entry and image_path:
                    if image_path not in self.codex_image_cache: # Load and cache image
                        try: 
                            self.codex_image_cache[image_path] = pygame.image.load(image_path).convert_alpha()
                        except pygame.error as e: 
                            logging.error(f"UIManager: Error loading Drone Codex image '{image_path}': {e}") # Logging
                            self.codex_image_cache[image_path] = None
                    cached_image = self.codex_image_cache.get(image_path)
                    if cached_image: # Scale and blit drone image
                        img_max_w = list_panel_width - 20
                        img_max_h = HEIGHT * 0.3
                        original_w, original_h = cached_image.get_size()
                        aspect = original_h / original_w if original_w > 0 else 1
                        scaled_w = img_max_w
                        scaled_h = int(scaled_w * aspect)
                        if scaled_h > img_max_h: 
                            scaled_h = int(img_max_h)
                            scaled_w = int(scaled_h / aspect if aspect > 0 else img_max_w)
                        try:
                            self.screen.blit(pygame.transform.smoothscale(cached_image, (scaled_w, scaled_h)), 
                                             (list_panel_x + (list_panel_width - scaled_w) // 2, current_image_y_pos))
                        except pygame.error as e: 
                            logging.error(f"UIManager: Error scaling Drone Codex image '{image_path}': {e}") # Logging
                
                # Display content text (scrollable)
                content_text = entry_data.get("content", "No content available.")
                scroll_offset_lines = ui_flow_ctrl.codex_content_scroll_offset
                wrapped_lines = self._wrap_text(content_text, content_font, text_area_width)
                ui_flow_ctrl.codex_current_entry_total_lines = len(wrapped_lines) # Store total lines for scrolling logic
                
                text_content_area_available_height = bottom_y_end - content_text_render_y - 10
                race_image_to_draw_below_text = None # For Alien Race images
                scaled_race_img_h = 0

                # Prepare image for Alien Race entries (drawn below text)
                if is_race_entry and image_path:
                    if image_path not in self.codex_image_cache:
                        try: 
                            self.codex_image_cache[image_path] = pygame.image.load(image_path).convert_alpha()
                        except pygame.error as e: 
                            logging.error(f"UIManager: Error loading Race Codex image '{image_path}': {e}") # Logging
                            self.codex_image_cache[image_path] = None
                    cached_race_image = self.codex_image_cache.get(image_path)
                    if cached_race_image: # Scale race image
                        img_max_w_race = content_panel_width * 0.6
                        img_max_h_race = HEIGHT * 0.25
                        original_w_race, original_h_race = cached_race_image.get_size()
                        aspect_race = original_h_race / original_w_race if original_w_race > 0 else 1
                        scaled_w_race = img_max_w_race
                        scaled_h_race = int(scaled_w_race * aspect_race)
                        if scaled_h_race > img_max_h_race: 
                            scaled_h_race = int(img_max_h_race)
                            scaled_w_race = int(scaled_h_race / aspect_race if aspect_race > 0 else img_max_w_race)
                        if scaled_w_race > 0 and scaled_h_race > 0:
                            try: 
                                race_image_to_draw_below_text = pygame.transform.smoothscale(cached_race_image, (scaled_w_race, scaled_h_race))
                                scaled_race_img_h = scaled_h_race
                                text_content_area_available_height -= (scaled_race_img_h + 20) # Adjust available height for text
                            except pygame.error as e: 
                                logging.error(f"UIManager: Error scaling Race Codex image '{image_path}': {e}") # Logging
                
                max_lines = text_content_area_available_height // content_line_height if content_line_height > 0 else 0
                if max_lines <= 0 and wrapped_lines: max_lines = 1 # Ensure at least one line is shown if content exists
                
                lines_drawn_y_end = content_text_render_y # Track Y position for drawing race image later
                for i in range(max_lines): # Draw visible lines of text
                    line_idx = scroll_offset_lines + i
                    if 0 <= line_idx < len(wrapped_lines):
                        line_surf = content_font.render(wrapped_lines[line_idx], True, WHITE)
                        self.screen.blit(line_surf, (content_panel_x + 10, content_text_render_y + i * content_line_height))
                        lines_drawn_y_end = content_text_render_y + (i + 1) * content_line_height
                
                # Draw Alien Race image below text if available
                if race_image_to_draw_below_text:
                    race_img_y_pos = lines_drawn_y_end + 20
                    if race_img_y_pos + scaled_race_img_h < bottom_y_end: # Ensure it fits
                        self.screen.blit(race_image_to_draw_below_text, 
                                         (content_panel_x + (text_area_width - race_image_to_draw_below_text.get_width()) // 2, race_img_y_pos))
                
                # Draw scroll indicators (Up/Down arrows) if content is scrollable
                if len(wrapped_lines) > max_lines: 
                    if scroll_offset_lines > 0: 
                        self.screen.blit(self._render_text_safe("▲ Up", "small_text", YELLOW), 
                                         (content_panel_x + text_area_width - self._render_text_safe("▲ Up", "small_text", YELLOW).get_width(), content_text_render_y - 25))
                    if scroll_offset_lines + max_lines < len(wrapped_lines):
                        scroll_down_surf = self._render_text_safe("▼ Down", "small_text", YELLOW)
                        # Adjust Y position of "Down" indicator based on whether race image is present
                        scroll_down_y_pos = lines_drawn_y_end + 5 
                        if race_image_to_draw_below_text and (race_img_y_pos + scaled_race_img_h + scroll_down_surf.get_height() > bottom_y_end -5):
                            scroll_down_y_pos = lines_drawn_y_end + 5 
                        elif not race_image_to_draw_below_text: 
                            scroll_down_y_pos = bottom_y_end - scroll_down_surf.get_height() -5
                        self.screen.blit(scroll_down_surf, (content_panel_x + text_area_width - scroll_down_surf.get_width(), scroll_down_y_pos ))
                nav_instr = "UP/DOWN: Scroll | ESC: Back to Entries List"
            else: # Error loading entry content
                self.screen.blit(self._render_text_safe("Error: Could not load entry content.", "medium_text", RED), 
                                 self._render_text_safe("Error: Could not load entry content.", "medium_text", RED).get_rect(center=(content_panel_x + content_panel_width // 2, HEIGHT // 2)))
                nav_instr = "ESC: Back"
        else: # Default navigation instruction
            nav_instr = "ESC: Main Menu"
        
        # Draw navigation instructions at the bottom
        nav_surf = self._render_text_safe(nav_instr, "small_text", self.INSTRUCTION_TEXT_COLOR)
        nav_bg_box = pygame.Surface((nav_surf.get_width() + self.INSTRUCTION_PADDING_X, nav_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        nav_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        nav_bg_box.blit(nav_surf, nav_surf.get_rect(center=(nav_bg_box.get_width() // 2, nav_bg_box.get_height() // 2)))
        self.screen.blit(nav_bg_box, nav_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))

    def draw_main_menu(self):
        """Draws the main menu screen with options."""
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        # Draw background (image or starfield)
        if self.ui_assets["menu_background"]:
            try: 
                self.screen.blit(pygame.transform.smoothscale(self.ui_assets["menu_background"], (WIDTH, HEIGHT)), (0,0))
            except Exception as e: 
                logging.error(f"UIManager: Error blitting menu background: {e}") # Logging
                self.screen.fill(BLACK) # Fallback background
        else: 
            self.screen.fill(BLACK) 
        
        if ui_flow_ctrl.menu_stars: # Draw starfield
            for star_params in ui_flow_ctrl.menu_stars: 
                pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])
        
        selected_option_idx = ui_flow_ctrl.selected_menu_option
        menu_item_start_y = HEIGHT // 2 - 80 
        item_spacing = 85 
        unselected_label_font_size = 48
        selected_label_font_size = 54
        temp_icon_font = self.fonts.get("ui_emoji_general", self.fonts.get("menu_text")) # Font for icons
        font_path_neuropol = self.game_controller.font_path_neuropol # Main menu font path

        # Menu options with icons (emojis or symbols)
        menu_options_with_icons = { 
            "Start Game": "🛸 Start Game", "Maze Defense": "🛡️ Maze Defense", 
            "Select Drone": "\U0001F579 Select Drone", "Codex": "📜 Codex", 
            "Settings": "\u2699 Settings", "Leaderboard": "🏆 Leaderboard", "Quit": "❌ Quit" 
        }
        actual_menu_options = ui_flow_ctrl.menu_options # Get options from UIFlowController

        # Calculate max width and height for consistent button size
        max_combined_width = 0
        max_content_height = 0
        icon_label_spacing = 10
        for option_key_calc in actual_menu_options:
            full_label_calc = menu_options_with_icons.get(option_key_calc, option_key_calc)
            icon_char_calc = ""
            label_text_calc = full_label_calc
            if len(full_label_calc) >= 2 and full_label_calc[1] == " " and not full_label_calc[0].isalnum(): 
                icon_char_calc = full_label_calc[0]
                label_text_calc = full_label_calc[2:]
            
            try: 
                temp_label_font_for_calc = pygame.font.Font(font_path_neuropol, selected_label_font_size) if font_path_neuropol else pygame.font.Font(None, selected_label_font_size)
            except Exception: 
                temp_label_font_for_calc = pygame.font.Font(None, selected_label_font_size)
            
            icon_surf_calc = temp_icon_font.render(icon_char_calc, True, WHITE) if icon_char_calc else None
            label_surf_calc = temp_label_font_for_calc.render(label_text_calc, True, WHITE)
            
            current_combined_width = 0
            current_content_height = 0
            if icon_surf_calc: 
                current_combined_width += icon_surf_calc.get_width() + icon_label_spacing
                current_content_height = max(current_content_height, icon_surf_calc.get_height())
            current_combined_width += label_surf_calc.get_width()
            current_content_height = max(current_content_height, label_surf_calc.get_height())
            
            max_combined_width = max(max_combined_width, current_combined_width)
            max_content_height = max(max_content_height, current_content_height)
        
        horizontal_padding = 40 
        vertical_padding = 20
        min_button_width = 300 
        fixed_button_width = max(min_button_width, max_combined_width + horizontal_padding)
        fixed_button_height = max_content_height + vertical_padding

        # Draw each menu item as a button
        for i, option_key in enumerate(actual_menu_options):
            full_label = menu_options_with_icons.get(option_key, option_key)
            is_selected = (i == selected_option_idx)
            text_color = GOLD if is_selected else WHITE
            
            icon_char = ""
            label_text = full_label
            if len(full_label) >= 2 and full_label[1] == " " and not full_label[0].isalnum(): 
                icon_char = full_label[0]
                label_text = full_label[2:]
            
            current_label_font_size = selected_label_font_size if is_selected else unselected_label_font_size
            try: 
                label_font = pygame.font.Font(font_path_neuropol, current_label_font_size) if font_path_neuropol else pygame.font.Font(None, current_label_font_size)
            except Exception: 
                label_font = pygame.font.Font(None, current_label_font_size)
            
            icon_font = temp_icon_font
            icon_surf = icon_font.render(icon_char, True, text_color) if icon_char else None
            label_surf = label_font.render(label_text, True, text_color)
            
            # Create button surface
            button_surface = pygame.Surface((fixed_button_width, fixed_button_height), pygame.SRCALPHA)
            bg_color = (70, 70, 70, 220) if is_selected else (50, 50, 50, 180) # Background color
            pygame.draw.rect(button_surface, bg_color, button_surface.get_rect(), border_radius=15)
            if is_selected: # Highlight selected button
                pygame.draw.rect(button_surface, GOLD, button_surface.get_rect(), 3, border_radius=15)
            
            # Position icon and label within the button
            content_start_x = horizontal_padding // 2 
            y_center_content = fixed_button_height // 2
            if icon_surf: 
                icon_rect = icon_surf.get_rect(centery=y_center_content)
                icon_rect.left = content_start_x
                button_surface.blit(icon_surf, icon_rect)
                content_start_x = icon_rect.right + icon_label_spacing
            
            label_rect = label_surf.get_rect(centery=y_center_content)
            label_rect.left = content_start_x
            button_surface.blit(label_surf, label_rect)
            
            current_button_y = menu_item_start_y + i * item_spacing
            button_screen_rect = button_surface.get_rect(center=(WIDTH // 2, current_button_y))
            self.screen.blit(button_surface, button_screen_rect) # Draw button to screen
            
        # Draw navigation instructions
        instr_text = "Use UP/DOWN keys, ENTER to select."
        instr_surf = self._render_text_safe(instr_text, "small_text", self.INSTRUCTION_TEXT_COLOR)
        instr_bg_box = pygame.Surface((instr_surf.get_width() + self.INSTRUCTION_PADDING_X, instr_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        instr_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        instr_bg_box.blit(instr_surf, instr_surf.get_rect(center=(instr_bg_box.get_width() // 2, instr_bg_box.get_height() // 2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))
        
        # Display warning if settings are modified (disables leaderboard)
        if gs.SETTINGS_MODIFIED:
            warning_surf = self._render_text_safe("Custom settings active: Leaderboard disabled.", "small_text", YELLOW)
            warning_bg_box = pygame.Surface((warning_surf.get_width() + self.INSTRUCTION_PADDING_X, warning_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
            warning_bg_box.fill(self.INSTRUCTION_BG_COLOR)
            warning_bg_box.blit(warning_surf, warning_surf.get_rect(center=(warning_bg_box.get_width() // 2, warning_bg_box.get_height() // 2)))
            self.screen.blit(warning_bg_box, warning_bg_box.get_rect(center=(WIDTH // 2, self.SECONDARY_INSTRUCTION_CENTER_Y)))

    def draw_drone_select_menu(self):
        """Draws the drone selection screen with stats and preview."""
        # (Logic remains largely the same as provided, ensure all variables are correctly accessed
        # from self.game_controller, self.ui_flow_controller, and self.drone_system as needed)
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        title_surf = self._render_text_safe("Select Drone", "title_text", GOLD)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 70))
        self.screen.blit(title_surf, title_rect)

        drone_options_ids = ui_flow_ctrl.drone_select_options
        selected_preview_idx = ui_flow_ctrl.selected_drone_preview_index

        if not drone_options_ids: # Handle case where no drones are available
            no_drones_surf = self._render_text_safe("NO DRONES AVAILABLE", "large_text", RED)
            self.screen.blit(no_drones_surf, no_drones_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            return

        current_drone_id = drone_options_ids[selected_preview_idx]
        drone_config = self.drone_system.get_drone_config(current_drone_id)
        drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False) # Get stats for normal play
        is_unlocked = self.drone_system.is_drone_unlocked(current_drone_id)
        is_currently_equipped = (current_drone_id == self.drone_system.get_selected_drone_id())
        
        # Get cached drone image or fallback
        drone_image_surf = self.game_controller.drone_main_display_cache.get(current_drone_id)
        img_width = drone_image_surf.get_width() if drone_image_surf else 200
        img_height = drone_image_surf.get_height() if drone_image_surf else 200

        # Drone Name
        name_text = drone_config.get("name", "N/A")
        name_surf_temp = self.fonts["drone_name_cycle"].render(name_text, True, WHITE) # For height calculation
        name_height = name_surf_temp.get_height()

        # Drone Stats Display
        hp_stat = drone_stats.get("hp")
        speed_stat = drone_stats.get("speed")
        turn_speed_stat = drone_stats.get("turn_speed")
        fire_rate_mult = drone_stats.get("fire_rate_multiplier", 1.0)
        special_ability_key = drone_stats.get("special_ability")

        hp_display = str(hp_stat) if hp_stat is not None else "N/A"
        speed_display = f"{speed_stat:.1f}" if isinstance(speed_stat, (int, float)) else "N/A"
        turn_speed_display = f"{turn_speed_stat:.1f}" if isinstance(turn_speed_stat, (int, float)) else "N/A"
        
        fire_rate_text = f"{fire_rate_mult:.2f}x mult"
        if fire_rate_mult == 1.0: fire_rate_text = "Normal"
        elif fire_rate_mult < 1.0: fire_rate_text += " (Faster)" # Note: Multiplier < 1 means faster cooldown
        else: fire_rate_text += " (Slower)"

        special_ability_name = "None"
        if special_ability_key == "phantom_cloak": special_ability_name = "Phantom Cloak"
        elif special_ability_key == "omega_boost": special_ability_name = "Omega Boost"
        elif special_ability_key == "energy_shield_pulse": special_ability_name = "Shield Pulse"
        
        stats_data_tuples = [
            ("HP:", hp_display), ("Speed:", speed_display), 
            ("Turn Speed:", turn_speed_display), ("Fire Rate:", fire_rate_text), 
            ("Special:", special_ability_name)
        ]
        stats_content_surfaces = []
        max_stat_label_w = 0
        max_stat_value_w = 0
        stat_line_h = self.fonts["drone_stats_label_cycle"].get_height() + 5 # Spacing for stats lines

        for label_str, value_str in stats_data_tuples:
            label_s = self._render_text_safe(label_str, "drone_stats_label_cycle", LIGHT_BLUE if is_unlocked else GREY)
            value_s = self._render_text_safe(value_str, "drone_stats_value_cycle", WHITE if is_unlocked else GREY)
            stats_content_surfaces.append((label_s, value_s))
            max_stat_label_w = max(max_stat_label_w, label_s.get_width())
            max_stat_value_w = max(max_stat_value_w, value_s.get_width())
        
        stats_box_padding = 15
        stats_box_visual_width = max_stat_label_w + max_stat_value_w + 3 * stats_box_padding # Width of the stats box
        stats_box_visual_height = (len(stats_content_surfaces) * stat_line_h) - (5 if stats_content_surfaces else 0) + 2 * stats_box_padding

        # Drone Description
        desc_text = drone_config.get("description", "")
        desc_color_final = (200,200,200) if is_unlocked else (100,100,100)
        desc_max_width_for_card = WIDTH * 0.45 # Max width for description text
        desc_lines_surfs = []
        words = desc_text.split(' ')
        current_line_text_desc = ""
        desc_font = self.fonts["drone_desc_cycle"]
        for word in words: # Wrap description text
            test_line = current_line_text_desc + word + " "
            if desc_font.size(test_line)[0] < desc_max_width_for_card:
                current_line_text_desc = test_line
            else:
                desc_lines_surfs.append(self._render_text_safe(current_line_text_desc.strip(), "drone_desc_cycle", desc_color_final))
                current_line_text_desc = word + " "
        if current_line_text_desc: 
            desc_lines_surfs.append(self._render_text_safe(current_line_text_desc.strip(), "drone_desc_cycle", desc_color_final))
        total_desc_height = sum(s.get_height() for s in desc_lines_surfs) + (len(desc_lines_surfs)-1)*3 if desc_lines_surfs else 0

        # Unlock/Select Info Text
        unlock_text_str = ""
        unlock_text_color = WHITE
        unlock_condition = drone_config.get("unlock_condition", {})
        if not is_unlocked:
            condition_text_str = unlock_condition.get("description", "Locked")
            unlock_cost_val = unlock_condition.get("value")
            type_is_cores_unlock = unlock_condition.get("type") == "cores"
            unlock_text_str = condition_text_str
            if type_is_cores_unlock and unlock_cost_val is not None:
                 can_afford = self.drone_system.get_player_cores() >= unlock_cost_val
                 unlock_text_str = f"Unlock: {unlock_cost_val} 💠 " # Use core emoji
                 unlock_text_str += "(ENTER)" if can_afford else "(Not Enough Cores)"
                 unlock_text_color = GREEN if can_afford else YELLOW
            else: # For other unlock types like level or boss
                unlock_text_color = YELLOW
        elif is_currently_equipped:
            unlock_text_str = "EQUIPPED"
            unlock_text_color = GREEN
        else: # Unlocked but not equipped
            unlock_text_str = "Press ENTER to Select"
            unlock_text_color = CYAN
        
        unlock_info_surf = self._render_text_safe(unlock_text_str, "drone_unlock_cycle", unlock_text_color)
        unlock_info_height = unlock_info_surf.get_height() if unlock_info_surf else 0

        # Calculate overall card dimensions
        spacing_between_elements = 15
        padding_inside_card = 25
        card_content_total_h = (img_height + spacing_between_elements + name_height + 
                                spacing_between_elements + stats_box_visual_height + 
                                spacing_between_elements + total_desc_height + 
                                spacing_between_elements + unlock_info_height)
        
        max_content_width_for_card = max(img_width, name_surf_temp.get_width(), 
                                         stats_box_visual_width, 
                                         max(s.get_width() for s in desc_lines_surfs) if desc_lines_surfs else 0, 
                                         unlock_info_surf.get_width() if unlock_info_surf else 0)
        
        card_w = max_content_width_for_card + 2 * padding_inside_card
        card_w = min(card_w, WIDTH * 0.6) # Cap card width
        card_h = card_content_total_h + 2 * padding_inside_card + 20 # Extra padding at bottom

        # Position and draw the main card
        title_bottom = title_rect.bottom if title_rect else 100
        main_card_x = (WIDTH - card_w) // 2
        main_card_y = title_bottom + 40
        main_card_rect = pygame.Rect(main_card_x, main_card_y, card_w, card_h)
        
        pygame.draw.rect(self.screen, (25,30,40,230), main_card_rect, border_radius=20) # Card background
        pygame.draw.rect(self.screen, GOLD, main_card_rect, 3, border_radius=20) # Card border

        # Draw elements inside the card, positioning them vertically
        current_y_in_card = main_card_rect.top + padding_inside_card

        # Drone Image
        if drone_image_surf:
            display_drone_image = drone_image_surf
            if not is_unlocked: # Dim image if locked
                temp_img = drone_image_surf.copy()
                temp_img.set_alpha(100)
                display_drone_image = temp_img
            final_img_rect = display_drone_image.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(display_drone_image, final_img_rect)
            current_y_in_card = final_img_rect.bottom + spacing_between_elements
        else: # Placeholder if no image
            current_y_in_card += img_height + spacing_between_elements 

        # Drone Name
        name_color_final = WHITE if is_unlocked else GREY
        name_surf_final = self._render_text_safe(name_text, "drone_name_cycle", name_color_final)
        final_name_rect = name_surf_final.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
        self.screen.blit(name_surf_final, final_name_rect)
        current_y_in_card = final_name_rect.bottom + spacing_between_elements

        # Stats Box
        final_stats_box_draw_rect = pygame.Rect(main_card_rect.centerx - stats_box_visual_width // 2, 
                                                current_y_in_card, 
                                                stats_box_visual_width, stats_box_visual_height)
        pygame.draw.rect(self.screen, (40,45,55,200), final_stats_box_draw_rect, border_radius=10) # Stats box bg
        pygame.draw.rect(self.screen, CYAN, final_stats_box_draw_rect, 1, border_radius=10) # Stats box border
        
        stat_y_pos_render = final_stats_box_draw_rect.top + stats_box_padding
        for i, (label_s, value_s) in enumerate(stats_content_surfaces): # Draw each stat line
            self.screen.blit(label_s, (final_stats_box_draw_rect.left + stats_box_padding, stat_y_pos_render))
            self.screen.blit(value_s, (final_stats_box_draw_rect.right - stats_box_padding - value_s.get_width(), stat_y_pos_render))
            stat_y_pos_render += max(label_s.get_height(), value_s.get_height()) + (5 if i < len(stats_content_surfaces)-1 else 0)
        current_y_in_card = final_stats_box_draw_rect.bottom + spacing_between_elements
        
        # Description
        desc_start_y_render = current_y_in_card
        for line_surf in desc_lines_surfs:
            self.screen.blit(line_surf, line_surf.get_rect(centerx=main_card_rect.centerx, top=desc_start_y_render))
            desc_start_y_render += line_surf.get_height() + 3 # Line spacing for description
        current_y_in_card = desc_start_y_render + 5 
        
        # Unlock/Select Info
        if unlock_info_surf:
            unlock_info_rect = unlock_info_surf.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(unlock_info_surf, unlock_info_rect)

        # Navigation Arrows (Left/Right)
        arrow_font = self.fonts.get("arrow_font_key", self.fonts["large_text"])
        left_arrow_surf = arrow_font.render("◀", True, WHITE if len(drone_options_ids) > 1 else GREY)
        right_arrow_surf = arrow_font.render("▶", True, WHITE if len(drone_options_ids) > 1 else GREY)
        arrow_y_center = main_card_rect.centery
        arrow_padding_from_card_edge = 40
        if len(drone_options_ids) > 1: # Only show arrows if multiple drones
            left_arrow_rect = left_arrow_surf.get_rect(centery=arrow_y_center, right=main_card_rect.left - arrow_padding_from_card_edge)
            self.screen.blit(left_arrow_surf, left_arrow_rect)
            right_arrow_rect = right_arrow_surf.get_rect(centery=arrow_y_center, left=main_card_rect.right + arrow_padding_from_card_edge)
            self.screen.blit(right_arrow_surf, right_arrow_rect)
        
        # Navigation Instructions
        instr_text = "LEFT/RIGHT: Cycle | ENTER: Select/Unlock | ESC: Back"
        instr_surf = self._render_text_safe(instr_text, "small_text", self.INSTRUCTION_TEXT_COLOR)
        instr_bg_box = pygame.Surface((instr_surf.get_width() + self.INSTRUCTION_PADDING_X, instr_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        instr_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        instr_bg_box.blit(instr_surf, instr_surf.get_rect(center=(instr_bg_box.get_width() // 2, instr_bg_box.get_height() // 2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))
        
        # Player Cores Display
        cores_label_text_surf = self._render_text_safe(f"Player Cores: ", "ui_text", GOLD)
        cores_value_text_surf = self._render_text_safe(f"{self.drone_system.get_player_cores()}", "ui_values", GOLD)
        cores_emoji_surf = self._render_text_safe(" 💠", "ui_emoji_general", GOLD) # Core emoji
        
        total_cores_display_width = cores_label_text_surf.get_width() + cores_value_text_surf.get_width() + cores_emoji_surf.get_width()
        cores_start_x = WIDTH - 20 - total_cores_display_width # Position on right side
        max_element_height_cores = max(cores_label_text_surf.get_height(), cores_value_text_surf.get_height(), cores_emoji_surf.get_height())
        # Position cores display above the bottom instruction text
        cores_y_baseline = self.BOTTOM_INSTRUCTION_CENTER_Y - (instr_bg_box.get_height() // 2) - 10 - max_element_height_cores 
        current_x_offset_cores = cores_start_x
        
        self.screen.blit(cores_label_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_label_text_surf.get_height()) // 2))
        current_x_offset_cores += cores_label_text_surf.get_width()
        self.screen.blit(cores_value_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_value_text_surf.get_height()) // 2))
        current_x_offset_cores += cores_value_text_surf.get_width()
        self.screen.blit(cores_emoji_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_emoji_surf.get_height()) // 2))

    def draw_settings_menu(self):
        """Draws the settings menu with configurable options."""
        # (Logic remains largely the same as provided, ensure all variables are correctly accessed
        # from self.ui_flow_controller and game_settings as needed)
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        title_surf = self._render_text_safe("Settings", "title_text", GOLD)
        title_bg = pygame.Surface((title_surf.get_width()+30, title_surf.get_height()+15), pygame.SRCALPHA)
        title_bg.fill((20,20,20,180)) # Semi-transparent background for title
        title_bg.blit(title_surf, title_surf.get_rect(center=(title_bg.get_width()//2, title_bg.get_height()//2)))
        self.screen.blit(title_bg, title_bg.get_rect(center=(WIDTH//2, 80)))

        settings_items = ui_flow_ctrl.settings_items_data
        selected_idx = ui_flow_ctrl.selected_setting_index
        
        item_y_start = 180 # Starting Y for settings items
        item_line_height = self.fonts["ui_text"].get_height() + 20 # Spacing between items
        max_items_on_screen = (HEIGHT - item_y_start - 120) // item_line_height # Calculate max visible items for scrolling
        
        view_start_index = 0 # For scrolling long lists of settings
        if len(settings_items) > max_items_on_screen:
            view_start_index = max(0, selected_idx - max_items_on_screen // 2)
            view_start_index = min(view_start_index, len(settings_items) - max_items_on_screen)
        view_end_index = min(view_start_index + max_items_on_screen, len(settings_items))

        # Draw each visible setting item
        for i_display, list_idx in enumerate(range(view_start_index, view_end_index)):
            if list_idx >= len(settings_items): continue # Should not happen with correct view_end_index
            
            item = settings_items[list_idx]
            y_pos = item_y_start + i_display * item_line_height
            color = YELLOW if list_idx == selected_idx else WHITE # Highlight selected item
            
            # Draw setting label
            label_surf = self._render_text_safe(item["label"], "ui_text", color)
            label_bg_rect_width = max(250, label_surf.get_width() + 20) # Ensure min width for bg
            label_bg_rect = pygame.Rect(WIDTH // 4 - 150, y_pos - 5, label_bg_rect_width, label_surf.get_height() + 10)
            pygame.draw.rect(self.screen, (30,30,30,160), label_bg_rect, border_radius=5) # Label background
            self.screen.blit(label_surf, (label_bg_rect.left + 10, y_pos))
            
            # Display note for selected item if available
            if "note" in item and list_idx == selected_idx:
                note_surf = self._render_text_safe(item["note"], "small_text", LIGHT_BLUE)
                self.screen.blit(note_surf, note_surf.get_rect(left=label_bg_rect.right + 15, centery=label_bg_rect.centery))

            # Display current value or action hint
            if item["type"] != "action": # For numeric or choice settings
                current_value = get_game_setting(item["key"])
                display_value = ""
                if item["type"] == "numeric":
                    display_format = item.get("display_format", "{}")
                    value_to_format = current_value
                    if item.get("is_ms_to_sec"): # Convert ms to seconds for display
                        value_to_format = current_value / 1000
                    try: 
                        display_value = display_format.format(value_to_format)
                    except (ValueError, TypeError): # Fallback if format fails
                        display_value = str(value_to_format) if not item.get("is_ms_to_sec") else f"{value_to_format:.0f}s"
                elif item["type"] == "choice": # Get display string for choice
                    display_value = item["get_display"](current_value)
                
                value_surf = self._render_text_safe(display_value, "ui_text", color)
                value_bg_rect_width = max(100, value_surf.get_width() + 20)
                value_bg_rect = pygame.Rect(WIDTH // 2 + 150, y_pos - 5, value_bg_rect_width, value_surf.get_height() + 10)
                pygame.draw.rect(self.screen, (30,30,30,160), value_bg_rect, border_radius=5) # Value background
                self.screen.blit(value_surf, (value_bg_rect.left + 10, y_pos))
                
                # Indicate if setting is modified from default
                if item["key"] in DEFAULT_SETTINGS and current_value != DEFAULT_SETTINGS[item["key"]]:
                    self.screen.blit(self._render_text_safe("*", "small_text", RED), (value_bg_rect.right + 5, y_pos))
            
            elif list_idx == selected_idx: # For "action" type settings (like Reset)
                 action_hint_surf = self._render_text_safe("<ENTER>", "ui_text", YELLOW)
                 action_hint_bg_rect = pygame.Rect(WIDTH // 2 + 150, y_pos - 5, action_hint_surf.get_width() + 20, action_hint_surf.get_height() + 10)
                 pygame.draw.rect(self.screen, (40,40,40,180), action_hint_bg_rect, border_radius=5)
                 self.screen.blit(action_hint_surf, (action_hint_bg_rect.left + 10, y_pos))
        
        # Draw navigation instructions
        instr_text = "UP/DOWN: Select | LEFT/RIGHT: Adjust | ENTER: Activate | ESC: Back"
        instr_surf = self._render_text_safe(instr_text, "small_text", self.INSTRUCTION_TEXT_COLOR)
        instr_bg_box = pygame.Surface((instr_surf.get_width() + self.INSTRUCTION_PADDING_X, instr_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        instr_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        instr_bg_box.blit(instr_surf, instr_surf.get_rect(center=(instr_bg_box.get_width() // 2, instr_bg_box.get_height() // 2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))
        
        # Warning if settings modified (disables leaderboard)
        if gs.SETTINGS_MODIFIED:
            warning_text = "Leaderboard disabled: settings changed from default values!"
            warning_surf = self._render_text_safe(warning_text, "small_text", RED)
            warning_bg_box = pygame.Surface((warning_surf.get_width() + self.INSTRUCTION_PADDING_X, warning_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
            warning_bg_box.fill(self.INSTRUCTION_BG_COLOR)
            warning_bg_box.blit(warning_surf, warning_surf.get_rect(center=(warning_bg_box.get_width() // 2, warning_bg_box.get_height() // 2)))
            self.screen.blit(warning_bg_box, warning_bg_box.get_rect(center=(WIDTH // 2, self.SECONDARY_INSTRUCTION_CENTER_Y)))

    def draw_gameplay_hud(self):
        """Draws the Heads-Up Display for standard gameplay and bonus levels."""
        if not self.game_controller.player: return # No HUD if no player

        # Panel background at the bottom
        panel_y_start = GAME_PLAY_AREA_HEIGHT
        panel_height = BOTTOM_PANEL_HEIGHT
        panel_surf = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA)
        panel_surf.fill((20,25,35,220)) # Dark semi-transparent panel
        pygame.draw.line(panel_surf, (80,120,170,200), (0,0), (WIDTH,0), 2) # Top border line
        self.screen.blit(panel_surf, (0, panel_y_start))

        # Layout parameters
        h_padding = 20 # Horizontal padding from screen edges
        v_padding = 10 # Vertical padding from panel top/bottom
        element_spacing = 6 # Vertical spacing between HUD elements
        bar_height = 18 # Height of progress bars (weapon charge, power-up duration)
        icon_to_bar_gap = 10 # Gap between an icon and its associated bar
        icon_spacing = 5 # Spacing between multiple icons (e.g., lives)
        text_icon_spacing = 2 # Spacing between text and an icon

        current_time_ticks = pygame.time.get_ticks()
        # Fonts for HUD elements
        label_font = self.fonts["ui_text"]
        value_font = self.fonts["ui_values"]
        emoji_general_font = self.fonts["ui_emoji_general"]
        small_value_font = self.fonts.get("small_text") # For smaller values like core count

        # --- Left Side of HUD (Player Vitals) ---
        vitals_x_start = h_padding
        current_vitals_y = panel_y_start + panel_height - v_padding # Start from bottom of panel and go up
        vitals_section_width = int(WIDTH / 3.2) # Max width for this section

        # Determine max icon width on the left for alignment of bars
        max_icon_width_left = 0
        player_obj = self.game_controller.player # Convenience reference
        temp_weapon_icon_surf = self._render_text_safe(WEAPON_MODE_ICONS.get(player_obj.current_weapon_mode, "💥"), "ui_emoji_small", ORANGE)
        max_icon_width_left = max(max_icon_width_left, temp_weapon_icon_surf.get_width())
        if self.ui_assets.get("current_drone_life_icon"):
            max_icon_width_left = max(max_icon_width_left, self.ui_assets["current_drone_life_icon"].get_width())
        
        # Player Lives
        life_icon_surf = self.ui_assets.get("current_drone_life_icon")
        if life_icon_surf:
            lives_y_pos = current_vitals_y - self.ui_icon_size_lives[1] # Position lives at the bottom of vitals
            lives_draw_x = vitals_x_start
            for i in range(self.game_controller.lives): # Draw one icon per life
                self.screen.blit(life_icon_surf, (lives_draw_x + i * (self.ui_icon_size_lives[0] + icon_spacing), lives_y_pos))
            current_vitals_y = lives_y_pos - element_spacing # Move Y up for next element

        # Weapon Charge Bar
        weapon_bar_y_pos = current_vitals_y - bar_height
        weapon_icon_surf = temp_weapon_icon_surf # Already rendered
        self.screen.blit(weapon_icon_surf, (vitals_x_start, weapon_bar_y_pos + (bar_height - weapon_icon_surf.get_height()) // 2)) # Center icon vertically with bar
        
        bar_start_x_weapon = vitals_x_start + weapon_icon_surf.get_width() + icon_to_bar_gap
        # Calculate bar width, ensuring it's not too small
        min_bar_segment_width = 25 
        bar_segment_reduction_factor = 0.85 # How much of the available space the bar takes
        bar_segment_width_weapon = max(min_bar_segment_width, int((vitals_section_width - (weapon_icon_surf.get_width() + icon_to_bar_gap)) * bar_segment_reduction_factor))
        
        charge_fill_pct = 0.0
        weapon_ready_color = PLAYER_BULLET_COLOR # Default color
        cooldown_duration = player_obj.current_shoot_cooldown
        time_since_last_shot = current_time_ticks - player_obj.last_shot_time
        
        # Adjust for special weapons (missile, lightning)
        if player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER") or \
           player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS"):
            weapon_ready_color = MISSILE_COLOR
            time_since_last_shot = current_time_ticks - player_obj.last_missile_shot_time
            cooldown_duration = player_obj.current_missile_cooldown
        elif player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_LIGHTNING"):
            weapon_ready_color = LIGHTNING_COLOR
            time_since_last_shot = current_time_ticks - player_obj.last_lightning_time
            cooldown_duration = player_obj.current_lightning_cooldown
        
        if cooldown_duration > 0: # Calculate charge percentage
            charge_fill_pct = min(1.0, time_since_last_shot / cooldown_duration)
        else: # No cooldown (or error), assume fully charged
            charge_fill_pct = 1.0
        
        charge_bar_fill_color = weapon_ready_color if charge_fill_pct >= 1.0 else ORANGE # Orange if charging
        weapon_bar_width_fill = int(bar_segment_width_weapon * charge_fill_pct)
        
        pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_weapon, weapon_bar_y_pos, bar_segment_width_weapon, bar_height)) # Bar background
        if weapon_bar_width_fill > 0:
            pygame.draw.rect(self.screen, charge_bar_fill_color, (bar_start_x_weapon, weapon_bar_y_pos, weapon_bar_width_fill, bar_height)) # Filled portion
        pygame.draw.rect(self.screen, WHITE, (bar_start_x_weapon, weapon_bar_y_pos, bar_segment_width_weapon, bar_height), 1) # Bar border
        current_vitals_y = weapon_bar_y_pos - element_spacing # Move Y up

        # Active Power-up Duration Bar (Shield or Speed Boost)
        active_powerup_for_ui = player_obj.active_powerup_type
        if active_powerup_for_ui and (player_obj.shield_active or player_obj.speed_boost_active):
            powerup_bar_y_pos = current_vitals_y - bar_height
            powerup_icon_char = ""
            powerup_bar_fill_color = WHITE
            powerup_fill_percentage = 0.0
            powerup_details_config = POWERUP_TYPES.get(active_powerup_for_ui, {})

            if active_powerup_for_ui == "shield" and player_obj.shield_active:
                powerup_icon_char = "🛡️" # Shield emoji
                powerup_bar_fill_color = powerup_details_config.get("color", LIGHT_BLUE)
                remaining_time = player_obj.shield_end_time - current_time_ticks
                if player_obj.shield_duration > 0 and remaining_time > 0:
                    powerup_fill_percentage = remaining_time / player_obj.shield_duration
            elif active_powerup_for_ui == "speed_boost" and player_obj.speed_boost_active:
                powerup_icon_char = "💨" # Speed boost emoji
                powerup_bar_fill_color = powerup_details_config.get("color", GREEN)
                remaining_time = player_obj.speed_boost_end_time - current_time_ticks
                if player_obj.speed_boost_duration > 0 and remaining_time > 0:
                    powerup_fill_percentage = remaining_time / player_obj.speed_boost_duration
            
            powerup_fill_percentage = max(0, min(1, powerup_fill_percentage)) # Clamp percentage
            
            if powerup_icon_char: # If a power-up is active and has an icon
                powerup_icon_surf = self._render_text_safe(powerup_icon_char, "ui_emoji_small", WHITE)
                self.screen.blit(powerup_icon_surf, (vitals_x_start, powerup_bar_y_pos + (bar_height - powerup_icon_surf.get_height()) // 2))
                
                bar_start_x_powerup = vitals_x_start + powerup_icon_surf.get_width() + icon_to_bar_gap
                bar_segment_width_powerup = max(min_bar_segment_width, int((vitals_section_width - (powerup_icon_surf.get_width() + icon_to_bar_gap)) * bar_segment_reduction_factor))
                bar_width_fill_powerup = int(bar_segment_width_powerup * powerup_fill_percentage)
                
                pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_powerup, powerup_bar_y_pos, bar_segment_width_powerup, bar_height))
                if bar_width_fill_powerup > 0:
                    pygame.draw.rect(self.screen, powerup_bar_fill_color, (bar_start_x_powerup, powerup_bar_y_pos, bar_width_fill_powerup, bar_height))
                pygame.draw.rect(self.screen, WHITE, (bar_start_x_powerup, powerup_bar_y_pos, bar_segment_width_powerup, bar_height), 1)
        
        # --- Right Side of HUD (Collectibles: Cores, Fragments, Rings) ---
        collectibles_x_anchor = WIDTH - h_padding # Anchor from right edge
        current_collectibles_y_right = panel_y_start + panel_height - v_padding # Start from bottom

        # Player Cores
        cores_emoji_char = "💠"
        cores_x_char = "x" # Separator "x"
        cores_value_str = str(self.drone_system.get_player_cores())
        cores_icon_surf = self._render_text_safe(cores_emoji_char, "ui_emoji_general", GOLD)
        cores_x_surf = self._render_text_safe(cores_x_char, "small_text", WHITE)
        cores_value_text_surf = self._render_text_safe(cores_value_str, "small_text", GOLD)
        
        total_cores_width = (cores_icon_surf.get_width() + text_icon_spacing + 
                             cores_x_surf.get_width() + text_icon_spacing + 
                             cores_value_text_surf.get_width())
        cores_start_x_draw = collectibles_x_anchor - total_cores_width # Position from right
        cores_display_max_height = max(cores_icon_surf.get_height(), cores_x_surf.get_height(), cores_value_text_surf.get_height())
        cores_y_pos = current_collectibles_y_right - cores_display_max_height # Position at bottom of this section
        
        current_x_offset = cores_start_x_draw
        self.screen.blit(cores_icon_surf, (current_x_offset, cores_y_pos + (cores_display_max_height - cores_icon_surf.get_height()) // 2))
        current_x_offset += cores_icon_surf.get_width() + text_icon_spacing
        self.screen.blit(cores_x_surf, (current_x_offset, cores_y_pos + (cores_display_max_height - cores_x_surf.get_height()) // 2))
        current_x_offset += cores_x_surf.get_width() + text_icon_spacing
        self.screen.blit(cores_value_text_surf, (current_x_offset, cores_y_pos + (cores_display_max_height - cores_value_text_surf.get_height()) // 2))
        current_collectibles_y_right = cores_y_pos - element_spacing # Move Y up

        # Core Fragments
        fragment_icon_h = self.ui_icon_size_fragments[1]
        fragment_y_pos_hud = current_collectibles_y_right - fragment_icon_h
        fragment_display_order_ids = []
        if CORE_FRAGMENT_DETAILS: # Get ordered list of fragment IDs for display
            try: 
                sorted_frag_keys = sorted([k for k in CORE_FRAGMENT_DETAILS.keys() if k != "fragment_vault_core"]) # Exclude vault core for HUD display
                fragment_display_order_ids = [CORE_FRAGMENT_DETAILS[key]["id"] for key in sorted_frag_keys if "id" in CORE_FRAGMENT_DETAILS[key]]
            except Exception as e: 
                logging.error(f"UIManager: Error creating fragment display order: {e}. Using unsorted.") # Logging
                fragment_display_order_ids = [details["id"] for _, details in CORE_FRAGMENT_DETAILS.items() if details and "id" in details and details.get("id") != "vault_core"]
        
        displayable_fragment_ids = fragment_display_order_ids[:TOTAL_CORE_FRAGMENTS_NEEDED] # Show slots for needed fragments
        
        if hasattr(self.game_controller, 'fragment_ui_target_positions'): # Clear old target positions
            self.game_controller.fragment_ui_target_positions.clear()

        if TOTAL_CORE_FRAGMENTS_NEEDED > 0 :
            total_fragments_width = TOTAL_CORE_FRAGMENTS_NEEDED * self.ui_icon_size_fragments[0] + \
                                    max(0, TOTAL_CORE_FRAGMENTS_NEEDED - 1) * icon_spacing
            fragments_block_start_x = collectibles_x_anchor - total_fragments_width
            
            for i in range(TOTAL_CORE_FRAGMENTS_NEEDED): # Draw each fragment slot
                frag_id_for_this_slot = None
                if i < len(displayable_fragment_ids): 
                    frag_id_for_this_slot = displayable_fragment_ids[i]
                
                # Determine icon (collected or empty)
                icon_to_draw = self.ui_assets["core_fragment_empty_icon"]
                if frag_id_for_this_slot and frag_id_for_this_slot in self.game_controller.hud_displayed_fragments:
                    icon_to_draw = self.ui_assets["core_fragment_icons"].get(frag_id_for_this_slot, self.ui_assets["core_fragment_empty_icon"])
                
                current_frag_x = fragments_block_start_x + i * (self.ui_icon_size_fragments[0] + icon_spacing)
                if icon_to_draw: 
                    self.screen.blit(icon_to_draw, (current_frag_x, fragment_y_pos_hud))
                
                # Store target position for animation if fragment is for this slot
                if frag_id_for_this_slot and hasattr(self.game_controller, 'fragment_ui_target_positions'):
                    self.game_controller.fragment_ui_target_positions[frag_id_for_this_slot] = \
                        (current_frag_x + self.ui_icon_size_fragments[0] // 2, 
                         fragment_y_pos_hud + self.ui_icon_size_fragments[1] // 2)
            current_collectibles_y_right = fragment_y_pos_hud - element_spacing # Move Y up

        # Collected Rings
        total_rings_this_level = self.game_controller.total_rings_per_level
        displayed_rings_count = self.game_controller.displayed_collected_rings_count # For smooth animation
        if self.ui_assets["ring_icon"] and total_rings_this_level > 0:
            ring_icon_h = self.ui_icon_size_rings[1]
            rings_y_pos_hud = current_collectibles_y_right - ring_icon_h
            total_ring_icons_width_only = total_rings_this_level * self.ui_icon_size_rings[0] + \
                                          max(0, total_rings_this_level - 1) * icon_spacing
            rings_block_start_x = collectibles_x_anchor - total_ring_icons_width_only
            
            for i in range(total_rings_this_level): # Draw each ring slot
                icon_to_draw = self.ui_assets["ring_icon"] if i < displayed_rings_count else self.ui_assets["ring_icon_empty"]
                if icon_to_draw: 
                    self.screen.blit(icon_to_draw, (rings_block_start_x + i * (self.ui_icon_size_rings[0] + icon_spacing), rings_y_pos_hud))
            
            # Determine target position for next ring animation
            _next_ring_slot_index = max(0, min(displayed_rings_count, total_rings_this_level - 1))
            target_slot_x_offset = _next_ring_slot_index * (self.ui_icon_size_rings[0] + icon_spacing)
            target_slot_center_x = rings_block_start_x + target_slot_x_offset + self.ui_icon_size_rings[0] // 2
            target_slot_center_y = rings_y_pos_hud + self.ui_icon_size_rings[1] // 2
            if hasattr(self.game_controller, 'ring_ui_target_pos'): 
                self.game_controller.ring_ui_target_pos = (target_slot_center_x, target_slot_center_y)
        
        # --- Center of HUD (Score, Level, Timer) ---
        score_emoji_char = "🏆 "
        score_text_str = f"Score: {self.game_controller.score}"
        score_emoji_surf = self._render_text_safe(score_emoji_char, "ui_emoji_general", GOLD)
        score_text_surf = self._render_text_safe(score_text_str, "ui_text", GOLD)
        
        level_emoji_char = "🎯 "
        level_text_str = f"Level: {self.game_controller.level}"
        current_scene_state = self.scene_manager.get_current_state()
        if current_scene_state == GAME_STATE_BONUS_LEVEL_PLAYING: 
            level_text_str = "Bonus!"
        elif current_scene_state.startswith("architect_vault"): 
            level_text_str = "Architect's Vault"
        level_emoji_surf = self._render_text_safe(level_emoji_char, "ui_emoji_general", CYAN)
        level_text_surf = self._render_text_safe(level_text_str, "ui_text", CYAN)
        
        # Timer display
        time_icon_char = "⏱ "
        time_ms_to_display = self.game_controller.level_time_remaining_ms
        if current_scene_state == GAME_STATE_BONUS_LEVEL_PLAYING: # Adjust for bonus level timer
            elapsed_bonus_time_ms = current_time_ticks - self.game_controller.bonus_level_timer_start
            bonus_duration_ms = self.game_controller.bonus_level_duration_ms
            time_ms_to_display = max(0, bonus_duration_ms - elapsed_bonus_time_ms)
        
        time_seconds_total = max(0, time_ms_to_display // 1000)
        time_value_str = f"{time_seconds_total // 60:02d}:{time_seconds_total % 60:02d}" # Format MM:SS
        time_color = WHITE
        
        is_vault_extraction = (current_scene_state.startswith("architect_vault") and 
                               self.game_controller.architect_vault_current_phase == "extraction")
        
        if not is_vault_extraction: # Standard timer color logic
            if time_seconds_total <= 10: 
                time_color = RED if (current_time_ticks // 250) % 2 == 0 else DARK_RED # Flashing red
            elif time_seconds_total <= 30: 
                time_color = YELLOW # Warning yellow
        
        time_icon_surf = self._render_text_safe(time_icon_char, "ui_emoji_general", time_color)
        time_value_surf = self._render_text_safe(time_value_str, "ui_text", time_color)
        
        # Calculate max height for vertical centering of score/level/timer
        max_central_element_height = 0
        if score_emoji_surf: max_central_element_height = max(max_central_element_height, score_emoji_surf.get_height())
        if score_text_surf: max_central_element_height = max(max_central_element_height, score_text_surf.get_height())
        if level_emoji_surf: max_central_element_height = max(max_central_element_height, level_emoji_surf.get_height())
        if level_text_surf: max_central_element_height = max(max_central_element_height, level_text_surf.get_height())
        if time_icon_surf and not is_vault_extraction: max_central_element_height = max(max_central_element_height, time_icon_surf.get_height())
        if time_value_surf and not is_vault_extraction: max_central_element_height = max(max_central_element_height, time_value_surf.get_height())
        
        info_y_baseline = panel_y_start + (panel_height - max_central_element_height) // 2 # Vertical center in panel
        spacing_between_center_elements = 25
        
        # Calculate total width of central elements for horizontal centering
        center_elements_total_width = (score_emoji_surf.get_width() + text_icon_spacing + 
                                       score_text_surf.get_width() + spacing_between_center_elements + 
                                       level_emoji_surf.get_width() + text_icon_spacing + 
                                       level_text_surf.get_width())
        if not is_vault_extraction: # Add timer width if not in vault extraction
            center_elements_total_width += (spacing_between_center_elements + 
                                            time_icon_surf.get_width() + text_icon_spacing + 
                                            time_value_surf.get_width())
        
        current_info_x = (WIDTH - center_elements_total_width) // 2 # Start X for central elements
        
        # Draw Score
        self.screen.blit(score_emoji_surf, (current_info_x, info_y_baseline + (max_central_element_height - score_emoji_surf.get_height()) // 2))
        current_info_x += score_emoji_surf.get_width() + text_icon_spacing
        self.screen.blit(score_text_surf, (current_info_x, info_y_baseline + (max_central_element_height - score_text_surf.get_height()) // 2))
        current_info_x += score_text_surf.get_width() + spacing_between_center_elements
        
        # Draw Level
        self.screen.blit(level_emoji_surf, (current_info_x, info_y_baseline + (max_central_element_height - level_emoji_surf.get_height()) // 2))
        current_info_x += level_emoji_surf.get_width() + text_icon_spacing
        self.screen.blit(level_text_surf, (current_info_x, info_y_baseline + (max_central_element_height - level_text_surf.get_height()) // 2))
        current_info_x += level_text_surf.get_width() + spacing_between_center_elements
        
        # Draw Timer (if not in vault extraction)
        if not is_vault_extraction:
            self.screen.blit(time_icon_surf, (current_info_x, info_y_baseline + (max_central_element_height - time_icon_surf.get_height()) // 2))
            current_info_x += time_icon_surf.get_width() + text_icon_spacing
            self.screen.blit(time_value_surf, (current_info_x, info_y_baseline + (max_central_element_height - time_value_surf.get_height()) // 2))
        
        # Draw animating collectibles (rings/fragments flying to HUD)
        if hasattr(self.game_controller, 'animating_rings_to_hud'):
            for ring_anim in self.game_controller.animating_rings_to_hud:
                if 'surface' in ring_anim and ring_anim['surface']:
                    anim_surf = ring_anim['surface']
                    draw_x = int(ring_anim['pos'][0] - anim_surf.get_width() / 2)
                    draw_y = int(ring_anim['pos'][1] - anim_surf.get_height() / 2)
                    self.screen.blit(anim_surf, (draw_x, draw_y))
        
        if hasattr(self.game_controller, 'animating_fragments_to_hud'):
            for frag_anim in self.game_controller.animating_fragments_to_hud:
                if 'surface' in frag_anim and frag_anim['surface']:
                    anim_surf = frag_anim['surface']
                    draw_x = int(frag_anim['pos'][0] - anim_surf.get_width() / 2)
                    draw_y = int(frag_anim['pos'][1] - anim_surf.get_height() / 2)
                    self.screen.blit(anim_surf, (draw_x, draw_y))

    def get_scaled_fragment_icon(self, fragment_id):
        """Returns a scaled icon for a given fragment ID, loading if necessary."""
        # Ensure assets are loaded if not already
        if not self.ui_assets["core_fragment_icons"] and not self.ui_assets["core_fragment_empty_icon"]:
            self._load_ui_assets() 
        
        if fragment_id in self.ui_assets["core_fragment_icons"]:
            return self.ui_assets["core_fragment_icons"][fragment_id]
        
        logging.warning(f"UIManager: Scaled icon for fragment_id '{fragment_id}' not found. Using fallback.") # Logging
        return self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", PURPLE)

    def draw_architect_vault_hud_elements(self):
        """Draws HUD elements specific to or modified for the Architect's Vault."""
        self.draw_gameplay_hud() # Base HUD is similar
        
        current_time = pygame.time.get_ticks()
        current_vault_phase = self.game_controller.architect_vault_current_phase

        # Display extraction timer prominently at the top
        if current_vault_phase == "extraction":
            time_remaining_ms_vault = self.game_controller.level_time_remaining_ms # Get remaining time
            time_val_str_vault = f"{max(0, time_remaining_ms_vault // 1000) // 60:02d}:{max(0, time_remaining_ms_vault // 1000) % 60:02d}"
            time_color_vault = RED
            if (time_remaining_ms_vault // 1000) > 10: # More than 10 seconds left
                time_color_vault = YELLOW
            # Flashing effect for last 10 seconds
            if (current_time // 250) % 2 == 0 and (time_remaining_ms_vault // 1000) <= 10 :
                time_color_vault = DARK_RED
            
            timer_surf_vault = self._render_text_safe(f"ESCAPE ROUTE COLLAPSING: {time_val_str_vault}", "vault_timer", time_color_vault)
            self.screen.blit(timer_surf_vault, timer_surf_vault.get_rect(centerx=WIDTH//2, top=10))
        
        # Display Architect's Vault specific messages
        vault_message = self.game_controller.architect_vault_message
        vault_message_timer_end = self.game_controller.architect_vault_message_timer
        if vault_message and current_time < vault_message_timer_end: # If message is active
            msg_surf = self._render_text_safe(vault_message, "vault_message", GOLD)
            msg_bg_surf = pygame.Surface((msg_surf.get_width() + 30, msg_surf.get_height() + 15), pygame.SRCALPHA)
            msg_bg_surf.fill((10, 0, 20, 200)) # Dark purple background for message
            msg_bg_surf.blit(msg_surf, msg_surf.get_rect(center=(msg_bg_surf.get_width()//2, msg_bg_surf.get_height()//2)))
            self.screen.blit(msg_bg_surf, msg_bg_surf.get_rect(centerx=WIDTH//2, bottom=GAME_PLAY_AREA_HEIGHT - 20)) # Position at bottom of game area

    def draw_pause_overlay(self):
        """Draws the pause screen overlay."""
        overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay_surface.fill((0,0,0,150)) # Semi-transparent black overlay
        self.screen.blit(overlay_surface, (0,0))
        
        pause_title_surf = self._render_text_safe("PAUSED", "large_text", WHITE)
        self.screen.blit(pause_title_surf, pause_title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))
        
        current_game_state_when_paused = self.scene_manager.get_current_state()
        pause_text_options = "P: Continue | M: Menu | Q: Quit Game" # Default options
        
        # Customize options based on game state
        if current_game_state_when_paused == GAME_STATE_PLAYING:
            pause_text_options = "P: Continue | L: Leaderboard | M: Menu | Q: Quit Game"
        elif current_game_state_when_paused.startswith("architect_vault"):
            pause_text_options = "P: Continue | ESC: Main Menu (Exit Vault) | Q: Quit Game"
        elif current_game_state_when_paused == GAME_STATE_MAZE_DEFENSE:
            pause_text_options = "P: Resume | M: Menu (End Defense) | Q: Quit"
            
        options_surf = self._render_text_safe(pause_text_options, "ui_text", WHITE)
        self.screen.blit(options_surf, options_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))

    def draw_game_over_overlay(self):
        """Draws the Game Over screen."""
        go_text_surf = self._render_text_safe("GAME OVER", "large_text", RED)
        score_text_surf = self._render_text_safe(f"Final Score: {self.game_controller.score}", "medium_text", WHITE)
        self.screen.blit(go_text_surf, go_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 120)))
        self.screen.blit(score_text_surf, score_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 30)))
        
        can_submit_score = not gs.SETTINGS_MODIFIED # Leaderboard submission disabled if settings changed
        is_high = self.game_controller.is_current_score_a_high_score()
        
        prompt_y_offset = HEIGHT // 2 + 50
        prompt_str = ""
        prompt_color = WHITE
        
        if not can_submit_score: # If leaderboard disabled
            no_lb_text_surf = self._render_text_safe("Leaderboard disabled (custom settings active).", "ui_text", YELLOW)
            self.screen.blit(no_lb_text_surf, no_lb_text_surf.get_rect(center=(WIDTH//2, prompt_y_offset)))
            prompt_y_offset += self.fonts["ui_text"].get_height() + 20
            prompt_str = "R: Restart  M: Menu  Q: Quit"
        elif is_high: # New high score
            prompt_str = "New High Score! Press any key to enter name."
            prompt_color = GOLD
        else: # Not a high score (but leaderboard enabled)
            prompt_str = "R: Restart  L: Leaderboard  M: Menu  Q: Quit"
            
        prompt_surf = self._render_text_safe(prompt_str, "ui_text", prompt_color)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, prompt_y_offset)))

    def draw_enter_name_overlay(self):
        """Draws the screen for entering player name for high score."""
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        title_surf = self._render_text_safe("New High Score!", "large_text", GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 180)))
        
        score_level_text = f"Your Score: {self.game_controller.score} (Level: {self.game_controller.level})"
        score_level_surf = self._render_text_safe(score_level_text, "medium_text", WHITE)
        self.screen.blit(score_level_surf, score_level_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 90)))
        
        prompt_name_surf = self._render_text_safe("Enter Name (max 6 chars, A-Z):", "ui_text", WHITE)
        self.screen.blit(prompt_name_surf, prompt_name_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 20)))
        
        player_name_input_str = ui_flow_ctrl.player_name_input_cache # Get current input from UIFlowController
        input_box_width = 300
        input_box_height = 60
        input_box_rect = pygame.Rect(WIDTH//2 - input_box_width//2, HEIGHT//2 + 30, input_box_width, input_box_height)
        pygame.draw.rect(self.screen, WHITE, input_box_rect, 2, border_radius=10) # Input box border
        
        input_text_surf = self._render_text_safe(player_name_input_str, "input_text", WHITE)
        self.screen.blit(input_text_surf, input_text_surf.get_rect(center=input_box_rect.center)) # Draw entered text
        
        submit_prompt_surf = self._render_text_safe("Press ENTER to submit.", "ui_text", CYAN)
        self.screen.blit(submit_prompt_surf, submit_prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 120)))

    def draw_leaderboard_overlay(self):
        """Draws the leaderboard screen."""
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        title_surf = self._render_text_safe("Leaderboard", "large_text", GOLD)
        title_bg_rect_width = title_surf.get_width() + 40
        title_bg_rect_height = title_surf.get_height() + 20
        title_bg_surf = pygame.Surface((title_bg_rect_width, title_bg_rect_height), pygame.SRCALPHA)
        title_bg_surf.fill((20,20,20,180)) # Title background
        title_bg_surf.blit(title_surf, title_surf.get_rect(center=(title_bg_rect_width//2, title_bg_rect_height//2)))
        self.screen.blit(title_bg_surf, title_bg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 300)))
        
        scores_to_display = ui_flow_ctrl.leaderboard_scores # Get scores from UIFlowController
        header_y = HEIGHT // 2 - 250 # Y position for column headers
        score_item_y_start = HEIGHT // 2 - 200 # Y position for first score item
        item_line_height = self.fonts["leaderboard_entry"].get_height() + 15 # Spacing between scores

        if not scores_to_display: # If no scores
            no_scores_surf = self._render_text_safe("No scores yet!", "medium_text", WHITE)
            no_scores_bg = pygame.Surface((no_scores_surf.get_width()+20, no_scores_surf.get_height()+10), pygame.SRCALPHA)
            no_scores_bg.fill((30,30,30,160))
            no_scores_bg.blit(no_scores_surf, no_scores_surf.get_rect(center=(no_scores_bg.get_width()//2, no_scores_bg.get_height()//2)))
            self.screen.blit(no_scores_bg, no_scores_bg.get_rect(center=(WIDTH//2, HEIGHT//2)))
        else: # Display scores
            cols_x_positions = {"Rank": WIDTH//2 - 460, "Name": WIDTH//2 - 300, "Level": WIDTH//2 + 100, "Score": WIDTH//2 + 280}
            header_font = self.fonts.get("leaderboard_header", self.fonts["ui_text"])
            entry_font = self.fonts.get("leaderboard_entry", self.fonts["ui_text"])
            
            # Draw column headers
            for col_name, x_pos in cols_x_positions.items():
                header_surf = header_font.render(col_name, True, WHITE)
                self.screen.blit(header_surf, (x_pos, header_y))
            
            # Draw each score entry
            for i, entry in enumerate(scores_to_display):
                if i >= get_game_setting("LEADERBOARD_MAX_ENTRIES"): break # Limit displayed entries
                y_pos = score_item_y_start + i * item_line_height
                texts_to_draw = [
                    (f"{i+1}.", WHITE, cols_x_positions["Rank"]), 
                    (str(entry.get('name','N/A')).upper(), CYAN, cols_x_positions["Name"]), 
                    (str(entry.get('level','-')), GREEN, cols_x_positions["Level"]), 
                    (str(entry.get('score',0)), GOLD, cols_x_positions["Score"])
                ]
                for text_str, color, x_coord in texts_to_draw:
                    text_surf = entry_font.render(text_str, True, color)
                    self.screen.blit(text_surf, (x_coord, y_pos))
        
        # Navigation instructions
        instr_text = "ESC: Main Menu | Q: Quit Game"
        instr_surf = self._render_text_safe(instr_text, "ui_text", self.INSTRUCTION_TEXT_COLOR) 
        instr_bg_box = pygame.Surface((instr_surf.get_width() + self.INSTRUCTION_PADDING_X, instr_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        instr_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        instr_bg_box.blit(instr_surf, instr_surf.get_rect(center=(instr_bg_box.get_width() // 2, instr_bg_box.get_height() // 2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))

    def draw_architect_vault_success_overlay(self):
        """Draws the overlay for successfully completing the Architect's Vault."""
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        msg_surf = self._render_text_safe(ui_flow_ctrl.architect_vault_result_message, "large_text", ui_flow_ctrl.architect_vault_result_message_color)
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 80)))
        prompt_surf = self._render_text_safe("Press ENTER or M to Continue", "ui_text", WHITE)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 100)))

    def draw_architect_vault_failure_overlay(self):
        """Draws the overlay for failing the Architect's Vault."""
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        msg_surf = self._render_text_safe(ui_flow_ctrl.architect_vault_result_message, "large_text", ui_flow_ctrl.architect_vault_result_message_color)
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
        
        # Display specific failure reason if available
        if hasattr(self.game_controller, 'architect_vault_failure_reason') and self.game_controller.architect_vault_failure_reason:
            reason_surf = self._render_text_safe(self.game_controller.architect_vault_failure_reason, "ui_text", YELLOW)
            self.screen.blit(reason_surf, reason_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))
            
        prompt_surf = self._render_text_safe("Press ENTER or M to Return to Menu", "ui_text", WHITE)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 80)))

    def draw_maze_defense_hud(self):
        """Draws the HUD specific to the Maze Defense game mode."""
        # Panel background (same as standard HUD)
        panel_y_start = GAME_PLAY_AREA_HEIGHT
        panel_height = BOTTOM_PANEL_HEIGHT
        panel_surf = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA)
        panel_surf.fill((20, 25, 35, 220)) 
        pygame.draw.line(panel_surf, (80, 120, 170, 200), (0, 0), (WIDTH, 0), 2)
        self.screen.blit(panel_surf, (0, panel_y_start))

        # Layout parameters
        h_padding = 20
        v_padding = 10
        element_spacing = 8 # Slightly more spacing for defense HUD elements
        text_icon_spacing = 3
        icon_spacing = 5

        # --- Left Side: Player Lives & Cores (if player is part of defense mode) ---
        current_hud_y = panel_y_start + panel_height - v_padding # Start from bottom of panel

        # Player Cores Display (Moved up to be drawn first on the left)
        cores_emoji_char = "💠"
        cores_value_str = str(self.drone_system.get_player_cores())
        cores_icon_surf = self._render_text_safe(cores_emoji_char, "ui_emoji_general", GOLD)
        cores_value_text_surf = self._render_text_safe(cores_value_str, "ui_values", GOLD)
        
        core_display_element_height = max(cores_icon_surf.get_height(), cores_value_text_surf.get_height())
        cores_y_pos = current_hud_y - core_display_element_height # Position at the bottom of this section
        cores_x_pos = h_padding
        
        self.screen.blit(cores_icon_surf, (cores_x_pos, cores_y_pos + (core_display_element_height - cores_icon_surf.get_height()) // 2))
        self.screen.blit(cores_value_text_surf, (cores_x_pos + cores_icon_surf.get_width() + text_icon_spacing, cores_y_pos + (core_display_element_height - cores_value_text_surf.get_height()) // 2))
        current_hud_y = cores_y_pos - element_spacing # Move Y up for next element (lives)

        # Player Lives (if applicable)
        if self.game_controller.player: # Check if player object exists for this mode
            life_icon_surf = self.ui_assets.get("current_drone_life_icon")
            if life_icon_surf:
                lives_y_pos = current_hud_y - self.ui_icon_size_lives[1]
                for i in range(self.game_controller.lives):
                    self.screen.blit(life_icon_surf, (h_padding + i * (self.ui_icon_size_lives[0] + icon_spacing), lives_y_pos))
                # current_hud_y = lives_y_pos - element_spacing # Not needed if lives are topmost on left
        
        # --- Center: Wave Info & Build Phase Prompts ---
        center_hud_x = WIDTH // 2
        combat_ctrl = self.game_controller.combat_controller
        if combat_ctrl and combat_ctrl.wave_manager:
            wave_manager = combat_ctrl.wave_manager
            wave_text_str = wave_manager.get_current_wave_display()
            wave_surf = self._render_text_safe(wave_text_str, "ui_text", CYAN)
            wave_rect = wave_surf.get_rect(centerx=center_hud_x, top=panel_y_start + v_padding)
            self.screen.blit(wave_surf, wave_rect)
            
            prompt_y_start = wave_rect.bottom + 5 # Y for prompts below wave text
            if wave_manager.is_build_phase_active:
                build_time_str = wave_manager.get_build_phase_time_remaining_display()
                build_time_surf = self._render_text_safe(build_time_str, "ui_text", YELLOW)
                build_time_rect = build_time_surf.get_rect(centerx=center_hud_x, top=prompt_y_start)
                self.screen.blit(build_time_surf, build_time_rect)
                prompt_y_start = build_time_rect.bottom + 3 # Adjust Y for next line of prompts
                
                # Prompts for placing turrets and starting wave
                turret_prompt_surf = self._render_text_safe("T: Place Turret", "small_text", GREEN)
                start_wave_prompt_surf = self._render_text_safe("SPACE: Start Wave", "small_text", GREEN)
                
                total_width_prompts = turret_prompt_surf.get_width() + start_wave_prompt_surf.get_width() + 20 # Combined width
                start_x_prompts = center_hud_x - total_width_prompts // 2 # Center the prompts block
                
                turret_prompt_rect = turret_prompt_surf.get_rect(topleft=(start_x_prompts, prompt_y_start))
                self.screen.blit(turret_prompt_surf, turret_prompt_rect)
                
                start_wave_prompt_rect = start_wave_prompt_surf.get_rect(left=turret_prompt_rect.right + 20, centery=turret_prompt_rect.centery)
                self.screen.blit(start_wave_prompt_surf, start_wave_prompt_rect)
            else: # Wave in progress
                self.screen.blit(self._render_text_safe("Wave In Progress!", "ui_text", ORANGE), 
                                 self._render_text_safe("Wave In Progress!", "ui_text", ORANGE).get_rect(centerx=center_hud_x, top=prompt_y_start))
        else: # Fallback if wave manager not ready
            self.screen.blit(self._render_text_safe("Loading Defense...", "ui_text", GREY), 
                             self._render_text_safe("Loading Defense...", "ui_text", GREY).get_rect(centerx=center_hud_x, centery=panel_y_start + panel_height // 2))
        
        # --- Top of Screen: Reactor Health Bar ---
        reactor = combat_ctrl.core_reactor if combat_ctrl else None
        if reactor and (reactor.alive or reactor.current_health > 0): # Draw if reactor exists and has health
            bar_width = WIDTH * 0.35
            bar_height_reactor = 22
            bar_x = (WIDTH - bar_width) / 2 # Center the health bar
            bar_y = 15 # Position near top of screen
            
            health_percentage = reactor.current_health / reactor.max_health if reactor.max_health > 0 else 0
            filled_width = bar_width * health_percentage
            
            pygame.draw.rect(self.screen, DARK_GREY, (bar_x, bar_y, bar_width, bar_height_reactor), border_radius=3) # Background
            
            fill_color = RED
            if health_percentage > 0.66: fill_color = GREEN
            elif health_percentage > 0.33: fill_color = YELLOW
            
            if filled_width > 0:
                pygame.draw.rect(self.screen, fill_color, (bar_x, bar_y, int(filled_width), bar_height_reactor), border_radius=3) # Filled portion
            pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, bar_width, bar_height_reactor), 2, border_radius=3) # Border
            
            # Reactor Icon and Health Text
            reactor_label_icon = self.ui_assets.get("reactor_icon_placeholder")
            if reactor_label_icon:
                self.screen.blit(reactor_label_icon, reactor_label_icon.get_rect(midright=(bar_x - 10, bar_y + bar_height_reactor // 2)))
            
            health_text_surf = self._render_text_safe(f"{int(reactor.current_health)}/{int(reactor.max_health)}", "small_text", WHITE)
            self.screen.blit(health_text_surf, health_text_surf.get_rect(midleft=(bar_x + bar_width + 10, bar_y + bar_height_reactor // 2)))
        
        # --- Right Side: Player Score ---
        score_x_anchor = WIDTH - h_padding 
        score_emoji_char = "🏆 "
        score_text_str = f"Score: {self.game_controller.score}"
        score_emoji_surf = self._render_text_safe(score_emoji_char, "ui_emoji_general", GOLD)
        score_text_surf = self._render_text_safe(score_text_str, "ui_text", GOLD)
        
        score_total_width = score_emoji_surf.get_width() + text_icon_spacing + score_text_surf.get_width()
        score_start_x = score_x_anchor - score_total_width
        score_max_height = max(score_emoji_surf.get_height(), score_text_surf.get_height())
        score_y_pos = panel_y_start + panel_height - v_padding - score_max_height # Position at bottom of this section
        
        self.screen.blit(score_emoji_surf, (score_start_x, score_y_pos + (score_max_height - score_emoji_surf.get_height()) // 2))
        self.screen.blit(score_text_surf, (score_start_x + score_emoji_surf.get_width() + text_icon_spacing, score_y_pos + (score_max_height - score_text_surf.get_height()) // 2))
