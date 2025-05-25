import pygame
import random
from entities import Enemy, SentinelDrone # Ensure SentinelDrone is imported
import game_settings as gs
from game_settings import TILE_SIZE 

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
        Spawns enemies for a given level.
        For levels 4-6, spawns SentinelDrones. Otherwise, spawns standard Enemies.
        """
        self.enemies.empty() 
        
        num_enemies = min(level + 1, 7) # Default number of enemies
        enemy_shoot_sound = self.game_controller.sounds.get('enemy_shoot')
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        
        # Determine which enemy type to spawn based on the level
        if 4 <= level <= 6:
            print(f"EnemyManager: Spawning SentinelDrones for level {level}")
            enemy_sprite_path = gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH")
            for _ in range(num_enemies):
                abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.6, TILE_SIZE * 0.6) # Sentinel size
                if abs_x is not None:
                    # SentinelDrone constructor might take slightly different or fewer params
                    # It uses its own settings for health, speed from game_settings.py
                    enemy = SentinelDrone(x=abs_x, y=abs_y,
                                          player_bullet_size_base=player_bullet_size_setting, # For its bullet size calculation
                                          shoot_sound=enemy_shoot_sound,
                                          sprite_path=enemy_sprite_path, # Explicitly pass sprite path
                                          target_player_ref=self.game_controller.player)
                    self.enemies.add(enemy)
                else:
                    print(f"EnemyManager: Could not find safe spawn for SentinelDrone on level {level}.")
        else:
            print(f"EnemyManager: Spawning standard TR-3B enemies for level {level}")
            regular_enemy_sprite = gs.get_game_setting("REGULAR_ENEMY_SPRITE_PATH")
            for _ in range(num_enemies):
                abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7) # Standard enemy size
                if abs_x is not None:
                    enemy = Enemy(abs_x, abs_y, player_bullet_size_setting,
                                  shoot_sound=enemy_shoot_sound,
                                  sprite_path=regular_enemy_sprite,
                                  target_player_ref=self.game_controller.player)
                    self.enemies.add(enemy)
                else:
                    print(f"EnemyManager: Could not find safe spawn for standard enemy on level {level}.")

    def spawn_prototype_drones(self, count, far_from_player=False):
        """
        Spawns prototype drones, typically for the Architect's Vault.
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
        for enemy_obj in list(self.enemies): 
            if enemy_obj.alive:
                enemy_obj.update(player_pos_pixels, maze, current_time, game_area_x_offset)
            elif not hasattr(enemy_obj, '_exploded'): 
                self.game_controller._create_explosion(enemy_obj.rect.centerx, enemy_obj.rect.centery)
                enemy_obj._exploded = True 
                enemy_obj.kill() 
            elif not enemy_obj.bullets and hasattr(enemy_obj, '_exploded'): 
                 enemy_obj.kill()


    def draw_all(self, surface):
        """Draws all managed enemies."""
        for enemy in self.enemies: 
            enemy.draw(surface)

    def reset_all(self):
        """Removes all enemies from the manager."""
        self.enemies.empty()

    def get_sprites(self):
        """Returns the sprite group of managed enemies for collision detection or other logic."""
        return self.enemies

    def get_active_enemies_count(self):
        """Returns the number of currently active (alive) enemies."""
        return sum(1 for e in self.enemies if e.alive)

