import pygame
import random
from entities import Enemy, SentinelDrone
from entities.defense_drone import DefenseDrone
from entities.tr3b_enemy import TR3BEnemy
from settings_manager import get_setting, set_setting, get_asset_path

class EnemyManager:
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        self.enemies = pygame.sprite.Group()
        self.tile_size = get_setting("gameplay", "TILE_SIZE", 80)

        self.defense_enemy_configs = {
            "defense_drone_1": { 
                "class": DefenseDrone, 
                "sprite_asset_key": "defense_drone_1_sprite_key", 
                "health": get_setting("defense_mode", "DEFENSE_DRONE_1_HEALTH", 75), 
                "speed": get_setting("defense_mode", "DEFENSE_DRONE_1_SPEED", 1.8), 
                "contact_damage": 25 
            },
            "defense_drone_2": { 
                "class": DefenseDrone, 
                "sprite_asset_key": "defense_drone_2_sprite_key", 
                "health": get_setting("defense_mode", "DEFENSE_DRONE_2_HEALTH", 150), 
                "speed": get_setting("defense_mode", "DEFENSE_DRONE_2_SPEED", 1.2), 
                "contact_damage": 30 
            },
            "defense_drone_3": { 
                "class": DefenseDrone, 
                "sprite_asset_key": "defense_drone_3_sprite_key", 
                "health": get_setting("defense_mode", "DEFENSE_DRONE_3_HEALTH", 50), 
                "speed": get_setting("defense_mode", "DEFENSE_DRONE_3_SPEED", 2.5), 
                "contact_damage": 20 
            },
            "defense_drone_4": { 
                "class": DefenseDrone, 
                "sprite_asset_key": "defense_drone_4_sprite_key", 
                "health": get_setting("defense_mode", "DEFENSE_DRONE_4_HEALTH", 250), 
                "speed": get_setting("defense_mode", "DEFENSE_DRONE_4_SPEED", 1.0), 
                "contact_damage": 40 
            },
            "defense_drone_5": { 
                "class": DefenseDrone, 
                "sprite_asset_key": "defense_drone_5_sprite_key", 
                "health": get_setting("defense_mode", "DEFENSE_DRONE_5_HEALTH", 100), 
                "speed": get_setting("defense_mode", "DEFENSE_DRONE_5_SPEED", 2.0), 
                "contact_damage": 35 
            }
        }

    def spawn_enemies_for_level(self, level):
        self.enemies.empty()
        num_enemies = min(level + 1, 7)
        
        if level >= 6:
            # Spawn mix of TR-3B and Sentinel drones for higher levels
            tr3b_count = min(level - 5, 3)  # Up to 3 TR-3B enemies based on level
            sentinel_count = num_enemies - tr3b_count
            
            # Spawn TR-3B enemies
            bullet_size = get_setting("weapons", "PLAYER_DEFAULT_BULLET_SIZE", 4)
            for _ in range(tr3b_count):
                if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.7, self.tile_size * 0.7):
                    self.enemies.add(TR3BEnemy(pos[0], pos[1], bullet_size, 
                                             self.asset_manager, "TR-3B_enemy_sprite_key", 
                                             'enemy_shoot', self.game_controller.player))
            
            # Spawn Sentinel drones
            for _ in range(sentinel_count):
                if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.6, self.tile_size * 0.6):
                    self.enemies.add(SentinelDrone(pos[0], pos[1], bullet_size, 
                                                 self.asset_manager, "sentinel_drone_sprite_key", 
                                                 'enemy_shoot', self.game_controller.player))
        elif level >= 4:
            # Spawn only Sentinel drones for mid levels
            bullet_size = get_setting("weapons", "PLAYER_DEFAULT_BULLET_SIZE", 4)
            for _ in range(num_enemies):
                if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.6, self.tile_size * 0.6):
                    self.enemies.add(SentinelDrone(pos[0], pos[1], bullet_size, 
                                                 self.asset_manager, "sentinel_drone_sprite_key", 
                                                 'enemy_shoot', self.game_controller.player))
        else:
            # Spawn regular enemies for early levels
            bullet_size = get_setting("weapons", "PLAYER_DEFAULT_BULLET_SIZE", 4)
            for _ in range(num_enemies):
                if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.7, self.tile_size * 0.7):
                    self.enemies.add(Enemy(pos[0], pos[1], bullet_size, 
                                         self.asset_manager, "regular_enemy_sprite_key", 
                                         'enemy_shoot', self.game_controller.player))

    def spawn_enemy_for_defense(self, enemy_type_key, spawn_position_grid, path_to_core):
        config = self.defense_enemy_configs.get(enemy_type_key)
        if not config:
             config = self.defense_enemy_configs["defense_drone_1"]
        
        EnemyClass = config["class"]
        abs_x, abs_y = self.game_controller.maze._grid_to_pixel_center(*spawn_position_grid)
        
        enemy = EnemyClass(x=abs_x, y=abs_y, asset_manager=self.asset_manager, sprite_asset_key=config["sprite_asset_key"], path_to_core=path_to_core)
        enemy.health = config.get("health", 100); enemy.max_health = enemy.health
        enemy.speed = config.get("speed", 1.5); enemy.contact_damage = config.get("contact_damage", 25)
        self.enemies.add(enemy)
        print(f"Spawned {enemy_type_key} at {abs_x}, {abs_y} with path length: {len(path_to_core)}")
        
    def update_enemies(self, primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=False):
        for enemy_obj in list(self.enemies):
            if enemy_obj.alive:
                enemy_obj.update(primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset, is_defense_mode)
            elif not hasattr(enemy_obj, '_exploded'):
                self.game_controller._create_explosion(enemy_obj.rect.centerx, enemy_obj.rect.centery)
                enemy_obj._exploded = True; enemy_obj.kill()
            elif hasattr(enemy_obj, '_exploded') and not enemy_obj.bullets:
                 enemy_obj.kill()

    def draw_all(self, surface, camera=None):
        for enemy in self.enemies:
            enemy.draw(surface, camera)
            if enemy.alive and hasattr(enemy, '_draw_health_bar'): enemy._draw_health_bar(surface, camera)

    def reset_all(self): self.enemies.empty()
    def get_sprites(self): return self.enemies
    def get_active_enemies_count(self): return sum(1 for e in self.enemies if e.alive)