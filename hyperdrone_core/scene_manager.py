# hyperdrone_core/scene_manager.py
import pygame
import os

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
    # Other settings accessed via gs.get_game_setting() or gs.CONSTANT_NAME
)
# GAME_STATE_MAZE_DEFENSE is now expected to be in game_settings.py

class SceneManager:
    def __init__(self, game_controller_ref):
        """
        Initializes the SceneManager.
        Args:
            game_controller_ref: A reference to the main game controller instance.
        """
        self.current_state = GAME_STATE_MAIN_MENU
        self.game_controller = game_controller_ref

        # Music paths (ensure these point to actual files)
        self.menu_music_path = os.path.join("assets", "sounds", "menu_music.wav")
        self.gameplay_music_path = os.path.join("assets", "sounds", "gameplay_music.wav")
        self.architect_vault_music_path = os.path.join("assets", "sounds", "architect_vault_theme.wav")
        self.defense_music_path = os.path.join("assets", "sounds", "defense_mode_music.wav") # Added for defense mode
        self.current_music_context = None

        self._update_music() # Initial music play

    def get_current_state(self):
        """Returns the current game state string."""
        return self.current_state

    def _play_music(self, music_path, context_label, volume_multiplier_key="MUSIC_VOLUME_MULTIPLIER", loops=-1):
        """Helper function to load and play music, applying volume settings."""
        if not music_path or not os.path.exists(music_path):
            print(f"SceneManager: Music file not found: {music_path} for context '{context_label}'.")
            if self.current_music_context == context_label:
                pygame.mixer.music.stop()
                self.current_music_context = None
            return

        try:
            pygame.mixer.music.load(music_path)
            # Use get_game_setting for volume, defaulting to 1.0 if key not found
            volume_setting = gs.get_game_setting(volume_multiplier_key, 1.0)
            pygame.mixer.music.set_volume(gs.get_game_setting("MUSIC_BASE_VOLUME", 0.5) * volume_setting)
            pygame.mixer.music.play(loops=loops)
            self.current_music_context = context_label
            print(f"SceneManager: Playing music '{music_path}' for context '{context_label}'.")
        except pygame.error as e:
            print(f"SceneManager: Error playing music '{music_path}': {e}")
            self.current_music_context = None

    def _update_music(self):
        """Selects and plays appropriate music based on the current game state and pause status."""
        music_map = {
            GAME_STATE_MAIN_MENU: (self.menu_music_path, "menu_theme"),
            GAME_STATE_DRONE_SELECT: (self.menu_music_path, "menu_theme"),
            GAME_STATE_SETTINGS: (self.menu_music_path, "menu_theme"),
            GAME_STATE_LEADERBOARD: (self.menu_music_path, "menu_theme"),
            GAME_STATE_ENTER_NAME: (self.menu_music_path, "menu_theme"), # Often shares menu theme
            GAME_STATE_GAME_OVER: (self.menu_music_path, "menu_theme"),   # Or a specific game over theme
            GAME_STATE_CODEX: (self.menu_music_path, "menu_theme"),       # Calm, ambient music
            GAME_STATE_RING_PUZZLE: (self.architect_vault_music_path, "puzzle_theme"), # Specific puzzle theme or vault theme
            GAME_STATE_GAME_INTRO_SCROLL: (self.menu_music_path, "intro_theme"), # Or a dedicated intro theme

            GAME_STATE_PLAYING: (self.gameplay_music_path, "gameplay_theme"),
            GAME_STATE_BONUS_LEVEL_PLAYING: (self.gameplay_music_path, "gameplay_theme"), # Or a faster bonus theme
            
            GAME_STATE_MAZE_DEFENSE: (self.defense_music_path, "defense_theme"), # Specific defense mode music

            GAME_STATE_ARCHITECT_VAULT_INTRO: (self.architect_vault_music_path, "architect_vault_ambient"),
            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: (self.architect_vault_music_path, "architect_vault_ambient"),
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET: (self.architect_vault_music_path, "architect_vault_action"),
            GAME_STATE_ARCHITECT_VAULT_EXTRACTION: (self.architect_vault_music_path, "architect_vault_action_tense"), # Potentially more tense

            GAME_STATE_ARCHITECT_VAULT_SUCCESS: (self.menu_music_path, "success_theme"), # Or a victory theme
            GAME_STATE_ARCHITECT_VAULT_FAILURE: (self.menu_music_path, "failure_theme")  # Or a somber theme
        }

        music_info = music_map.get(self.current_state)

        if music_info:
            path, context = music_info
            if self.current_music_context != context or not pygame.mixer.music.get_busy():
                self._play_music(path, context)
        # else: No specific music for this state, current music continues or stops based on previous state.

        # Handle pause/unpause based on game_controller's paused state
        if hasattr(self.game_controller, 'paused'):
            if self.game_controller.paused:
                if pygame.mixer.music.get_busy(): # Only pause if playing
                    pygame.mixer.music.pause()
            else: # Game is not paused
                # Check if music was paused and should be unpaused for the current context
                is_music_really_paused = not pygame.mixer.music.get_busy() and pygame.mixer.music.get_pos() > 0 # Pygame specific check for paused state
                
                current_expected_context = music_map.get(self.current_state, (None, None))[1]

                if is_music_really_paused and self.current_music_context == current_expected_context:
                    pygame.mixer.music.unpause()
                elif not pygame.mixer.music.get_busy() and self.current_music_context == current_expected_context:
                    # If music stopped but should be playing for this context (e.g., after unpausing from a state where music was stopped)
                    current_path_for_context = music_map.get(self.current_state, (None, None))[0]
                    if current_path_for_context:
                         self._play_music(current_path_for_context, self.current_music_context)


    def set_game_state(self, new_state, **kwargs):
        """
        Sets the current game state and notifies the GameController to initialize
        the scene via its sub-controllers. Also updates background music.
        Args:
            new_state (str): The new game state to transition to.
            **kwargs: Additional arguments to pass to the scene initialization logic.
                      For example, `triggering_terminal` for the ring puzzle.
        """
        if self.current_state == new_state:
            # Avoid re-initializing if already in this state, unless it's a gameplay state
            # that might need re-entry logic (e.g., after unpausing, though pause is handled separately).
            # This simple check is often sufficient.
            is_gameplay_state = new_state in [
                GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, GAME_STATE_MAZE_DEFENSE
            ] or new_state.startswith("architect_vault")
            if not (is_gameplay_state and hasattr(self.game_controller, 'paused') and self.game_controller.paused):
                 # If not a gameplay state or if it is but game is not paused, no need to re-set same state.
                return

        old_state = self.current_state
        self.current_state = new_state
        print(f"SceneManager: Game state changed from '{old_state}' to: '{self.current_state}'")

        self._update_music() # Update music based on the new state

        # Notify GameController to handle scene-specific initialization.
        # GameController will then delegate to UIFlowController, PuzzleController, or CombatController.
        if hasattr(self.game_controller, 'handle_scene_transition'):
            self.game_controller.handle_scene_transition(new_state, old_state, **kwargs)
        else:
            print(f"SceneManager: Warning - GameController does not have 'handle_scene_transition' method.")


    def update(self):
        """
        Called every frame by the main game loop.
        Can be used for scene-specific timed transitions or checks.
        (This logic was previously in GameController's update for scene transitions)
        """
        current_time = pygame.time.get_ticks()
        current_state = self.get_current_state()

        # Example of a timed transition that SceneManager could handle:
        if current_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            # Check if the intro message/animation duration has passed
            # This specific timer might be managed by GameController or UIFlowController now.
            # This is just an example of how SceneManager *could* do it.
            if hasattr(self.game_controller, 'architect_vault_message_timer') and \
               hasattr(self.game_controller, 'architect_vault_current_phase') and \
               self.game_controller.architect_vault_current_phase == "intro": # Check phase too
                if current_time > self.game_controller.architect_vault_message_timer:
                    # Transition to the next phase/state
                    self.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        
        elif current_state == GAME_STATE_BONUS_LEVEL_START:
            if hasattr(self.game_controller, 'bonus_level_start_display_end_time'):
                 if current_time > self.game_controller.bonus_level_start_display_end_time:
                    self.set_game_state(GAME_STATE_BONUS_LEVEL_PLAYING)
        
        # Music should be updated if game unpauses, which is handled in _update_music via GameController's paused state
        if hasattr(self.game_controller, 'paused') and not self.game_controller.paused:
            self._update_music()

