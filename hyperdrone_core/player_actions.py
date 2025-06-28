# hyperdrone_core/player_actions.py
from pygame.time import get_ticks
from pygame import K_w, K_UP, K_s, K_DOWN, K_a, K_LEFT, K_d, K_RIGHT, K_SPACE, K_LSHIFT, K_RSHIFT, K_f, K_F1, K_TAB

class PlayerActions:
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        self.turn_left = False
        self.turn_right = False
        self.is_shooting = False

    def handle_key_down(self, event):
        player = self.game_controller.player
        if not player or not player.alive:
            return

        key = event.key
        
        # Movement controls
        if key in (K_w, K_UP):
            player.is_cruising = True
            # Activate speed boost if available
            if (hasattr(player, 'powerup_manager') and 
                hasattr(player.powerup_manager, 'speed_boost_armed') and 
                player.powerup_manager.speed_boost_armed):
                player.activate_speed_boost()
        
        elif key in (K_s, K_DOWN):
            player.is_cruising = False

        elif key in (K_a, K_LEFT):
            self.turn_left = True
        
        elif key in (K_d, K_RIGHT):
            self.turn_right = True
        
        elif key == K_SPACE:
            self.is_shooting = True
        
        # Special abilities
        elif key in (K_LSHIFT, K_RSHIFT):
            if (hasattr(player, 'special_ability') and 
                player.special_ability == "phantom_cloak" and
                player.try_activate_cloak(get_ticks())):
                self.game_controller.play_sound('cloak_activate')
                        
        elif key == K_f:
            if hasattr(player, 'activate_ability'):
                player.activate_ability("temporary_barricade", self.game_controller)

        # Weapon cycling
        elif key == K_TAB:
            if hasattr(player, 'cycle_weapon_state'):
                player.cycle_weapon_state()
                self.game_controller.play_sound('ui_confirm')

        # Emergency enemy elimination
        elif key == K_F1:
            self._emergency_clear_enemies()

    def handle_key_up(self, event):
        key = event.key
        
        if key in (K_a, K_LEFT):
            self.turn_left = False
        elif key in (K_d, K_RIGHT):
            self.turn_right = False
        elif key == K_SPACE:
            self.is_shooting = False

    def update_player_movement_and_actions(self, current_time_ms):
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
        player = self.game_controller.player
        if not player or not player.alive:
            return
            
        # Get enemies group
        combat_ctrl = self.game_controller.combat_controller
        enemies_group = combat_ctrl.enemy_manager.get_sprites()

        if combat_ctrl.boss_active:
            enemies_group.add(combat_ctrl.maze_guardian)

        player.shoot(
            sound_asset_key='shoot',
            missile_sound_asset_key='missile_launch',
            maze=self.game_controller.maze,
            enemies_group=enemies_group
        )

    def _emergency_clear_enemies(self):
        """Emergency function to clear stuck enemies"""
        combat_ctrl = self.game_controller.combat_controller
        if not (hasattr(combat_ctrl, 'enemy_manager') and 
                hasattr(combat_ctrl.enemy_manager, 'get_active_enemies_count')):
            return
            
        enemy_count = combat_ctrl.enemy_manager.get_active_enemies_count()
        if enemy_count > 0:
            for enemy in list(combat_ctrl.enemy_manager.enemies):
                if enemy.alive:
                    enemy.health = 0
                    enemy.alive = False
            
            if hasattr(self.game_controller, 'set_story_message'):
                self.game_controller.set_story_message(f"Emergency: {enemy_count} stuck enemies eliminated", 2000)