# entities/turret.py
import pygame
import math
import random

import game_settings as gs
from game_settings import (
    TILE_SIZE, WHITE, RED, GREEN, YELLOW, DARK_GREY, CYAN, GOLD,
    PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
    PLAYER_BULLET_COLOR, WEAPON_MODES_SEQUENCE 
)
try:
    from .bullet import Bullet
except ImportError:
    print("Warning (turret.py): Could not import Bullet from .bullet. Using placeholder.")
    # Minimal placeholder if Bullet class is not found (should not happen in full project)
    class Bullet(pygame.sprite.Sprite): 
        def __init__(self, x, y, angle, speed, lifetime, size, color, damage, 
                     bounces=0, pierces=0, can_pierce_walls=False):
            super().__init__()
            self.image = pygame.Surface([size*2, size*2]) # Create a simple square image
            self.image.fill(color)
            self.rect = self.image.get_rect(center=(x,y))
            self.alive = True
            self.lifetime = lifetime
            self.damage = damage 
            # Minimal update for placeholder
        def update(self, maze, offset): self.lifetime -=1; _ = maze; _ = offset;  
        def draw(self, surface): surface.blit(self.image, self.rect)


class Turret(pygame.sprite.Sprite):
    TURRET_COST = gs.get_game_setting("TURRET_BASE_COST", 50) # Get from game_settings
    UPGRADE_COST = gs.get_game_setting("TURRET_UPGRADE_COST", 100) # Get from game_settings
    BASE_RANGE = TILE_SIZE * 3
    BASE_FIRE_RATE = 1000  # Milliseconds
    BASE_DAMAGE = 10
    MAX_UPGRADE_LEVEL = gs.get_game_setting("TURRET_MAX_UPGRADE_LEVEL", 3) # Get from game_settings

    def __init__(self, x, y, game_controller_ref):
        """
        Initializes a Turret.
        Args:
            x (int): Center x-coordinate.
            y (int): Center y-coordinate.
            game_controller_ref: Reference to the main game controller for accessing sounds, etc.
        """
        super().__init__()
        self.x = float(x) # Store position as float for precise calculations
        self.y = float(y)
        self.game_controller_ref = game_controller_ref # For accessing global game elements like sounds

        self.size = int(TILE_SIZE * 0.8) # Visual size of the turret base
        self.turret_base_color = (100, 100, 120) # Default base color
        self.turret_barrel_color = (150, 150, 170) # Default barrel color
        self.turret_upgrade_colors = [ # Colors to indicate upgrade level
            (100, 100, 120), # Level 0
            (100, 150, 120), # Level 1 (e.g., greenish)
            (150, 150, 100), # Level 2 (e.g., yellowish)
            (180, 100, 100)  # Level 3 (e.g., reddish/powerful)
        ]


        self.angle = 0  # Angle in degrees, 0 is typically right
        self.target = None # Current enemy target
        self.upgrade_level = 0 # Initial upgrade level

        # This flag is controlled by BuildMenu to show range when turret is selected
        self.show_range_indicator = False 

        self._apply_upgrade_stats() # Set initial stats based on level 0

        # Randomize initial shot time slightly to prevent all turrets firing in perfect sync
        self.last_shot_time = pygame.time.get_ticks() - random.randint(0, int(self.fire_rate)) 
        
        self.bullets = pygame.sprite.Group() # Group to manage bullets fired by this turret

        # Create the turret's visual representation
        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA) # Use SRCALPHA for transparency
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) # Ensure center is int
        self._draw_turret() # Initial draw after all necessary attributes are set

    def _apply_upgrade_stats(self):
        """Applies stats based on the current upgrade_level."""
        # Example: Range increases with each upgrade level
        self.range = self.BASE_RANGE + (self.upgrade_level * TILE_SIZE * 0.5)
        # Example: Fire rate (cooldown) decreases (fires faster)
        self.fire_rate = float(self.BASE_FIRE_RATE * (0.85 ** self.upgrade_level))
        # Example: Damage increases
        self.damage = self.BASE_DAMAGE * (1.25 ** self.upgrade_level)
        
        print(f"Turret ({self.x:.0f},{self.y:.0f}) stats Lvl {self.upgrade_level}. Range: {self.range:.0f}, FireRate: {self.fire_rate:.0f}ms, Dmg: {self.damage:.1f}")


    def _draw_turret(self):
        """Draws the turret on its self.image surface, including base and barrel."""
        self.image.fill((0, 0, 0, 0))  # Clear with transparency

        # Draw turret base (e.g., a rounded rectangle)
        base_rect_size = self.size
        base_rect = pygame.Rect(0, 0, base_rect_size, base_rect_size)
        base_rect.center = (self.size // 2, self.size // 2) # Center on the turret's own surface
        
        # Get color based on upgrade level
        current_base_color = self.turret_upgrade_colors[min(self.upgrade_level, len(self.turret_upgrade_colors)-1)]
        pygame.draw.rect(self.image, current_base_color, base_rect, border_radius=int(base_rect_size*0.1))
        pygame.draw.rect(self.image, WHITE, base_rect, 1, border_radius=int(base_rect_size*0.1)) # Outline


        # Draw turret barrel
        barrel_length = self.size * 0.6 # Barrel extends from center
        barrel_width = self.size * 0.15 # Thickness of the barrel
        
        # Calculate barrel end point based on current angle
        # Barrel starts at the center of the turret's image
        center_of_image_x = self.size // 2
        center_of_image_y = self.size // 2
        
        barrel_end_x = center_of_image_x + barrel_length * math.cos(math.radians(self.angle))
        barrel_end_y = center_of_image_y + barrel_length * math.sin(math.radians(self.angle))
        
        # Draw the barrel line
        pygame.draw.line(self.image, self.turret_barrel_color, 
                         (center_of_image_x, center_of_image_y), 
                         (barrel_end_x, barrel_end_y), 
                         int(barrel_width))
        # Optional: Draw a small circle at the base of the barrel for a more finished look
        pygame.draw.circle(self.image, self.turret_barrel_color, (center_of_image_x, center_of_image_y), int(barrel_width*1.2)) 

        # Note: The range indicator circle is drawn by UIManager/BuildMenu directly on the main screen,
        # not on the turret's self.image, so it doesn't rotate with the turret.

    def find_target(self, enemies_group):
        """Finds the closest enemy within range."""
        self.target = None 
        closest_enemy = None
        min_dist_sq = self.range ** 2 # Use squared distance for efficiency

        for enemy in enemies_group:
            if not enemy.alive: # Skip dead enemies
                continue
            
            # Calculate squared distance from turret to enemy
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        
        self.target = closest_enemy # Assign the found target (or None if no enemy in range)

    def aim_at_target(self):
        """Aims the turret barrel at the current target by updating self.angle."""
        if self.target and self.target.alive:
            dx = self.target.rect.centerx - self.x
            dy = self.target.rect.centery - self.y
            self.angle = math.degrees(math.atan2(dy, dx)) # Update angle
            self._draw_turret() # Redraw the turret with the new barrel angle
            return True # Aimed successfully
        return False # No valid target to aim at

    def shoot(self):
        """Fires a bullet at the current target if conditions are met (cooldown, target exists)."""
        current_time = pygame.time.get_ticks()
        if self.target and self.target.alive and (current_time - self.last_shot_time > int(self.fire_rate)):
            self.last_shot_time = current_time

            # Calculate bullet spawn position (e.g., from the tip of the barrel)
            barrel_tip_offset = self.size * 0.3 # Adjust as needed for visual barrel length
            spawn_x = self.x + barrel_tip_offset * math.cos(math.radians(self.angle))
            spawn_y = self.y + barrel_tip_offset * math.sin(math.radians(self.angle))

            # Define bullet properties (could be influenced by turret upgrades)
            bullet_speed = PLAYER_BULLET_SPEED * 0.8 # Turret bullets might be slightly slower
            bullet_lifetime = PLAYER_BULLET_LIFETIME * 0.7
            bullet_size = PLAYER_DEFAULT_BULLET_SIZE * 0.8
            bullet_color = GOLD # Or a specific turret bullet color
            
            new_bullet = Bullet(
                spawn_x, spawn_y, self.angle, # Fire in the direction the turret is aimed
                bullet_speed, bullet_lifetime, int(bullet_size), bullet_color,
                int(self.damage) # Use the turret's current damage
            )
            self.bullets.add(new_bullet) # Add to the turret's bullet group
            
            # Play shooting sound via game_controller
            if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'):
                self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.3) # Use a specific turret sound

    def upgrade(self):
        """Upgrades the turret if possible, improving its stats."""
        if self.upgrade_level < self.MAX_UPGRADE_LEVEL:
            self.upgrade_level += 1
            self._apply_upgrade_stats() # Re-calculate stats based on new level
            self._draw_turret() # Redraw turret to reflect potential visual changes (e.g., color)
            print(f"Turret at ({self.x:.0f},{self.y:.0f}) upgraded to level {self.upgrade_level}.")
            return True 
        print(f"Turret at ({self.x:.0f},{self.y:.0f}) is already max level {self.MAX_UPGRADE_LEVEL}.")
        return False


    def update(self, enemies_group, maze_ref, game_area_x_offset=0):
        """
        Updates the turret's logic: find target, aim, shoot, update bullets.
        Args:
            enemies_group (pygame.sprite.Group): Group of active enemies.
            maze_ref (Maze or MazeChapter2): The current maze instance for bullet collision.
            game_area_x_offset (int): The x-offset of the game area.
        """
        self.find_target(enemies_group)
        if self.aim_at_target(): # If aiming was successful (target found)
            self.shoot() # Attempt to shoot
        
        self.bullets.update(maze_ref, game_area_x_offset) # Update all bullets fired by this turret


    def draw(self, surface):
        """Draws the turret and its bullets."""
        surface.blit(self.image, self.rect) # Draw the turret itself
        self.bullets.draw(surface) # Draw all active bullets from this turret

        # The actual drawing of the range indicator when a turret is selected
        # is handled by the UIManager or BuildMenu, drawing directly onto the main screen,
        # so it's not part of the turret's rotated image.
        # Example of how it might be drawn by an external manager:
        # if self.show_range_indicator and self.game_controller_ref.is_build_phase:
        #    pygame.draw.circle(surface, (*CYAN[:3], 70), self.rect.center, int(self.range), 2)
