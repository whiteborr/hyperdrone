# hyperdrone_core/event_manager.py
import sys
import pygame

import game_settings as gs 
from game_settings import (
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_CODEX,
    GAME_STATE_BONUS_LEVEL_PLAYING, 
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_RING_PUZZLE, GAME_STATE_GAME_INTRO_SCROLL 
)

# Ensure GAME_STATE_MAZE_DEFENSE is available
if not hasattr(gs, 'GAME_STATE_MAZE_DEFENSE'):
    GAME_STATE_MAZE_DEFENSE = "maze_defense_mode" 
    print("EventManager: GAME_STATE_MAZE_DEFENSE not found in game_settings, using local fallback.")
else:
    GAME_STATE_MAZE_DEFENSE = gs.GAME_STATE_MAZE_DEFENSE


class EventManager:
    def __init__(self, game_controller_ref, scene_manager_ref):
        """
        Initializes the EventManager.
        Args:
            game_controller_ref: Reference to the main GameController.
            scene_manager_ref: Reference to the SceneManager.
        """
        self.game_controller = game_controller_ref
        self.scene_manager = scene_manager_ref
        self.player_name_input_cache = "" 

    def process_events(self):
        """Processes all Pygame events and delegates actions to the GameController or SceneManager."""
        current_time = pygame.time.get_ticks() 
        current_game_state = self.scene_manager.get_current_state()
        keys = pygame.key.get_pressed() 
        mouse_pos = pygame.mouse.get_pos() # Get mouse position once per frame

        for event in pygame.event.get(): 
            if event.type == pygame.QUIT: 
                if hasattr(self.game_controller, 'quit_game'):
                    self.game_controller.quit_game()
                else: 
                    pygame.quit()
                    sys.exit()

            # --- MOUSEBUTTONDOWN EVENTS (Primarily for UI interaction in build mode) ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                if current_game_state == GAME_STATE_MAZE_DEFENSE and \
                   hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase and \
                   hasattr(self.game_controller.ui_manager, 'build_menu') and self.game_controller.ui_manager.build_menu:
                    
                    # Let BuildMenu handle its own panel clicks first
                    if self.game_controller.ui_manager.build_menu.handle_input(event, mouse_pos):
                        continue # Event consumed by BuildMenu panel

                    # If click was not on the panel, it might be on the game world (e.g., selecting a turret)
                    # Right-click to select/deselect turret on map
                    if event.button == 3: # Right mouse button
                        if not self.game_controller.ui_manager.build_menu.is_mouse_over_build_menu(mouse_pos):
                            clicked_turret = None
                            for t in self.game_controller.turrets:
                                if t.rect.collidepoint(mouse_pos):
                                    clicked_turret = t
                                    break
                            if clicked_turret:
                                self.game_controller.ui_manager.build_menu.set_selected_turret(clicked_turret)
                                if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_select', 0.6)
                            else:
                                self.game_controller.ui_manager.build_menu.clear_selected_turret()
                            # No continue here, as right-click on map doesn't prevent other actions unless specifically designed


            # --- KEYDOWN EVENTS (Single key presses) ---
            if event.type == pygame.KEYDOWN:
                if hasattr(self.game_controller, 'story_message_active') and \
                   self.game_controller.story_message_active and \
                   hasattr(self.game_controller, 'story_message') and \
                   self.game_controller.story_message and \
                   current_game_state != GAME_STATE_GAME_INTRO_SCROLL:
                    if event.key == pygame.K_SPACE: 
                        self.game_controller.story_message_active = False
                        if hasattr(self.game_controller, 'play_sound'):
                            self.game_controller.play_sound('ui_select', 0.5)
                        print("EventManager: Story message dismissed by SPACE.")
                        continue 
                
                if current_game_state == GAME_STATE_GAME_INTRO_SCROLL:
                    if hasattr(self.game_controller, 'intro_sequence_finished') and \
                       self.game_controller.intro_sequence_finished:
                        if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                            print("EventManager: Intro sequence finished, proceeding to game.")
                            if hasattr(self.game_controller, 'initialize_game_session'):
                                self.game_controller.initialize_game_session() 
                            self.scene_manager.set_game_state(GAME_STATE_PLAYING)
                            if hasattr(self.game_controller, 'play_sound'):
                                self.game_controller.play_sound('ui_confirm')
                            continue 
                    else: 
                        if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_ESCAPE:
                             if hasattr(self.game_controller, 'skip_current_intro_screen'):
                                self.game_controller.skip_current_intro_screen()
                                print("EventManager: Skipped current intro screen.")
                             continue 

                if event.key == pygame.K_q and current_game_state in [
                    GAME_STATE_MAIN_MENU, GAME_STATE_LEADERBOARD, GAME_STATE_CODEX, GAME_STATE_GAME_OVER
                ] and not (hasattr(self.game_controller, 'paused') and self.game_controller.paused):
                    if hasattr(self.game_controller, 'quit_game'):
                         self.game_controller.quit_game()
                    continue

                if current_game_state == GAME_STATE_RING_PUZZLE:
                    puzzle_handled_event = False
                    if self.game_controller.current_ring_puzzle and \
                       self.game_controller.ring_puzzle_active_flag:
                        self.game_controller.current_ring_puzzle.handle_input(event)
                        puzzle_handled_event = True

                    if event.key == pygame.K_ESCAPE: 
                        print("EventManager: Exiting ring puzzle via ESCAPE.")
                        self.game_controller.ring_puzzle_active_flag = False
                        self.scene_manager.set_game_state(GAME_STATE_PLAYING) 
                        if self.game_controller.ui_manager.build_menu: # Deactivate build menu if returning to defense mode
                            if self.game_controller.is_build_phase: self.game_controller.ui_manager.build_menu.activate()
                            else: self.game_controller.ui_manager.build_menu.deactivate()
                        continue

                    if self.game_controller.current_ring_puzzle and \
                       self.game_controller.current_ring_puzzle.is_solved() and \
                       not self.game_controller.current_ring_puzzle.active: 
                       if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                            print("EventManager: Continuing after solved ring puzzle.")
                            if self.game_controller.last_interacted_terminal:
                                print(f"EventManager: Removing last interacted terminal: {self.game_controller.last_interacted_terminal.item_id}")
                                self.game_controller.last_interacted_terminal.kill()
                                self.game_controller.last_interacted_terminal = None
                            
                            self.game_controller.ring_puzzle_active_flag = False
                            self.scene_manager.set_game_state(GAME_STATE_PLAYING) # Or previous state
                            if self.game_controller.ui_manager.build_menu: # Deactivate build menu if returning to defense mode
                                if self.game_controller.is_build_phase: self.game_controller.ui_manager.build_menu.activate()
                                else: self.game_controller.ui_manager.build_menu.deactivate()
                            continue
                    if puzzle_handled_event: continue 
                
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
                    elif event.key == pygame.K_ESCAPE:
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
                
                elif current_game_state == GAME_STATE_MAZE_DEFENSE:
                    if event.key == pygame.K_p: # Pause in defense mode
                        if hasattr(self.game_controller, 'toggle_pause'):
                            self.game_controller.toggle_pause()
                    
                    if self.game_controller.paused: 
                         if hasattr(self.game_controller, 'handle_pause_menu_input'):
                            self.game_controller.handle_pause_menu_input(event.key, current_game_state)
                    else: # Active defense mode inputs
                        # Player movement/shooting (if player is controllable in defense)
                        if self.game_controller.player and self.game_controller.player.alive:
                            if event.key == pygame.K_UP:
                                if hasattr(self.game_controller.player_actions, 'start_moving_forward'):
                                    self.game_controller.player_actions.start_moving_forward()
                            elif event.key == pygame.K_DOWN:
                                if hasattr(self.game_controller.player_actions, 'stop_moving_forward'):
                                    self.game_controller.player_actions.stop_moving_forward()
                        
                        # Build Phase Actions
                        if hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase:
                            if event.key == pygame.K_t: # 'T' to place turret
                                if hasattr(self.game_controller, 'try_place_turret'):
                                    self.game_controller.try_place_turret(mouse_pos) # mouse_pos from top of loop
                            elif event.key == pygame.K_u: # 'U' to upgrade selected turret
                                if self.game_controller.ui_manager.build_menu and \
                                   self.game_controller.ui_manager.build_menu.selected_turret_on_map:
                                    if hasattr(self.game_controller, 'try_upgrade_turret'):
                                        self.game_controller.try_upgrade_turret(self.game_controller.ui_manager.build_menu.selected_turret_on_map)
                                else:
                                    if hasattr(self.game_controller, 'play_sound'): self.game_controller.play_sound('ui_denied', 0.5)
                                    print("EventManager: 'U' pressed, but no turret selected for upgrade.")
                            elif event.key == pygame.K_SPACE: # SPACE to start next wave
                                if self.game_controller.wave_manager:
                                    self.game_controller.wave_manager.manual_start_next_wave()
                        # else: Combat phase, 'T' and 'U' might do nothing or different things

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
            
        # --- CONTINUOUS INPUT HANDLING (Keys held down) ---
        if not (hasattr(self.game_controller, 'story_message_active') and self.game_controller.story_message_active) and \
           current_game_state not in [GAME_STATE_GAME_INTRO_SCROLL, GAME_STATE_RING_PUZZLE] :
            
            if not self.game_controller.paused and self.game_controller.player and self.game_controller.player.alive:
                is_active_player_control_state_continuous = current_game_state in [
                    GAME_STATE_PLAYING,
                    GAME_STATE_BONUS_LEVEL_PLAYING,
                    GAME_STATE_MAZE_DEFENSE, # Player can move/shoot in defense mode
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
                        GAME_STATE_MAZE_DEFENSE, 
                        GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
                        GAME_STATE_ARCHITECT_VAULT_EXTRACTION
                    ]
                    if can_shoot_in_current_state and keys[pygame.K_SPACE]: 
                        if hasattr(self.game_controller.player_actions, 'shoot'):
                            self.game_controller.player_actions.shoot(current_time)
