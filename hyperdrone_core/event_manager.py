# hyperdrone_core/event_manager.py
import sys
import pygame

import game_settings as gs # Alias for game_settings
from game_settings import (
    # Import specific game state constants used for comparisons
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_CODEX,
    GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_RING_PUZZLE # Added the new game state for the ring puzzle
    # Other settings would be accessed via gs.get_game_setting() or gs.CONSTANT_NAME if needed
)

class EventManager:
    def __init__(self, game_controller_ref, scene_manager_ref):
        """
        Initializes the EventManager.
        Args:
            game_controller_ref: Reference to the main game controller.
            scene_manager_ref: Reference to the SceneManager.
        """
        self.game_controller = game_controller_ref
        self.scene_manager = scene_manager_ref
        self.player_name_input_cache = ""

    def process_events(self):
        """
        Processes all Pygame events and calls appropriate handlers
        on the game_controller or scene_manager.
        """
        current_time = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if hasattr(self.game_controller, 'quit_game'):
                    self.game_controller.quit_game()
                else:
                    pygame.quit()
                    sys.exit()

            if event.type == pygame.KEYDOWN:
                # Global quit shortcut for certain states (if not paused)
                if event.key == pygame.K_q and current_game_state in [
                    GAME_STATE_GAME_OVER, GAME_STATE_LEADERBOARD, GAME_STATE_MAIN_MENU, GAME_STATE_CODEX,
                ] and not (hasattr(self.game_controller, 'paused') and self.game_controller.paused):
                    if hasattr(self.game_controller, 'quit_game'):
                         self.game_controller.quit_game()
                    continue # Event handled

                # --- Handle Ring Puzzle Input ---
                if current_game_state == GAME_STATE_RING_PUZZLE:
                    if self.game_controller.current_ring_puzzle and \
                       self.game_controller.ring_puzzle_active_flag:
                        
                        # Pass event to the puzzle's own handler first
                        # The puzzle module handles K_1, K_2, K_3 (up to K_9) for rotations
                        self.game_controller.current_ring_puzzle.handle_input(event)

                        if event.key == pygame.K_ESCAPE:
                            print("EventManager: Exiting ring puzzle via ESCAPE.")
                            self.game_controller.ring_puzzle_active_flag = False
                            # Optional: self.game_controller.current_ring_puzzle = None 
                            # if hasattr(self.game_controller, 'paused') and self.game_controller.paused:
                            # self.game_controller.toggle_pause() # Unpause if game was paused for puzzle
                            self.scene_manager.set_game_state(GAME_STATE_PLAYING) # Or previous valid state
                            continue 

                        # If puzzle is solved, Enter/Space might also transition out
                        # The puzzle sets its 'active' flag to False once solved.
                        if self.game_controller.current_ring_puzzle.is_solved() and \
                           not self.game_controller.current_ring_puzzle.active:
                           if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                                print("EventManager: Continuing after solved ring puzzle.")
                                self.game_controller.ring_puzzle_active_flag = False
                                # Decide what happens next, e.g., back to gameplay or a reward screen
                                self.scene_manager.set_game_state(GAME_STATE_PLAYING)
                                # self.game_controller.current_ring_puzzle = None # Clear puzzle instance
                                continue
                    # If puzzle is not active (e.g. error loading, or already solved and waiting for exit input)
                    elif event.key == pygame.K_ESCAPE: # Still allow ESC to exit this scene
                         print("EventManager: Exiting (potentially non-interactive) ring puzzle scene via ESCAPE.")
                         self.scene_manager.set_game_state(GAME_STATE_PLAYING) # Or main menu
                         continue
                    # After handling puzzle input, continue to next event, skip other state checks for this keydown
                    continue 


                # --- Existing event handling for other states ---
                if current_game_state == GAME_STATE_MAIN_MENU:
                    if hasattr(self.game_controller, 'handle_main_menu_input'):
                        self.game_controller.handle_main_menu_input(event.key)

                elif current_game_state == GAME_STATE_DRONE_SELECT:
                    if hasattr(self.game_controller, 'handle_drone_select_input'):
                        self.game_controller.handle_drone_select_input(event.key)

                elif current_game_state == GAME_STATE_SETTINGS:
                    if hasattr(self.game_controller, 'handle_settings_input'):
                        self.game_controller.handle_settings_input(event.key)
                
                elif current_game_state == GAME_STATE_CODEX:
                    if hasattr(self.game_controller, 'handle_codex_input'):
                        self.game_controller.handle_codex_input(event.key)
                    elif event.key == pygame.K_ESCAPE: # Fallback ESC for Codex if not handled internally
                        if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select')
                        if not (hasattr(self.game_controller, 'codex_current_view') and self.game_controller.codex_current_view != "categories"):
                             self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

                elif current_game_state in [GAME_STATE_PLAYING,
                                            GAME_STATE_BONUS_LEVEL_PLAYING,
                                            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
                                            GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
                                            GAME_STATE_ARCHITECT_VAULT_EXTRACTION]:
                    if event.key == pygame.K_p:
                        if hasattr(self.game_controller, 'toggle_pause'):
                            self.game_controller.toggle_pause()

                    if self.game_controller.paused:
                        if hasattr(self.game_controller, 'handle_pause_menu_input'):
                            self.game_controller.handle_pause_menu_input(event.key, current_game_state)
                    else:
                        if self.game_controller.player and self.game_controller.player.alive:
                            if event.key == pygame.K_UP:
                                if hasattr(self.game_controller.player_actions, 'start_moving_forward'):
                                    self.game_controller.player_actions.start_moving_forward()
                            elif event.key == pygame.K_DOWN:
                                if hasattr(self.game_controller.player_actions, 'stop_moving_forward'):
                                    self.game_controller.player_actions.stop_moving_forward()
                            elif event.key == pygame.K_c:
                                if hasattr(self.game_controller.player_actions, 'try_activate_cloak'):
                                    self.game_controller.player_actions.try_activate_cloak(current_time)
                            elif event.key == pygame.K_s:
                                if hasattr(self.game_controller.player, 'cycle_weapon_state'):
                                    if self.game_controller.player.cycle_weapon_state(force_cycle=True):
                                        if hasattr(self.game_controller, 'play_sound'):
                                            self.game_controller.play_sound('ui_select')

                        if current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
                            if event.key == pygame.K_1:
                                if hasattr(self.game_controller, 'try_activate_vault_terminal'):
                                    self.game_controller.try_activate_vault_terminal(0)
                            elif event.key == pygame.K_2:
                                if hasattr(self.game_controller, 'try_activate_vault_terminal'):
                                    self.game_controller.try_activate_vault_terminal(1)
                            elif event.key == pygame.K_3:
                                if hasattr(self.game_controller, 'try_activate_vault_terminal'):
                                    self.game_controller.try_activate_vault_terminal(2)
                
                elif current_game_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)

                elif current_game_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS or \
                     current_game_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_m:
                        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

                elif current_game_state == GAME_STATE_GAME_OVER:
                    if hasattr(self.game_controller, 'handle_game_over_input'):
                        self.game_controller.handle_game_over_input(event.key)

                elif current_game_state == GAME_STATE_ENTER_NAME:
                    if event.key == pygame.K_RETURN:
                        if hasattr(self.game_controller, 'submit_leaderboard_name'):
                            self.game_controller.submit_leaderboard_name(self.player_name_input_cache)
                        self.player_name_input_cache = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name_input_cache = self.player_name_input_cache[:-1]
                    elif len(self.player_name_input_cache) < 6 and event.unicode.isalpha():
                        self.player_name_input_cache += event.unicode.upper()
                    
                    if hasattr(self.game_controller, 'update_player_name_input_display'):
                        self.game_controller.update_player_name_input_display(self.player_name_input_cache)

                elif current_game_state == GAME_STATE_LEADERBOARD:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_m:
                        if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select')
                        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            # End of event.type == pygame.KEYDOWN block
        # End of event loop

        # Continuous input handling for player movement and shooting
        # This should NOT interfere with the ring puzzle state if it's a modal overlay
        if current_game_state != GAME_STATE_RING_PUZZLE: # Check if not in puzzle state
            if not self.game_controller.paused and self.game_controller.player and self.game_controller.player.alive:
                is_active_player_control_state_continuous = current_game_state in [
                    GAME_STATE_PLAYING,
                    GAME_STATE_BONUS_LEVEL_PLAYING,
                    GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, # Player might still move even if puzzle is different
                    GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
                    GAME_STATE_ARCHITECT_VAULT_EXTRACTION
                ]

                if is_active_player_control_state_continuous:
                    if hasattr(self.game_controller.player_actions, 'handle_continuous_input'):
                        self.game_controller.player_actions.handle_continuous_input(keys, current_time)

                    can_shoot_in_current_state = current_game_state in [
                        GAME_STATE_PLAYING,
                        GAME_STATE_BONUS_LEVEL_PLAYING,
                        GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
                        GAME_STATE_ARCHITECT_VAULT_EXTRACTION
                    ]
                    if can_shoot_in_current_state and keys[pygame.K_SPACE]:
                        if hasattr(self.game_controller.player_actions, 'shoot'):
                            self.game_controller.player_actions.shoot(current_time)