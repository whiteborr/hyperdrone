# entities/jet_stream_particle.py
import pygame
from math import sin, cos, radians
from random import uniform

class JetStreamParticle(pygame.sprite.Sprite):
    """
    A persistent visual effect that creates a jet stream exhaust trail.
    It attaches to a parent sprite (the player drone) and updates its
    position and angle every frame to match.
    """
    def __init__(self, parent_drone, offset_vector):
        """
        Initializes the JetStreamParticle.

        Args:
            parent_drone: The sprite this jet stream is attached to.
            offset_vector: An (x, y) tuple for the stream's position relative 
                           to the parent's center (e.g., (0, 15) for a side engine).
        """
        super().__init__()
        self.parent = parent_drone
        self.offset = pygame.math.Vector2(offset_vector)

        # The image and rect will be created dynamically in the update() method,
        # so we start with a placeholder.
        self.image = pygame.Surface([1, 1], pygame.SRCALPHA)
        self.rect = self.image.get_rect()

    def update(self):
        """
        Recalculates the position, angle, and appearance of the jet stream
        based on the parent drone's current state.
        """
        # Determine the stream's length and intensity based on drone state
        is_cruising = getattr(self.parent, 'is_cruising', False)
        is_boosting = hasattr(self.parent, 'powerup_manager') and self.parent.powerup_manager.speed_boost_active

        if not is_cruising:
            self.image = pygame.Surface([1, 1], pygame.SRCALPHA) # Effectively invisible
            self.rect = self.image.get_rect()
            return
            
        base_length = 120 if is_boosting else 70
        length_variation = uniform(0.95, 1.05)
        current_length = base_length * length_variation

        # Get the drone's current angle and position
        drone_angle_rad = radians(self.parent.angle)
        drone_pos = pygame.math.Vector2(self.parent.rect.center)

        # Rotate the offset vector to find the stream's base position on the drone
        rotated_offset = self.offset.rotate(-self.parent.angle)
        start_pos = drone_pos + rotated_offset

        # Calculate the end position of the stream
        end_pos_x = start_pos.x - cos(drone_angle_rad) * current_length
        end_pos_y = start_pos.y - sin(drone_angle_rad) * current_length
        end_pos = pygame.math.Vector2(end_pos_x, end_pos_y)

        # Dynamically redraw the sprite
        self._redraw(start_pos, end_pos, is_boosting)

    def _redraw(self, start, end, is_boosting):
        """
        Creates the visual representation of the jet stream on a new surface.
        This uses several layered lines to create a glowing effect.
        """
        # Create a surface just large enough to contain the jet stream line
        padding = 20
        min_x, max_x = min(start.x, end.x), max(start.x, end.x)
        min_y, max_y = min(start.y, end.y), max(start.y, end.y)
        width = max_x - min_x + padding
        height = max_y - min_y + padding
        
        self.image = pygame.Surface([width, height], pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(min_x - padding / 2, min_y - padding / 2))

        # Remap global coordinates to the local surface
        local_start = start - self.rect.topleft
        local_end = end - self.rect.topleft

        # Draw the stream with a gradient effect for a "glow"
        outer_width = 14 if is_boosting else 10
        mid_width = 9 if is_boosting else 6
        inner_width = 4 if is_boosting else 2
        
        # 1. Outer glow (Faint Orange)
        pygame.draw.line(self.image, (255, 150, 0, 100), local_start, local_end, outer_width)
        # 2. Middle core (Bright Yellow)
        pygame.draw.line(self.image, (255, 255, 0, 150), local_start, local_end, mid_width)
        # 3. Inner core (Bright White)
        pygame.draw.line(self.image, (255, 255, 255, 200), local_start, local_end, inner_width)


    def draw(self, surface, camera=None):
        # This custom draw method is needed because the rect is already in world coordinates
        if camera:
            surface.blit(self.image, camera.apply_to_rect(self.rect))
        else:
            surface.blit(self.image, self.rect)