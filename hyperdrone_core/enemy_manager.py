import pygame
import random
import json
import os
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
        
        # Load enemy configurations from JSON file
        self.enemy_configs = {}
        config_path = os.path.join("data", "enemy_configs.json")
        try:
            with open(config_path, 'r') as f:
                self.enemy_configs = json.load(f)["enemies"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading enemy configs: {e}")
            # Fallback to default configs if file can't be loaded

    def spawn_enemy_by_id(self, enemy_id, x, y, **kwargs):
        """Spawn an enemy by its ID from the configuration"""
        config = self.enemy_configs.get(enemy_id)
        if not config:
            print(f"ERROR: Enemy config for '{enemy_id}' not found.")
            return None
            
        # Dynamically get the class based on class_name
        class_name = config.get("class_name", "Enemy")
        enemy_class = None
        
        if class_name == "Enemy":
            enemy_class = Enemy
        elif class_name == "SentinelDrone":
            enemy_class = SentinelDrone
        elif class_name == "TR3BEnemy":
            enemy_class = TR3BEnemy
        elif class_name == "DefenseDrone":
            enemy_class = DefenseDrone
        else:
            print(f"ERROR: Unknown enemy class '{class_name}'")
            return None
            
        # Create the enemy instance
        enemy = enemy_class(x, y, self.asset_manager, config, self.game_controller.player if hasattr(self.game_controller, 'player') else None)
        
        # Handle unique arguments like path_to_core for defense mode
        if 'path_to_core' in kwargs and hasattr(enemy, 'path'):
            enemy.path = kwargs['path_to_core']
            enemy.current_path_index = 1 if enemy.path and len(enemy.path) > 1 else -1
            
        self.enemies.add(enemy)
        return enemy
        
    def spawn_enemies_for_level(self, level):
        self.enemies.empty()
        num_enemies = min(level + 1, 7)
        
        if level >= 6:
            # Spawn mix of TR-3B and Sentinel drones for higher levels
            tr3b_count = min(level - 5, 3)  # Up to 3 TR-3B enemies based on level
            sentinel_count = num_enemies - tr3b_count
            
            # Spawn TR-3B enemies
            for _ in range(tr3b_count):
                if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.7, self.tile_size * 0.7):
                    self.spawn_enemy_by_id("tr3b", pos[0], pos[1])
            
            # Spawn Sentinel drones
            for _ in range(sentinel_count):
                if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.6, self.tile_size * 0.6):
                    self.spawn_enemy_by_id("sentinel", pos[0], pos[1])
        elif level >= 4:
            # Spawn only Sentinel drones for mid levels
            for _ in range(num_enemies):
                if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.6, self.tile_size * 0.6):
                    self.spawn_enemy_by_id("sentinel", pos[0], pos[1])
        else:
            # Spawn regular enemies for early levels
            for _ in range(num_enemies):
                if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.7, self.tile_size * 0.7):
                    self.spawn_enemy_by_id("regular_enemy", pos[0], pos[1])

    def spawn_enemy_for_defense(self, enemy_type_key, spawn_position_grid, path_to_core):
        abs_x, abs_y = self.game_controller.maze._grid_to_pixel_center(*spawn_position_grid)
        
        # Use the new spawn_enemy_by_id method with the path_to_core parameter
        enemy = self.spawn_enemy_by_id(enemy_type_key, abs_x, abs_y, path_to_core=path_to_core)
        
        if enemy:
            print(f"Spawned {enemy_type_key} at {abs_x}, {abs_y} with path length: {len(path_to_core)}")
        else:
            # Fallback to defense_drone_1 if the requested enemy type doesn't exist
            enemy = self.spawn_enemy_by_id("defense_drone_1", abs_x, abs_y, path_to_core=path_to_core)
            if enemy:
                print(f"Fallback: Spawned defense_drone_1 at {abs_x}, {abs_y} with path length: {len(path_to_core)}")
        
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