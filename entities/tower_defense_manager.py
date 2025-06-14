import pygame
import logging
import random
from typing import List, Tuple, Dict, Optional
from entities.path_manager import PathManager
from entities.enemy_pathfinder import PathfindingEnemy
from entities.turret import Turret
from settings_manager import get_setting

logger = logging.getLogger(__name__)

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
        
        # Sprite groups
        self.enemies_group = pygame.sprite.Group()
        self.towers_group = pygame.sprite.Group()
        
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
        if hasattr(maze, 'grid'):
            # Make a deep copy of the grid to avoid modifying the original
            import copy
            grid_copy = copy.deepcopy(maze.grid)
            self.path_manager.set_grid(grid_copy)
            
        # Set goal point (core reactor position)
        if hasattr(maze, 'core_reactor_grid_pos') and maze.core_reactor_grid_pos:
            self.path_manager.set_goal_point(maze.core_reactor_grid_pos)
            
        # Set spawn points
        if hasattr(maze, 'ENEMY_SPAWN_GRID_POSITIONS'):
            self.path_manager.set_spawn_points(maze.ENEMY_SPAWN_GRID_POSITIONS)
            
        # Log initialization status
        logger.info(f"TowerDefenseManager initialized with grid size: {self.grid_width}x{self.grid_height}")
        logger.info(f"Goal point set to: {self.path_manager.goal_point}")
        logger.info(f"Spawn points: {len(self.path_manager.spawn_points)}")
            
    def try_place_tower(self, screen_pos: Tuple[int, int], asset_manager) -> bool:
        """
        Try to place a tower at the given screen position
        Returns True if tower was placed, False otherwise
        """
        # Convert screen position to grid position
        x, y = screen_pos
        x -= self.game_area_x_offset  # Adjust for game area offset
        grid_col = int(x // self.tile_size)
        grid_row = int(y // self.tile_size)
        
        # Check if tower can be placed
        if not self.path_manager.can_place_tower(grid_row, grid_col):
            logger.info(f"Cannot place tower at ({grid_row}, {grid_col}) - would block all paths")
            return False
            
        # Check if player has enough resources
        tower_cost = Turret.TURRET_COST
        if self.player_resources < tower_cost:
            logger.info(f"Not enough resources to place tower (need {tower_cost})")
            return False
            
        # Place tower
        tile_center_x = grid_col * self.tile_size + self.tile_size // 2 + self.game_area_x_offset
        tile_center_y = grid_row * self.tile_size + self.tile_size // 2
        
        # Create new tower
        new_tower = Turret(tile_center_x, tile_center_y, None, asset_manager)
        self.towers_group.add(new_tower)
        
        # Update grid to mark tower position
        self.path_manager.grid[grid_row][grid_col] = 'T'
        
        # Deduct resources
        self.player_resources -= tower_cost
        
        # Trigger path recalculation for all enemies
        self.recalculate_all_enemy_paths()
        
        return True
        
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
            
        # Choose a random spawn point
        spawn_point = random.choice(self.path_manager.spawn_points)
        
        # Import the DefenseDronePathfinder class
        from entities.defense_drone_pathfinder import DefenseDronePathfinder
        
        # Create enemy based on type
        enemy = None
        
        # Check if this is a defense drone type
        if enemy_type.startswith("defense_drone_") and asset_manager:
            drone_number = enemy_type.split("_")[-1]
            sprite_key = f"defense_drone_{drone_number}_sprite_key"
            
            # Create appropriate defense drone with proper sprite
            if drone_number == "1":
                health = get_setting("gameplay", "DEFENSE_DRONE_1_HEALTH", 100)
                speed = get_setting("gameplay", "DEFENSE_DRONE_1_SPEED", 1.0)
                enemy = DefenseDronePathfinder(spawn_point, self.path_manager, asset_manager, sprite_key, speed=speed, health=health)
            elif drone_number == "2":
                health = get_setting("gameplay", "DEFENSE_DRONE_2_HEALTH", 200)
                speed = get_setting("gameplay", "DEFENSE_DRONE_2_SPEED", 0.7)
                enemy = DefenseDronePathfinder(spawn_point, self.path_manager, asset_manager, sprite_key, speed=speed, health=health)
            elif drone_number == "3":
                health = get_setting("gameplay", "DEFENSE_DRONE_3_HEALTH", 80)
                speed = get_setting("gameplay", "DEFENSE_DRONE_3_SPEED", 1.5)
                enemy = DefenseDronePathfinder(spawn_point, self.path_manager, asset_manager, sprite_key, speed=speed, health=health)
            elif drone_number == "4":
                health = get_setting("gameplay", "DEFENSE_DRONE_4_HEALTH", 300)
                speed = get_setting("gameplay", "DEFENSE_DRONE_4_SPEED", 0.5)
                enemy = DefenseDronePathfinder(spawn_point, self.path_manager, asset_manager, sprite_key, speed=speed, health=health)
            elif drone_number == "5":
                health = get_setting("gameplay", "DEFENSE_DRONE_5_HEALTH", 150)
                speed = get_setting("gameplay", "DEFENSE_DRONE_5_SPEED", 1.2)
                enemy = DefenseDronePathfinder(spawn_point, self.path_manager, asset_manager, sprite_key, speed=speed, health=health)
        else:
            # Create basic enemy types
            if enemy_type == 'basic':
                enemy = PathfindingEnemy(spawn_point, self.path_manager, speed=1.0, health=100)
            elif enemy_type == 'fast':
                enemy = PathfindingEnemy(spawn_point, self.path_manager, speed=2.0, health=50)
            elif enemy_type == 'tank':
                enemy = PathfindingEnemy(spawn_point, self.path_manager, speed=0.5, health=200)
            
        if enemy:
            self.enemies_group.add(enemy)
            return enemy
        return None
        
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
        # Update enemies
        self.enemies_group.update()
        
        # Update towers
        self.towers_group.update(self.enemies_group, None, self.game_area_x_offset)
        
        # Handle enemy spawning for active wave
        if self.wave_active and self.enemies_remaining_in_wave > 0:
            self.spawn_timer += delta_time_ms
            if self.spawn_timer >= 1000:  # Spawn every second
                # Get the enemy type for this spawn
                enemy_index = len(self.current_wave_enemy_types) - self.enemies_remaining_in_wave
                if 0 <= enemy_index < len(self.current_wave_enemy_types):
                    enemy_type = self.current_wave_enemy_types[enemy_index]
                else:
                    enemy_type = "basic"
                
                # Get asset manager from game controller if available
                asset_manager = None
                if hasattr(self, 'game_controller') and hasattr(self.game_controller, 'asset_manager'):
                    asset_manager = self.game_controller.asset_manager
                
                self.spawn_enemy(enemy_type, asset_manager)
                self.enemies_remaining_in_wave -= 1
                self.spawn_timer = 0
                
        # Check if wave is complete
        if self.wave_active and self.enemies_remaining_in_wave <= 0 and len(self.enemies_group) == 0:
            self.wave_active = False
            logger.info(f"Wave {self.current_wave} complete")
            
    def draw(self, surface: pygame.Surface, camera=None):
        """Draw all game elements"""
        # Draw enemies
        for enemy in self.enemies_group:
            enemy.draw_path(surface, camera)  # Debug path drawing
            
        self.enemies_group.draw(surface)
        
        # Draw towers
        for tower in self.towers_group:
            tower.draw(surface, camera)