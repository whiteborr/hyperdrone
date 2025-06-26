# hyperdrone_core/boss_fight_state.py
from pygame.time import get_ticks
from pygame.font import Font
from pygame.sprite import spritecollide
from pygame import KEYDOWN, KEYUP, K_p, K_f
from random import randint, choice
from logging import getLogger, info
from .state import State
from settings_manager import get_setting
from entities import Maze, MazeGuardian, PlayerDrone
from entities.elemental_core import ElementalCore, CipherCore
from entities.particle import ParticleSystem
from drone_management import DRONE_DATA
from constants import GAME_STATE_STORY_MAP

logger = getLogger(__name__)

class BossFightState(State):
    """
    Chapter 2: The Guardian - Fire Core Boss Fight
    
    Manages the entire boss battle sequence against the Maze Guardian.
    Features Fire Core collection and purge abilities.
    """
    def enter(self, previous_state=None, **kwargs):
        """Initializes the boss arena, the player, and the Maze Guardian."""
        info("Entering Chapter 2: The Guardian (Fire Core Boss Fight)...")
        
        # Initialize Fire Core system
        self.fire_core = None
        self.cipher_core = CipherCore()
        self.core_collected = False
        self.chapter_complete = False
        self.particles = ParticleSystem()
        
        # Fire core abilities
        self.purge_cooldown = 0
        self.purge_duration = 5000  # 5 seconds
        self.weapon_boost_active = False
        self.weapon_boost_timer = 0
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
            # Set initial weapon based on owned weapons
            owned_weapons = self.game.drone_system.get_owned_weapons()
            if owned_weapons and 0 not in owned_weapons:
                owned_weapons = [0] + owned_weapons
            if owned_weapons:
                self.game.player.set_weapon_mode(owned_weapons[0])
        else:
            self.game.player.reset(player_spawn_pos[0], player_spawn_pos[1])
            # Ensure weapon sprite is updated after reset
            self.game.player._update_drone_sprite()
        
        # Set up combat controller for the boss fight
        self.game.combat_controller.set_active_entities(
            player=self.game.player,
            maze=self.game.maze
        )
        
        # Update UI manager to reflect current weapon
        if hasattr(self.game, 'ui_manager'):
            self.game.ui_manager.update_weapon_icon_surface(self.game.player.current_weapon_mode)
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
        
        # Place Fire Core in the arena (will appear after boss defeat)
        self._setup_fire_core()

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
            info(f"Starting wave {self.current_wave}/{self.total_waves} with {self.enemies_to_kill_in_wave} {self.current_enemy_type} enemies")
            self.game.set_story_message(f"Wave {self.current_wave}/{self.total_waves}: Defeat the guardian's minions!", 3000)
        else:
            self._spawn_boss()
    
    def _spawn_boss(self):
        """Spawn the Maze Guardian boss after all waves are cleared"""
        if not self.boss_spawned:
            info("All waves cleared! Spawning the Maze Guardian boss!")
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
            info(f"Spawned {enemy_type} {self.enemies_spawned_in_wave}/{self.enemies_to_kill_in_wave} for wave {self.current_wave}")
    
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
        
        # Update Fire Core abilities
        self._update_fire_abilities(current_time)
        
        # Update particles
        self.particles.update(delta_time)
        
        # Update Fire Core if not collected
        if self.fire_core and not self.core_collected:
            self.fire_core.update(delta_time)
            
            # Check for core collection
            if self.game.player.rect.colliderect(self.fire_core.rect):
                self._collect_fire_core()
        
        # Check if the boss has been defeated
        if self.game.combat_controller.boss_active and not self.game.combat_controller.maze_guardian.alive:
            if hasattr(self.game, 'story_manager'):
                self.game.story_manager.complete_objective_by_id("c2_defeat_guardian")
            
            # Create explosion effect for the boss
            if hasattr(self.game.combat_controller.maze_guardian, 'rect') and not hasattr(self, 'boss_explosion_created'):
                # Call the boss's own death explosion method which creates multiple explosions
                if hasattr(self.game.combat_controller.maze_guardian, '_create_death_explosion'):
                    self.game.combat_controller.maze_guardian._create_death_explosion()
                else:
                    # Fallback to simple explosion if method doesn't exist
                    boss_rect = self.game.combat_controller.maze_guardian.rect
                    if hasattr(self.game, '_create_explosion'):
                        self.game._create_explosion(boss_rect.centerx, boss_rect.centery, 40, 'boss_death')
                
                self.boss_explosion_created = True
                self.victory_time = current_time + 3000  # Show victory message for 3 seconds
                self.game.set_story_message("Maze Guardian defeated! The Fire Core has appeared!", 3000)
                
                # Spawn Fire Core at boss location
                if self.fire_core:
                    boss_pos = self.game.combat_controller.maze_guardian.rect.center
                    self.fire_core.rect.center = boss_pos
                    
                return
                
            # After showing the victory message and collecting core, advance chapter
            if hasattr(self, 'victory_time') and current_time > self.victory_time:
                if self.core_collected:
                    self.chapter_complete = True
                    # Trigger narrative transition with "Echo in the Code" story beat
                    self.game.state_manager.set_state(
                        GAME_STATE_STORY_MAP,
                        chapter_completed=True,
                        completed_chapter="Chapter 2: The Guardian"
                    )
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
                elif event.key == K_f and self.core_collected:
                    # Activate Fire Core purge ability
                    self._activate_purge_ability()
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
        
        # Draw Fire Core if available
        if self.fire_core and not self.core_collected:
            camera_offset = getattr(self.game, 'camera', (0, 0))
            self.fire_core.draw(surface, camera_offset)
        
        # Draw particles
        camera_offset = getattr(self.game, 'camera', (0, 0))
        self.particles.draw(surface, camera_offset)
        
        # Draw Fire Core UI
        self._draw_fire_core_ui(surface)
    
    def _setup_fire_core(self):
        """Setup the Fire Core that appears after boss defeat"""
        # Initially place off-screen, will be moved to boss location on defeat
        self.fire_core = ElementalCore(
            -100, -100,  # Off-screen initially
            ElementalCore.FIRE,
            self.game.asset_manager
        )
    
    def _collect_fire_core(self):
        """Handle Fire Core collection"""
        if self.fire_core.collect():
            self.core_collected = True
            
            # Insert into Cipher Core
            self.cipher_core.insert_core(ElementalCore.FIRE, self.fire_core)
            
            # Play collection sound
            self.game.asset_manager.play_sound("collect_fragment")
            
            # Create fire particle effect
            self.particles.create_explosion(
                self.fire_core.rect.centerx,
                self.fire_core.rect.centery,
                (255, 69, 0),  # Fire orange color
                particle_count=25
            )
            
            # Activate weapon boost
            self.weapon_boost_active = True
            self.weapon_boost_timer = get_ticks() + 30000  # 30 seconds
            
            # Show message
            self.game.set_story_message("Fire Core collected! Purge abilities unlocked! Press F to purge corruption.", 4000)
            logger.info("Fire Core collected! Purge and weapon boost abilities unlocked.")
    
    def _activate_purge_ability(self):
        """Activate Fire Core purge ability to clear corruption"""
        current_time = get_ticks()
        
        if current_time < self.purge_cooldown:
            return  # Still on cooldown
        
        if not self.cipher_core.has_ability("purge_corruption"):
            return  # Don't have the ability
        
        # Set cooldown
        self.purge_cooldown = current_time + 15000  # 15 second cooldown
        
        # Create purge effect around player
        player_pos = self.game.player.rect.center
        purge_radius = 200
        
        # Damage all enemies in range
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if self.game.combat_controller.boss_active and self.game.combat_controller.maze_guardian:
            enemy_sprites.add(self.game.combat_controller.maze_guardian)
        
        purged_count = 0
        for enemy in enemy_sprites:
            if hasattr(enemy, 'rect'):
                distance = ((enemy.rect.centerx - player_pos[0])**2 + (enemy.rect.centery - player_pos[1])**2)**0.5
                if distance <= purge_radius:
                    # Apply purge damage
                    purge_damage = 50
                    if hasattr(enemy, 'take_damage'):
                        enemy.take_damage(purge_damage)
                    purged_count += 1
                    
                    # Create purge effect on enemy
                    self.particles.create_explosion(
                        enemy.rect.centerx,
                        enemy.rect.centery,
                        (255, 100, 0),  # Orange fire
                        particle_count=15
                    )
        
        # Create main purge effect
        self.particles.create_explosion(
            player_pos[0], player_pos[1],
            (255, 69, 0),  # Fire color
            particle_count=40
        )
        
        # Play purge sound
        self.game.asset_manager.play_sound("laser_fire")
        
        logger.info(f"Purge ability activated! Affected {purged_count} enemies.")
    
    def _update_fire_abilities(self, current_time):
        """Update Fire Core abilities"""
        # Update weapon boost
        if self.weapon_boost_active and current_time > self.weapon_boost_timer:
            self.weapon_boost_active = False
            logger.info("Fire Core weapon boost expired")
        
        # Apply weapon boost effect
        if self.weapon_boost_active and hasattr(self.game.player, 'damage_multiplier'):
            self.game.player.damage_multiplier = 1.5  # 50% damage boost
        elif hasattr(self.game.player, 'damage_multiplier'):
            self.game.player.damage_multiplier = 1.0  # Normal damage
    
    def _draw_fire_core_ui(self, surface):
        """Draw Fire Core specific UI elements"""
        font = Font(None, 24)
        
        # Chapter title
        title_font = Font(None, 36)
        title_text = title_font.render("Chapter 2: The Guardian", True, (255, 215, 0))
        surface.blit(title_text, (10, 10))
        
        # Fire Core status
        if self.core_collected:
            status_text = "Fire Core: Collected"
            color = (255, 69, 0)  # Fire orange
        else:
            status_text = "Fire Core: Not Found"
            color = (128, 128, 128)  # Gray
        
        status_surface = font.render(status_text, True, color)
        surface.blit(status_surface, (10, surface.get_height() - 80))
        
        # Abilities status
        if self.core_collected:
            # Purge cooldown
            current_time = get_ticks()
            if current_time < self.purge_cooldown:
                cooldown_left = (self.purge_cooldown - current_time) // 1000
                purge_text = f"Purge: {cooldown_left}s cooldown"
                color = (255, 100, 100)
            else:
                purge_text = "Purge: Ready (Press F)"
                color = (100, 255, 100)
            
            purge_surface = font.render(purge_text, True, color)
            surface.blit(purge_surface, (10, surface.get_height() - 50))
            
            # Weapon boost status
            if self.weapon_boost_active:
                boost_left = (self.weapon_boost_timer - current_time) // 1000
                boost_text = f"Weapon Boost: {boost_left}s remaining"
                boost_color = (255, 215, 0)  # Gold
            else:
                boost_text = "Weapon Boost: Inactive"
                boost_color = (128, 128, 128)
            
            boost_surface = font.render(boost_text, True, boost_color)
            surface.blit(boost_surface, (10, surface.get_height() - 20))
