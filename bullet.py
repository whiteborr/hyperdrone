# bullet.py
import pygame
import math
from game_settings import (
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
    MISSILE_COLOR, MISSILE_SPEED, MISSILE_LIFETIME, MISSILE_SIZE, MISSILE_TURN_RATE,
    LIGHTNING_COLOR, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE, TILE_SIZE,
    WIDTH, GAME_PLAY_AREA_HEIGHT # For boundary checks
)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle)
        self.speed = float(speed)
        self.lifetime = int(lifetime) # In frames
        self.size = int(size)
        self.color = color
        self.damage = int(damage)
        self.max_bounces = int(max_bounces)
        self.bounces_done = 0
        self.max_pierces = int(max_pierces)
        self.pierces_done = 0
        self.alive = True

        self.image = pygame.Surface([self.size * 2, self.size * 2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.size, self.size), self.size)
        self.rect = self.image.get_rect(center=(self.x, self.y))

        rad_angle = math.radians(self.angle)
        self.dx = math.sin(rad_angle) * self.speed
        self.dy = -math.cos(rad_angle) * self.speed # Pygame y is inverted

    def update(self, maze=None): # Maze needed for bouncing
        if not self.alive:
            self.kill() # Remove from all groups
            return

        self.x += self.dx
        self.y += self.dy
        self.rect.center = (self.x, self.y)
        self.lifetime -= 1

        if self.lifetime <= 0:
            self.alive = False
            return

        # Boundary checks (simple screen boundaries for now)
        # game_area_x_offset is assumed to be 0 for bullets originating from player
        if not (0 < self.rect.centerx < WIDTH and 0 < self.rect.centery < GAME_PLAY_AREA_HEIGHT):
            if self.bounces_done < self.max_bounces:
                # A more sophisticated bounce would reflect based on which boundary was hit
                # For simplicity, let's just reverse direction if it hits a generic boundary
                # This is a placeholder for proper wall collision bouncing
                if self.rect.left < 0 or self.rect.right > WIDTH:
                    self.dx *= -1
                    self.angle = (180 - self.angle) % 360 # Approximate angle reflection
                if self.rect.top < 0 or self.rect.bottom > GAME_PLAY_AREA_HEIGHT:
                    self.dy *= -1
                    self.angle = (-self.angle) % 360 # Approximate angle reflection
                self.bounces_done += 1
            else:
                self.alive = False
            return # Stop further processing if bounced or died

        # Maze collision for bouncing (simplified)
        if maze and self.max_bounces > 0:
            # Create a small rect for the bullet tip for more precise collision
            tip_rect = pygame.Rect(self.x - self.size/2, self.y - self.size/2, self.size, self.size)
            
            wall_hit_type = maze.is_wall(tip_rect.centerx, tip_rect.centery, self.size, self.size)

            if wall_hit_type: # If it hits any wall defined by the maze
                if self.bounces_done < self.max_bounces:
                    # Determine bounce direction based on wall orientation (simplified)
                    # This is a very basic bounce logic.
                    # A proper bounce needs to know the normal of the wall hit.
                    # For now, we'll assume horizontal or vertical walls.
                    
                    # Check if primarily horizontal or vertical movement led to collision
                    # This is a heuristic. Better to check wall normal.
                    collided_horizontally = False
                    collided_vertically = False

                    # Check collision with a slightly pushed back position to see which component caused it
                    prev_x, prev_y = self.x - self.dx, self.y - self.dy
                    if maze.is_wall(prev_x, self.y, self.size, self.size): # Likely vertical wall
                        collided_horizontally = True
                    if maze.is_wall(self.x, prev_y, self.size, self.size): # Likely horizontal wall
                        collided_vertically = True
                    
                    if collided_horizontally and not collided_vertically : # Hit a vertical wall
                        self.dx *= -1
                        self.angle = (180 - self.angle) % 360 
                    elif collided_vertically and not collided_horizontally: # Hit a horizontal wall
                        self.dy *= -1
                        self.angle = (-self.angle) % 360
                    else: # Corner hit or ambiguous, reverse both (or just die)
                        self.dx *= -1
                        self.dy *= -1
                        self.angle = (self.angle + 180) % 360
                        
                    self.bounces_done += 1
                    # Move bullet slightly out of wall to prevent getting stuck
                    self.x += self.dx * 0.5 
                    self.y += self.dy * 0.5
                    self.rect.center = (self.x, self.y)
                else:
                    self.alive = False


class Missile(pygame.sprite.Sprite):
    def __init__(self, x, y, initial_angle, damage, enemies_group):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = float(initial_angle)
        self.speed = MISSILE_SPEED
        self.lifetime = MISSILE_LIFETIME
        self.damage = damage
        self.enemies_group = enemies_group # For targeting
        self.target = None
        self.turn_rate = MISSILE_TURN_RATE
        self.alive = True

        # Basic missile image
        self.original_image = pygame.Surface([MISSILE_SIZE * 2, MISSILE_SIZE * 3], pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, MISSILE_COLOR, 
                            [(MISSILE_SIZE, 0), (0, MISSILE_SIZE*3), (MISSILE_SIZE*2, MISSILE_SIZE*3)])
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def _find_target(self):
        if not self.enemies_group:
            return None
        closest_enemy = None
        min_dist_sq = float('inf')
        for enemy in self.enemies_group:
            if hasattr(enemy, 'alive') and not enemy.alive: continue # Skip dead enemies
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        return closest_enemy

    def update(self, enemies_group_updated=None, maze=None): # maze for potential future wall collision
        if not self.alive:
            self.kill()
            return

        if enemies_group_updated is not None: # Allow updating the enemy group reference
            self.enemies_group = enemies_group_updated

        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive):
            self.target = self._find_target()

        if self.target:
            target_dx = self.target.rect.centerx - self.x
            target_dy = self.target.rect.centery - self.y
            target_angle = math.degrees(math.atan2(-target_dx, -target_dy)) # Note: atan2 for y,x then adjust
            
            # Normalize angles to be between 0 and 360
            current_angle_norm = self.angle % 360
            target_angle_norm = (target_angle + 360) % 360

            # Calculate shortest angle to turn
            angle_diff = target_angle_norm - current_angle_norm
            if angle_diff > 180: angle_diff -= 360
            if angle_diff < -180: angle_diff += 360

            # Apply turn rate
            turn_amount = max(-self.turn_rate, min(self.turn_rate, angle_diff))
            self.angle += turn_amount
            self.angle %= 360


        rad_angle = math.radians(self.angle)
        self.x += math.sin(rad_angle) * self.speed
        self.y -= math.cos(rad_angle) * self.speed
        
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(self.x, self.y))

        self.lifetime -= 1
        if self.lifetime <= 0 or not (0 < self.rect.centerx < WIDTH and 0 < self.rect.centery < GAME_PLAY_AREA_HEIGHT):
            self.alive = False


class LightningZap(pygame.sprite.Sprite):
    def __init__(self, start_pos, target_pos, damage, lifetime):
        super().__init__()
        self.start_pos = start_pos
        self.target_pos = target_pos if target_pos else (start_pos[0], start_pos[1] - LIGHTNING_ZAP_RANGE) # Default straight if no target
        self.damage = damage
        self.lifetime = lifetime # In frames
        self.alive = True
        self.color = LIGHTNING_COLOR
        self.creation_time = pygame.time.get_ticks()

        # Create a surface that can encompass the lightning bolt
        # This is a simplified visual; a proper one would use multiple segments or a texture
        max_x = max(self.start_pos[0], self.target_pos[0])
        min_x = min(self.start_pos[0], self.target_pos[0])
        max_y = max(self.start_pos[1], self.target_pos[1])
        min_y = min(self.start_pos[1], self.target_pos[1])
        
        width = max_x - min_x + 10 # Add padding
        height = max_y - min_y + 10 # Add padding
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(min_x - 5, min_y - 5))

        # Draw the lightning bolt relative to the surface's top-left
        local_start = (self.start_pos[0] - self.rect.left, self.start_pos[1] - self.rect.top)
        local_target = (self.target_pos[0] - self.rect.left, self.target_pos[1] - self.rect.top)
        
        # Simple line for now, can be made jagged
        pygame.draw.line(self.image, self.color, local_start, local_target, 3)
        # Add some "glow" or particles
        pygame.draw.circle(self.image, self.color, local_start, 5)
        pygame.draw.circle(self.image, self.color, local_target, 5)


    def update(self, current_time): # current_time passed from GameController
        if not self.alive:
            self.kill()
            return

        # Fade out effect (optional) or just time-based disappearance
        if current_time - self.creation_time > self.lifetime:
            self.alive = False
        else:
            # Pulsing alpha effect
            alpha_pulse = abs(math.sin((current_time - self.creation_time) * 0.02)) # Faster pulse for zap
            alpha = 100 + int(alpha_pulse * 155) # Range 100-255
            self.image.set_alpha(alpha)

