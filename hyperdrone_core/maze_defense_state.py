# hyperdrone_core/maze_defense_state.py
import pygame
from .state import State
from settings_manager import get_setting

class MazeDefenseState(State):
    """State for the maze defense gameplay mode"""
    
    def enter(self, previous_state=None, **kwargs):
        """Initialize the maze defense state"""
        self.game.combat_controller.reset_combat_state()
        self.game.puzzle_controller.reset_puzzles_state()
        
        # Create maze for defense mode
        from entities.maze_chapter3 import MazeChapter3
        self.game.maze = MazeChapter3(game_area_x_offset=300)
        
        # Get tile size from settings
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        
        # Set up camera
        from hyperdrone_core.camera import Camera
        self.game.camera = Camera(
            self.game.maze.actual_maze_cols * tile_size, 
            self.game.maze.actual_maze_rows * tile_size
        )
        
        # Set initial zoom level
        if hasattr(self.game.maze, 'initial_zoom_level'):
            self.game.camera.zoom_level = self.game.maze.initial_zoom_level
        
        # Initialize tower defense manager
        from entities.tower_defense_manager import TowerDefenseManager
        self.game.tower_defense_manager = TowerDefenseManager(
            self.game.maze.actual_maze_cols, 
            self.game.maze.actual_maze_rows, 
            tile_size, 
            self.game.maze.game_area_x_offset
        )
        
        # Set game controller reference
        self.game.tower_defense_manager.game_controller = self.game
        self.game.tower_defense_manager.initialize_from_maze(self.game.maze)
        
        # Create core reactor
        reactor_pos = self.game.maze.get_core_reactor_spawn_position_abs()
        if reactor_pos:
            reactor_health = get_setting("defense_mode", "DEFENSE_REACTOR_HEALTH", 1000)
            from entities.core_reactor import CoreReactor
            self.game.core_reactor = CoreReactor(
                reactor_pos[0], reactor_pos[1], 
                self.game.asset_manager, 
                health=reactor_health
            )
            self.game.reactor_group.empty()  # Clear any existing reactors
            self.game.reactor_group.add(self.game.core_reactor)
            
        # Set active entities
        self.game.combat_controller.set_active_entities(
            player=None, 
            maze=self.game.maze, 
            core_reactor=self.game.core_reactor, 
            turrets_group=self.game.turrets_group
        )
        
        # Start first build phase
        self.game.combat_controller.wave_manager.start_first_build_phase()
        self.game.is_build_phase = True
    
    def handle_events(self, events):
        """Handle input events specific to maze defense state"""
        # Handle continuous key presses for camera panning
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = 1
        
        if (dx != 0 or dy != 0) and self.game.camera:
            self.game.camera.pan(dx, dy)
        
        # Process discrete events
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                elif event.key == pygame.K_SPACE:
                    if self.game.combat_controller.wave_manager:
                        self.game.combat_controller.wave_manager.manual_start_next_wave()
            
            # Handle mouse wheel for zoom
            elif event.type == pygame.MOUSEWHEEL and self.game.camera:
                if event.y > 0: 
                    self.game.camera.zoom(1.1)
                elif event.y < 0: 
                    self.game.camera.zoom(0.9)
            
            # Handle mouse button down events
            elif event.type == pygame.MOUSEBUTTONDOWN and self.game.camera:
                screen_pos = event.pos
                # Check if click is on build menu
                if (self.game.ui_manager.build_menu and 
                    self.game.ui_manager.build_menu.is_mouse_over_build_menu(screen_pos)):
                    self.game.ui_manager.build_menu.handle_input(event, screen_pos)
                else:
                    # Convert screen position to world position
                    world_pos = self.game.camera.screen_to_world(screen_pos)
                    if event.button == 1:  # Left click
                        self.game.combat_controller.try_place_turret(world_pos)
                    elif event.button == 3:  # Right click
                        self.game.combat_controller.try_upgrade_clicked_turret(world_pos)
    
    def update(self, delta_time):
        """Update game logic for maze defense state"""
        current_time_ms = pygame.time.get_ticks()
        
        # Update combat controller
        self.game.combat_controller.update(current_time_ms, delta_time)
        
        # Update build menu if available
        if (self.game.camera and hasattr(self.game.ui_manager, 'build_menu') and 
            self.game.ui_manager.build_menu):
            self.game.ui_manager.build_menu.update(
                pygame.mouse.get_pos(), 
                "maze_defense", 
                self.game.camera
            )
    
    def draw(self, surface):
        """Draw the maze defense state"""
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        surface.fill(black_color)
        
        # Draw maze
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        # Draw tower defense elements
        if hasattr(self.game, 'tower_defense_manager'):
            self.game.tower_defense_manager.draw(surface, self.game.camera)
        
        # Draw turrets
        if self.game.turrets_group:
            for turret in self.game.turrets_group:
                turret.draw(surface, self.game.camera)
        
        # Draw reactor
        if self.game.reactor_group:
            for reactor in self.game.reactor_group:
                reactor.draw(surface, self.game.camera)
        
        # Draw enemies
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        
        # Update and draw explosion particles
        self.game.explosion_particles_group.update()
        self.game.explosion_particles_group.draw(surface)
        
        # Draw build menu if in build phase
        if (self.game.ui_manager.build_menu and 
            self.game.ui_manager.build_menu.is_active and 
            self.game.is_build_phase):
            self.game.ui_manager.build_menu.draw(surface)