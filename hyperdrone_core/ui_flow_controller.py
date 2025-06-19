# hyperdrone_core/ui_flow_controller.py
import pygame
import random
import logging

from settings_manager import get_setting
from constants import (
    WHITE, GOLD, RED,
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
    GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, GAME_STATE_CODEX,
    GAME_STATE_PLAYING, GAME_STATE_MAZE_DEFENSE, GAME_STATE_GAME_INTRO_SCROLL,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    KEY_DEFEATED_BOSSES
)
from . import leaderboard

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
        
        self.menu_options = ["Start Game", "Maze Defense", "Select Drone", "Codex", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0
        self.menu_stars = self._create_stars(200)

        self.drone_select_options = []
        self.selected_drone_preview_index = 0

        self.settings_items_data = []
        self.selected_setting_index = 0

        self.player_name_input_cache = ""
        self.game_over_acknowledged = False
        
        self.codex_categories_list = []
        self.codex_current_view = "categories"
        self.codex_selected_category_index = 0
        self.codex_current_category_name = ""
        self.codex_entries_in_category_list = []
        self.codex_selected_entry_index_in_category = 0
        self.codex_selected_entry_id = None
        self.codex_content_scroll_offset = 0
        self.codex_current_entry_total_lines = 0

        self.architect_vault_result_message = ""
        self.architect_vault_result_message_color = WHITE

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
        """
        state_handlers = {
            GAME_STATE_MAIN_MENU: self._handle_main_menu_input,
            GAME_STATE_DRONE_SELECT: self._handle_drone_select_input,
            GAME_STATE_SETTINGS: self._handle_settings_input,
            "SettingsState": self._handle_settings_input,  # Add support for string-based state name
            GAME_STATE_LEADERBOARD: self._handle_leaderboard_input,
            GAME_STATE_CODEX: self._handle_codex_input,
            GAME_STATE_ENTER_NAME: self._handle_enter_name_input,
            GAME_STATE_GAME_OVER: self._handle_game_over_input,
            GAME_STATE_ARCHITECT_VAULT_SUCCESS: self._handle_vault_result_input,
            GAME_STATE_ARCHITECT_VAULT_FAILURE: self._handle_vault_result_input,
            GAME_STATE_GAME_INTRO_SCROLL: self._handle_game_intro_input
        }
        
        handler = state_handlers.get(current_game_state)
        if handler:
            return handler(key)
        
        return False

    def update(self, current_time_ms, delta_time_ms, current_game_state):
        """Called every frame to update UI animations or timed transitions."""
        # MODIFICATION: Use class names for state IDs to match the StateManager.
        menu_like_states = [
            "MainMenuState", "LeaderboardState", "SettingsState",
            "DroneSelectState", "CodexState", "GameOverState", "EnterNameState"
        ]
        
        if current_game_state in menu_like_states:
            if self.menu_stars:
                height = get_setting("display", "HEIGHT", 1080)
                width = get_setting("display", "WIDTH", 1920)
                for star in self.menu_stars:
                    # Update star position
                    star[1] += star[2] * (delta_time_ms / 1000.0)
                    # Reset star if it goes off-screen
                    if star[1] > height:
                        star[0] = random.randint(0, width)
                        star[1] = 0

    def _create_stars(self, num_stars):
        """Helper to create a list of star parameters for background effects."""
        stars = []
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        for _ in range(num_stars):
            x = random.randint(0, width)
            y = random.randint(0, height)
            speed = random.uniform(10, 50)
            size = random.uniform(0.5, 2)
            stars.append([x, y, speed, size])
        return stars

    def initialize_main_menu(self):
        self.selected_menu_option = 0
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
        self.leaderboard_scores = leaderboard.load_scores()

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
            self.architect_vault_result_message_color = GOLD
        else:
            self.architect_vault_result_message = "MISSION FAILED"
            self.architect_vault_result_message_color = RED
        if hasattr(self.game_controller, 'architect_vault_failure_reason'):
            self.game_controller.architect_vault_failure_reason = failure_reason

    def initialize_game_intro(self, intro_data):
        self.intro_screens_data = intro_data
        self.current_intro_screen_index = 0
        self.intro_screen_start_time = pygame.time.get_ticks()
        self.intro_sequence_finished = False

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
            if selected_action == "Start Game": self.scene_manager.set_state(GAME_STATE_GAME_INTRO_SCROLL)
            elif selected_action == "Maze Defense": self.scene_manager.set_state(GAME_STATE_MAZE_DEFENSE)
            elif selected_action == "Select Drone": self.scene_manager.set_state(GAME_STATE_DRONE_SELECT)
            elif selected_action == "Settings": self.scene_manager.set_state(GAME_STATE_SETTINGS)
            elif selected_action == "Leaderboard": self.scene_manager.set_state(GAME_STATE_LEADERBOARD)
            elif selected_action == "Codex": self.scene_manager.set_state(GAME_STATE_CODEX)
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
                self.scene_manager.set_state(GAME_STATE_MAIN_MENU)
            else:
                if self.drone_system.unlock_drone(selected_id):
                    self.game_controller.play_sound('lore_unlock')
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
        elif key == pygame.K_RETURN:
            if selected_item["type"] == "action":
                if item_key == "RESET_SETTINGS_ACTION":
                    # Reset settings to defaults
                    from settings_manager import reset_all_settings_to_default
                    reset_all_settings_to_default()
                    # Reinitialize settings menu to reflect changes
                    self.settings_items_data = self.game_controller._get_settings_menu_items_data_structure()
                    self.game_controller.play_sound('ui_confirm')
                return True
            elif selected_item.get("action") == "start_chapter" and selected_item["type"] == "choice":
                # Handle chapter selection
                category = selected_item.get("category", "testing")
                current_val = get_setting(category, item_key)
                if current_val:
                    # Extract chapter number from chapter_id (e.g., "chapter_2" -> 2)
                    try:
                        chapter_num = int(current_val.split("_")[1]) - 1
                        # Save the selected chapter setting before starting it
                        from settings_manager import set_setting
                        set_setting(category, item_key, current_val)
                        self._start_selected_chapter(chapter_num)
                        self.game_controller.play_sound('ui_confirm')
                    except (ValueError, IndexError):
                        self.game_controller.play_sound('ui_denied')
                return True
        
        direction = 0
        if key == pygame.K_LEFT or key == pygame.K_a: direction = -1
        elif key == pygame.K_RIGHT or key == pygame.K_d: direction = 1
        
        if direction != 0:
            category = selected_item.get("category", "gameplay")
            current_val = get_setting(category, item_key)
            if selected_item["type"] == "numeric":
                step = selected_item.get("step", 1)
                # Handle case where current_val is None
                if current_val is None:
                    current_val = selected_item.get("min", 0)
                new_val = current_val + direction * step
                new_val = max(selected_item["min"], min(new_val, selected_item["max"]))
                from settings_manager import set_setting
                set_setting(category, item_key, new_val)
                self.game_controller.play_sound('ui_select')
            elif selected_item["type"] == "choice":
                choices = selected_item["choices"]
                try:
                    # Handle the case where current_val is not in choices
                    if current_val not in choices:
                        new_idx = 0 if direction > 0 else len(choices) - 1
                    else:
                        current_idx = choices.index(current_val)
                        new_idx = (current_idx + direction) % len(choices)
                    from settings_manager import set_setting
                    set_setting(category, item_key, choices[new_idx])
                    self.game_controller.play_sound('ui_select')
                except (ValueError, TypeError):
                    # If there's any error, just set to the first choice
                    if choices:
                        from settings_manager import set_setting
                        set_setting(category, item_key, choices[0])
                        self.game_controller.play_sound('ui_select')
            return True
        return False
        
    def _start_selected_chapter(self, chapter_index):
        """Set up prerequisites and start the selected chapter."""
        if not hasattr(self.game_controller, 'story_manager'):
            return
            
        story_manager = self.game_controller.story_manager
        
        # Validate chapter index
        if chapter_index < 0 or chapter_index >= len(story_manager.chapters):
            return
            
        # Set the current chapter in the story manager
        story_manager.current_chapter_index = chapter_index
        
        # Set up prerequisites based on chapter
        if chapter_index >= 1:  # Chapter 2 or later
            # Mark all objectives in previous chapters as complete but don't trigger completion logic
            for i in range(chapter_index):
                prev_chapter = story_manager.chapters[i]
                for obj in prev_chapter.objectives:
                    obj.completed = True  # Set directly without calling complete()
                    
            # For Chapter 2 (Guardian), unlock VANTIS drone
            if chapter_index >= 1 and hasattr(self.game_controller, 'drone_system'):
                self.game_controller.drone_system.unlock_drone("VANTIS")
                
            # For Chapter 3 (Corrupted Sector), defeat the Guardian boss
            if chapter_index >= 2:
                if hasattr(self.game_controller, 'drone_system'):
                    # Add the boss to defeated_bosses directly
                    self.game_controller.drone_system.add_defeated_boss("MAZE_GUARDIAN")
                    self.game_controller.drone_system.unlock_drone("STRIX")
                
            # For Chapter 4 (Harvest Chamber), collect core fragments
            if chapter_index >= 3:
                if hasattr(self.game_controller, 'drone_system'):
                    self.game_controller.drone_system.collect_core_fragment("alpha")
                    self.game_controller.drone_system.collect_core_fragment("beta")
                    self.game_controller.drone_system.collect_core_fragment("gamma")
        
        # Start the chapter
        next_state_id = story_manager.chapters[chapter_index].next_state_id
        if next_state_id and self.scene_manager:
            # Use the correct next_state_id from the chapter instead of always defaulting to PlayingState
            self.scene_manager.set_state(next_state_id)

    def _handle_leaderboard_input(self, key):
        if key == pygame.K_RETURN or key == pygame.K_q or key == pygame.K_ESCAPE:
            self.scene_manager.set_state(GAME_STATE_MAIN_MENU)
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
                leaderboard.add_score(self.player_name_input_cache, self.game_controller.score, self.game_controller.level)
                self.scene_manager.set_state(GAME_STATE_LEADERBOARD)
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
        score_is_high = leaderboard.is_high_score(self.game_controller.score, self.game_controller.level)
        settings_modified = get_setting("gameplay", "SETTINGS_MODIFIED", False)
        if score_is_high and not settings_modified:
            self.scene_manager.set_state(GAME_STATE_ENTER_NAME)
        else:
            if key == pygame.K_r: self.scene_manager.set_state(GAME_STATE_PLAYING, action="restart")
            elif key == pygame.K_l: self.scene_manager.set_state(GAME_STATE_LEADERBOARD)
            elif key == pygame.K_m: self.scene_manager.set_state(GAME_STATE_MAIN_MENU)
            elif key == pygame.K_q: self.game_controller.quit_game()
        return True

    def _handle_vault_result_input(self, key):
        if key == pygame.K_RETURN or key == pygame.K_m or key == pygame.K_SPACE:
            self.scene_manager.set_state(GAME_STATE_MAIN_MENU)
            return True
        return False
        
    def _handle_game_intro_input(self, key):
        if key == pygame.K_SPACE or key == pygame.K_RETURN:
            if self.current_intro_screen_index >= len(self.intro_screens_data) - 1:
                self.intro_sequence_finished = True
            else:
                self.current_intro_screen_index += 1
                self.intro_screen_start_time = pygame.time.get_ticks()
            return True
        elif key == pygame.K_ESCAPE:
            self.scene_manager.set_state(GAME_STATE_MAIN_MENU)
            return True
        return False

    def advance_intro_screen(self):
        """Advance to the next intro screen."""
        if self.current_intro_screen_index >= len(self.intro_screens_data) - 1:
            self.intro_sequence_finished = True
        else:
            self.current_intro_screen_index += 1
            self.intro_screen_start_time = pygame.time.get_ticks()
            
    def skip_intro(self):
        """Skip the intro sequence."""
        self.intro_sequence_finished = True