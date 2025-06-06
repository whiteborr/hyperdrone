# hyperdrone_core/enemy_manager.py
import pygame
import random
from entities import Enemy, SentinelDrone # Ensure SentinelDrone is imported
import game_settings as gs
from game_settings import TILE_SIZE 

class EnemyManager:
    def __init__(self, game_controller_ref, asset_manager):
        """
        Initializes the EnemyManager.
        Args:
            game_controller_ref: A reference to the main GameController instance.
            asset_manager: The central AssetManager for loading game assets.
        """
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager # Store the AssetManager instance
        self.enemies = pygame.sprite.Group() # Group to hold all active enemy sprites

        # This dictionary now stores asset keys instead of direct paths.
        # These keys must match the keys preloaded in GameController's manifest.
        self.defense_enemy_configs = {
            "standard_drone": {
                "class": Enemy,
                "sprite_asset_key": "regular_enemy_sprite_key", # Key for AssetManager
                "health": gs.get_game_setting("ENEMY_HEALTH", 100),
                "speed": gs.get_game_setting("ENEMY_SPEED", 1.5),
                "shoot_cooldown": gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500),
                "contact_damage": 25
            },
            "fast_drone": { 
                "class": Enemy,
                "sprite_asset_key": "regular_enemy_sprite_key", # Can reuse or use a new one e.g., "fast_enemy_sprite_key"
                "health": int(gs.get_game_setting("ENEMY_HEALTH", 100) * 0.7),
                "speed": gs.get_game_setting("ENEMY_SPEED", 1.5) * 1.5,
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.8),
                "contact_damage": 20
            },
            "armored_drone": { 
                "class": Enemy,
                "sprite_asset_key": "regular_enemy_sprite_key", # Can reuse or use a new one e.g., "armored_enemy_sprite_key"
                "health": int(gs.get_game_setting("ENEMY_HEALTH", 100) * 1.8),
                "speed": gs.get_game_setting("ENEMY_SPEED", 1.5) * 0.7,
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 1.2),
                "contact_damage": 35
            },
            "sentinel_drone": {
                "class": SentinelDrone,
                "sprite_asset_key": "sentinel_drone_sprite_key", # Key for AssetManager
                "health": gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75),
                "speed": gs.get_game_setting("SENTINEL_DRONE_SPEED", 3.0),
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.7), 
                "contact_damage": 30
            }
        }


    def spawn_enemies_for_level(self, level):
        """
        Spawns enemies for a given level in the standard game mode.
        """
        self.enemies.empty()
        num_enemies = min(level + 1, 7) 
        enemy_shoot_sound_key = 'enemy_shoot' # Sound key for AssetManager
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        
        # Spawning different enemy types based on level
        if 4 <= level <= 6: 
            print(f"EnemyManager: Spawning SentinelDrones for level {level}")
            sentinel_sprite_key = "sentinel_drone_sprite_key"
            for _ in range(num_enemies):
                abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.6, TILE_SIZE * 0.6) 
                if abs_x is not None:
                    enemy = SentinelDrone(x=abs_x, y=abs_y,
                                          player_bullet_size_base=player_bullet_size_setting, 
                                          shoot_sound_key=enemy_shoot_sound_key,
                                          asset_manager=self.asset_manager,
                                          sprite_asset_key=sentinel_sprite_key, 
                                          target_player_ref=self.game_controller.player)
                    self.enemies.add(enemy)
                else:
                    print(f"EnemyManager: Could not find safe spawn for SentinelDrone on level {level}.")
        else: 
            print(f"EnemyManager: Spawning standard TR-3B enemies for level {level}")
            regular_enemy_sprite_key = "regular_enemy_sprite_key"
            for _ in range(num_enemies):
                abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7) 
                if abs_x is not None:
                    enemy = Enemy(abs_x, abs_y, player_bullet_size_setting,
                                  shoot_sound_key=enemy_shoot_sound_key,
                                  asset_manager=self.asset_manager,
                                  sprite_asset_key=regular_enemy_sprite_key,
                                  target_player_ref=self.game_controller.player)
                    self.enemies.add(enemy)
                else:
                    print(f"EnemyManager: Could not find safe spawn for standard enemy on level {level}.")

    def spawn_prototype_drones(self, count, far_from_player=False):
        """
        Spawns prototype drones, typically for the Architect's Vault.
        """
        if not self.game_controller.maze: 
            print("EnemyManager: Cannot spawn prototype drones, maze not initialized.")
            return

        enemy_shoot_sound_key = 'enemy_shoot'
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        prototype_sprite_key = "prototype_drone_sprite_key"

        for _ in range(count):
            abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7) 
            if abs_x is not None:
                proto_drone = Enemy(abs_x, abs_y, player_bullet_size_setting,
                                    shoot_sound_key=enemy_shoot_sound_key,
                                    asset_manager=self.asset_manager,
                                    sprite_asset_key=prototype_sprite_key,
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
        """
        shoot_sound_key = 'enemy_shoot'
        player_bullet_size_base = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        sprite_key = "sentinel_drone_sprite_key"
        
        sentinel = SentinelDrone(
            x=x, y=y,
            player_bullet_size_base=player_bullet_size_base,
            shoot_sound_key=shoot_sound_key,
            asset_manager=self.asset_manager,
            sprite_asset_key=sprite_key,
            target_player_ref=self.game_controller.player 
        )
        self.enemies.add(sentinel)
        print(f"EnemyManager: Spawned Sentinel Drone at ({x}, {y})")

    def spawn_enemy_for_defense(self, enemy_type_key, spawn_position, reactor_target):
        """
        Spawns a specific type of enemy for the Maze Defense mode.
        """
        config = self.defense_enemy_configs.get(enemy_type_key)
        if not config:
            print(f"EnemyManager: Unknown enemy_type_key '{enemy_type_key}' for defense mode. Spawning standard drone.")
            config = self.defense_enemy_configs.get("standard_drone")
            if not config: 
                print("EnemyManager: CRITICAL - 'standard_drone' config missing in defense_enemy_configs.")
                return

        EnemyClass = config["class"]
        abs_x, abs_y = spawn_position
        enemy_shoot_sound_key = 'enemy_shoot'
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")

        enemy = EnemyClass(x=abs_x, y=abs_y,
                           player_bullet_size_base=player_bullet_size_setting,
                           shoot_sound_key=enemy_shoot_sound_key,
                           asset_manager=self.asset_manager,
                           sprite_asset_key=config["sprite_asset_key"],
                           target_player_ref=self.game_controller.player)

        enemy.health = config.get("health", enemy.health)
        enemy.max_health = config.get("health", enemy.max_health) 
        enemy.speed = config.get("speed", enemy.speed)
        enemy.shoot_cooldown = config.get("shoot_cooldown", enemy.shoot_cooldown)
        
        enemy.defense_target = reactor_target
        enemy.is_in_defense_mode = True 
        enemy.contact_damage = config.get("contact_damage", 25)

        self.enemies.add(enemy)

    def update_enemies(self, primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset=0, is_defense_mode=False):
        """
        Unified update method for all enemies.
        """
        for enemy_obj in list(self.enemies):
            if enemy_obj.alive:
                enemy_obj.update(primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset, is_defense_mode)
            elif not hasattr(enemy_obj, '_exploded'):
                explosion_sound_key = 'enemy_shoot' # Default explosion sound key
                if isinstance(enemy_obj, SentinelDrone):
                    explosion_sound_key = 'prototype_drone_explode' 
                
                self.game_controller._create_explosion(enemy_obj.rect.centerx, enemy_obj.rect.centery, specific_sound_key=explosion_sound_key)
                enemy_obj._exploded = True
                enemy_obj.kill()
            elif not enemy_obj.bullets and hasattr(enemy_obj, '_exploded'):
                 enemy_obj.kill()

    def draw_all(self, surface):
        """Draws all managed enemies and their health bars."""
        for enemy in self.enemies: 
            enemy.draw(surface)
            if enemy.alive and hasattr(enemy, '_draw_health_bar'):
                enemy._draw_health_bar(surface)

    def reset_all(self):
        """Removes all enemies from the manager."""
        self.enemies.empty() 
        print("EnemyManager: All enemies reset.")

    def get_sprites(self):
        """Returns the sprite group of managed enemies."""
        return self.enemies

    def get_active_enemies_count(self):
        """Returns the number of currently active (alive) enemies."""
        return sum(1 for e in self.enemies if e.alive)
