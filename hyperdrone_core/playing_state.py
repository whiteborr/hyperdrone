# hyperdrone_core/playing_state.py
import pygame
from .state import State

class PlayingState(State):
    """State for the main gameplay"""
    
    def enter(self, previous_state=None, **kwargs):
        """Initialize the playing state"""
        self.game.combat_controller.reset_combat_state()
        self.game.puzzle_controller.reset_puzzles_state()
        
        # Initialize maze and player
        self.game.maze = self.game.level_manager.create_maze()
        spawn_x, spawn_y = self.game._get_safe_spawn_point(self.game.gs.TILE_SIZE * 0.7, self.game.gs.TILE_SIZE * 0.7)
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        
        from entities import PlayerDrone
        self.game.player = PlayerDrone(
            spawn_x, spawn_y, drone_id, drone_stats, 
            self.game.asset_manager, sprite_key, 'crash', 
            self.game.drone_system
        )
        
        # Set up combat controller
        self.game.combat_controller.set_active_entities(
            player=self.game.player, 
            maze=self.game.maze, 
            power_ups_group=self.game.power_ups_group
        )
        
        # Spawn enemies
        self.game.combat_controller.enemy_manager.spawn_enemies_for_level(self.game.level_manager.level)
        
        # Set up puzzle controller
        self.game.puzzle_controller.set_active_entities(
            player=self.game.player, 
            drone_system=self.game.drone_system, 
            scene_manager=self.game.state_manager
        )
        
        # Reset camera
        self.game.camera = None
        
        # Start level timer
        self.game.level_timer_start_ticks = pygame.time.get_ticks()
        self.game.level_time_remaining_ms = self.game.gs.get_game_setting("LEVEL_TIMER_DURATION")
        
        # Reset item manager
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.reset_for_level()
    
    def handle_events(self, events):
        """Handle input events specific to playing state"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        """Update game logic for playing state"""
        current_time_ms = pygame.time.get_ticks()
        
        if not self.game.player:
            return
            
        # Update player
        self.game.player.update(
            current_time_ms, 
            self.game.maze, 
            self.game.combat_controller.enemy_manager.get_sprites(), 
            self.game.player_actions, 
            self.game.maze.game_area_x_offset if self.game.maze else 0
        )
        
        # Update combat
        self.game.combat_controller.update(current_time_ms, delta_time)
        
        # Update item manager
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.update(current_time_ms, self.game.maze)
            
        # Handle collectible collisions
        self.game._handle_collectible_collisions()
        
        # Check if level is cleared
        self.game._check_level_clear_condition()
        
        # Update continuous player movement and actions
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
    
    def draw(self, surface):
        """Draw the playing state"""
        surface.fill(self.game.gs.BLACK)
        
        # Draw maze
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        # Draw collectibles and powerups
        for item_group in [
            self.game.collectible_rings_group, 
            self.game.power_ups_group, 
            self.game.core_fragments_group, 
            self.game.vault_logs_group,
            self.game.glyph_tablets_group, 
            self.game.architect_echoes_group
        ]:
            for item in item_group:
                item.draw(surface, self.game.camera)
        
        # Update and draw explosion particles
        self.game.explosion_particles_group.update()
        self.game.explosion_particles_group.draw(surface)
        
        # Draw player
        if self.game.player:
            self.game.player.draw(surface)
            
        # Draw enemies
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
            
        # Draw animating rings
        ring_icon = self.game.asset_manager.get_image("ring_ui_icon")
        self.game.level_manager.draw_ring_animations(surface, ring_icon)