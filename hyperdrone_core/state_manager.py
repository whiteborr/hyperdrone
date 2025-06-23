# hyperdrone_core/state_manager.py
from pygame import Surface
from pygame.mixer import music
from pygame.time import get_ticks
from pygame import error as pygame_error
import os
import time
import logging
from settings_manager import get_setting
from constants import (
    GAME_STATE_PLAYING, GAME_STATE_MAZE_DEFENSE, GAME_STATE_MAIN_MENU,
    GAME_STATE_GAME_OVER, GAME_STATE_LEADERBOARD, GAME_STATE_SETTINGS,
    GAME_STATE_DRONE_SELECT, GAME_STATE_CODEX, GAME_STATE_ENTER_NAME,
    GAME_STATE_GAME_INTRO_SCROLL, GAME_STATE_RING_PUZZLE, GAME_STATE_STORY_MAP,
    GAME_STATE_BONUS_LEVEL_START, GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_BOSS_FIGHT, GAME_STATE_CORRUPTED_SECTOR, GAME_STATE_HARVEST_CHAMBER
)
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
from .story_map_state import StoryMapState
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
from .corrupted_sector_state import CorruptedSectorState
from .harvest_chamber_state import HarvestChamberState
from .weapons_upgrade_shop_state import WeaponsUpgradeShopState

logger = logging.getLogger(__name__)

class StateManager:
    """
    Manages game states using the State Design Pattern.
    
    Provides centralized state management with validation, transition history,
    and automatic music management. Supports complex state transitions with
    parameter passing and maintains a registry of allowed transitions.
    
    Key Features:
    - State validation and transition control
    - Automatic music management per state
    - State transition history tracking
    - Legacy state mapping for backward compatibility
    
    Attributes:
        current_state (State): Currently active game state
        registry (StateRegistry): Manages state registration and transitions
        state_classes (dict): Maps state IDs to their implementation classes
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
        
        # Fade transition attributes
        self.fading_out = False
        self.fading_in = False
        self.fade_alpha = 0
        self.fade_surface = None
        self.pending_state_id = None
        self.pending_state_kwargs = {}
        self.fade_speed = 5
        
        # Import and initialize the state registry
        from .state_registry import state_registry
        self.registry = state_registry
        
        # Register state classes
        self._register_state_classes()
        
        # Initialize fade surface
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        self.fade_surface = Surface((screen_width, screen_height))
        self.fade_surface.fill((0, 0, 0))
        
        # Initialize with default state (skip fade for initial state)
        self._set_state_direct("MainMenuState")
        
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
            "StoryMapState": StoryMapState,
            "BonusLevelStartState": BonusLevelStartState,
            "BonusLevelPlayingState": BonusLevelPlayingState,
            "ArchitectVaultIntroState": ArchitectVaultIntroState,
            "ArchitectVaultEntryPuzzleState": ArchitectVaultEntryPuzzleState,
            "ArchitectVaultGauntletState": ArchitectVaultGauntletState,
            "ArchitectVaultExtractionState": ArchitectVaultExtractionState,
            "ArchitectVaultSuccessState": ArchitectVaultSuccessState,
            "ArchitectVaultFailureState": ArchitectVaultFailureState,
            "BossFightState": BossFightState,
            "CorruptedSectorState": CorruptedSectorState,
            "HarvestChamberState": HarvestChamberState,
            "WeaponsUpgradeShopState": WeaponsUpgradeShopState
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
            GAME_STATE_STORY_MAP: "StoryMapState",
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
            GAME_STATE_CORRUPTED_SECTOR: "CorruptedSectorState",
            GAME_STATE_HARVEST_CHAMBER: "HarvestChamberState"
        }
        
    def _register_allowed_transitions(self):
        """Register allowed transitions between states"""
        # Main menu transitions
        self.registry.register_transition("MainMenuState", "StoryMapState")
        self.registry.register_transition("MainMenuState", "SettingsState")
        self.registry.register_transition("MainMenuState", "LeaderboardState")
        self.registry.register_transition("MainMenuState", "DroneSelectState")
        self.registry.register_transition("MainMenuState", "CodexState")
        self.registry.register_transition("MainMenuState", "GameIntroScrollState")
        self.registry.register_transition("MainMenuState", "MazeDefenseState")
        self.registry.register_transition("MainMenuState", "WeaponsUpgradeShopState")
        
        # Settings transitions
        self.registry.register_transition("SettingsState", "MainMenuState")
        self.registry.register_transition("SettingsState", "StoryMapState")
        self.registry.register_transition("SettingsState", "CorruptedSectorState")
        self.registry.register_transition("SettingsState", "PlayingState")
        self.registry.register_transition("SettingsState", "BossFightState")
        self.registry.register_transition("SettingsState", "HarvestChamberState")
        
        # Leaderboard transitions
        self.registry.register_transition("LeaderboardState", "MainMenuState")
        
        # Drone select transitions
        self.registry.register_transition("DroneSelectState", "MainMenuState")
        
        # Codex transitions
        self.registry.register_transition("CodexState", "MainMenuState")
        
        # Weapons upgrade shop transitions
        self.registry.register_transition("WeaponsUpgradeShopState", "MainMenuState")
        self.registry.register_transition("WeaponsUpgradeShopState", "PlayingState")
        self.registry.register_transition("PlayingState", "WeaponsUpgradeShopState")
        
        # Game intro transitions
        self.registry.register_transition("GameIntroScrollState", "StoryMapState")
        
        # Story map transitions
        self.registry.register_transition("StoryMapState", "PlayingState")
        self.registry.register_transition("StoryMapState", "BossFightState")
        self.registry.register_transition("StoryMapState", "CorruptedSectorState")
        self.registry.register_transition("StoryMapState", "HarvestChamberState")
        self.registry.register_transition("StoryMapState", "MazeDefenseState")
        
        # Playing state transitions
        self.registry.register_transition("PlayingState", "GameOverState")
        self.registry.register_transition("PlayingState", "RingPuzzleState")
        self.registry.register_transition("PlayingState", "BonusLevelStartState")
        self.registry.register_transition("PlayingState", "ArchitectVaultIntroState")
        self.registry.register_transition("PlayingState", "MazeDefenseState")
        self.registry.register_transition("PlayingState", "BossFightState")
        self.registry.register_transition("PlayingState", "StoryMapState")

        # Game over transitions
        self.registry.register_transition("GameOverState", "MainMenuState")
        self.registry.register_transition("GameOverState", "EnterNameState")
        self.registry.register_transition("GameOverState", "StoryMapState")
        self.registry.register_transition("GameOverState", "PlayingState")
        self.registry.register_transition("GameOverState", "MazeDefenseState")
        self.registry.register_transition("GameOverState", "BossFightState")
        self.registry.register_transition("GameOverState", "CorruptedSectorState")
        self.registry.register_transition("GameOverState", "HarvestChamberState")
        
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
        self.registry.register_transition("BossFightState", "CorruptedSectorState")
        self.registry.register_transition("BossFightState", "StoryMapState")

        # Corrupted Sector transitions
        self.registry.register_transition("CorruptedSectorState", "GameOverState")
        self.registry.register_transition("CorruptedSectorState", "HarvestChamberState")
        self.registry.register_transition("CorruptedSectorState", "StoryMapState")

        # Harvest Chamber transitions
        self.registry.register_transition("HarvestChamberState", "GameOverState")
        self.registry.register_transition("HarvestChamberState", "MainMenuState") # Placeholder for now
    
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
                music.stop()
                self.current_music_context_key = None
            return

        try:
            music.load(music_path)
            # Use new game volume setting
            game_volume = get_setting("audio", "VOLUME_GAME", 5) / 10.0
            base_volume = get_setting("display", "MUSIC_BASE_VOLUME", 0.5)
            music.set_volume(base_volume * game_volume)
            music.play(loops=loops)
            self.current_music_context_key = music_key
            logger.info(f"Playing music for context key '{music_key}' at volume {game_volume}")
        except pygame_error as e:
            logger.error(f"Error playing music '{music_path}': {e}")
            self.current_music_context_key = None
    
    def _update_music(self):
        """Selects and plays appropriate music based on the current game state."""
        if not self.current_state:
            return
            
        # Update volume for currently playing music
        if music.get_busy():
            game_volume = get_setting("audio", "VOLUME_GAME", 5) / 10.0
            base_volume = get_setting("display", "MUSIC_BASE_VOLUME", 0.5)
            music.set_volume(base_volume * game_volume)
            
        current_state_id = self.current_state.get_state_id()
        
        music_map = {
            "MainMenuState": "menu_theme",
            "DroneSelectState": "menu_theme",
            "SettingsState": "menu_theme",
            "LeaderboardState": "menu_theme",
            "EnterNameState": "menu_theme",
            "GameOverState": "menu_theme",
            "CodexState": "menu_theme",
            "WeaponsUpgradeShopState": "menu_theme",
            "RingPuzzleState": "architect_vault_theme",
            "GameIntroScrollState": "menu_theme",
            "StoryMapState": "menu_theme",
            "PlayingState": "gameplay_theme",
            "BossFightState": "boss_theme", 
            "CorruptedSectorState": "corrupted_theme",
            "HarvestChamberState": "shmup_theme",
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
            if self.current_music_context_key != music_key_for_state or not music.get_busy():
                self._play_music(music_key_for_state)

        if hasattr(self.game_controller, 'paused'):
            if self.game_controller.paused:
                if music.get_busy():
                    music.pause()
            else:
                if not music.get_busy() and music.get_pos() > 0:
                    music.unpause()
                elif not music.get_busy() and self.current_music_context_key == music_key_for_state:
                    self._play_music(self.current_music_context_key)
    
    def set_state(self, state_id, **kwargs):
        """
        Sets the current game state and initializes it.
        
        Validates the transition, handles state cleanup, creates new state instance,
        and updates music. Supports forced restarts for gameplay states and
        maintains transition history.
        
        Args:
            state_id (str): The identifier of the state to set (class name or legacy constant)
            **kwargs: Additional parameters to pass to the state's enter method
                - force_restart (bool): Force state restart even if already active
                - Any state-specific initialization parameters
                
        Returns:
            None
            
        Raises:
            Logs warning if transition is not allowed by the registry
        """
        if state_id in self.legacy_state_mapping:
            state_id = self.legacy_state_mapping[state_id]
        
        # Special case for PlayingState - always allow restarting the playing state
        # This is needed for player respawning when they lose a life
        force_restart = kwargs.get('force_restart', False)
        
        if self.current_state and self.current_state.get_state_id() == state_id and not force_restart:
            is_gameplay_state = state_id in ["PlayingState", "BonusLevelPlayingState", "MazeDefenseState", "BossFightState", "CorruptedSectorState", "HarvestChamberState"] or state_id.startswith("ArchitectVault")
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
        
        # Start fade transition if not already fading
        if not self.fading_out and not self.fading_in:
            self.fading_out = True
            self.fade_alpha = 0
            self.pending_state_id = state_id
            self.pending_state_kwargs = kwargs
            return
    
    def _set_state_direct(self, state_id, **kwargs):
        """Direct state change without fade transition."""
        if state_id in self.legacy_state_mapping:
            state_id = self.legacy_state_mapping[state_id]
        
        old_state = self.current_state
        old_state_id = old_state.get_state_id() if old_state else None
        
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
        
        # Update fade transitions
        if self.fading_out:
            self.fade_alpha += self.fade_speed
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                self.fading_out = False
                self.fading_in = True
                # Perform actual state change
                self._perform_state_change()
        elif self.fading_in:
            self.fade_alpha -= self.fade_speed
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.fading_in = False
            
        current_time = get_ticks()
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
                    
        elif current_state_id == "StoryMapState":
            if hasattr(self.game_controller, 'story_map_state') and hasattr(self.game_controller.story_map_state, 'ready_to_transition'):
                if self.game_controller.story_map_state.ready_to_transition:
                    self.game_controller.story_map_state._transition_to_gameplay()
        
        if hasattr(self.game_controller, 'paused') and not self.game_controller.paused:
            self._update_music()
    
    def _perform_state_change(self):
        """Performs the actual state change after fade-out completes."""
        if not self.pending_state_id:
            return
            
        state_id = self.pending_state_id
        kwargs = self.pending_state_kwargs
        
        if state_id in self.legacy_state_mapping:
            state_id = self.legacy_state_mapping[state_id]
        
        old_state = self.current_state
        old_state_id = old_state.get_state_id() if old_state else None
        
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
        
        # Clear pending state
        self.pending_state_id = None
        self.pending_state_kwargs = {}
    
    def draw_fade_transition(self, screen):
        """Draws the fade transition overlay."""
        if (self.fading_out or self.fading_in) and self.fade_alpha > 0:
            self.fade_surface.set_alpha(self.fade_alpha)
            screen.blit(self.fade_surface, (0, 0))
