# hyperdrone_core/scene_manager.py
import pygame
import os # Keep for os.path.exists check

import game_settings as gs
from game_settings import (
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_CODEX,
    GAME_STATE_BONUS_LEVEL_START, GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_RING_PUZZLE, GAME_STATE_GAME_INTRO_SCROLL, GAME_STATE_MAZE_DEFENSE
)

class SceneManager:
    def __init__(self, game_controller_ref):
        """
        Initializes the SceneManager.
        Args:
            game_controller_ref: A reference to the main game controller instance.
        """
        self.game_controller = game_controller_ref
        self.asset_manager = self.game_controller.asset_manager # Get reference to AssetManager
        self.current_state = GAME_STATE_MAIN_MENU

        # Music paths are now handled by AssetManager. We only need to track the current music's key.
        self.current_music_context_key = None 

        self._update_music() # Initial music play

    def get_current_state(self):
        """Returns the current game state string."""
        return self.current_state

    def _play_music(self, music_key, volume_multiplier_key="MUSIC_VOLUME_MULTIPLIER", loops=-1):
        """Helper function to load and play music using AssetManager."""
        # Get the full file path from the AssetManager using the provided key
        music_path = self.asset_manager.get_music_path(music_key)

        if not music_path or not os.path.exists(music_path):
            print(f"SceneManager: Music file not found for key '{music_key}'.")
            if self.current_music_context_key == music_key:
                pygame.mixer.music.stop()
                self.current_music_context_key = None
            return

        try:
            pygame.mixer.music.load(music_path)
            volume_setting = gs.get_game_setting(volume_multiplier_key, 1.0)
            pygame.mixer.music.set_volume(gs.get_game_setting("MUSIC_BASE_VOLUME", 0.5) * volume_setting)
            pygame.mixer.music.play(loops=loops)
            self.current_music_context_key = music_key # Store the key of the playing music
            print(f"SceneManager: Playing music for context key '{music_key}'.")
        except pygame.error as e:
            print(f"SceneManager: Error playing music '{music_path}': {e}")
            self.current_music_context_key = None

    def _update_music(self):
        """Selects and plays appropriate music based on the current game state and pause status."""
        # This map now uses asset keys for music tracks, defined in GameController's manifest
        music_map = {
            GAME_STATE_MAIN_MENU: "menu_theme",
            GAME_STATE_DRONE_SELECT: "menu_theme",
            GAME_STATE_SETTINGS: "menu_theme",
            GAME_STATE_LEADERBOARD: "menu_theme",
            GAME_STATE_ENTER_NAME: "menu_theme",
            GAME_STATE_GAME_OVER: "menu_theme",
            GAME_STATE_CODEX: "menu_theme",
            GAME_STATE_RING_PUZZLE: "architect_vault_theme",
            GAME_STATE_GAME_INTRO_SCROLL: "menu_theme",

            GAME_STATE_PLAYING: "gameplay_theme",
            GAME_STATE_BONUS_LEVEL_PLAYING: "gameplay_theme",
            
            GAME_STATE_MAZE_DEFENSE: "defense_theme",

            GAME_STATE_ARCHITECT_VAULT_INTRO: "architect_vault_theme",
            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: "architect_vault_theme",
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET: "architect_vault_theme",
            GAME_STATE_ARCHITECT_VAULT_EXTRACTION: "architect_vault_theme",

            GAME_STATE_ARCHITECT_VAULT_SUCCESS: "menu_theme",
            GAME_STATE_ARCHITECT_VAULT_FAILURE: "menu_theme"
        }

        music_key_for_state = music_map.get(self.current_state)

        if music_key_for_state:
            # If the music for the new state is different from what's playing, or if nothing is playing
            if self.current_music_context_key != music_key_for_state or not pygame.mixer.music.get_busy():
                self._play_music(music_key_for_state)
        # else: no specific music for this state, current music continues or stops based on previous state.

        # Handle pause/unpause based on game_controller's paused state
        if hasattr(self.game_controller, 'paused'):
            if self.game_controller.paused:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.pause()
            else: # Game is not paused
                # If music was paused, unpause it
                if not pygame.mixer.music.get_busy() and pygame.mixer.music.get_pos() > 0:
                    pygame.mixer.music.unpause()
                # If music was stopped but should be playing for this context (e.g., after returning to menu)
                elif not pygame.mixer.music.get_busy() and self.current_music_context_key == music_key_for_state:
                    self._play_music(self.current_music_context_key)


    def set_game_state(self, new_state, **kwargs):
        """
        Sets the current game state and notifies the GameController to initialize
        the scene. Also updates background music.
        """
        if self.current_state == new_state:
            # Avoid redundant state changes unless it's a gameplay state being re-entered (e.g., after unpausing)
            is_gameplay_state = new_state in [
                GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, GAME_STATE_MAZE_DEFENSE
            ] or new_state.startswith("architect_vault")
            if not (is_gameplay_state and hasattr(self.game_controller, 'paused') and self.game_controller.paused):
                return

        old_state = self.current_state
        self.current_state = new_state
        print(f"SceneManager: Game state changed from '{old_state}' to: '{self.current_state}'")

        self._update_music() # Update music based on the new state

        if hasattr(self.game_controller, 'handle_scene_transition'):
            self.game_controller.handle_scene_transition(new_state, old_state, **kwargs)
        else:
            print(f"SceneManager: Warning - GameController does not have 'handle_scene_transition' method.")


    def update(self):
        """
        Called every frame by the main game loop for timed transitions or checks.
        """
        current_time = pygame.time.get_ticks()
        current_state = self.get_current_state()

        if current_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            if hasattr(self.game_controller, 'architect_vault_message_timer') and \
               hasattr(self.game_controller, 'architect_vault_current_phase') and \
               self.game_controller.architect_vault_current_phase == "intro":
                if current_time > self.game_controller.architect_vault_message_timer:
                    self.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        
        elif current_state == GAME_STATE_BONUS_LEVEL_START:
            if hasattr(self.game_controller, 'bonus_level_start_display_end_time'):
                 if current_time > self.game_controller.bonus_level_start_display_end_time:
                    self.set_game_state(GAME_STATE_BONUS_LEVEL_PLAYING)
        
        # Music pause/unpause is now handled more robustly in _update_music
        if hasattr(self.game_controller, 'paused') and not self.game_controller.paused:
            self._update_music()

