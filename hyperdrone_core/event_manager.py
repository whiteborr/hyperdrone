# hyperdrone_core/event_manager.py
import sys
import pygame

import game_settings as gs
from game_settings import (
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS,
    GAME_STATE_DRONE_SELECT, GAME_STATE_CODEX,
    GAME_STATE_BONUS_LEVEL_PLAYING, 
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT, 
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_RING_PUZZLE, GAME_STATE_GAME_INTRO_SCROLL, GAME_STATE_MAZE_DEFENSE
)

class EventManager:
    def __init__(self, game_controller_ref, scene_manager_ref, 
                 combat_controller_ref, puzzle_controller_ref, ui_flow_controller_ref):
        """
        Initializes the EventManager.
        Args:
            game_controller_ref: Reference to the main GameController.
            scene_manager_ref: Reference to the SceneManager.
            combat_controller_ref: Reference to the CombatController.
            puzzle_controller_ref: Reference to the PuzzleController.
            ui_flow_controller_ref: Reference to the UIFlowController.
        """
        self.game_controller = game_controller_ref
        self.scene_manager = scene_manager_ref
        self.combat_controller = combat_controller_ref
        self.puzzle_controller = puzzle_controller_ref
        self.ui_flow_controller = ui_flow_controller_ref
        
    def process_events(self):
        """Processes all Pygame events and delegates actions."""
        current_time_ms = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()
        keys_pressed = pygame.key.get_pressed() 
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get(): 
            if event.type == pygame.QUIT:
                self.game_controller.quit_game()
                return 

            if hasattr(self.game_controller, 'story_message_active') and \
               self.game_controller.story_message_active and \
               event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and \
               current_game_state != GAME_STATE_GAME_INTRO_SCROLL:
                self.game_controller.story_message_active = False
                self.game_controller.play_sound('ui_select', 0.5)
                continue 
                
            event_consumed = False
            
            if current_game_state in [GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT,
                                      GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD,
                                      GAME_STATE_CODEX, GAME_STATE_ENTER_NAME,
                                      GAME_STATE_GAME_OVER, GAME_STATE_GAME_INTRO_SCROLL,
                                      GAME_STATE_ARCHITECT_VAULT_SUCCESS, 
                                      GAME_STATE_ARCHITECT_VAULT_FAILURE]:
                if self.ui_flow_controller.handle_input(event, current_game_state):
                    event_consumed = True
            
            elif not event_consumed and current_game_state == GAME_STATE_RING_PUZZLE:
                if self.puzzle_controller.handle_input(event, current_game_state):
                    event_consumed = True
            
            elif not event_consumed and current_game_state in [
                GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
                GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
                GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT,
                GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
                GAME_STATE_MAZE_DEFENSE 
            ]:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p: 
                        self.game_controller.toggle_pause()
                        event_consumed = True
                    
                    if self.game_controller.paused:
                        self.game_controller.handle_pause_menu_input(event.key, current_game_state)
                        event_consumed = True
                    else: # Game is not paused
                        # Player specific actions (if player exists and is alive)
                        # This block is for states where the player is actively controlled.
                        if self.game_controller.player and self.game_controller.player.alive and \
                           current_game_state != GAME_STATE_MAZE_DEFENSE: # Exclude maze defense from this player block
                            if event.key == pygame.K_UP:
                                self.game_controller.player_actions.start_moving_forward()
                                event_consumed = True
                            elif event.key == pygame.K_DOWN:
                                self.game_controller.player_actions.stop_moving_forward()
                                event_consumed = True
                            elif event.key == pygame.K_c:
                                self.game_controller.player_actions.try_activate_cloak(current_time_ms)
                                event_consumed = True
                            elif event.key == pygame.K_s: 
                                if self.game_controller.player.cycle_weapon_state(force_cycle=True):
                                    self.game_controller.play_sound('ui_select')
                                event_consumed = True
                        
                        # Architect's Vault Entry Puzzle specific inputs
                        if current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
                            if self.puzzle_controller.handle_input(event, current_game_state):
                                event_consumed = True
                        
                        # Maze Defense build phase inputs (checked when not paused, regardless of player object)
                        if current_game_state == GAME_STATE_MAZE_DEFENSE and \
                           hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase:
                            if event.key == pygame.K_t:
                                self.combat_controller.try_place_turret(mouse_pos)
                                event_consumed = True
                            elif event.key == pygame.K_u:
                                selected_turret = getattr(self.game_controller.ui_manager.build_menu, 'selected_turret_on_map', None)
                                if selected_turret:
                                    self.combat_controller.try_upgrade_turret(selected_turret)
                                else: self.game_controller.play_sound('ui_denied')
                                event_consumed = True
                            elif event.key == pygame.K_SPACE: 
                                if self.combat_controller.wave_manager:
                                    self.combat_controller.wave_manager.manual_start_next_wave()
                                event_consumed = True
                
                elif event.type == pygame.MOUSEBUTTONDOWN: 
                    if current_game_state == GAME_STATE_MAZE_DEFENSE and \
                       hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase and \
                       self.game_controller.ui_manager.build_menu:
                        
                        if self.game_controller.ui_manager.build_menu.handle_input(event, mouse_pos):
                            event_consumed = True
                        elif event.button == 3 and not self.game_controller.ui_manager.build_menu.is_mouse_over_build_menu(mouse_pos):
                            clicked_turret = None
                            for t in self.game_controller.turrets_group: 
                                if t.rect.collidepoint(mouse_pos):
                                    clicked_turret = t; break
                            if clicked_turret:
                                self.game_controller.ui_manager.build_menu.set_selected_turret(clicked_turret)
                                self.game_controller.play_sound('ui_select', 0.6)
                            else:
                                self.game_controller.ui_manager.build_menu.clear_selected_turret()
                            event_consumed = True 

            if event_consumed:
                continue 

        # Continuous Input Handling
        is_active_player_control_state_for_continuous_input = current_game_state in [
            GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT,
            GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
            # GAME_STATE_MAZE_DEFENSE # Player is not typically controlled with continuous input here
        ]

        if not self.game_controller.paused and self.game_controller.player and self.game_controller.player.alive and \
           is_active_player_control_state_for_continuous_input:
            
            self.game_controller.player_actions.handle_continuous_input(keys_pressed, current_time_ms)

            can_shoot_in_current_state_continuous = current_game_state in [
                GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
                GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT,
                GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
                # GAME_STATE_MAZE_DEFENSE # Add if player can shoot with spacebar in defense
            ]
            if can_shoot_in_current_state_continuous and keys_pressed[pygame.K_SPACE]:
                self.game_controller.player_actions.shoot(current_time_ms)

