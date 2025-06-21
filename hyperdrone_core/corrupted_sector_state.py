# hyperdrone_core/corrupted_sector_state.pyAdd commentMore actions
import pygame
import random
import logging
from .state import State
from settings_manager import get_setting
from entities import Maze, GlitchingWall, PlayerDrone

logger = logging.getLogger(__name__)

class CorruptedSectorState(State):
    """
    Manages the gameplay for Chapter 3: The Corrupted Sector.
    This state will feature environmental puzzles, hazards, and lore collection.
    """
    def _handle_bullet_enemy_collisions(self):
        """Handle collisions between player bullets/missiles/lightning and enemies"""
        if not self.game.player or not hasattr(self.game.player, 'bullets_group'):
            return
            
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if not enemy_sprites:
            return
            
        # Check bullet collisions with enemies
        for bullet in self.game.player.bullets_group:
            for enemy in pygame.sprite.spritecollide(bullet, enemy_sprites, False):
                if enemy.alive and bullet.alive:
                    enemy.take_damage(bullet.damage)
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
                        if hasattr(enemy, 'rect') and enemy.rect:
                            self.game._create_explosion(enemy.rect.centerx, enemy.rect.centery, 10, 'missile_launch')
                        missile.alive = False
                        missile.kill()
                        
        # Check lightning zap collisions with enemies
        if hasattr(self.game.player, 'lightning_zaps_group'):
            for zap in self.game.player.lightning_zaps_group:
                if not hasattr(zap, 'damage_applied') or not zap.damage_applied:
                    if zap.initial_target_ref and hasattr(zap.initial_target_ref, 'alive') and zap.initial_target_ref.alive:
                        zap.initial_target_ref.take_damage(zap.damage)
                        if hasattr(zap.initial_target_ref, 'rect') and zap.initial_target_ref.rect:
                            self.game._create_explosion(
                                zap.initial_target_ref.rect.centerx, 
                                zap.initial_target_ref.rect.centery, 
                                5, None
                            )
                        zap.damage_applied = True

    def _spawn_glitching_walls(self):
        """
        Finds empty path tiles in the maze and spawns GlitchingWall hazards.
        """
        if not self.game.maze or not self.game.player:
            return

        # Clear any existing walls from previous attempts
        self.game.glitching_walls_group.empty()

        # Get player position in grid coordinates
        player_grid_x = int((self.game.player.x - self.game.maze.game_area_x_offset) // self.game.maze.tile_size)
        player_grid_y = int(self.game.player.y // self.game.maze.tile_size)

        walkable_cells = []
        for r, row in enumerate(self.game.maze.grid):
            for c, tile in enumerate(row):
                if tile == 0: # 0 represents a walkable path
                    # Avoid spawning too close to the edges and player
                    distance_to_player = abs(r - player_grid_y) + abs(c - player_grid_x)
                    if 1 < r < self.game.maze.actual_maze_rows - 2 and \
                       1 < c < self.game.maze.actual_maze_cols - 2 and \
                       distance_to_player > 3:  # Keep walls at least 3 tiles away from player
                        walkable_cells.append((r, c))
        
        random.shuffle(walkable_cells)

        # Get number of walls to spawn from settings
        num_walls_to_spawn = get_setting("hazards", "GLITCH_WALL_COUNT", 8)  # Reduced count
        
        for i in range(min(num_walls_to_spawn, len(walkable_cells))):
            grid_r, grid_c = walkable_cells[i]
            
            # Convert grid position to absolute pixel position
            tile_size = self.game.maze.tile_size
            x = grid_c * tile_size + self.game.maze.game_area_x_offset
            y = grid_r * tile_size
            
            # Create the wall and add it to the game's group
            new_wall = GlitchingWall(x, y)
            self.game.glitching_walls_group.add(new_wall)

    def enter(self, previous_state=None, **kwargs):
        """Initializes the corrupted sector level."""
        logger.info("Entering CorruptedSectorState...")
        self.game.maze = Maze(maze_type="corrupted")

        # --- Robust Player Initialization ---
        # Get a safe spawn position for the player
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        player_spawn_pos = self.game._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)

        # Always create a fresh player drone for this state
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        self.game.player = PlayerDrone(
            player_spawn_pos[0], player_spawn_pos[1], drone_id, drone_stats,
            self.game.asset_manager, sprite_key, 'crash', self.game.drone_system
        )
        
        # Reset lives to starting value
        self.game.lives = get_setting("gameplay", "PLAYER_LIVES", 3)
        
        # Spawn the corrupted logs for this chapter's objectives
        log_ids = ["log_alpha", "log_beta"] 
        self.game.item_manager.spawn_corrupted_logs(self.game.maze, log_ids)

        # Temporarily disable glitching walls to prevent immediate death
        # self._spawn_glitching_walls()

        # Set up combat controller and spawn enemies
        self.game.combat_controller.set_active_entities(
            player=self.game.player, 
            maze=self.game.maze, 
            power_ups_group=self.game.power_ups_group
        )
        self.game.combat_controller.enemy_manager.spawn_enemies_for_level(3)

        current_chapter = self.game.story_manager.get_current_chapter()
        if not (current_chapter and current_chapter.chapter_id == "chapter_3"):
             logger.warning("Entered CorruptedSectorState but not on Chapter 3 in story.")
             
    def update(self, delta_time):
        """Update game logic for the corrupted sector."""
        current_time_ms = pygame.time.get_ticks()

        if not self.game.player:
            self.game.state_manager.set_state("MainMenuState")
            return
            
        self.game.player.update(current_time_ms, self.game.maze, self.game.combat_controller.enemy_manager.get_sprites(), self.game.player_actions, self.game.maze.game_area_x_offset if self.game.maze else 0)
        self.game.combat_controller.update(current_time_ms, delta_time)
        self._handle_bullet_enemy_collisions()

        # --- MODIFICATION: Direct Objective Completion Logic ---
        # Check for player collection of logs
        collected_log_id = self.game._handle_collectible_collisions()
        if collected_log_id:
            # Directly find the matching objective and complete it.
            # Example: If collected_log_id is "log_alpha", complete objective with target "log_alpha"
            for objective in self.game.story_manager.get_current_chapter().objectives:
                if objective.target == collected_log_id:
                    self.game.story_manager.complete_objective_by_id(objective.objective_id)
        
        # Check if all objectives for Chapter 3 are complete
        current_chapter = self.game.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_3" and current_chapter.is_complete():
            self.game.story_manager.advance_chapter()
            self.game.state_manager.set_state("StoryMapState")
            logger.info("Chapter 3 Complete! Transitioning...")

        if not self.game.player.alive:
            self.game._handle_player_death_or_life_loss()
        
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
        
    def handle_events(self, events):
        """Handle player input."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)

    def draw(self, surface):
        """Render the corrupted sector."""
        surface.fill((30, 10, 30))
        
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
            
        # Draw the corrupted logs
        if self.game.corrupted_logs_group:
            self.game.corrupted_logs_group.draw(surface)

        # Draw the glitching walls
        if self.game.glitching_walls_group:
            for wall in self.game.glitching_walls_group:
                wall.draw(surface, self.game.camera)

        if self.game.player:
            self.game.player.draw(surface)
            
        self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        
        # Draw the main UI hud
        if self.game.player and hasattr(self.game.player, 'active_abilities'):
            self.game.ui_manager.draw_gameplay_hud(self.game.player.active_abilities)
        else:
            self.game.ui_manager.draw_gameplay_hud()