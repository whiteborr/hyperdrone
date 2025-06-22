# hyperdrone_core/playing_state.pyAdd commentMore actions
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
                            bullet.kill()
                    else:
                        bullet.alive = False
                        bullet.kill()
                        
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
                        missile.kill()  # Ensure missile is removed from sprite group
                        
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
        
        # Spawn enemies for the current level
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
            
        # Display Chapter 1 level information if applicable
        current_chapter = self.game.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            self.game.set_story_message(f"Chapter 1 - Level {self.game.level_manager.chapter1_level} of {self.game.level_manager.chapter1_max_levels}", 3000)
    
    def handle_events(self, events):
        """Handle input events specific to playing state"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                elif event.key == pygame.K_TAB:
                    if self.game.player:
                        self.game.player.cycle_weapon_state()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        """Update game logic for playing state"""
        current_time_ms = pygame.time.get_ticks()
        
        if not self.game.player:
            return
            
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
        self._handle_bullet_enemy_collisions()
        
        # Check for level completion
        if self.game._check_level_clear_condition():
            return  # Level advanced, stop further updates
        
        # Check story objectives for Chapter 1
        current_chapter = self.game.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            # Only complete chapter objectives when we've finished all 4 levels
            if self.game.level_manager.chapter1_level >= self.game.level_manager.chapter1_max_levels:
                # Check if all rings for the level have been collected
                if self.game.level_manager.collected_rings_count >= self.game.level_manager.total_rings_per_level:
                    self.game.story_manager.complete_objective_by_id("c1_collect_rings")

                # Check if all enemies on the level have been defeated
                if self.game.combat_controller.enemy_manager.get_active_enemies_count() == 0:
                    self.game.story_manager.complete_objective_by_id("c1_clear_hostiles")

                # If all objectives for chapter 1 are done, advance the story and go to story map
                if current_chapter.is_complete():
                    self.game.story_manager.advance_chapter()
                    # Transition to the story map to show Chapter 2
                    self.game.state_manager.set_state("StoryMapState")
                    return # Stop further updates in this state as a transition is happening

        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
    
    def draw(self, surface):
        """Draw the playing state"""
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        surface.fill(black_color)
        
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
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
        
        self.game.explosion_particles_group.update()
        self.game.explosion_particles_group.draw(surface)
        
        # Update and draw energy particles
        self.game.energy_particles_group.update()
        self.game.energy_particles_group.draw(surface)
        
        # Draw HUD container for orichalc fragments
        if hasattr(self.game, 'hud_container'):
            orichalc_count = self.game.drone_system.get_cores()
            self.game.hud_container.draw(surface, orichalc_count)
        
        if self.game.player:
            self.game.player.draw(surface)
            
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
            
        ring_icon = self.game.asset_manager.get_image("ring_ui_icon")
        self.game.level_manager.draw_ring_animations(surface, ring_icon)
        
        # Draw fragment animationsAdd commentMore actions
        self.game._draw_fragment_animations()
