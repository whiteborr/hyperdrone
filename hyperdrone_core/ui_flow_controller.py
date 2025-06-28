# hyperdrone_core/ui_flow_controller.py
from pygame.time import get_ticks
from pygame.key import name as key_name
from pygame import K_UP, K_DOWN, K_LEFT, K_RIGHT, K_RETURN, K_SPACE, K_ESCAPE, K_BACKSPACE, K_w, K_s, K_a, K_d, K_r, K_l, K_m, K_q
from random import randint, uniform
from logging import getLogger, info

from settings_manager import get_setting, set_setting, save_settings
from constants import (
    WHITE, GOLD, RED,
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
    GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, GAME_STATE_CODEX,
    GAME_STATE_PLAYING, GAME_STATE_MAZE_DEFENSE, GAME_STATE_GAME_INTRO_SCROLL,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE
)
from ui.leaderboard_ui import add_score, is_high_score, load_scores

logger = getLogger(__name__)

class UIFlowController:
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        self.scene_manager = None
        self.ui_manager = None
        self.drone_system = None
        
        # Menu state
        self.menu_options = ["Start Game", "Select Drone", "Weapon Upgrade Shop", "Codex", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0
        self.menu_stars = self._create_stars(200)

        # Drone selection
        self.drone_select_options = []
        self.selected_drone_preview_index = 0

        # Settings
        self.settings_items_data = []
        self.selected_setting_index = 0

        # Name input
        self.player_name_input_cache = ""
        self.game_over_acknowledged = False
        
        # Codex
        self.codex_categories_list = []
        self.codex_current_view = "categories"
        self.codex_selected_category_index = 0
        self.codex_current_category_name = ""
        self.codex_entries_in_category_list = []
        self.codex_selected_entry_index_in_category = 0
        self.codex_selected_entry_id = None
        self.codex_content_scroll_offset = 0
        self.codex_current_entry_total_lines = 0

        # Vault result
        self.architect_vault_result_message = ""
        self.architect_vault_result_message_color = WHITE

        # Intro
        self.intro_screens_data = []
        self.current_intro_screen_index = 0
        self.intro_screen_start_time = 0
        self.intro_sequence_finished = False
        
        # Leaderboard
        self.leaderboard_scores = []

    def set_dependencies(self, scene_manager, ui_manager, drone_system):
        self.scene_manager = scene_manager
        self.ui_manager = ui_manager
        self.drone_system = drone_system

    def handle_key_input(self, key, current_game_state):
        state_handlers = {
            GAME_STATE_MAIN_MENU: self._handle_main_menu_input,
            GAME_STATE_DRONE_SELECT: self._handle_drone_select_input,
            "drone_select": self._handle_drone_select_input,
            GAME_STATE_SETTINGS: self._handle_settings_input,
            "SettingsState": self._handle_settings_input,
            GAME_STATE_LEADERBOARD: self._handle_leaderboard_input,
            GAME_STATE_CODEX: self._handle_codex_input,
            GAME_STATE_ENTER_NAME: self._handle_enter_name_input,
            GAME_STATE_GAME_OVER: self._handle_game_over_input,
            GAME_STATE_ARCHITECT_VAULT_SUCCESS: self._handle_vault_result_input,
            GAME_STATE_ARCHITECT_VAULT_FAILURE: self._handle_vault_result_input,
            GAME_STATE_GAME_INTRO_SCROLL: self._handle_game_intro_input
        }
        
        handler = state_handlers.get(current_game_state)
        return handler(key) if handler else False

    def update(self, current_time_ms, delta_time_ms, current_game_state):
        menu_states = [
            "MainMenuState", "LeaderboardState", "SettingsState",
            "DroneSelectState", "CodexState", "GameOverState", "EnterNameState"
        ]
        
        if current_game_state in menu_states and self.menu_stars:
            height = get_setting("display", "HEIGHT", 1080)
            width = get_setting("display", "WIDTH", 1920)
            for star in self.menu_stars:
                star[1] += star[2] * (delta_time_ms / 1000.0)
                if star[1] > height:
                    star[0] = randint(0, width)
                    star[1] = 0

    def _create_stars(self, num_stars):
        stars = []
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        for _ in range(num_stars):
            x = randint(0, width)
            y = randint(0, height)
            speed = uniform(10, 50)
            size = uniform(0.5, 2)
            stars.append([x, y, speed, size])
        return stars

    def initialize_main_menu(self, selected_option=0):
        self.selected_menu_option = selected_option
        if hasattr(self.game_controller, 'combat_controller'):
            self.game_controller.combat_controller.reset_combat_state()

    def initialize_drone_select(self):
        if not self.drone_system:
            return
        self.drone_select_options = self.drone_system.get_all_drone_ids_in_order()
        current_id = self.drone_system.get_selected_drone_id()
        self.selected_drone_preview_index = (
            self.drone_select_options.index(current_id) 
            if current_id in self.drone_select_options else 0
        )

    def initialize_settings(self, settings_data):
        self.settings_items_data = settings_data
        self.selected_setting_index = 0

    def initialize_leaderboard(self):
        self.leaderboard_scores = load_scores()

    def initialize_codex(self):
        if not self.drone_system:
            return
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
        self.intro_screen_start_time = get_ticks()
        self.intro_sequence_finished = False

    def reset_ui_flow_states(self):
        self.selected_menu_option = 0
        self.selected_drone_preview_index = 0
        self.selected_setting_index = 0
        self.player_name_input_cache = ""
        self.game_over_acknowledged = False
        self.codex_current_view = "categories"
        self.codex_selected_category_index = 0
        self.codex_content_scroll_offset = 0
        
    def _handle_main_menu_input(self, key):
        if key in (K_UP, K_w):
            self.selected_menu_option = (self.selected_menu_option - 1) % len(self.menu_options)
            self.game_controller.play_sound('ui_select')
            return True
        elif key in (K_DOWN, K_s):
            self.selected_menu_option = (self.selected_menu_option + 1) % len(self.menu_options)
            self.game_controller.play_sound('ui_select')
            return True
        elif key in (K_RETURN, K_SPACE):
            selected_action = self.menu_options[self.selected_menu_option]
            self.game_controller.play_sound('ui_confirm')
            
            action_map = {
                "Start Game": GAME_STATE_GAME_INTRO_SCROLL,
                "Select Drone": GAME_STATE_DRONE_SELECT,
                "Weapon Upgrade Shop": "WeaponsUpgradeShopState",
                "Settings": GAME_STATE_SETTINGS,
                "Leaderboard": GAME_STATE_LEADERBOARD,
                "Codex": GAME_STATE_CODEX,
                "Quit": None
            }
            
            if selected_action == "Quit":
                self.game_controller.quit_game()
            else:
                self.scene_manager.set_state(action_map[selected_action])
            return True
        return False

    def _handle_drone_select_input(self, key):
        if not self.drone_select_options:
            return False
        
        num_options = len(self.drone_select_options)
        
        if key in (K_LEFT, K_a):
            self.selected_drone_preview_index = (self.selected_drone_preview_index - 1) % num_options
            self.game_controller.play_sound('ui_select')
            return True
        elif key in (K_RIGHT, K_d):
            self.selected_drone_preview_index = (self.selected_drone_preview_index + 1) % num_options
            self.game_controller.play_sound('ui_select')
            return True
        elif key in (K_RETURN, K_SPACE):
            selected_id = self.drone_select_options[self.selected_drone_preview_index]
            
            if self.drone_system.is_drone_unlocked(selected_id):
                self.drone_system.set_selected_drone(selected_id)
                self.game_controller.play_sound('ui_confirm')
                if hasattr(self.ui_manager, 'update_player_life_icon_surface'):
                    self.ui_manager.update_player_life_icon_surface()
                
                drone_select_index = (
                    self.menu_options.index("Select Drone") 
                    if "Select Drone" in self.menu_options else 0
                )
                self.scene_manager.set_state(GAME_STATE_MAIN_MENU, selected_option=drone_select_index)
            else:
                unlock_result = self.drone_system.unlock_drone(selected_id)
                sound = 'lore_unlock' if unlock_result else 'ui_denied'
                self.game_controller.play_sound(sound)
            return True
        return False

    def _handle_settings_input(self, key):
        if not self.settings_items_data:
            return False
            
        selected_item = self.settings_items_data[self.selected_setting_index]
        
        if key in (K_UP, K_w):
            self.selected_setting_index = (self.selected_setting_index - 1) % len(self.settings_items_data)
            self.game_controller.play_sound('ui_select', 0.5)
            return True
        elif key in (K_DOWN, K_s):
            self.selected_setting_index = (self.selected_setting_index + 1) % len(self.settings_items_data)
            self.game_controller.play_sound('ui_select', 0.5)
            return True
        elif key == K_RETURN:
            return self._handle_setting_action(selected_item)
        elif key in (K_LEFT, K_a, K_RIGHT, K_d):
            direction = -1 if key in (K_LEFT, K_a) else 1
            return self._handle_setting_change(selected_item, direction)
        
        return False

    def _handle_setting_action(self, selected_item):
        if selected_item["type"] == "action":
            if selected_item["key"] == "RESET_SETTINGS_ACTION":
                from settings_manager import reset_all_settings_to_default
                reset_all_settings_to_default()
                self.game_controller.lives = get_setting("gameplay", "PLAYER_LIVES", 3)
                self.settings_items_data = self.game_controller._get_settings_menu_items_data_structure()
                self.game_controller.play_sound('ui_confirm')
            return True
        elif selected_item.get("action") == "start_chapter" and selected_item["type"] == "choice":
            category = selected_item.get("category", "testing")
            current_val = get_setting(category, selected_item["key"])
            if current_val:
                try:
                    chapter_num = int(current_val.split("_")[1]) - 1
                    set_setting(category, selected_item["key"], current_val)
                    self._start_selected_chapter(chapter_num)
                    self.game_controller.play_sound('ui_confirm')
                except (ValueError, IndexError):
                    self.game_controller.play_sound('ui_denied')
            return True
        return False

    def _handle_setting_change(self, selected_item, direction):
        category = selected_item.get("category", "gameplay")
        key = selected_item["key"]
        current_val = get_setting(category, key)
        
        if selected_item["type"] == "numeric":
            step = selected_item.get("step", 1)
            current_val = current_val if current_val is not None else selected_item.get("min", 0)
            new_val = max(selected_item["min"], min(selected_item["max"], current_val + direction * step))
            set_setting(category, key, new_val)
            self._handle_special_settings(key, new_val)
            
        elif selected_item["type"] == "choice":
            choices = selected_item["choices"]
            try:
                if current_val not in choices:
                    new_idx = 0 if direction > 0 else len(choices) - 1
                else:
                    current_idx = choices.index(current_val)
                    new_idx = (current_idx + direction) % len(choices)
                set_setting(category, key, choices[new_idx])
                self._handle_special_settings(key, choices[new_idx])
            except (ValueError, TypeError):
                if choices:
                    set_setting(category, key, choices[0])
                    self._handle_special_settings(key, choices[0])
        
        return True

    def _handle_special_settings(self, key, value):
        if key == "PLAYER_LIVES":
            self.game_controller.lives = value
            self.game_controller.play_sound('ui_select')
        elif key == "VOLUME_FX":
            self.game_controller.play_sound('shoot', volume_override=value/10.0)
            save_settings()
        elif key == "VOLUME_GAME":
            if hasattr(self.game_controller, 'state_manager'):
                self.game_controller.state_manager._update_music()
            save_settings()
        else:
            self.game_controller.play_sound('ui_select')
        
    def _start_selected_chapter(self, chapter_index):
        if not hasattr(self.game_controller, 'story_manager'):
            return
            
        story_manager = self.game_controller.story_manager
        
        if 0 <= chapter_index < len(story_manager.chapters):
            story_manager.current_chapter_index = chapter_index
            story_manager._apply_chapter_prerequisites(chapter_index)
            if self.scene_manager:
                self.scene_manager.set_state("StoryMapState")

    def _handle_leaderboard_input(self, key):
        if key in (K_RETURN, K_q, K_ESCAPE):
            leaderboard_index = (
                self.menu_options.index("Leaderboard") 
                if "Leaderboard" in self.menu_options else 0
            )
            self.scene_manager.set_state(GAME_STATE_MAIN_MENU, selected_option=leaderboard_index)
            return True
        return False

    def _handle_codex_input(self, key):
        if self.codex_current_view == "categories":
            return self._handle_codex_categories_input(key)
        elif self.codex_current_view == "entries":
            return self._handle_codex_entries_input(key)
        elif self.codex_current_view == "content":
            return self._handle_codex_content_input(key)
        return False

    def _handle_codex_categories_input(self, key):
        if key == K_ESCAPE:
            codex_index = self.menu_options.index("Codex") if "Codex" in self.menu_options else 0
            self.scene_manager.set_state(GAME_STATE_MAIN_MENU, selected_option=codex_index)
        elif key in (K_UP, K_w):
            self.codex_selected_category_index = (self.codex_selected_category_index - 1) % len(self.codex_categories_list) if self.codex_categories_list else 0
        elif key in (K_DOWN, K_s):
            self.codex_selected_category_index = (self.codex_selected_category_index + 1) % len(self.codex_categories_list) if self.codex_categories_list else 0
        elif key == K_RETURN and self.codex_categories_list:
            self.codex_current_view = "entries"
            self.codex_current_category_name = self.codex_categories_list[self.codex_selected_category_index]
            self.codex_entries_in_category_list = self.drone_system.get_unlocked_lore_entries_by_category(self.codex_current_category_name)
            self.codex_selected_entry_index_in_category = 0
        
        self.game_controller.play_sound('ui_select', 0.5)
        return True

    def _handle_codex_entries_input(self, key):
        if key == K_ESCAPE:
            self.codex_current_view = "categories"
        elif key in (K_UP, K_w):
            self.codex_selected_entry_index_in_category = (self.codex_selected_entry_index_in_category - 1) % len(self.codex_entries_in_category_list) if self.codex_entries_in_category_list else 0
        elif key in (K_DOWN, K_s):
            self.codex_selected_entry_index_in_category = (self.codex_selected_entry_index_in_category + 1) % len(self.codex_entries_in_category_list) if self.codex_entries_in_category_list else 0
        elif key == K_RETURN and self.codex_entries_in_category_list:
            self.codex_current_view = "content"
            self.codex_selected_entry_id = self.codex_entries_in_category_list[self.codex_selected_entry_index_in_category]['id']
            self.codex_content_scroll_offset = 0
        
        self.game_controller.play_sound('ui_select', 0.5)
        return True

    def _handle_codex_content_input(self, key):
        if key == K_ESCAPE:
            self.codex_current_view = "entries"
        elif key in (K_UP, K_w):
            self.codex_content_scroll_offset = max(0, self.codex_content_scroll_offset - 1)
        elif key in (K_DOWN, K_s):
            self.codex_content_scroll_offset = min(max(0, self.codex_current_entry_total_lines - 10), self.codex_content_scroll_offset + 1)
        
        self.game_controller.play_sound('ui_select', 0.5)
        return True

    def _handle_enter_name_input(self, key):
        if key == K_RETURN:
            if len(self.player_name_input_cache) > 0:
                add_score(self.player_name_input_cache, self.game_controller.score, self.game_controller.level)
                self.scene_manager.set_state(GAME_STATE_LEADERBOARD)
            return True
        elif key == K_BACKSPACE:
            self.player_name_input_cache = self.player_name_input_cache[:-1]
            return True
        elif len(self.player_name_input_cache) < 6:
            try:
                char = key_name(key).upper()
                if len(char) == 1 and char.isalpha():
                    self.player_name_input_cache += char
                    return True
            except:
                pass
        return False

    def _handle_game_over_input(self, key):
        score_is_high = is_high_score(self.game_controller.score, self.game_controller.level)
        settings_modified = get_setting("gameplay", "SETTINGS_MODIFIED", False)
        
        if score_is_high and not settings_modified:
            self.scene_manager.set_state(GAME_STATE_ENTER_NAME)
        else:
            actions = {
                K_r: (GAME_STATE_PLAYING, {"action": "restart"}),
                K_l: (GAME_STATE_LEADERBOARD, {}),
                K_m: (GAME_STATE_MAIN_MENU, {}),
                K_q: (None, {})
            }
            
            if key in actions:
                state, kwargs = actions[key]
                if state:
                    self.scene_manager.set_state(state, **kwargs)
                else:
                    self.game_controller.quit_game()
        return True

    def _handle_vault_result_input(self, key):
        if key in (K_RETURN, K_m, K_SPACE):
            self.scene_manager.set_state(GAME_STATE_MAIN_MENU)
            return True
        return False
        
    def _handle_game_intro_input(self, key):
        if key in (K_SPACE, K_RETURN):
            if self.current_intro_screen_index >= len(self.intro_screens_data) - 1:
                self.intro_sequence_finished = True
            else:
                self.current_intro_screen_index += 1
                self.intro_screen_start_time = get_ticks()
            return True
        elif key == K_ESCAPE:
            settings_index = self.menu_options.index("Settings") if "Settings" in self.menu_options else 0
            self.scene_manager.set_state(GAME_STATE_MAIN_MENU, selected_option=settings_index)
            return True
        return False

    def advance_intro_screen(self):
        if self.current_intro_screen_index >= len(self.intro_screens_data) - 1:
            self.intro_sequence_finished = True
        else:
            self.current_intro_screen_index += 1
            self.intro_screen_start_time = get_ticks()
            
    def skip_intro(self):
        self.intro_sequence_finished = True