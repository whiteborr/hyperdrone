# hyperdrone_core/corrupted_sector_state.py
from pygame.sprite import spritecollide
from pygame.time import get_ticks
from pygame import KEYDOWN, KEYUP, K_p, K_l, K_ESCAPE
from pygame.font import Font
from random import shuffle, randint
from logging import getLogger, info, warning
from .state import State
from settings_manager import get_setting
from entities import Maze, GlitchingWall, PlayerDrone
from entities.elemental_core import ElementalCore, CipherCore
from entities.particle import ParticleSystem
from constants import GAME_STATE_STORY_MAP
import pygame

logger = getLogger(__name__)

class CorruptedSectorState(State):
    """
    Chapter 3: Corruption Sector - Air Core Puzzle Maze
    
    Features shifting corridors, glitching logic, spatial puzzles, and glyph decoding.
    The player must navigate through a maze where walls move and logic is corrupted.
    Collect the Air Core to unlock enhanced sensors and logic-shifting abilities.
    """
    
    def __init__(self, game_controller):
        super().__init__(game_controller)
        # Air Core system
        self.air_core = None
        self.cipher_core = CipherCore()
        self.core_collected = False
        self.particles = ParticleSystem()
        
        # Chapter state
        self.chapter_complete = False
        self.objectives_completed = 0
        self.total_objectives = 4  # Increased for glyph puzzles
        
        # Glyph puzzle system
        self.glyph_chambers = []
        self.active_glyphs = set()
        self.glyph_sequence = []
        self.player_sequence = []
        self.glyph_puzzle_active = False
        
        # Air Core abilities
        self.logic_shift_cooldown = 0
        self.enhanced_sensors_active = False
        self.sensor_range = 300
        
        # UI elements
        self.font = Font(None, 36)
        self.small_font = Font(None, 24)
    def _handle_bullet_enemy_collisions(self):
        """Handle collisions between player bullets/missiles/lightning and enemies"""
        if not self.game.player or not hasattr(self.game.player, 'bullets_group'):
            return
            
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if not enemy_sprites:
            return
            
        # Check bullet collisions with enemies
        for bullet in self.game.player.bullets_group:
            for enemy in spritecollide(bullet, enemy_sprites, False):
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
                for enemy in spritecollide(missile, enemy_sprites, False):
                    if enemy.alive and missile.alive:
                        enemy.take_damage(missile.damage)
                        if hasattr(enemy, 'rect') and enemy.rect:
                            self.game._create_explosion(enemy.rect.centerx, enemy.rect.centery, 10, 'missile_launch')
                        missile.alive = False
                        missile.kill()
    
    def _setup_glyph_chambers(self):
        """Setup glyph puzzle chambers"""
        if not hasattr(self.game, 'maze') or not self.game.maze:
            return
            
        tile_size = getattr(self.game.maze, 'tile_size', 80)
        
        # Create 4 glyph chambers
        for i in range(4):
            x = (i * 6 + 4) * tile_size
            y = (i * 3 + 5) * tile_size
            
            chamber = {
                'rect': pygame.Rect(x, y, tile_size, tile_size),
                'glyph_id': i + 1,
                'activated': False,
                'glow_alpha': 128
            }
            self.glyph_chambers.append(chamber)
        
        # Generate random glyph sequence
        self.glyph_sequence = [randint(1, 4) for _ in range(4)]
        logger.info(f"Glyph sequence generated: {self.glyph_sequence}")
    
    def _find_air_core_chamber(self):
        """Find position for Air Core chamber"""
        if not hasattr(self.game, 'maze') or not self.game.maze:
            return (400, 300)  # Default position
            
        tile_size = getattr(self.game.maze, 'tile_size', 80)
        cols = getattr(self.game.maze, 'cols', 10)
        rows = getattr(self.game.maze, 'rows', 10)
        
        # Place in center-left area
        center_x = (cols // 4) * tile_size
        center_y = (rows // 2) * tile_size
        return (center_x, center_y)
    
    def _collect_air_core(self):
        """Handle Air Core collection"""
        if self.air_core.collect():
            self.core_collected = True
            
            # Insert into Cipher Core
            self.cipher_core.insert_core(ElementalCore.AIR, self.air_core)
            
            # Play collection sound
            if hasattr(self.game, 'asset_manager'):
                self.game.asset_manager.play_sound("collect_fragment")
            
            # Create air particle effect
            self.particles.create_explosion(
                self.air_core.rect.centerx,
                self.air_core.rect.centery,
                (135, 206, 235),  # Sky blue
                particle_count=30
            )
            
            # Activate enhanced sensors
            self.enhanced_sensors_active = True
            
            # Show message
            if hasattr(self.game, 'set_story_message'):
                self.game.set_story_message("Air Core collected! Enhanced sensors and logic shift unlocked!", 4000)
            logger.info("Air Core collected! Logic abilities unlocked.")
    
    def _activate_logic_shift(self):
        """Activate Air Core logic shift ability"""
        current_time = get_ticks()
        
        if current_time < self.logic_shift_cooldown:
            return  # Still on cooldown
        
        if not self.cipher_core.has_ability("logic_shift"):
            return  # Don't have the ability
        
        # Set cooldown
        self.logic_shift_cooldown = current_time + 10000  # 10 second cooldown
        
        # Create logic shift effect
        if hasattr(self.game, 'player') and self.game.player:
            player_pos = self.game.player.rect.center
            self.particles.create_explosion(
                player_pos[0], player_pos[1],
                (135, 206, 235),  # Air blue
                particle_count=25
            )
        
        # Play shift sound
        if hasattr(self.game, 'asset_manager'):
            self.game.asset_manager.play_sound("ui_confirm")
        
        logger.info("Logic shift activated! Corruption temporarily stabilized.")
    
    def _input_glyph_sequence(self, glyph_num):
        """Handle glyph sequence input"""
        if not self.glyph_puzzle_active:
            # Start glyph puzzle if near a chamber
            if hasattr(self.game, 'player') and self.game.player:
                player_pos = self.game.player.rect.center
                for chamber in self.glyph_chambers:
                    distance = ((chamber['rect'].centerx - player_pos[0])**2 + (chamber['rect'].centery - player_pos[1])**2)**0.5
                    if distance < 100:  # Within range
                        self.glyph_puzzle_active = True
                        self.player_sequence = []
                        if hasattr(self.game, 'set_story_message'):
                            self.game.set_story_message("Glyph puzzle activated! Input the correct sequence.", 3000)
                        break
        
        if self.glyph_puzzle_active:
            self.player_sequence.append(glyph_num)
            
            # Check if sequence is complete
            if len(self.player_sequence) >= len(self.glyph_sequence):
                if self.player_sequence == self.glyph_sequence:
                    # Correct sequence!
                    self._solve_glyph_puzzle()
                else:
                    # Wrong sequence, reset
                    self.player_sequence = []
                    if hasattr(self.game, 'set_story_message'):
                        self.game.set_story_message("Incorrect sequence. Try again.", 2000)
    
    def _solve_glyph_puzzle(self):
        """Handle successful glyph puzzle solution"""
        self.glyph_puzzle_active = False
        self.objectives_completed += 1
        
        # Create success effect
        for chamber in self.glyph_chambers:
            chamber['activated'] = True
            self.particles.create_explosion(
                chamber['rect'].centerx,
                chamber['rect'].centery,
                (255, 215, 0),  # Gold
                particle_count=15
            )
        
        # Play success sound
        if hasattr(self.game, 'asset_manager'):
            self.game.asset_manager.play_sound("lore_unlock")
        
        if hasattr(self.game, 'set_story_message'):
            self.game.set_story_message("Glyph puzzle solved! Corruption reduced.", 3000)
        logger.info("Glyph puzzle solved successfully!")
    
    def _update_air_abilities(self, current_time):
        """Update Air Core abilities"""
        # Enhanced sensors show hidden enemies and passages
        if self.enhanced_sensors_active:
            # Could reveal hidden elements in the maze
            pass
    
    def _update_glyph_puzzles(self, current_time):
        """Update glyph puzzle effects"""
        # Update glyph chamber glow effects
        for chamber in self.glyph_chambers:
            if chamber['activated']:
                chamber['glow_alpha'] = 255
            else:
                chamber['glow_alpha'] = int(128 + 127 * pygame.math.sin(current_time * 0.005))
    
    def _draw_glyph_chambers(self, surface, camera_offset):
        """Draw glyph puzzle chambers"""
        for chamber in self.glyph_chambers:
            # Draw chamber
            draw_rect = chamber['rect'].copy()
            draw_rect.x -= camera_offset[0]
            draw_rect.y -= camera_offset[1]
            
            if chamber['activated']:
                color = (255, 215, 0)  # Gold when activated
            else:
                color = (100, 100, 200)  # Blue when inactive
            
            pygame.draw.rect(surface, color, draw_rect)
            pygame.draw.rect(surface, (255, 255, 255), draw_rect, 2)
            
            # Draw glyph number
            font = Font(None, 48)
            glyph_text = font.render(str(chamber['glyph_id']), True, (255, 255, 255))
            text_rect = glyph_text.get_rect(center=draw_rect.center)
            surface.blit(glyph_text, text_rect)
    
    def _draw_sensor_range(self, surface, camera_offset):
        """Draw enhanced sensor range visualization"""
        if not self.enhanced_sensors_active or not hasattr(self.game, 'player') or not self.game.player:
            return
        
        player_pos = self.game.player.rect.center
        draw_pos = (player_pos[0] - camera_offset[0], player_pos[1] - camera_offset[1])
        
        # Draw sensor range circle
        sensor_surface = pygame.Surface((self.sensor_range * 2, self.sensor_range * 2), pygame.SRCALPHA)
        pygame.draw.circle(sensor_surface, (135, 206, 235, 50), (self.sensor_range, self.sensor_range), self.sensor_range)
        
        sensor_rect = sensor_surface.get_rect(center=draw_pos)
        surface.blit(sensor_surface, sensor_rect)
    
    def _complete_chapter(self):
        """Complete Chapter 3"""
        self.chapter_complete = True
        
        # Show completion message
        if hasattr(self.game, 'set_story_message'):
            self.game.set_story_message("Chapter 3 Complete! Air Core secured, corruption purged.", 3000)
        
        # Transition back to story map
        self.game.state_manager.set_state(
            GAME_STATE_STORY_MAP,
            chapter_completed=True,
            completed_chapter="Chapter 3: Corruption Sector"
        )
    
    def _draw_air_core_ui(self, surface):
        """Draw Air Core specific UI elements"""
        current_time = get_ticks()
        
        # Chapter title
        title_text = self.font.render("Chapter 3: Corruption Sector", True, (255, 215, 0))
        surface.blit(title_text, (10, 10))
        
        # Objectives
        obj_text = f"Objectives: {self.objectives_completed}/{self.total_objectives}"
        obj_surface = self.small_font.render(obj_text, True, (255, 255, 255))
        surface.blit(obj_surface, (10, 50))
        
        # Air Core status
        if self.core_collected:
            core_status = "Air Core: Collected"
            core_color = (135, 206, 235)  # Sky blue
        else:
            core_status = "Air Core: Not Found"
            core_color = (128, 128, 128)
        
        core_surface = self.small_font.render(core_status, True, core_color)
        surface.blit(core_surface, (10, surface.get_height() - 80))
        
        # Abilities status
        if self.core_collected:
            # Logic shift cooldown
            if current_time < self.logic_shift_cooldown:
                cooldown_left = (self.logic_shift_cooldown - current_time) // 1000
                shift_text = f"Logic Shift: {cooldown_left}s cooldown"
                shift_color = (255, 100, 100)
            else:
                shift_text = "Logic Shift: Ready (Press L)"
                shift_color = (100, 255, 100)
            
            shift_surface = self.small_font.render(shift_text, True, shift_color)
            surface.blit(shift_surface, (10, surface.get_height() - 50))
        
        # Glyph puzzle status
        if self.glyph_puzzle_active:
            glyph_text = f"Glyph Sequence: {len(self.player_sequence)}/{len(self.glyph_sequence)}"
            glyph_surface = self.small_font.render(glyph_text, True, (255, 215, 0))
            surface.blit(glyph_surface, (10, surface.get_height() - 20))
        
        # Controls
        controls_text = self.small_font.render("Keys 1-4: Glyph input | L: Logic shift", True, (200, 200, 200))
        surface.blit(controls_text, (10, surface.get_height() - 30))
                        
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
        
        shuffle(walkable_cells)

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
        info("Entering Chapter 3: Corruption Sector (Air Core)...")
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
        
        # Setup glyph puzzles
        self._setup_glyph_chambers()
        
        # Place Air Core in a sealed chamber
        core_pos = self._find_air_core_chamber()
        self.air_core = ElementalCore(
            core_pos[0], core_pos[1],
            ElementalCore.AIR,
            self.game.asset_manager
        )
        
        # Spawn the corrupted logs for this chapter's objectives
        log_ids = ["log_alpha", "log_beta"] 
        if hasattr(self.game, 'item_manager'):
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
             warning("Entered CorruptedSectorState but not on Chapter 3 in story.")
             
    def update(self, delta_time):
        """Update game logic for the corrupted sector."""
        current_time_ms = get_ticks()

        if not self.game.player:
            self.game.state_manager.set_state("MainMenuState")
            return
            
        # Update Air Core
        if self.air_core and not self.core_collected:
            self.air_core.update(delta_time)
            
            # Check for core collection
            if self.game.player.rect.colliderect(self.air_core.rect):
                self._collect_air_core()
        
        # Update Air Core abilities
        self._update_air_abilities(current_time_ms)
        
        # Update particles
        self.particles.update(delta_time)
        
        # Update glyph puzzles
        self._update_glyph_puzzles(current_time_ms)
        
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
        
        # Check for chapter completion
        if self.objectives_completed >= self.total_objectives and self.core_collected and not self.chapter_complete:
            self._complete_chapter()
        
        # Check if all objectives for Chapter 3 are complete
        if hasattr(self.game, 'story_manager'):
            current_chapter = self.game.story_manager.get_current_chapter()
            if current_chapter and current_chapter.chapter_id == "chapter_3" and current_chapter.is_complete():
                if hasattr(self.game.story_manager, 'advance_chapter'):
                    self.game.story_manager.advance_chapter()
                self.game.state_manager.set_state("StoryMapState")
                info("Chapter 3 Complete! Transitioning...")

        if not self.game.player.alive:
            self.game._handle_player_death_or_life_loss()
        
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
        
    def handle_events(self, events):
        """Handle player input."""
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    self.game.toggle_pause()
                elif event.key == K_ESCAPE:
                    # Return to story map
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                elif event.key == K_l and self.core_collected:
                    # Activate logic shift ability
                    self._activate_logic_shift()
                elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                    # Glyph sequence input
                    glyph_num = event.key - pygame.K_1 + 1
                    self._input_glyph_sequence(glyph_num)
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
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
        
        # Draw Air Core
        if self.air_core and not self.core_collected:
            camera_offset = getattr(self.game, 'camera', (0, 0))
            self.air_core.draw(surface, camera_offset)
        
        # Draw glyph chambers
        camera_offset = getattr(self.game, 'camera', (0, 0))
        self._draw_glyph_chambers(surface, camera_offset)
        
        # Draw enhanced sensor range if active
        if self.enhanced_sensors_active:
            self._draw_sensor_range(surface, camera_offset)
        
        # Draw particles
        self.particles.draw(surface, camera_offset)
        
        # Draw the main UI hud
        if self.game.player and hasattr(self.game.player, 'active_abilities'):
            self.game.ui_manager.draw_gameplay_hud(self.game.player.active_abilities)
        else:
            self.game.ui_manager.draw_gameplay_hud()
        
        # Draw Air Core UI
        self._draw_air_core_ui(surface)
