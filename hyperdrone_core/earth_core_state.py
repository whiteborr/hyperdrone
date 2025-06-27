# hyperdrone_core/earth_core_state.py
from pygame import KEYDOWN, KEYUP, K_p, K_ESCAPE
from pygame.time import get_ticks
from pygame.sprite import spritecollide
from .state import State
from settings_manager import get_setting
from constants import GAME_STATE_STORY_MAP

class EarthCoreState(State):
    """Chapter 1: Earth Core - simplified to work like PlayingState"""
    
    def __init__(self, game_controller):
        super().__init__(game_controller)
    
    def get_state_id(self):
        return "EarthCoreState"
    
    def enter(self, previous_state=None, **kwargs):
        """Initialize like PlayingState"""
        self.game.combat_controller.reset_combat_state()
        
        # Clear all collectible groups like PlayingState
        self.game.collectible_rings_group.empty()
        self.game.power_ups_group.empty()
        self.game.core_fragments_group.empty()
        self.game.vault_logs_group.empty()
        self.game.glyph_tablets_group.empty()
        self.game.architect_echoes_group.empty()
        
        # Initialize maze and player like PlayingState
        self.game.maze = self.game.level_manager.create_maze()
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        spawn_x, spawn_y = self.game._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
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
        self.game.combat_controller.enemy_manager.spawn_enemies_for_level(1)
        
        # Reset item manager and spawn collectibles
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.reset_for_level()
            self.game.item_manager._spawn_all_rings(self.game.maze)
    
    def exit(self, next_state=None):
        pass
    
    def handle_events(self, events):
        """Handle events like PlayingState"""
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    self.game.toggle_pause()
                elif event.key == K_ESCAPE:
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        """Update like PlayingState"""
        current_time_ms = get_ticks()
        
        if not self.game.player:
            return
            
        # Update like PlayingState
        self.game.player.update(
            current_time_ms, 
            self.game.maze, 
            self.game.combat_controller.enemy_manager.get_sprites(), 
            self.game.player_actions, 
            self.game.maze.game_area_x_offset if self.game.maze else 0
        )
        
        if self.game.player and not self.game.player.alive:
            self.game._handle_player_death_or_life_loss()
        
        self.game.combat_controller.update(current_time_ms, delta_time)
        
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.update(current_time_ms, self.game.maze)
            
        self.game._handle_collectible_collisions()
        
        # Handle bullet-enemy collisions like PlayingState
        self._handle_bullet_enemy_collisions()
        
        # Check for level clear condition like PlayingState
        if self.game.level_manager.check_level_clear_condition():
            pass  # Level progression handled by level manager
        
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
    
    def _handle_bullet_enemy_collisions(self):
        """Handle collisions between player bullets and enemies - copied from PlayingState"""
        if not self.game.player or not hasattr(self.game.player, 'bullets_group'):
            return
            
        # Get enemy sprites
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if not enemy_sprites:
            return
            
        # Check bullet collisions with enemies
        for bullet in self.game.player.bullets_group:
            for enemy in spritecollide(bullet, enemy_sprites, False):
                if enemy.alive and bullet.alive:
                    # Apply damage to enemy
                    enemy.take_damage(bullet.damage)
                    
                    # Handle bullet piercing logic
                    if bullet.max_pierces > 0:
                        bullet.pierces_done += 1
                        if bullet.pierces_done > bullet.max_pierces:
                            bullet.alive = False
                            bullet.kill()
                    else:
                        bullet.alive = False
                        bullet.kill()
    
    def draw(self, surface):
        """Draw like PlayingState"""
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        surface.fill(black_color)
        
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        # Draw all collectible groups like PlayingState
        for item_group in [
            self.game.collectible_rings_group, 
            self.game.power_ups_group, 
            self.game.core_fragments_group, 
            self.game.vault_logs_group,
            self.game.glyph_tablets_group, 
            self.game.architect_echoes_group,
            self.game.spawned_barricades_group
        ]:
            for item in item_group:
                item.draw(surface, self.game.camera)
                # Update orichalc fragments
                from entities.orichalc_fragment import OrichalcFragment
                if isinstance(item, OrichalcFragment):
                    item.update()
        
        # Draw explosion particles
        self.game.explosion_particles_group.update()
        self.game.explosion_particles_group.draw(surface)
        
        # Draw energy particles
        self.game.energy_particles_group.update()
        self.game.energy_particles_group.draw(surface)
        
        if self.game.player:
            self.game.player.draw(surface)
            
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        
        # Draw ring animations
        ring_icon = self.game.asset_manager.get_image("ring_ui_icon")
        self.game.level_manager.draw_ring_animations(surface, ring_icon)
        
        # Draw fragment animations
        self.game._draw_fragment_animations()