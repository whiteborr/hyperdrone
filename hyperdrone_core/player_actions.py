# hyperdrone_core/player_actions.py
import pygame
import game_settings as gs

class PlayerActions:
    """Handles direct player-initiated actions like movement, shooting, and abilities."""
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        # self.move_forward flag is no longer needed here; state is in PlayerDrone
        self.turn_left = False
        self.turn_right = False
        self.is_shooting = False

    def handle_key_down(self, event):
        """Processes key press events."""
        player = self.game_controller.player
        if not player or not player.alive:
            return

        # --- UPDATED MOVEMENT LOGIC ---
        if event.key == pygame.K_w or event.key == pygame.K_UP:
            player.is_cruising = True # Toggle cruise control ON
            if player.active_powerup_type == "speed_boost":
                player.attempt_speed_boost_activation()
        
        elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
            player.is_cruising = False # Toggle cruise control OFF
        # --- END UPDATED MOVEMENT LOGIC ---

        elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
            self.turn_left = True
        
        elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
            self.turn_right = True
        
        elif event.key == pygame.K_SPACE:
            self.is_shooting = True
        
        elif event.key == pygame.K_c:
            player.cycle_weapon_state()
            self.game_controller.play_sound('ui_select')

        elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
            if player.special_ability == "phantom_cloak":
                if player.try_activate_cloak(pygame.time.get_ticks()):
                    self.game_controller.play_sound('cloak_activate')

    def handle_key_up(self, event):
        """Processes key release events."""
        # --- UPDATED MOVEMENT LOGIC ---
        # Releasing the UP key no longer stops movement
        # if event.key == pygame.K_w or event.key == pygame.K_UP:
        #     self.move_forward = False
        # --- END UPDATED MOVEMENT LOGIC ---
        
        if event.key == pygame.K_a or event.key == pygame.K_LEFT:
            self.turn_left = False
        
        elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
            self.turn_right = False
        
        elif event.key == pygame.K_SPACE:
            self.is_shooting = False

    def update_player_movement_and_actions(self, current_time_ms):
        """Called every frame to update player state based on held keys."""
        # The 'cruising' state is now managed entirely by the PlayerDrone object.
        # This method only needs to handle turning and shooting, which are still based on held keys.
        if self.turn_left:
            self.turn("left")
        
        if self.turn_right:
            self.turn("right")

        if self.is_shooting:
            self.shoot(current_time_ms)

    def turn(self, direction):
        if self.game_controller.player and self.game_controller.player.alive:
            self.game_controller.player.rotate(direction)

    def shoot(self, current_time_ms):
        if not self.game_controller.player or not self.game_controller.player.alive:
            return
            
        player = self.game_controller.player
        maze_ref = self.game_controller.maze
        combat_ctrl = self.game_controller.combat_controller
        enemies_group_ref = combat_ctrl.enemy_manager.get_sprites()

        if combat_ctrl.boss_active:
            enemies_group_ref.add(combat_ctrl.maze_guardian)

        player.shoot(
            sound_asset_key='shoot',
            missile_sound_asset_key='missile_launch',
            maze=maze_ref,
            enemies_group=enemies_group_ref
        )
