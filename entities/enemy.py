import math
import random
import os

import pygame

from .bullet import Bullet

import game_settings as gs
from game_settings import (
    # Constants directly used by the Enemy class
    TILE_SIZE, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_COLOR, #
    ENEMY_BULLET_SPEED, ENEMY_BULLET_COOLDOWN, ENEMY_BULLET_LIFETIME, #
    ENEMY_BULLET_COLOR, ENEMY_BULLET_DAMAGE, #
    PLAYER_DEFAULT_BULLET_SIZE, # Used as a base for enemy bullet size
    WIDTH, GAME_PLAY_AREA_HEIGHT # For boundary checks
)

# The local Bullet class definition previously in enemy.py is now removed,
# as we are importing the main Bullet class from .bullet

class Enemy(pygame.sprite.Sprite): #
    def __init__(self, x, y, player_bullet_size_base, shoot_sound=None, sprite_path=None, target_player_ref=None): #
        super().__init__() #
        self.x = float(x) #
        self.y = float(y) #
        self.angle = 0.0  #
        # Use gs.get_game_setting for dynamic settings if needed, otherwise direct constant for base values
        self.speed = gs.ENEMY_SPEED #
        self.health = gs.ENEMY_HEALTH #
        self.max_health = gs.ENEMY_HEALTH #
        self.alive = True #
        self.shoot_sound = shoot_sound #
        self.player_ref = target_player_ref #

        self.original_image = None #
        self.image = None          #
        self.rect = None           #
        self.collision_rect = None #

        self._load_sprite(sprite_path) #

        self.bullets = pygame.sprite.Group() #
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, int(ENEMY_BULLET_COOLDOWN)) #
        self.shoot_cooldown = ENEMY_BULLET_COOLDOWN #
        
        self.enemy_bullet_size = int(player_bullet_size_base // 1.5) if player_bullet_size_base else 3 #

        self.state = "patrolling" #
        self.patrol_target_pos = None #
        self.state_timer = 0 #

    def _load_sprite(self, sprite_path): #
        """Loads the enemy's sprite or creates a default one."""
        default_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7)) #
        
        if sprite_path and os.path.exists(sprite_path): #
            try: #
                loaded_image = pygame.image.load(sprite_path).convert_alpha() #
                self.original_image = pygame.transform.scale(loaded_image, default_size) #
            except pygame.error as e: #
                print(f"Error loading enemy sprite '{sprite_path}': {e}. Using fallback.") #
                self.original_image = None #
        else: #
            if sprite_path: print(f"Warning: Enemy sprite path not found: {sprite_path}. Using fallback.") #
            self.original_image = None #

        if self.original_image is None: #
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA) #
            self.original_image.fill(ENEMY_COLOR) #

        self.image = self.original_image.copy() #
        self.rect = self.image.get_rect(center=(self.x, self.y)) #
        
        self.collision_rect_width = self.rect.width * 0.8 #
        self.collision_rect_height = self.rect.height * 0.8 #
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height) #
        self.collision_rect.center = self.rect.center #

    def update(self, player_pos, maze, current_time, game_area_x_offset=0): #
        """Updates the enemy's state, movement, and actions."""
        if not self.alive: #
            if not self.bullets: #
                self.kill() #
            self.bullets.update(maze, game_area_x_offset) #
            return #

        self._update_ai(player_pos, maze, current_time) #
        self._update_movement(maze, game_area_x_offset) #

        self.image = pygame.transform.rotate(self.original_image, -self.angle) #
        self.rect = self.image.get_rect(center=(self.x, self.y)) #
        self.collision_rect.center = self.rect.center #

        self.bullets.update(maze, game_area_x_offset) #

        if player_pos and (current_time - self.last_shot_time > self.shoot_cooldown): #
            dx_player = player_pos[0] - self.x #
            dy_player = player_pos[1] - self.y #
            distance_to_player = math.hypot(dx_player, dy_player) #
            
            shooting_range = TILE_SIZE * 10 #
            if distance_to_player < shooting_range: #
                self.shoot(target_pos=player_pos) #
                self.last_shot_time = current_time #

    def _update_ai(self, player_pos, maze, current_time): #
        """Basic AI logic for state transitions and targeting."""
        if not player_pos: #
            self.state = "patrolling" #
        else: #
            dx = player_pos[0] - self.x #
            dy = player_pos[1] - self.y #
            distance_to_player = math.hypot(dx, dy) #

            chase_range = TILE_SIZE * 8 #

            if distance_to_player < chase_range: #
                self.state = "chasing" #
                target_angle_rad = math.atan2(dy, dx) #
                self.angle = math.degrees(target_angle_rad) #
            else: #
                self.state = "patrolling" #
        
        if self.state == "patrolling": #
            if not self.patrol_target_pos or current_time > self.state_timer: #
                self.angle += random.uniform(-45, 45) #
                self.angle %= 360 #
                self.state_timer = current_time + random.randint(2000, 5000) #

    def _update_movement(self, maze, game_area_x_offset=0): #
        """Updates position based on current angle and speed, with collision."""
        rad_angle = math.radians(self.angle) #
        move_dx = math.cos(rad_angle) * self.speed #
        move_dy = math.sin(rad_angle) * self.speed #

        next_x = self.x + move_dx #
        next_y = self.y + move_dy #

        temp_collision_rect = self.collision_rect.copy() #
        temp_collision_rect.center = (next_x, next_y) #

        collided = False #
        if maze: #
            if maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery,
                            self.collision_rect_width, self.collision_rect_height): #
                collided = True #

        if not collided: #
            self.x = next_x #
            self.y = next_y #
        else: #
            self.angle += random.choice([-90, 90, 180]) #
            self.angle %= 360 #

        half_col_width = self.collision_rect_width / 2 #
        half_col_height = self.collision_rect_height / 2 #

        min_x_bound = game_area_x_offset + half_col_width #
        max_x_bound = WIDTH - half_col_width # Using imported constant
        min_y_bound = half_col_height #
        max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height # Using imported constant
        
        self.x = max(min_x_bound, min(self.x, max_x_bound)) #
        self.y = max(min_y_bound, min(self.y, max_y_bound)) #
        
        self.rect.center = (int(self.x), int(self.y)) #
        self.collision_rect.center = self.rect.center #

    def shoot(self, target_pos=None): #
        """Creates and fires a bullet."""
        if not self.alive: #
            return #

        rad_fire_angle = math.radians(self.angle) #
        tip_offset_distance = self.rect.width / 2 #
        
        fire_origin_x = self.x + math.cos(rad_fire_angle) * tip_offset_distance #
        fire_origin_y = self.y + math.sin(rad_fire_angle) * tip_offset_distance #
        
        bullet_angle_to_fire = self.angle #
        if target_pos: #
            dx_target = target_pos[0] - fire_origin_x #
            dy_target = target_pos[1] - fire_origin_y #
            bullet_angle_to_fire = math.degrees(math.atan2(dy_target, dx_target)) #
        
        # Using the imported Bullet class from .bullet
        new_bullet = Bullet(
            x=fire_origin_x, y=fire_origin_y, angle=bullet_angle_to_fire,
            speed=ENEMY_BULLET_SPEED, # Using imported constant
            lifetime=ENEMY_BULLET_LIFETIME, # Using imported constant
            size=self.enemy_bullet_size,
            color=ENEMY_BULLET_COLOR, # Using imported constant
            damage=ENEMY_BULLET_DAMAGE # Using imported constant
        ) #
        self.bullets.add(new_bullet) #
        if self.shoot_sound: #
            self.shoot_sound.play() #

    def take_damage(self, amount): #
        """Reduces enemy health by a given amount."""
        if not self.alive: #
            return #
        self.health -= amount #
        if self.health <= 0: #
            self.health = 0 #
            self.alive = False #

    def draw(self, surface): #
        """Draws the enemy and its bullets."""
        if self.alive: #
            surface.blit(self.image, self.rect) #
            # self._draw_health_bar(surface) # Optional health bar
        
        self.bullets.draw(surface) #

    def _draw_health_bar(self, surface): #
        if self.alive and self.health < self.max_health: #
            bar_width = self.rect.width * 0.8 #
            bar_height = 5 #
            bar_x = self.rect.centerx - bar_width / 2 #
            bar_y = self.rect.top - bar_height - 2 #

            health_percent = self.health / self.max_health #
            fill_width = int(bar_width * health_percent) #
            
            pygame.draw.rect(surface, (50,50,50), (bar_x, bar_y, bar_width, bar_height)) #
            health_color = (0,255,0) if health_percent > 0.5 else (255,255,0) if health_percent > 0.2 else (255,0,0) #
            if fill_width > 0: #
                pygame.draw.rect(surface, health_color, (bar_x, bar_y, fill_width, bar_height)) #
            pygame.draw.rect(surface, (200,200,200), (bar_x, bar_y, bar_width, bar_height), 1) #