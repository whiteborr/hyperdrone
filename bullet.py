import pygame
import math
import os # For path joining if any assets were directly loaded here (not typical for bullets)

# Import necessary constants from game_settings
try:
    from game_settings import (
        PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
        MISSILE_COLOR, MISSILE_SPEED, MISSILE_LIFETIME, MISSILE_SIZE, MISSILE_TURN_RATE, MISSILE_DAMAGE,
        LIGHTNING_COLOR, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE,
        WIDTH, GAME_PLAY_AREA_HEIGHT, TILE_SIZE # For boundary checks and potentially other logic
    )
except ImportError:
    # Fallback values if game_settings.py is not found or constants are missing
    print("Warning (bullet.py): Could not import all constants from game_settings. Using fallbacks.")
    PLAYER_BULLET_COLOR = (255, 200, 0)
    PLAYER_BULLET_SPEED = 7
    PLAYER_BULLET_LIFETIME = 100
    PLAYER_DEFAULT_BULLET_SIZE = 4
    MISSILE_COLOR = (200, 0, 200)
    MISSILE_SPEED = 5
    MISSILE_LIFETIME = 200
    MISSILE_SIZE = 8
    MISSILE_TURN_RATE = 4
    MISSILE_DAMAGE = 50
    LIGHTNING_COLOR = (0, 128, 255)
    LIGHTNING_LIFETIME = 30 # Frames
    LIGHTNING_ZAP_RANGE = 250
    WIDTH = 1920
    GAME_PLAY_AREA_HEIGHT = 1080 - 120
    TILE_SIZE = 80


class Bullet(pygame.sprite.Sprite):
    """Represents a standard projectile."""
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle) # Angle in degrees, 0 is right, positive is CCW
        self.speed = float(speed)
        self.lifetime = int(lifetime) # In frames
        self.size = int(size)
        self.color = color
        self.damage = int(damage)
        self.max_bounces = int(max_bounces)
        self.bounces_done = 0
        self.max_pierces = int(max_pierces)
        self.pierces_done = 0 # Track how many enemies this bullet has pierced
        self.alive = True

        # Create the bullet's image (a simple circle)
        self.image = pygame.Surface([self.size * 2, self.size * 2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.size, self.size), self.size)
        self.rect = self.image.get_rect(center=(self.x, self.y))

        # Calculate movement components based on angle (0 degrees = right)
        rad_angle = math.radians(self.angle)
        self.dx = math.cos(rad_angle) * self.speed
        self.dy = math.sin(rad_angle) * self.speed # Pygame y is inverted by screen coordinates, but math is standard

    def update(self, maze=None, game_area_x_offset=0): # Added game_area_x_offset
        """Updates the bullet's position and state."""
        if not self.alive:
            self.kill() # Ensure removal from sprite groups
            return

        # Move the bullet
        self.x += self.dx
        self.y += self.dy
        self.rect.center = (int(self.x), int(self.y))

        # Decrease lifetime
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            return

        # Boundary checks (simple screen boundaries for now)
        # These boundaries should use game_area_x_offset and GAME_PLAY_AREA_HEIGHT
        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH # Assuming WIDTH is the total screen width
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT

        # Check if bullet is out of bounds
        is_out_of_bounds = not (min_x_bound < self.rect.centerx < max_x_bound and \
                                min_y_bound < self.rect.centery < max_y_bound)

        if is_out_of_bounds:
            if self.bounces_done < self.max_bounces:
                # Simplified bounce off screen edges
                bounced = False
                if self.rect.left < min_x_bound or self.rect.right > max_x_bound:
                    self.dx *= -1
                    self.angle = (180 - self.angle) % 360 # Reflect angle horizontally
                    bounced = True
                if self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
                    self.dy *= -1
                    self.angle = (-self.angle) % 360 # Reflect angle vertically
                    bounced = True
                
                if bounced:
                    self.bounces_done += 1
                    # Nudge bullet back into bounds slightly to prevent sticking
                    self.x = max(min_x_bound + self.size, min(self.x, max_x_bound - self.size))
                    self.y = max(min_y_bound + self.size, min(self.y, max_y_bound - self.size))
                    self.rect.center = (int(self.x), int(self.y))
                else: # If somehow out of bounds but didn't trigger specific edge bounce
                    self.alive = False

            else: # No bounces left
                self.alive = False
            return # Stop further processing if bounced or died at boundary

        # Maze collision for bouncing (if maze is provided and bullet can bounce)
        if maze and self.max_bounces > 0:
            # For maze collision, use the bullet's current position (self.x, self.y)
            # and its size for the check.
            wall_hit_type = maze.is_wall(self.x, self.y, self.size, self.size) # Using self.size for hit check

            if wall_hit_type:
                if self.bounces_done < self.max_bounces:
                    # --- More accurate bounce logic ---
                    # To determine bounce, we ideally need the wall's normal.
                    # A simpler approach: check movement direction against wall.
                    # Create a tiny step back to see which component caused the collision.
                    prev_x_check = self.x - self.dx * 0.1 # Tiny step back
                    prev_y_check = self.y - self.dy * 0.1

                    hit_vertical_wall = False
                    hit_horizontal_wall = False

                    # If moving from prev_x_check to self.x caused a hit, but not if only y changed
                    if maze.is_wall(self.x, prev_y_check, self.size, self.size):
                        hit_vertical_wall = True
                    
                    # If moving from prev_y_check to self.y caused a hit, but not if only x changed
                    if maze.is_wall(prev_x_check, self.y, self.size, self.size):
                        hit_horizontal_wall = True

                    if hit_vertical_wall and not hit_horizontal_wall: # Primarily hit a vertical surface
                        self.dx *= -1
                        self.angle = (180 - self.angle) % 360
                    elif hit_horizontal_wall and not hit_vertical_wall: # Primarily hit a horizontal surface
                        self.dy *= -1
                        self.angle = (-self.angle) % 360
                    else: # Corner hit or ambiguous, reflect both (or use a more complex normal calculation)
                        self.dx *= -1
                        self.dy *= -1
                        self.angle = (self.angle + 180) % 360
                        
                    self.bounces_done += 1
                    # Nudge bullet slightly out of wall to prevent getting stuck
                    self.x += self.dx * 0.1 # Apply a small step in new direction
                    self.y += self.dy * 0.1
                    self.rect.center = (int(self.x), int(self.y))
                else: # Max bounces reached
                    self.alive = False
    
    def draw(self, surface): # Added basic draw method for testing/consistency
        """Draws the bullet on the given surface."""
        if self.alive:
            surface.blit(self.image, self.rect)


class Missile(pygame.sprite.Sprite):
    """Represents a homing missile."""
    def __init__(self, x, y, initial_angle, damage, enemies_group):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = float(initial_angle) # Angle in degrees, 0 is right
        self.speed = MISSILE_SPEED
        self.lifetime = MISSILE_LIFETIME
        self.damage = damage
        self.enemies_group = enemies_group # For targeting
        self.target = None
        self.turn_rate = MISSILE_TURN_RATE # Degrees per frame
        self.alive = True

        # Basic missile image (e.g., a triangle pointing in its angle of motion)
        # Size can be based on MISSILE_SIZE
        self.original_image_surface = pygame.Surface([MISSILE_SIZE * 1.5, MISSILE_SIZE * 2.5], pygame.SRCALPHA)
        # Draw a simple triangle shape for the missile, pointing "up" (0 degrees for the shape)
        # We will rotate this shape according to self.angle
        points = [
            (MISSILE_SIZE * 0.75, 0),                    # Tip
            (0, MISSILE_SIZE * 2.5),                     # Bottom-left
            (MISSILE_SIZE * 1.5, MISSILE_SIZE * 2.5)     # Bottom-right
        ]
        pygame.draw.polygon(self.original_image_surface, MISSILE_COLOR, points)
        
        # The missile sprite should be rotated so that its "tip" (0 degrees for the shape)
        # aligns with self.angle (where 0 degrees is to the right).
        # If the shape points "up" (0, -1 direction), we need to rotate it by -90 degrees
        # initially to make it point right if self.angle is 0.
        self.original_image = pygame.transform.rotate(self.original_image_surface, 90) # Rotate shape to point right initially

        self.image = pygame.transform.rotate(self.original_image, -self.angle) # Initial rotation
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def _find_target(self):
        """Finds the closest living enemy to target."""
        if not self.enemies_group:
            return None
        closest_enemy = None
        min_dist_sq = float('inf')

        for enemy in self.enemies_group:
            if hasattr(enemy, 'alive') and not enemy.alive: # Check if enemy is actually dead
                continue
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        return closest_enemy

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0): # Added game_area_x_offset
        """Updates the missile's position, orientation, and state."""
        if not self.alive:
            self.kill()
            return

        if enemies_group_updated is not None: # Allow updating the enemy group reference
            self.enemies_group = enemies_group_updated

        # Acquire or re-acquire target if current one is dead or None
        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive):
            self.target = self._find_target()

        # Steer towards target if one exists
        if self.target:
            target_x, target_y = self.target.rect.center
            dx_to_target = target_x - self.x
            dy_to_target = target_y - self.y
            
            # Angle to target in degrees (0 is right, positive CCW)
            # math.atan2(y, x) gives angle relative to positive x-axis
            angle_to_target_rad = math.atan2(dy_to_target, dx_to_target)
            angle_to_target_deg = math.degrees(angle_to_target_rad)

            # Normalize current angle and target angle to be within 0-360 or -180 to 180
            current_angle_norm = self.angle % 360
            target_angle_norm = (angle_to_target_deg + 360) % 360 # Ensure positive

            # Calculate the shortest angle to turn
            angle_diff = target_angle_norm - current_angle_norm
            if angle_diff > 180:
                angle_diff -= 360
            elif angle_diff < -180:
                angle_diff += 360

            # Apply turn rate: turn by at most self.turn_rate degrees per frame
            turn_this_frame = max(-self.turn_rate, min(self.turn_rate, angle_diff))
            self.angle = (self.angle + turn_this_frame) % 360
        
        # Move missile forward based on its current angle
        rad_current_angle = math.radians(self.angle)
        self.x += math.cos(rad_current_angle) * self.speed
        self.y += math.sin(rad_current_angle) * self.speed
        
        # Update image rotation and rect
        self.image = pygame.transform.rotate(self.original_image, -self.angle) # Negative for Pygame's rotation
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        # Lifetime and boundary checks
        self.lifetime -= 1
        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT
        if self.lifetime <= 0 or \
           not (min_x_bound < self.rect.centerx < max_x_bound and 
                min_y_bound < self.rect.centery < max_y_bound):
            self.alive = False

    def draw(self, surface): # Added basic draw method
        """Draws the missile on the given surface."""
        if self.alive:
            surface.blit(self.image, self.rect)


class LightningZap(pygame.sprite.Sprite):
    """Represents a lightning zap effect."""
    def __init__(self, start_pos, target_pos, damage, lifetime_frames): # Renamed lifetime to lifetime_frames
        super().__init__()
        self.start_pos = start_pos
        # If no target, zap straight in player's direction (or a default direction)
        # For simplicity, if target_pos is None, we might make it a short zap forward from start_pos
        # This depends on how player.py calls it. Assuming player.py provides a reasonable target_pos.
        self.target_pos = target_pos if target_pos else (start_pos[0] + LIGHTNING_ZAP_RANGE, start_pos[1]) # Default right
        
        self.damage = damage # Damage is applied on hit by game logic, not by the zap itself
        self.lifetime_frames = int(lifetime_frames) # Lifetime in frames
        self.frames_elapsed = 0
        self.alive = True
        self.color = LIGHTNING_COLOR

        # Create a surface that can encompass the lightning bolt
        # The rect of this sprite will be used for collision detection by the game logic
        # For drawing, we'll draw a line on the main screen.
        # For collision, a line segment might be better, or a series of small rects.
        # Here, self.rect will be a line-like rect for simplicity in sprite groups.
        
        # Determine bounding box for the line segment
        all_x = [self.start_pos[0], self.target_pos[0]]
        all_y = [self.start_pos[1], self.target_pos[1]]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)

        # Create a minimal rect for the sprite (e.g., for group management)
        # The actual "hitbox" for lightning is often handled differently (e.g., line segment cast)
        # For now, let's make the rect cover the line for visual grouping.
        rect_width = max(1, max_x - min_x) # Ensure at least 1 pixel wide
        rect_height = max(1, max_y - min_y)
        self.image = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA) # Transparent surface
        self.rect = self.image.get_rect(topleft=(min_x, min_y))
        
        # Store points relative to the sprite's own surface for drawing on it (optional)
        self.local_start = (self.start_pos[0] - min_x, self.start_pos[1] - min_y)
        self.local_target = (self.target_pos[0] - min_x, self.target_pos[1] - min_y)
        
        # Pre-draw a simple representation on its own image (optional, could also draw directly on main screen)
        # pygame.draw.line(self.image, self.color, self.local_start, self.local_target, 3)

    def update(self, current_time_ticks=None): # current_time_ticks is not strictly needed if using frame count
        """Updates the lightning zap's state (e.g., lifetime)."""
        if not self.alive:
            self.kill()
            return

        self.frames_elapsed += 1
        if self.frames_elapsed > self.lifetime_frames:
            self.alive = False
        else:
            # Optional: Update visual effect, like alpha fading
            # For a simple zap, it might just disappear after its lifetime.
            # Example: Fade out
            # alpha = 255 * (1 - (self.frames_elapsed / self.lifetime_frames))
            # self.image.set_alpha(int(max(0, alpha)))
            pass

    def draw(self, surface):
        """Draws the lightning zap on the given surface."""
        if self.alive:
            # For a more dynamic look, redraw the line each frame with slight variations
            # or draw directly on the main surface instead of using self.image.
            # Drawing directly on the main surface:
            current_alpha = 255 * (1 - (self.frames_elapsed / self.lifetime_frames)**2) # Fade out quickly
            current_alpha = int(max(0, min(255, current_alpha)))
            
            if current_alpha > 0:
                # Simple line
                # pygame.draw.line(surface, (*self.color[:3], current_alpha), self.start_pos, self.target_pos, 3)
                
                # Jagged line effect
                self._draw_jagged_line(surface, self.start_pos, self.target_pos, self.color, current_alpha, 3, 5, 10)


    def _draw_jagged_line(self, surface, p1, p2, color, alpha, thickness, num_segments=5, max_offset=10):
        """Helper to draw a jagged line for a more electric look."""
        points = [p1]
        dx_total = p2[0] - p1[0]
        dy_total = p2[1] - p1[1]

        for i in range(1, num_segments):
            t = i / num_segments
            base_x = p1[0] + dx_total * t
            base_y = p1[1] + dy_total * t
            
            # Add random offset perpendicular to the line segment
            # For simplicity, just random x/y offset here
            offset_x = (random.random() - 0.5) * 2 * max_offset
            offset_y = (random.random() - 0.5) * 2 * max_offset
            points.append((base_x + offset_x, base_y + offset_y))
        
        points.append(p2)

        # Draw the segments
        if len(points) > 1:
            try:
                pygame.draw.lines(surface, (*color[:3], alpha), False, points, thickness)
            except TypeError: # If color doesn't have alpha yet
                 pygame.draw.lines(surface, color, False, points, thickness)