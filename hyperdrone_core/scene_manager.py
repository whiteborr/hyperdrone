import pygame
import os

import game_settings as gs
from game_settings import (
    # Import specific game state constants if used frequently
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_CODEX, # Added GAME_STATE_CODEX
    GAME_STATE_BONUS_LEVEL_START, GAME_STATE_BONUS_LEVEL_PLAYING, 
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, 
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION, 
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE 
    # Other settings will be accessed via gs.get_game_setting() or gs.CONSTANT_NAME
)

class SceneManager:
    def __init__(self, game_controller_ref):
        """
        Initializes the SceneManager.
        Args:
            game_controller_ref: A reference to the main game controller/loop instance,
                                 used to call initialization methods for different scenes
                                 and to check game state (e.g., self.game_controller.paused).
        """
        self.current_state = GAME_STATE_MAIN_MENU # Default starting state
        self.game_controller = game_controller_ref # Reference to the main game logic class

        # Define music paths (these should point to actual files in your assets/sounds directory)
        self.menu_music_path = os.path.join("assets", "sounds", "menu_music.wav") #
        self.gameplay_music_path = os.path.join("assets", "sounds", "gameplay_music.wav") #
        self.architect_vault_music_path = os.path.join("assets", "sounds", "architect_vault_theme.wav") #
        self.current_music_context = None # Tracks which music (menu, gameplay, etc.) is playing or should be

        # Initial music play based on the starting state
        self._update_music() #

    def get_current_state(self): #
        """Returns the current game state string."""
        return self.current_state #

    def _play_music(self, music_path, context_label, volume=0.5, loops=-1): #
        """
        Helper function to load and play music, checking if the path exists.
        """
        if not music_path or not os.path.exists(music_path): #
            print(f"SceneManager: Music file not found or path is None: {music_path}. Skipping playback for context '{context_label}'.") #
            if self.current_music_context == context_label: #
                pygame.mixer.music.stop() #
                self.current_music_context = None #
            return #

        try: #
            pygame.mixer.music.load(music_path) #
            pygame.mixer.music.set_volume(volume) #
            pygame.mixer.music.play(loops=loops) #
            self.current_music_context = context_label #
            print(f"SceneManager: Playing music '{music_path}' for context '{context_label}'.") #
        except pygame.error as e: #
            print(f"SceneManager: Error playing music '{music_path}': {e}") #
            self.current_music_context = None #

    def _update_music(self): #
        """
        Selects and plays the appropriate background music based on the current game state.
        Also handles pausing/unpausing music if the game_controller is paused.
        """
        music_map = {
            GAME_STATE_MAIN_MENU: (self.menu_music_path, "menu_theme"),
            GAME_STATE_DRONE_SELECT: (self.menu_music_path, "menu_theme"),
            GAME_STATE_SETTINGS: (self.menu_music_path, "menu_theme"),
            GAME_STATE_LEADERBOARD: (self.menu_music_path, "menu_theme"),
            GAME_STATE_ENTER_NAME: (self.menu_music_path, "menu_theme"),
            GAME_STATE_GAME_OVER: (self.menu_music_path, "menu_theme"),
            GAME_STATE_CODEX: (self.menu_music_path, "menu_theme"), # Codex uses menu music

            GAME_STATE_PLAYING: (self.gameplay_music_path, "gameplay_theme"),
            GAME_STATE_BONUS_LEVEL_PLAYING: (self.gameplay_music_path, "gameplay_theme"),

            GAME_STATE_ARCHITECT_VAULT_INTRO: (self.architect_vault_music_path, "architect_vault_ambient"),
            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: (self.architect_vault_music_path, "architect_vault_ambient"),
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET: (self.architect_vault_music_path, "architect_vault_action"),
            GAME_STATE_ARCHITECT_VAULT_EXTRACTION: (self.architect_vault_music_path, "architect_vault_action"),

            GAME_STATE_ARCHITECT_VAULT_SUCCESS: (self.menu_music_path, "menu_theme"),
            GAME_STATE_ARCHITECT_VAULT_FAILURE: (self.menu_music_path, "menu_theme")
        } #

        music_info = music_map.get(self.current_state) #
        
        if music_info: #
            path, context = music_info #
            if self.current_music_context != context or not pygame.mixer.music.get_busy(): #
                self._play_music(path, context) #
        else: #
            # If current state has no defined music, stop if it wasn't menu music (which might persist if no other music is defined)
            if self.current_music_context not in [None, "menu_theme"]: #
                 pass # Allow menu music to persist if no other specific music for a minor state

        # Handle pause/unpause based on game_controller's paused state
        if hasattr(self.game_controller, 'paused'): #
            if self.game_controller.paused: #
                if pygame.mixer.music.get_busy(): #
                    pygame.mixer.music.pause() #
            else: # Game is not paused
                # Check if music was paused (not busy but had a position)
                is_music_paused = not pygame.mixer.music.get_busy() and pygame.mixer.music.get_pos() > 0 
                
                # Ensure the context for unpausing matches the current state's expected music context
                current_expected_context = music_map.get(self.current_state, (None, None))[1]
                
                if is_music_paused and self.current_music_context == current_expected_context:
                    pygame.mixer.music.unpause()
                elif not pygame.mixer.music.get_busy() and self.current_music_context: # Music stopped, but should be playing
                    current_path_for_context = music_map.get(self.current_state, (None, None))[0] 
                    if current_path_for_context and self.current_music_context == current_expected_context: 
                        self._play_music(current_path_for_context, self.current_music_context) # Replay if stopped and context is correct
                # If music is busy and volume is up, it's likely already playing/unpaused correctly.

    def set_game_state(self, new_state): #
        """
        Sets the current game state and calls relevant initialization methods
        on the game_controller. Also updates background music.
        """
        if self.current_state == new_state: #
            is_playing_state = new_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
                               new_state.startswith("architect_vault") #
            if not (is_playing_state and hasattr(self.game_controller, 'paused') and self.game_controller.paused): #
                return #

        old_state = self.current_state #
        self.current_state = new_state #
        print(f"SceneManager: Game state changed from '{old_state}' to: '{self.current_state}'") #

        self._update_music() # Update music based on the new state

        # Call game controller's scene-specific initialization methods
        if self.current_state == GAME_STATE_MAIN_MENU: #
            if hasattr(self.game_controller, 'initialize_main_menu_scene'): #
                self.game_controller.initialize_main_menu_scene() #
        elif self.current_state == GAME_STATE_PLAYING: #
            pass # Gameplay initialization is usually part of initialize_game_session
        elif self.current_state == GAME_STATE_DRONE_SELECT: #
            if hasattr(self.game_controller, 'initialize_drone_select_scene'): #
                self.game_controller.initialize_drone_select_scene() #
        elif self.current_state == GAME_STATE_SETTINGS: #
             if hasattr(self.game_controller, 'initialize_settings_scene'): #
                self.game_controller.initialize_settings_scene() #
        elif self.current_state == GAME_STATE_LEADERBOARD: #
            if hasattr(self.game_controller, 'initialize_leaderboard_scene'): #
                self.game_controller.initialize_leaderboard_scene() #
        elif self.current_state == GAME_STATE_CODEX: # New state
            if hasattr(self.game_controller, 'initialize_codex_scene'):
                self.game_controller.initialize_codex_scene()
        elif self.current_state == GAME_STATE_GAME_OVER: #
            if hasattr(self.game_controller, 'handle_game_over_scene_entry'): #
                self.game_controller.handle_game_over_scene_entry() #
        elif self.current_state == GAME_STATE_ENTER_NAME: #
            if hasattr(self.game_controller, 'initialize_enter_name_scene'): #
                self.game_controller.initialize_enter_name_scene() #
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_INTRO: #
            if hasattr(self.game_controller, 'initialize_architect_vault_session'): #
                 if not old_state.startswith("architect_vault"): #
                    self.game_controller.initialize_architect_vault_session() #
            if hasattr(self.game_controller, 'start_architect_vault_intro'): #
                self.game_controller.start_architect_vault_intro() #
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: #
            if hasattr(self.game_controller, 'start_architect_vault_entry_puzzle'): #
                self.game_controller.start_architect_vault_entry_puzzle() #
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_GAUNTLET: #
            if hasattr(self.game_controller, 'start_architect_vault_gauntlet'): #
                self.game_controller.start_architect_vault_gauntlet() #
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_EXTRACTION: #
            if hasattr(self.game_controller, 'start_architect_vault_extraction'): #
                self.game_controller.start_architect_vault_extraction() #
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS: #
            if hasattr(self.game_controller, 'handle_architect_vault_success_scene'): #
                self.game_controller.handle_architect_vault_success_scene() #
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_FAILURE: #
            if hasattr(self.game_controller, 'handle_architect_vault_failure_scene'): #
                self.game_controller.handle_architect_vault_failure_scene() #

    def update(self): #
        """
        Called every frame by the main game loop.
        Can be used for scene-specific timed transitions or checks.
        """
        current_time = pygame.time.get_ticks() #

        if self.current_state == GAME_STATE_ARCHITECT_VAULT_INTRO: #
            if hasattr(self.game_controller, 'architect_vault_message_timer') and \
               hasattr(self.game_controller, 'architect_vault_current_phase') and \
               self.game_controller.architect_vault_current_phase == "intro": #
                if current_time > self.game_controller.architect_vault_message_timer: #
                    self.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE) #
        
        elif self.current_state == GAME_STATE_BONUS_LEVEL_START: #
            if hasattr(self.game_controller, 'bonus_level_start_display_end_time'): #
                 if current_time > self.game_controller.bonus_level_start_display_end_time: #
                    self.set_game_state(GAME_STATE_BONUS_LEVEL_PLAYING) #