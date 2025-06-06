# hyperdrone_core/ui_flow_controller.py
import pygame
import random
import logging

import game_settings as gs
from game_settings import (
    WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT, 
    # <<< FIX: Added missing game state constants >>>
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT,
    GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, GAME_STATE_CODEX,
    GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, GAME_STATE_PLAYING, GAME_STATE_MAZE_DEFENSE,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_GAME_INTRO_SCROLL,
    get_game_setting, set_game_setting, reset_all_settings_to_default,
    SETTINGS_MODIFIED
)

logger = logging.getLogger(__name__)

class UIFlowController:
    """
    Manages the state and navigation logic for UI-heavy screens like menus,
    settings, leaderboards, and codex.
    """
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        self.scene_manager = None
        self.ui_manager = None
        self.drone_system = None
        self.leaderboard_scores = []
        
        # Menu state variables
        self.menu_options = ["Start Game", "Maze Defense", "Select Drone", "Codex", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0
        self.menu_stars = self._create_stars(200)

        # Drone Select state variables
        self.drone_select_options = []
        self.selected_drone_preview_index = 0

        # Settings state variables
        self.settings_items_data = []
        self.selected_setting_index = 0

        # Leaderboard/Game Over state
        self.player_name_input_cache = ""
        self.game_over_acknowledged = False
        
        # Codex state variables
        self.codex_categories_list = []
        self.codex_current_view = "categories"
        self.codex_selected_category_index = 0
        self.codex_current_category_name = ""
        self.codex_entries_in_category_list = []
        self.codex_selected_entry_index_in_category = 0
        self.codex_selected_entry_id = None
        self.codex_content_scroll_offset = 0
        self.codex_current_entry_total_lines = 0

        # Architect Vault Result Screen
        self.architect_vault_result_message = ""
        self.architect_vault_result_message_color = gs.WHITE

        # Game Intro Scroll
        self.intro_screens_data = []
        self.current_intro_screen_index = 0
        self.intro_screen_start_time = 0
        self.intro_sequence_finished = False
        
        logger.info("UIFlowController initialized.")


    def set_dependencies(self, scene_manager, ui_manager, drone_system):
        """Sets references to other managers after they are initialized."""
        self.scene_manager = scene_manager
        self.ui_manager = ui_manager
        self.drone_system = drone_system

    def handle_key_input(self, key, current_game_state):
        """
        Public method to route keyboard input to the correct handler based on game state.
        This is called by the EventManager.
        """
        if current_game_state == GAME_STATE_MAIN_MENU:
            return self._handle_main_menu_input(key)
        elif current_game_state == GAME_STATE_DRONE_SELECT:
            return self._handle_drone_select_input(key)
        elif current_game_state == GAME_STATE_SETTINGS:
            return self._handle_settings_input(key)
        elif current_game_state == GAME_STATE_LEADERBOARD:
            return self._handle_leaderboard_input(key)
        elif current_game_state == GAME_STATE_CODEX:
            return self._handle_codex_input(key)
        elif current_game_state == GAME_STATE_ENTER_NAME:
            return self._handle_enter_name_input(key)
        elif current_game_state == GAME_STATE_GAME_OVER:
            return self._handle_game_over_input(key)
        elif current_game_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS or current_game_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
            return self._handle_vault_result_input(key)
        elif current_game_state == GAME_STATE_GAME_INTRO_SCROLL:
            return self._handle_game_intro_input(key)
        
        return False # Input was not handled by any UI flow

    def update(self, current_time_ms, delta_time_ms, current_game_state):
        """Called every frame to update UI animations or timed transitions."""
        if current_game_state == GAME_STATE_MAIN_MENU:
            if self.menu_stars:
                for star in self.menu_stars:
                    star[1] += star[2] * (delta_time_ms / 1000.0)
                    if star[1] > HEIGHT:
                        star[0] = random.randint(0, WIDTH)
                        star[1] = 0

    def _create_stars(self, num_stars):
        """Helper to create a list of star parameters for background effects."""
        stars = []
        for _ in range(num_stars):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            speed = random.uniform(10, 50)
            size = random.uniform(0.5, 2)
            stars.append([x, y, speed, size])
        return stars

    # --- Initialization Methods for Each UI State ---
    def initialize_main_menu(self):
        self.selected_menu_option = 0
        if self.game_controller and self.game_controller.player:
            self.game_controller.player = None
        if self.game_controller and hasattr(self.game_controller, 'combat_controller'):
            self.game_controller.combat_controller.reset_combat_state()

    def initialize_drone_select(self):
        if not self.drone_system: return
        self.drone_select_options = self.drone_system.get_all_drone_ids_in_order()
        current_id = self.drone_system.get_selected_drone_id()
        if current_id in self.drone_select_options:
            self.selected_drone_preview_index = self.drone_select_options.index(current_id)
        else:
            self.selected_drone_preview_index = 0

    def initialize_settings(self, settings_data):
        self.settings_items_data = settings_data
        self.selected_setting_index = 0

    def initialize_leaderboard(self):
        if self.game_controller and hasattr(self.game_controller, 'leaderboard'):
            self.leaderboard_scores = self.game_controller.leaderboard.load_scores()

    def initialize_codex(self):
        if not self.drone_system: return
        self.codex_current_view = "categories"
        self.codex_categories_list = self.drone_system.get_unlocked_lore_categories()
        self.codex_selected_category_index = 0
        self.codex_content_scroll_offset = 0

    def initialize_enter_name(self):
        self.player_name_input_cache = ""

    def initialize_architect_vault_result_screen(self, success=True, failure_reason=""):
        if success:
            self.architect_vault_result_message = "VAULT CONQUERED"
            self.architect_vault_result_message_color = gs.GOLD
        else:
            self.architect_vault_result_message = "MISSION FAILED"
            self.architect_vault_result_message_color = gs.RED
        self.game_controller.architect_vault_failure_reason = failure_reason

    def initialize_game_intro(self, intro_data):
        self.intro_screens_data = intro_data
        self.current_intro_screen_index = 0
        self.intro_screen_start_time = pygame.time.get_ticks()
        self.intro_sequence_finished = False
        self.game_controller._prepare_current_intro_screen_surfaces()

    def reset_ui_flow_states(self):
        """Resets all UI state variables to their defaults."""
        self.selected_menu_option = 0
        self.selected_drone_preview_index = 0
        self.selected_setting_index = 0
        self.player_name_input_cache = ""
        self.game_over_acknowledged = False
        self.codex_current_view = "categories"
        self.codex_selected_category_index = 0
        self.codex_content_scroll_offset = 0
        logger.info("UIFlowController: UI states reset.")
        
    # --- Private Input Handlers for Each UI State ---
    
    def _handle_main_menu_input(self, key):
        if key == pygame.K_UP or key == pygame.K_w:
            self.selected_menu_option = (self.selected_menu_option - 1) % len(self.menu_options)
            self.game_controller.play_sound('ui_select')
            return True
        elif key == pygame.K_DOWN or key == pygame.K_s:
            self.selected_menu_option = (self.selected_menu_option + 1) % len(self.menu_options)
            self.game_controller.play_sound('ui_select')
            return True
        elif key == pygame.K_RETURN or key == pygame.K_SPACE:
            selected_action = self.menu_options[self.selected_menu_option]
            logger.info(f"Main menu action selected: {selected_action}")
            self.game_controller.play_sound('ui_confirm')
            if selected_action == "Start Game": self.scene_manager.set_game_state(GAME_STATE_GAME_INTRO_SCROLL)
            elif selected_action == "Maze Defense": self.scene_manager.set_game_state(GAME_STATE_MAZE_DEFENSE)
            elif selected_action == "Select Drone": self.scene_manager.set_game_state(GAME_STATE_DRONE_SELECT)
            elif selected_action == "Settings": self.scene_manager.set_game_state(GAME_STATE_SETTINGS)
            elif selected_action == "Leaderboard": self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
            elif selected_action == "Codex": self.scene_manager.set_game_state(GAME_STATE_CODEX)
            elif selected_action == "Quit": self.game_controller.quit_game()
            return True
        return False

    def _handle_drone_select_input(self, key):
        if not self.drone_select_options: return False
        num_options = len(self.drone_select_options)
        
        if key == pygame.K_LEFT or key == pygame.K_a:
            self.selected_drone_preview_index = (self.selected_drone_preview_index - 1 + num_options) % num_options
            self.game_controller.play_sound('ui_select')
            return True
        elif key == pygame.K_RIGHT or key == pygame.K_d:
            self.selected_drone_preview_index = (self.selected_drone_preview_index + 1) % num_options
            self.game_controller.play_sound('ui_select')
            return True
        elif key == pygame.K_RETURN or key == pygame.K_SPACE:
            selected_id = self.drone_select_options[self.selected_drone_preview_index]
            if self.drone_system.is_drone_unlocked(selected_id):
                self.drone_system.set_selected_drone(selected_id)
                self.game_controller.play_sound('ui_confirm')
                if hasattr(self.ui_manager, 'update_player_life_icon_surface'): self.ui_manager.update_player_life_icon_surface()
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            else: # Attempt to unlock
                if self.drone_system.unlock_drone(selected_id):
                    self.game_controller.play_sound('lore_unlock') # Re-use sound
                else:
                    self.game_controller.play_sound('ui_denied')
            return True
        return False

    def _handle_settings_input(self, key):
        if not self.settings_items_data: return False
        selected_item = self.settings_items_data[self.selected_setting_index]
        item_key = selected_item["key"]
        
        if key == pygame.K_UP or key == pygame.K_w:
            self.selected_setting_index = (self.selected_setting_index - 1 + len(self.settings_items_data)) % len(self.settings_items_data)
            self.game_controller.play_sound('ui_select', 0.5)
            return True
        elif key == pygame.K_DOWN or key == pygame.K_s:
            self.selected_setting_index = (self.selected_setting_index + 1) % len(self.settings_items_data)
            self.game_controller.play_sound('ui_select', 0.5)
            return True
        elif key == pygame.K_RETURN and selected_item["type"] == "action":
            if item_key == "RESET_SETTINGS_ACTION":
                reset_all_settings_to_default()
                self.game_controller.play_sound('ui_confirm')
            return True
        
        direction = 0
        if key == pygame.K_LEFT or key == pygame.K_a: direction = -1
        elif key == pygame.K_RIGHT or key == pygame.K_d: direction = 1
        
        if direction != 0:
            current_val = get_game_setting(item_key)
            if selected_item["type"] == "numeric":
                step = selected_item.get("step", 1)
                new_val = current_val + direction * step
                new_val = max(selected_item["min"], min(new_val, selected_item["max"]))
                set_game_setting(item_key, new_val)
                self.game_controller.play_sound('ui_select')
            elif selected_item["type"] == "choice":
                choices = selected_item["choices"]
                try:
                    current_idx = choices.index(current_val)
                    new_idx = (current_idx + direction + len(choices)) % len(choices)
                    set_game_setting(item_key, choices[new_idx])
                    self.game_controller.play_sound('ui_select')
                except ValueError: pass # Value not in choices, do nothing
            return True
        return False

    def _handle_leaderboard_input(self, key):
        if key == pygame.K_RETURN or key == pygame.K_q:
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            return True
        return False

    def _handle_codex_input(self, key):
        if self.codex_current_view == "categories":
            if key in (pygame.K_UP, pygame.K_w): self.codex_selected_category_index = (self.codex_selected_category_index - 1 + len(self.codex_categories_list)) % len(self.codex_categories_list) if self.codex_categories_list else 0
            elif key in (pygame.K_DOWN, pygame.K_s): self.codex_selected_category_index = (self.codex_selected_category_index + 1) % len(self.codex_categories_list) if self.codex_categories_list else 0
            elif key == pygame.K_RETURN:
                if self.codex_categories_list:
                    self.codex_current_view = "entries"
                    self.codex_current_category_name = self.codex_categories_list[self.codex_selected_category_index]
                    self.codex_entries_in_category_list = self.drone_system.get_unlocked_lore_entries_by_category(self.codex_current_category_name)
                    self.codex_selected_entry_index_in_category = 0
        elif self.codex_current_view == "entries":
            if key == pygame.K_ESCAPE: self.codex_current_view = "categories"
            elif key in (pygame.K_UP, pygame.K_w): self.codex_selected_entry_index_in_category = (self.codex_selected_entry_index_in_category - 1 + len(self.codex_entries_in_category_list)) % len(self.codex_entries_in_category_list) if self.codex_entries_in_category_list else 0
            elif key in (pygame.K_DOWN, pygame.K_s): self.codex_selected_entry_index_in_category = (self.codex_selected_entry_index_in_category + 1) % len(self.codex_entries_in_category_list) if self.codex_entries_in_category_list else 0
            elif key == pygame.K_RETURN:
                if self.codex_entries_in_category_list:
                    self.codex_current_view = "content"
                    self.codex_selected_entry_id = self.codex_entries_in_category_list[self.codex_selected_entry_index_in_category]['id']
                    self.codex_content_scroll_offset = 0
        elif self.codex_current_view == "content":
            if key == pygame.K_ESCAPE: self.codex_current_view = "entries"
            elif key in (pygame.K_UP, pygame.K_w): self.codex_content_scroll_offset = max(0, self.codex_content_scroll_offset - 1)
            elif key in (pygame.K_DOWN, pygame.K_s): self.codex_content_scroll_offset = min(max(0, self.codex_current_entry_total_lines - 10), self.codex_content_scroll_offset + 1)
        
        self.game_controller.play_sound('ui_select', 0.5)
        return True

    def _handle_enter_name_input(self, key):
        if key == pygame.K_RETURN:
            if len(self.player_name_input_cache) > 0:
                self.game_controller.submit_leaderboard_name(self.player_name_input_cache)
            return True
        elif key == pygame.K_BACKSPACE:
            self.player_name_input_cache = self.player_name_input_cache[:-1]
            return True
        elif len(self.player_name_input_cache) < 6:
            try:
                char = pygame.key.name(key).upper()
                if len(char) == 1 and char.isalpha():
                    self.player_name_input_cache += char
                    return True
            except: pass
        return False

    def _handle_game_over_input(self, key):
        if self.game_controller.is_current_score_a_high_score() and not gs.SETTINGS_MODIFIED:
            self.scene_manager.set_game_state(GAME_STATE_ENTER_NAME)
        else:
            if key == pygame.K_r: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU, action="restart") # Or GAME_STATE_PLAYING
            elif key == pygame.K_l: self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
            elif key == pygame.K_m: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            elif key == pygame.K_q: self.game_controller.quit_game()
        return True

    def _handle_vault_result_input(self, key):
        if key == pygame.K_RETURN or key == pygame.K_m or key == pygame.K_SPACE:
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            return True
        return False
        
    def _handle_game_intro_input(self, key):
        if key == pygame.K_SPACE or key == pygame.K_RETURN:
            if self.intro_sequence_finished:
                self.scene_manager.set_game_state(GAME_STATE_PLAYING)
            else:
                self.current_intro_screen_index += 1
                if self.current_intro_screen_index >= len(self.intro_screens_data):
                    self.intro_sequence_finished = True
                else:
                    self.intro_screen_start_time = pygame.time.get_ticks()
                    self.game_controller._prepare_current_intro_screen_surfaces()
            return True
        elif key == pygame.K_ESCAPE:
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            return True
        return False
