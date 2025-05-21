import pygame
import os
from game_settings import (
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_BONUS_LEVEL_START, GAME_STATE_BONUS_LEVEL_PLAYING, 
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, 
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE
)

class SceneManager:
    def __init__(self, game_controller_ref):
        """
        Initializes the SceneManager.
        Args:
            game_controller_ref: A reference to the main game controller/loop instance,
                                 used to call initialization methods for different scenes.
        """
        self.current_state = GAME_STATE_MAIN_MENU
        self.game_controller = game_controller_ref # Reference to the main game logic class

        # Music paths (can be moved to an AudioManager later if preferred)
        self.menu_music_path = os.path.join("assets", "sounds", "menu_logo.wav")
        self.gameplay_music_path = os.path.join("assets", "sounds", "background_music.wav")
        self.architect_vault_music_path = os.path.join("assets", "sounds", "architect_vault_theme.wav") # Placeholder
        self.current_music_context = None
        
        # Initial music play
        self._update_music()


    def get_current_state(self):
        return self.current_state

    def _play_music(self, music_path, context_label, volume=0.5, loops=-1):
        """Helper function to play music, checking if path exists."""
        if not music_path or not os.path.exists(music_path):
            print(f"Music file not found or path is None: {music_path}. Skipping playback for context {context_label}.")
            if self.current_music_context == context_label: # If it was supposed to play this, stop current music
                pygame.mixer.music.stop()
                self.current_music_context = None
            return
            
        try:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=loops)
            self.current_music_context = context_label
        except pygame.error as e:
            print(f"Error playing music '{music_path}': {e}")

    def _update_music(self):
        """Plays music based on the current game state."""
        music_map = {
            GAME_STATE_MAIN_MENU: (self.menu_music_path, "menu"),
            GAME_STATE_PLAYING: (self.gameplay_music_path, "gameplay"),
            GAME_STATE_LEADERBOARD: (self.menu_music_path, "menu"),
            GAME_STATE_ENTER_NAME: (self.menu_music_path, "menu"),
            GAME_STATE_GAME_OVER: (self.menu_music_path, "menu"),
            GAME_STATE_SETTINGS: (self.menu_music_path, "menu"),
            GAME_STATE_DRONE_SELECT: (self.menu_music_path, "menu"),
            GAME_STATE_BONUS_LEVEL_START: (self.gameplay_music_path, "gameplay"),
            GAME_STATE_BONUS_LEVEL_PLAYING: (self.gameplay_music_path, "gameplay"),
            GAME_STATE_ARCHITECT_VAULT_INTRO: (self.architect_vault_music_path, "architect_vault"),
            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: (self.architect_vault_music_path, "architect_vault"),
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET: (self.architect_vault_music_path, "architect_vault_action"),
            GAME_STATE_ARCHITECT_VAULT_EXTRACTION: (self.architect_vault_music_path, "architect_vault_action"),
            GAME_STATE_ARCHITECT_VAULT_SUCCESS: (self.menu_music_path, "menu"),
            GAME_STATE_ARCHITECT_VAULT_FAILURE: (self.menu_music_path, "menu")
        }
        
        music_info = music_map.get(self.current_state)
        is_playing_state = self.current_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
                           self.current_state.startswith("architect_vault")

        if music_info:
            path, context = music_info
            if self.current_music_context != context or not pygame.mixer.music.get_busy():
                self._play_music(path, context)
            elif is_playing_state and self.game_controller.paused: # Check paused status via game_controller
                 pass # Music should already be paused by game_controller
            elif is_playing_state and not self.game_controller.paused:
                 pygame.mixer.music.unpause()


    def set_game_state(self, new_state):
        """
        Sets the current game state and calls relevant initialization methods
        on the game_controller.
        """
        if self.current_state == new_state:
            # Allow re-triggering for paused states if unpausing
            is_playing_state = new_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
                               new_state.startswith("architect_vault")
            if not (is_playing_state and self.game_controller.paused): # game_controller will have a 'paused' attribute
                return

        old_state = self.current_state
        self.current_state = new_state
        print(f"SceneManager: Game state changed from {old_state} to: {self.current_state}")

        self._update_music() # Update music based on the new state

        # Call initialization methods on the game_controller based on the new state
        if self.current_state == GAME_STATE_MAIN_MENU:
            if hasattr(self.game_controller, 'initialize_main_menu_scene'): # Example method name
                self.game_controller.initialize_main_menu_scene()
        elif self.current_state == GAME_STATE_PLAYING:
            # This might be called by initialize_game_session in game_controller
            pass
        elif self.current_state == GAME_STATE_DRONE_SELECT:
            if hasattr(self.game_controller, 'initialize_drone_select_scene'):
                self.game_controller.initialize_drone_select_scene()
        elif self.current_state == GAME_STATE_SETTINGS:
             if hasattr(self.game_controller, 'initialize_settings_scene'):
                self.game_controller.initialize_settings_scene()
        elif self.current_state == GAME_STATE_LEADERBOARD:
            if hasattr(self.game_controller, 'initialize_leaderboard_scene'):
                self.game_controller.initialize_leaderboard_scene()
        
        # Architect's Vault specific initializations (delegated to game_controller)
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            if hasattr(self.game_controller, 'initialize_architect_vault_session'):
                self.game_controller.initialize_architect_vault_session() 
            if hasattr(self.game_controller, 'start_architect_vault_intro'):
                self.game_controller.start_architect_vault_intro()

        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            if hasattr(self.game_controller, 'start_architect_vault_entry_puzzle'):
                self.game_controller.start_architect_vault_entry_puzzle()

        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_GAUNTLET:
            if hasattr(self.game_controller, 'start_architect_vault_gauntlet'):
                self.game_controller.start_architect_vault_gauntlet()
        
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_EXTRACTION:
            if hasattr(self.game_controller, 'start_architect_vault_extraction'):
                self.game_controller.start_architect_vault_extraction()

        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS:
            if hasattr(self.game_controller, 'handle_architect_vault_success'):
                self.game_controller.handle_architect_vault_success()
        
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
            if hasattr(self.game_controller, 'handle_architect_vault_failure'):
                self.game_controller.handle_architect_vault_failure()
        
        elif self.current_state == GAME_STATE_GAME_OVER:
            if hasattr(self.game_controller, 'handle_game_over'):
                self.game_controller.handle_game_over()
        
        elif self.current_state == GAME_STATE_ENTER_NAME:
            if hasattr(self.game_controller, 'initialize_enter_name_scene'):
                self.game_controller.initialize_enter_name_scene()


    def update(self):
        """
        Called every frame. Can be used for scene-specific timed transitions
        or checks if not handled by the game_controller's state updates.
        For example, transitioning from ARCHITECT_VAULT_INTRO after a delay.
        """
        current_time = pygame.time.get_ticks()

        # Example: Transition from intro states after a message timer
        if self.current_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            if hasattr(self.game_controller, 'architect_vault_message_timer'):
                if current_time > self.game_controller.architect_vault_message_timer:
                    self.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        # Other timed transitions within scenes could be managed here or within game_controller
