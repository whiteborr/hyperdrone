# hyperdrone_core/state_manager.py
import pygame
import os
import game_settings as gs
from .state import State
from .playing_state import PlayingState
from .maze_defense_state import MazeDefenseState
from .main_menu_state import MainMenuState
from .game_over_state import GameOverState
from .leaderboard_state import LeaderboardState
from .settings_state import SettingsState
from .drone_select_state import DroneSelectState
from .codex_state import CodexState
from .enter_name_state import EnterNameState
from .game_intro_scroll_state import GameIntroScrollState
from .ring_puzzle_state import RingPuzzleState
from .bonus_level_state import BonusLevelStartState, BonusLevelPlayingState
from .architect_vault_states import (
    ArchitectVaultIntroState,
    ArchitectVaultEntryPuzzleState,
    ArchitectVaultGauntletState,
    ArchitectVaultExtractionState,
    ArchitectVaultSuccessState,
    ArchitectVaultFailureState
)

class StateManager:
    """
    Manages game states using the State Design Pattern.
    Replaces the string-based state management in SceneManager.
    """
    def __init__(self, game_controller_ref):
        """
        Initializes the StateManager.
        Args:
            game_controller_ref: A reference to the main game controller instance.
        """
        self.game_controller = game_controller_ref
        self.asset_manager = self.game_controller.asset_manager
        self.current_state = None
        self.state_classes = {}
        self.current_music_context_key = None
        
        # Register state classes
        self._register_state_classes()
        
        # Initialize with default state
        self.set_state("MainMenuState")
        
        self._update_music()  # Initial music play
    
    def _register_state_classes(self):
        """Register all available state classes"""
        # Register implemented states
        self.state_classes = {
            "PlayingState": PlayingState,
            "MazeDefenseState": MazeDefenseState,
            "MainMenuState": MainMenuState,
            "GameOverState": GameOverState,
            "LeaderboardState": LeaderboardState,
            "SettingsState": SettingsState,
            "DroneSelectState": DroneSelectState,
            "CodexState": CodexState,
            "EnterNameState": EnterNameState,
            "GameIntroScrollState": GameIntroScrollState,
            "RingPuzzleState": RingPuzzleState,
            "BonusLevelStartState": BonusLevelStartState,
            "BonusLevelPlayingState": BonusLevelPlayingState,
            "ArchitectVaultIntroState": ArchitectVaultIntroState,
            "ArchitectVaultEntryPuzzleState": ArchitectVaultEntryPuzzleState,
            "ArchitectVaultGauntletState": ArchitectVaultGauntletState,
            "ArchitectVaultExtractionState": ArchitectVaultExtractionState,
            "ArchitectVaultSuccessState": ArchitectVaultSuccessState,
            "ArchitectVaultFailureState": ArchitectVaultFailureState
        }
        
        # Map from old string constants to new state classes for backward compatibility
        self.legacy_state_mapping = {
            gs.GAME_STATE_PLAYING: "PlayingState",
            gs.GAME_STATE_MAZE_DEFENSE: "MazeDefenseState",
            gs.GAME_STATE_MAIN_MENU: "MainMenuState",
            gs.GAME_STATE_GAME_OVER: "GameOverState",
            gs.GAME_STATE_LEADERBOARD: "LeaderboardState",
            gs.GAME_STATE_SETTINGS: "SettingsState",
            gs.GAME_STATE_DRONE_SELECT: "DroneSelectState",
            gs.GAME_STATE_CODEX: "CodexState",
            gs.GAME_STATE_ENTER_NAME: "EnterNameState",
            gs.GAME_STATE_GAME_INTRO_SCROLL: "GameIntroScrollState",
            gs.GAME_STATE_RING_PUZZLE: "RingPuzzleState",
            gs.GAME_STATE_BONUS_LEVEL_START: "BonusLevelStartState",
            gs.GAME_STATE_BONUS_LEVEL_PLAYING: "BonusLevelPlayingState",
            gs.GAME_STATE_ARCHITECT_VAULT_INTRO: "ArchitectVaultIntroState",
            gs.GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: "ArchitectVaultEntryPuzzleState",
            gs.GAME_STATE_ARCHITECT_VAULT_GAUNTLET: "ArchitectVaultGauntletState",
            gs.GAME_STATE_ARCHITECT_VAULT_EXTRACTION: "ArchitectVaultExtractionState",
            gs.GAME_STATE_ARCHITECT_VAULT_SUCCESS: "ArchitectVaultSuccessState",
            gs.GAME_STATE_ARCHITECT_VAULT_FAILURE: "ArchitectVaultFailureState"
        }
    
    def get_current_state(self):
        """Returns the current state object."""
        return self.current_state
    
    def get_current_state_id(self):
        """Returns the current state's identifier (for backward compatibility)."""
        if self.current_state:
            return self.current_state.get_state_id()
        return None
    
    def _play_music(self, music_key, volume_multiplier_key="MUSIC_VOLUME_MULTIPLIER", loops=-1):
        """Helper function to load and play music using AssetManager."""
        # Get the full file path from the AssetManager using the provided key
        music_path = self.asset_manager.get_music_path(music_key)

        if not music_path or not os.path.exists(music_path):
            print(f"StateManager: Music file not found for key '{music_key}'.")
            if self.current_music_context_key == music_key:
                pygame.mixer.music.stop()
                self.current_music_context_key = None
            return

        try:
            pygame.mixer.music.load(music_path)
            volume_setting = gs.get_game_setting(volume_multiplier_key, 1.0)
            pygame.mixer.music.set_volume(gs.get_game_setting("MUSIC_BASE_VOLUME", 0.5) * volume_setting)
            pygame.mixer.music.play(loops=loops)
            self.current_music_context_key = music_key  # Store the key of the playing music
            print(f"StateManager: Playing music for context key '{music_key}'.")
        except pygame.error as e:
            print(f"StateManager: Error playing music '{music_path}': {e}")
            self.current_music_context_key = None
    
    def _update_music(self):
        """Selects and plays appropriate music based on the current game state."""
        if not self.current_state:
            return
            
        current_state_id = self.current_state.get_state_id()
        
        # This map now uses asset keys for music tracks, defined in GameController's manifest
        music_map = {
            "MainMenuState": "menu_theme",
            "DroneSelectState": "menu_theme",
            "SettingsState": "menu_theme",
            "LeaderboardState": "menu_theme",
            "EnterNameState": "menu_theme",
            "GameOverState": "menu_theme",
            "CodexState": "menu_theme",
            "RingPuzzleState": "architect_vault_theme",
            "GameIntroScrollState": "menu_theme",
            "PlayingState": "gameplay_theme",
            "BonusLevelPlayingState": "gameplay_theme",
            "MazeDefenseState": "defense_theme",
            "ArchitectVaultIntroState": "architect_vault_theme",
            "ArchitectVaultEntryPuzzleState": "architect_vault_theme",
            "ArchitectVaultGauntletState": "architect_vault_theme",
            "ArchitectVaultExtractionState": "architect_vault_theme",
            "ArchitectVaultSuccessState": "menu_theme",
            "ArchitectVaultFailureState": "menu_theme"
        }

        music_key_for_state = music_map.get(current_state_id)

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
            else:  # Game is not paused
                # If music was paused, unpause it
                if not pygame.mixer.music.get_busy() and pygame.mixer.music.get_pos() > 0:
                    pygame.mixer.music.unpause()
                # If music was stopped but should be playing for this context (e.g., after returning to menu)
                elif not pygame.mixer.music.get_busy() and self.current_music_context_key == music_key_for_state:
                    self._play_music(self.current_music_context_key)
    
    def set_state(self, state_id, **kwargs):
        """
        Sets the current game state and initializes it.
        Args:
            state_id: The identifier of the state to set (class name or legacy string constant)
            **kwargs: Additional parameters to pass to the state's enter method
        """
        # Handle legacy string constants
        if state_id in self.legacy_state_mapping:
            state_id = self.legacy_state_mapping[state_id]
            
        # Check if the state class exists
        if state_id not in self.state_classes:
            print(f"StateManager: Unknown state '{state_id}'")
            return
            
        # Get the previous state for reference
        previous_state = self.current_state
        
        # Exit the current state if it exists
        if self.current_state:
            self.current_state.exit(state_id)
            
        # Create the new state
        state_class = self.state_classes[state_id]
        self.current_state = state_class(self.game_controller)
        
        # Enter the new state
        self.current_state.enter(previous_state, **kwargs)
        
        # Update music for the new state
        self._update_music()
        
        # Notify game controller about state transition if it has a handler
        if hasattr(self.game_controller, 'handle_state_transition'):
            self.game_controller.handle_state_transition(state_id, 
                previous_state.get_state_id() if previous_state else None, 
                **kwargs)
            state_id = self.legacy_state_mapping[state_id]
        
        # Check if the state exists
        if state_id not in self.state_classes:
            print(f"StateManager: Error - State '{state_id}' not found.")
            return
        
        # Check if we're already in this state
        if self.current_state and self.current_state.get_state_id() == state_id:
            # Avoid redundant state changes unless it's a gameplay state being re-entered (e.g., after unpausing)
            is_gameplay_state = state_id in [
                "PlayingState", "BonusLevelPlayingState", "MazeDefenseState"
            ] or state_id.startswith("ArchitectVault")
            if not (is_gameplay_state and hasattr(self.game_controller, 'paused') and self.game_controller.paused):
                return
        
        # Store the previous state for reference
        previous_state = self.current_state
        
        # Exit the current state if it exists
        if self.current_state:
            self.current_state.exit(state_id)
        
        # Create and initialize the new state
        state_class = self.state_classes[state_id]
        self.current_state = state_class(self.game_controller)
        
        # Enter the new state
        self.current_state.enter(previous_state, **kwargs)
        
        print(f"StateManager: State changed to: '{state_id}'")
        
        # Update music based on the new state
        self._update_music()
        
        # Notify the game controller about the state transition
        if hasattr(self.game_controller, 'handle_state_transition'):
            self.game_controller.handle_state_transition(state_id, previous_state.get_state_id() if previous_state else None, **kwargs)
    
    def update(self):
        """
        Called every frame by the main game loop for timed transitions or checks.
        Similar to SceneManager's update method for backward compatibility.
        """
        if not self.current_state:
            return
            
        current_time = pygame.time.get_ticks()
        current_state_id = self.current_state.get_state_id()
        
        # Handle timed transitions similar to SceneManager
        if current_state_id == "ArchitectVaultIntroState":
            if hasattr(self.game_controller, 'architect_vault_message_timer') and \
               hasattr(self.game_controller, 'architect_vault_current_phase') and \
               self.game_controller.architect_vault_current_phase == "intro":
                if current_time > self.game_controller.architect_vault_message_timer:
                    self.set_state("ArchitectVaultEntryPuzzleState")
        
        elif current_state_id == "BonusLevelStartState":
            if hasattr(self.game_controller, 'bonus_level_start_display_end_time'):
                if current_time > self.game_controller.bonus_level_start_display_end_time:
                    self.set_state("BonusLevelPlayingState")
        
        # Music pause/unpause is now handled in _update_music
        if hasattr(self.game_controller, 'paused') and not self.game_controller.paused:
            self._update_music()
        """
        Sets the current game state and initializes it.
        Args:
            state_id: The identifier of the state to set (class name or legacy string constant)
            **kwargs: Additional parameters to pass to the state's enter method
        """
        # Handle legacy string constants
        if state_id in self.legacy_state_mapping:
            state_id = self.legacy_state_mapping[state_id]
        
        # Avoid redundant state changes
        if self.current_state and self.current_state.get_state_id() == state_id:
            # Special case for gameplay states being re-entered after unpausing
            is_gameplay_state = state_id in ["PlayingState", "BonusLevelPlayingState", "MazeDefenseState"] or state_id.startswith("ArchitectVault")
            if not (is_gameplay_state and hasattr(self.game_controller, 'paused') and self.game_controller.paused):
                return
        
        # Get the state class
        state_class = self.state_classes.get(state_id)
        if not state_class:
            print(f"StateManager: Unknown state '{state_id}'")
            return
        
        # Store the old state for reference
        old_state = self.current_state
        old_state_id = old_state.get_state_id() if old_state else None
        
        # Exit the current state if it exists
        if old_state:
            old_state.exit(state_id)
        
        # Create and enter the new state
        new_state = state_class(self.game_controller)
        new_state.enter(old_state_id, **kwargs)
        
        # Update the current state
        self.current_state = new_state
        print(f"StateManager: Game state changed from '{old_state_id}' to: '{new_state.get_state_id()}'")
        
        # Update music based on the new state
        self._update_music()
        
        # Notify the game controller about the transition
        if hasattr(self.game_controller, 'handle_state_transition'):
            self.game_controller.handle_state_transition(new_state.get_state_id(), old_state_id, **kwargs)
    
    def update(self):
        """
        Called every frame by the main game loop for timed transitions or checks.
        """
        if not self.current_state:
            return
            
        # Music pause/unpause is now handled more robustly in _update_music
        if hasattr(self.game_controller, 'paused') and not self.game_controller.paused:
            self._update_music()