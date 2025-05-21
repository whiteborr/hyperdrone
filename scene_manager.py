import pygame
import os

# Import all necessary game state constants from game_settings.py
try:
    from game_settings import (
        GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
        GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
        GAME_STATE_BONUS_LEVEL_START, GAME_STATE_BONUS_LEVEL_PLAYING, # Assuming bonus level is still a concept
        GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
        GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
        GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE
        # Add any other game states if they influence music or scene initialization
    )
except ImportError:
    print("Critical Error (scene_manager.py): Could not import game state constants from game_settings.py.")
    # Fallback string values if import fails, though this will likely lead to issues.
    GAME_STATE_MAIN_MENU = "main_menu"
    GAME_STATE_PLAYING = "playing"
    # ... (add all other fallbacks if necessary, but ideally the import works)
    GAME_STATE_ARCHITECT_VAULT_INTRO = "architect_vault_intro"


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
        self.menu_music_path = os.path.join("assets", "sounds", "menu_music.wav") # Example path
        self.gameplay_music_path = os.path.join("assets", "sounds", "gameplay_music.wav") # Example path
        self.architect_vault_music_path = os.path.join("assets", "sounds", "architect_vault_theme.wav") # Example path
        self.current_music_context = None # Tracks which music (menu, gameplay, etc.) is playing or should be

        # Initial music play based on the starting state
        self._update_music()

    def get_current_state(self):
        """Returns the current game state string."""
        return self.current_state

    def _play_music(self, music_path, context_label, volume=0.5, loops=-1):
        """
        Helper function to load and play music, checking if the path exists.
        Args:
            music_path (str): Path to the music file.
            context_label (str): A label for the music context (e.g., "menu", "gameplay").
            volume (float): Music volume (0.0 to 1.0).
            loops (int): Number of times to loop the music (-1 for infinite).
        """
        if not music_path or not os.path.exists(music_path):
            print(f"SceneManager: Music file not found or path is None: {music_path}. Skipping playback for context '{context_label}'.")
            # If this context was supposed to be playing, stop current music to avoid wrong track
            if self.current_music_context == context_label:
                pygame.mixer.music.stop()
                self.current_music_context = None
            return

        try:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(volume) # Set volume before playing
            pygame.mixer.music.play(loops=loops)
            self.current_music_context = context_label # Update current music context
            print(f"SceneManager: Playing music '{music_path}' for context '{context_label}'.")
        except pygame.error as e:
            print(f"SceneManager: Error playing music '{music_path}': {e}")
            self.current_music_context = None # Reset context on error

    def _update_music(self):
        """
        Selects and plays the appropriate background music based on the current game state.
        Also handles pausing/unpausing music if the game_controller is paused.
        """
        # Map game states to music files and their contexts
        music_map = {
            GAME_STATE_MAIN_MENU: (self.menu_music_path, "menu_theme"),
            GAME_STATE_DRONE_SELECT: (self.menu_music_path, "menu_theme"),
            GAME_STATE_SETTINGS: (self.menu_music_path, "menu_theme"),
            GAME_STATE_LEADERBOARD: (self.menu_music_path, "menu_theme"),
            GAME_STATE_ENTER_NAME: (self.menu_music_path, "menu_theme"), # Usually quiet or menu music
            GAME_STATE_GAME_OVER: (self.menu_music_path, "menu_theme"),   # Or a specific game over track

            GAME_STATE_PLAYING: (self.gameplay_music_path, "gameplay_theme"),
            GAME_STATE_BONUS_LEVEL_PLAYING: (self.gameplay_music_path, "gameplay_theme"), # Or a unique bonus track

            GAME_STATE_ARCHITECT_VAULT_INTRO: (self.architect_vault_music_path, "architect_vault_ambient"),
            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: (self.architect_vault_music_path, "architect_vault_ambient"),
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET: (self.architect_vault_music_path, "architect_vault_action"), # Potentially more intense
            GAME_STATE_ARCHITECT_VAULT_EXTRACTION: (self.architect_vault_music_path, "architect_vault_action"), # Intense escape music

            GAME_STATE_ARCHITECT_VAULT_SUCCESS: (self.menu_music_path, "menu_theme"), # Or a victory jingle then menu
            GAME_STATE_ARCHITECT_VAULT_FAILURE: (self.menu_music_path, "menu_theme")  # Or a failure jingle then menu
        }

        music_info = music_map.get(self.current_state)
        is_active_gameplay_state = self.current_state in [
            GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE # Puzzle might have ambient music
        ]

        if music_info:
            path, context = music_info
            # Change track if context is different or if music is not currently playing
            if self.current_music_context != context or not pygame.mixer.music.get_busy():
                self._play_music(path, context) # Volume can be adjusted here or in _play_music
        else: # No specific music for this state, stop current music if it's not a persistent theme
            if self.current_music_context not in [None, "menu_theme"]: # Example: don't stop menu theme if transitioning to a minor state without music
                 # pygame.mixer.music.stop() # Or fade out: pygame.mixer.music.fadeout(500)
                 # self.current_music_context = None
                 pass # Decide if music should stop or continue from previous state

        # Handle pausing/unpausing music based on game_controller's paused state
        if hasattr(self.game_controller, 'paused'):
            if self.game_controller.paused:
                if pygame.mixer.music.get_busy(): # Only pause if music is playing
                    pygame.mixer.music.pause()
                    # print("SceneManager: Music paused.")
            else: # Game is not paused
                if not pygame.mixer.music.get_busy() and self.current_music_context:
                    # If music was stopped (e.g. due to pause) and should be playing, restart it for current context
                    current_path_for_context = music_map.get(self.current_state, (None, None))[0]
                    if current_path_for_context:
                        self._play_music(current_path_for_context, self.current_music_context)
                        # print(f"SceneManager: Music resumed for context '{self.current_music_context}'.")
                elif pygame.mixer.music.get_volume() > 0: # Check if it was paused (volume might be 0 if stopped)
                    # This logic might need refinement; pygame.mixer.music.unpause() only works if previously paused.
                    # A simple way is to just ensure the correct track for the current_music_context is playing if not paused.
                    # The check `not pygame.mixer.music.get_busy()` above handles restarting if it was fully stopped.
                    # If it was truly just paused by pygame.mixer.music.pause(), then unpause.
                    # However, pygame doesn't have a direct "is_paused" state for music.
                    # A common pattern is to just call play again if it should be playing and isn't.
                    # The `self.current_music_context != context or not pygame.mixer.music.get_busy()`
                    # at the start of the music_info block handles restarting if needed.
                    pass


    def set_game_state(self, new_state):
        """
        Sets the current game state and calls relevant initialization methods
        on the game_controller. Also updates background music.
        """
        if self.current_state == new_state:
            # Allow re-triggering for paused states if unpausing, or if it's a forced re-init
            is_playing_state = new_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
                               new_state.startswith("architect_vault")
            if not (is_playing_state and hasattr(self.game_controller, 'paused') and self.game_controller.paused):
                return # No change if already in this state and not unpausing

        old_state = self.current_state
        self.current_state = new_state
        print(f"SceneManager: Game state changed from '{old_state}' to: '{self.current_state}'")

        self._update_music() # Update music based on the new state

        # Call initialization methods on the game_controller based on the new state
        # These methods should exist in your GameController class (game_loop.py)
        if self.current_state == GAME_STATE_MAIN_MENU:
            if hasattr(self.game_controller, 'initialize_main_menu_scene'):
                self.game_controller.initialize_main_menu_scene()
        elif self.current_state == GAME_STATE_PLAYING:
            # Game session initialization is often handled by a specific action (e.g., "Start Game" from menu)
            # which then calls game_controller.initialize_game_session() and then sets state.
            # If set_game_state(GAME_STATE_PLAYING) is called directly, ensure init happens.
            # For now, assume GameController handles the actual game setup before this state is active.
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
        elif self.current_state == GAME_STATE_GAME_OVER:
            if hasattr(self.game_controller, 'handle_game_over_scene_entry'): # Or similar method name
                self.game_controller.handle_game_over_scene_entry()
        elif self.current_state == GAME_STATE_ENTER_NAME:
            if hasattr(self.game_controller, 'initialize_enter_name_scene'):
                self.game_controller.initialize_enter_name_scene()

        # Architect's Vault specific initializations (delegated to game_controller)
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            # initialize_architect_vault_session might be called once when entering the vault sequence
            if hasattr(self.game_controller, 'initialize_architect_vault_session'): # Call if not already in vault sequence
                 if not old_state.startswith("architect_vault"): # Only init session if coming from outside vault
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
            if hasattr(self.game_controller, 'handle_architect_vault_success_scene'):
                self.game_controller.handle_architect_vault_success_scene()
        elif self.current_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
            if hasattr(self.game_controller, 'handle_architect_vault_failure_scene'):
                self.game_controller.handle_architect_vault_failure_scene()
        # Add other states as needed

    def update(self):
        """
        Called every frame by the main game loop.
        Can be used for scene-specific timed transitions or checks if not handled
        by the game_controller's state update logic.
        Example: Transitioning from ARCHITECT_VAULT_INTRO after a message timer.
        """
        current_time = pygame.time.get_ticks()

        if self.current_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            # Check if the intro message timer has expired to transition
            if hasattr(self.game_controller, 'architect_vault_message_timer') and \
               hasattr(self.game_controller, 'architect_vault_current_phase') and \
               self.game_controller.architect_vault_current_phase == "intro": # Ensure it's still in intro phase
                if current_time > self.game_controller.architect_vault_message_timer:
                    self.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        
        # Add other timed transitions if necessary. For example, from a "Level Start" display.
        # if self.current_state == GAME_STATE_BONUS_LEVEL_START:
        #     if current_time > self.game_controller.bonus_level_start_display_end_time: # Example attribute
        #         self.set_game_state(GAME_STATE_BONUS_LEVEL_PLAYING)