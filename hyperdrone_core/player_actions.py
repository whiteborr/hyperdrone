# hyperdrone_core/player_actions.py
import pygame
import game_settings as gs

class PlayerActions:
    """
    Handles player-initiated actions by interpreting keyboard input and
    updating the player's state for movement, shooting, and abilities.
    """
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        self.move_forward = False
        self.move_backward = False
        self.turn_left = False
        self.turn_right = False
        self.is_shooting = False

    def handle_key_down(self, event):
        """Processes key press events to set action flags."""
        if event.key in (pygame.K_w, pygame.K_UP):
            self.move_forward = True
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            self.move_backward = True
        elif event.key in (pygame.K_a, pygame.K_LEFT):
            self.turn_left = True
        elif event.key in (pygame.K_d, pygame.K_RIGHT):
            self.turn_right = True
        elif event.key == pygame.K_SPACE:
            self.is_shooting = True
        
        player = self.game_controller.player
        if not player or not player.alive:
            return

        if event.key == pygame.K_c:
            player.cycle_weapon_state()
            self.game_controller.play_sound('ui_select')
        elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            if hasattr(player, 'special_ability') and player.special_ability == "phantom_cloak":
                if player.try_activate_cloak(pygame.time.get_ticks()):
                    self.game_controller.play_sound('cloak_activate')

    def handle_key_up(self, event):
        """Processes key release events to reset action flags."""
        if event.key in (pygame.K_w, pygame.K_UP):
            self.move_forward = False
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            self.move_backward = False
        elif event.key in (pygame.K_a, pygame.K_LEFT):
            self.turn_left = False
        elif event.key in (pygame.K_d, pygame.K_RIGHT):
            self.turn_right = False
        elif event.key == pygame.K_SPACE:
            self.is_shooting = False

    def update_player_movement_and_actions(self, current_time_ms):
        """
        Called every frame to update the player's state based on the action flags.
        """
        player = self.game_controller.player
        if not player or not player.alive:
            return
            
        # Set movement direction based on flags
        move_direction = 0
        if self.move_forward:
            move_direction = 1
        elif self.move_backward:
            move_direction = -1
        player.set_movement(move_direction)

        # Handle turning
        if self.turn_left:
            player.rotate("left")
        if self.turn_right:
            player.rotate("right")
        
        # Handle shooting
        if self.is_shooting:
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