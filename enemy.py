# enemy.py
import pygame
import math
import random
import os 

# Corrected import for Bullet class
try:
    from bullet import Bullet 
except ImportError:
    print("Warning (enemy.py): Could not import Bullet from bullet.py. Enemy shooting will be affected.")
    # Define a dummy Bullet class if bullet.py or Bullet class is not found
    class Bullet(pygame.sprite.Sprite):
        def __init__(self, x, y, angle, speed, lifetime, size, color, damage): # Removed owner from dummy
            super().__init__()
            self.image = pygame.Surface([size*2, size*2]) 
            self.rect = self.image.get_rect(center=(x,y))
            self.alive = True
        def update(self, maze=None): 
            if not self.alive: self.kill()


from game_settings import (
    TILE_SIZE, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_COLOR,
    ENEMY_BULLET_SPEED, ENEMY_BULLET_COOLDOWN, ENEMY_BULLET_LIFETIME,
    ENEMY_BULLET_COLOR, ENEMY_BULLET_DAMAGE, PLAYER_DEFAULT_BULLET_SIZE, 
    WIDTH, GAME_PLAY_AREA_HEIGHT 
)

class Enemy(pygame.sprite.Sprite):
    # Corrected constructor to accept player_default_bullet_size
    def __init__(self, x, y, player_default_bullet_size, shoot_sound=None, sprite_path=None, target_player=None): 
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = 0  
        self.speed = ENEMY_SPEED 
        self.health = ENEMY_HEALTH 
        self.max_health = ENEMY_HEALTH 
        self.alive = True
        self.shoot_sound = shoot_sound
        self.player_ref = target_player 

        self.original_image = None
        self.image = None
        self.rect = None
        self.collision_rect = None 

        self._load_sprite(sprite_path) 

        self.bullets = pygame.sprite.Group()
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, ENEMY_BULLET_COOLDOWN) 
        self.shoot_cooldown = ENEMY_BULLET_COOLDOWN 
        
        # Store the passed-in player default bullet size
        self.player_bullet_size_base = player_default_bullet_size # Used in shoot method

        self.state = "patrolling" 
        self.patrol_target_pos = None
        self.state_timer = 0

    def _load_sprite(self, sprite_path):
        default_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7)) 
        if sprite_path and os.path.exists(sprite_path):
            try:
                self.original_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(self.original_image, default_size)
            except pygame.error as e:
                print(f"Error loading enemy sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
                self.original_image.fill(ENEMY_COLOR) 
        else:
            if sprite_path: print(f"Warning: Enemy sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            self.original_image.fill(ENEMY_COLOR)
        
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(self.x, self.y))
        
        self.collision_rect_width = self.rect.width * 0.8
        self.collision_rect_height = self.rect.height * 0.8
        self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center


    def update(self, player_pos, maze, current_time):
        if not self.alive:
            self.bullets.empty() 
            self.kill()
            return

        self._update_ai(player_pos, maze, current_time)
        self._update_movement(maze) 

        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.collision_rect.center = self.rect.center

        self.bullets.update(maze) 

        if current_time - self.last_shot_time > self.shoot_cooldown:
            if player_pos:
                dx = player_pos[0] - self.x
                dy = player_pos[1] - self.y
                distance_to_player = math.hypot(dx, dy)
                if distance_to_player < TILE_SIZE * 10: 
                    self.shoot(player_pos) 
                    self.last_shot_time = current_time


    def _update_ai(self, player_pos, maze, current_time):
        if player_pos:
            dx = player_pos[0] - self.x
            dy = player_pos[1] - self.y
            distance_to_player = math.hypot(dx, dy)

            if distance_to_player < TILE_SIZE * 8: # Chase range
                self.state = "chasing"
                # Aim towards player
                # Original angle calculation: math.degrees(math.atan2(-dy, dx)) - 90
                # If this makes the enemy face the opposite direction, add 180 degrees.
                self.angle = (math.degrees(math.atan2(-dy, dx)) - 90 + 180) % 360 
            else:
                self.state = "patrolling"
        
        if self.state == "patrolling":
            if not self.patrol_target_pos or current_time > self.state_timer:
                self.angle += random.uniform(-30, 30)
                self.state_timer = current_time + random.randint(2000, 5000) 

    def _update_movement(self, maze):
        rad_angle = math.radians(self.angle)
        move_dx = math.sin(rad_angle) * self.speed
        move_dy = -math.cos(rad_angle) * self.speed

        next_x = self.x + move_dx
        next_y = self.y + move_dy

        next_rect = self.collision_rect.copy()
        next_rect.center = (next_x, next_y)
        
        wall_hit = False
        if maze:
            if maze.is_wall(next_rect.centerx, next_rect.centery, self.collision_rect_width, self.collision_rect_height):
                wall_hit = True

        if not wall_hit:
            self.x = next_x
            self.y = next_y
        else:
            self.angle += random.choice([-90, 90, 180]) 

        self.x = max(self.rect.width/2, min(self.x, WIDTH - self.rect.width/2)) 
        self.y = max(self.rect.height/2, min(self.y, GAME_PLAY_AREA_HEIGHT - self.rect.height/2)) 
        
        self.rect.center = (self.x, self.y)
        self.collision_rect.center = self.rect.center


    def shoot(self, target_pos=None):
        if not self.alive:
            return

        rad = math.radians(self.angle)
        tip_offset = self.rect.height / 2 
        tip_x = self.x + math.sin(rad) * tip_offset
        tip_y = self.y - math.cos(rad) * tip_offset
        
        bullet_angle_to_shoot = self.angle
        if target_pos: 
            dx = target_pos[0] - tip_x
            dy = target_pos[1] - tip_y
            bullet_angle_to_shoot = math.degrees(math.atan2(-dy, dx)) - 90
        
        # Use the instance variable that was set in __init__
        bullet_s = int(self.player_bullet_size_base // 1.5) 

        new_bullet = Bullet(
            x=tip_x, y=tip_y, angle=bullet_angle_to_shoot,
            speed=ENEMY_BULLET_SPEED, 
            lifetime=ENEMY_BULLET_LIFETIME, 
            size=bullet_s, 
            color=ENEMY_BULLET_COLOR, 
            damage=ENEMY_BULLET_DAMAGE
            # owner=self # Removed owner argument
        )
        self.bullets.add(new_bullet)
        if self.shoot_sound:
            self.shoot_sound.play()

    def take_damage(self, amount):
        if not self.alive:
            return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def draw(self, surface):
        if self.alive:
            surface.blit(self.image, self.rect)
        
        self.bullets.draw(surface)

