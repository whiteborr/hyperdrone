# hyperdrone_core/puzzle_controller.py
import pygame
import os # For asset paths

import game_settings as gs
from game_settings import (
    GAME_STATE_RING_PUZZLE, GAME_STATE_PLAYING, GAME_STATE_MAZE_DEFENSE, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    TOTAL_CORE_FRAGMENTS_NEEDED, CORE_FRAGMENT_DETAILS # For Architect's Vault puzzle
)

# Import puzzle-related entities and modules
from entities import AncientAlienTerminal # For triggering puzzles
from .ring_puzzle_module import RingPuzzle # The actual Ring Puzzle logic

class PuzzleController:
    """
    Manages puzzle mechanics, interactions, and state within the game.
    This includes the Ring Puzzle and the Architect's Vault entry terminals.
    """
    def __init__(self, game_controller_ref):
        """
        Initializes the PuzzleController.

        Args:
            game_controller_ref: A reference to the main GameController instance.
        """
        self.game_controller = game_controller_ref
        self.player = None # Will be set by GameController
        self.drone_system = None # Will be set by GameController (for lore, rewards)
        self.scene_manager = None # Will be set by GameController (to change game states)
        
        # Ring Puzzle specific attributes
        self.current_ring_puzzle = None
        self.ring_puzzle_active_flag = False # Tracks if the ring puzzle UI should be shown
        self.ring_puzzle_solved_this_session = False # To prevent re-triggering rewards for the same terminal
        self.last_interacted_terminal_for_ring_puzzle = None

        # Architect's Vault Entry Puzzle specific attributes
        self.architect_vault_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
        self.architect_vault_puzzle_terminals_group = pygame.sprite.Group() # Group of terminal sprites

        print("PuzzleController initialized.")

    def set_active_entities(self, player, drone_system, scene_manager, alien_terminals_group=None, architect_vault_terminals_group=None):
        """
        Sets references to currently active game entities relevant to puzzles.
        Called by GameController.
        """
        self.player = player
        self.drone_system = drone_system
        self.scene_manager = scene_manager
        if alien_terminals_group is not None:
            # This group might be managed by GameController or a future CollectiblesManager
            # For now, PuzzleController can get a reference if it needs to directly check them.
            pass # self.alien_terminals_group = alien_terminals_group (if needed)
        if architect_vault_terminals_group is not None:
            self.architect_vault_puzzle_terminals_group = architect_vault_terminals_group


    def update(self, current_time_ms, current_game_state):
        """
        Main update loop for the PuzzleController.
        Called every frame by the GameController.

        Args:
            current_time_ms (int): The current game time in milliseconds.
            current_game_state (str): The current game state from SceneManager.
        """
        if current_game_state == GAME_STATE_RING_PUZZLE:
            if self.ring_puzzle_active_flag and self.current_ring_puzzle:
                self.current_ring_puzzle.update()
                if self.current_ring_puzzle.is_solved() and \
                   not self.current_ring_puzzle.active and \
                   not self.ring_puzzle_solved_this_session:
                    self._handle_ring_puzzle_solved()
        
        elif current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            # Logic for Architect's Vault entry puzzle (e.g., checking terminal states)
            # This might be mostly event-driven (activating terminals)
            pass


    def handle_input(self, event, current_game_state):
        """
        Handles player input relevant to puzzles.
        Called by EventManager.
        Args:
            event: The pygame event.
            current_game_state (str): The current game state.
        Returns:
            bool: True if the event was consumed by the puzzle system, False otherwise.
        """
        if current_game_state == GAME_STATE_RING_PUZZLE:
            if self.ring_puzzle_active_flag and self.current_ring_puzzle:
                self.current_ring_puzzle.handle_input(event) # RingPuzzle handles its own keys (1,2,3)
                # Check for ESC to exit puzzle
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.exit_ring_puzzle()
                    return True
                # Check for ENTER/SPACE if puzzle is solved but not yet dismissed
                if self.current_ring_puzzle.is_solved() and \
                   not self.current_ring_puzzle.active and \
                   event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE):
                    self.exit_ring_puzzle(puzzle_was_solved=True)
                    return True
                return True # Event consumed by ring puzzle

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
        Initializes and starts the Ring Puzzle.
        Called by GameController when player interacts with an AncientAlienTerminal.
        """
        if not self.scene_manager or not self.drone_system:
            print("PuzzleController: SceneManager or DroneSystem not available to start ring puzzle.")
            return

        # Check if this specific terminal has already been solved in this session/save
        if self.drone_system.has_puzzle_terminal_been_solved(terminal_sprite.item_id):
            self.game_controller.set_story_message("This terminal's data has already been extracted.")
            self.game_controller.play_sound('ui_denied')
            return


        ring_configs = [ # Example configuration
            ("ring1.png", 6), ("ring2.png", 8), ("ring3.png", 12)
        ]
        puzzle_asset_path = os.path.join("assets", "images", "puzzles")
        
        try:
            self.current_ring_puzzle = RingPuzzle(
                gs.get_game_setting("WIDTH"), 
                gs.get_game_setting("HEIGHT"),
                ring_configs,
                assets_path=puzzle_asset_path
            )
            self.ring_puzzle_active_flag = True
            self.ring_puzzle_solved_this_session = False # Reset for this new puzzle instance
            self.last_interacted_terminal_for_ring_puzzle = terminal_sprite
            self.scene_manager.set_game_state(GAME_STATE_RING_PUZZLE)
            self.game_controller.play_sound('ui_confirm') # Sound for puzzle start
            print(f"PuzzleController: Ring Puzzle started for terminal {terminal_sprite.item_id}.")
        except Exception as e:
            print(f"PuzzleController: Error initializing RingPuzzle: {e}")
            self.current_ring_puzzle = None
            self.ring_puzzle_active_flag = False
            # Revert to playing state if puzzle fails to load
            self.scene_manager.set_game_state(GAME_STATE_PLAYING)


    def _handle_ring_puzzle_solved(self):
        """Handles the logic when the Ring Puzzle is solved."""
        print("PuzzleController: Ring Puzzle solved!")
        self.ring_puzzle_solved_this_session = True
        # Rewards and lore unlocks
        if self.drone_system:
            self.drone_system.add_player_cores(gs.get_game_setting("RING_PUZZLE_CORE_REWARD", 750))
            # Mark this specific terminal as solved
            if self.last_interacted_terminal_for_ring_puzzle:
                self.drone_system.mark_puzzle_terminal_as_solved(self.last_interacted_terminal_for_ring_puzzle.item_id)

            # Unlock specific lore related to this puzzle
            lore_id_to_unlock = "lore_element115_casing_opened" # Example
            unlocked_ids = self.drone_system.unlock_lore_entry_by_id(lore_id_to_unlock)
            if unlocked_ids:
                lore_details = self.drone_system.get_lore_entry_details(unlocked_ids[0])
                message = lore_details.get("title", "E-115 Casing Opened") if lore_details else "E-115 Casing Opened"
                self.game_controller.set_story_message(f"Puzzle Solved: {message} data acquired.")
            else:
                 self.game_controller.set_story_message("Puzzle Solved. Data re-analyzed.")
        
        self.game_controller.play_sound('level_up') # Or a specific puzzle_solve sound

        # The RingPuzzle itself sets its 'active' to False.
        # EventManager will handle exiting the puzzle screen on ENTER/SPACE.

    def exit_ring_puzzle(self, puzzle_was_solved=False):
        """Cleans up and exits the ring puzzle state."""
        self.ring_puzzle_active_flag = False
        
        if puzzle_was_solved and self.last_interacted_terminal_for_ring_puzzle:
            # Remove the terminal sprite from the game world
            self.last_interacted_terminal_for_ring_puzzle.kill()
            print(f"PuzzleController: Terminal {self.last_interacted_terminal_for_ring_puzzle.item_id} removed after solving puzzle.")
        
        self.current_ring_puzzle = None
        self.last_interacted_terminal_for_ring_puzzle = None
        
        # Return to the previous game state (likely PLAYING)
        # GameController might have stored the previous state or default to PLAYING
        # For now, assume it goes back to PLAYING.
        self.scene_manager.set_game_state(GAME_STATE_PLAYING)
        # Ensure build menu is handled correctly if returning to defense mode
        if self.game_controller.ui_manager and self.game_controller.ui_manager.build_menu:
            if self.game_controller.scene_manager.get_current_state() == GAME_STATE_MAZE_DEFENSE and \
               hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase:
                self.game_controller.ui_manager.build_menu.activate()
            else:
                 self.game_controller.ui_manager.build_menu.deactivate()
        print("PuzzleController: Exited Ring Puzzle.")


    def try_activate_architect_vault_terminal(self, terminal_idx_pressed):
        """
        Attempts to activate one of the Architect's Vault entry terminals.
        Called by EventManager based on player input (keys 1, 2, 3).
        """
        if not (0 <= terminal_idx_pressed < len(self.architect_vault_terminals_activated)):
            print(f"PuzzleController: Invalid terminal index {terminal_idx_pressed} pressed.")
            return

        if self.architect_vault_terminals_activated[terminal_idx_pressed]:
            self.game_controller.play_sound('ui_denied') # Already active
            self.game_controller.set_story_message(f"Terminal {terminal_idx_pressed + 1} already active.")
            return

        # Determine required fragment for this terminal
        fragment_ids_for_puzzle_terminals = ["cf_alpha", "cf_beta", "cf_gamma"]
        required_fragment_id = fragment_ids_for_puzzle_terminals[terminal_idx_pressed]
        
        frag_conf = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == required_fragment_id), None)
        required_fragment_name = frag_conf.get("name", "a Core Fragment") if frag_conf else "a Core Fragment"

        if self.drone_system and self.drone_system.has_collected_fragment(required_fragment_id):
            self.architect_vault_terminals_activated[terminal_idx_pressed] = True
            
            # Visual feedback for the terminal sprite (GameController might handle this)
            for t_sprite in self.architect_vault_puzzle_terminals_group:
                if hasattr(t_sprite, 'terminal_id') and t_sprite.terminal_id == terminal_idx_pressed:
                    t_sprite.is_active = True # Mark sprite as active
                    # GameController's drawing logic can change color based on t_sprite.is_active
                    break
            
            self.game_controller.play_sound('vault_barrier_disable')
            self.game_controller.set_story_message(f"Terminal {terminal_idx_pressed + 1} ({required_fragment_name}) activated!")

            if all(self.architect_vault_terminals_activated):
                self.game_controller.set_story_message("All terminals active. Lockdown disengaged. Prepare for Gauntlet!")
                # GameController will transition state after a delay or on message clear
                if hasattr(self.game_controller, 'start_architect_vault_gauntlet'):
                     # This is a direct call, GameController might want a delay
                    self.game_controller.scene_manager.set_game_state(gs.GAME_STATE_ARCHITECT_VAULT_GAUNTLET)
        else:
            self.game_controller.set_story_message(f"Terminal {terminal_idx_pressed + 1} requires {required_fragment_name}.")
            self.game_controller.play_sound('ui_denied')

    def reset_puzzles_state(self):
        """Resets the state of all puzzles, e.g., for a new game."""
        self.current_ring_puzzle = None
        self.ring_puzzle_active_flag = False
        self.ring_puzzle_solved_this_session = False
        self.last_interacted_terminal_for_ring_puzzle = None
        
        self.architect_vault_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
        # Clearing the group might be handled by GameController when it re-initializes scenes
        # self.architect_vault_puzzle_terminals_group.empty() 
        print("PuzzleController: All puzzle states reset.")

    def draw_active_puzzle(self, surface):
        """
        Draws the UI for the currently active puzzle.
        Called by UIManager.
        """
        current_game_state = self.scene_manager.get_current_state()
        if current_game_state == GAME_STATE_RING_PUZZLE:
            if self.ring_puzzle_active_flag and self.current_ring_puzzle:
                # The RingPuzzle class has its own draw method that takes the surface
                self.current_ring_puzzle.draw(surface)
        
        # Architect's Vault entry puzzle might not have a dedicated draw method here,
        # as its elements (terminals) are part of the game world drawn by GameController.
        # However, hints or status for that puzzle could be drawn here if needed.

