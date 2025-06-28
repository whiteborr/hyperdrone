# entities/tower_defense_manager.py
from pygame.sprite import Group
from logging import getLogger
from random import choice
from copy import deepcopy
from entities.path_manager import PathManager
from entities.enemy_pathfinder import PathfindingEnemy
from entities.turret import Turret
from settings_manager import get_setting

logger = getLogger(__name__)

class TowerDefenseManager:
    def __init__(self, grid_width, grid_height, tile_size, game_area_x_offset=0):
        self.width = grid_width
        self.height = grid_height
        self.tile_size = tile_size
        self.x_offset = game_area_x_offset
        
        self.path_manager = PathManager(grid_width, grid_height, tile_size)
        self.enemies = Group()
        self.towers = Group()
        
        # Wave state
        self.wave = 0
        self.enemies_left = 0
        self.spawn_timer = 0
        self.wave_active = False
        self.wave_enemy_types = []
        
        self.game_controller = None
        
    def initialize_from_maze(self, maze):
        if hasattr(maze, 'grid'):
            self.path_manager.set_grid(deepcopy(maze.grid))
        
        # Set goal from maze core position
        goal = getattr(maze, 'core_pos', None) or getattr(maze, 'core_reactor_grid_pos', None)
        if goal:
            self.path_manager.set_goal_point(goal)
        
        # Set spawn points
        spawns = [(1, 1), (1, 18), (13, 1), (13, 18)]
        self.path_manager.set_spawn_points(spawns)
        
        logger.info(f"Initialized {self.width}x{self.height} grid with {len(spawns)} spawns")
            
    def try_place_tower(self, screen_pos, asset_manager):
        r, c = self._screen_to_grid(screen_pos)
        
        if (not self._can_place_at(r, c) or 
            not self._has_resources() or 
            not self._place_tower(r, c, asset_manager)):
            return False
        
        self._spend_resources()
        self._recalculate_paths()
        return True
    
    def _screen_to_grid(self, pos):
        x, y = pos
        c = int((x - self.x_offset) // self.tile_size)
        r = int(y // self.tile_size)
        return r, c
    
    def _can_place_at(self, r, c):
        return self.path_manager.grid[r][c] == 'T'
    
    def _has_resources(self):
        return self._get_cores() >= Turret.TURRET_COST
    
    def _get_cores(self):
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            return self.game_controller.drone_system.get_cores()
        return 0
    
    def _place_tower(self, r, c, asset_manager):
        x = c * self.tile_size + self.tile_size // 2 + self.x_offset
        y = r * self.tile_size + self.tile_size // 2
        
        tower = Turret(x, y, None, asset_manager)
        self.towers.add(tower)
        
        if self.game_controller and hasattr(self.game_controller, 'turrets_group'):
            self.game_controller.turrets_group.add(tower)
        
        self.path_manager.grid[r][c] = 'U'
        return True
    
    def _spend_resources(self):
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            self.game_controller.drone_system.spend_cores(Turret.TURRET_COST)
        
    def _recalculate_paths(self):
        for enemy in self.enemies:
            if hasattr(enemy, 'trigger_path_recalculation'):
                enemy.trigger_path_recalculation()
                
    def spawn_enemy(self, enemy_type='basic', asset_manager=None):
        if not self.path_manager.spawns:
            return None
        
        spawn = self._get_spawn_point()
        enemy = self._create_enemy(enemy_type, spawn, asset_manager)
        
        if enemy:
            self.enemies.add(enemy)
            if hasattr(enemy, 'calculate_path'):
                enemy.calculate_path()
        
        return enemy
    
    def _get_spawn_point(self):
        spawn = choice(self.path_manager.spawns)
        r, c = spawn
        if 0 <= r < self.height and 0 <= c < self.width:
            return spawn
        return (1, 1)
    
    def _create_enemy(self, enemy_type, spawn, asset_manager):
        if enemy_type.startswith("defense_drone_") and asset_manager:
            return self._create_drone(enemy_type, spawn, asset_manager)
        return self._create_basic(enemy_type, spawn)
    
    def _create_drone(self, enemy_type, spawn, asset_manager):
        from entities.defense_drone_pathfinder import DefenseDronePathfinder
        
        num = enemy_type.split("_")[-1]
        configs = {
            "1": {"health": 100, "speed": 1.0},
            "2": {"health": 200, "speed": 0.7},
            "3": {"health": 80, "speed": 1.5},
            "4": {"health": 300, "speed": 0.5},
            "5": {"health": 150, "speed": 1.2}
        }
        
        if num in configs:
            config = configs[num]
            health = get_setting("gameplay", f"DEFENSE_DRONE_{num}_HEALTH", config["health"])
            speed = get_setting("gameplay", f"DEFENSE_DRONE_{num}_SPEED", config["speed"])
            sprite_key = f"defense_drone_{num}_sprite_key"
            return DefenseDronePathfinder(spawn, self.path_manager, asset_manager, sprite_key, speed=speed, health=health)
        
        return None
    
    def _create_basic(self, enemy_type, spawn):
        configs = {
            'basic': {'speed': 1.0, 'health': 100},
            'fast': {'speed': 2.0, 'health': 50},
            'tank': {'speed': 0.5, 'health': 200}
        }
        
        if enemy_type in configs:
            config = configs[enemy_type]
            return PathfindingEnemy(spawn, self.path_manager, speed=config['speed'], health=config['health'])
        
        return None
        
    def start_wave(self, wave_number, enemies_count, spawn_interval_ms=1000, enemy_types=None):
        self.wave = wave_number
        self.enemies_left = enemies_count
        self.spawn_timer = 0
        self.wave_active = True
        self.wave_enemy_types = enemy_types or ["basic"] * enemies_count
        
        logger.info(f"Starting wave {wave_number} with {enemies_count} enemies")
        
    def update(self, delta_time_ms):
        self._update_enemies()
        self._update_towers()
        self._handle_spawning(delta_time_ms)
        self._check_wave_complete()
    
    def _update_enemies(self):
        for enemy in self.enemies:
            enemy.update()
            if not enemy.alive:
                enemy.kill()
    
    def _update_towers(self):
        self.towers.update(self.enemies, None, self.x_offset)
    
    def _handle_spawning(self, delta_time_ms):
        if not (self.wave_active and self.enemies_left > 0):
            return
        
        self.spawn_timer += delta_time_ms
        if self.spawn_timer >= 1000:
            enemy_type = self._get_next_enemy_type()
            asset_manager = self._get_asset_manager()
            
            self.spawn_enemy(enemy_type, asset_manager)
            self.enemies_left -= 1
            self.spawn_timer = 0
    
    def _get_next_enemy_type(self):
        idx = len(self.wave_enemy_types) - self.enemies_left
        if 0 <= idx < len(self.wave_enemy_types):
            return self.wave_enemy_types[idx]
        return "defense_drone_1"
    
    def _get_asset_manager(self):
        if hasattr(self.game_controller, 'asset_manager'):
            return self.game_controller.asset_manager
        return None
    
    def _check_wave_complete(self):
        if (self.wave_active and self.enemies_left <= 0 and len(self.enemies) == 0):
            self.wave_active = False
            logger.info(f"Wave {self.wave} complete")
            
    def draw(self, surface, camera=None):
        if camera:
            for enemy in self.enemies:
                if hasattr(enemy, 'draw_path'):
                    enemy.draw_path(surface, camera)
        
        self.enemies.draw(surface)
        
        for tower in self.towers:
            tower.draw(surface, camera)
