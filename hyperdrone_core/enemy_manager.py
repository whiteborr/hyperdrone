import pygame
import random
from entities import Enemy, SentinelDrone # MazeGuardian is handled by GameController directly
import game_settings as gs
from game_settings import TILE_SIZE # For _get_safe_spawn_point call

class EnemyManager:
    def __init__(self, game_controller):
        """
        Initializes the EnemyManager.
        Args:
            game_controller: A reference to the main GameController instance.
        """
        self.game_controller = game_controller
        self.enemies = pygame.sprite.Group()

    def spawn_enemies_for_level(self, level):
        """
        Spawns standard enemies for a given level.
        Mirrors logic from GameController._spawn_enemies_for_level.
        """
        self.enemies.empty() # Clear previous standard enemies
        num_enemies = min(level + 1, 7)
        enemy_shoot_sound = self.game_controller.sounds.get('enemy_shoot')
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        regular_enemy_sprite = gs.get_game_setting("REGULAR_ENEMY_SPRITE_PATH")

        for _ in range(num_enemies):
            # Use GameController's method to find a safe spawn point
            abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7)
            if abs_x is not None:
                enemy = Enemy(abs_x, abs_y, player_bullet_size_setting,
                              shoot_sound=enemy_shoot_sound,
                              sprite_path=regular_enemy_sprite,
                              target_player_ref=self.game_controller.player)
                self.enemies.add(enemy)
            else:
                print("EnemyManager: Could not find safe spawn for standard enemy.")

    def spawn_prototype_drones(self, count, far_from_player=False):
        """
        Spawns prototype drones, typically for the Architect's Vault.
        Mirrors logic from GameController._spawn_prototype_drones.
        Note: This adds to existing enemies, so call reset_all() if these are the only ones desired.
        """
        if not self.game_controller.maze:
            return

        enemy_shoot_sound = self.game_controller.sounds.get('enemy_shoot')
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        prototype_sprite = gs.get_game_setting("PROTOTYPE_DRONE_SPRITE_PATH")

        for _ in range(count):
            abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7)
            if abs_x is not None:
                proto_drone = Enemy(abs_x, abs_y, player_bullet_size_setting,
                                    shoot_sound=enemy_shoot_sound,
                                    sprite_path=prototype_sprite,
                                    target_player_ref=self.game_controller.player)
                proto_drone.health = gs.get_game_setting("PROTOTYPE_DRONE_HEALTH")
                proto_drone.max_health = gs.get_game_setting("PROTOTYPE_DRONE_HEALTH")
                proto_drone.speed = gs.get_game_setting("PROTOTYPE_DRONE_SPEED")
                proto_drone.shoot_cooldown = gs.get_game_setting("PROTOTYPE_DRONE_SHOOT_COOLDOWN")
                self.enemies.add(proto_drone)
            else:
                print("EnemyManager: Could not find safe spawn for prototype drone.")
    
    def spawn_sentinel_drone_at_location(self, x, y):
        """
        Spawns a single SentinelDrone at a specific location.
        Used by MazeGuardian.
        """
        shoot_sound = self.game_controller.sounds.get('enemy_shoot')
        player_bullet_size_base = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        sprite_path = gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH")
        
        sentinel = SentinelDrone(
            x=x, y=y,
            player_bullet_size_base=player_bullet_size_base,
            shoot_sound=shoot_sound,
            sprite_path=sprite_path,
            target_player_ref=self.game_controller.player
        )
        self.enemies.add(sentinel)
        print(f"EnemyManager: Spawned Sentinel Drone at ({x}, {y})")


    def update_all(self, player_pos_pixels, maze, current_time, game_area_x_offset=0):
        """
        Updates all managed enemies.
        Handles explosion creation for defeated enemies.
        """
        for enemy_obj in list(self.enemies): # Iterate over a copy for safe removal
            if enemy_obj.alive:
                enemy_obj.update(player_pos_pixels, maze, current_time, game_area_x_offset)
            elif not hasattr(enemy_obj, '_exploded'): # Check if explosion already triggered
                # Call GameController's explosion method
                self.game_controller._create_explosion(enemy_obj.rect.centerx, enemy_obj.rect.centery)
                enemy_obj._exploded = True # Mark as exploded
                enemy_obj.kill() # Remove from all sprite groups
            elif not enemy_obj.bullets and hasattr(enemy_obj, '_exploded'): # If no more bullets and already exploded
                 enemy_obj.kill()


    def draw_all(self, surface):
        """Draws all managed enemies."""
        for enemy in self.enemies: # Individual draw to ensure custom draw logic (like health bars) is called
            enemy.draw(surface)
        # Alternatively, if Enemy.draw handles everything and is efficient:
        # self.enemies.draw(surface)

    def reset_all(self):
        """Removes all enemies from the manager."""
        self.enemies.empty()

    def get_sprites(self):
        """Returns the sprite group of managed enemies for collision detection or other logic."""
        return self.enemies

    def get_active_enemies_count(self):
        """Returns the number of currently active (alive) enemies."""
        return sum(1 for e in self.enemies if e.alive)