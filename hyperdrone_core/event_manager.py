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
    def __init__(self, game_controller_ref, scene_manager_ref, combat_controller_ref, puzzle_controller_ref, ui_flow_controller_ref):
        self.game_controller = game_controller_ref
        self.scene_manager = scene_manager_ref
        self.combat_controller = combat_controller_ref
        self.puzzle_controller = puzzle_controller_ref
        self.ui_flow_controller = ui_flow_controller_ref
        logger.info("EventManager initialized.")

    def process_events(self):
        current_time_ms = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()
        
        # --- Handle continuous key presses for camera panning (ONLY in maze defense) ---
        if current_game_state == GAME_STATE_MAZE_DEFENSE and not self.game_controller.paused and self.game_controller.camera:
            keys = pygame.key.get_pressed()
            dx, dy = 0, 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]: dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = 1
            if dx != 0 or dy != 0:
                self.game_controller.camera.pan(dx, dy)

        # --- Event Loop (for discrete events) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game_controller.quit_game()
            
            # --- Mouse Wheel for Zoom (ONLY in maze defense) ---
            if event.type == pygame.MOUSEWHEEL and current_game_state == GAME_STATE_MAZE_DEFENSE and self.game_controller.camera:
                if event.y > 0: self.game_controller.camera.zoom(1.1)
                elif event.y < 0: self.game_controller.camera.zoom(0.9)

            # --- Keyboard Down Events ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.handle_escape_key(current_game_state)
                if self.ui_flow_controller.handle_key_input(event.key, current_game_state): continue
                is_gameplay_state = current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or current_game_state.startswith("architect_vault")
                if is_gameplay_state and not self.game_controller.paused: self.game_controller.player_actions.handle_key_down(event)
                if current_game_state == GAME_STATE_MAZE_DEFENSE and not self.game_controller.paused:
                    if event.key == pygame.K_SPACE:
                        if self.combat_controller.wave_manager: self.combat_controller.wave_manager.manual_start_next_wave()
                if event.key == pygame.K_p and (is_gameplay_state or current_game_state == GAME_STATE_MAZE_DEFENSE): self.game_controller.toggle_pause()
                if self.puzzle_controller.handle_input(event, current_game_state): continue

            # --- Keyboard Up Events ---
            if event.type == pygame.KEYUP:
                 if not self.game_controller.paused: self.game_controller.player_actions.handle_key_up(event)
            
            # --- Mouse Button Down Events ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Turret actions ONLY in maze defense
                if current_game_state == GAME_STATE_MAZE_DEFENSE and not self.game_controller.paused and self.game_controller.camera:
                    screen_pos = event.pos
                    if self.game_controller.ui_manager.build_menu and self.game_controller.ui_manager.build_menu.is_mouse_over_build_menu(screen_pos):
                        self.game_controller.ui_manager.build_menu.handle_input(event, screen_pos); continue
                    world_pos = self.game_controller.camera.screen_to_world(screen_pos)
                    if event.button == 1: self.combat_controller.try_place_turret(world_pos)
                    elif event.button == 3: self.combat_controller.try_upgrade_clicked_turret(world_pos)
                else:
                    if self.game_controller.ui_manager.build_menu: self.game_controller.ui_manager.build_menu.handle_input(event, event.pos)

        # Continuous Input for Player Drone (standard modes)
        is_gameplay_state_for_continuous = current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or current_game_state.startswith("architect_vault")
        if is_gameplay_state_for_continuous and not self.game_controller.paused:
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
        # Continuous Input for Player Drone (standard modes)
        is_gameplay_state_for_continuous = current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or current_game_state.startswith("architect_vault")
        if is_gameplay_state_for_continuous and not self.game_controller.paused:
            self.game_controller.player_actions.update_player_movement_and_actions(current_time_ms)