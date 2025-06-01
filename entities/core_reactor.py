# entities/core_reactor.py
import pygame
import math # Needed for sin function for pulsing effect
import random # For randomizing pulse start

# It's good practice to import game_settings with an alias if it's used frequently.
# However, for specific constants, direct import can also be clear.
import game_settings as gs
from game_settings import (
    TILE_SIZE, WHITE, RED, GREEN, YELLOW, DARK_GREY
    # Add any other specific constants you might need from game_settings.py later
)

class CoreReactor(pygame.sprite.Sprite):
    def __init__(self, x, y, health=500, size_in_tiles=2):
        """
        Initializes the Core Reactor.

        Args:
            x (int): The x-coordinate of the reactor's center.
            y (int): The y-coordinate of the reactor's center.
            health (int): The maximum and initial health of the reactor.
            size_in_tiles (int): The size of the reactor in terms of game tiles.
                                 For example, 2 means 2x2 tiles.
        """
        super().__init__() # Initialize the parent Sprite class

        # --- Core Attributes ---
        self.x = float(x) # Store position as float for smooth movement if ever needed
        self.y = float(y)
        self.max_health = int(health)
        self.current_health = int(health)
        self.alive = True # Reactor is initially active

        # --- Visuals ---
        self.size = int(TILE_SIZE * size_in_tiles)  # Calculate pixel size based on tiles
        
        # Create the main image surface for the reactor. SRCALPHA allows for transparency.
        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)
        
        # Properties for a simple pulsating visual effect
        self.base_color = (50, 50, 200)  # A deep, stable blue for the core
        self.pulse_color_bright = (100, 150, 255) # Brighter, slightly different hue for pulsing
        self.pulse_speed = 0.03  # Controls how fast the pulse animation runs
        self.pulse_timer = random.uniform(0, math.pi * 2) # Randomize start of pulse for variety if multiple reactors exist
        
        self._draw_reactor_visual()  # Call the method to perform the initial draw of the reactor's appearance

        # Set the rectangle for positioning and collision detection
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) # Ensure rect center is integer
        
        # --- Health Bar Properties ---
        self.health_bar_height = 10  # Pixel height of the health bar
        self.health_bar_width_ratio = 1.0  # Health bar is the same width as the reactor sprite
        self.health_bar_y_offset = 10  # Vertical offset below the reactor sprite

    def _draw_reactor_visual(self):
        """
        Draws the reactor's visual appearance onto its self.image surface.
        This method is called during initialization and in the update loop to animate.
        """
        self.image.fill((0, 0, 0, 0))  # Clear the surface with full transparency for SRCALPHA

        # --- Pulsating Effect Calculation ---
        self.pulse_timer += self.pulse_speed # Increment timer for animation
        if self.pulse_timer > math.pi * 2: # Keep timer within one full sine wave cycle (0 to 2*pi)
            self.pulse_timer -= math.pi * 2
            
        # Use a sine wave to create a smooth pulsing effect (normalized to 0-1 range)
        pulse_factor = (math.sin(self.pulse_timer) + 1) / 2
        
        # Interpolate color based on pulse_factor for a glowing effect
        r = int(self.base_color[0] + (self.pulse_color_bright[0] - self.base_color[0]) * pulse_factor)
        g = int(self.base_color[1] + (self.pulse_color_bright[1] - self.base_color[1]) * pulse_factor)
        b = int(self.base_color[2] + (self.pulse_color_bright[2] - self.base_color[2]) * pulse_factor)
        current_core_color = (r, g, b)

        # --- Drawing the Reactor Shape ---
        # Draw a simple representation (e.g., concentric squares or circles)
        center_x, center_y = self.size // 2, self.size // 2 # Center of the self.image surface
        num_layers = 3 # Number of concentric shapes to draw for a layered look
        
        for i in range(num_layers):
            layer_size_ratio = 1 - i * 0.25 # Layers get smaller towards the center
            layer_size = self.size * layer_size_ratio
            layer_rect = pygame.Rect(0, 0, int(layer_size), int(layer_size)) # Ensure int for rect dimensions
            layer_rect.center = (center_x, center_y) # Center this layer
            
            # Vary alpha for layers to create depth
            layer_alpha = int(200 * (1 - i * 0.3)) # Inner layers more opaque
            layer_color_tuple = current_core_color
            if i % 2 == 1: # Slightly vary color for inner layers for more visual interest
                 layer_color_tuple = (min(255,r+30), min(255,g+30), min(255,b+30))

            # Draw the layer with its calculated color and alpha
            # Pygame's draw.rect on an SRCALPHA surface handles the alpha component of the color correctly.
            pygame.draw.rect(self.image, (*layer_color_tuple, layer_alpha), layer_rect, border_radius=int(self.size * 0.05)) # Small border radius

        # Draw a border around the reactor
        pygame.draw.rect(self.image, WHITE, (0, 0, self.size, self.size), 2, border_radius=int(self.size*0.05))

    def take_damage(self, amount, game_controller_ref=None):
        """
        Reduces the reactor's health by the given amount.
        Args:
            amount (int): The amount of damage to inflict.
            game_controller_ref (GameController, optional): Reference to the main game controller
                                                          to play sounds. Defaults to None.
        """
        if not self.alive: # If already destroyed, do nothing
            return
        
        self.current_health -= amount
        
        # Placeholder for playing a reactor hit sound
        if game_controller_ref and hasattr(game_controller_ref, 'play_sound'):
            game_controller_ref.play_sound('reactor_hit_placeholder') # Replace with actual sound key

        if self.current_health <= 0:
            self.current_health = 0
            self.alive = False
            print("Core Reactor Destroyed! Game Over.") # Log destruction
            
            # Placeholder for playing a reactor destruction sound
            if game_controller_ref and hasattr(game_controller_ref, 'play_sound'):
                game_controller_ref.play_sound('reactor_destroyed_placeholder') # Replace with actual sound key
            
            # The main game loop will check self.alive to trigger game over.

    def draw_health_bar(self, surface):
        """Draws the reactor's health bar on the given surface."""
        # Don't draw if fully destroyed and health is zero (or make it look broken)
        if not self.alive and self.current_health == 0: 
            return

        bar_width = self.size * self.health_bar_width_ratio
        # Position the health bar relative to the reactor's rect
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.bottom + self.health_bar_y_offset 
        
        health_percentage = 0.0 # Default to 0 if max_health is 0
        if self.max_health > 0: # Avoid division by zero
            health_percentage = max(0, self.current_health / self.max_health) # Ensure not negative
        
        filled_width = bar_width * health_percentage
        
        # Draw background of the health bar
        pygame.draw.rect(surface, DARK_GREY, (bar_x, bar_y, bar_width, self.health_bar_height))
        
        # Determine fill color based on health percentage
        fill_color = RED # Low health
        if health_percentage > 0.6:
            fill_color = GREEN # High health
        elif health_percentage > 0.3:
            fill_color = YELLOW # Medium health
            
        if filled_width > 0: # Only draw fill if there's health
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(filled_width), self.health_bar_height))
        
        # Draw border for the health bar
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, self.health_bar_height), 1)

    def update(self):
        """
        Updates the reactor's state each frame.
        Currently used for animating the reactor's visual pulse.
        """
        if self.alive:
            self._draw_reactor_visual() # Redraw to update the pulsating effect

    def draw(self, surface):
        """
        Draws the reactor and its health bar onto the provided surface.
        Args:
            surface (pygame.Surface): The surface to draw on.
        """
        surface.blit(self.image, self.rect) # Draw the reactor sprite
        # Draw health bar if reactor is alive or still has some health (e.g., during destruction animation)
        if self.alive or self.current_health > 0: 
            self.draw_health_bar(surface)

