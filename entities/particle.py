import pygame
import random
import math
import game_settings as gs

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

        if self.blast_mode:
            self.color = random.choice(gs.FLAME_COLORS)
            self.size = random.uniform(gs.THRUST_PARTICLE_START_SIZE_BLAST_MIN, gs.THRUST_PARTICLE_START_SIZE_BLAST_MAX)
            self.gravity, self.shrink_rate = 0, gs.THRUST_PARTICLE_SHRINK_RATE_BLAST
            self.lifetime = gs.THRUST_PARTICLE_LIFETIME_BLAST
            speed = random.uniform(gs.THRUST_PARTICLE_SPEED_MIN_BLAST, gs.THRUST_PARTICLE_SPEED_MAX_BLAST)
        else:
            self.color, self.size = random.choice(color_list), random.uniform(min_size, max_size)
            self.gravity, self.shrink_rate = gravity, shrink_rate
            self.lifetime, speed = lifetime_frames, random.uniform(min_speed, max_speed)

        self.initial_size, self.current_lifetime = self.size, 0

        angle_rad = math.radians(random.uniform(0, 360) if base_angle_deg is None else base_angle_deg + random.uniform(-spread_angle_deg / 2, spread_angle_deg / 2))
        self.vx, self.vy = math.cos(angle_rad) * speed, math.sin(angle_rad) * speed
        
        max_start_size = gs.THRUST_PARTICLE_START_SIZE_BLAST_MAX if self.blast_mode else max_size
        surf_dim = max(2, int(max_start_size * 2) + 2)
        self.image = pygame.Surface([surf_dim, surf_dim], pygame.SRCALPHA)
        self._redraw_image()
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def _redraw_image(self):
        surf_dim = max(2, int(self.size * 2) + 2)
        if self.image.get_width() < surf_dim or self.image.get_height() < surf_dim:
             self.image = pygame.Surface([surf_dim, surf_dim], pygame.SRCALPHA)
        else:
            self.image.fill((0,0,0,0))

        center_pos = self.image.get_width() // 2
        life_ratio = max(0, 1 - (self.current_lifetime / self.lifetime if self.lifetime > 0 else 1))
        current_alpha = int(255 * (life_ratio ** 1.5)) if self.blast_mode else 255
        draw_color = (*self.color[:3], max(0, min(255, current_alpha)))

        if self.size >= 1:
            pygame.draw.circle(self.image, draw_color, (center_pos, center_pos), int(self.size))

    def update(self):
        self.current_lifetime += 1
        if self.current_lifetime >= self.lifetime: self.kill(); return
        self.vy += self.gravity; self.x += self.vx; self.y += self.vy
        
        prev_size = self.size
        if self.blast_mode:
            life_ratio = max(0, 1 - (self.current_lifetime / self.lifetime if self.lifetime > 0 else 1))
            self.size = self.initial_size * (life_ratio ** 0.7)
        else:
            self.size -= self.shrink_rate
        if self.size < 1: self.kill(); return
        if self.size != prev_size or self.blast_mode: self._redraw_image()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def draw(self, surface, camera=None): 
        if self.alive(): 
            if camera:
                screen_rect = camera.apply_to_rect(self.rect)
                if not screen_rect.colliderect(surface.get_rect()): return
                if screen_rect.width > 0 and screen_rect.height > 0:
                    # The particle's image is pre-rendered with effects, so we just scale it
                    scaled_image = pygame.transform.smoothscale(self.image, screen_rect.size)
                    surface.blit(scaled_image, screen_rect.topleft)
            else:
                surface.blit(self.image, self.rect)