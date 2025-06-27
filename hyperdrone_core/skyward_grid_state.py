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
    """
    Bonus Chapter: The Skyward Grid - Horizontal Scrolling SHMUP
    
    Features:
    - Horizontal scrolling shoot-em-up gameplay
    - CRUCIBLE Gorgon drones as enemies
    - Sky fortress boss encounter
    - Stormy sky environment with orbital grid
    - Reveals global stakes and outside world awareness
    """
    
    def __init__(self, game_controller):
        super().__init__(game_controller)
        self.player = None
        self.enemies = Group()
        self.enemy_projectiles = Group()
        self.particles = ParticleSystem()
        
        # Horizontal scrolling
        self.scroll_speed = 2
        self.background_x = 0
        self.level_length = 5000  # 5000 pixels long
        self.distance_traveled = 0
        
        # Enemy spawning
        self.spawn_timer = 0
        self.spawn_interval = 2000  # 2 seconds
        self.enemy_types = ["gorgon_drone", "interceptor", "mine"]
        
        # Boss system
        self.boss = None
        self.boss_spawned = False
        self.boss_spawn_distance = 4000  # Spawn boss at 80% completion
        
        # Chapter state
        self.chapter_complete = False
        self.completion_time = 0
        self.start_time = 0
        
        # Environmental effects
        self.lightning_timer = 0
        self.lightning_interval = 3000  # Lightning every 3 seconds
        self.storm_intensity = 0.5
        
        # Grid effects
        self.grid_lines = []
        self.grid_pulse_timer = 0
        
        # UI elements
        self.font = Font(None, 36)
        self.small_font = Font(None, 24)
        
        # Difficulty scaling
        self.difficulty_multiplier = 1.0
        
    def get_state_id(self):
        return "SkywardGridState"
    
    def enter(self, previous_state=None, **kwargs):
        """Initialize Bonus Chapter"""
        logger.info("Entering Bonus Chapter: The Skyward Grid")
        
        self.start_time = get_ticks()
        
        # Initialize player at left side of screen
        screen_height = get_setting("display", "HEIGHT", 1080)
        self.player = PlayerDrone(
            100, screen_height // 2,  # Left side, center vertically
            self.game.asset_manager,
            self.game.drone_system.get_current_drone_config()
        )
        
        # Lock player to horizontal movement only
        self.player.horizontal_only = True
        
        # Setup orbital grid
        self._setup_orbital_grid()
        
        # Set stormy atmosphere
        self.storm_intensity = uniform(0.3, 0.8)
        
        logger.info("Skyward Grid initialized successfully")
    
    def exit(self, next_state=None):
        """Clean up Bonus Chapter"""
        logger.info("Exiting Skyward Grid")
        
        if self.chapter_complete:
            # Unlock special intel for true ending
            if hasattr(self.game, 'story_manager'):
                self.game.story_manager.unlock_true_ending_intel()
    
    def handle_events(self, events):
        """Handle Bonus Chapter specific events"""
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    # Pause functionality
                    self.game.paused = not self.game.paused
                elif event.key == K_ESCAPE:
                    # Return to story map
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                elif event.key == K_SPACE:
                    # Player shooting
                    self.player.shoot()
                elif event.key in [K_UP, K_w]:
                    self.player.thrust_up = True
                elif event.key in [K_DOWN, K_s]:
                    self.player.thrust_down = True
            elif event.type == KEYUP:
                if event.key in [K_UP, K_w]:
                    self.player.thrust_up = False
                elif event.key in [K_DOWN, K_s]:
                    self.player.thrust_down = False
    
    def update(self, delta_time):
        """Update Bonus Chapter logic"""
        if self.game.paused:
            return
            
        current_time = get_ticks()
        
        # Update scrolling
        self.distance_traveled += self.scroll_speed
        self.background_x -= self.scroll_speed
        
        # Update difficulty
        self.difficulty_multiplier = 1.0 + (self.distance_traveled / 1000) * 0.2
        
        # Update player (vertical movement only)
        self._update_player_horizontal(delta_time)
        
        # Spawn enemies
        if current_time > self.spawn_timer and self.distance_traveled < self.level_length:
            self._spawn_enemy()
            self.spawn_timer = current_time + max(500, int(self.spawn_interval / self.difficulty_multiplier))
        
        # Update enemies
        for enemy in list(self.enemies):
            enemy.update(None, current_time, delta_time)  # No maze for horizontal SHMUP
            
            # Remove enemies that have moved off-screen
            if enemy.rect.right < -100:
                enemy.kill()
        
        # Update enemy projectiles
        for projectile in list(self.enemy_projectiles):
            projectile.rect.x -= self.scroll_speed + 3  # Move left faster than scroll
            if projectile.rect.right < -50:
                projectile.kill()
        
        # Update particles
        self.particles.update(delta_time)
        
        # Update environmental effects
        self._update_storm_effects(current_time)
        self._update_grid_effects(current_time)
        
        # Spawn boss
        if (self.distance_traveled >= self.boss_spawn_distance and 
            not self.boss_spawned):
            self._spawn_sky_fortress_boss()
        
        # Update boss
        if self.boss:
            self.boss.update(None, current_time, delta_time)
            
            # Check if boss is defeated
            if not self.boss.alive:
                self._handle_boss_defeated()
        
        # Handle collisions
        self._handle_collisions()
        
        # Check for level completion
        if (self.distance_traveled >= self.level_length and 
            len(self.enemies) == 0 and 
            (not self.boss or not self.boss.alive)):
            self._complete_chapter()
    
    def draw(self, surface):
        """Draw Bonus Chapter"""
        # Draw stormy sky background
        self._draw_stormy_background(surface)
        
        # Draw orbital grid
        self._draw_orbital_grid(surface)
        
        # Draw environmental effects
        self._draw_storm_effects(surface)
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(surface, (0, 0))  # No camera offset for horizontal SHMUP
        
        # Draw enemy projectiles
        for projectile in self.enemy_projectiles:
            circle(surface, (255, 100, 100), projectile.rect.center, 4)
        
        # Draw boss
        if self.boss:
            self.boss.draw(surface, (0, 0))
        
        # Draw player
        self.player.draw(surface, (0, 0))
        
        # Draw particles
        self.particles.draw(surface, (0, 0))
        
        # Draw UI
        self._draw_ui(surface)
    
    def _setup_orbital_grid(self):
        """Setup the orbital grid pattern"""
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        # Create grid lines
        grid_spacing = 100
        
        # Vertical lines
        for x in range(0, screen_width + grid_spacing, grid_spacing):
            self.grid_lines.append({
                'type': 'vertical',
                'pos': x,
                'alpha': randint(50, 150)
            })
        
        # Horizontal lines
        for y in range(0, screen_height + grid_spacing, grid_spacing):
            self.grid_lines.append({
                'type': 'horizontal',
                'pos': y,
                'alpha': randint(50, 150)
            })
    
    def _update_player_horizontal(self, delta_time):
        """Update player for horizontal SHMUP movement"""
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        # Vertical movement only
        if hasattr(self.player, 'thrust_up') and self.player.thrust_up:
            self.player.rect.y -= int(self.player.speed * delta_time / 16)
        if hasattr(self.player, 'thrust_down') and self.player.thrust_down:
            self.player.rect.y += int(self.player.speed * delta_time / 16)
        
        # Keep player on screen
        self.player.rect.y = max(0, min(screen_height - self.player.rect.height, self.player.rect.y))
        
        # Update player bullets
        if hasattr(self.player, 'bullets_group'):
            for bullet in list(self.player.bullets_group):
                bullet.rect.x += 8  # Move bullets right
                if bullet.rect.left > get_setting("display", "WIDTH", 1920):
                    bullet.kill()
    
    def _spawn_enemy(self):
        """Spawn an enemy appropriate for horizontal SHMUP"""
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        enemy_type = choice(self.enemy_types)
        
        # Spawn at right edge
        x = screen_width + 50
        y = randint(50, screen_height - 50)
        
        enemy = Enemy(x, y, self.game.asset_manager)
        
        # Configure enemy based on type
        if enemy_type == "gorgon_drone":
            enemy.health = int(30 * self.difficulty_multiplier)
            enemy.speed = 2 + self.difficulty_multiplier * 0.5
            enemy.ai_type = "straight_line"
            
        elif enemy_type == "interceptor":
            enemy.health = int(50 * self.difficulty_multiplier)
            enemy.speed = 3 + self.difficulty_multiplier * 0.5
            enemy.ai_type = "sine_wave"
            
        elif enemy_type == "mine":
            enemy.health = int(15 * self.difficulty_multiplier)
            enemy.speed = 1 + self.difficulty_multiplier * 0.3
            enemy.ai_type = "homing"
            enemy.target = self.player.rect.center
        
        # Set horizontal movement
        enemy.horizontal_velocity = -enemy.speed
        
        self.enemies.add(enemy)
        
        # Some enemies shoot
        if random() < 0.3:  # 30% chance to shoot
            self._enemy_shoot(enemy)
    
    def _enemy_shoot(self, enemy):
        """Make an enemy shoot at the player"""
        # Calculate direction to player
        dx = self.player.rect.centerx - enemy.rect.centerx
        dy = self.player.rect.centery - enemy.rect.centery
        distance = sqrt(dx*dx + dy*dy)
        
        if distance > 0:
            # Normalize direction
            dx /= distance
            dy /= distance
            
            # Create projectile
            projectile = Sprite()
            projectile.rect = Rect(enemy.rect.centerx, enemy.rect.centery, 8, 8)
            projectile.velocity_x = dx * 5
            projectile.velocity_y = dy * 5
            projectile.damage = 20
            
            self.enemy_projectiles.add(projectile)
    
    def _spawn_sky_fortress_boss(self):
        """Spawn the Sky Fortress boss"""
        self.boss_spawned = True
        
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        # Spawn boss at right edge, center vertically
        boss_x = screen_width + 100
        boss_y = screen_height // 2
        
        self.boss = Enemy(boss_x, boss_y, self.game.asset_manager)
        self.boss.health = 500
        self.boss.max_health = 500
        self.boss.speed = 1.5
        self.boss.damage = 40
        self.boss.ai_type = "fortress"
        
        # Make boss larger
        self.boss.rect.width = 120
        self.boss.rect.height = 80
        
        # Create dramatic entrance effect
        self.particles.create_explosion(
            boss_x, boss_y,
            (255, 255, 0),  # Yellow
            particle_count=60
        )
        
        # Play boss music
        self.game.asset_manager.play_sound("boss_intro")
        
        logger.info("Sky Fortress boss has appeared!")
    
    def _update_storm_effects(self, current_time):
        """Update storm and lightning effects"""
        # Lightning strikes
        if current_time > self.lightning_timer:
            self.lightning_timer = current_time + randint(2000, 5000)
            self._create_lightning_strike()
        
        # Update storm intensity
        self.storm_intensity += uniform(-0.1, 0.1)
        self.storm_intensity = max(0.2, min(1.0, self.storm_intensity))
    
    def _create_lightning_strike(self):
        """Create a lightning strike effect"""
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        # Random lightning position
        x = randint(0, screen_width)
        
        # Create lightning particles
        self.particles.create_explosion(
            x, 0,  # Top of screen
            (255, 255, 255),  # White
            particle_count=20
        )
        
        # Lightning sound
        self.game.asset_manager.play_sound("laser_charge")
    
    def _update_grid_effects(self, current_time):
        """Update orbital grid effects"""
        self.grid_pulse_timer += 16  # Assuming 60 FPS
        
        # Pulse grid lines
        for line in self.grid_lines:
            pulse = sin(self.grid_pulse_timer * 0.01 + line['pos'] * 0.1)
            line['alpha'] = int(100 + 50 * pulse)
    
    def _handle_collisions(self):
        """Handle all collision detection"""
        # Player bullets vs enemies
        if hasattr(self.player, 'bullets_group'):
            for bullet in list(self.player.bullets_group):
                for enemy in list(self.enemies):
                    if bullet.rect.colliderect(enemy.rect):
                        # Damage enemy
                        enemy.health -= getattr(bullet, 'damage', 25)
                        bullet.kill()
                        
                        # Create hit effect
                        self.particles.create_explosion(
                            enemy.rect.centerx,
                            enemy.rect.centery,
                            (255, 100, 0),  # Orange
                            particle_count=10
                        )
                        
                        # Remove enemy if dead
                        if enemy.health <= 0:
                            enemy.kill()
                            
                            # Award points
                            if hasattr(self.game, 'score'):
                                self.game.score += 100
                
                # Player bullets vs boss
                if self.boss and bullet.rect.colliderect(self.boss.rect):
                    self.boss.health -= getattr(bullet, 'damage', 25)
                    bullet.kill()
                    
                    # Create hit effect
                    self.particles.create_explosion(
                        self.boss.rect.centerx,
                        self.boss.rect.centery,
                        (255, 0, 0),  # Red
                        particle_count=15
                    )
        
        # Enemy projectiles vs player
        for projectile in list(self.enemy_projectiles):
            if projectile.rect.colliderect(self.player.rect):
                # Damage player
                self.player.health -= getattr(projectile, 'damage', 20)
                projectile.kill()
                
                # Create hit effect
                self.particles.create_explosion(
                    self.player.rect.centerx,
                    self.player.rect.centery,
                    (255, 255, 0),  # Yellow
                    particle_count=8
                )
                
                # Check if player is defeated
                if self.player.health <= 0:
                    self._handle_player_defeated()
        
        # Enemies vs player (collision damage)
        for enemy in list(self.enemies):
            if enemy.rect.colliderect(self.player.rect):
                # Damage both
                self.player.health -= 30
                enemy.health -= 50
                
                # Create collision effect
                self.particles.create_explosion(
                    (enemy.rect.centerx + self.player.rect.centerx) // 2,
                    (enemy.rect.centery + self.player.rect.centery) // 2,
                    (255, 255, 255),  # White
                    particle_count=20
                )
                
                # Remove enemy
                enemy.kill()
                
                # Check if player is defeated
                if self.player.health <= 0:
                    self._handle_player_defeated()
    
    def _handle_boss_defeated(self):
        """Handle Sky Fortress boss defeat"""
        # Create massive explosion
        self.particles.create_explosion(
            self.boss.rect.centerx,
            self.boss.rect.centery,
            (255, 215, 0),  # Gold
            particle_count=100
        )
        
        # Play victory sound
        self.game.asset_manager.play_sound("boss_death")
        
        # Award bonus points
        if hasattr(self.game, 'score'):
            self.game.score += 1000
        
        logger.info("Sky Fortress boss defeated!")
    
    def _handle_player_defeated(self):
        """Handle player defeat"""
        # Create player explosion
        self.particles.create_explosion(
            self.player.rect.centerx,
            self.player.rect.centery,
            (255, 0, 0),  # Red
            particle_count=50
        )
        
        # Play death sound
        self.game.asset_manager.play_sound("player_death")
        
        # Transition to game over
        self.game.state_manager.set_state("GameOverState")
    
    def _complete_chapter(self):
        """Complete the Bonus Chapter"""
        self.chapter_complete = True
        self.completion_time = get_ticks() - self.start_time
        
        # Show completion message
        self.game.set_story_message("Skyward Grid Complete! Crucial intel obtained for the true ending.", 4000)
        
        # Transition back to story map
        self.game.state_manager.set_state(
            GAME_STATE_STORY_MAP,
            chapter_completed=True,
            completed_chapter="Bonus: The Skyward Grid"
        )
    
    def _draw_stormy_background(self, surface):
        """Draw the stormy sky background"""
        # Base sky color (dark stormy)
        base_color = (20, 20, 40)
        surface.fill(base_color)
        
        # Add storm clouds effect
        cloud_alpha = int(100 * self.storm_intensity)
        cloud_surface = Surface(surface.get_size())
        cloud_surface.set_alpha(cloud_alpha)
        cloud_surface.fill((40, 40, 60))
        surface.blit(cloud_surface, (0, 0))
    
    def _draw_orbital_grid(self, surface):
        """Draw the orbital grid overlay"""
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)
        
        for line in self.grid_lines:
            color = (0, 100, 200, line['alpha'])  # Blue grid
            
            if line['type'] == 'vertical':
                x = (line['pos'] + self.background_x) % (screen_width + 100)
                line(surface, color[:3], (x, 0), (x, screen_height), 1)
            else:  # horizontal
                y = line['pos']
                line(surface, color[:3], (0, y), (screen_width, y), 1)
    
    def _draw_storm_effects(self, surface):
        """Draw additional storm effects"""
        # Rain effect
        if self.storm_intensity > 0.5:
            for _ in range(int(20 * self.storm_intensity)):
                x = randint(0, surface.get_width())
                y = randint(0, surface.get_height())
                line(surface, (100, 100, 150), (x, y), (x - 2, y + 10), 1)
    
    def _draw_ui(self, surface):
        """Draw Bonus Chapter UI"""
        # Chapter title
        title_text = self.font.render("Bonus: The Skyward Grid", True, (255, 215, 0))
        surface.blit(title_text, (10, 10))
        
        # Progress
        progress = min(100, (self.distance_traveled / self.level_length) * 100)
        progress_text = f"Progress: {progress:.1f}%"
        progress_surface = self.small_font.render(progress_text, True, (255, 255, 255))
        surface.blit(progress_surface, (10, 50))
        
        # Player health
        health_text = f"Health: {self.player.health}/{self.player.max_health}"
        health_surface = self.small_font.render(health_text, True, (255, 255, 255))
        surface.blit(health_surface, (10, 80))
        
        # Boss health (if active)
        if self.boss and self.boss.alive:
            boss_health_text = f"Sky Fortress: {self.boss.health}/{self.boss.max_health}"
            boss_surface = self.small_font.render(boss_health_text, True, (255, 100, 100))
            surface.blit(boss_surface, (10, 110))
        
        # Controls
        controls = [
            "SPACE: Shoot",
            "UP/DOWN: Move",
            "ESC: Exit"
        ]
        
        for i, control in enumerate(controls):
            control_surface = self.small_font.render(control, True, (200, 200, 200))
            surface.blit(control_surface, (surface.get_width() - 200, 10 + i * 25))
        
        # Storm intensity indicator
        storm_text = f"Storm: {int(self.storm_intensity * 100)}%"
        storm_surface = self.small_font.render(storm_text, True, (150, 150, 255))
        surface.blit(storm_surface, (10, surface.get_height() - 30))