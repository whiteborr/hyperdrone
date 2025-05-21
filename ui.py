import pygame
import os
import math # For UI effects like pulsing

# Import constants directly from game_settings.py
try:
    from game_settings import (
        WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT, BOTTOM_PANEL_HEIGHT, TILE_SIZE,
        BLACK, GOLD, WHITE, GREEN, CYAN, RED, DARK_RED, GREY, YELLOW, LIGHT_BLUE, ORANGE, PURPLE,
        DARK_GREY, DARK_PURPLE, ARCHITECT_VAULT_BG_COLOR, ARCHITECT_VAULT_WALL_COLOR, ARCHITECT_VAULT_ACCENT_COLOR,
        WEAPON_MODE_ICONS, PLAYER_BULLET_COLOR, MISSILE_COLOR, LIGHTNING_COLOR, POWERUP_TYPES,
        GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
        GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME,
        GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, # Assuming bonus level still used
        GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
        GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
        GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
        DEFAULT_SETTINGS, # For checking if settings are modified
        TOTAL_CORE_FRAGMENTS_NEEDED, CORE_FRAGMENT_DETAILS, # For HUD display
        get_game_setting # To access current game settings
    )
except ImportError:
    print("Critical Error (ui.py): Could not import from game_settings.py. UI will likely fail.")
    # Add minimal fallbacks if absolutely necessary for standalone testing, but this indicates a project setup issue.
    WIDTH, HEIGHT = 1920, 1080
    GAME_PLAY_AREA_HEIGHT, BOTTOM_PANEL_HEIGHT, TILE_SIZE = 960, 120, 80
    BLACK, GOLD, WHITE, RED, CYAN, YELLOW, GREEN, LIGHT_BLUE, ORANGE, PURPLE, GREY, DARK_RED, DARK_GREY, DARK_PURPLE = [(0,0,0)]*14
    ARCHITECT_VAULT_BG_COLOR, ARCHITECT_VAULT_WALL_COLOR, ARCHITECT_VAULT_ACCENT_COLOR = [(0,0,0)]*3
    WEAPON_MODE_ICONS, POWERUP_TYPES, CORE_FRAGMENT_DETAILS = {}, {}, {}
    PLAYER_BULLET_COLOR, MISSILE_COLOR, LIGHTNING_COLOR = [(255,255,255)]*3
    GAME_STATE_MAIN_MENU = "main_menu" # etc. for all states
    DEFAULT_SETTINGS = {}
    TOTAL_CORE_FRAGMENTS_NEEDED = 3
    def get_game_setting(key): return None


# Import DRONE_DATA for drone select screen details
try:
    from drone_configs import DRONE_DATA, DRONE_DISPLAY_ORDER # DRONE_DISPLAY_ORDER might be used by GameController
except ImportError:
    print("Critical Error (ui.py): Could not import from drone_configs.py. Drone selection UI will fail.")
    DRONE_DATA = {}

# Import leaderboard module for displaying leaderboard scores
try:
    import leaderboard
except ImportError:
    print("Warning (ui.py): Could not import leaderboard.py. Leaderboard display will fail.")
    class leaderboard: # Dummy class
        @staticmethod
        def load_scores(): return []
        @staticmethod
        def is_high_score(s, l): return False


class UIManager:
    def __init__(self, screen, fonts, game_controller_ref, scene_manager_ref, drone_system_ref):
        """
        Initializes the UIManager.
        Args:
            screen: The main Pygame screen surface to draw on.
            fonts: A dictionary of pre-loaded Pygame font objects from GameController.
            game_controller_ref: Reference to the main GameController instance.
            scene_manager_ref: Reference to the SceneManager instance.
            drone_system_ref: Reference to the DroneSystem instance.
        """
        self.screen = screen
        self.fonts = fonts
        self.game_controller = game_controller_ref
        self.scene_manager = scene_manager_ref
        self.drone_system = drone_system_ref

        self.ui_assets = {
            "ring_icon": None,
            "ring_icon_empty": None,
            "menu_background": None, # Main menu background/logo
            "current_drone_life_icon": None # Cached surface for player life icon
        }
        self.ui_icon_size_lives = (30, 30) # Standard size for life icons in HUD
        self.ui_icon_size_rings = (20, 20) # Standard size for ring icons in HUD

        self._load_ui_assets()
        self.update_player_life_icon_surface() # Initial load based on currently selected drone

    def _load_ui_assets(self):
        """Loads UI-specific assets like icons and background images."""
        # Load Ring Icon
        ring_icon_path = os.path.join("assets", "images", "collectibles", "ring_ui_icon.png")
        
        # Load Menu Background
        menu_bg_path = os.path.join("assets", "images", "ui", "menu_logo_hyperdrone.png") # Main path
        

    def update_player_life_icon_surface(self):
        """
        Updates the cached surface for the player's life icon based on the currently selected drone.
        This should be called when the selected drone changes.
        """
        selected_drone_id = self.drone_system.get_selected_drone_id()
        drone_config = self.drone_system.get_drone_config(selected_drone_id) # Gets config from DRONE_DATA

        icon_path = drone_config.get("icon_path") if drone_config else None # "icon_path" from drone_configs.py

        if icon_path and os.path.exists(icon_path):
            try:
                raw_icon = pygame.image.load(icon_path).convert_alpha()
                self.ui_assets["current_drone_life_icon"] = pygame.transform.smoothscale(raw_icon, self.ui_icon_size_lives)
            except pygame.error as e:
                print(f"UIManager: Error loading life icon for {selected_drone_id} ('{icon_path}'): {e}. Using fallback.")
                self.ui_assets["current_drone_life_icon"] = self._create_fallback_icon_surface(
                    size=self.ui_icon_size_lives, text="♥", color=CYAN, font_key="ui_emoji_small"
                )
        else:
            if icon_path: print(f"UIManager: Warning - Life icon path not found: {icon_path}")
            self.ui_assets["current_drone_life_icon"] = self._create_fallback_icon_surface(
                size=self.ui_icon_size_lives, text="♥", color=CYAN, font_key="ui_emoji_small" # Emoji as fallback
            )

    def _create_fallback_icon_surface(self, size=(30,30), text="?", color=GREY, text_color=WHITE, font_key="ui_text"):
        """Creates a fallback surface (e.g., a colored box with text) for an icon if its image fails to load."""
        surface = pygame.Surface(size, pygame.SRCALPHA) # Use SRCALPHA for transparency
        surface.fill(color)
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 1) # Thin white border

        font_to_use = self.fonts.get(font_key, pygame.font.Font(None, max(10, size[1]-4))) # Default to system font
        if text and font_to_use:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2))
                surface.blit(text_surf, text_rect)
            except Exception as e: # Catch any font rendering errors
                print(f"UIManager: Error rendering fallback icon text '{text}' with font '{font_key}': {e}")
        return surface

    def _render_text_safe(self, text, font_key, color, fallback_size=24):
        """Safely renders text using a specified font key, with a fallback to system font."""
        font = self.fonts.get(font_key)
        if not font: # If the font key wasn't found in preloaded fonts
            # print(f"UIManager: Font key '{font_key}' not found. Using system font size {fallback_size}.")
            font = pygame.font.Font(None, fallback_size) # Pygame's default font
        try:
            return font.render(str(text), True, color) # Ensure text is string
        except Exception as e:
            print(f"UIManager: Error rendering text '{text}' with font '{font_key}': {e}")
            # Fallback to rendering "ERR" in red with system font
            error_font = pygame.font.Font(None, fallback_size)
            return error_font.render("ERR", True, RED)

    def draw_current_scene_ui(self):
        """Main dispatcher that draws UI elements based on the current game scene."""
        current_state = self.scene_manager.get_current_state()

        # Common background for menu-like states (can be overridden by specific menu draw methods)
        is_menu_like_state = current_state in [
            GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT,
            GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD,
            GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
            GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME
        ]

        if is_menu_like_state:
            self.screen.fill(BLACK) # Default dark background for menus
            if hasattr(self.game_controller, 'menu_stars') and self.game_controller.menu_stars:
                 for star_params in self.game_controller.menu_stars: # x, y, speed, size
                    pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

        # Dispatch to specific UI drawing methods
        if current_state == GAME_STATE_MAIN_MENU:
            self.draw_main_menu()
        elif current_state == GAME_STATE_DRONE_SELECT:
            self.draw_drone_select_menu()
        elif current_state == GAME_STATE_SETTINGS:
            self.draw_settings_menu()
        elif current_state == GAME_STATE_LEADERBOARD:
            self.draw_leaderboard_overlay()
        elif current_state == GAME_STATE_GAME_OVER:
            self.draw_game_over_overlay()
        elif current_state == GAME_STATE_ENTER_NAME:
            self.draw_enter_name_overlay()
        elif current_state.startswith("architect_vault"): # Covers all architect vault states
            self.draw_architect_vault_hud_elements() # Draws vault-specific HUD (can call draw_gameplay_hud)
            if self.game_controller.paused: self.draw_pause_overlay() # Pause overlay for vault
            # Specific full-screen overlays for vault success/failure
            if current_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS:
                self.draw_architect_vault_success_overlay()
            elif current_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
                self.draw_architect_vault_failure_overlay()
        elif current_state == GAME_STATE_PLAYING or current_state == GAME_STATE_BONUS_LEVEL_PLAYING:
            self.draw_gameplay_hud() # Standard gameplay HUD
            if self.game_controller.paused: self.draw_pause_overlay() # Pause overlay for gameplay

    def draw_main_menu(self):
        """Draws the main menu UI."""
        # Use a background image if available, otherwise a fill
        if self.ui_assets["menu_background"]:
            try:
                # Scale background to fit screen dimensions (WIDTH, HEIGHT from game_settings)
                scaled_bg = pygame.transform.smoothscale(self.ui_assets["menu_background"], (WIDTH, HEIGHT))
                self.screen.blit(scaled_bg, (0,0))
            except Exception as e:
                print(f"UIManager: Error blitting menu background: {e}")
                self.screen.fill(BLACK) # Fallback fill
        else:
            # self.screen.fill(BLACK) # Already filled by draw_current_scene_ui if menu-like
            pass


        # Get menu options and selection state from GameController
        menu_options = getattr(self.game_controller, 'menu_options', ["Start", "Quit"])
        selected_option_idx = getattr(self.game_controller, 'selected_menu_option', 0)

        menu_item_start_y = HEIGHT // 2 - 80 # Adjust starting position
        item_spacing = 75 # Space between menu items
        base_font_size = self.fonts["menu_text"].get_height() # Assuming "menu_text" font is loaded

        for i, option_text in enumerate(menu_options):
            is_selected = (i == selected_option_idx)
            text_color = GOLD if is_selected else WHITE

            active_menu_font = self.fonts["menu_text"]
            if is_selected: # Make selected item slightly larger or different font style
                 try:
                     # GameController should have font_path_neuropol if this is used
                     font_path = getattr(self.game_controller, 'font_path_neuropol', None)
                     active_menu_font = pygame.font.Font(font_path, base_font_size + 8)
                 except Exception: # Fallback if custom font fails
                     active_menu_font = pygame.font.Font(None, base_font_size + 8)

            text_surf = active_menu_font.render(option_text, True, text_color)
            if hasattr(text_surf, 'get_rect'):
                text_rect = text_surf.get_rect()
                # Create a button-like background for each menu item
                button_width = text_rect.width + 60
                button_height = text_rect.height + 25
                button_surface_rect = pygame.Rect(0,0,button_width, button_height)
                button_surface_rect.center = (WIDTH // 2, menu_item_start_y + i * item_spacing)

                # Draw button background with rounded corners
                button_bg_surface = pygame.Surface(button_surface_rect.size, pygame.SRCALPHA)
                current_bg_color = (70,70,70,220) if is_selected else (50,50,50,180) # Alpha for transparency
                pygame.draw.rect(button_bg_surface, current_bg_color, button_bg_surface.get_rect(), border_radius=15)
                if is_selected: # Highlight selected button with a border
                    pygame.draw.rect(button_bg_surface, GOLD, button_bg_surface.get_rect(), 3, border_radius=15)

                # Blit text onto the button background
                button_bg_surface.blit(text_surf, text_surf.get_rect(center=(button_width//2, button_height//2)))
                self.screen.blit(button_bg_surface, button_surface_rect.topleft)

        # Instructions text
        instr_surf = self._render_text_safe("Use UP/DOWN keys, ENTER to select.", "small_text", CYAN)
        instr_bg_box=pygame.Surface((instr_surf.get_width()+20,instr_surf.get_height()+10),pygame.SRCALPHA)
        instr_bg_box.fill((30,30,30,150)) # Semi-transparent background for instructions
        instr_bg_box.blit(instr_surf,instr_surf.get_rect(center=(instr_bg_box.get_width()//2,instr_bg_box.get_height()//2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH//2, HEIGHT-100)))

        # Warning if settings are modified (disables leaderboard)
        if get_game_setting("SETTINGS_MODIFIED"): # Use get_game_setting from game_settings
            warning_surf = self._render_text_safe("Custom settings active: Leaderboard disabled.", "small_text", YELLOW)
            self.screen.blit(warning_surf, warning_surf.get_rect(center=(WIDTH//2, HEIGHT-50)))


    def draw_drone_select_menu(self):
        """Draws the drone selection menu UI."""
        # Screen fill and stars are handled by draw_current_scene_ui

        title_surf = self._render_text_safe("Select Drone", "title_text", GOLD)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 70))
        self.screen.blit(title_surf, title_rect)

        # Get drone options and selection state from GameController/DroneSystem
        drone_options_ids = getattr(self.game_controller, 'drone_select_options', []) # Should be DRONE_DISPLAY_ORDER
        selected_preview_idx = getattr(self.game_controller, 'selected_drone_preview_index', 0)

        if not drone_options_ids:
            no_drones_surf = self._render_text_safe("NO DRONES AVAILABLE", "large_text", RED)
            self.screen.blit(no_drones_surf, no_drones_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            return

        current_drone_id = drone_options_ids[selected_preview_idx]
        drone_config = self.drone_system.get_drone_config(current_drone_id) # From DRONE_DATA
        # Get effective stats (could be modified by game mode, e.g., vault)
        # Assuming drone_system.get_drone_stats takes is_in_architect_vault argument
        drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False) # False for menu
        is_unlocked = self.drone_system.is_drone_unlocked(current_drone_id)
        is_currently_equipped = (current_drone_id == self.drone_system.get_selected_drone_id())

        # Drone Image Display (from GameController's cache)
        drone_image_surf = None
        if hasattr(self.game_controller, 'drone_main_display_cache'):
            drone_image_surf = self.game_controller.drone_main_display_cache.get(current_drone_id)
        
        img_width = drone_image_surf.get_width() if drone_image_surf else 200
        img_height = drone_image_surf.get_height() if drone_image_surf else 200

        # Drone Name
        name_text = drone_config.get("name", "N/A")
        name_surf_temp = self.fonts["drone_name_cycle"].render(name_text, True, WHITE) # Font for name
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
        
        fire_rate_text = f"{1/fire_rate_mult:.1f}x" if fire_rate_mult != 0 else "N/A"
        if fire_rate_mult == 1.0: fire_rate_text += " (Normal)"
        elif fire_rate_mult < 1.0: fire_rate_text += " (Faster)" # Multiplier < 1 means faster
        else: fire_rate_text += " (Slower)"

        special_ability_name = "None" # Default
        if special_ability_key == "phantom_cloak": special_ability_name = "Phantom Cloak"
        elif special_ability_key == "omega_boost": special_ability_name = "Omega Boost"
        # Add more special ability names here

        stats_data_tuples = [
            ("HP:", hp_display), ("Speed:", speed_display), ("Turn Speed:", turn_speed_display),
            ("Fire Rate:", fire_rate_text), ("Special:", special_ability_name)
        ]
        stats_content_surfaces = []
        max_stat_label_w = 0
        max_stat_value_w = 0
        stat_line_h = self.fonts["drone_stats_label_cycle"].get_height() + 5 # Font for stat labels

        for label_str, value_str in stats_data_tuples:
            label_s = self._render_text_safe(label_str, "drone_stats_label_cycle", LIGHT_BLUE if is_unlocked else GREY)
            value_s = self._render_text_safe(value_str, "drone_stats_value_cycle", WHITE if is_unlocked else GREY) # Font for stat values
            stats_content_surfaces.append((label_s, value_s))
            max_stat_label_w = max(max_stat_label_w, label_s.get_width())
            max_stat_value_w = max(max_stat_value_w, value_s.get_width())

        stats_box_padding = 15
        stats_box_visual_width = max_stat_label_w + max_stat_value_w + 3 * stats_box_padding
        stats_box_visual_height = (len(stats_content_surfaces) * stat_line_h) - (5 if stats_content_surfaces else 0) + 2 * stats_box_padding

        # Drone Description
        desc_text = drone_config.get("description", "")
        desc_color_final = (200,200,200) if is_unlocked else (100,100,100)
        desc_max_width_for_card = WIDTH * 0.45 # Max width for description text
        desc_lines_surfs = []
        words = desc_text.split(' ')
        current_line_text_desc = ""
        desc_font = self.fonts["drone_desc_cycle"] # Font for description
        for word in words:
            test_line = current_line_text_desc + word + " "
            if desc_font.size(test_line)[0] < desc_max_width_for_card:
                current_line_text_desc = test_line
            else:
                desc_lines_surfs.append(self._render_text_safe(current_line_text_desc.strip(), "drone_desc_cycle", desc_color_final))
                current_line_text_desc = word + " "
        if current_line_text_desc: # Add any remaining part of the description
            desc_lines_surfs.append(self._render_text_safe(current_line_text_desc.strip(), "drone_desc_cycle", desc_color_final))
        total_desc_height = sum(s.get_height() for s in desc_lines_surfs) + (len(desc_lines_surfs)-1)*3 if desc_lines_surfs else 0

        # Unlock/Select Info
        unlock_text_str = ""
        unlock_text_color = WHITE
        unlock_condition = drone_config.get("unlock_condition", {})
        if not is_unlocked:
            condition_text_str = unlock_condition.get("description", "Locked")
            unlock_cost_val = unlock_condition.get("value")
            type_is_cores_unlock = unlock_condition.get("type") == "cores"
            unlock_text_str = condition_text_str
            if type_is_cores_unlock and unlock_cost_val is not None and self.drone_system.get_player_cores() >= unlock_cost_val:
                unlock_text_str += f" (ENTER to Unlock: {unlock_cost_val} 💠)" # Use core emoji
                unlock_text_color = GREEN # Can afford
            else:
                unlock_text_color = YELLOW # Cannot afford or other condition
        elif is_currently_equipped:
            unlock_text_str = "EQUIPPED"
            unlock_text_color = GREEN
        else: # Unlocked but not equipped
            unlock_text_str = "Press ENTER to Select"
            unlock_text_color = CYAN

        unlock_info_surf = self._render_text_safe(unlock_text_str, "drone_unlock_cycle", unlock_text_color) # Font for unlock info
        unlock_info_height = unlock_info_surf.get_height() if unlock_info_surf else 0

        # Main Card Layout
        spacing_between_elements = 15
        padding_inside_card = 25
        card_content_total_h = (img_height + spacing_between_elements + name_height + spacing_between_elements +
                                stats_box_visual_height + spacing_between_elements + total_desc_height +
                                spacing_between_elements + unlock_info_height)
        max_content_width_for_card = max(img_width, name_surf_temp.get_width(), stats_box_visual_width,
                                         max(s.get_width() for s in desc_lines_surfs) if desc_lines_surfs else 0,
                                         unlock_info_surf.get_width() if unlock_info_surf else 0)
        card_w = max_content_width_for_card + 2 * padding_inside_card
        card_w = min(card_w, WIDTH * 0.6) # Max card width
        card_h = card_content_total_h + 2 * padding_inside_card + 20 # Extra padding at bottom

        title_bottom = title_rect.bottom if title_rect else 100
        main_card_x = (WIDTH - card_w) // 2 # Center the card
        main_card_y = title_bottom + 40
        main_card_rect = pygame.Rect(main_card_x, main_card_y, card_w, card_h)

        # Draw Card Background
        pygame.draw.rect(self.screen, (25,30,40,230), main_card_rect, border_radius=20) # Dark semi-transparent BG
        pygame.draw.rect(self.screen, GOLD, main_card_rect, 3, border_radius=20) # Gold border

        # Draw Content Inside Card
        current_y_in_card = main_card_rect.top + padding_inside_card

        # Drone Image
        if drone_image_surf:
            display_drone_image = drone_image_surf
            if not is_unlocked: # Dim if locked
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
        final_stats_box_draw_rect = pygame.Rect(main_card_rect.centerx - stats_box_visual_width // 2, current_y_in_card,
                                                stats_box_visual_width, stats_box_visual_height)
        pygame.draw.rect(self.screen, (40,45,55,200), final_stats_box_draw_rect, border_radius=10) # Stats box BG
        pygame.draw.rect(self.screen, CYAN, final_stats_box_draw_rect, 1, border_radius=10) # Stats box border
        stat_y_pos_render = final_stats_box_draw_rect.top + stats_box_padding
        for i, (label_s, value_s) in enumerate(stats_content_surfaces):
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

        # Unlock/Select Info Text
        if unlock_info_surf:
            unlock_info_rect = unlock_info_surf.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(unlock_info_surf, unlock_info_rect)

        # Navigation Arrows (Left/Right)
        arrow_font = self.fonts.get("arrow_font_key", self.fonts["large_text"]) # Large arrow font
        left_arrow_surf = arrow_font.render("◀", True, WHITE if len(drone_options_ids) > 1 else GREY)
        right_arrow_surf = arrow_font.render("▶", True, WHITE if len(drone_options_ids) > 1 else GREY)
        arrow_y_center = main_card_rect.centery
        arrow_padding_from_card_edge = 40
        if len(drone_options_ids) > 1: # Only show arrows if there's more than one drone
            left_arrow_rect = left_arrow_surf.get_rect(centery=arrow_y_center, right=main_card_rect.left - arrow_padding_from_card_edge)
            self.screen.blit(left_arrow_surf, left_arrow_rect)
            right_arrow_rect = right_arrow_surf.get_rect(centery=arrow_y_center, left=main_card_rect.right + arrow_padding_from_card_edge)
            self.screen.blit(right_arrow_surf, right_arrow_rect)

        # Instructions Text at Bottom
        instr_surf = self._render_text_safe("LEFT/RIGHT: Cycle | ENTER: Select/Unlock | ESC: Back", "small_text", CYAN)
        instr_bg_rect = pygame.Rect(0, HEIGHT - 70, WIDTH, 30) # Position for instructions
        instr_surf_rect = instr_surf.get_rect(center=instr_bg_rect.center)
        self.screen.blit(instr_surf, instr_surf_rect)

        # Player Cores Display
        cores_label_text_surf = self._render_text_safe(f"Player Cores: ", "ui_text", GOLD)
        cores_value_text_surf = self._render_text_safe(f"{self.drone_system.get_player_cores()}", "ui_values", GOLD)
        cores_emoji_surf = self._render_text_safe(" 💠", "ui_emoji_general", GOLD) # Core emoji
        total_cores_display_width = cores_label_text_surf.get_width() + cores_value_text_surf.get_width() + cores_emoji_surf.get_width()
        cores_start_x = WIDTH - 20 - total_cores_display_width # Align to right
        max_element_height_cores = max(cores_label_text_surf.get_height(), cores_value_text_surf.get_height(), cores_emoji_surf.get_height())
        cores_y_baseline = HEIGHT - 20 - max_element_height_cores # Position near bottom right
        
        current_x_offset_cores = cores_start_x
        self.screen.blit(cores_label_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_label_text_surf.get_height()) // 2))
        current_x_offset_cores += cores_label_text_surf.get_width()
        self.screen.blit(cores_value_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_value_text_surf.get_height()) // 2))
        current_x_offset_cores += cores_value_text_surf.get_width()
        self.screen.blit(cores_emoji_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_emoji_surf.get_height()) // 2))


    def draw_settings_menu(self):
        """Draws the settings menu UI."""
        # Screen fill and stars handled by draw_current_scene_ui
        title_surf = self._render_text_safe("Settings", "title_text", GOLD)
        title_bg = pygame.Surface((title_surf.get_width()+30, title_surf.get_height()+15), pygame.SRCALPHA)
        title_bg.fill((20,20,20,180)) # Semi-transparent background for title
        title_bg.blit(title_surf, title_surf.get_rect(center=(title_bg.get_width()//2, title_bg.get_height()//2)))
        self.screen.blit(title_bg, title_bg.get_rect(center=(WIDTH//2, 80))) # Position title

        # Get settings items and selection state from GameController
        settings_items = getattr(self.game_controller, 'settings_items_data', [])
        selected_idx = getattr(self.game_controller, 'selected_setting_index', 0)

        item_y_start = 180 # Y position for the first setting item
        item_line_height = self.fonts["ui_text"].get_height() + 20 # Increased spacing
        max_items_on_screen = (HEIGHT - item_y_start - 120) // item_line_height # Calculate visible items

        view_start_index = 0 # For scrolling if many settings
        if len(settings_items) > max_items_on_screen:
            view_start_index = max(0, selected_idx - max_items_on_screen // 2)
            view_start_index = min(view_start_index, len(settings_items) - max_items_on_screen)
        view_end_index = min(view_start_index + max_items_on_screen, len(settings_items))

        for i_display, list_idx in enumerate(range(view_start_index, view_end_index)):
            if list_idx >= len(settings_items): continue
            item = settings_items[list_idx]
            y_pos = item_y_start + i_display * item_line_height
            color = YELLOW if list_idx == selected_idx else WHITE # Highlight selected item

            # Setting Label
            label_surf = self._render_text_safe(item["label"], "ui_text", color)
            label_bg_rect_width = max(250, label_surf.get_width() + 20) # Min width for label BG
            label_bg_rect = pygame.Rect(WIDTH // 4 - 150, y_pos - 5, label_bg_rect_width, label_surf.get_height() + 10)
            pygame.draw.rect(self.screen, (30,30,30,160), label_bg_rect, border_radius=5) # BG for label
            self.screen.blit(label_surf, (label_bg_rect.left + 10, y_pos))

            # Setting Note (if selected)
            if "note" in item and list_idx == selected_idx:
                note_surf = self._render_text_safe(item["note"], "small_text", LIGHT_BLUE)
                self.screen.blit(note_surf, note_surf.get_rect(left=label_bg_rect.right + 15, centery=label_bg_rect.centery))

            # Setting Value or Action Hint
            if item["type"] != "action":
                current_value = get_game_setting(item["key"]) # Use get_game_setting
                display_value = ""
                # Format numeric values (e.g., time in seconds, floats)
                if item["type"] == "numeric":
                    display_format = item.get("display_format", "{}") # Default format
                    value_to_format = current_value
                    if item.get("is_ms_to_sec"): # Convert ms to seconds for display
                        value_to_format = current_value / 1000
                    try:
                        display_value = display_format.format(value_to_format)
                    except (ValueError, TypeError): # Fallback if format string or value is incompatible
                        display_value = str(value_to_format) if not item.get("is_ms_to_sec") else f"{value_to_format:.0f}s"

                elif item["type"] == "choice": # For settings with predefined choices
                    display_value = item["get_display"](current_value) # Uses a lambda from settings_items_data

                value_surf = self._render_text_safe(display_value, "ui_text", color)
                value_bg_rect_width = max(100, value_surf.get_width() + 20) # Min width for value BG
                value_bg_rect = pygame.Rect(WIDTH // 2 + 150, y_pos - 5, value_bg_rect_width, value_surf.get_height() + 10)
                pygame.draw.rect(self.screen, (30,30,30,160), value_bg_rect, border_radius=5) # BG for value
                self.screen.blit(value_surf, (value_bg_rect.left + 10, y_pos))

                # Indicate if setting is modified from default
                if item["key"] in DEFAULT_SETTINGS and current_value != DEFAULT_SETTINGS[item["key"]]:
                    self.screen.blit(self._render_text_safe("*", "small_text", RED), (value_bg_rect.right + 5, y_pos))
            elif list_idx == selected_idx: # Hint for "action" type settings (e.g., Reset)
                 action_hint_surf = self._render_text_safe("<ENTER>", "ui_text", YELLOW)
                 action_hint_bg_rect = pygame.Rect(WIDTH // 2 + 150, y_pos - 5, action_hint_surf.get_width() + 20, action_hint_surf.get_height() + 10)
                 pygame.draw.rect(self.screen, (40,40,40,180), action_hint_bg_rect, border_radius=5) # BG for action hint
                 self.screen.blit(action_hint_surf, (action_hint_bg_rect.left + 10, y_pos))

        # Instructions at bottom
        instr_surf = self._render_text_safe("UP/DOWN: Select | LEFT/RIGHT: Adjust | ENTER: Activate | ESC: Back", "small_text", CYAN)
        instr_bg = pygame.Surface((instr_surf.get_width()+20, instr_surf.get_height()+10), pygame.SRCALPHA)
        instr_bg.fill((20,20,20,180))
        instr_bg.blit(instr_surf, (10,5))
        self.screen.blit(instr_bg, instr_bg.get_rect(center=(WIDTH//2, HEIGHT-70)))

        if get_game_setting("SETTINGS_MODIFIED"): # Warning if settings modified
            warning_surf = self._render_text_safe("Settings changed. Leaderboard will be disabled.", "small_text", YELLOW)
            warning_bg = pygame.Surface((warning_surf.get_width()+10, warning_surf.get_height()+5), pygame.SRCALPHA)
            warning_bg.fill((20,20,20,180))
            warning_bg.blit(warning_surf, (5,2))
            self.screen.blit(warning_bg, warning_bg.get_rect(center=(WIDTH//2, HEIGHT-35)))


    def draw_gameplay_hud(self):
        """Draws the Heads-Up Display during gameplay."""
        if not self.game_controller.player: return # No HUD if no player

        panel_y_start = GAME_PLAY_AREA_HEIGHT
        panel_height = BOTTOM_PANEL_HEIGHT
        # Draw HUD panel background
        panel_surf = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA)
        panel_surf.fill((20,25,35,220)) # Dark semi-transparent background for HUD
        pygame.draw.line(panel_surf, (80,120,170,200), (0,0), (WIDTH,0), 2) # Top border line for HUD
        self.screen.blit(panel_surf, (0, panel_y_start))

        # HUD layout parameters
        h_padding = 20; v_padding = 10; element_spacing = 6; bar_height = 18;
        icon_to_bar_gap = 10; icon_spacing = 5; text_icon_spacing = 4
        current_time_ticks = pygame.time.get_ticks() # For animations or timed elements

        # Fonts for HUD elements
        label_font = self.fonts["ui_text"]
        value_font = self.fonts["ui_values"]
        emoji_general_font = self.fonts["ui_emoji_general"]
        # emoji_small_font = self.fonts["ui_emoji_small"] # Already used for life icon fallback

        # --- Vitals Section (Left Side) ---
        vitals_x_start = h_padding
        current_vitals_y = panel_y_start + panel_height - v_padding # Align from bottom of panel
        vitals_section_width = int(WIDTH / 3.2) # Max width for this section
        min_bar_segment_width = 25 # Min width for health/weapon bars
        bar_segment_reduction_factor = 0.85 # How much of vitals_section_width the bar takes

        # Player Lives Display
        life_icon_surf = self.ui_assets.get("current_drone_life_icon") # Cached drone life icon
        if life_icon_surf:
            # Align lives icons from the bottom up
            lives_y_pos = current_vitals_y - self.ui_icon_size_lives[1]
            lives_draw_x = vitals_x_start # Start drawing lives from left
            for i in range(self.game_controller.lives):
                self.screen.blit(life_icon_surf, (lives_draw_x + i * (self.ui_icon_size_lives[0] + icon_spacing), lives_y_pos))
            current_vitals_y = lives_y_pos - element_spacing # Move Y-pos up for next element

        # Player Health Bar
        player_obj = self.game_controller.player # Convenience reference
        health_bar_y_pos = current_vitals_y - bar_height
        health_icon_char = "❤️" # Standard health emoji
        health_icon_surf = self._render_text_safe(health_icon_char, "ui_emoji_small", RED)
        self.screen.blit(health_icon_surf, (vitals_x_start, health_bar_y_pos + (bar_height - health_icon_surf.get_height()) // 2))
        
        bar_start_x_health = vitals_x_start + health_icon_surf.get_width() + icon_to_bar_gap
        available_width_for_health_bar = vitals_section_width - (health_icon_surf.get_width() + icon_to_bar_gap)
        bar_segment_width_health = max(min_bar_segment_width, int(available_width_for_health_bar * bar_segment_reduction_factor))
        
        health_percentage = player_obj.health / player_obj.max_health if player_obj.max_health > 0 else 0
        health_bar_width_fill = int(bar_segment_width_health * health_percentage)
        health_fill_color = GREEN if health_percentage > 0.6 else YELLOW if health_percentage > 0.3 else RED
        
        pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_health, health_bar_y_pos, bar_segment_width_health, bar_height)) # Bar BG
        if health_bar_width_fill > 0:
            pygame.draw.rect(self.screen, health_fill_color, (bar_start_x_health, health_bar_y_pos, health_bar_width_fill, bar_height)) # Filled part
        pygame.draw.rect(self.screen, WHITE, (bar_start_x_health, health_bar_y_pos, bar_segment_width_health, bar_height), 1) # Border
        current_vitals_y = health_bar_y_pos - element_spacing

        # Weapon Charge Bar
        weapon_bar_y_pos = current_vitals_y - bar_height
        weapon_icon_char = WEAPON_MODE_ICONS.get(player_obj.current_weapon_mode, "💥") # Get icon from settings
        weapon_icon_surf = self._render_text_safe(weapon_icon_char, "ui_emoji_small", ORANGE)
        self.screen.blit(weapon_icon_surf, (vitals_x_start, weapon_bar_y_pos + (bar_height - weapon_icon_surf.get_height()) // 2))

        bar_start_x_weapon = vitals_x_start + weapon_icon_surf.get_width() + icon_to_bar_gap
        bar_segment_width_weapon = max(min_bar_segment_width, int((vitals_section_width - (weapon_icon_surf.get_width() + icon_to_bar_gap)) * bar_segment_reduction_factor))
        
        charge_fill_pct = 0.0
        weapon_ready_color = PLAYER_BULLET_COLOR # Default
        cooldown_duration = player_obj.current_shoot_cooldown
        time_since_last_shot = current_time_ticks - player_obj.last_shot_time

        # Adjust for special weapons like missiles or lightning
        if player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER") or \
           player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS"):
            weapon_ready_color = MISSILE_COLOR
            time_since_last_shot = current_time_ticks - player_obj.last_missile_shot_time
            cooldown_duration = player_obj.current_missile_cooldown
        elif player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_LIGHTNING"):
            weapon_ready_color = LIGHTNING_COLOR
            time_since_last_shot = current_time_ticks - player_obj.last_lightning_time
            cooldown_duration = player_obj.current_lightning_cooldown

        if cooldown_duration > 0:
            charge_fill_pct = min(1.0, time_since_last_shot / cooldown_duration)
        else: # No cooldown (or error), assume ready
            charge_fill_pct = 1.0
        
        charge_bar_fill_color = weapon_ready_color if charge_fill_pct >= 1.0 else ORANGE # Orange while charging
        weapon_bar_width_fill = int(bar_segment_width_weapon * charge_fill_pct)
        
        pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_weapon, weapon_bar_y_pos, bar_segment_width_weapon, bar_height))
        if weapon_bar_width_fill > 0:
            pygame.draw.rect(self.screen, charge_bar_fill_color, (bar_start_x_weapon, weapon_bar_y_pos, weapon_bar_width_fill, bar_height))
        pygame.draw.rect(self.screen, WHITE, (bar_start_x_weapon, weapon_bar_y_pos, bar_segment_width_weapon, bar_height), 1)
        current_vitals_y = weapon_bar_y_pos - element_spacing

        # Active Power-up Bar (Shield or Speed Boost)
        active_powerup_for_ui = player_obj.active_powerup_type # Player tracks this
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
                powerup_icon_char = "💨" # Speed emoji
                powerup_bar_fill_color = powerup_details_config.get("color", GREEN)
                remaining_time = player_obj.speed_boost_end_time - current_time_ticks
                if player_obj.speed_boost_duration > 0 and remaining_time > 0:
                    powerup_fill_percentage = remaining_time / player_obj.speed_boost_duration
            
            powerup_fill_percentage = max(0, min(1, powerup_fill_percentage)) # Clamp between 0 and 1
            if powerup_icon_char: # Only draw if there's an active, recognized power-up
                powerup_icon_surf = self._render_text_safe(powerup_icon_char, "ui_emoji_small", WHITE)
                self.screen.blit(powerup_icon_surf, (vitals_x_start, powerup_bar_y_pos + (bar_height - powerup_icon_surf.get_height()) // 2))
                
                bar_start_x_powerup = vitals_x_start + powerup_icon_surf.get_width() + icon_to_bar_gap
                bar_segment_width_powerup = max(min_bar_segment_width, int((vitals_section_width - (powerup_icon_surf.get_width() + icon_to_bar_gap)) * bar_segment_reduction_factor))
                bar_width_fill_powerup = int(bar_segment_width_powerup * powerup_fill_percentage)

                pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_powerup, powerup_bar_y_pos, bar_segment_width_powerup, bar_height))
                if bar_width_fill_powerup > 0:
                    pygame.draw.rect(self.screen, powerup_bar_fill_color, (bar_start_x_powerup, powerup_bar_y_pos, bar_width_fill_powerup, bar_height))
                pygame.draw.rect(self.screen, WHITE, (bar_start_x_powerup, powerup_bar_y_pos, bar_segment_width_powerup, bar_height), 1)
        # current_vitals_y = powerup_bar_y_pos - element_spacing # No further elements in this stack

        # --- Collectibles Section (Right Side) ---
        collectibles_x_anchor = WIDTH - h_padding # Anchor to the right edge
        current_collectibles_y = panel_y_start + panel_height - v_padding # Align from bottom of panel

        # Player Cores Display
        cores_emoji_char = "💠"
        cores_value_str = f" {self.drone_system.get_player_cores()}"
        cores_icon_surf = self._render_text_safe(cores_emoji_char, "ui_emoji_general", GOLD)
        cores_value_text_surf = self._render_text_safe(cores_value_str, "ui_values", GOLD)
        cores_display_height = max(cores_icon_surf.get_height(), cores_value_text_surf.get_height())
        cores_y_pos = current_collectibles_y - cores_display_height
        
        total_cores_width = cores_icon_surf.get_width() + text_icon_spacing + cores_value_text_surf.get_width()
        cores_start_x_draw = collectibles_x_anchor - total_cores_width # Align from right
        
        self.screen.blit(cores_icon_surf, (cores_start_x_draw, cores_y_pos + (cores_display_height - cores_icon_surf.get_height()) // 2))
        self.screen.blit(cores_value_text_surf, (cores_start_x_draw + cores_icon_surf.get_width() + text_icon_spacing, cores_y_pos + (cores_display_height - cores_value_text_surf.get_height()) // 2))
        current_collectibles_y = cores_y_pos - element_spacing # Move Y-pos up for next element

        # Collected Rings Display
        rings_y_pos_hud = current_collectibles_y # Temp var for clarity
        
        # Get ring counts from GameController, these should always be defined
        total_rings_this_level = getattr(self.game_controller, 'total_rings_per_level', 5)
        displayed_rings_count = getattr(self.game_controller, 'displayed_collected_rings', 0)

        if self.ui_assets["ring_icon"]: # Check if ring icon asset is loaded
            ring_icon_h = self.ui_icon_size_rings[1]
            rings_y_pos_hud = current_collectibles_y - ring_icon_h # Y position for the row of rings
            
            total_ring_icons_width_only = max(0, total_rings_this_level * (self.ui_icon_size_rings[0] + icon_spacing) - icon_spacing if total_rings_this_level > 0 else 0)
            rings_block_start_x = collectibles_x_anchor - total_ring_icons_width_only # Align from right
            
            for i in range(total_rings_this_level):
                icon_to_draw = self.ui_assets["ring_icon"] if i < displayed_rings_count else self.ui_assets["ring_icon_empty"]
                if icon_to_draw:
                    self.screen.blit(icon_to_draw, (rings_block_start_x + i * (self.ui_icon_size_rings[0] + icon_spacing), rings_y_pos_hud))
            current_collectibles_y = rings_y_pos_hud - element_spacing
        
        # Core Fragments Display (if applicable to current game mode)
        num_fragments_collected = len(self.drone_system.get_collected_fragments_ids())
        if TOTAL_CORE_FRAGMENTS_NEEDED > 0: # Only show if fragments are part of the game
            frag_text_str = f"Fragments: {num_fragments_collected}/{TOTAL_CORE_FRAGMENTS_NEEDED}"
            frag_color = PURPLE if num_fragments_collected < TOTAL_CORE_FRAGMENTS_NEEDED else GOLD # Gold if all collected
            frag_surf = self._render_text_safe(frag_text_str, "ui_text", frag_color)
            frag_y_pos = current_collectibles_y - frag_surf.get_height()
            frag_x_pos = collectibles_x_anchor - frag_surf.get_width() # Align from right
            self.screen.blit(frag_surf, (frag_x_pos, frag_y_pos))
            # current_collectibles_y = frag_y_pos - element_spacing # No further elements in this stack

        # --- Center Info (Score, Level, Timer) ---
        info_y_pos = panel_y_start + (panel_height - label_font.get_height()) // 2 # Vertically center in panel

        # Score
        score_emoji_char = "🏆 "
        score_text_str = f"Score: {self.game_controller.score}"
        score_emoji_surf = self._render_text_safe(score_emoji_char, "ui_emoji_general", GOLD)
        score_text_surf = self._render_text_safe(score_text_str, "ui_text", GOLD)

        # Level
        level_emoji_char = "🎯 "
        level_text_str = f"Level: {self.game_controller.level}"
        current_scene_state = self.scene_manager.get_current_state()
        if current_scene_state == GAME_STATE_BONUS_LEVEL_PLAYING: level_text_str = "Bonus!"
        elif current_scene_state.startswith("architect_vault"): level_text_str = "Architect's Vault"
        level_emoji_surf = self._render_text_safe(level_emoji_char, "ui_emoji_general", CYAN)
        level_text_surf = self._render_text_safe(level_text_str, "ui_text", CYAN)

        # Timer
        time_icon_char = "⏱ "
        time_ms_to_display = self.game_controller.level_time_remaining_ms
        # Bonus level might have its own timer logic in GameController
        if current_scene_state == GAME_STATE_BONUS_LEVEL_PLAYING:
            elapsed_bonus_time_ms = current_time_ticks - getattr(self.game_controller, 'bonus_level_timer_start', current_time_ticks)
            bonus_duration_ms = getattr(self.game_controller, 'bonus_level_duration_ms', 60000)
            time_ms_to_display = max(0, bonus_duration_ms - elapsed_bonus_time_ms)
        
        time_seconds_total = max(0, time_ms_to_display // 1000)
        time_value_str = f"{time_seconds_total // 60:02d}:{time_seconds_total % 60:02d}"
        
        time_color = WHITE
        # Blinking red/yellow for low time, unless it's vault extraction phase (handled by vault HUD)
        is_vault_extraction = (current_scene_state.startswith("architect_vault") and \
                               getattr(self.game_controller, 'architect_vault_current_phase', None) == "extraction")
        if not is_vault_extraction:
            if time_seconds_total <= 10: time_color = RED if (current_time_ticks // 250) % 2 == 0 else DARK_RED # Blink red
            elif time_seconds_total <= 30: time_color = YELLOW
        
        time_icon_surf = self._render_text_safe(time_icon_char, "ui_emoji_general", time_color)
        time_value_surf = self._render_text_safe(time_value_str, self.fonts["ui_values"], time_color) # Use specific timer font if needed

        # Layout center elements
        spacing_between_center_elements = 25
        center_elements_total_width = (
            score_emoji_surf.get_width() + text_icon_spacing + score_text_surf.get_width() +
            spacing_between_center_elements +
            level_emoji_surf.get_width() + text_icon_spacing + level_text_surf.get_width() +
            spacing_between_center_elements +
            time_icon_surf.get_width() + text_icon_spacing + time_value_surf.get_width()
        )
        current_info_x = (WIDTH - center_elements_total_width) // 2 # Center the whole block

        # Blit Score
        self.screen.blit(score_emoji_surf, (current_info_x, info_y_pos + (score_text_surf.get_height() - score_emoji_surf.get_height()) // 2))
        current_info_x += score_emoji_surf.get_width() + text_icon_spacing
        self.screen.blit(score_text_surf, (current_info_x, info_y_pos))
        current_info_x += score_text_surf.get_width() + spacing_between_center_elements

        # Blit Level
        self.screen.blit(level_emoji_surf, (current_info_x, info_y_pos + (level_text_surf.get_height() - level_emoji_surf.get_height()) // 2))
        current_info_x += level_emoji_surf.get_width() + text_icon_spacing
        self.screen.blit(level_text_surf, (current_info_x, info_y_pos))
        current_info_x += level_text_surf.get_width() + spacing_between_center_elements

        # Blit Timer (unless it's vault extraction, which has its own timer display)
        if not is_vault_extraction:
            self.screen.blit(time_icon_surf, (current_info_x, info_y_pos + (time_value_surf.get_height() - time_icon_surf.get_height()) // 2))
            current_info_x += time_icon_surf.get_width() + text_icon_spacing
            self.screen.blit(time_value_surf, (current_info_x, info_y_pos))

        # Update target position for ring collection animation (used by GameController)
        # This 'total_rings_this_level' is now defined earlier
        if total_rings_this_level > 0 and self.ui_assets["ring_icon"]:
            _total_ring_icons_display_width = max(0, total_rings_this_level * (self.ui_icon_size_rings[0] + icon_spacing) - icon_spacing)
            _rings_block_start_x_no_text = collectibles_x_anchor - _total_ring_icons_display_width
            _target_ring_row_y_for_anim = rings_y_pos_hud # Y position of the ring icons
            _next_ring_slot_index = max(0, min(displayed_rings_count, total_rings_this_level - 1))
            
            target_slot_x_offset = _next_ring_slot_index * (self.ui_icon_size_rings[0] + icon_spacing)
            target_slot_center_x = _rings_block_start_x_no_text + target_slot_x_offset + self.ui_icon_size_rings[0] // 2
            target_slot_center_y = _target_ring_row_y_for_anim + self.ui_icon_size_rings[1] // 2
            
            # GameController stores and updates animating_rings and uses this target_pos
            if hasattr(self.game_controller, 'ring_ui_target_pos'):
                self.game_controller.ring_ui_target_pos = (target_slot_center_x, target_slot_center_y)

        # Draw animating rings (GameController updates their positions)
        if hasattr(self.game_controller, 'animating_rings'):
            for ring_anim in self.game_controller.animating_rings:
                if 'surface' in ring_anim and ring_anim['surface']:
                    self.screen.blit(ring_anim['surface'], (int(ring_anim['pos'][0]), int(ring_anim['pos'][1])))


    def draw_architect_vault_hud_elements(self):
        """Draws HUD elements specific to the Architect's Vault, potentially on top of or replacing parts of gameplay HUD."""
        self.draw_gameplay_hud() # Draw the base gameplay HUD first

        current_time = pygame.time.get_ticks()
        current_vault_phase = getattr(self.game_controller, 'architect_vault_current_phase', None)
        
        # Vault specific timer for extraction phase (prominently displayed)
        if current_vault_phase == "extraction":
            time_remaining_ms_vault = getattr(self.game_controller, 'level_time_remaining_ms', 0)
            time_val_str_vault = f"{max(0, time_remaining_ms_vault // 1000) // 60:02d}:{max(0, time_remaining_ms_vault // 1000) % 60:02d}"
            
            time_color_vault = RED
            if (time_remaining_ms_vault // 1000) > 10: time_color_vault = YELLOW
            if (current_time // 250) % 2 == 0 and (time_remaining_ms_vault // 1000) <= 10 : time_color_vault = DARK_RED # Blink
            
            timer_surf_vault = self._render_text_safe(f"ESCAPE ROUTE COLLAPSING: {time_val_str_vault}", "vault_timer", time_color_vault)
            self.screen.blit(timer_surf_vault, timer_surf_vault.get_rect(centerx=WIDTH//2, top=10)) # Position at top center

        # Display Architect's Vault messages (e.g., phase changes, warnings)
        vault_message = getattr(self.game_controller, 'architect_vault_message', "")
        vault_message_timer_end = getattr(self.game_controller, 'architect_vault_message_timer', 0)
        if vault_message and current_time < vault_message_timer_end:
            msg_surf = self._render_text_safe(vault_message, "vault_message", GOLD) # Large gold message
            # Background for the message
            msg_bg_surf = pygame.Surface((msg_surf.get_width() + 30, msg_surf.get_height() + 15), pygame.SRCALPHA)
            msg_bg_surf.fill((10, 0, 20, 200)) # Dark, semi-transparent purple
            msg_bg_surf.blit(msg_surf, msg_surf.get_rect(center=(msg_bg_surf.get_width()//2, msg_bg_surf.get_height()//2)))
            # Position message (e.g., bottom center of game play area)
            self.screen.blit(msg_bg_surf, msg_bg_surf.get_rect(centerx=WIDTH//2, bottom=GAME_PLAY_AREA_HEIGHT - 20))


    def draw_pause_overlay(self):
        """Draws the pause menu overlay."""
        overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay_surface.fill((0,0,0,150)) # Dark semi-transparent overlay
        self.screen.blit(overlay_surface, (0,0))

        pause_title_surf = self._render_text_safe("PAUSED", "large_text", WHITE)
        self.screen.blit(pause_title_surf, pause_title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))

        # Pause menu options depend on the game state when paused
        current_game_state_when_paused = self.scene_manager.get_current_state() # This is the state that was paused
        pause_text_options = "P: Continue | M: Menu | Q: Quit Game" # Default
        if current_game_state_when_paused == GAME_STATE_PLAYING:
             pause_text_options = "P: Continue | L: Leaderboard | M: Menu | Q: Quit Game"
        elif current_game_state_when_paused.startswith("architect_vault"):
             pause_text_options = "P: Continue | ESC: Main Menu (Exit Vault) | Q: Quit Game"

        options_surf = self._render_text_safe(pause_text_options, "ui_text", WHITE)
        self.screen.blit(options_surf, options_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))


    def draw_game_over_overlay(self):
        """Draws the game over screen."""
        # Screen fill and stars are handled by draw_current_scene_ui
        go_text_surf = self._render_text_safe("GAME OVER", "large_text", RED)
        score_text_surf = self._render_text_safe(f"Final Score: {self.game_controller.score}", "medium_text", WHITE) # Larger score text
        self.screen.blit(go_text_surf, go_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 120)))
        self.screen.blit(score_text_surf, score_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 30)))

        can_submit_score = not get_game_setting("SETTINGS_MODIFIED")
        is_new_high = can_submit_score and leaderboard.is_high_score(self.game_controller.score, self.game_controller.level)
        prompt_y_offset = HEIGHT // 2 + 50

        if not can_submit_score:
            no_lb_text_surf = self._render_text_safe("Leaderboard disabled (custom settings).", "ui_text", YELLOW)
            self.screen.blit(no_lb_text_surf, no_lb_text_surf.get_rect(center=(WIDTH//2, prompt_y_offset)))
            prompt_y_offset += self.fonts["ui_text"].get_height() + 20 # Adjust spacing

        prompt_str = "R: Restart  M: Menu  Q: Quit"
        prompt_color = WHITE
        if can_submit_score and is_new_high:
            prompt_str = "New High Score! Press any key to enter name."
            prompt_color = GOLD
        elif can_submit_score: # Can submit, but not a new high (or leaderboard full)
            prompt_str = "R: Restart  L: Leaderboard  M: Menu  Q: Quit"

        prompt_surf = self._render_text_safe(prompt_str, "ui_text", prompt_color)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, prompt_y_offset)))


    def draw_enter_name_overlay(self):
        """Draws the screen for entering name for a new high score."""
        # Screen fill and stars handled by draw_current_scene_ui
        title_surf = self._render_text_safe("New High Score!", "large_text", GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 180)))

        score_level_text = f"Your Score: {self.game_controller.score} (Level: {self.game_controller.level})"
        score_level_surf = self._render_text_safe(score_level_text, "medium_text", WHITE) # Larger text
        self.screen.blit(score_level_surf, score_level_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 90)))

        prompt_name_surf = self._render_text_safe("Enter Name (max 6 chars, A-Z):", "ui_text", WHITE)
        self.screen.blit(prompt_name_surf, prompt_name_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 20)))

        # Input Box for Name
        # Get current input text from GameController (which gets it from EventManager)
        player_name_input_str = getattr(self.game_controller, 'player_name_input_display_cache', "")
        input_box_width = 300; input_box_height = 60
        input_box_rect = pygame.Rect(WIDTH//2 - input_box_width//2, HEIGHT//2 + 30, input_box_width, input_box_height)
        pygame.draw.rect(self.screen, WHITE, input_box_rect, 2, border_radius=10) # Rounded border
        
        input_text_surf = self._render_text_safe(player_name_input_str, "input_text", WHITE) # Large font for input
        self.screen.blit(input_text_surf, input_text_surf.get_rect(center=input_box_rect.center))

        submit_prompt_surf = self._render_text_safe("Press ENTER to submit.", "ui_text", CYAN)
        self.screen.blit(submit_prompt_surf, submit_prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 120)))


    def draw_leaderboard_overlay(self):
        """Draws the leaderboard display screen."""
        # Screen fill and stars handled by draw_current_scene_ui
        title_surf = self._render_text_safe("Leaderboard", "large_text", GOLD)
        title_bg_rect_width = title_surf.get_width() + 40
        title_bg_rect_height = title_surf.get_height() + 20
        title_bg_surf = pygame.Surface((title_bg_rect_width, title_bg_rect_height), pygame.SRCALPHA)
        title_bg_surf.fill((20,20,20,180)) # Semi-transparent BG for title
        title_bg_surf.blit(title_surf, title_surf.get_rect(center=(title_bg_rect_width//2, title_bg_rect_height//2)))
        self.screen.blit(title_bg_surf, title_bg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 300))) # Position title

        scores_to_display = getattr(self.game_controller, 'leaderboard_scores', []) # Get scores from GameController
        
        header_y = HEIGHT // 2 - 250 # Y position for column headers
        score_item_y_start = HEIGHT // 2 - 200 # Y position for the first score entry
        item_line_height = self.fonts["leaderboard_entry"].get_height() + 15 # Spacing for entries

        if not scores_to_display:
            no_scores_surf = self._render_text_safe("No scores yet!", "medium_text", WHITE) # Larger text
            no_scores_bg = pygame.Surface((no_scores_surf.get_width()+20, no_scores_surf.get_height()+10), pygame.SRCALPHA)
            no_scores_bg.fill((30,30,30,160))
            no_scores_bg.blit(no_scores_surf, no_scores_surf.get_rect(center=(no_scores_bg.get_width()//2, no_scores_bg.get_height()//2)))
            self.screen.blit(no_scores_bg, no_scores_bg.get_rect(center=(WIDTH//2, HEIGHT//2)))
        else:
            # Define column positions (adjust these based on your desired layout)
            cols_x_positions = {"Rank": WIDTH//2 - 350, "Name": WIDTH//2 - 250, "Level": WIDTH//2 + 50, "Score": WIDTH//2 + 200}
            header_font = self.fonts.get("leaderboard_header", self.fonts["ui_text"])
            entry_font = self.fonts.get("leaderboard_entry", self.fonts["ui_text"])

            # Draw Headers
            for col_name, x_pos in cols_x_positions.items():
                header_surf = header_font.render(col_name, True, WHITE)
                header_bg = pygame.Surface((header_surf.get_width()+15, header_surf.get_height()+8), pygame.SRCALPHA)
                header_bg.fill((40,40,40,170)) # Darker BG for headers
                header_bg.blit(header_surf, header_surf.get_rect(center=(header_bg.get_width()//2, header_bg.get_height()//2)))
                self.screen.blit(header_bg, (x_pos, header_y))

            # Draw Score Entries
            for i, entry in enumerate(scores_to_display):
                if i >= get_game_setting("LEADERBOARD_MAX_ENTRIES"): break # Use setting for max entries
                y_pos = score_item_y_start + i * item_line_height
                
                # Data for each column of the entry
                texts_to_draw = [
                    (f"{i+1}.", WHITE, cols_x_positions["Rank"]),
                    (str(entry.get('name','N/A')).upper(), CYAN, cols_x_positions["Name"]), # Ensure name is string and uppercase
                    (str(entry.get('level','-')), GREEN, cols_x_positions["Level"]),
                    (str(entry.get('score',0)), GOLD, cols_x_positions["Score"])
                ]
                for text_str, color, x_coord in texts_to_draw:
                    text_surf = entry_font.render(text_str, True, color)
                    # Optional: background for each item for better readability
                    # item_bg=pygame.Surface((text_surf.get_width()+8,text_surf.get_height()+4),pygame.SRCALPHA)
                    # item_bg.fill((30,30,30,150)); item_bg.blit(text_surf,(4,2))
                    # self.screen.blit(item_bg,(x_coord,y_pos))
                    self.screen.blit(text_surf, (x_coord, y_pos)) # Simpler: just blit text

        # Instructions at bottom
        menu_prompt_surf = self._render_text_safe("ESC: Main Menu | Q: Quit Game", "ui_text", WHITE)
        prompt_bg = pygame.Surface((menu_prompt_surf.get_width()+20, menu_prompt_surf.get_height()+10), pygame.SRCALPHA)
        prompt_bg.fill((20,20,20,180))
        prompt_bg.blit(menu_prompt_surf, prompt_bg.get_rect(center=(prompt_bg.get_width()//2, prompt_bg.get_height()//2)))
        self.screen.blit(prompt_bg, prompt_bg.get_rect(center=(WIDTH//2, HEIGHT-100)))


    def draw_architect_vault_success_overlay(self):
        """Draws the overlay for successfully completing the Architect's Vault."""
        # Screen fill handled by draw_current_scene_ui
        msg_surf = self._render_text_safe("Vault Conquered!", "large_text", GOLD)
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 80)))

        # Display reward information (e.g., blueprint ID)
        blueprint_id = get_game_setting("ARCHITECT_REWARD_BLUEPRINT_ID") # Get from game_settings
        reward_text = f"Blueprint Acquired: {blueprint_id}" if blueprint_id else "Ancient Technology Secured!"
        reward_surf = self._render_text_safe(reward_text, "medium_text", CYAN)
        self.screen.blit(reward_surf, reward_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))

        prompt_surf = self._render_text_safe("Press ENTER or M to Continue", "ui_text", WHITE)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 100)))


    def draw_architect_vault_failure_overlay(self):
        """Draws the overlay for failing the Architect's Vault."""
        # Screen fill handled by draw_current_scene_ui
        msg_surf = self._render_text_safe("Vault Mission Failed", "large_text", RED)
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))

        reason_text = getattr(self.game_controller, 'architect_vault_failure_reason', "Critical systems compromised.")
        reason_surf = self._render_text_safe(reason_text, "ui_text", YELLOW)
        self.screen.blit(reason_surf, reason_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))
        
        prompt_surf = self._render_text_safe("Press ENTER or M to Return to Menu", "ui_text", WHITE)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 80)))