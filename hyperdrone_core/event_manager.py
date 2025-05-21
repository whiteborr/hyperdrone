import sys
import pygame

import game_settings as gs # Alias for game_settings
from game_settings import (
    # Import specific game state constants used for comparisons
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE
    # Other settings would be accessed via gs.get_game_setting() or gs.CONSTANT_NAME if needed
)
# If SceneManager needed to be type-hinted or directly instantiated (it's passed as ref):
# from .scene_manager import SceneManager

class EventManager:
    def __init__(self, game_controller_ref, scene_manager_ref):
        """
        Initializes the EventManager.
        Args:
            game_controller_ref: Reference to the main game controller.
            scene_manager_ref: Reference to the SceneManager.
        """
        self.game_controller = game_controller_ref #
        self.scene_manager = scene_manager_ref #
        self.player_name_input_cache = "" # Cache for name entry during GAME_STATE_ENTER_NAME

    def process_events(self): #
        """
        Processes all Pygame events and calls appropriate handlers
        on the game_controller or scene_manager.
        """
        current_time = pygame.time.get_ticks() #
        current_game_state = self.scene_manager.get_current_state() #
        keys = pygame.key.get_pressed() #

        for event in pygame.event.get(): #
            if event.type == pygame.QUIT: #
                if hasattr(self.game_controller, 'quit_game'): #
                    self.game_controller.quit_game() #
                else: #
                    pygame.quit() #
                    sys.exit() #

            if event.type == pygame.KEYDOWN: #
                # --- Quit Game (Global for specific states) ---
                if event.key == pygame.K_q and current_game_state in [
                    GAME_STATE_GAME_OVER, GAME_STATE_LEADERBOARD, GAME_STATE_MAIN_MENU,
                ] and not self.game_controller.paused: #
                    if hasattr(self.game_controller, 'quit_game'): #
                         self.game_controller.quit_game() #
                    continue # Event handled

                # --- Main Menu ---
                if current_game_state == GAME_STATE_MAIN_MENU: #
                    if hasattr(self.game_controller, 'handle_main_menu_input'): #
                        self.game_controller.handle_main_menu_input(event.key) #

                # --- Drone Select ---
                elif current_game_state == GAME_STATE_DRONE_SELECT: #
                    if hasattr(self.game_controller, 'handle_drone_select_input'): #
                        self.game_controller.handle_drone_select_input(event.key) #

                # --- Settings ---
                elif current_game_state == GAME_STATE_SETTINGS: #
                    if hasattr(self.game_controller, 'handle_settings_input'): #
                        self.game_controller.handle_settings_input(event.key) #

                # --- Gameplay (Regular, Bonus, Architect's Vault Combat/Puzzle) ---
                elif current_game_state in [GAME_STATE_PLAYING,
                                            GAME_STATE_BONUS_LEVEL_PLAYING,
                                            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
                                            GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
                                            GAME_STATE_ARCHITECT_VAULT_EXTRACTION]: #
                    if event.key == pygame.K_p: # Pause
                        if hasattr(self.game_controller, 'toggle_pause'): #
                            self.game_controller.toggle_pause() #

                    if self.game_controller.paused: # Handle input when paused
                        if hasattr(self.game_controller, 'handle_pause_menu_input'): #
                            self.game_controller.handle_pause_menu_input(event.key, current_game_state) #
                    else: # Handle input when not paused (active gameplay)
                        if self.game_controller.player and self.game_controller.player.alive: #
                            if event.key == pygame.K_UP: # MODIFIED: Start continuous forward movement
                                if hasattr(self.game_controller.player_actions, 'start_moving_forward'): #
                                    self.game_controller.player_actions.start_moving_forward() #
                            elif event.key == pygame.K_DOWN: # MODIFIED: Stop continuous forward movement
                                if hasattr(self.game_controller.player_actions, 'stop_moving_forward'): #
                                    self.game_controller.player_actions.stop_moving_forward() #
                            elif event.key == pygame.K_c: # Cloak ability
                                if hasattr(self.game_controller.player_actions, 'try_activate_cloak'): #
                                    self.game_controller.player_actions.try_activate_cloak(current_time) #
                            elif event.key == pygame.K_s: # Cycle weapon
                                if hasattr(self.game_controller.player, 'cycle_weapon_state'): #
                                    if self.game_controller.player.cycle_weapon_state(force_cycle=True): #
                                        if hasattr(self.game_controller, 'play_sound'): #
                                            self.game_controller.play_sound('ui_select') #

                        # Architect's Vault Entry Puzzle specific inputs
                        if current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: #
                            if event.key == pygame.K_1: #
                                if hasattr(self.game_controller, 'try_activate_vault_terminal'): #
                                    self.game_controller.try_activate_vault_terminal(0) #
                            elif event.key == pygame.K_2: #
                                if hasattr(self.game_controller, 'try_activate_vault_terminal'): #
                                    self.game_controller.try_activate_vault_terminal(1) #
                            elif event.key == pygame.K_3: #
                                if hasattr(self.game_controller, 'try_activate_vault_terminal'): #
                                    self.game_controller.try_activate_vault_terminal(2) #
                
                # --- Architect's Vault Intro ---
                elif current_game_state == GAME_STATE_ARCHITECT_VAULT_INTRO: #
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE: #
                        self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE) #

                # --- Post-Game / Post-Vault States (Success/Failure) ---
                elif current_game_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS or \
                     current_game_state == GAME_STATE_ARCHITECT_VAULT_FAILURE: #
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_m: #
                        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU) #

                # --- Game Over ---
                elif current_game_state == GAME_STATE_GAME_OVER: #
                    if hasattr(self.game_controller, 'handle_game_over_input'): #
                        self.game_controller.handle_game_over_input(event.key) #

                # --- Enter Name for Leaderboard ---
                elif current_game_state == GAME_STATE_ENTER_NAME: #
                    if event.key == pygame.K_RETURN: #
                        if hasattr(self.game_controller, 'submit_leaderboard_name'): #
                            self.game_controller.submit_leaderboard_name(self.player_name_input_cache) #
                        self.player_name_input_cache = "" #
                    elif event.key == pygame.K_BACKSPACE: #
                        self.player_name_input_cache = self.player_name_input_cache[:-1] #
                    elif len(self.player_name_input_cache) < 6 and event.unicode.isalpha(): #
                        self.player_name_input_cache += event.unicode.upper() #
                    
                    if hasattr(self.game_controller, 'update_player_name_input_display'): #
                        self.game_controller.update_player_name_input_display(self.player_name_input_cache) #

                # --- Leaderboard Display ---
                elif current_game_state == GAME_STATE_LEADERBOARD: #
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_m: #
                        if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select') #
                        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU) #

            #KeyUp event for stopping forward movement (if K_UP was released)
            # This part of the original code was:
            # elif event.type == pygame.KEYUP:
            #     if current_game_state == GAME_STATE_PLAYING or \
            #        current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING or \
            #        current_game_state.startswith("architect_vault"):
            #         if not self.game_controller.paused and self.game_controller.player and self.game_controller.player.alive:
            #             if event.key == pygame.K_UP:
            #                 if hasattr(self.game_controller.player_actions, 'stop_moving_forward_on_key_up'):
            #                     self.game_controller.player_actions.stop_moving_forward_on_key_up()
            # Based on your player_actions.py, K_DOWN now stops movement, and K_UP starts it.
            # The player_actions.py:stop_moving_forward_on_key_up is no longer strictly necessary
            # if K_DOWN is the dedicated "stop" button.
            # However, if you want K_UP release to also stop, that logic would remain.
            # For now, I'm keeping the event loop focused on KEYDOWN for these primary actions
            # as per the most recent player_actions.py structure.


        # --- Continuous Key Presses (Handled every frame, outside the event loop for smooth actions) ---
        if not self.game_controller.paused and self.game_controller.player and self.game_controller.player.alive: #
            is_active_player_control_state_continuous = current_game_state in [
                GAME_STATE_PLAYING,
                GAME_STATE_BONUS_LEVEL_PLAYING,
                GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, # Player can still move
                GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
                GAME_STATE_ARCHITECT_VAULT_EXTRACTION
            ] #

            if is_active_player_control_state_continuous: #
                # Player rotation (continuous)
                if hasattr(self.game_controller.player_actions, 'handle_continuous_input'): #
                    self.game_controller.player_actions.handle_continuous_input(keys, current_time) #

                # Player shooting (continuous if space is held)
                can_shoot_in_current_state = current_game_state in [
                    GAME_STATE_PLAYING,
                    GAME_STATE_BONUS_LEVEL_PLAYING,
                    GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
                    GAME_STATE_ARCHITECT_VAULT_EXTRACTION
                ] #
                if can_shoot_in_current_state and keys[pygame.K_SPACE]: #
                    if hasattr(self.game_controller.player_actions, 'shoot'): #
                        self.game_controller.player_actions.shoot(current_time) #