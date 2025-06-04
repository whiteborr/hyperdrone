# hyperdrone_core/ui_flow_controller.py
import pygame
import os
import random # For starfield

import game_settings as gs
from game_settings import (
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
    GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME,
    GAME_STATE_CODEX, GAME_STATE_GAME_INTRO_SCROLL,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE, # Added vault result states
    WIDTH, HEIGHT, FPS # For starfield or other UI effects
)
# Import other necessary modules or classes
from drone_management import DRONE_DISPLAY_ORDER # For drone selection screen
from . import leaderboard # For leaderboard data

class UIFlowController:
    """
    Manages the flow of UI-heavy game states like menus, leaderboards,
    settings, drone selection, codex, game intro, and game over screens.
    It handles the logic and data for these states, and interacts with
    the UIManager for drawing and the SceneManager for state transitions.
    """
    def __init__(self, game_controller_ref):
        """
        Initializes the UIFlowController.

        Args:
            game_controller_ref: A reference to the main GameController instance.
        """
        self.game_controller = game_controller_ref
        self.scene_manager = None 
        self.ui_manager = None    
        self.drone_system = None  
        
        # --- Main Menu State ---
        self.menu_options = ["Start Game", "Maze Defense", "Select Drone", "Codex", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0
        self.menu_stars = [] 

        # --- Drone Select State ---
        self.drone_select_options = DRONE_DISPLAY_ORDER[:] 
        self.selected_drone_preview_index = 0
        # self.drone_main_display_cache is managed by GameController and accessed via game_controller_ref if needed by UIManager

        # --- Settings Menu State ---
        self.settings_items_data = [] 
        self.selected_setting_index = 0

        # --- Leaderboard State ---
        self.leaderboard_scores = []

        # --- Enter Name State (Game Over) ---
        self.player_name_input_cache = "" 

        # --- Codex State ---
        self.codex_current_view = "categories" 
        self.codex_categories_list = []
        self.codex_selected_category_index = 0
        self.codex_current_category_name = None
        self.codex_entries_in_category_list = []
        self.codex_selected_entry_index_in_category = 0
        self.codex_selected_entry_id = None
        self.codex_content_scroll_offset = 0
        self.codex_current_entry_total_lines = 0 

        # --- Game Intro Scroll State ---
        self.intro_screens_data = [] 
        self.current_intro_screen_index = 0
        self.intro_screen_start_time = 0
        self.intro_sequence_finished = False
        
        # --- Architect Vault Result Message Handling ---
        # These might be simple messages displayed by UIManager based on data from here
        self.architect_vault_result_message = "" # e.g., "Vault Conquered!"
        self.architect_vault_result_message_color = gs.GOLD

        print("UIFlowController initialized.")

    def set_dependencies(self, scene_manager, ui_manager, drone_system):
        """
        Sets references to other managers. Called by GameController.
        """
        self.scene_manager = scene_manager
        self.ui_manager = ui_manager    
        self.drone_system = drone_system
        
        self._initialize_menu_stars()
        # Settings items data and intro data will be fetched from GameController
        # when their respective scenes are initialized by GameController.
        # This avoids UIFlowController needing to know about GameController's internal methods
        # for fetching these structures during its own __init__ or set_dependencies.

    def _initialize_menu_stars(self, num_stars=150):
        self.menu_stars = []
        for _ in range(num_stars):
            x = random.randint(0, gs.get_game_setting("WIDTH"))
            y = random.randint(0, gs.get_game_setting("HEIGHT"))
            speed = random.uniform(0.1, 0.7) # Pixels per frame (approx, adjusted by delta_time)
            size = random.randint(1, 2)
            self.menu_stars.append([x, y, speed, size])

    def update(self, current_time_ms, delta_time_ms, current_game_state):
        """
        Main update loop for the UIFlowController.
        Handles logic for UI states like menu star movement, intro screen timing.
        """
        if current_game_state in [GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT,
                                  GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, 
                                  GAME_STATE_CODEX, GAME_STATE_GAME_OVER, 
                                  GAME_STATE_ENTER_NAME, GAME_STATE_ARCHITECT_VAULT_SUCCESS,
                                  GAME_STATE_ARCHITECT_VAULT_FAILURE]:
            if self.menu_stars:
                # Normalize speed based on FPS to make movement consistent
                # Assuming delta_time_ms is time since last frame
                # Target frame time for 60 FPS is approx 16.66 ms
                frame_time_ratio = delta_time_ms / (1000.0 / FPS if FPS > 0 else 16.66)
                for star in self.menu_stars:
                    star_speed_adjusted = star[2] * frame_time_ratio 
                    star[0] -= star_speed_adjusted 
                    if star[0] < 0:
                        star[0] = gs.get_game_setting("WIDTH")
                        star[1] = random.randint(0, gs.get_game_setting("HEIGHT"))
        
        elif current_game_state == GAME_STATE_GAME_INTRO_SCROLL:
            if not self.intro_sequence_finished:
                # Use get_game_setting for INTRO_SCREEN_DURATION_MS for consistency
                if current_time_ms - self.intro_screen_start_time >= gs.get_game_setting("INTRO_SCREEN_DURATION_MS", 6000):
                    self.advance_intro_screen()

    def handle_input(self, event, current_game_state):
        """
        Handles player input for UI-centric game states.
        Called by EventManager.
        Returns:
            bool: True if the event was consumed, False otherwise.
        """
        # Centralized sound playing for UI feedback
        def play_ui_sound(sound_name, volume=0.6):
            if hasattr(self.game_controller, 'play_sound'):
                self.game_controller.play_sound(sound_name, volume)

        if current_game_state == GAME_STATE_MAIN_MENU:
            return self._handle_main_menu_input(event, play_ui_sound)
        elif current_game_state == GAME_STATE_DRONE_SELECT:
            return self._handle_drone_select_input(event, play_ui_sound)
        elif current_game_state == GAME_STATE_SETTINGS:
            return self._handle_settings_input(event, play_ui_sound)
        elif current_game_state == GAME_STATE_LEADERBOARD:
            return self._handle_leaderboard_input(event, play_ui_sound)
        elif current_game_state == GAME_STATE_CODEX:
            return self._handle_codex_input(event, play_ui_sound)
        elif current_game_state == GAME_STATE_ENTER_NAME:
            return self._handle_enter_name_input(event, play_ui_sound) # Sound might be different here
        elif current_game_state == GAME_STATE_GAME_OVER:
            return self._handle_game_over_input(event, play_ui_sound)
        elif current_game_state == GAME_STATE_GAME_INTRO_SCROLL:
            return self._handle_game_intro_input(event, play_ui_sound)
        elif current_game_state in [GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE]:
            return self._handle_vault_result_input(event, play_ui_sound)
            
        return False

    def _handle_main_menu_input(self, event, play_sound_func):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_menu_option = (self.selected_menu_option - 1 + len(self.menu_options)) % len(self.menu_options)
                play_sound_func('ui_select')
            elif event.key == pygame.K_DOWN:
                self.selected_menu_option = (self.selected_menu_option + 1) % len(self.menu_options)
                play_sound_func('ui_select')
            elif event.key == pygame.K_RETURN:
                play_sound_func('ui_confirm')
                action = self.menu_options[self.selected_menu_option]
                if action == "Start Game":
                    self.scene_manager.set_game_state(GAME_STATE_GAME_INTRO_SCROLL)
                elif action == "Maze Defense":
                    # GameController will handle the actual initialization
                    self.game_controller.initialize_specific_game_mode("maze_defense")
                elif action == "Select Drone":
                    self.scene_manager.set_game_state(GAME_STATE_DRONE_SELECT)
                elif action == "Codex":
                    self.scene_manager.set_game_state(GAME_STATE_CODEX)
                elif action == "Settings":
                    self.scene_manager.set_game_state(GAME_STATE_SETTINGS)
                elif action == "Leaderboard":
                    self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
                elif action == "Quit":
                    self.game_controller.quit_game()
            elif event.key == pygame.K_q:
                self.game_controller.quit_game()
            return True
        return False

    def _handle_drone_select_input(self, event, play_sound_func):
        if event.type == pygame.KEYDOWN:
            num_options = len(self.drone_select_options)
            if num_options == 0: return True 

            if event.key == pygame.K_LEFT:
                self.selected_drone_preview_index = (self.selected_drone_preview_index - 1 + num_options) % num_options
                play_sound_func('ui_select')
            elif event.key == pygame.K_RIGHT:
                self.selected_drone_preview_index = (self.selected_drone_preview_index + 1) % num_options
                play_sound_func('ui_select')
            elif event.key == pygame.K_RETURN:
                selected_id = self.drone_select_options[self.selected_drone_preview_index]
                if self.drone_system.is_drone_unlocked(selected_id):
                    if self.drone_system.set_selected_drone_id(selected_id):
                        play_sound_func('ui_confirm')
                        if self.ui_manager: self.ui_manager.update_player_life_icon_surface()
                        self.drone_system.check_and_unlock_lore_entries(event_trigger=f"drone_selected_{selected_id}")
                else: 
                    unlocked_status, _ = self.drone_system.attempt_unlock_drone_with_cores(selected_id)
                    if unlocked_status: play_sound_func('ui_confirm')
                    else: play_sound_func('ui_denied')
            elif event.key == pygame.K_ESCAPE:
                play_sound_func('ui_select')
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            return True
        return False

    def _handle_settings_input(self, event, play_sound_func):
        if event.type == pygame.KEYDOWN:
            if not self.settings_items_data: return True

            current_item = self.settings_items_data[self.selected_setting_index]
            setting_key = current_item["key"]

            if event.key == pygame.K_UP:
                self.selected_setting_index = (self.selected_setting_index - 1 + len(self.settings_items_data)) % len(self.settings_items_data)
                play_sound_func('ui_select')
            elif event.key == pygame.K_DOWN:
                self.selected_setting_index = (self.selected_setting_index + 1) % len(self.settings_items_data)
                play_sound_func('ui_select')
            elif event.key == pygame.K_RETURN:
                if current_item["type"] == "action" and setting_key == "RESET_SETTINGS_ACTION":
                    gs.reset_all_settings_to_default()
                    # GameController needs to handle screen reinitialization if fullscreen changes
                    if hasattr(self.game_controller, 'check_and_apply_screen_settings_change'):
                        self.game_controller.check_and_apply_screen_settings_change()
                    play_sound_func('ui_confirm')
            elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                if current_item["type"] != "action":
                    play_sound_func('ui_select', 0.7)
                    current_val = gs.get_game_setting(setting_key)
                    direction = 1 if event.key == pygame.K_RIGHT else -1
                    if current_item["type"] == "numeric":
                        step = current_item["step"]; min_v = current_item["min"]; max_v = current_item["max"]
                        new_val = current_val + step * direction
                        new_val = max(min_v, min(max_v, new_val))
                        gs.set_game_setting(setting_key, type(current_val)(new_val))
                    elif current_item["type"] == "choice":
                        choices = current_item.get("choices", [])
                        if choices:
                            try:
                                current_choice_idx = choices.index(current_val)
                                new_idx = (current_choice_idx + direction + len(choices)) % len(choices)
                                gs.set_game_setting(setting_key, choices[new_idx])
                            except ValueError: gs.set_game_setting(setting_key, choices[0])
                    if setting_key == "FULLSCREEN_MODE" and hasattr(self.game_controller, 'check_and_apply_screen_settings_change'):
                         self.game_controller.check_and_apply_screen_settings_change()
            elif event.key == pygame.K_ESCAPE:
                play_sound_func('ui_select')
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            return True
        return False

    def _handle_leaderboard_input(self, event, play_sound_func):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_m:
                play_sound_func('ui_select')
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            elif event.key == pygame.K_q:
                self.game_controller.quit_game()
            return True
        return False

    def _handle_codex_input(self, event, play_sound_func):
        if event.type == pygame.KEYDOWN:
            play_sound_func('ui_select', 0.6)
            if self.codex_current_view == "categories":
                # (Category navigation logic - remains largely the same)
                if event.key == pygame.K_UP: self.codex_selected_category_index = (self.codex_selected_category_index - 1 + len(self.codex_categories_list)) % len(self.codex_categories_list) if self.codex_categories_list else 0
                elif event.key == pygame.K_DOWN: self.codex_selected_category_index = (self.codex_selected_category_index + 1) % len(self.codex_categories_list) if self.codex_categories_list else 0
                elif event.key == pygame.K_RETURN:
                    if self.codex_categories_list:
                        self.codex_current_category_name = self.codex_categories_list[self.codex_selected_category_index]
                        self.codex_current_view = "entries"; self.codex_selected_entry_index_in_category = 0
                        self._populate_codex_entries_for_category()
                elif event.key == pygame.K_ESCAPE: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            elif self.codex_current_view == "entries":
                # (Entry navigation logic - remains largely the same)
                if event.key == pygame.K_UP: self.codex_selected_entry_index_in_category = (self.codex_selected_entry_index_in_category - 1 + len(self.codex_entries_in_category_list)) % len(self.codex_entries_in_category_list) if self.codex_entries_in_category_list else 0
                elif event.key == pygame.K_DOWN: self.codex_selected_entry_index_in_category = (self.codex_selected_entry_index_in_category + 1) % len(self.codex_entries_in_category_list) if self.codex_entries_in_category_list else 0
                elif event.key == pygame.K_RETURN:
                    if self.codex_entries_in_category_list and 0 <= self.codex_selected_entry_index_in_category < len(self.codex_entries_in_category_list):
                        self.codex_selected_entry_id = self.codex_entries_in_category_list[self.codex_selected_entry_index_in_category].get("id")
                        self.codex_current_view = "content"; self.codex_content_scroll_offset = 0
                elif event.key == pygame.K_ESCAPE: self.codex_current_view = "categories"; self.codex_current_category_name = None; self.codex_selected_entry_id = None; self.codex_content_scroll_offset = 0
            elif self.codex_current_view == "content":
                # (Content scrolling logic - remains largely the same)
                if event.key == pygame.K_UP: self.codex_content_scroll_offset = max(0, self.codex_content_scroll_offset - 1)
                elif event.key == pygame.K_DOWN:
                    max_visible = self.ui_manager.codex_max_visible_lines_content if self.ui_manager and hasattr(self.ui_manager, 'codex_max_visible_lines_content') and self.ui_manager.codex_max_visible_lines_content > 0 else 1
                    max_scroll = max(0, self.codex_current_entry_total_lines - max_visible)
                    if self.codex_content_scroll_offset < max_scroll: self.codex_content_scroll_offset += 1
                elif event.key == pygame.K_ESCAPE: self.codex_current_view = "entries"; self.codex_selected_entry_id = None; self.codex_content_scroll_offset = 0
            return True
        return False

    def _handle_enter_name_input(self, event, play_sound_func):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.player_name_input_cache:
                    # GameController will handle the actual submission and state change
                    self.game_controller.submit_leaderboard_name(self.player_name_input_cache)
                else: # If name is empty, go to leaderboard or menu
                    play_sound_func('ui_denied') # Maybe a different sound for empty submission
                    self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
                self.player_name_input_cache = "" # Clear cache after attempt
            elif event.key == pygame.K_BACKSPACE:
                self.player_name_input_cache = self.player_name_input_cache[:-1]
                play_sound_func('ui_select', 0.4) # Softer sound for backspace
            elif len(self.player_name_input_cache) < 6 and event.unicode.isalpha():
                self.player_name_input_cache += event.unicode.upper()
                play_sound_func('ui_select', 0.5) # Sound for typing
            return True
        return False

    def _handle_game_over_input(self, event, play_sound_func):
        if event.type == pygame.KEYDOWN:
            can_submit = not gs.SETTINGS_MODIFIED
            is_high = leaderboard.is_high_score(self.game_controller.score, self.game_controller.level)
            
            if can_submit and is_high:
                play_sound_func('ui_confirm') # Sound for proceeding to name entry
                self.scene_manager.set_game_state(GAME_STATE_ENTER_NAME)
            elif event.key == pygame.K_r:
                play_sound_func('ui_confirm')
                self.scene_manager.set_game_state(GAME_STATE_GAME_INTRO_SCROLL)
            elif event.key == pygame.K_l:
                play_sound_func('ui_select')
                self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
            elif event.key == pygame.K_m:
                play_sound_func('ui_select')
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            elif event.key == pygame.K_q:
                self.game_controller.quit_game()
            return True
        return False

    def _handle_game_intro_input(self, event, play_sound_func):
        if event.type == pygame.KEYDOWN:
            if self.intro_sequence_finished:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    play_sound_func('ui_confirm')
                    # GameController handles the actual game session initialization
                    self.game_controller.initialize_specific_game_mode("standard_play")
            else: # Intro not finished, skip current screen
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_ESCAPE:
                    play_sound_func('ui_select', 0.5)
                    self.skip_current_intro_screen()
            return True
        return False

    def _handle_vault_result_input(self, event, play_sound_func):
        """Handles input for Architect Vault Success/Failure screens."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_m:
                play_sound_func('ui_confirm')
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
                return True
        return False

    # --- Scene Initialization/Data Population Methods ---
    def initialize_main_menu(self):
        self.selected_menu_option = 0

    def initialize_drone_select(self):
        current_selected_id = self.drone_system.get_selected_drone_id()
        try: self.selected_drone_preview_index = self.drone_select_options.index(current_selected_id)
        except ValueError: self.selected_drone_preview_index = 0

    def initialize_settings(self, settings_data_from_gc):
        self.settings_items_data = settings_data_from_gc
        self.selected_setting_index = 0

    def initialize_leaderboard(self):
        self.leaderboard_scores = leaderboard.load_scores()

    def initialize_enter_name(self):
        self.player_name_input_cache = ""

    def initialize_codex(self):
        self.codex_current_view = "categories"
        self.codex_selected_category_index = 0
        self.codex_current_category_name = None
        self.codex_selected_entry_id = None
        self.codex_content_scroll_offset = 0
        self._populate_codex_categories()

    def _populate_codex_categories(self):
        if not self.drone_system or not self.drone_system.all_lore_entries:
            self.codex_categories_list = []; return
        unlocked_ids = self.drone_system.get_unlocked_lore_ids()
        all_lore = self.drone_system.get_all_loaded_lore_entries()
        self.codex_categories_list = sorted(list(set(
            entry.get("category", "Misc") for id, entry in all_lore.items() if id in unlocked_ids and entry
        )))
        if not self.codex_categories_list and unlocked_ids: self.codex_categories_list = ["Misc"]

    def _populate_codex_entries_for_category(self):
        if not self.drone_system or not self.codex_current_category_name:
            self.codex_entries_in_category_list = []; return
        unlocked_ids = self.drone_system.get_unlocked_lore_ids()
        all_lore = self.drone_system.get_all_loaded_lore_entries()
        self.codex_entries_in_category_list = []
        for id in unlocked_ids:
            entry_data = all_lore.get(id)
            if entry_data and entry_data.get("category", "Misc") == self.codex_current_category_name:
                self.codex_entries_in_category_list.append(entry_data)
        self.codex_entries_in_category_list.sort(key=lambda e: e.get("title", "Untitled"))

    def initialize_game_intro(self, intro_data_from_gc):
        self.intro_screens_data = intro_data_from_gc
        self.current_intro_screen_index = 0
        self.intro_sequence_finished = False
        self.intro_screen_start_time = pygame.time.get_ticks() 

    def advance_intro_screen(self):
        self.current_intro_screen_index += 1
        if not self.intro_screens_data or self.current_intro_screen_index >= len(self.intro_screens_data):
            self.intro_sequence_finished = True
        else:
            self.intro_screen_start_time = pygame.time.get_ticks()

    def skip_current_intro_screen(self):
        if not self.intro_sequence_finished:
            self.advance_intro_screen()
            if not self.intro_screens_data or self.current_intro_screen_index >= len(self.intro_screens_data):
                self.intro_sequence_finished = True
    
    def initialize_architect_vault_result_screen(self, success, failure_reason=""):
        """Sets up messages for the vault success/failure screens."""
        if success:
            self.architect_vault_result_message = "Vault Conquered! Blueprint Acquired!"
            self.architect_vault_result_message_color = gs.GOLD
        else:
            self.architect_vault_result_message = f"Vault Mission Failed: {failure_reason}"
            self.architect_vault_result_message_color = gs.RED
        # UIManager will use these to draw the screen.

    def reset_ui_flow_states(self):
        self.selected_menu_option = 0
        self.selected_drone_preview_index = 0
        self.selected_setting_index = 0
        self.player_name_input_cache = ""
        self.initialize_codex() 
        # Game intro data is static, but its progression state needs reset
        self.current_intro_screen_index = 0
        self.intro_sequence_finished = False
        self.intro_screen_start_time = 0
        self.architect_vault_result_message = ""
        print("UIFlowController: UI states reset.")

