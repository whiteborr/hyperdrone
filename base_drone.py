import pygame
import math

# It's good practice to have fallback default values or import them
# from game_settings if they are universally applicable.
# For now, using some common defaults.
try:
    from game_settings import PLAYER_SPEED, TILE_SIZE, WIDTH, GAME_PLAY_AREA_HEIGHT, CYAN
except ImportError:
    # Fallback values if game_settings.py is not found or constants are missing
    # These should ideally match your project's defaults.
    PLAYER_SPEED = 3
    TILE_SIZE = 80
    WIDTH = 1920
    GAME_PLAY_AREA_HEIGHT = 1080 - 120 # Example, assuming bottom panel
    CYAN = (0, 255, 255)


class BaseDrone(pygame.sprite.Sprite):
    def __init__(self, x, y, size=None, speed=None): # Made size and speed optional with fallbacks
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        
        # Use provided size or default to TILE_SIZE * 0.8 (consistent with player's _load_sprite)
        self.size = float(size) if size is not None else TILE_SIZE * 0.8
        # Use provided speed or default to PLAYER_SPEED
        self.speed = float(speed) if speed is not None else PLAYER_SPEED
        
        self.angle = 0.0  # Initial angle (0 degrees usually means facing right)
        self.alive = True
        self.moving_forward = False # State for movement

        # Basic image and rect for Pygame sprite group functionality
        # Subclasses (like Player's Drone) will typically override self.image with their own sprites.
        # This provides a default visual if a subclass doesn't load its own image immediately.
        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)
        # Fill with a transparent color or a simple placeholder shape
        # For example, a semi-transparent circle:
        # pygame.draw.circle(self.image, (*CYAN, 128), (self.size // 2, self.size // 2), self.size // 2)
        self.rect = self.image.get_rect(center=(self.x, self.y))

        # Collision rect can be defined here, often slightly smaller than visual rect
        # Subclasses might want to refine this based on their specific shape.
        self.collision_rect_width = self.rect.width * 0.7
        self.collision_rect_height = self.rect.height * 0.7
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center

    def rotate(self, direction, rotation_speed):
        """
        Rotates the drone.
        'left' for Counter-Clockwise (CCW), 'right' for Clockwise (CW).
        This assumes self.angle where 0 is right, positive is CCW.
        """
        if direction == "left":
            self.angle += rotation_speed
        elif direction == "right":
            self.angle -= rotation_speed
        self.angle %= 360  # Keep angle within 0-359 degrees

    def update_movement(self, maze=None, game_area_x_offset=0): # Added game_area_x_offset
        """
        Updates the drone's position based on its speed and angle,
        with optional maze collision handling and boundary checks.
        """
        if self.moving_forward and self.alive:
            angle_rad = math.radians(self.angle)
            # In Pygame, positive y is down.
            # Standard math: cos for x, sin for y.
            # If angle 0 is right: dx = cos, dy = sin
            # If angle 0 is up (like in original player): dx = sin, dy = -cos
            # Assuming angle 0 is right for this base class, consistent with player's dynamic draw
            dx = math.cos(angle_rad) * self.speed
            dy = math.sin(angle_rad) * self.speed

            next_x = self.x + dx
            next_y = self.y + dy

            # Use collision_rect for more accurate collision detection
            # Store old position in case of collision to revert
            old_x_col, old_y_col = self.collision_rect.centerx, self.collision_rect.centery
            
            # Tentatively update collision_rect position for checking
            temp_collision_rect = self.collision_rect.copy()
            temp_collision_rect.center = (next_x, next_y) # Center collision rect at potential new x,y

            collided_with_wall = False
            if maze:
                # Check wall collision using the center of the temp_collision_rect
                # and its dimensions.
                if maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery,
                                self.collision_rect_width, self.collision_rect_height):
                    collided_with_wall = True

            if not collided_with_wall:
                self.x = next_x
                self.y = next_y
            else:
                # Basic collision response: stop movement or revert slightly
                # More sophisticated response (sliding) could be added.
                self.x = old_x_col - (self.collision_rect.width - self.collision_rect_width)/2 # Realign x to old collision center
                self.y = old_y_col - (self.collision_rect.height - self.collision_rect_height)/2 # Realign y
                self.moving_forward = False # Stop movement on collision

        # Boundary checks
        # Use collision_rect dimensions for boundary checks
        half_col_width = self.collision_rect_width / 2
        half_col_height = self.collision_rect_height / 2
        
        # Define min/max based on game area
        # These should ideally come from game_settings
        min_x_bound = game_area_x_offset + half_col_width
        max_x_bound = WIDTH - half_col_width # Assumes WIDTH is full screen/game area width
        min_y_bound = half_col_height
        max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height # Use defined game play area height

        self.x = max(min_x_bound, min(self.x, max_x_bound))
        self.y = max(min_y_bound, min(self.y, max_y_bound))

        # Update the visual rect and collision_rect after all position adjustments
        self.rect.center = (int(self.x), int(self.y))
        self.collision_rect.center = self.rect.center


    def draw(self, surface):
        """
        Basic draw method for BaseDrone.
        Subclasses (like Player's Drone) should override this with their specific sprite.
        This draws a simple shape if self.image is not otherwise set by a subclass.
        """
        if self.alive:
            # If self.image was loaded by a subclass, it will be rotated there.
            # If not, this provides a very basic rotated representation.
            if self.image.get_width() <=1 or self.image.get_height() <=1 : # Check if image is just a placeholder pixel
                 # Draw a simple triangle if no proper image is set
                points = [
                    (self.size / 2, 0),  # Tip
                    (0, self.size),      # Bottom-left
                    (self.size, self.size) # Bottom-right
                ]
                # Create a temporary surface for the basic shape
                shape_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                pygame.draw.polygon(shape_surf, CYAN, points) # Use a default color
                
                rotated_image = pygame.transform.rotate(shape_surf, -self.angle)
                draw_rect = rotated_image.get_rect(center=self.rect.center)
                surface.blit(rotated_image, draw_rect)
            else:
                # If a subclass has set self.image (and likely rotated it in its update), just blit it.
                # This assumes the subclass's update method handles rotation of self.image.
                surface.blit(self.image, self.rect)


    def update(self, maze=None, game_area_x_offset=0): # Added game_area_x_offset
        """
        Basic update method for a BaseDrone.
        Calls movement update. Subclasses can extend this.
        """
        if self.alive:
            self.update_movement(maze, game_area_x_offset)
            # Ensure rect is updated after movement
            self.rect.center = (int(self.x), int(self.y))
            self.collision_rect.center = self.rect.center
        else:
            self.kill() # Remove from sprite groups if not alive

    def reset(self, x, y):
        """
        Resets the drone's basic state.
        """
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.alive = True
        self.moving_forward = False
        # self.speed remains as initialized, or could be reset to a default if needed.
        self.rect.center = (int(self.x), int(self.y))
        self.collision_rect.center = self.rect.center
        # Health and other specific attributes should be reset by the subclass (e.g., Player's Drone)