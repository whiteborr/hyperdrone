# hyperdrone_core/boss_fight_state.py
from pygame.time import get_ticks
from pygame.font import Font
from pygame.sprite import spritecollide
from pygame import KEYDOWN, KEYUP, K_p
from random import randint, choice
import logging
from .state import State
from settings_manager import get_setting
from entities import Maze, MazeGuardian, PlayerDrone
from drone_management import DRONE_DATA

logger = logging.getLogger(__name__)

class BossFightState(State):
    """
    Manages the entire boss battle sequence against the Maze Guardian.
    This state sets up a special arena and controls the win/loss conditions
    for the boss fight.
    """
    def enter(self, previous_state=None, **kwargs):
        """Initializes the boss arena, the player, and the Maze Guardian."""
        logger.info("Entering BossFightState...")
        # Create a specific arena for the boss fight (more open layout)
        self.game.maze = Maze(maze_type="boss_arena")

        # Get a safe spawn position for the player
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        player_spawn_pos = self.game._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
        
        # We need to re-initialize the player or reset its position
        if not self.game.player:
            drone_id = self.game.drone_system.get_selected_drone_id()
            drone_stats = self.game.drone_system.get_drone_stats(drone_id)
            drone_config = DRONE_DATA.get(drone_id, {})
            sprite_key = "drone_default"  # Default fallback sprite key
            if "ingame_sprite_path" in drone_config:
                # Extract just the filename without the assets/ prefix
                sprite_path = drone_config["ingame_sprite_path"]
                if sprite_path.startswith("assets/"):
                    sprite_path = sprite_path[7:]  # Remove "assets/" prefix
                sprite_key = sprite_path
            self.game.player = PlayerDrone(
                player_spawn_pos[0], player_spawn_pos[1], drone_id, drone_stats,
                self.game.asset_manager, sprite_key, 'crash', self.game.drone_system
            )
        else:
            self.game.player.reset(player_spawn_pos[0], player_spawn_pos[1])
        
        # Set up combat controller for the boss fight
        self.game.combat_controller.set_active_entities(
            player=self.game.player,
            maze=self.game.maze
        )
        # Ensure enemy group is clear before boss minions are spawned
        self.game.combat_controller.enemy_manager.reset_all()
        
        # Initialize boss fight wave system
        self.current_wave = 0
        self.total_waves = 3  # 3 waves of enemies before boss
        # Define wave structure: [count, enemy_type]
        self.wave_definitions = [
            [5, "prototype_enemy"],
            [7, "sentinel"],
            [10, "prototype_enemy"]
        ]
        self.enemies_spawned_in_wave = 0
        self.enemies_to_kill_in_wave = 0
        self.wave_start_time = get_ticks()
        self.spawn_delay = 1000  # ms between enemy spawns
        self.last_spawn_time = 0
        self.boss_spawned = False
        
        # Start the first wave
        self._start_next_wave()
        
        # Message to player
        self.game.set_story_message(f"Wave 1/{self.total_waves}: Defeat the guardian's minions!", 3000)

    def _start_next_wave(self):
        """Start the next wave of enemies"""
        self.current_wave += 1
        if self.current_wave <= self.total_waves:
            wave_def = self.wave_definitions[self.current_wave - 1]
            self.enemies_to_kill_in_wave = wave_def[0]  # Count
            self.current_enemy_type = wave_def[1]  # Enemy type
            self.enemies_spawned_in_wave = 0
            self.wave_start_time = get_ticks()
            self.last_spawn_time = 0
            logger.info(f"Starting wave {self.current_wave}/{self.total_waves} with {self.enemies_to_kill_in_wave} {self.current_enemy_type} enemies")
            self.game.set_story_message(f"Wave {self.current_wave}/{self.total_waves}: Defeat the guardian's minions!", 3000)
        else:
            self._spawn_boss()
    
    def _spawn_boss(self):
        """Spawn the Maze Guardian boss after all waves are cleared"""
        if not self.boss_spawned:
            logger.info("All waves cleared! Spawning the Maze Guardian boss!")
            self.game.set_story_message("The Maze Guardian has appeared!", 5000)
            
            # Spawn the Maze Guardian
            boss_spawn_pos = (get_setting("display", "WIDTH", 1920) - 300, get_setting("display", "HEIGHT", 1080) / 2)
            self.game.combat_controller.maze_guardian = MazeGuardian(
                boss_spawn_pos[0], boss_spawn_pos[1],
                self.game.player,
                self.game.maze,
                self.game.combat_controller,
                self.game.asset_manager
            )
            self.game.combat_controller.boss_active = True
            self.game.combat_controller.enemy_manager.enemies.add(self.game.combat_controller.maze_guardian)
            self.boss_spawned = True
    
    def _spawn_wave_enemy(self):
        """Spawn a single enemy for the current wave"""
        if self.enemies_spawned_in_wave < self.enemies_to_kill_in_wave:
            # Get walkable tiles from the maze
            walkable_tiles = []
            if self.game.maze and hasattr(self.game.maze, 'get_walkable_tiles_abs'):
                walkable_tiles = self.game.maze.get_walkable_tiles_abs()
            
            if not walkable_tiles:
                # Fallback if no walkable tiles
                width = get_setting("display", "WIDTH", 1920)
                height = get_setting("display", "HEIGHT", 1080)
                game_area_x_offset = self.game.maze.game_area_x_offset if self.game.maze else 0
                x = randint(game_area_x_offset + 100, width - 100)
                y = randint(50, height - 50)
            else:
                # Find perimeter tiles (tiles near the edge of the maze)
                width = get_setting("display", "WIDTH", 1920)
                height = get_setting("display", "HEIGHT", 1080)
                game_area_x_offset = self.game.maze.game_area_x_offset if self.game.maze else 0
                
                # Define the perimeter zone (tiles within 2 tiles of the edge)
                perimeter_margin = self.game.maze.tile_size * 2
                perimeter_tiles = []
                
                for tile in walkable_tiles:
                    tx, ty = tile
                    # Check if tile is near any edge of the screen
                    if (tx < game_area_x_offset + perimeter_margin or 
                        tx > width - perimeter_margin or 
                        ty < perimeter_margin or 
                        ty > height - perimeter_margin):
                        perimeter_tiles.append(tile)
                
                # If no perimeter tiles found, use any walkable tile
                if not perimeter_tiles:
                    perimeter_tiles = walkable_tiles
                
                # Choose a random perimeter tile
                x, y = choice(perimeter_tiles)
            
            # Use the enemy type defined for the current wave
            enemy_type = self.current_enemy_type
            
            self.game.combat_controller.enemy_manager.spawn_enemy_by_id(enemy_type, x, y)
            self.enemies_spawned_in_wave += 1
            logger.info(f"Spawned {enemy_type} {self.enemies_spawned_in_wave}/{self.enemies_to_kill_in_wave} for wave {self.current_wave}")
    
    def update(self, delta_time):
        """Update all entities and check for the end of the fight."""
        current_time = get_ticks()

        # If player doesn't exist, something is wrong, exit to prevent crash.
        if not self.game.player:
            self.game.state_manager.set_state("MainMenuState")
            return
            
        self.game.player.update(current_time, self.game.maze, self.game.combat_controller.enemy_manager.get_sprites(), self.game.player_actions, self.game.maze.game_area_x_offset if self.game.maze else 0)
        self.game.combat_controller.update(current_time, delta_time)
        
        # Update player actions (rotation, shooting)
        self.game.player_actions.update_player_movement_and_actions(current_time)
        
        # Handle bullet-enemy collisions
        self._handle_bullet_enemy_collisions()
        
        # Handle wave system
        if not self.boss_spawned:
            # Check if we need to spawn more enemies for the current wave
            if self.enemies_spawned_in_wave < self.enemies_to_kill_in_wave:
                if current_time - self.last_spawn_time > self.spawn_delay:
                    self._spawn_wave_enemy()
                    self.last_spawn_time = current_time
            
            # Check if the current wave is cleared
            active_enemies = len(self.game.combat_controller.enemy_manager.get_sprites())
            if self.enemies_spawned_in_wave >= self.enemies_to_kill_in_wave and active_enemies == 0:
                # Wave cleared, start the next one
                self._start_next_wave()
        
        # Check if the boss has been defeated
        if self.game.combat_controller.boss_active and not self.game.combat_controller.maze_guardian.alive:
            self.game.story_manager.complete_objective_by_id("c2_defeat_guardian")
            
            # Create explosion effect for the boss
            if hasattr(self.game.combat_controller.maze_guardian, 'rect') and not hasattr(self, 'boss_explosion_created'):
                # Call the boss's own death explosion method which creates multiple explosions
                if hasattr(self.game.combat_controller.maze_guardian, '_create_death_explosion'):
                    self.game.combat_controller.maze_guardian._create_death_explosion()
                else:
                    # Fallback to simple explosion if method doesn't exist
                    boss_rect = self.game.combat_controller.maze_guardian.rect
                    self.game._create_explosion(boss_rect.centerx, boss_rect.centery, 40, 'boss_death')
                
                self.boss_explosion_created = True
                self.victory_time = current_time + 3000  # Show victory message for 3 seconds
                self.game.set_story_message("Congratulations! Maze Guardian defeated!", 3000)
                return
                
            # After showing the victory message, advance to Chapter 3 and go to the story map
            if hasattr(self, 'victory_time') and current_time > self.victory_time:
                self.game.story_manager.advance_chapter()
                self.game.state_manager.set_state("StoryMapState")
                return

        # Check if the player has been defeated
        if not self.game.player.alive:
            self.game._handle_player_death_or_life_loss()
            
    def _handle_bullet_enemy_collisions(self):
        """Handle collisions between player bullets/missiles/lightning and enemies"""
        if not self.game.player or not hasattr(self.game.player, 'bullets_group'):
            return
            
        # Get enemy sprites and add the boss if active
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if self.game.combat_controller.boss_active and self.game.combat_controller.maze_guardian:
            enemy_sprites.add(self.game.combat_controller.maze_guardian)
            
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
                        
        # Check missile collisions with enemies
        if hasattr(self.game.player, 'missiles_group'):
            for missile in self.game.player.missiles_group:
                for enemy in spritecollide(missile, enemy_sprites, False):
                    if enemy.alive and missile.alive:
                        enemy.take_damage(missile.damage)
                        # Create larger explosion for missile hits
                        if hasattr(enemy, 'rect') and enemy.rect:
                            self.game._create_explosion(enemy.rect.centerx, enemy.rect.centery, 10, 'missile_launch')
                        missile.alive = False
                        missile.kill()
                        missile.kill()

    def handle_events(self, events):
        """Handle player input during the boss fight."""
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    self.game.toggle_pause()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
                self.game.player_actions.handle_key_up(event)

    def draw(self, surface):
        """Render the boss fight scene."""
        surface.fill(get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30)))
        
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        if self.game.player:
            self.game.player.draw(surface)
            
        if self.game.combat_controller.boss_active:
            self.game.combat_controller.maze_guardian.draw(surface)
            
        self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        self.game.ui_manager.draw_gameplay_hud()
        
        # Draw wave information
        if not self.boss_spawned:
            font = Font(None, 36)
            wave_text = f"Wave {self.current_wave}/{self.total_waves}"
            enemies_text = f"Enemies: {self.enemies_to_kill_in_wave - len(self.game.combat_controller.enemy_manager.get_sprites())}/{self.enemies_to_kill_in_wave}"
            
            wave_surface = font.render(wave_text, True, (255, 255, 255))
            enemies_surface = font.render(enemies_text, True, (255, 255, 255))
            
            surface.blit(wave_surface, (50, 50))
            surface.blit(enemies_surface, (50, 90))
