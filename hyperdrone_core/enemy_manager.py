from pygame.sprite import Group
import json
import os
import logging
from entities import Enemy, SentinelDrone
from entities.defense_drone import DefenseDrone
from entities.tr3b_enemy import TR3BEnemy
from settings_manager import get_setting

logger = logging.getLogger(__name__)

class EnemyManager:
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        self.enemies = Group()
        self.tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        
        # Load enemy configurations from JSON file
        self.enemy_configs = {}
        config_path = os.path.join("data", "enemy_configs.json")
        try:
            with open(config_path, 'r') as f:
                self.enemy_configs = json.load(f)["enemies"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading enemy configs: {e}")
            # Fallback to default configs if file can't be loaded

    def spawn_enemy_by_id(self, enemy_id, x, y, **kwargs):
        """Spawn an enemy by its ID from the configuration"""
        # For level 1, use prototype_enemy as fallback if regular_enemy fails
        if enemy_id == "regular_enemy":
            config = self.enemy_configs.get(enemy_id)
            if not config:
                logger.warning(f"Regular enemy config not found, using prototype_enemy instead")
                enemy_id = "prototype_enemy"
                config = self.enemy_configs.get(enemy_id)
        else:
            config = self.enemy_configs.get(enemy_id)
            
        if not config:
            logger.error(f"Enemy config for '{enemy_id}' not found.")
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
            logger.error(f"Unknown enemy class '{class_name}'")
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
        
        # Get screen dimensions to ensure enemies are within visible area
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        game_play_area_height = get_setting("display", "GAME_PLAY_AREA_HEIGHT", 960)
        
        # Track spawned enemies to ensure we have the correct count
        spawned_count = 0
        max_attempts = 20  # Limit attempts to prevent infinite loops
        
        if level >= 6:
            # Spawn mix of TR-3B and Sentinel drones for higher levels
            tr3b_count = min(level - 5, 3)  # Up to 3 TR-3B enemies based on level
            sentinel_count = num_enemies - tr3b_count
            
            # Spawn TR-3B enemies
            for _ in range(tr3b_count):
                attempts = 0
                while attempts < max_attempts:
                    if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.7, self.tile_size * 0.7):
                        # Verify position is within screen bounds
                        if 0 < pos[0] < width and 0 < pos[1] < game_play_area_height:
                            enemy = self.spawn_enemy_by_id("tr3b", pos[0], pos[1])
                            if enemy:
                                spawned_count += 1
                                break
                    attempts += 1
            
            # Spawn Sentinel drones
            for _ in range(sentinel_count):
                attempts = 0
                while attempts < max_attempts:
                    if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.6, self.tile_size * 0.6):
                        # Verify position is within screen bounds
                        if 0 < pos[0] < width and 0 < pos[1] < game_play_area_height:
                            enemy = self.spawn_enemy_by_id("sentinel", pos[0], pos[1])
                            if enemy:
                                spawned_count += 1
                                break
                    attempts += 1
        elif level >= 4:
            # Spawn only Sentinel drones for mid levels
            for _ in range(num_enemies):
                attempts = 0
                while attempts < max_attempts:
                    if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.6, self.tile_size * 0.6):
                        # Verify position is within screen bounds
                        if 0 < pos[0] < width and 0 < pos[1] < game_play_area_height:
                            enemy = self.spawn_enemy_by_id("sentinel", pos[0], pos[1])
                            if enemy:
                                spawned_count += 1
                                break
                    attempts += 1
        else:
            # Spawn regular enemies for early levels
            for _ in range(num_enemies):
                attempts = 0
                while attempts < max_attempts:
                    if pos := self.game_controller._get_safe_spawn_point(self.tile_size * 0.7, self.tile_size * 0.7):
                        # Verify position is within screen bounds
                        if 0 < pos[0] < width and 0 < pos[1] < game_play_area_height:
                            enemy = self.spawn_enemy_by_id("regular_enemy", pos[0], pos[1])
                            if enemy:
                                spawned_count += 1
                                break
                    attempts += 1
        
        logger.info(f"Level {level}: Spawned {spawned_count} enemies out of {num_enemies} requested")

    def spawn_enemy_for_defense(self, enemy_type_key, spawn_position_grid, path_to_core):
        abs_x, abs_y = self.game_controller.maze._grid_to_pixel_center(*spawn_position_grid)
        
        # Use the new spawn_enemy_by_id method with the path_to_core parameter
        enemy = self.spawn_enemy_by_id(enemy_type_key, abs_x, abs_y, path_to_core=path_to_core)
        
        if enemy:
            logger.info(f"Spawned {enemy_type_key} at {abs_x}, {abs_y} with path length: {len(path_to_core)}")
        else:
            # Fallback to defense_drone_1 if the requested enemy type doesn't exist
            enemy = self.spawn_enemy_by_id("defense_drone_1", abs_x, abs_y, path_to_core=path_to_core)
            if enemy:
                logger.info(f"Fallback: Spawned defense_drone_1 at {abs_x}, {abs_y} with path length: {len(path_to_core)}")
        
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
            enemy.draw(surface, None)
            if enemy.alive and hasattr(enemy, '_draw_health_bar'): enemy._draw_health_bar(surface, None)

    def reset_all(self): self.enemies.empty()
    def get_sprites(self): return self.enemies
    def get_active_enemies_count(self): 
        return sum(1 for e in self.enemies if e.alive)
