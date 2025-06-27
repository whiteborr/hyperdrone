# hyperdrone_core/player_actions.py
from pygame.time import get_ticks
from pygame import K_w, K_UP, K_s, K_DOWN, K_a, K_LEFT, K_d, K_RIGHT, K_SPACE, K_LSHIFT, K_RSHIFT, K_f, K_F1, K_TAB

class PlayerActions:
    """
    Handles player-initiated actions by interpreting keyboard input and
    updating the player's state for movement, shooting, and abilities.
    """
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        self.turn_left = False
        self.turn_right = False
        self.is_shooting = False

    def handle_key_down(self, event):
        """
        Processes key press events to set action flags. This includes toggling
        the drone's cruise control for movement.
        """
        player = self.game_controller.player
        if not player or not player.alive:
            return

        # Toggle cruise control ON with forward key.
        if event.key == K_w or event.key == K_UP:
            player.is_cruising = True
            # Activate speed boost if armed
            if hasattr(player.powerup_manager, 'speed_boost_armed') and player.powerup_manager.speed_boost_armed:
                player.activate_speed_boost()
        
        # Toggle cruise control OFF with backward key.
        elif event.key == K_s or event.key == K_DOWN:
            player.is_cruising = False

        elif event.key == K_a or event.key == K_LEFT:
            self.turn_left = True
        
        elif event.key == K_d or event.key == K_RIGHT:
            self.turn_right = True
        
        elif event.key == K_SPACE:
            self.is_shooting = True
        
        elif event.key == K_LSHIFT or event.key == K_RSHIFT:
            if hasattr(player, 'special_ability') and player.special_ability == "phantom_cloak":
                if player.try_activate_cloak(get_ticks()):
                    if hasattr(self.game_controller, 'play_sound'):
                        self.game_controller.play_sound('cloak_activate')
                        
        # NEW: Key binding for active abilities (e.g., 'F' key)
        elif event.key == K_f:
            if hasattr(player, 'activate_ability'):
                player.activate_ability("temporary_barricade", self.game_controller) # Pass game_controller_ref

        # Weapon cycling with Tab key
        elif event.key == K_TAB:
            if hasattr(player, 'cycle_weapon_state'):
                player.cycle_weapon_state()
                if hasattr(self.game_controller, 'play_sound'):
                    self.game_controller.play_sound('ui_confirm')

        # Emergency key to eliminate stuck enemies (F1)
        elif event.key == K_F1:
            if hasattr(self.game_controller, 'combat_controller') and hasattr(self.game_controller.combat_controller, 'enemy_manager'):
                enemy_count = self.game_controller.combat_controller.enemy_manager.get_active_enemies_count()
                if enemy_count > 0:
                    for enemy in list(self.game_controller.combat_controller.enemy_manager.enemies):
                        if enemy.alive:
                            enemy.health = 0
                            enemy.alive = False
                    if hasattr(self.game_controller, 'set_story_message'):
                        self.game_controller.set_story_message(f"Emergency: {enemy_count} stuck enemies eliminated", 2000)

    def handle_key_up(self, event):
        """Processes key release events to reset action flags."""
        if event.key == K_a or event.key == K_LEFT:
            self.turn_left = False
        
        elif event.key == K_d or event.key == K_RIGHT:
            self.turn_right = False
        
        elif event.key == K_SPACE:
            self.is_shooting = False

    def update_player_movement_and_actions(self, current_time_ms):
        """
        Called every frame to update the player's state based on continuous
        (held-key) actions like turning and shooting.
        """
        if self.turn_left:
            self.turn("left")
        
        if self.turn_right:
            self.turn("right")

        if self.is_shooting:
            self.shoot(current_time_ms)

    def turn(self, direction):
        """Instructs the player drone to rotate."""
        if self.game_controller.player and self.game_controller.player.alive:
            self.game_controller.player.rotate(direction)

    def shoot(self, current_time_ms):
        """Instructs the player drone to fire its weapon."""
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
