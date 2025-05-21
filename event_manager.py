import pygame
import sys

from game_settings import (
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_BONUS_LEVEL_PLAYING, # Old bonus, might be deprecated
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, 
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE
    # Import other necessary constants from game_settings as needed
)
# It's generally better if EventManager doesn't directly import game_settings for values,
# but rather gets necessary info (like current_time) passed to its methods or via game_controller.
# However, for game state constants, direct import is fine.

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
        self.player_name_input_cache = "" # Cache for name entry

    def process_events(self):
        """
        Processes all Pygame events and calls appropriate handlers
        on the game_controller or scene_manager.
        """
        current_time = pygame.time.get_ticks() # Get current time once per event loop
        current_game_state = self.scene_manager.get_current_state()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if hasattr(self.game_controller, 'quit_game'):
                    self.game_controller.quit_game()
                else: # Fallback if game_controller doesn't have quit_game
                    pygame.quit()
                    sys.exit()

            if event.type == pygame.KEYDOWN:
                # --- Quit Game (Global) ---
                if event.key == pygame.K_q and current_game_state in [
                    GAME_STATE_GAME_OVER, GAME_STATE_LEADERBOARD
                ]: # Specific states where Q is quit
                    if hasattr(self.game_controller, 'quit_game'):
                         self.game_controller.quit_game()
                    continue # Event handled

                # --- Main Menu ---
                if current_game_state == GAME_STATE_MAIN_MENU:
                    if hasattr(self.game_controller, 'handle_main_menu_input'):
                        self.game_controller.handle_main_menu_input(event.key)
                
                # --- Drone Select ---
                elif current_game_state == GAME_STATE_DRONE_SELECT:
                    if hasattr(self.game_controller, 'handle_drone_select_input'):
                        self.game_controller.handle_drone_select_input(event.key)
                
                # --- Settings ---
                elif current_game_state == GAME_STATE_SETTINGS:
                    if hasattr(self.game_controller, 'handle_settings_input'):
                        self.game_controller.handle_settings_input(event.key)

                # --- Gameplay (Regular & Old Bonus) & Architect's Vault Combat ---
                elif current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, 
                                            GAME_STATE_ARCHITECT_VAULT_GAUNTLET, 
                                            GAME_STATE_ARCHITECT_VAULT_EXTRACTION]:
                    if event.key == pygame.K_p:
                        if hasattr(self.game_controller, 'toggle_pause'):
                            self.game_controller.toggle_pause()
                    
                    if self.game_controller.paused: # Paused gameplay input
                        if hasattr(self.game_controller, 'handle_pause_menu_input'):
                            self.game_controller.handle_pause_menu_input(event.key)
                    else: # Active gameplay input (movement direction changes)
                        if self.game_controller.player and self.game_controller.player.alive:
                            if event.key == pygame.K_UP:
                                if hasattr(self.game_controller.player_actions, 'start_moving_forward'):
                                    self.game_controller.player_actions.start_moving_forward()
                            elif event.key == pygame.K_DOWN:
                                if hasattr(self.game_controller.player_actions, 'stop_moving_forward'):
                                    self.game_controller.player_actions.stop_moving_forward()
                            # Rotation and cloak are handled by get_pressed below for continuous input

                # --- Architect's Vault Specific (Non-Combat) ---
                elif current_game_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
                
                elif current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
                    if event.key == pygame.K_p: # Allow pausing puzzle
                        if hasattr(self.game_controller, 'toggle_pause'):
                            self.game_controller.toggle_pause()
                    elif self.game_controller.paused:
                         if event.key == pygame.K_ESCAPE: # Exit to main menu from pause
                            if hasattr(self.game_controller, 'unpause_and_set_state'):
                                self.game_controller.unpause_and_set_state(GAME_STATE_MAIN_MENU)
                    else: # Active puzzle input
                        if event.key == pygame.K_1: 
                            if hasattr(self.game_controller, 'try_activate_vault_terminal'):
                                self.game_controller.try_activate_vault_terminal(0)
                        elif event.key == pygame.K_2:
                            if hasattr(self.game_controller, 'try_activate_vault_terminal'):
                                self.game_controller.try_activate_vault_terminal(1)
                        elif event.key == pygame.K_3:
                            if hasattr(self.game_controller, 'try_activate_vault_terminal'):
                                self.game_controller.try_activate_vault_terminal(2)
                        # Allow movement during puzzle
                        if self.game_controller.player and self.game_controller.player.alive:
                            if event.key == pygame.K_UP:
                                if hasattr(self.game_controller.player_actions, 'start_moving_forward'):
                                    self.game_controller.player_actions.start_moving_forward()
                            elif event.key == pygame.K_DOWN:
                                if hasattr(self.game_controller.player_actions, 'stop_moving_forward'):
                                    self.game_controller.player_actions.stop_moving_forward()


                # --- Post-Game / Post-Vault States ---
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
                            self.player_name_input_cache = "" # Clear cache
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name_input_cache = self.player_name_input_cache[:-1]
                    elif len(self.player_name_input_cache) < 6 and event.unicode.isalpha():
                        self.player_name_input_cache += event.unicode.upper()
                    # Update the game_controller's copy of the name for display
                    if hasattr(self.game_controller, 'update_player_name_input_display'):
                        self.game_controller.update_player_name_input_display(self.player_name_input_cache)

                elif current_game_state == GAME_STATE_LEADERBOARD:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_m:
                        if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select')
                        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            
            # Handle KEYUP for stopping movement (more reliable than checking not pressed)
            if event.type == pygame.KEYUP:
                if current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, 
                                          GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, 
                                          GAME_STATE_ARCHITECT_VAULT_GAUNTLET, 
                                          GAME_STATE_ARCHITECT_VAULT_EXTRACTION]:
                    if not self.game_controller.paused and self.game_controller.player and self.game_controller.player.alive:
                        if event.key == pygame.K_UP:
                            if hasattr(self.game_controller.player_actions, 'stop_moving_forward_on_key_up'): # New method in player_actions
                                self.game_controller.player_actions.stop_moving_forward_on_key_up()


        # --- Continuous Key Presses (Outside the event loop for smooth actions) ---
        if not self.game_controller.paused and self.game_controller.player and self.game_controller.player.alive:
            keys = pygame.key.get_pressed()
            
            # Player rotation and cloak (applies to multiple active states)
            is_active_player_control_state = current_game_state in [
                GAME_STATE_PLAYING, 
                GAME_STATE_BONUS_LEVEL_PLAYING,
                GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, # Allow rotation in puzzle
                GAME_STATE_ARCHITECT_VAULT_GAUNTLET, 
                GAME_STATE_ARCHITECT_VAULT_EXTRACTION
            ]
            if is_active_player_control_state:
                if hasattr(self.game_controller.player_actions, 'handle_continuous_input'):
                    self.game_controller.player_actions.handle_continuous_input(keys, current_time)

            # Player shooting (only in combat states)
            can_shoot_in_current_state = current_game_state in [
                GAME_STATE_PLAYING, 
                GAME_STATE_BONUS_LEVEL_PLAYING, # Assuming old bonus allows shooting
                GAME_STATE_ARCHITECT_VAULT_GAUNTLET, 
                GAME_STATE_ARCHITECT_VAULT_EXTRACTION
            ]
            if can_shoot_in_current_state:
                if keys[pygame.K_SPACE]:
                    if hasattr(self.game_controller.player_actions, 'shoot'):
                        # Event manager doesn't know about maze or enemies directly,
                        # player_actions.shoot will get them from game_controller.player
                        self.game_controller.player_actions.shoot(current_time)
