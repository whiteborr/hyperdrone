import pygame
import sys

# Import all necessary game state constants from game_settings.py
try:
    from game_settings import (
        GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
        GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
        GAME_STATE_BONUS_LEVEL_PLAYING, # Assuming this state is still potentially used
        GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
        GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
        GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE
        # Add any other game state constants if they are used for event handling
    )
except ImportError:
    print("Critical Error (event_manager.py): Could not import game state constants from game_settings.py.")
    # Fallback string values if import fails, though this will likely lead to issues.
    GAME_STATE_MAIN_MENU = "main_menu"
    GAME_STATE_PLAYING = "playing"
    GAME_STATE_GAME_OVER = "game_over"
    GAME_STATE_LEADERBOARD = "leaderboard_display"
    GAME_STATE_ENTER_NAME = "enter_name"
    GAME_STATE_SETTINGS = "settings_menu"
    GAME_STATE_DRONE_SELECT = "drone_select_menu"
    GAME_STATE_BONUS_LEVEL_PLAYING = "bonus_level_playing"
    GAME_STATE_ARCHITECT_VAULT_INTRO = "architect_vault_intro"
    GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE = "architect_vault_entry_puzzle"
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET = "architect_vault_gauntlet"
    GAME_STATE_ARCHITECT_VAULT_EXTRACTION = "architect_vault_extraction"
    GAME_STATE_ARCHITECT_VAULT_SUCCESS = "architect_vault_success"
    GAME_STATE_ARCHITECT_VAULT_FAILURE = "architect_vault_failure"

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
        self.player_name_input_cache = "" # Cache for name entry during GAME_STATE_ENTER_NAME

    def process_events(self):
        """
        Processes all Pygame events and calls appropriate handlers
        on the game_controller or scene_manager.
        """
        current_time = pygame.time.get_ticks() # Get current time once per event loop
        current_game_state = self.scene_manager.get_current_state()
        keys = pygame.key.get_pressed() # Get state of all keys for continuous checks

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if hasattr(self.game_controller, 'quit_game'):
                    self.game_controller.quit_game()
                else: # Fallback if game_controller doesn't have quit_game
                    pygame.quit()
                    sys.exit()

            if event.type == pygame.KEYDOWN:
                # --- Quit Game (Global for specific states) ---
                if event.key == pygame.K_q and current_game_state in [
                    GAME_STATE_GAME_OVER, GAME_STATE_LEADERBOARD, GAME_STATE_MAIN_MENU,
                ] and not self.game_controller.paused:
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

                # --- Gameplay (Regular, Bonus, Architect's Vault Combat/Puzzle) ---
                elif current_game_state in [GAME_STATE_PLAYING,
                                            GAME_STATE_BONUS_LEVEL_PLAYING,
                                            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
                                            GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
                                            GAME_STATE_ARCHITECT_VAULT_EXTRACTION]:
                    if event.key == pygame.K_p: # Pause
                        if hasattr(self.game_controller, 'toggle_pause'):
                            self.game_controller.toggle_pause()

                    if self.game_controller.paused: # Handle input when paused
                        if hasattr(self.game_controller, 'handle_pause_menu_input'):
                            self.game_controller.handle_pause_menu_input(event.key, current_game_state)
                    else: # Handle input when not paused (active gameplay)
                        if self.game_controller.player and self.game_controller.player.alive:
                            if event.key == pygame.K_UP: # MODIFIED: Start continuous forward movement
                                if hasattr(self.game_controller.player_actions, 'start_moving_forward'):
                                    self.game_controller.player_actions.start_moving_forward()
                            elif event.key == pygame.K_DOWN: # MODIFIED: Stop continuous forward movement
                                if hasattr(self.game_controller.player_actions, 'stop_moving_forward'):
                                    self.game_controller.player_actions.stop_moving_forward()
                            elif event.key == pygame.K_c: # Cloak ability
                                if hasattr(self.game_controller.player_actions, 'try_activate_cloak'):
                                    self.game_controller.player_actions.try_activate_cloak(current_time)
                            elif event.key == pygame.K_s: # Cycle weapon
                                if hasattr(self.game_controller.player, 'cycle_weapon_state'):
                                    if self.game_controller.player.cycle_weapon_state(force_cycle=True):
                                        if hasattr(self.game_controller, 'play_sound'):
                                            self.game_controller.play_sound('ui_select')

                        # Architect's Vault Entry Puzzle specific inputs
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
                
                # --- Architect's Vault Intro ---
                elif current_game_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)

                # --- Post-Game / Post-Vault States (Success/Failure) ---
                elif current_game_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS or \
                     current_game_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_m:
                        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

                # --- Game Over ---
                elif current_game_state == GAME_STATE_GAME_OVER:
                    if hasattr(self.game_controller, 'handle_game_over_input'):
                        self.game_controller.handle_game_over_input(event.key)

                # --- Enter Name for Leaderboard ---
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

                # --- Leaderboard Display ---
                elif current_game_state == GAME_STATE_LEADERBOARD:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_m:
                        if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select')
                        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

            # REMOVED KEYUP handling for K_UP to stop movement.
            # The player now continues moving forward after K_UP is pressed, until K_DOWN is pressed.

        # --- Continuous Key Presses (Handled every frame, outside the event loop for smooth actions) ---
        if not self.game_controller.paused and self.game_controller.player and self.game_controller.player.alive:
            is_active_player_control_state_continuous = current_game_state in [
                GAME_STATE_PLAYING,
                GAME_STATE_BONUS_LEVEL_PLAYING,
                GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
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