# hyperdrone_core/playing_state.py
import pygame
from .state import State
from settings_manager import get_setting

class PlayingState(State):
    """State for the main gameplay"""
    
    def _handle_bullet_enemy_collisions(self):
        """Handle collisions between player bullets/missiles/lightning and enemies"""
        if not self.game.player or not hasattr(self.game.player, 'bullets_group'):
            return
            
        # Get enemy sprites
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if not enemy_sprites:
            return
            
        # Check bullet collisions with enemies
        for bullet in self.game.player.bullets_group:
            for enemy in pygame.sprite.spritecollide(bullet, enemy_sprites, False):
                if enemy.alive and bullet.alive:
                    # Apply damage to enemy
                    enemy.take_damage(bullet.damage)
                    
                    # Handle bullet piercing logic
                    if bullet.max_pierces > 0:
                        bullet.pierces_done += 1
                        if bullet.pierces_done > bullet.max_pierces:
                            bullet.alive = False
                    else:
                        bullet.alive = False
                        
        # Check missile collisions with enemies
        if hasattr(self.game.player, 'missiles_group'):
            for missile in self.game.player.missiles_group:
                for enemy in pygame.sprite.spritecollide(missile, enemy_sprites, False):
                    if enemy.alive and missile.alive:
                        enemy.take_damage(missile.damage)
                        # Create larger explosion for missile hits
                        if hasattr(enemy, 'rect') and enemy.rect:
                            self.game._create_explosion(enemy.rect.centerx, enemy.rect.centery, 10, 'missile_launch')
                        missile.alive = False
                        
        # Check lightning zap collisions with enemies
        if hasattr(self.game.player, 'lightning_zaps_group'):
            for zap in self.game.player.lightning_zaps_group:
                if not hasattr(zap, 'damage_applied') or not zap.damage_applied:
                    # Lightning zaps apply damage to their target directly
                    if zap.initial_target_ref and hasattr(zap.initial_target_ref, 'alive') and zap.initial_target_ref.alive:
                        zap.initial_target_ref.take_damage(zap.damage)
                        # Create lightning effect at target position
                        if hasattr(zap.initial_target_ref, 'rect') and zap.initial_target_ref.rect:
                            self.game._create_explosion(
                                zap.initial_target_ref.rect.centerx, 
                                zap.initial_target_ref.rect.centery, 
                                5, None
                            )
                        zap.damage_applied = True
    
    def enter(self, previous_state=None, **kwargs):
        """Initialize the playing state"""
        self.game.combat_controller.reset_combat_state()
        self.game.puzzle_controller.reset_puzzles_state()
        
        # Clear all collectible groups first
        self.game.collectible_rings_group.empty()
        self.game.power_ups_group.empty()
        self.game.core_fragments_group.empty()
        self.game.vault_logs_group.empty()
        self.game.glyph_tablets_group.empty()
        self.game.architect_echoes_group.empty()
        
        # Initialize maze and player
        self.game.maze = self.game.level_manager.create_maze()
        tile_size = get_setting("display", "TILE_SIZE", 64)
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
        self.game.level_time_remaining_ms = get_setting("gameplay", "LEVEL_TIMER_DURATION", 180000)
        
        # Reset item manager and spawn collectibles
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.reset_for_level()
            # Force immediate spawn of rings
            self.game.item_manager._spawn_all_rings(self.game.maze)
    
    def handle_events(self, events):
        """Handle input events specific to playing state"""
        # --- FIX: Get the current chapter ONCE at the start of the method ---
        # This ensures the variable is always available within the function's scope.
        current_chapter = self.game.story_manager.get_current_chapter()

        for event in events:
            # --- ORIGINAL gameplay logic ---
            if event.type == pygame.KEYDOWN:
                # Handle pausing
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                # Pass other keys to the player_actions handler for movement, shooting etc.
                else:
                    self.game.player_actions.handle_key_down(event)

            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)
            
            # --- NEW story interaction logic ---
            # We still check for KEYDOWN here for our specific story keys
            if event.type == pygame.KEYDOWN:
                # And we check if a chapter is active before trying to use it
                if current_chapter:
                    
                    # Temporary key to complete the 1st objective
                    if event.key == pygame.K_1:
                        if len(current_chapter.objectives) > 0:
                            objective_to_complete_id = current_chapter.objectives[0].objective_id
                            current_chapter.complete_objective_by_id(objective_to_complete_id)

                    # Temporary key to complete the 2nd objective
                    elif event.key == pygame.K_2:
                        if len(current_chapter.objectives) > 1:
                            objective_to_complete_id = current_chapter.objectives[1].objective_id
                            current_chapter.complete_objective_by_id(objective_to_complete_id)
                    
                    # Temporary key to advance to the next chapter
                    elif event.key == pygame.K_n:
                        self.game.story_manager.advance_chapter()
    
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
        
        # Check if player died and handle respawn
        if self.game.player and not self.game.player.alive:
            self.game._handle_player_death_or_life_loss()
        
        # Update combat
        self.game.combat_controller.update(current_time_ms, delta_time)
        
        # Update item manager
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.update(current_time_ms, self.game.maze)
            
        # Handle collectible collisions
        self.game._handle_collectible_collisions()
        
        # Handle bullet-enemy collisions
        self._handle_bullet_enemy_collisions()
        
        # Check if level is cleared
        self.game._check_level_clear_condition()
        
        # Update continuous player movement and actions
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
    
    def draw(self, surface):
        """Draw the playing state"""
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        surface.fill(black_color)
        
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