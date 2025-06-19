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
        
        # Camera has been removed
        self.game.camera = None
        
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
        # Process discrete events
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                elif event.key == pygame.K_SPACE:
                    if self.game.combat_controller.wave_manager:
                        self.game.combat_controller.wave_manager.manual_start_next_wave()
            
            # Handle mouse button down events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                screen_pos = event.pos
                # Check if click is on build menu
                if (self.game.ui_manager.build_menu and 
                    self.game.ui_manager.build_menu.is_mouse_over_build_menu(screen_pos)):
                    self.game.ui_manager.build_menu.handle_input(event, screen_pos)
                else:
                    # Use screen position directly as world position
                    world_pos = screen_pos
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
        if hasattr(self.game.ui_manager, 'build_menu') and self.game.ui_manager.build_menu:
            self.game.ui_manager.build_menu.update(
                pygame.mouse.get_pos(), 
                "maze_defense", 
                None
            )
    
    def draw(self, surface):
        """Draw the maze defense state"""
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        surface.fill(black_color)
        
        # Draw maze
        if self.game.maze:
            self.game.maze.draw(surface, None)
        
        # Draw tower defense elements
        if hasattr(self.game, 'tower_defense_manager'):
            self.game.tower_defense_manager.draw(surface, None)
        
        # Draw turrets
        if self.game.turrets_group:
            for turret in self.game.turrets_group:
                turret.draw(surface, None)
        
        # Draw reactor
        if self.game.reactor_group:
            for reactor in self.game.reactor_group:
                reactor.draw(surface, None)
        
        # Draw enemies
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, None)
        
        # Update and draw explosion particles
        self.game.explosion_particles_group.update()
        self.game.explosion_particles_group.draw(surface)
        
        # Draw build menu if in build phase
        if (self.game.ui_manager.build_menu and 
            self.game.ui_manager.build_menu.is_active and 
            self.game.is_build_phase):
            self.game.ui_manager.build_menu.draw(surface)