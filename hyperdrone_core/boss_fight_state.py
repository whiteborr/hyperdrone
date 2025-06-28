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
    def enter(self, previous_state=None, **kwargs):
        info("Entering Chapter 2: The Guardian (Fire Core Boss Fight)...")
        
        # Initialize systems
        self.fire_core = None
        self.cipher_core = CipherCore()
        self.core_collected = False
        self.chapter_complete = False
        self.particles = ParticleSystem()
        
        # Fire core abilities
        self.purge_cooldown = 0
        self.weapon_boost_active = False
        self.weapon_boost_timer = 0
        
        # Create boss arena
        self.game.maze = Maze(maze_type="boss_arena")
        
        # Initialize player
        self._setup_player()
        
        # Setup combat
        self.game.combat_controller.set_active_entities(player=self.game.player, maze=self.game.maze)
        self.game.combat_controller.enemy_manager.reset_all()
        
        # Wave system
        self.current_wave = 0
        self.total_waves = 3
        self.wave_definitions = [[5, "prototype_enemy"], [7, "sentinel"], [10, "prototype_enemy"]]
        self.enemies_spawned_in_wave = 0
        self.enemies_to_kill_in_wave = 0
        self.spawn_delay = 1000
        self.last_spawn_time = 0
        self.boss_spawned = False
        
        # Start first wave
        self._start_next_wave()
        self.game.set_story_message(f"Wave 1/{self.total_waves}: Defeat the guardian's minions!", 3000)
        
        # Setup Fire Core
        self._setup_fire_core()

    def _setup_player(self):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        spawn_pos = self.game._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
        
        if not self.game.player:
            drone_id = self.game.drone_system.get_selected_drone_id()
            drone_stats = self.game.drone_system.get_drone_stats(drone_id)
            drone_config = DRONE_DATA.get(drone_id, {})
            
            sprite_key = "drone_default"
            if "ingame_sprite_path" in drone_config:
                sprite_path = drone_config["ingame_sprite_path"]
                if sprite_path.startswith("assets/"):
                    sprite_path = sprite_path[7:]
                sprite_key = sprite_path
                
            self.game.player = PlayerDrone(
                spawn_pos[0], spawn_pos[1], drone_id, drone_stats,
                self.game.asset_manager, sprite_key, 'crash', self.game.drone_system
            )
            
            # Set initial weapon
            owned_weapons = self.game.drone_system.get_owned_weapons()
            if owned_weapons and 0 not in owned_weapons:
                owned_weapons = [0] + owned_weapons
            if owned_weapons:
                self.game.player.set_weapon_mode(owned_weapons[0])
        else:
            self.game.player.reset(spawn_pos[0], spawn_pos[1])
            self.game.player._update_drone_sprite()
        
        # Update UI
        if hasattr(self.game, 'ui_manager'):
            self.game.ui_manager.update_weapon_icon_surface(self.game.player.current_weapon_mode)

    def _start_next_wave(self):
        self.current_wave += 1
        if self.current_wave <= self.total_waves:
            wave_def = self.wave_definitions[self.current_wave - 1]
            self.enemies_to_kill_in_wave = wave_def[0]
            self.current_enemy_type = wave_def[1]
            self.enemies_spawned_in_wave = 0
            self.last_spawn_time = 0
            info(f"Starting wave {self.current_wave}/{self.total_waves}")
            self.game.set_story_message(f"Wave {self.current_wave}/{self.total_waves}: Defeat the guardian's minions!", 3000)
        else:
            self._spawn_boss()
    
    def _spawn_boss(self):
        if not self.boss_spawned:
            info("Spawning Maze Guardian boss!")
            self.game.set_story_message("The Maze Guardian has appeared!", 5000)
            
            boss_spawn_pos = (get_setting("display", "WIDTH", 1920) - 300, get_setting("display", "HEIGHT", 1080) / 2)
            self.game.combat_controller.maze_guardian = MazeGuardian(
                boss_spawn_pos[0], boss_spawn_pos[1],
                self.game.player, self.game.maze,
                self.game.combat_controller, self.game.asset_manager
            )
            self.game.combat_controller.boss_active = True
            self.game.combat_controller.enemy_manager.enemies.add(self.game.combat_controller.maze_guardian)
            self.boss_spawned = True
    
    def _spawn_wave_enemy(self):
        if self.enemies_spawned_in_wave >= self.enemies_to_kill_in_wave:
            return
            
        # Get spawn position
        x, y = self._get_spawn_position()
        
        # Spawn enemy
        self.game.combat_controller.enemy_manager.spawn_enemy_by_id(self.current_enemy_type, x, y)
        self.enemies_spawned_in_wave += 1
    
    def _get_spawn_position(self):
        # Try to get walkable tiles
        walkable_tiles = []
        if self.game.maze and hasattr(self.game.maze, 'get_walkable_tiles_abs'):
            walkable_tiles = self.game.maze.get_walkable_tiles_abs()
        
        if not walkable_tiles:
            # Fallback random position
            width = get_setting("display", "WIDTH", 1920)
            height = get_setting("display", "HEIGHT", 1080)
            x_offset = self.game.maze.game_area_x_offset if self.game.maze else 0
            return randint(x_offset + 100, width - 100), randint(50, height - 50)
        
        # Find perimeter tiles
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        x_offset = self.game.maze.game_area_x_offset if self.game.maze else 0
        margin = self.game.maze.tile_size * 2
        
        perimeter_tiles = []
        for tx, ty in walkable_tiles:
            if (tx < x_offset + margin or tx > width - margin or 
                ty < margin or ty > height - margin):
                perimeter_tiles.append((tx, ty))
        
        return choice(perimeter_tiles if perimeter_tiles else walkable_tiles)
    
    def update(self, delta_time):
        current_time = get_ticks()

        if not self.game.player:
            self.game.state_manager.set_state("MainMenuState")
            return
            
        # Update entities
        self.game.player.update(current_time, self.game.maze, 
                               self.game.combat_controller.enemy_manager.get_sprites(), 
                               self.game.player_actions, 
                               self.game.maze.game_area_x_offset if self.game.maze else 0)
        self.game.combat_controller.update(current_time, delta_time)
        self.game.player_actions.update_player_movement_and_actions(current_time)
        
        # Handle collisions
        self._handle_bullet_enemy_collisions()
        
        # Handle wave system
        if not self.boss_spawned:
            if (self.enemies_spawned_in_wave < self.enemies_to_kill_in_wave and 
                current_time - self.last_spawn_time > self.spawn_delay):
                self._spawn_wave_enemy()
                self.last_spawn_time = current_time
            
            # Check wave completion
            active_enemies = len(self.game.combat_controller.enemy_manager.get_sprites())
            if (self.enemies_spawned_in_wave >= self.enemies_to_kill_in_wave and 
                active_enemies == 0):
                self._start_next_wave()
        
        # Update Fire Core systems
        self._update_fire_abilities(current_time)
        self.particles.update(delta_time)
        
        # Update Fire Core
        if self.fire_core and not self.core_collected:
            self.fire_core.update(delta_time)
            if self.game.player.rect.colliderect(self.fire_core.rect):
                self._collect_fire_core()
        
        # Check boss defeat
        if (self.game.combat_controller.boss_active and 
            not self.game.combat_controller.maze_guardian.alive):
            self._handle_boss_defeat(current_time)
        
        # Check player death
        if not self.game.player.alive:
            self.game._handle_player_death_or_life_loss()
    
    def _handle_boss_defeat(self, current_time):
        if hasattr(self.game, 'story_manager'):
            self.game.story_manager.complete_objective_by_id("c2_defeat_guardian")
        
        # Create explosion effect
        if not hasattr(self, 'boss_explosion_created'):
            if hasattr(self.game.combat_controller.maze_guardian, '_create_death_explosion'):
                self.game.combat_controller.maze_guardian._create_death_explosion()
            else:
                boss_rect = self.game.combat_controller.maze_guardian.rect
                if hasattr(self.game, '_create_explosion'):
                    self.game._create_explosion(boss_rect.centerx, boss_rect.centery, 40, 'boss_death')
            
            self.boss_explosion_created = True
            self.victory_time = current_time + 3000
            self.game.set_story_message("Maze Guardian defeated! The Fire Core has appeared!", 3000)
            
            # Move Fire Core to boss location
            if self.fire_core:
                self.fire_core.rect.center = self.game.combat_controller.maze_guardian.rect.center
            return
        
        # Check for chapter completion
        if (hasattr(self, 'victory_time') and current_time > self.victory_time and 
            self.core_collected):
            self.chapter_complete = True
            self.game.state_manager.set_state(
                GAME_STATE_STORY_MAP,
                chapter_completed=True,
                completed_chapter="Chapter 2: The Guardian"
            )
            
    def _handle_bullet_enemy_collisions(self):
        if not self.game.player or not hasattr(self.game.player, 'bullets_group'):
            return
            
        # Get enemy sprites
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if self.game.combat_controller.boss_active and self.game.combat_controller.maze_guardian:
            enemy_sprites.add(self.game.combat_controller.maze_guardian)
            
        if not enemy_sprites:
            return
            
        # Check bullet collisions
        for bullet in self.game.player.bullets_group:
            for enemy in spritecollide(bullet, enemy_sprites, False):
                if enemy.alive and bullet.alive:
                    enemy.take_damage(bullet.damage)
                    
                    # Handle piercing
                    if bullet.max_pierces > 0:
                        bullet.pierces_done += 1
                        if bullet.pierces_done > bullet.max_pierces:
                            bullet.alive = False
                            bullet.kill()
                    else:
                        bullet.alive = False
                        bullet.kill()
                        
        # Check missile collisions
        if hasattr(self.game.player, 'missiles_group'):
            for missile in self.game.player.missiles_group:
                for enemy in spritecollide(missile, enemy_sprites, False):
                    if enemy.alive and missile.alive:
                        enemy.take_damage(missile.damage)
                        if hasattr(enemy, 'rect') and enemy.rect:
                            self.game._create_explosion(enemy.rect.centerx, enemy.rect.centery, 10, 'missile_launch')
                        missile.alive = False
                        missile.kill()

    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    self.game.toggle_pause()
                elif event.key == K_f and self.core_collected:
                    self._activate_purge_ability()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
                self.game.player_actions.handle_key_up(event)

    def draw(self, surface):
        surface.fill(get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30)))
        
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        if self.game.player:
            self.game.player.draw(surface)
            
        if self.game.combat_controller.boss_active:
            self.game.combat_controller.maze_guardian.draw(surface)
            
        self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        self.game.ui_manager.draw_gameplay_hud()
        
        # Draw wave info
        if not self.boss_spawned:
            font = Font(None, 36)
            wave_text = f"Wave {self.current_wave}/{self.total_waves}"
            enemies_left = self.enemies_to_kill_in_wave - len(self.game.combat_controller.enemy_manager.get_sprites())
            enemies_text = f"Enemies: {enemies_left}/{self.enemies_to_kill_in_wave}"
            
            surface.blit(font.render(wave_text, True, (255, 255, 255)), (50, 50))
            surface.blit(font.render(enemies_text, True, (255, 255, 255)), (50, 90))
        
        # Draw Fire Core
        if self.fire_core and not self.core_collected:
            camera_offset = getattr(self.game, 'camera', (0, 0))
            self.fire_core.draw(surface, camera_offset)
        
        # Draw particles and UI
        camera_offset = getattr(self.game, 'camera', (0, 0))
        self.particles.draw(surface, camera_offset)
        self._draw_fire_core_ui(surface)
    
    def _setup_fire_core(self):
        self.fire_core = ElementalCore(-100, -100, ElementalCore.FIRE, self.game.asset_manager)
    
    def _collect_fire_core(self):
        if self.fire_core.collect():
            self.core_collected = True
            self.cipher_core.insert_core(ElementalCore.FIRE, self.fire_core)
            
            # Effects
            self.game.asset_manager.play_sound("collect_fragment")
            self.particles.create_explosion(
                self.fire_core.rect.centerx, self.fire_core.rect.centery,
                (255, 69, 0), particle_count=25
            )
            
            # Activate abilities
            self.weapon_boost_active = True
            self.weapon_boost_timer = get_ticks() + 30000
            
            self.game.set_story_message("Fire Core collected! Purge abilities unlocked! Press F to purge corruption.", 4000)
            logger.info("Fire Core collected!")
    
    def _activate_purge_ability(self):
        current_time = get_ticks()
        
        if current_time < self.purge_cooldown or not self.cipher_core.has_ability("purge_corruption"):
            return
        
        # Set cooldown
        self.purge_cooldown = current_time + 15000
        
        # Get targets in range
        player_pos = self.game.player.rect.center
        purge_radius = 200
        
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if self.game.combat_controller.boss_active and self.game.combat_controller.maze_guardian:
            enemy_sprites.add(self.game.combat_controller.maze_guardian)
        
        # Apply purge damage
        purged_count = 0
        for enemy in enemy_sprites:
            if hasattr(enemy, 'rect'):
                distance = ((enemy.rect.centerx - player_pos[0])**2 + (enemy.rect.centery - player_pos[1])**2)**0.5
                if distance <= purge_radius:
                    if hasattr(enemy, 'take_damage'):
                        enemy.take_damage(50)
                    purged_count += 1
                    
                    self.particles.create_explosion(
                        enemy.rect.centerx, enemy.rect.centery,
                        (255, 100, 0), particle_count=15
                    )
        
        # Create main effect
        self.particles.create_explosion(player_pos[0], player_pos[1], (255, 69, 0), particle_count=40)
        self.game.asset_manager.play_sound("laser_fire")
        
        logger.info(f"Purge activated! Affected {purged_count} enemies")
    
    def _update_fire_abilities(self, current_time):
        # Update weapon boost
        if self.weapon_boost_active and current_time > self.weapon_boost_timer:
            self.weapon_boost_active = False
        
        # Apply damage multiplier
        if hasattr(self.game.player, 'damage_multiplier'):
            self.game.player.damage_multiplier = 1.5 if self.weapon_boost_active else 1.0
    
    def _draw_fire_core_ui(self, surface):
        font = Font(None, 24)
        
        # Chapter title
        title_font = Font(None, 36)
        title = title_font.render("Chapter 2: The Guardian", True, (255, 215, 0))
        surface.blit(title, (10, 10))
        
        # Fire Core status
        if self.core_collected:
            status_text = "Fire Core: Collected"
            color = (255, 69, 0)
        else:
            status_text = "Fire Core: Not Found"
            color = (128, 128, 128)
        
        surface.blit(font.render(status_text, True, color), (10, surface.get_height() - 80))
        
        # Abilities
        if self.core_collected:
            current_time = get_ticks()
            
            # Purge status
            if current_time < self.purge_cooldown:
                cooldown_left = (self.purge_cooldown - current_time) // 1000
                purge_text = f"Purge: {cooldown_left}s cooldown"
                purge_color = (255, 100, 100)
            else:
                purge_text = "Purge: Ready (Press F)"
                purge_color = (100, 255, 100)
            
            surface.blit(font.render(purge_text, True, purge_color), (10, surface.get_height() - 50))
            
            # Weapon boost status
            if self.weapon_boost_active:
                boost_left = (self.weapon_boost_timer - current_time) // 1000
                boost_text = f"Weapon Boost: {boost_left}s remaining"
                boost_color = (255, 215, 0)
            else:
                boost_text = "Weapon Boost: Inactive"
                boost_color = (128, 128, 128)
            
            surface.blit(font.render(boost_text, True, boost_color), (10, surface.get_height() - 20))