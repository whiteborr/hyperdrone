# ring_puzzle_module.py
import pygame
import os
import math
import random

# Define some colors (can be replaced with your game_settings if available)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
DARK_GREY = (50, 50, 50)
HIGHLIGHT_GREEN = (100, 255, 100, 100) # Semi-transparent for glow

class Ring:
    """
    Manages a single rotatable ring in the puzzle.
    """
    def __init__(self, image_filename, segments, screen_center, assets_path="assets/images/puzzles/"):
        """
        Initializes a Ring object.

        Args:
            image_filename (str): The filename of the ring image (e.g., "ring1.png").
            segments (int): The number of distinct segments or positions this ring can snap to.
            screen_center (tuple): A tuple (x, y) for the center of the screen/puzzle.
            assets_path (str): The base path to the puzzle assets.
        """
        self.segments = segments
        if self.segments <= 0:
            raise ValueError("Ring segments must be a positive integer.")
        self.rotation_step = 360.0 / self.segments
        self.current_angle = 0.0  # Angle in degrees

        image_path = os.path.join(assets_path, image_filename)
        try:
            self.original_image = pygame.image.load(image_path).convert_alpha()
        except pygame.error as e:
            print(f"Error loading ring image '{image_path}': {e}")
            # Create a fallback surface if image loading fails
            self.original_image = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(self.original_image, (128, 128, 128), (50, 50), 45, 5)
            font = pygame.font.SysFont(None, 20)
            text_surf = font.render("IMG ERR", True, WHITE)
            text_rect = text_surf.get_rect(center=(50,50))
            self.original_image.blit(text_surf, text_rect)


        self.image = self.original_image
        self.rect = self.image.get_rect(center=screen_center)
        self.screen_center = screen_center

    def rotate(self, clockwise=True):
        """
        Rotates the ring by one segment step.

        Args:
            clockwise (bool): True to rotate clockwise, False for counter-clockwise.
        """
        if clockwise:
            self.current_angle += self.rotation_step
        else:
            self.current_angle -= self.rotation_step
        
        self.current_angle %= 360 # Keep angle within 0-359.99... degrees

        # Update the visual representation
        self.image = pygame.transform.rotate(self.original_image, -self.current_angle) # Pygame rotates counter-clockwise
        self.rect = self.image.get_rect(center=self.screen_center)

    def set_angle(self, angle):
        """
        Sets the ring to a specific angle and updates its visual representation.
        """
        self.current_angle = angle % 360
        self.image = pygame.transform.rotate(self.original_image, -self.current_angle)
        self.rect = self.image.get_rect(center=self.screen_center)

    def is_aligned(self):
        """
        Checks if the ring is at its original rotation (angle = 0).
        Uses a small tolerance for floating point comparisons.
        """
        return math.isclose(self.current_angle % 360, 0.0, abs_tol=1e-5) or \
               math.isclose(self.current_angle % 360, 360.0, abs_tol=1e-5)


    def draw(self, surface):
        """
        Draws the ring onto the given surface.

        Args:
            surface (pygame.Surface): The surface to draw on.
        """
        surface.blit(self.image, self.rect)

class RingPuzzle:
    """
    Manages the collection of rings and the overall puzzle logic.
    """
    def __init__(self, screen_width, screen_height, ring_configurations, assets_path="assets/images/puzzles/"):
        """
        Initializes the RingPuzzle.

        Args:
            screen_width (int): The width of the game screen.
            screen_height (int): The height of the game screen.
            ring_configurations (list): A list of tuples, where each tuple contains:
                                        (image_filename_str, num_segments_int).
                                        Example: [("ring1.png", 6), ("ring2.png", 8), ("ring3.png", 12)]
            assets_path (str): Path to the puzzle image assets.
        """
        self.screen_center = (screen_width // 2, screen_height // 2)
        self.assets_path = assets_path
        
        if not ring_configurations or len(ring_configurations) == 0:
            raise ValueError("Ring configurations cannot be empty.")
        if len(ring_configurations) > 9: # Max keys 1-9
            print("Warning: RingPuzzle supports up to 9 rings for direct key control (1-9).")

        self.rings = []
        for i, config in enumerate(ring_configurations):
            if len(config) != 2:
                raise ValueError(f"Invalid ring configuration for ring {i}: {config}. Expected (filename, segments).")
            image_filename, segments = config
            self.rings.append(Ring(image_filename, segments, self.screen_center, self.assets_path))
        
        self.active = True  # Puzzle can be interacted with
        self.solved_once = False # To control the solved message persistence

        # Basic font for solved message (can be customized)
        try:
            self.font = pygame.font.Font(None, 48) # Default font
            self.small_font = pygame.font.Font(None, 24)
        except Exception as e:
            print(f"Could not load default font for puzzle: {e}")
            self.font = pygame.font.SysFont('arial', 48) # System fallback
            self.small_font = pygame.font.SysFont('arial', 24)


        # Pre-render a glow surface for solved state
        max_ring_dim = 0
        if self.rings:
            last_ring_rect = pygame.transform.rotate(self.rings[-1].original_image, 0).get_rect()
            max_ring_dim = max(last_ring_rect.width, last_ring_rect.height) * 1.1 # Slightly larger than the outermost ring
        
        self.glow_surface = pygame.Surface((max_ring_dim, max_ring_dim), pygame.SRCALPHA)
        pygame.draw.circle(self.glow_surface, HIGHLIGHT_GREEN, 
                           (max_ring_dim // 2, max_ring_dim // 2), 
                           max_ring_dim // 2, int(max_ring_dim * 0.05)) # Glow thickness relative to size
        self.glow_rect = self.glow_surface.get_rect(center=self.screen_center)

        self.scramble_rings()

    def scramble_rings(self):
        """
        Randomly rotates each ring to ensure the puzzle isn't solved initially.
        Ensures that the puzzle is not initially in a solved state.
        """
        all_aligned = True
        for ring in self.rings:
            random_steps = random.randint(0, ring.segments - 1)
            ring.set_angle(random_steps * ring.rotation_step)
            if not ring.is_aligned():
                all_aligned = False
        
        # If by sheer chance all rings ended up aligned, misalign at least one
        if all_aligned and self.rings:
            self.rings[0].rotate() 
            if self.rings[0].is_aligned() and ring.segments > 1: # if it rotated back to 0
                 self.rings[0].rotate()


        self.active = True
        self.solved_once = False

    def reset(self):
        """
        Resets the puzzle to a new scrambled state.
        """
        self.scramble_rings()

    def handle_input(self, event):
        """
        Processes Pygame events to handle puzzle input.
        Call this from your main game loop's event handling section.

        Args:
            event (pygame.event.Event): The Pygame event to process.
        """
        if not self.active:
            return

        if event.type == pygame.KEYDOWN:
            key_to_ring_index = {
                pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
                pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
                pygame.K_7: 6, pygame.K_8: 7, pygame.K_9: 8,
            }
            
            ring_index_to_rotate = key_to_ring_index.get(event.key)

            if ring_index_to_rotate is not None and ring_index_to_rotate < len(self.rings):
                # For simplicity, each key press rotates clockwise.
                # You could add Shift+Key for counter-clockwise or use other keys.
                self.rings[ring_index_to_rotate].rotate(clockwise=True)
                if self.is_solved():
                    self.active = False # Stop further interaction once solved
                    self.solved_once = True
                    print("Ring Puzzle Solved!") # Or trigger a game event

    def update(self):
        """
        Update method for the puzzle. 
        Currently, key presses are handled in `handle_input`.
        This can be used for animations or other continuous updates if needed.
        """
        # If visual feedback on solve needs continuous update (e.g. pulsing glow),
        # it would go here. For now, it's a static change on solve.
        pass

    def is_solved(self):
        """
        Checks if all rings are aligned to their original position (angle 0).

        Returns:
            bool: True if the puzzle is solved, False otherwise.
        """
        if not self.rings: # Should not happen if initialized correctly
            return False
        return all(ring.is_aligned() for ring in self.rings)

    def draw(self, surface):
        """
        Draws all rings of the puzzle onto the given surface.
        Also draws visual feedback if the puzzle is solved.

        Args:
            surface (pygame.Surface): The surface to draw on.
        """
        # Optional: Draw a background for the puzzle area
        # puzzle_area_rect = pygame.Rect(0, 0, self.screen_center[0]*1.5, self.screen_center[1]*1.5)
        # puzzle_area_rect.center = self.screen_center
        # pygame.draw.rect(surface, DARK_GREY, puzzle_area_rect, border_radius=10)

        for ring in self.rings:
            ring.draw(surface)

        # Draw alignment marker (simple line at the top for now)
        marker_start = (self.screen_center[0], self.screen_center[1] - self.rings[0].original_image.get_height() // 2 - 20)
        marker_end = (self.screen_center[0], self.screen_center[1] - self.rings[-1].original_image.get_height() // 2 - 50) # Outermost ring + buffer
        if self.rings: # Ensure rings exist
             outermost_ring_radius = self.rings[-1].original_image.get_width() / 2
             marker_start = (self.screen_center[0], self.screen_center[1] - outermost_ring_radius - 10)
             marker_end = (self.screen_center[0], self.screen_center[1] - outermost_ring_radius - 30)
             pygame.draw.line(surface, GREEN, marker_start, marker_end, 3)


        if self.solved_once: # Show solved message/feedback persistently after first solve
            # Draw solved glow
            surface.blit(self.glow_surface, self.glow_rect)
            
            # Draw "SOLVED!" message
            text_surface = self.font.render("SOLVED!", True, GREEN)
            text_rect = text_surface.get_rect(center=(self.screen_center[0], self.screen_center[1]))
            surface.blit(text_surface, text_rect)
        elif self.active:
            # You could draw instructions here if needed
            instructions = "Align symbols to the top marker. Keys 1-3 rotate rings."
            if len(self.rings) > 3:
                 instructions = f"Align symbols. Keys 1-{len(self.rings)} rotate rings."

            instr_surf = self.small_font.render(instructions, True, WHITE)
            instr_rect = instr_surf.get_rect(center=(self.screen_center[0], self.screen_center[1] + self.rings[-1].original_image.get_height()//2 + 40 ))
            surface.blit(instr_surf, instr_rect)


if __name__ == '__main__':
    # Example Usage (requires Pygame to be initialized and ring images to exist)
    pygame.init()
    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Ring Puzzle Test")
    clock = pygame.time.Clock()

    # --- IMPORTANT: Create Dummy Ring Images for Testing ---
    # Create a dummy assets/images/puzzles directory if it doesn't exist
    assets_base = "assets"
    puzzle_assets_path = os.path.join(assets_base, "images", "puzzles")
    if not os.path.exists(puzzle_assets_path):
        os.makedirs(puzzle_assets_path)

    # Create dummy ring images
    dummy_ring_configs = []
    ring_colors = [(255,100,100), (100,255,100), (100,100,255)]
    ring_base_size = 100
    for i in range(3):
        filename = f"ring{i+1}.png"
        segments = [6, 8, 10][i] # Example segments
        dummy_ring_configs.append((filename, segments))
        
        ring_size = ring_base_size + i * 80 # Increase size for outer rings
        img_surf = pygame.Surface((ring_size, ring_size), pygame.SRCALPHA)
        
        # Draw the ring itself (a thick circle)
        pygame.draw.circle(img_surf, ring_colors[i], (ring_size // 2, ring_size // 2), ring_size // 2 - 5, 10)

        # Draw segment markers or symbols (simple lines for this dummy image)
        # One of these symbols should visually represent the "0 angle" or "solved" position
        # For this test, we'll put a distinct marker at the "top" (0 degrees in image space)
        marker_font = pygame.font.SysFont(None, int(ring_size*0.15))

        for seg_idx in range(segments):
            angle_deg = (seg_idx / segments) * 360
            angle_rad = math.radians(angle_deg - 90) # -90 to make 0 deg at top for drawing
            
            radius_for_symbol = ring_size // 2 - 25 # Position symbols inside the ring band
            
            x = ring_size // 2 + radius_for_symbol * math.cos(angle_rad)
            y = ring_size // 2 + radius_for_symbol * math.sin(angle_rad)

            symbol_char = chr(65 + seg_idx) # A, B, C...
            if seg_idx == 0: # Distinctive marker for the "solved" segment
                symbol_surf = marker_font.render("●", True, WHITE) # A filled circle
            else:
                symbol_surf = marker_font.render(symbol_char, True, WHITE)
            
            symbol_rect = symbol_surf.get_rect(center=(int(x), int(y)))

            # Rotate symbol text to be upright (optional, can be complex)
            # For dummy, just blit as is. Real symbols would be part of the ring image.
            img_surf.blit(symbol_surf, symbol_rect)

        pygame.image.save(img_surf, os.path.join(puzzle_assets_path, filename))
    print(f"Dummy ring images created in {puzzle_assets_path} for testing.")
    # --- End Dummy Image Creation ---


    # Initialize the puzzle (make sure dummy_ring_configs matches your created files)
    # Example: ring_configs = [("ring1.png", 6), ("ring2.png", 8), ("ring3.png", 10)]
    try:
        puzzle = RingPuzzle(screen_width, screen_height, dummy_ring_configs, assets_path=puzzle_assets_path)
        puzzle_active_in_game = True # Simulate being in the puzzle mini-game state
    except Exception as e:
        print(f"Failed to initialize puzzle for testing: {e}")
        pygame.quit()
        exit()


    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r: # Reset key for testing
                    puzzle.reset()
                    print("Puzzle Reset.")
            
            if puzzle_active_in_game: # Only process puzzle input if it's the active game state
                puzzle.handle_input(event)

        if puzzle_active_in_game:
            puzzle.update()

        screen.fill(DARK_GREY) # Background color
        if puzzle_active_in_game:
            puzzle.draw(screen)
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()