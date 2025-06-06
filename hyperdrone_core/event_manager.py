# hyperdrone_core/event_manager.py
import pygame
import sys
import logging

import game_settings as gs
from game_settings import (
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
    GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, GAME_STATE_CODEX,
    GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_RING_PUZZLE, GAME_STATE_MAZE_DEFENSE
)

logger = logging.getLogger(__name__)

class EventManager:
    """
    Handles all Pygame events and user input, routing them to the appropriate controllers.
    """
    def __init__(self, game_controller_ref, scene_manager_ref, combat_controller_ref, puzzle_controller_ref, ui_flow_controller_ref):
        self.game_controller = game_controller_ref
        self.scene_manager = scene_manager_ref
        self.combat_controller = combat_controller_ref
        self.puzzle_controller = puzzle_controller_ref
        self.ui_flow_controller = ui_flow_controller_ref
        logger.info("EventManager initialized.")

    def process_events(self):
        """
        Processes all events in the Pygame event queue and handles continuous key presses.
        This is called once per frame from the main game loop.
        """
        current_time_ms = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()

        # --- Event Loop (for discrete events like key presses, mouse clicks) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game_controller.quit_game()
            
            # --- Keyboard Down Events ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.handle_escape_key(current_game_state)
                
                # Let the UIFlowController handle its own menu navigation first
                if self.ui_flow_controller.handle_key_input(event.key, current_game_state):
                    continue # Input was handled by UI flow, no further processing needed

                # Gameplay-specific key presses
                is_gameplay_state = current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
                                    current_game_state.startswith("architect_vault")

                if is_gameplay_state and not self.game_controller.paused:
                    self.game_controller.player_actions.handle_key_down(event)
                
                if current_game_state == GAME_STATE_MAZE_DEFENSE and not self.game_controller.paused:
                    if event.key == pygame.K_t:
                        # Assuming mouse position is needed for turret placement
                        mouse_pos = pygame.mouse.get_pos()
                        self.combat_controller.try_place_turret(mouse_pos)
                    elif event.key == pygame.K_u:
                        if self.game_controller.ui_manager.build_menu and \
                           self.game_controller.ui_manager.build_menu.selected_turret_on_map:
                           self.combat_controller.try_upgrade_turret(self.game_controller.ui_manager.build_menu.selected_turret_on_map)
                    elif event.key == pygame.K_SPACE:
                        if self.combat_controller.wave_manager:
                           self.combat_controller.wave_manager.try_start_next_wave(current_time_ms)
                
                if event.key == pygame.K_p and (is_gameplay_state or current_game_state == GAME_STATE_MAZE_DEFENSE):
                    self.game_controller.toggle_pause()

                # Puzzle-specific input
                if self.puzzle_controller.handle_input(event, current_game_state):
                    continue

            # --- Keyboard Up Events ---
            if event.type == pygame.KEYUP:
                 if not self.game_controller.paused:
                    self.game_controller.player_actions.handle_key_up(event)
            
            # --- Mouse Events ---
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP or event.type == pygame.MOUSEMOTION:
                mouse_pos = pygame.mouse.get_pos()
                if self.game_controller.ui_manager and self.game_controller.ui_manager.build_menu:
                    if self.game_controller.ui_manager.build_menu.handle_input(event, mouse_pos):
                        continue # Input was handled by the build menu

        # --- Continuous Input (for actions that happen as long as a key is held) ---
        # The PlayerActions class now uses internal flags (e.g., self.move_forward)
        # which are set by the KEYDOWN/KEYUP events. This method updates the player's
        # state based on those flags.
        is_gameplay_state_for_continuous = current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
                                           current_game_state.startswith("architect_vault")

        if is_gameplay_state_for_continuous and not self.game_controller.paused:
            # <<< FIX: Changed method name from handle_continuous_input to update_player_movement_and_actions >>>
            self.game_controller.player_actions.update_player_movement_and_actions(current_time_ms)


    def handle_escape_key(self, current_game_state):
        """Handles the logic for when the ESCAPE key is pressed."""
        if current_game_state in [GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, GAME_STATE_CODEX, GAME_STATE_ENTER_NAME]:
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
        
        elif current_game_state.startswith("architect_vault"):
            # In the vault, ESC should probably pause the game or bring up a menu
            # to confirm exiting, as it's a special gameplay mode.
            self.game_controller.toggle_pause()
        
        elif current_game_state in [GAME_STATE_RING_PUZZLE]:
            self.puzzle_controller.exit_ring_puzzle(puzzle_was_solved=False)

        elif current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, GAME_STATE_MAZE_DEFENSE]:
            self.game_controller.toggle_pause()

        elif current_game_state == GAME_STATE_MAIN_MENU:
            # In the main menu, ESC could either do nothing or quit the game.
            # Let's make it do nothing to prevent accidental quits.
            pass
