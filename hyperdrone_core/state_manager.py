# hyperdrone_core/state_manager.py
import pygame
import os
import time
import logging
from settings_manager import get_setting

# Define game state constants directly here to avoid circular imports
GAME_STATE_PLAYING = get_setting("game_states", "GAME_STATE_PLAYING", "playing")
GAME_STATE_MAZE_DEFENSE = get_setting("game_states", "GAME_STATE_MAZE_DEFENSE", "maze_defense_mode")
GAME_STATE_MAIN_MENU = get_setting("game_states", "GAME_STATE_MAIN_MENU", "main_menu")
GAME_STATE_GAME_OVER = get_setting("game_states", "GAME_STATE_GAME_OVER", "game_over")
GAME_STATE_LEADERBOARD = get_setting("game_states", "GAME_STATE_LEADERBOARD", "leaderboard_display")
GAME_STATE_SETTINGS = get_setting("game_states", "GAME_STATE_SETTINGS", "settings_menu")
GAME_STATE_DRONE_SELECT = get_setting("game_states", "GAME_STATE_DRONE_SELECT", "drone_select_menu")
GAME_STATE_CODEX = get_setting("game_states", "GAME_STATE_CODEX", "codex_screen")
GAME_STATE_ENTER_NAME = get_setting("game_states", "GAME_STATE_ENTER_NAME", "enter_name")
GAME_STATE_GAME_INTRO_SCROLL = get_setting("game_states", "GAME_STATE_GAME_INTRO_SCROLL", "game_intro_scroll")
GAME_STATE_RING_PUZZLE = get_setting("game_states", "GAME_STATE_RING_PUZZLE", "ring_puzzle_active")
GAME_STATE_BONUS_LEVEL_START = get_setting("game_states", "GAME_STATE_BONUS_LEVEL_START", "bonus_level_start")
GAME_STATE_BONUS_LEVEL_PLAYING = get_setting("game_states", "GAME_STATE_BONUS_LEVEL_PLAYING", "bonus_level_playing")
GAME_STATE_ARCHITECT_VAULT_INTRO = get_setting("game_states", "GAME_STATE_ARCHITECT_VAULT_INTRO", "architect_vault_intro")
GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE = get_setting("game_states", "GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE", "architect_vault_entry_puzzle")
GAME_STATE_ARCHITECT_VAULT_GAUNTLET = get_setting("game_states", "GAME_STATE_ARCHITECT_VAULT_GAUNTLET", "architect_vault_gauntlet")
GAME_STATE_ARCHITECT_VAULT_EXTRACTION = get_setting("game_states", "GAME_STATE_ARCHITECT_VAULT_EXTRACTION", "architect_vault_extraction")
GAME_STATE_ARCHITECT_VAULT_SUCCESS = get_setting("game_states", "GAME_STATE_ARCHITECT_VAULT_SUCCESS", "architect_vault_success")
GAME_STATE_ARCHITECT_VAULT_FAILURE = get_setting("game_states", "GAME_STATE_ARCHITECT_VAULT_FAILURE", "architect_vault_failure")
GAME_STATE_BOSS_FIGHT = get_setting("game_states", "GAME_STATE_BOSS_FIGHT", "boss_fight")
GAME_STATE_CORRUPTED_SECTOR = get_setting("game_states", "GAME_STATE_CORRUPTED_SECTOR", "corrupted_sector")
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
from .boss_fight_state import BossFightState
from .corrupted_sector_state import CorruptedSectorState # Import the new state

logger = logging.getLogger(__name__)

class StateManager:
    """
    Manages game states using the State Design Pattern.
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
        
        # Import and initialize the state registry
        from .state_registry import state_registry
        self.registry = state_registry
        
        # Register state classes
        self._register_state_classes()
        
        # Initialize with default state
        self.set_state("MainMenuState")
        
        self._update_music()  # Initial music play
    
    def _register_state_classes(self):
        """Register all available state classes"""
        # Define state classes
        state_classes = {
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
            "ArchitectVaultFailureState": ArchitectVaultFailureState,
            "BossFightState": BossFightState,
            "CorruptedSectorState": CorruptedSectorState # Add the new state here
        }
        
        # Register states with both the local cache and the central registry
        self.state_classes = state_classes
        for state_id, state_class in state_classes.items():
            self.registry.register_state(state_id, state_class)
        
        # Register allowed transitions
        self._register_allowed_transitions()
        
        # Map from old string constants to new state classes for backward compatibility
        self.legacy_state_mapping = {
            GAME_STATE_PLAYING: "PlayingState",
            GAME_STATE_MAZE_DEFENSE: "MazeDefenseState",
            GAME_STATE_MAIN_MENU: "MainMenuState",
            GAME_STATE_GAME_OVER: "GameOverState",
            GAME_STATE_LEADERBOARD: "LeaderboardState",
            GAME_STATE_SETTINGS: "SettingsState",
            GAME_STATE_DRONE_SELECT: "DroneSelectState",
            GAME_STATE_CODEX: "CodexState",
            GAME_STATE_ENTER_NAME: "EnterNameState",
            GAME_STATE_GAME_INTRO_SCROLL: "GameIntroScrollState",
            GAME_STATE_RING_PUZZLE: "RingPuzzleState",
            GAME_STATE_BONUS_LEVEL_START: "BonusLevelStartState",
            GAME_STATE_BONUS_LEVEL_PLAYING: "BonusLevelPlayingState",
            GAME_STATE_ARCHITECT_VAULT_INTRO: "ArchitectVaultIntroState",
            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: "ArchitectVaultEntryPuzzleState",
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET: "ArchitectVaultGauntletState",
            GAME_STATE_ARCHITECT_VAULT_EXTRACTION: "ArchitectVaultExtractionState",
            GAME_STATE_ARCHITECT_VAULT_SUCCESS: "ArchitectVaultSuccessState",
            GAME_STATE_ARCHITECT_VAULT_FAILURE: "ArchitectVaultFailureState",
            GAME_STATE_BOSS_FIGHT: "BossFightState",
            GAME_STATE_CORRUPTED_SECTOR: "CorruptedSectorState"
        }
        
    def _register_allowed_transitions(self):
        """Register allowed transitions between states"""
        # Main menu transitions
        self.registry.register_transition("MainMenuState", "PlayingState")
        self.registry.register_transition("MainMenuState", "SettingsState")
        self.registry.register_transition("MainMenuState", "LeaderboardState")
        self.registry.register_transition("MainMenuState", "DroneSelectState")
        self.registry.register_transition("MainMenuState", "CodexState")
        self.registry.register_transition("MainMenuState", "GameIntroScrollState")
        self.registry.register_transition("MainMenuState", "MazeDefenseState")
        
        # Settings transitions
        self.registry.register_transition("SettingsState", "MainMenuState")
        
        # Leaderboard transitions
        self.registry.register_transition("LeaderboardState", "MainMenuState")
        
        # Drone select transitions
        self.registry.register_transition("DroneSelectState", "MainMenuState")
        
        # Codex transitions
        self.registry.register_transition("CodexState", "MainMenuState")
        
        # Game intro transitions
        self.registry.register_transition("GameIntroScrollState", "PlayingState")
        
        # Playing state transitions
        self.registry.register_transition("PlayingState", "GameOverState")
        self.registry.register_transition("PlayingState", "RingPuzzleState")
        self.registry.register_transition("PlayingState", "BonusLevelStartState")
        self.registry.register_transition("PlayingState", "ArchitectVaultIntroState")
        self.registry.register_transition("PlayingState", "MazeDefenseState")
        self.registry.register_transition("PlayingState", "BossFightState")

        # Game over transitions
        self.registry.register_transition("GameOverState", "MainMenuState")
        self.registry.register_transition("GameOverState", "EnterNameState")
        
        # Enter name transitions
        self.registry.register_transition("EnterNameState", "LeaderboardState")
        
        # Ring puzzle transitions
        self.registry.register_transition("RingPuzzleState", "PlayingState")
        
        # Bonus level transitions
        self.registry.register_transition("BonusLevelStartState", "BonusLevelPlayingState")
        self.registry.register_transition("BonusLevelPlayingState", "PlayingState")
        self.registry.register_transition("BonusLevelPlayingState", "GameOverState")
        
        # Architect vault transitions
        self.registry.register_transition("ArchitectVaultIntroState", "ArchitectVaultEntryPuzzleState")
        self.registry.register_transition("ArchitectVaultEntryPuzzleState", "ArchitectVaultGauntletState")
        self.registry.register_transition("ArchitectVaultGauntletState", "ArchitectVaultExtractionState")
        self.registry.register_transition("ArchitectVaultExtractionState", "ArchitectVaultSuccessState")
        self.registry.register_transition("ArchitectVaultExtractionState", "ArchitectVaultFailureState")
        self.registry.register_transition("ArchitectVaultSuccessState", "PlayingState")
        self.registry.register_transition("ArchitectVaultFailureState", "PlayingState")
        
        # Maze defense transitions
        self.registry.register_transition("MazeDefenseState", "PlayingState")
        self.registry.register_transition("MazeDefenseState", "GameOverState")

        # Boss fight transitions
        self.registry.register_transition("BossFightState", "GameOverState")
        self.registry.register_transition("BossFightState", "MainMenuState")
        self.registry.register_transition("BossFightState", "CorruptedSectorState") # Transition to Chapter 3 state

        # Corrupted Sector transitions
        self.registry.register_transition("CorruptedSectorState", "GameOverState")
        # In the future, this will transition to Chapter 4's state
        self.registry.register_transition("CorruptedSectorState", "MainMenuState")
    
    def get_current_state(self):
        """Returns the current state object."""
        return self.current_state
    
    def get_current_state_id(self):
        """Returns the current state's identifier."""
        if self.current_state:
            return self.current_state.get_state_id()
        return None
    
    def _play_music(self, music_key, volume_multiplier_key="MUSIC_VOLUME_MULTIPLIER", loops=-1):
        """Helper function to load and play music using AssetManager."""
        music_path = self.asset_manager.get_music_path(music_key)

        if not music_path or not os.path.exists(music_path):
            logger.warning(f"Music file not found for key '{music_key}'")
            if self.current_music_context_key == music_key:
                pygame.mixer.music.stop()
                self.current_music_context_key = None
            return

        try:
            pygame.mixer.music.load(music_path)
            volume_setting = get_setting("display", volume_multiplier_key, 1.0)
            base_volume = get_setting("display", "MUSIC_BASE_VOLUME", 0.5)
            pygame.mixer.music.set_volume(base_volume * volume_setting)
            pygame.mixer.music.play(loops=loops)
            self.current_music_context_key = music_key
            logger.info(f"Playing music for context key '{music_key}'")
        except pygame.error as e:
            logger.error(f"Error playing music '{music_path}': {e}")
            self.current_music_context_key = None
    
    def _update_music(self):
        """Selects and plays appropriate music based on the current game state."""
        if not self.current_state:
            return
            
        current_state_id = self.current_state.get_state_id()
        
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
            "BossFightState": "boss_theme", 
            "CorruptedSectorState": "corrupted_theme", # Add theme for the new chapter
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
            if self.current_music_context_key != music_key_for_state or not pygame.mixer.music.get_busy():
                self._play_music(music_key_for_state)

        if hasattr(self.game_controller, 'paused'):
            if self.game_controller.paused:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.pause()
            else:
                if not pygame.mixer.music.get_busy() and pygame.mixer.music.get_pos() > 0:
                    pygame.mixer.music.unpause()
                elif not pygame.mixer.music.get_busy() and self.current_music_context_key == music_key_for_state:
                    self._play_music(self.current_music_context_key)
    
    def set_state(self, state_id, **kwargs):
        """
        Sets the current game state and initializes it.
        Args:
            state_id: The identifier of the state to set (class name or legacy string constant)
            **kwargs: Additional parameters to pass to the state's enter method
        """
        if state_id in self.legacy_state_mapping:
            state_id = self.legacy_state_mapping[state_id]
        
        if self.current_state and self.current_state.get_state_id() == state_id:
            is_gameplay_state = state_id in ["PlayingState", "BonusLevelPlayingState", "MazeDefenseState", "BossFightState", "CorruptedSectorState"] or state_id.startswith("ArchitectVault")
            if not (is_gameplay_state and hasattr(self.game_controller, 'paused') and self.game_controller.paused):
                return
        
        old_state = self.current_state
        old_state_id = old_state.get_state_id() if old_state else None
        
        if old_state_id and not self.registry.is_transition_allowed(old_state_id, state_id):
            logger.warning(f"Transition from '{old_state_id}' to '{state_id}' is not allowed")
            return
        
        state_class = self.registry.get_state_class(state_id)
        if not state_class:
            logger.error(f"Unknown state '{state_id}'")
            return
        
        if old_state:
            old_state.exit(state_id)
        
        new_state = state_class(self.game_controller)
        new_state.enter(old_state_id, **kwargs)
        
        self.current_state = new_state
        
        self.registry.record_transition(old_state_id, state_id, time.time())
        
        logger.info(f"Game state changed from '{old_state_id}' to '{state_id}'")
        
        self._update_music()
        
        if hasattr(self.game_controller, 'handle_state_transition'):
            self.game_controller.handle_state_transition(state_id, old_state_id, **kwargs)
    
    def update(self):
        """
        Called every frame by the main game loop for timed transitions or checks.
        """
        if not self.current_state:
            return
            
        current_time = pygame.time.get_ticks()
        current_state_id = self.current_state.get_state_id()
        
        # Handle timed transitions
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
        
        if hasattr(self.game_controller, 'paused') and not self.game_controller.paused:
            self._update_music()
