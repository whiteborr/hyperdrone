import pygame
import math
import random
import logging

from settings_manager import get_setting
from constants import FLAME_COLORS
from .particle import Particle

logger = logging.getLogger(__name__)

class PowerUpManager:
    def __init__(self, player_ref):
        self.player = player_ref
        self.shield_active = False
        self.shield_end_time = 0
        self.speed_boost_armed = False
        self.speed_boost_active = False
        self.speed_boost_end_time = 0
        self.speed_boost_duration = 0
        self.speed_boost_multiplier = 1.0
        self.propulsion_active = False
        self.propulsion_particles = pygame.sprite.Group()
        self.last_particle_time = 0
        self.original_player_speed = self.player.speed
    
    def activate_shield(self, duration_ms):
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration_ms
    
    def arm_speed_boost(self, duration_ms, multiplier=1.5):
        self.speed_boost_armed = True
        self.speed_boost_duration = duration_ms
        self.speed_boost_multiplier = multiplier
    
    def activate_speed_boost(self):
        if self.speed_boost_armed:
            self.speed_boost_active = True
            self.speed_boost_end_time = pygame.time.get_ticks() + self.speed_boost_duration
            self.player.speed = self.original_player_speed * self.speed_boost_multiplier
            self.activate_shield(self.speed_boost_duration)
            self.propulsion_active = True
            self.speed_boost_armed = False

    def update(self, current_time_ms):
        """Update all power-up states and create particles only for speed boost."""
        # Update shield timer
        if self.shield_active and current_time_ms > self.shield_end_time:
            self.shield_active = False
            logger.debug("Shield deactivated")
        
        # Update speed boost timer and create exhaust particles ONLY if the boost is active
        if self.speed_boost_active:
            if current_time_ms > self.speed_boost_end_time:
                # Deactivate boost when timer runs out
                self.speed_boost_active = False
                self.propulsion_active = False
                self.player.speed = self.original_player_speed
                logger.debug("Speed boost deactivated")
            else:
                # If boost is active, check if it's time to spawn particles
                particle_spawn_interval = 30  # Controls the density of the trail
                if current_time_ms - self.last_particle_time > particle_spawn_interval:
                    self._create_propulsion_particles(is_boosting=True)
                    self.last_particle_time = current_time_ms
            
        # This will update any remaining particles until they fade out
        self.propulsion_particles.update()

    def _create_propulsion_particles(self, is_boosting):
        angle_rad = math.radians(self.player.angle + 180)
        base_offset = self.player.rect.width / 2.5
        
        spawn_x = self.player.x + math.cos(angle_rad) * base_offset
        spawn_y = self.player.y + math.sin(angle_rad) * base_offset

        num_particles = random.randint(2, 3) if is_boosting else 1
        
        for _ in range(num_particles):
            if is_boosting:
                speed = random.uniform(get_setting("particles", "THRUST_PARTICLE_SPEED_MIN_BLAST", 2.0), 
                                      get_setting("particles", "THRUST_PARTICLE_SPEED_MAX_BLAST", 4.0))
                size = random.uniform(get_setting("particles", "THRUST_PARTICLE_START_SIZE_BLAST_MIN", 2.0), 
                                     get_setting("particles", "THRUST_PARTICLE_START_SIZE_BLAST_MAX", 4.0))
                lifetime = get_setting("particles", "THRUST_PARTICLE_LIFETIME_BLAST", 20)
            else:
                min_speed = get_setting("particles", "THRUST_PARTICLE_SPEED_MIN_BLAST", 2.0) * 0.5
                max_speed = get_setting("particles", "THRUST_PARTICLE_SPEED_MAX_BLAST", 4.0) * 0.5
                min_size = get_setting("particles", "THRUST_PARTICLE_START_SIZE_BLAST_MIN", 2.0) * 0.4
                max_size = get_setting("particles", "THRUST_PARTICLE_START_SIZE_BLAST_MAX", 4.0) * 0.6
                speed = random.uniform(min_speed, max_speed)
                size = random.uniform(min_size, max_size)
                lifetime = int(get_setting("particles", "THRUST_PARTICLE_LIFETIME_BLAST", 20) * 0.7)

            particle = Particle(
                x=spawn_x, y=spawn_y,
                color_list=FLAME_COLORS,
                min_speed=speed, max_speed=speed,
                min_size=size, max_size=size,
                lifetime_frames=lifetime,
                base_angle_deg=self.player.angle + 180,
                spread_angle_deg=get_setting("particles", "THRUST_PARTICLE_SPREAD_ANGLE", 15),
                blast_mode=True
            )
            self.propulsion_particles.add(particle)
            
    def draw(self, surface, camera=None):
        """Draws all power-up effects, including the drone's shield glow."""
        # First, draw the propulsion particles so they appear behind everything.
        self.propulsion_particles.draw(surface, camera)
        
        # --- NEW SHIELD GLOW LOGIC ---
        if self.shield_active and self.player.rect and hasattr(self.player, 'original_image'):
            
            # 1. Get the current rotated image of the player drone to match its orientation.
            rotated_image = pygame.transform.rotate(self.player.original_image, -self.player.angle)
            
            # 2. Create a mask from the drone's image to get its exact pixel-perfect shape.
            mask = pygame.mask.from_surface(rotated_image)
            
            # 3. Create a new surface from the mask, which will be our glow color.
            # We can also add a pulsing alpha to make it feel more alive.
            pulse_alpha = 100 + (math.sin(pygame.time.get_ticks() * 0.008) + 1) * 75 # Varies between 100-250
            glow_color = (150, 220, 255, pulse_alpha) # A nice cyan-white shield color
            
            # This creates a colored silhouette of the drone's shape.
            glow_silhouette = mask.to_surface(setcolor=glow_color, unsetcolor=(0, 0, 0, 0))
            
            # 4. To create the "glow" effect, we will blit this silhouette multiple times with slight offsets.
            # This is a classic and efficient way to simulate a bloom or glow effect in Pygame.
            glow_surface_size = (glow_silhouette.get_width() + 8, glow_silhouette.get_height() + 8)
            glow_surface = pygame.Surface(glow_surface_size, pygame.SRCALPHA)
            
            # Blit the silhouette at four corners to create the outline.
            glow_surface.blit(glow_silhouette, (0, 4))
            glow_surface.blit(glow_silhouette, (8, 4))
            glow_surface.blit(glow_silhouette, (4, 0))
            glow_surface.blit(glow_silhouette, (4, 8))

            # 5. Position the final glow surface so it's centered on the player.
            glow_rect = glow_surface.get_rect(center=self.player.rect.center)
            
            # 6. Draw the final effect to the main screen, accounting for the camera.
            if camera:
                screen_rect = camera.apply_to_rect(glow_rect)
                if screen_rect.width > 0 and screen_rect.height > 0:
                    scaled_glow_surface = pygame.transform.smoothscale(glow_surface, screen_rect.size)
                    # Using BLEND_RGBA_ADD makes the glow brighter and more "energetic".
                    surface.blit(scaled_glow_surface, screen_rect, special_flags=pygame.BLEND_RGBA_ADD)
            else:
                surface.blit(glow_surface, glow_rect, special_flags=pygame.BLEND_RGBA_ADD)

    def handle_damage(self, amount):
        return self.shield_active