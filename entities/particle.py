# entities/particle.py
from pygame.sprite import Sprite
from pygame.draw import circle
from pygame import Surface, SRCALPHA
from random import choice, uniform
from math import radians, cos, sin
from settings_manager import get_setting
from constants import FLAME_COLORS

class Particle(Sprite):
    def __init__(self, x, y, color_list, 
                 min_speed, max_speed, 
                 min_size, max_size, 
                 gravity=0.1, shrink_rate=0.1, lifetime_frames=30,
                 base_angle_deg=None, spread_angle_deg=360,
                 x_offset=0, y_offset=0,
                 blast_mode=False):
        super().__init__()
        
        self.x, self.y = float(x + x_offset), float(y + y_offset)
        self.blast_mode = blast_mode
        self.lifetime = lifetime_frames

        if self.blast_mode:
            self.color = choice(FLAME_COLORS)
            self.size = uniform(min_size, max_size)
            speed = uniform(min_speed, max_speed)
        else:
            self.color = choice(color_list)
            self.size = uniform(min_size, max_size)
            speed = uniform(min_speed, max_speed)
            self.gravity = gravity
            self.shrink_rate = shrink_rate

        self.initial_size = self.size
        self.current_lifetime = 0
        
        angle = base_angle_deg if base_angle_deg is not None else uniform(0, 360)
        angle += uniform(-spread_angle_deg / 2, spread_angle_deg / 2)
        angle_rad = radians(angle)
        
        self.vx, self.vy = cos(angle_rad) * speed, sin(angle_rad) * speed
        
        surf_dim = int(self.initial_size * 2) + 2
        self.image = Surface([surf_dim, surf_dim], SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._redraw_image()

    def _redraw_image(self):
        self.image.fill((0, 0, 0, 0))
        center_pos = self.image.get_width() // 2
        draw_size = int(self.size)
        if draw_size < 1:
            return

        life_ratio = 1.0 - (self.current_lifetime / self.lifetime)
        current_alpha = int(255 * (life_ratio ** 1.5))
        
        if current_alpha > 0:
            draw_color = (*self.color[:3], current_alpha)
            circle(self.image, draw_color, (center_pos, center_pos), draw_size)

    def update(self):
        self.current_lifetime += 1
        if self.current_lifetime >= self.lifetime:
            self.kill()
            return

        self.x += self.vx
        self.y += self.vy

        if self.blast_mode:
            life_ratio = 1.0 - (self.current_lifetime / self.lifetime)
            self.size = self.initial_size * life_ratio
        else:
            self.size -= self.shrink_rate

        if self.size < 0.5:
            self.kill()
            return
            
        self._redraw_image()
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, surface, camera=None): 
        if self.alive():
            if camera:
                screen_rect = camera.apply_to_rect(self.rect)
                if not screen_rect.colliderect(surface.get_rect()) or screen_rect.width <= 0:
                    return
                # Optimized drawing for scaled particles
                draw_pos = (int(screen_rect.centerx), int(screen_rect.centery))
                draw_radius = int(self.size * camera.zoom_level)
                if draw_radius > 0:
                    life_ratio = 1.0 - (self.current_lifetime / self.lifetime)
                    alpha = int(255 * (life_ratio ** 1.5))
                    color = (*self.color[:3], alpha)
                    circle(surface, color, draw_pos, draw_radius)
            else:
                surface.blit(self.image, self.rect)

class ParticleSystem:
    def __init__(self):
        self.particles = []
    
    def create_explosion(self, x, y, color, particle_count=20):
        for _ in range(particle_count):
            particle = Particle(x, y, [color], 1, 5, 2, 8, lifetime_frames=30)
            self.particles.append(particle)
    
    def update(self, delta_time):
        for particle in self.particles[:]:
            particle.update()
            if not particle.alive():
                self.particles.remove(particle)
    
    def draw(self, surface, camera_offset=(0, 0)):
        for particle in self.particles:
            particle.draw(surface)
