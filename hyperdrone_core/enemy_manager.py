import pygame
import random
from entities import Enemy, SentinelDrone, DefenseDrone
import game_settings as gs
from game_settings import TILE_SIZE 

class EnemyManager:
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        self.enemies = pygame.sprite.Group()

        self.defense_enemy_configs = {
            "defense_drone_1": { "class": DefenseDrone, "sprite_asset_key": "defense_drone_1_sprite_key", "health": gs.DEFENSE_DRONE_1_HEALTH, "speed": gs.DEFENSE_DRONE_1_SPEED, "contact_damage": 25 },
            "defense_drone_2": { "class": DefenseDrone, "sprite_asset_key": "defense_drone_2_sprite_key", "health": gs.DEFENSE_DRONE_2_HEALTH, "speed": gs.DEFENSE_DRONE_2_SPEED, "contact_damage": 30 },
            "defense_drone_3": { "class": DefenseDrone, "sprite_asset_key": "defense_drone_3_sprite_key", "health": gs.DEFENSE_DRONE_3_HEALTH, "speed": gs.DEFENSE_DRONE_3_SPEED, "contact_damage": 20 },
            "defense_drone_4": { "class": DefenseDrone, "sprite_asset_key": "defense_drone_4_sprite_key", "health": gs.DEFENSE_DRONE_4_HEALTH, "speed": gs.DEFENSE_DRONE_4_SPEED, "contact_damage": 40 },
            "defense_drone_5": { "class": DefenseDrone, "sprite_asset_key": "defense_drone_5_sprite_key", "health": gs.DEFENSE_DRONE_5_HEALTH, "speed": gs.DEFENSE_DRONE_5_SPEED, "contact_damage": 35 }
        }

    def spawn_enemies_for_level(self, level):
        self.enemies.empty()
        num_enemies = min(level + 1, 7)
        if level >= 4:
            for _ in range(num_enemies):
                if pos := self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.6, TILE_SIZE * 0.6):
                    self.enemies.add(SentinelDrone(pos[0], pos[1], gs.PLAYER_DEFAULT_BULLET_SIZE, self.asset_manager, "sentinel_drone_sprite_key", 'enemy_shoot', self.game_controller.player))
        else:
            for _ in range(num_enemies):
                if pos := self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7):
                    self.enemies.add(Enemy(pos[0], pos[1], gs.PLAYER_DEFAULT_BULLET_SIZE, self.asset_manager, "regular_enemy_sprite_key", 'enemy_shoot', self.game_controller.player))

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