import math
import pygame

import game_settings as gs
from game_settings import (
    # Import specific constants if they are used very frequently in this base class
    # For BaseDrone, these were the ones directly used in the original file
    TILE_SIZE,          #
    WIDTH,              #
    GAME_PLAY_AREA_HEIGHT, #
    CYAN                #
    # PLAYER_SPEED is used as a default, access via gs.get_game_setting("PLAYER_SPEED")
)

class BaseDrone(pygame.sprite.Sprite):
    def __init__(self, x, y, size=None, speed=None):
        super().__init__() #
        self.x = float(x) #
        self.y = float(y) #
        
        self.size = float(size) if size is not None else TILE_SIZE * 0.8 #
        self.speed = float(speed) if speed is not None else gs.get_game_setting("PLAYER_SPEED") #
        
        self.angle = 0.0  #
        self.alive = True #
        self.moving_forward = False #

        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA) #
        self.rect = self.image.get_rect(center=(self.x, self.y)) #

        self.collision_rect_width = self.rect.width * 0.7 #
        self.collision_rect_height = self.rect.height * 0.7 #
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height) #
        self.collision_rect.center = self.rect.center #

    def rotate(self, direction, rotation_speed): #
        if direction == "left": #
            self.angle += rotation_speed #
        elif direction == "right": #
            self.angle -= rotation_speed #
        self.angle %= 360  #

    def update_movement(self, maze=None, game_area_x_offset=0): #
        if self.moving_forward and self.alive: #
            angle_rad = math.radians(self.angle) #
            dx = math.cos(angle_rad) * self.speed #
            dy = math.sin(angle_rad) * self.speed #
            next_x = self.x + dx #
            next_y = self.y + dy #

            old_x_col, old_y_col = self.collision_rect.centerx, self.collision_rect.centery #
            
            temp_collision_rect = self.collision_rect.copy() #
            temp_collision_rect.center = (next_x, next_y) #

            collided_with_wall = False #
            if maze: #
                if maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery,
                                self.collision_rect_width, self.collision_rect_height): #
                    collided_with_wall = True #

            if not collided_with_wall: #
                self.x = next_x #
                self.y = next_y #
            else: #
                # Realigning to old collision center might not be the best,
                # as it could cause slight visual jitter if visual rect and collision_rect are different.
                # For simplicity, just stopping movement. Player/Enemy can override.
                self.x = self.collision_rect.centerx - (temp_collision_rect.centerx - self.x) # crude attempt to stay put before collision
                self.y = self.collision_rect.centery - (temp_collision_rect.centery - self.y)
                # More robust: use old_x_col, old_y_col or simply don't update self.x, self.y.
                # self.x, self.y are already at the "before move attempt" state if we don't update them.
                # Let's stick to not updating x,y on collision to avoid complex reversion.
                # The player class has a more specific _handle_wall_collision.
                self.moving_forward = False #

        half_col_width = self.collision_rect_width / 2 #
        half_col_height = self.collision_rect_height / 2 #
        
        # Use constants imported from game_settings for boundaries
        min_x_bound = game_area_x_offset + half_col_width #
        max_x_bound = WIDTH - half_col_width #
        min_y_bound = half_col_height #
        max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height #

        self.x = max(min_x_bound, min(self.x, max_x_bound)) #
        self.y = max(min_y_bound, min(self.y, max_y_bound)) #

        self.rect.center = (int(self.x), int(self.y)) #
        self.collision_rect.center = self.rect.center #


    def draw(self, surface): #
        if self.alive: #
            # If a subclass (like PlayerDrone) properly sets and rotates self.image,
            # this will draw the correct rotated sprite.
            # If self.image is the default Surface([self.size, self.size]), this won't show much.
            # The original draw method had a fallback to draw a triangle, which might be useful
            # for debugging if a subclass fails to set its image.
            if self.image and (self.image.get_width() > 1 or self.image.get_height() > 1): #
                 # Assumes subclasses handle rotation of their specific original_image into self.image
                surface.blit(self.image, self.rect) #
            else: # Fallback for basic drawing if self.image is minimal or not set by subclass
                # Draw a simple triangle if no proper image is set
                points = [ #
                    (self.size / 2, 0),  # Tip
                    (0, self.size),      # Bottom-left
                    (self.size, self.size) # Bottom-right
                ]
                shape_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA) #
                pygame.draw.polygon(shape_surf, CYAN, points) #
                
                rotated_image = pygame.transform.rotate(shape_surf, -self.angle) #
                draw_rect = rotated_image.get_rect(center=self.rect.center) #
                surface.blit(rotated_image, draw_rect) #


    def update(self, maze=None, game_area_x_offset=0): #
        if self.alive: #
            self.update_movement(maze, game_area_x_offset) #
            # Subclasses (like PlayerDrone) will handle rotation of self.image in their own update.
            # BaseDrone's rect is updated in update_movement.
        else: #
            self.kill() # Remove from sprite groups if not alive

    def reset(self, x, y): #
        self.x = float(x) #
        self.y = float(y) #
        self.angle = 0.0 #
        self.alive = True #
        self.moving_forward = False #
        self.rect.center = (int(self.x), int(self.y)) #
        self.collision_rect.center = self.rect.center #