# entities/tower_defense_manager.py
from pygame.sprite import Group
from pygame import Surface
from logging import getLogger
from random import choice, randint
from typing import List, Tuple, Dict, Optional
from copy import deepcopy
from entities.path_manager import PathManager
from entities.enemy_pathfinder import PathfindingEnemy
from entities.turret import Turret
from settings_manager import get_setting

logger = getLogger(__name__)

class TowerDefenseManager:
    """
    Manages the tower defense game mechanics including:
    - Grid state
    - Tower placement validation
    - Enemy spawning and path recalculation
    - Wave management
    """
    def __init__(self, grid_width: int, grid_height: int, tile_size: int, game_area_x_offset: int = 0):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.tile_size = tile_size
        self.game_area_x_offset = game_area_x_offset
        
        # Create path manager
        self.path_manager = PathManager(grid_width, grid_height, tile_size)
        self.path_manager.tower_defense_manager = self
        
        # Sprite groups
        self.enemies_group = Group()
        self.towers_group = Group()
        
        # Wave management
        self.current_wave = 0
        self.enemies_remaining_in_wave = 0
        self.spawn_timer = 0
        self.wave_active = False
        self.current_wave_enemy_types = []
        
        # Store reference to game controller (will be set later)
        self.game_controller = None
        
        # Resources
        self.player_resources = 100
        
    def initialize_from_maze(self, maze):
        """Initialize grid from an existing maze object"""
        self._copy_maze_grid(maze)
        self._set_goal_point(maze)
        self._set_spawn_points()
        self._log_initialization_status()
    
    def _copy_maze_grid(self, maze):
        """Copy the maze grid to avoid modifying the original"""
        if hasattr(maze, 'grid'):
            grid_copy = deepcopy(maze.grid)
            self.path_manager.set_grid(grid_copy)
    
    def _set_goal_point(self, maze):
        """Set the goal point from maze core reactor position"""
        if hasattr(maze, 'CORE_GRID_POSITION') and maze.CORE_GRID_POSITION:
            self.path_manager.set_goal_point(maze.CORE_GRID_POSITION)
        elif hasattr(maze, 'core_reactor_grid_pos') and maze.core_reactor_grid_pos:
            self.path_manager.set_goal_point(maze.core_reactor_grid_pos)
    
    def _set_spawn_points(self):
        """Set hardcoded valid spawn points within grid bounds"""
        valid_spawn_points = [(1, 1), (1, 18), (13, 1), (13, 18)]
        self.path_manager.set_spawn_points(valid_spawn_points)
        logger.info(f"Using hardcoded valid spawn points: {valid_spawn_points}")
    
    def _log_initialization_status(self):
        """Log the initialization status"""
        logger.info(f"TowerDefenseManager initialized with grid size: {self.grid_width}x{self.grid_height}")
        logger.info(f"Goal point set to: {self.path_manager.goal_point}")
        logger.info(f"Spawn points: {len(self.path_manager.spawn_points)}")
            
    def try_place_tower(self, screen_pos: Tuple[int, int], asset_manager) -> bool:
        """
        Try to place a tower at the given screen position
        Returns True if tower was placed, False otherwise
        """
        grid_pos = self._screen_to_grid_position(screen_pos)
        
        if not self._can_place_tower_at(grid_pos):
            return False
        
        if not self._has_enough_resources():
            return False
        
        self._create_and_place_tower(grid_pos, asset_manager)
        self._deduct_tower_cost()
        self.recalculate_all_enemy_paths()
        
        return True
    
    def _screen_to_grid_position(self, screen_pos: Tuple[int, int]) -> Tuple[int, int]:
        """Convert screen position to grid position"""
        x, y = screen_pos
        x -= self.game_area_x_offset
        grid_col = int(x // self.tile_size)
        grid_row = int(y // self.tile_size)
        return grid_row, grid_col
    
    def _can_place_tower_at(self, grid_pos: Tuple[int, int]) -> bool:
        """Check if a tower can be placed at the given grid position"""
        grid_row, grid_col = grid_pos
        
        if self.path_manager.grid[grid_row][grid_col] != 'T':
            logger.info(f"Cannot place tower at ({grid_row}, {grid_col}) - not a designated turret spot")
            return False
        
        return True
    
    def _has_enough_resources(self) -> bool:
        """Check if player has enough resources to place a tower"""
        tower_cost = Turret.TURRET_COST
        cores = self._get_player_cores()
        
        if cores < tower_cost:
            logger.info(f"Not enough resources to place tower (need {tower_cost})")
            return False
        
        return True
    
    def _get_player_cores(self) -> int:
        """Get the number of cores the player has"""
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            return self.game_controller.drone_system.get_cores()
        return 0
    
    def _create_and_place_tower(self, grid_pos: Tuple[int, int], asset_manager):
        """Create and place a new tower at the specified position"""
        grid_row, grid_col = grid_pos
        
        # Calculate tile center position
        tile_center_x = grid_col * self.tile_size + self.tile_size // 2 + self.game_area_x_offset
        tile_center_y = grid_row * self.tile_size + self.tile_size // 2
        
        # Create and add tower
        new_tower = Turret(tile_center_x, tile_center_y, None, asset_manager)
        self.towers_group.add(new_tower)
        
        # Add to game controller's turrets group
        if self.game_controller and hasattr(self.game_controller, 'turrets_group'):
            self.game_controller.turrets_group.add(new_tower)
        
        # Mark grid position as occupied
        self.path_manager.grid[grid_row][grid_col] = 'U'
    
    def _deduct_tower_cost(self):
        """Deduct tower cost from player's resources"""
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            self.game_controller.drone_system.spend_cores(Turret.TURRET_COST)
        
    def recalculate_all_enemy_paths(self):
        """Trigger path recalculation for all active enemies"""
        for enemy in self.enemies_group:
            if hasattr(enemy, 'trigger_path_recalculation'):
                enemy.trigger_path_recalculation()
                
    def spawn_enemy(self, enemy_type: str = 'basic', asset_manager=None):
        """Spawn a new enemy at one of the spawn points"""
        if not self.path_manager.spawn_points:
            logger.error("No spawn points defined")
            return None
        
        spawn_point = self._get_valid_spawn_point()
        enemy = self._create_enemy(enemy_type, spawn_point, asset_manager)
        
        if enemy:
            self._add_enemy_to_game(enemy)
            return enemy
        
        return None
    
    def _get_valid_spawn_point(self) -> Tuple[int, int]:
        """Get a valid spawn point within grid bounds"""
        original_spawn_point = choice(self.path_manager.spawn_points)
        
        if self._is_spawn_point_valid(original_spawn_point):
            return original_spawn_point
        
        logger.warning(f"Spawn point {original_spawn_point} is out of bounds, using (1, 1)")
        return (1, 1)
    
    def _is_spawn_point_valid(self, spawn_point: Tuple[int, int]) -> bool:
        """Check if spawn point is within grid bounds"""
        row, col = spawn_point
        return (0 <= row < self.grid_height and 0 <= col < self.grid_width)
    
    def _create_enemy(self, enemy_type: str, spawn_point: Tuple[int, int], asset_manager):
        """Create an enemy based on type"""
        if enemy_type.startswith("defense_drone_") and asset_manager:
            return self._create_defense_drone(enemy_type, spawn_point, asset_manager)
        else:
            return self._create_basic_enemy(enemy_type, spawn_point)
    
    def _create_defense_drone(self, enemy_type: str, spawn_point: Tuple[int, int], asset_manager):
        """Create a defense drone enemy"""
        from entities.defense_drone_pathfinder import DefenseDronePathfinder
        
        drone_number = enemy_type.split("_")[-1]
        sprite_key = f"defense_drone_{drone_number}_sprite_key"
        
        drone_configs = {
            "1": {"health": 100, "speed": 1.0},
            "2": {"health": 200, "speed": 0.7},
            "3": {"health": 80, "speed": 1.5},
            "4": {"health": 300, "speed": 0.5},
            "5": {"health": 150, "speed": 1.2}
        }
        
        if drone_number in drone_configs:
            config = drone_configs[drone_number]
            health = get_setting("gameplay", f"DEFENSE_DRONE_{drone_number}_HEALTH", config["health"])
            speed = get_setting("gameplay", f"DEFENSE_DRONE_{drone_number}_SPEED", config["speed"])
            return DefenseDronePathfinder(spawn_point, self.path_manager, asset_manager, sprite_key, speed=speed, health=health)
        
        return None
    
    def _create_basic_enemy(self, enemy_type: str, spawn_point: Tuple[int, int]):
        """Create a basic enemy type"""
        enemy_configs = {
            'basic': {'speed': 1.0, 'health': 100},
            'fast': {'speed': 2.0, 'health': 50},
            'tank': {'speed': 0.5, 'health': 200}
        }
        
        if enemy_type in enemy_configs:
            config = enemy_configs[enemy_type]
            return PathfindingEnemy(spawn_point, self.path_manager, speed=config['speed'], health=config['health'])
        
        return None
    
    def _add_enemy_to_game(self, enemy):
        """Add enemy to the game and calculate its path"""
        self.enemies_group.add(enemy)
        if hasattr(enemy, 'calculate_path'):
            enemy.calculate_path()
        
    def start_wave(self, wave_number: int, enemies_count: int, spawn_interval_ms: int = 1000, enemy_types=None):
        """Start a new wave of enemies"""
        self.current_wave = wave_number
        self.enemies_remaining_in_wave = enemies_count
        self.spawn_timer = 0
        self.wave_active = True
        
        # Store enemy types for this wave
        self.current_wave_enemy_types = enemy_types if enemy_types else ["basic"] * enemies_count
        
        logger.info(f"Starting wave {wave_number} with {enemies_count} enemies")
        
    def update(self, delta_time_ms: int):
        """Update game state"""
        self._update_enemies()
        self._update_towers()
        self._handle_wave_spawning(delta_time_ms)
        self._check_wave_completion()
    
    def _update_enemies(self):
        """Update all enemies and remove dead ones"""
        for enemy in self.enemies_group:
            enemy.update()
            if not enemy.alive:
                enemy.kill()
    
    def _update_towers(self):
        """Update all towers with enemy targeting"""
        self.towers_group.update(self.enemies_group, None, self.game_area_x_offset)
    
    def _handle_wave_spawning(self, delta_time_ms: int):
        """Handle enemy spawning for active waves"""
        if not (self.wave_active and self.enemies_remaining_in_wave > 0):
            return
        
        self.spawn_timer += delta_time_ms
        if self.spawn_timer >= 1000:  # Spawn every second
            enemy_type = self._get_next_enemy_type()
            asset_manager = self._get_asset_manager()
            
            spawned_enemy = self.spawn_enemy(enemy_type, asset_manager)
            if spawned_enemy:
                logger.info(f"Spawned {enemy_type} at {spawned_enemy.x}, {spawned_enemy.y}")
            
            self.enemies_remaining_in_wave -= 1
            self.spawn_timer = 0
    
    def _get_next_enemy_type(self) -> str:
        """Get the enemy type for the next spawn"""
        enemy_index = len(self.current_wave_enemy_types) - self.enemies_remaining_in_wave
        
        if 0 <= enemy_index < len(self.current_wave_enemy_types):
            return self.current_wave_enemy_types[enemy_index]
        
        return "defense_drone_1"
    
    def _get_asset_manager(self):
        """Get asset manager from game controller if available"""
        if hasattr(self, 'game_controller') and hasattr(self.game_controller, 'asset_manager'):
            return self.game_controller.asset_manager
        return None
    
    def _check_wave_completion(self):
        """Check if the current wave is complete"""
        if (self.wave_active and 
            self.enemies_remaining_in_wave <= 0 and 
            len(self.enemies_group) == 0):
            self.wave_active = False
            logger.info(f"Wave {self.current_wave} complete")
            
    def draw(self, surface: Surface, camera=None):
        """Draw all game elements"""
        self._draw_enemy_paths(surface, camera)
        self._draw_enemies(surface)
        self._draw_towers(surface, camera)
    
    def _draw_enemy_paths(self, surface: Surface, camera):
        """Draw enemy paths for debugging when camera is available"""
        if camera is not None:
            for enemy in self.enemies_group:
                if hasattr(enemy, 'draw_path'):
                    enemy.draw_path(surface, camera)
    
    def _draw_enemies(self, surface: Surface):
        """Draw all enemies"""
        self.enemies_group.draw(surface)
    
    def _draw_towers(self, surface: Surface, camera):
        """Draw all towers"""
        for tower in self.towers_group:
            tower.draw(surface, camera)
