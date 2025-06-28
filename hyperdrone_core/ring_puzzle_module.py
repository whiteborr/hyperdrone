# hyperdrone_core/ring_puzzle_module.py
from pygame import Surface, SRCALPHA, KEYDOWN, K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9
from pygame.draw import circle, line
from pygame.font import Font
from pygame.transform import rotate
from os.path import splitext
from math import isclose
from random import randint
from logging import getLogger

from settings_manager import get_setting

logger = getLogger(__name__)

# Colors
WHITE = get_setting("colors", "WHITE", (255, 255, 255))
GREEN = get_setting("colors", "GREEN", (0, 255, 0))
HIGHLIGHT_GREEN = (100, 255, 100, 100)

class Ring:
    def __init__(self, image_filename, segments, screen_center, asset_manager):
        self.image_filename = image_filename
        self.asset_manager = asset_manager
        self.segments = max(1, segments)  # Ensure positive
        self.rotation_step = 360.0 / self.segments
        self.current_angle = 0.0
        self.screen_center = screen_center

        # Load image
        base_name = splitext(image_filename)[0]
        asset_key = f"ring_puzzle_{base_name}_img"
        self.original_image = self.asset_manager.get_image(asset_key)
        
        # Fallback if image not found
        if not self.original_image:
            logger.warning(f"Ring '{image_filename}': Image not found, using fallback")
            self.original_image = self._create_fallback_image()

        self.image = self.original_image
        self.rect = self.image.get_rect(center=screen_center)

    def _create_fallback_image(self):
        img = Surface((100, 100), SRCALPHA)
        circle(img, (128, 128, 128), (50, 50), 45, 5)
        font = Font(None, 20)
        text = font.render("IMG ERR", True, WHITE)
        img.blit(text, text.get_rect(center=(50, 50)))
        return img

    def rotate(self, clockwise=True):
        if clockwise:
            self.current_angle += self.rotation_step
        else:
            self.current_angle -= self.rotation_step
        self.current_angle %= 360
        self._update_image()

    def set_angle(self, angle):
        self.current_angle = angle % 360
        self._update_image()

    def _update_image(self):
        self.image = rotate(self.original_image, -self.current_angle)
        self.rect = self.image.get_rect(center=self.screen_center)

    def is_aligned(self):
        angle = self.current_angle % 360
        return isclose(angle, 0.0, abs_tol=1e-5) or isclose(angle, 360.0, abs_tol=1e-5)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class RingPuzzle:
    def __init__(self, screen_width, screen_height, ring_configurations, asset_manager):
        self.screen_center = (screen_width // 2, screen_height // 2)
        self.asset_manager = asset_manager
        
        if not ring_configurations:
            raise ValueError("Ring configurations cannot be empty")
        if len(ring_configurations) > 9:
            logger.warning("RingPuzzle supports up to 9 rings for key control (1-9)")

        # Create rings
        self.rings = []
        for i, (filename, segments) in enumerate(ring_configurations):
            self.rings.append(Ring(filename, segments, self.screen_center, asset_manager))
        
        self.active = True 
        self.solved_once = False 

        # Setup fonts
        self.font = asset_manager.get_font("medium_text", 48) or Font(None, 48)
        self.small_font = asset_manager.get_font("small_text", 24) or Font(None, 24)

        # Setup glow effect
        self._setup_glow_effect()
        
        # Scramble initial state
        self.scramble_rings()

    def _setup_glow_effect(self):
        # Calculate max ring dimension
        max_dim = 300  # Default
        if self.rings and self.rings[-1].original_image:
            try:
                last_ring = self.rings[-1].original_image
                max_dim = max(last_ring.get_width(), last_ring.get_height()) * 1.1
            except AttributeError:
                pass
        
        self.max_ring_dim = max(max_dim, 300)
        
        # Create glow surface
        size = int(self.max_ring_dim)
        self.glow_surface = Surface((size, size), SRCALPHA)
        circle(self.glow_surface, HIGHLIGHT_GREEN, (size // 2, size // 2), size // 2, int(size * 0.05))
        self.glow_rect = self.glow_surface.get_rect(center=self.screen_center)

    def scramble_rings(self):
        if not self.rings:
            return
            
        logger.info("Scrambling rings...")
        
        for attempt in range(20):  # Max attempts
            for ring in self.rings:
                if ring.segments > 1:
                    random_steps = randint(1, ring.segments - 1)
                    ring.set_angle(random_steps * ring.rotation_step)
                else:
                    ring.set_angle(0)
            
            if not self.is_solved():
                break
        
        # Force one ring off if still solved
        if self.is_solved() and self.rings and self.rings[0].segments > 1:
            self.rings[0].rotate()

        self.active = True
        self.solved_once = False

    def reset(self):
        self.scramble_rings()

    def handle_input(self, event):
        if not self.active or event.type != KEYDOWN:
            return
            
        # Map keys to ring indices
        key_map = {
            K_1: 0, K_2: 1, K_3: 2, K_4: 3, K_5: 4,
            K_6: 5, K_7: 6, K_8: 7, K_9: 8
        }
        
        ring_index = key_map.get(event.key)
        if ring_index is not None and ring_index < len(self.rings):
            self.rings[ring_index].rotate(clockwise=True)
            if self.is_solved():
                self.active = False 
                self.solved_once = True 
                logger.info("Ring Puzzle Solved!")

    def update(self):
        pass

    def is_solved(self):
        return self.rings and all(ring.is_aligned() for ring in self.rings)

    def draw(self, surface):
        # Draw rings
        for ring in self.rings:
            ring.draw(surface)

        # Draw alignment marker
        self._draw_alignment_marker(surface)

        # Draw status and instructions
        if self.solved_once:
            if not self.active:
                surface.blit(self.glow_surface, self.glow_rect)
            text = self.font.render("SOLVED!", True, GREEN)
            surface.blit(text, text.get_rect(center=self.screen_center))
        elif self.active:
            self._draw_instructions(surface)

    def _draw_alignment_marker(self, surface):
        if self.rings and self.rings[-1].original_image:
            radius = self.rings[-1].original_image.get_height() / 2
            start_y = self.screen_center[1] - radius - 10
            end_y = self.screen_center[1] - radius - 30
        else:
            start_y = self.screen_center[1] - 50
            end_y = self.screen_center[1] - 70
            
        line(surface, GREEN, (self.screen_center[0], start_y), (self.screen_center[0], end_y), 3)

    def _draw_instructions(self, surface):
        num_rings = len(self.rings)
        if num_rings == 0:
            instructions = "(Error: No rings configured)"
        elif num_rings <= 3:
            instructions = f"Align symbols to the top marker. Keys 1-{num_rings} rotate rings."
        else:
            instructions = "Align symbols to the top marker. Use number keys to rotate rings."

        text = self.small_font.render(instructions, True, WHITE)
        y_pos = self.screen_center[1] + (int(self.max_ring_dim) // 2) + 40
        surface.blit(text, text.get_rect(center=(self.screen_center[0], y_pos)))