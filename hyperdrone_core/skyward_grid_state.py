# hyperdrone_core/skyward_grid_state.py
from pygame import KEYDOWN, KEYUP, K_p, K_ESCAPE, K_SPACE, K_UP, K_w, K_DOWN, K_s, Rect, Surface
from pygame.sprite import Group, Sprite
from pygame.time import get_ticks
from pygame.font import Font
from pygame.draw import circle, line
from logging import getLogger
from .state import State
from entities.player import PlayerDrone
from entities.enemy import Enemy
from entities.particle import ParticleSystem
from settings_manager import get_setting
from constants import GAME_STATE_STORY_MAP
from random import uniform, choice, randint, random
from math import sqrt, sin

logger = getLogger(__name__)

class SkywardGridState(State):
    def __init__(self, game_controller):
        super().__init__(game_controller)
        self.player = None
        self.enemies = Group()
        self.enemy_projectiles = Group()
        self.particles = ParticleSystem()
        
        # Scrolling and level
        self.scroll_speed = 2
        self.background_x = 0
        self.level_length = 5000
        self.distance_traveled = 0
        
        # Enemy spawning
        self.spawn_timer = 0
        self.spawn_interval = 2000
        self.enemy_types = ["gorgon_drone", "interceptor", "mine"]
        
        # Boss
        self.boss = None
        self.boss_spawned = False
        self.boss_spawn_distance = 4000
        
        # State
        self.chapter_complete = False
        self.start_time = 0
        
        # Effects
        self.lightning_timer = 0
        self.storm_intensity = 0.5
        self.grid_lines = []
        self.grid_pulse_timer = 0
        
        # UI
        self.font = Font(None, 36)
        self.small_font = Font(None, 24)
        self.difficulty_multiplier = 1.0
        
    def get_state_id(self):
        return "SkywardGridState"
    
    def enter(self, previous_state=None, **kwargs):
        logger.info("Entering Bonus Chapter: The Skyward Grid")
        
        self.start_time = get_ticks()
        
        # Initialize player
        screen_height = get_setting("display", "HEIGHT", 1080)
        self.player = PlayerDrone(
            100, screen_height // 2,
            self.game.asset_manager,
            self.game.drone_system.get_current_drone_config()
        )
        self.player.horizontal_only = True
        
        # Setup effects
        self._setup_orbital_grid()
        self.storm_intensity = uniform(0.3, 0.8)
    
    def exit(self, next_state=None):
        if self.chapter_complete and hasattr(self.game, 'story_manager'):
            self.game.story_manager.unlock_true_ending_intel()
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                key = event.key
                if key == K_p:
                    self.game.paused = not self.game.paused
                elif key == K_ESCAPE:
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                elif key == K_SPACE:
                    self.player.shoot()
                elif key in [K_UP, K_w]:
                    self.player.thrust_up = True
                elif key in [K_DOWN, K_s]:
                    self.player.thrust_down = True
            elif event.type == KEYUP:
                key = event.key
                if key in [K_UP, K_w]:
                    self.player.thrust_up = False
                elif key in [K_DOWN, K_s]:
                    self.player.thrust_down = False
    
    def update(self, delta_time):
        if self.game.paused:
            return
            
        current_time = get_ticks()
        
        # Update scrolling and difficulty
        self.distance_traveled += self.scroll_speed
        self.background_x -= self.scroll_speed
        self.difficulty_multiplier = 1.0 + (self.distance_traveled / 1000) * 0.2
        
        # Update entities
        self._update_player(delta_time)
        self._update_enemies(current_time, delta_time)
        self._update_projectiles()
        self.particles.update(delta_time)
        
        # Spawn enemies
        if current_time > self.spawn_timer and self.distance_traveled < self.level_length:
            self._spawn_enemy()
            self.spawn_timer = current_time + max(500, int(self.spawn_interval / self.difficulty_multiplier))
        
        # Update effects
        self._update_effects(current_time)
        
        # Boss logic
        if self.distance_traveled >= self.boss_spawn_distance and not self.boss_spawned:
            self._spawn_boss()
        
        if self.boss:
            self.boss.update(None, current_time, delta_time)
            if not self.boss.alive:
                self._handle_boss_defeated()
        
        # Handle collisions and completion
        self._handle_collisions()
        
        if (self.distance_traveled >= self.level_length and 
            len(self.enemies) == 0 and (not self.boss or not self.boss.alive)):
            self._complete_chapter()
    
    def draw(self, surface):
        # Draw background and effects
        self._draw_background(surface)
        self._draw_grid(surface)
        self._draw_storm_effects(surface)
        
        # Draw entities
        for enemy in self.enemies:
            enemy.draw(surface, (0, 0))
        
        for projectile in self.enemy_projectiles:
            circle(surface, (255, 100, 100), projectile.rect.center, 4)
        
        if self.boss:
            self.boss.draw(surface, (0, 0))
        
        self.player.draw(surface, (0, 0))
        self.particles.draw(surface, (0, 0))
        
        # Draw UI
        self._draw_ui(surface)
    
    def _setup_orbital_grid(self):
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        grid_spacing = 100
        
        # Create grid lines
        for x in range(0, screen_width + grid_spacing, grid_spacing):
            self.grid_lines.append({'type': 'vertical', 'pos': x, 'alpha': randint(50, 150)})
        
        for y in range(0, screen_height + grid_spacing, grid_spacing):
            self.grid_lines.append({'type': 'horizontal', 'pos': y, 'alpha': randint(50, 150)})
    
    def _update_player(self, delta_time):
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        # Vertical movement
        if hasattr(self.player, 'thrust_up') and self.player.thrust_up:
            self.player.rect.y -= int(self.player.speed * delta_time / 16)
        if hasattr(self.player, 'thrust_down') and self.player.thrust_down:
            self.player.rect.y += int(self.player.speed * delta_time / 16)
        
        # Keep on screen
        self.player.rect.y = max(0, min(screen_height - self.player.rect.height, self.player.rect.y))
        
        # Update bullets
        if hasattr(self.player, 'bullets_group'):
            for bullet in list(self.player.bullets_group):
                bullet.rect.x += 8
                if bullet.rect.left > get_setting("display", "WIDTH", 1920):
                    bullet.kill()
    
    def _update_enemies(self, current_time, delta_time):
        for enemy in list(self.enemies):
            enemy.update(None, current_time, delta_time)
            if enemy.rect.right < -100:
                enemy.kill()
    
    def _update_projectiles(self):
        for projectile in list(self.enemy_projectiles):
            projectile.rect.x -= self.scroll_speed + 3
            if projectile.rect.right < -50:
                projectile.kill()
    
    def _update_effects(self, current_time):
        # Lightning
        if current_time > self.lightning_timer:
            self.lightning_timer = current_time + randint(2000, 5000)
            self._create_lightning()
        
        # Storm intensity
        self.storm_intensity += uniform(-0.1, 0.1)
        self.storm_intensity = max(0.2, min(1.0, self.storm_intensity))
        
        # Grid pulse
        self.grid_pulse_timer += 16
        for line in self.grid_lines:
            pulse = sin(self.grid_pulse_timer * 0.01 + line['pos'] * 0.1)
            line['alpha'] = int(100 + 50 * pulse)
    
    def _spawn_enemy(self):
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        enemy_type = choice(self.enemy_types)
        x = screen_width + 50
        y = randint(50, screen_height - 50)
        
        enemy = Enemy(x, y, self.game.asset_manager)
        
        # Configure by type
        configs = {
            "gorgon_drone": {"health": 30, "speed": 2, "ai": "straight_line"},
            "interceptor": {"health": 50, "speed": 3, "ai": "sine_wave"},
            "mine": {"health": 15, "speed": 1, "ai": "homing"}
        }
        
        config = configs[enemy_type]
        enemy.health = int(config["health"] * self.difficulty_multiplier)
        enemy.speed = config["speed"] + self.difficulty_multiplier * 0.5
        enemy.ai_type = config["ai"]
        enemy.horizontal_velocity = -enemy.speed
        
        if enemy_type == "mine":
            enemy.target = self.player.rect.center
        
        self.enemies.add(enemy)
        
        # Random shooting
        if random() < 0.3:
            self._enemy_shoot(enemy)
    
    def _enemy_shoot(self, enemy):
        dx = self.player.rect.centerx - enemy.rect.centerx
        dy = self.player.rect.centery - enemy.rect.centery
        distance = sqrt(dx*dx + dy*dy)
        
        if distance > 0:
            dx /= distance
            dy /= distance
            
            projectile = Sprite()
            projectile.rect = Rect(enemy.rect.centerx, enemy.rect.centery, 8, 8)
            projectile.velocity_x = dx * 5
            projectile.velocity_y = dy * 5
            projectile.damage = 20
            
            self.enemy_projectiles.add(projectile)
    
    def _spawn_boss(self):
        self.boss_spawned = True
        
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        boss_x = screen_width + 100
        boss_y = screen_height // 2
        
        self.boss = Enemy(boss_x, boss_y, self.game.asset_manager)
        self.boss.health = 500
        self.boss.max_health = 500
        self.boss.speed = 1.5
        self.boss.damage = 40
        self.boss.ai_type = "fortress"
        self.boss.rect.width = 120
        self.boss.rect.height = 80
        
        # Effects
        self.particles.create_explosion(boss_x, boss_y, (255, 255, 0), particle_count=60)
        self.game.asset_manager.play_sound("boss_intro")
        
        logger.info("Sky Fortress boss appeared!")
    
    def _create_lightning(self):
        screen_width = get_setting("display", "WIDTH", 1920)
        x = randint(0, screen_width)
        
        self.particles.create_explosion(x, 0, (255, 255, 255), particle_count=20)
        self.game.asset_manager.play_sound("laser_charge")
    
    def _handle_collisions(self):
        # Player bullets vs enemies/boss
        if hasattr(self.player, 'bullets_group'):
            for bullet in list(self.player.bullets_group):
                # vs enemies
                for enemy in list(self.enemies):
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.health -= getattr(bullet, 'damage', 25)
                        bullet.kill()
                        self.particles.create_explosion(enemy.rect.centerx, enemy.rect.centery, (255, 100, 0), particle_count=10)
                        
                        if enemy.health <= 0:
                            enemy.kill()
                            if hasattr(self.game, 'score'):
                                self.game.score += 100
                
                # vs boss
                if self.boss and bullet.rect.colliderect(self.boss.rect):
                    self.boss.health -= getattr(bullet, 'damage', 25)
                    bullet.kill()
                    self.particles.create_explosion(self.boss.rect.centerx, self.boss.rect.centery, (255, 0, 0), particle_count=15)
        
        # Enemy projectiles vs player
        for projectile in list(self.enemy_projectiles):
            if projectile.rect.colliderect(self.player.rect):
                self.player.health -= getattr(projectile, 'damage', 20)
                projectile.kill()
                self.particles.create_explosion(self.player.rect.centerx, self.player.rect.centery, (255, 255, 0), particle_count=8)
                
                if self.player.health <= 0:
                    self._handle_player_defeated()
        
        # Enemy collision damage
        for enemy in list(self.enemies):
            if enemy.rect.colliderect(self.player.rect):
                self.player.health -= 30
                enemy.health -= 50
                
                center_x = (enemy.rect.centerx + self.player.rect.centerx) // 2
                center_y = (enemy.rect.centery + self.player.rect.centery) // 2
                self.particles.create_explosion(center_x, center_y, (255, 255, 255), particle_count=20)
                
                enemy.kill()
                
                if self.player.health <= 0:
                    self._handle_player_defeated()
    
    def _handle_boss_defeated(self):
        self.particles.create_explosion(self.boss.rect.centerx, self.boss.rect.centery, (255, 215, 0), particle_count=100)
        self.game.asset_manager.play_sound("boss_death")
        
        if hasattr(self.game, 'score'):
            self.game.score += 1000
        
        logger.info("Sky Fortress boss defeated!")
    
    def _handle_player_defeated(self):
        self.particles.create_explosion(self.player.rect.centerx, self.player.rect.centery, (255, 0, 0), particle_count=50)
        self.game.asset_manager.play_sound("player_death")
        self.game.state_manager.set_state("GameOverState")
    
    def _complete_chapter(self):
        self.chapter_complete = True
        self.game.set_story_message("Skyward Grid Complete! Crucial intel obtained for the true ending.", 4000)
        self.game.state_manager.set_state(GAME_STATE_STORY_MAP, chapter_completed=True, completed_chapter="Bonus: The Skyward Grid")
    
    def _draw_background(self, surface):
        # Stormy sky
        surface.fill((20, 20, 40))
        
        cloud_alpha = int(100 * self.storm_intensity)
        cloud_surface = Surface(surface.get_size())
        cloud_surface.set_alpha(cloud_alpha)
        cloud_surface.fill((40, 40, 60))
        surface.blit(cloud_surface, (0, 0))
    
    def _draw_grid(self, surface):
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        for line_data in self.grid_lines:
            color = (0, 100, 200)
            
            if line_data['type'] == 'vertical':
                x = (line_data['pos'] + self.background_x) % (screen_width + 100)
                line(surface, color, (x, 0), (x, screen_height), 1)
            else:
                y = line_data['pos']
                line(surface, color, (0, y), (screen_width, y), 1)
    
    def _draw_storm_effects(self, surface):
        if self.storm_intensity > 0.5:
            for _ in range(int(20 * self.storm_intensity)):
                x = randint(0, surface.get_width())
                y = randint(0, surface.get_height())
                line(surface, (100, 100, 150), (x, y), (x - 2, y + 10), 1)
    
    def _draw_ui(self, surface):
        # Title
        title = self.font.render("Bonus: The Skyward Grid", True, (255, 215, 0))
        surface.blit(title, (10, 10))
        
        # Progress
        progress = min(100, (self.distance_traveled / self.level_length) * 100)
        progress_text = self.small_font.render(f"Progress: {progress:.1f}%", True, (255, 255, 255))
        surface.blit(progress_text, (10, 50))
        
        # Health
        health_text = self.small_font.render(f"Health: {self.player.health}/{self.player.max_health}", True, (255, 255, 255))
        surface.blit(health_text, (10, 80))
        
        # Boss health
        if self.boss and self.boss.alive:
            boss_text = self.small_font.render(f"Sky Fortress: {self.boss.health}/{self.boss.max_health}", True, (255, 100, 100))
            surface.blit(boss_text, (10, 110))
        
        # Controls
        controls = ["SPACE: Shoot", "UP/DOWN: Move", "ESC: Exit"]
        for i, control in enumerate(controls):
            control_surface = self.small_font.render(control, True, (200, 200, 200))
            surface.blit(control_surface, (surface.get_width() - 200, 10 + i * 25))
        
        # Storm indicator
        storm_text = self.small_font.render(f"Storm: {int(self.storm_intensity * 100)}%", True, (150, 150, 255))
        surface.blit(storm_text, (10, surface.get_height() - 30))