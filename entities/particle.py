import pygame
import random
import math
import game_settings as gs # For new particle settings

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color_list, 
                 min_speed, max_speed, 
                 min_size, max_size, 
                 gravity=0.1, shrink_rate=0.1, lifetime_frames=30,
                 base_angle_deg=None, spread_angle_deg=360, # New: Directional parameters
                 x_offset=0, y_offset=0, # New: Offset parameters
                 blast_mode=False): # New: Blast mode toggle
        super().__init__()
        
        # Apply offset to initial position
        self.x = float(x + x_offset)
        self.y = float(y + y_offset)
        
        self.blast_mode = blast_mode

        if self.blast_mode:
            self.color = random.choice(gs.FLAME_COLORS)
            self.size = random.uniform(gs.THRUST_PARTICLE_START_SIZE_BLAST_MIN, gs.THRUST_PARTICLE_START_SIZE_BLAST_MAX)
            self.gravity = 0  # No gravity for flame thrust
            self.shrink_rate = gs.THRUST_PARTICLE_SHRINK_RATE_BLAST # Use specific shrink rate
            self.lifetime = gs.THRUST_PARTICLE_LIFETIME_BLAST
            speed = random.uniform(gs.THRUST_PARTICLE_SPEED_MIN_BLAST, gs.THRUST_PARTICLE_SPEED_MAX_BLAST)
        else: # Original behavior for explosions etc.
            self.color = random.choice(color_list)
            self.size = random.uniform(min_size, max_size)
            self.gravity = gravity
            self.shrink_rate = shrink_rate
            self.lifetime = lifetime_frames
            speed = random.uniform(min_speed, max_speed)

        self.initial_size = self.size 
        self.current_lifetime = 0

        # Calculate emission angle
        if base_angle_deg is not None:
            angle_offset = random.uniform(-spread_angle_deg / 2, spread_angle_deg / 2)
            final_angle_deg = base_angle_deg + angle_offset
            angle_rad = math.radians(final_angle_deg)
        else: # Original random 360 spread if no base_angle_deg
            angle_rad = random.uniform(0, 2 * math.pi)
        
        self.vx = math.cos(angle_rad) * speed
        self.vy = math.sin(angle_rad) * speed
        
        # Create image surface (will be updated in update if size changes)
        # Ensure initial surface can hold the largest possible particle to avoid clipping
        # This might need adjustment if particles can grow, but they only shrink here.
        max_possible_start_size = gs.THRUST_PARTICLE_START_SIZE_BLAST_MAX if self.blast_mode else max_size
        surf_dim = int(max_possible_start_size * 2) + 2 # Add a small buffer
        if surf_dim < 2: surf_dim = 2 # Ensure minimum surface dimension

        self.image = pygame.Surface([surf_dim, surf_dim], pygame.SRCALPHA)
        self._redraw_image() # Initial draw with correct current size
        self.rect = self.image.get_rect(center=(self.x, self.y))


    def _redraw_image(self):
        """Helper to redraw the particle image when size or color changes."""
        # Ensure surface can contain the current size
        surf_dim = int(self.size * 2) + 2
        if surf_dim < 2 : surf_dim = 2
        
        # Check if surface needs resizing (only if current image is too small)
        if self.image.get_width() < surf_dim or self.image.get_height() < surf_dim:
             self.image = pygame.Surface([surf_dim, surf_dim], pygame.SRCALPHA)
        else: # Clear existing surface if not resizing
            self.image.fill((0,0,0,0))

        center_pos = self.image.get_width() // 2 # Center on the potentially larger surface

        # Determine color and alpha
        life_ratio = max(0, 1 - (self.current_lifetime / self.lifetime))
        current_alpha = 255
        if self.blast_mode: # Flame particles fade out
            current_alpha = int(255 * (life_ratio ** 1.5)) # Faster fade
        
        draw_color = (*self.color[:3], max(0, min(255, current_alpha)))

        if self.size >= 1:
            pygame.draw.circle(self.image, draw_color, (center_pos, center_pos), int(self.size))
        
        # Update rect based on the actual center of the potentially resized image
        # self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) # This is done in update()

    def update(self):
        self.current_lifetime += 1
        if self.current_lifetime >= self.lifetime:
            self.kill() 
            return

        self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy
        
        prev_size = self.size
        # Shrink based on lifetime for blast mode, or fixed rate for others
        if self.blast_mode:
            life_ratio = max(0, 1 - (self.current_lifetime / self.lifetime))
            self.size = self.initial_size * (life_ratio ** 0.7) # Non-linear shrink for flames
        else:
            self.size -= self.shrink_rate # Original shrink logic for explosions

        if self.size < 1:
            self.kill()
            return
        
        if self.size != prev_size or self.blast_mode: # Redraw if size changed or if it's a blast particle (for alpha fade)
            self._redraw_image()
        
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))


    def draw(self, surface): 
        if self.alive(): 
            surface.blit(self.image, self.rect)
