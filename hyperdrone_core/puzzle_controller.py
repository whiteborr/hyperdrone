# hyperdrone_core/puzzle_controller.pyAdd commentMore actions
import pygame
import os 
import logging

from settings_manager import get_setting, settings_manager
from constants import (
    GAME_STATE_RING_PUZZLE, GAME_STATE_PLAYING, GAME_STATE_MAZE_DEFENSE, 
    GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, GAME_STATE_ARCHITECT_VAULT_GAUNTLET
)

from entities import AncientAlienTerminal
from .ring_puzzle_module import RingPuzzle

logger = logging.getLogger(__name__)

class PuzzleController:
    """
    Manages puzzle mechanics, interactions, and state within the game.
    """
    def __init__(self, game_controller_ref, asset_manager):
        """
        Initializes the PuzzleController.
        Args:
            game_controller_ref: A reference to the main GameController instance.
            asset_manager: The central AssetManager for loading game assets.
        """
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager # Store the AssetManager instance
        self.player = None
        self.drone_system = None
        self.scene_manager = None
        
        self.current_ring_puzzle = None
        self.ring_puzzle_active_flag = False
        self.ring_puzzle_solved_this_session = False
        self.last_interacted_terminal_for_ring_puzzle = None

        total_fragments = get_setting("collectibles", "TOTAL_CORE_FRAGMENTS_NEEDED", 3)
        self.architect_vault_terminals_activated = [False] * total_fragments
        self.architect_vault_puzzle_terminals_group = pygame.sprite.Group()

        logger.info("PuzzleController initialized.")

    def set_active_entities(self, player, drone_system, scene_manager, alien_terminals_group=None, architect_vault_terminals_group=None):
        """Sets references to currently active game entities relevant to puzzles."""
        self.player = player
        self.drone_system = drone_system
        self.scene_manager = scene_manager
        if architect_vault_terminals_group is not None:
            self.architect_vault_puzzle_terminals_group = architect_vault_terminals_group


    def update(self, current_time_ms, current_game_state):
        """Main update loop for the PuzzleController."""
        if current_game_state == GAME_STATE_RING_PUZZLE:
            if self.ring_puzzle_active_flag and self.current_ring_puzzle:
                self.current_ring_puzzle.update()
                if self.current_ring_puzzle.is_solved() and \
                   not self.current_ring_puzzle.active and \
                   not self.ring_puzzle_solved_this_session:
                    self._handle_ring_puzzle_solved()
        
        elif current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            pass


    def handle_input(self, event, current_game_state):
        """Handles player input relevant to puzzles."""
        if current_game_state == GAME_STATE_RING_PUZZLE:
            if self.ring_puzzle_active_flag and self.current_ring_puzzle:
                self.current_ring_puzzle.handle_input(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.exit_ring_puzzle()
                    return True
                if self.current_ring_puzzle.is_solved() and \
                   not self.current_ring_puzzle.active and \
                   event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE):
                    self.exit_ring_puzzle(puzzle_was_solved=True)
                    return True
                return True

        elif current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.try_activate_architect_vault_terminal(0)
                    return True
                elif event.key == pygame.K_2:
                    self.try_activate_architect_vault_terminal(1)
                    return True
                elif event.key == pygame.K_3:
                    self.try_activate_architect_vault_terminal(2)
                    return True
        return False


    def start_ring_puzzle(self, terminal_sprite):
        """
        Initializes and starts the Ring Puzzle, passing the AssetManager to it.
        """
        if not self.scene_manager or not self.drone_system:
            logger.error("PuzzleController: SceneManager or DroneSystem not available to start ring puzzle.")
            return

        if self.drone_system.has_puzzle_terminal_been_solved(terminal_sprite.item_id):
            self.game_controller.set_story_message("This terminal's data has already been extracted.")
            self.game_controller.play_sound('ui_denied')
            return

        ring_configs = [
            ("ring1.png", 6), ("ring2.png", 8), ("ring3.png", 12)
        ]
        
        try:
            screen_width = get_setting("display", "WIDTH", 1920)
            screen_height = get_setting("display", "HEIGHT", 1080)
            
            self.current_ring_puzzle = RingPuzzle(
                screen_width, 
                screen_height,
                ring_configs,
                asset_manager=self.asset_manager # Pass asset_manager to RingPuzzle
            )
            self.ring_puzzle_active_flag = True
            self.ring_puzzle_solved_this_session = False
            self.last_interacted_terminal_for_ring_puzzle = terminal_sprite
            self.scene_manager.set_game_state(GAME_STATE_RING_PUZZLE)
            self.game_controller.play_sound('ui_confirm')
            logger.info(f"PuzzleController: Ring Puzzle started for terminal {terminal_sprite.item_id}.")
        except Exception as e:
            logger.error(f"PuzzleController: Error initializing RingPuzzle: {e}")
            self.current_ring_puzzle = None
            self.ring_puzzle_active_flag = False
            self.scene_manager.set_game_state(GAME_STATE_PLAYING)


    def _handle_ring_puzzle_solved(self):
        """Handles the logic when the Ring Puzzle is solved."""
        logger.info("PuzzleController: Ring Puzzle solved!")
        self.ring_puzzle_solved_this_session = True
        
        if self.drone_system:
            reward = get_setting("puzzles", "RING_PUZZLE_CORE_REWARD", 750)
            self.drone_system.add_player_cores(reward)
            if self.last_interacted_terminal_for_ring_puzzle:
                self.drone_system.mark_puzzle_terminal_as_solved(self.last_interacted_terminal_for_ring_puzzle.item_id)

            lore_id_to_unlock = "lore_element115_casing_opened"
            unlocked_ids = self.drone_system.unlock_lore_entry_by_id(lore_id_to_unlock)
            if unlocked_ids:
                lore_details = self.drone_system.get_lore_entry_details(unlocked_ids[0])
                message = lore_details.get("title", "E-115 Casing Opened") if lore_details else "E-115 Casing Opened"
                self.game_controller.set_story_message(f"Puzzle Solved: {message} data acquired.")
            else:
                 self.game_controller.set_story_message("Puzzle Solved. Data re-analyzed.")
        
        self.game_controller.play_sound('level_up')

    def exit_ring_puzzle(self, puzzle_was_solved=False):
        """Cleans up and exits the ring puzzle state."""
        self.ring_puzzle_active_flag = False
        
        if puzzle_was_solved and self.last_interacted_terminal_for_ring_puzzle:
            self.last_interacted_terminal_for_ring_puzzle.kill()
        
        self.current_ring_puzzle = None
        self.last_interacted_terminal_for_ring_puzzle = None
        
        self.scene_manager.set_game_state(GAME_STATE_PLAYING)

        if self.game_controller.ui_manager and self.game_controller.ui_manager.build_menu:
            if self.game_controller.scene_manager.get_current_state() == GAME_STATE_MAZE_DEFENSE and \
               hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase:
                self.game_controller.ui_manager.build_menu.activate()
            else:
                 self.game_controller.ui_manager.build_menu.deactivate()
        logger.info("PuzzleController: Exited Ring Puzzle.")


    def try_activate_architect_vault_terminal(self, terminal_idx_pressed):
        """
        Attempts to activate one of the Architect's Vault entry terminals.
        """
        if not (0 <= terminal_idx_pressed < len(self.architect_vault_terminals_activated)):
            logger.warning(f"PuzzleController: Invalid terminal index {terminal_idx_pressed} pressed.")
            return

        if self.architect_vault_terminals_activated[terminal_idx_pressed]:
            self.game_controller.play_sound('ui_denied')
            self.game_controller.set_story_message(f"Terminal {terminal_idx_pressed + 1} already active.")
            return

        fragment_ids_for_puzzle_terminals = ["cf_alpha", "cf_beta", "cf_gamma"]
        required_fragment_id = fragment_ids_for_puzzle_terminals[terminal_idx_pressed]
        
        # Get core fragment details from settings manager
        core_fragments = settings_manager.get_core_fragment_details()
        frag_conf = next((details for _, details in core_fragments.items() 
                         if details and details.get("id") == required_fragment_id), None)
        required_fragment_name = frag_conf.get("name", "a Core Fragment") if frag_conf else "a Core Fragment"

        if self.drone_system and self.drone_system.has_collected_fragment(required_fragment_id):
            self.architect_vault_terminals_activated[terminal_idx_pressed] = True
            
            for t_sprite in self.architect_vault_puzzle_terminals_group:
                if hasattr(t_sprite, 'terminal_id') and t_sprite.terminal_id == terminal_idx_pressed:
                    t_sprite.is_active = True
                    break
            
            self.game_controller.play_sound('vault_barrier_disable')
            self.game_controller.set_story_message(f"Terminal {terminal_idx_pressed + 1} ({required_fragment_name}) activated!")

            if all(self.architect_vault_terminals_activated):
                self.game_controller.set_story_message("All terminals active. Lockdown disengaged. Prepare for Gauntlet!")
                if hasattr(self.game_controller, 'start_architect_vault_gauntlet'):
                    self.game_controller.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_GAUNTLET)
        else:
            self.game_controller.set_story_message(f"Terminal {terminal_idx_pressed + 1} requires {required_fragment_name}.")
            self.game_controller.play_sound('ui_denied')

    def reset_puzzles_state(self):
        """Resets the state of all puzzles, e.g., for a new game."""
        self.current_ring_puzzle = None
        self.ring_puzzle_active_flag = False
        self.ring_puzzle_solved_this_session = False
        self.last_interacted_terminal_for_ring_puzzle = None
        
        total_fragments = get_setting("collectibles", "TOTAL_CORE_FRAGMENTS_NEEDED", 3)
        self.architect_vault_terminals_activated = [False] * total_fragments
        logger.info("PuzzleController: All puzzle states reset.")

    def draw_active_puzzle(self, surface):
        """Draws the UI for the currently active puzzle."""
        current_game_state = self.scene_manager.get_current_state()
        if current_game_state == GAME_STATE_RING_PUZZLE:
            if self.ring_puzzle_active_flag and self.current_ring_puzzle:
                self.current_ring_puzzle.draw(surface)