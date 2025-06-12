import pygame
import random
import math
from settings_manager import get_setting
from constants import FLAME_COLORS

class Particle(pygame.sprite.Sprite):
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
            self.color = random.choice(FLAME_COLORS)
            self.size = random.uniform(min_size, max_size)
            speed = random.uniform(min_speed, max_speed)
        else:
            self.color = random.choice(color_list)
            self.size = random.uniform(min_size, max_size)
            speed = random.uniform(min_speed, max_speed)
            self.gravity = gravity
            self.shrink_rate = shrink_rate

        self.initial_size = self.size
        self.current_lifetime = 0
        
        angle = base_angle_deg if base_angle_deg is not None else random.uniform(0, 360)
        angle += random.uniform(-spread_angle_deg / 2, spread_angle_deg / 2)
        angle_rad = math.radians(angle)
        
        self.vx, self.vy = math.cos(angle_rad) * speed, math.sin(angle_rad) * speed
        
        surf_dim = int(self.initial_size * 2) + 2
        self.image = pygame.Surface([surf_dim, surf_dim], pygame.SRCALPHA)
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
            pygame.draw.circle(self.image, draw_color, (center_pos, center_pos), draw_size)

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
                    pygame.draw.circle(surface, color, draw_pos, draw_radius)
            else:
                surface.blit(self.image, self.rect)
