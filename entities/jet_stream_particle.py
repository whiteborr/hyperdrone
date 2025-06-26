# entities/jetstream_particle.py

from pygame.sprite import Sprite
from pygame.draw import circle
from pygame import Surface, SRCALPHA
from random import choice, uniform
from math import radians, cos, sin

# --- Local Definitions for Colors ---
# These would typically be in a constants file, but are included here for completeness.
FLAME_COLORS = [(255, 100, 0), (255, 150, 0), (255, 200, 50), (255, 80, 0)]
JETSTREAM_COLORS = [(100, 150, 255), (120, 170, 255), (150, 200, 255)]
JETSTREAM_SIDE_COLORS = [(200, 220, 255), (220, 235, 255)]

# --- Base Particle Class (from particle.py) ---
# Included here so this file is self-contained and doesn't depend on another file.

class Particle(Sprite):
    """
    A single particle used for effects like explosions or jetstreams.
    It moves, shrinks, and fades over its lifetime.
    """
    def __init__(self, x, y, color_list, 
                 min_speed, max_speed, 
                 min_size, max_size, 
                 gravity=0.1, shrink_rate=0.1, lifetime_frames=30,
                 base_angle_deg=None, spread_angle_deg=360,
                 x_offset=0, y_offset=0,
                 blast_mode=False):
        """
        Initializes a particle with various properties.
        """
        super().__init__()
        
        self.x, self.y = float(x + x_offset), float(y + y_offset)
        self.blast_mode = blast_mode
        self.lifetime = lifetime_frames

        # --- Set particle properties ---
        if self.blast_mode:
            # Used for explosion-like effects
            self.color = choice(FLAME_COLORS)
            self.size = uniform(min_size, max_size)
            speed = uniform(min_speed, max_speed)
        else:
            # Used for jetstream-like effects
            self.color = choice(color_list)
            self.size = uniform(min_size, max_size)
            speed = uniform(min_speed, max_speed)
            self.gravity = gravity
            self.shrink_rate = shrink_rate

        self.initial_size = self.size
        self.current_lifetime = 0
        
        # --- Calculate initial velocity ---
        angle = base_angle_deg if base_angle_deg is not None else uniform(0, 360)
        angle += uniform(-spread_angle_deg / 2, spread_angle_deg / 2)
        angle_rad = radians(angle)
        
        self.vx, self.vy = cos(angle_rad) * speed, sin(angle_rad) * speed
        
        # --- Create the particle's visual surface ---
        surf_dim = int(self.initial_size * 2) + 2
        self.image = Surface([surf_dim, surf_dim], SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._redraw_image()

    def _redraw_image(self):
        """
        Internal function to draw the particle onto its Surface.
        The alpha value is based on the particle's remaining lifetime.
        """
        self.image.fill((0, 0, 0, 0)) # Transparent background
        center_pos = self.image.get_width() // 2
        draw_size = int(self.size)
        if draw_size < 1:
            return

        # Fade the particle out over its life
        life_ratio = 1.0 - (self.current_lifetime / self.lifetime)
        current_alpha = int(255 * (life_ratio ** 1.5))
        
        if current_alpha > 0:
            draw_color = (*self.color[:3], current_alpha)
            circle(self.image, draw_color, (center_pos, center_pos), draw_size)

    def update(self):
        """
        Updates the particle's position, size, and lifetime each frame.
        The particle is killed when its lifetime expires or it becomes too small.
        """
        self.current_lifetime += 1
        if self.current_lifetime >= self.lifetime:
            self.kill()
            return

        self.x += self.vx
        self.y += self.vy

        if self.blast_mode:
            life_ratio = 1.0 - (self.current_lifetime / self.lifetime)
            self.size = self.initial_size * life_ratio
        else:
            self.size -= self.shrink_rate

        if self.size < 0.5:
            self.kill()
            return
            
        self._redraw_image()
        self.rect.center = (int(self.x), int(self.y))

# --- New Jetstream Manager Class ---

class JetstreamManager:
    """
    Manages a three-stream particle jet effect for a target sprite.
    
    This class creates a central jetstream and two smaller, flanking jetstreams.
    It is not a sprite itself, but rather a manager that creates and holds a group
    of Particle sprites. It should be updated each frame to emit new particles.
    """
    def __init__(self, target, particle_group):
        """
        Initializes the Jetstream manager.
        
        Args:
            target (Sprite): The sprite to attach the jetstream to (e.g., the player).
                             The target must have 'rect' and 'angle' attributes.
            particle_group (Group): The main sprite group to which particles will be added
                                    for rendering and updates.
        """
        self.target = target
        self.particle_group = particle_group
        self.is_active = False

        # --- Configuration for the main jetstream ---
        self.main_jet_config = {
            "color_list": JETSTREAM_COLORS,
            "min_speed": 2.5, "max_speed": 4.5,
            "min_size": 3, "max_size": 6,
            "spread_angle_deg": 25,
            "shrink_rate": 0.15,
            "lifetime_frames": 40
        }

        # --- Configuration for the side jetstreams (smaller and weaker) ---
        self.side_jet_config = {
            "color_list": JETSTREAM_SIDE_COLORS,
            "min_speed": 2.0, "max_speed": 3.5,
            "min_size": 1, "max_size": 4,
            "spread_angle_deg": 20,
            "shrink_rate": 0.12,
            "lifetime_frames": 30
        }
        
        # --- Calculate offsets based on the target's size ---
        # How far behind the target's center the jets originate
        self.rear_offset = self.target.rect.width / 2 if hasattr(self.target, 'rect') else 20
        # How far to the side of the center line the side jets are
        self.side_offset = self.target.rect.width / 3 if hasattr(self.target, 'rect') else 15

    def set_active(self, active_state):
        """Activates or deactivates the jetstream particle emission."""
        self.is_active = active_state

    def update(self):
        """
        Update the jetstream, emitting new particles if active.
        This should be called every frame from the main game loop.
        """
        if not self.is_active or not hasattr(self.target, 'rect') or not hasattr(self.target, 'angle'):
            return

        # Calculate the base angle for the jetstream (opposite to the target's facing angle)
        base_angle_deg = self.target.angle + 180 
        angle_rad = radians(self.target.angle)

        # --- Calculate Emitter Positions ---
        # 1. Find the central point at the rear of the target
        rear_x = self.target.rect.centerx - self.rear_offset * cos(angle_rad)
        rear_y = self.target.rect.centery - self.rear_offset * sin(angle_rad)

        # 2. Emit the central particle for this frame
        self._emit_particle(rear_x, rear_y, base_angle_deg, self.main_jet_config)

        # 3. Find the positions for the side jets using a perpendicular vector
        perp_angle_rad = radians(self.target.angle - 90)
        side_dx = self.side_offset * cos(perp_angle_rad)
        side_dy = self.side_offset * sin(perp_angle_rad)

        # Define points for the two side jets
        left_jet_x, left_jet_y = rear_x - side_dx, rear_y - side_dy
        right_jet_x, right_jet_y = rear_x + side_dx, rear_y + side_dy
        
        # 4. Emit the two side particles for this frame
        self._emit_particle(left_jet_x, left_jet_y, base_angle_deg, self.side_jet_config)
        self._emit_particle(right_jet_x, right_jet_y, base_angle_deg, self.side_jet_config)

    def _emit_particle(self, x, y, base_angle, config):
        """Helper function to create a single particle and add it to the main group."""
        p = Particle(
            x=x, y=y,
            color_list=config["color_list"],
            min_speed=config["min_speed"], max_speed=config["max_speed"],
            min_size=config["min_size"], max_size=config["max_size"],
            shrink_rate=config["shrink_rate"],
            lifetime_frames=config["lifetime_frames"],
            base_angle_deg=base_angle,
            spread_angle_deg=config["spread_angle_deg"]
        )
        self.particle_group.add(p)
