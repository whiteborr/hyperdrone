# hyperdrone_core/enemy_manager.py
from pygame.sprite import Group
from json import load, JSONDecodeError
from os.path import join
from logging import getLogger
from entities import Enemy, SentinelDrone
from entities.defense_drone import DefenseDrone
from entities.tr3b_enemy import TR3BEnemy
from settings_manager import get_setting

logger = getLogger(__name__)

class EnemyManager:
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        self.enemies = Group()
        self.tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        
        # Load enemy configurations
        self.enemy_configs = self._load_configs()
        
        # Enemy class mapping
        self.enemy_classes = {
            "Enemy": Enemy,
            "SentinelDrone": SentinelDrone,
            "TR3BEnemy": TR3BEnemy,
            "DefenseDrone": DefenseDrone
        }

    def _load_configs(self):
        try:
            with open(join("data", "enemy_configs.json"), 'r') as f:
                return load(f)["enemies"]
        except (FileNotFoundError, JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading enemy configs: {e}")
            return {}

    def spawn_enemy_by_id(self, enemy_id, x, y, **kwargs):
        # Handle fallback for regular_enemy
        if enemy_id == "regular_enemy" and enemy_id not in self.enemy_configs:
            logger.warning("Regular enemy config not found, using prototype_enemy")
            enemy_id = "prototype_enemy"
            
        config = self.enemy_configs.get(enemy_id)
        if not config:
            logger.error(f"Enemy config for '{enemy_id}' not found")
            return None
            
        # Get enemy class
        class_name = config.get("class_name", "Enemy")
        enemy_class = self.enemy_classes.get(class_name)
        
        if not enemy_class:
            logger.error(f"Unknown enemy class '{class_name}'")
            return None
            
        # Create enemy
        player = getattr(self.game_controller, 'player', None)
        enemy = enemy_class(x, y, self.asset_manager, config, player)
        
        # Set path for defense mode
        if 'path_to_core' in kwargs and hasattr(enemy, 'path'):
            enemy.path = kwargs['path_to_core']
            enemy.current_path_index = 1 if enemy.path and len(enemy.path) > 1 else -1
            
        self.enemies.add(enemy)
        return enemy
        
    def spawn_enemies_for_level(self, level):
        self.enemies.empty()
        num_enemies = min(level + 1, 7)
        
        # Get screen bounds
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "GAME_PLAY_AREA_HEIGHT", 960)
        
        spawned_count = 0
        
        if level >= 6:
            # High level: TR-3B + Sentinels
            tr3b_count = min(level - 5, 3)
            sentinel_count = num_enemies - tr3b_count
            
            spawned_count += self._spawn_enemy_type("tr3b", tr3b_count, width, height, 0.7)
            spawned_count += self._spawn_enemy_type("sentinel", sentinel_count, width, height, 0.6)
            
        elif level >= 4:
            # Mid level: Sentinels only
            spawned_count += self._spawn_enemy_type("sentinel", num_enemies, width, height, 0.6)
            
        else:
            # Early level: Regular enemies
            spawned_count += self._spawn_enemy_type("regular_enemy", num_enemies, width, height, 0.7)
        
        logger.info(f"Level {level}: Spawned {spawned_count}/{num_enemies} enemies")

    def _spawn_enemy_type(self, enemy_type, count, width, height, size_factor):
        spawned = 0
        max_attempts = 20
        
        for _ in range(count):
            for attempt in range(max_attempts):
                pos = self.game_controller._get_safe_spawn_point(
                    self.tile_size * size_factor, 
                    self.tile_size * size_factor
                )
                
                if pos and 0 < pos[0] < width and 0 < pos[1] < height:
                    if self.spawn_enemy_by_id(enemy_type, pos[0], pos[1]):
                        spawned += 1
                        break
                        
        return spawned

    def spawn_enemy_for_defense(self, enemy_type_key, spawn_position_grid, path_to_core):
        abs_x, abs_y = self.game_controller.maze._grid_to_pixel_center(*spawn_position_grid)
        
        # Try to spawn requested enemy type
        enemy = self.spawn_enemy_by_id(enemy_type_key, abs_x, abs_y, path_to_core=path_to_core)
        
        if enemy:
            logger.info(f"Spawned {enemy_type_key} at {abs_x}, {abs_y}")
        else:
            # Fallback to defense_drone_1
            enemy = self.spawn_enemy_by_id("defense_drone_1", abs_x, abs_y, path_to_core=path_to_core)
            if enemy:
                logger.info(f"Fallback: Spawned defense_drone_1 at {abs_x}, {abs_y}")
        
    def update_enemies(self, target_pos, maze, current_time_ms, delta_time_ms, x_offset=0, is_defense_mode=False):
        for enemy in list(self.enemies):
            if enemy.alive:
                enemy.update(target_pos, maze, current_time_ms, delta_time_ms, x_offset, is_defense_mode)
            elif not hasattr(enemy, '_exploded'):
                self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery)
                enemy._exploded = True
                enemy.kill()
            elif hasattr(enemy, '_exploded') and not enemy.bullets:
                enemy.kill()

    def draw_all(self, surface, camera=None):
        for enemy in self.enemies:
            enemy.draw(surface, None)
            if enemy.alive and hasattr(enemy, '_draw_health_bar'):
                enemy._draw_health_bar(surface, None)

    def reset_all(self):
        self.enemies.empty()
        
    def get_sprites(self):
        return self.enemies
        
    def get_active_enemies_count(self):
        return sum(1 for e in self.enemies if e.alive)