# hyperdrone_core/ring_puzzle_module.pyAdd commentMore actions
import pygame
import os
import math
import random
import traceback
import logging

from settings_manager import get_setting

logger = logging.getLogger(__name__)

# Get colors from settings
WHITE = get_setting("colors", "WHITE", (255, 255, 255))
GREEN = get_setting("colors", "GREEN", (0, 255, 0))
DARK_GREY = get_setting("colors", "DARK_GREY", (50, 50, 50))
HIGHLIGHT_GREEN = (100, 255, 100, 100) # Semi-transparent for glow

class Ring:
    def __init__(self, image_filename, segments, screen_center, asset_manager):
        """
        Initializes a single ring for the puzzle.
        Args:
            image_filename (str): The filename of the ring's image (e.g., "ring1.png").
            segments (int): The number of rotational stops for this ring.
            screen_center (tuple): The (x, y) center of the screen.
            asset_manager: The central AssetManager instance.
        """
        self.image_filename = image_filename # For logging
        self.asset_manager = asset_manager
        self.segments = segments
        if self.segments <= 0:
            raise ValueError("Ring segments must be a positive integer.")
        self.rotation_step = 360.0 / self.segments
        self.current_angle = 0.0
        self.screen_center = screen_center

        # Construct the asset key from the filename (e.g., "ring1.png" -> "ring_puzzle_ring1_img")
        base_name = os.path.splitext(image_filename)[0] # "ring1"
        asset_key = f"ring_puzzle_{base_name}_img"

        # Get the pre-loaded image from the asset manager
        self.original_image = self.asset_manager.get_image(asset_key)
        
        # Fallback if the image wasn't loaded
        if self.original_image is None:
            logger.warning(f"Ring '{self.image_filename}': Image for key '{asset_key}' not found. Using fallback.")
            self.original_image = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(self.original_image, (128, 128, 128), (50, 50), 45, 5)
            font = pygame.font.SysFont(None, 20)
            text_surf = font.render("IMG ERR", True, WHITE)
            text_rect = text_surf.get_rect(center=(50,50))
            self.original_image.blit(text_surf, text_rect)

        self.image = self.original_image
        self.rect = self.image.get_rect(center=self.screen_center)


    def rotate(self, clockwise=True):
        old_angle = self.current_angle
        if clockwise:
            self.current_angle += self.rotation_step
        else:
            self.current_angle -= self.rotation_step
        self.current_angle %= 360
        # logger.debug(f"Ring {self.image_filename}: Rotated from {old_angle:.2f} to {self.current_angle:.2f} (step: {self.rotation_step:.2f})")
        
        self.image = pygame.transform.rotate(self.original_image, -self.current_angle)
        self.rect = self.image.get_rect(center=self.screen_center)

    def set_angle(self, angle):
        self.current_angle = angle % 360
        # logger.debug(f"Ring {self.image_filename}: Angle set to {self.current_angle:.2f}")
        self.image = pygame.transform.rotate(self.original_image, -self.current_angle)
        self.rect = self.image.get_rect(center=self.screen_center)

    def is_aligned(self):
        angle_mod_360 = self.current_angle % 360
        return math.isclose(angle_mod_360, 0.0, abs_tol=1e-5) or \
               math.isclose(angle_mod_360, 360.0, abs_tol=1e-5)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class RingPuzzle:
    def __init__(self, screen_width, screen_height, ring_configurations, asset_manager):
        """
        Initializes the Ring Puzzle.
        Args:
            screen_width (int): Width of the screen.
            screen_height (int): Height of the screen.
            ring_configurations (list): List of tuples, e.g., [("ring1.png", 6), ...].
            asset_manager: The central AssetManager instance.
        """
        self.screen_center = (screen_width // 2, screen_height // 2)
        self.asset_manager = asset_manager
        
        if not ring_configurations or len(ring_configurations) == 0:
            raise ValueError("Ring configurations cannot be empty.")
        if len(ring_configurations) > 9: 
            logger.warning("RingPuzzle supports up to 9 rings for direct key control (1-9).")

        self.rings = []
        logger.info("RingPuzzle __init__: Creating rings...")
        for i, config in enumerate(ring_configurations):
            if len(config) != 2:
                raise ValueError(f"Invalid ring configuration for ring {i}: {config}. Expected (filename, segments).")
            image_filename, segments = config
            logger.info(f"RingPuzzle __init__: Creating Ring {i} with image '{image_filename}' and {segments} segments.")
            # Pass the asset_manager to the Ring constructor
            self.rings.append(Ring(image_filename, segments, self.screen_center, self.asset_manager))
        
        self.active = True 
        self.solved_once = False 

        # Get fonts from the AssetManager
        # Using abstract keys that should be defined in GameController's manifest
        self.font = self.asset_manager.get_font("medium_text", 48) # e.g. "medium_text_48"
        self.small_font = self.asset_manager.get_font("small_text", 24) # e.g. "small_text_24"
        
        # Fallback if fonts are not loaded
        if not self.font: self.font = pygame.font.Font(None, 48)
        if not self.small_font: self.small_font = pygame.font.Font(None, 24)

        self.max_ring_dim = 0 
        if self.rings and self.rings[-1].original_image:
            try: 
                last_ring_rect = pygame.transform.rotate(self.rings[-1].original_image, 0).get_rect()
                self.max_ring_dim = max(last_ring_rect.width, last_ring_rect.height) * 1.1
            except AttributeError: 
                 logger.warning("Could not determine max_ring_dim from ring images, using default.")
                 self.max_ring_dim = 300 
        else: 
            self.max_ring_dim = 300 

        if self.max_ring_dim <=0: self.max_ring_dim = 300
        
        self.glow_surface = pygame.Surface((int(self.max_ring_dim), int(self.max_ring_dim)), pygame.SRCALPHA)
        pygame.draw.circle(self.glow_surface, HIGHLIGHT_GREEN, 
                           (int(self.max_ring_dim) // 2, int(self.max_ring_dim) // 2), 
                           int(self.max_ring_dim) // 2, int(self.max_ring_dim * 0.05)) 
        self.glow_rect = self.glow_surface.get_rect(center=self.screen_center)

        self.scramble_rings()
        logger.info(f"RingPuzzle __init__: Initial solved state after scramble: {self.is_solved()}")


    def scramble_rings(self): 
        # (This method's logic remains the same)
        if not self.rings: return
        logger.info("RingPuzzle: Scrambling rings...")
        attempts = 0
        max_attempts = 20

        while attempts < max_attempts:
            for ring_idx, ring in enumerate(self.rings):
                if ring.segments > 1:
                    random_steps = random.randint(1, ring.segments - 1)
                    ring.set_angle(random_steps * ring.rotation_step)
                else:
                    ring.set_angle(0) 
            
            if not self.is_solved(): 
                logger.info(f"RingPuzzle: Rings scrambled.")
                break
            else: 
                logger.info(f"RingPuzzle: Attempt {attempts+1} - Accidentally scrambled to solved state, re-scrambling...")
            attempts += 1
        
        if self.is_solved() and self.rings and self.rings[0].segments > 1: 
            logger.warning("RingPuzzle: Still solved after max scramble attempts, forcing one ring off.")
            self.rings[0].rotate()

        self.active = True
        self.solved_once = False
        logger.info("RingPuzzle: Scramble complete. Puzzle active.")


    def reset(self):
        self.scramble_rings()

    def handle_input(self, event):
        # (This method's logic remains the same)
        if not self.active: return
        if event.type == pygame.KEYDOWN:
            key_to_ring_index = {
                pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
                pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
                pygame.K_7: 6, pygame.K_8: 7, pygame.K_9: 8,
            }
            ring_index_to_rotate = key_to_ring_index.get(event.key)
            if ring_index_to_rotate is not None and ring_index_to_rotate < len(self.rings):
                self.rings[ring_index_to_rotate].rotate(clockwise=True)
                if self.is_solved():
                    self.active = False 
                    self.solved_once = True 
                    logger.info("Ring Puzzle Solved! (from handle_input)")

    def update(self):
        pass 

    def is_solved(self):
        # (This method's logic remains the same)
        if not self.rings: return False
        return all(r.is_aligned() for r in self.rings)

    def draw(self, surface):
        # (This method's logic remains the same)
        for ring in self.rings:
            ring.draw(surface)

        marker_y_start, marker_y_end = 0,0
        if self.rings and self.rings[-1].original_image: 
             outermost_ring_radius = self.rings[-1].original_image.get_height() / 2 
             marker_y_start = self.screen_center[1] - outermost_ring_radius - 10
             marker_y_end = self.screen_center[1] - outermost_ring_radius - 30
             pygame.draw.line(surface, GREEN, (self.screen_center[0], marker_y_start), (self.screen_center[0], marker_y_end), 3)
        else: 
            pygame.draw.line(surface, GREEN, (self.screen_center[0], self.screen_center[1] - 50), (self.screen_center[0], self.screen_center[1] - 70), 3)

        if self.solved_once: 
            if not self.active : 
                surface.blit(self.glow_surface, self.glow_rect)
            text_surface = self.font.render("SOLVED!", True, GREEN)
            text_rect = text_surface.get_rect(center=(self.screen_center[0], self.screen_center[1]))
            surface.blit(text_surface, text_rect)
        elif self.active:
            instructions = "Align symbols to the top marker."
            num_active_rings = len(self.rings)
            if num_active_rings > 0 and num_active_rings <=3 :
                instructions += f" Keys 1-{num_active_rings} rotate rings."
            elif num_active_rings > 0 :
                instructions += " Use number keys to rotate rings."
            else:
                instructions = " (Error: No rings configured for puzzle interaction)"

            instr_surf = self.small_font.render(instructions, True, WHITE)
            current_max_ring_dim = self.max_ring_dim if hasattr(self, 'max_ring_dim') and self.max_ring_dim > 0 else 300
            bottom_of_puzzle_y = self.screen_center[1] + (int(current_max_ring_dim) // 2) + 20
            instr_rect = instr_surf.get_rect(center=(self.screen_center[0], bottom_of_puzzle_y + 20 ))
            surface.blit(instr_surf, instr_rect)

if __name__ == '__main__':
    pygame.init()
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Ring Puzzle Test")
    clock = pygame.time.Clock()

    # --- MOCK ASSET MANAGER FOR TESTING ---
    class MockAssetManager:
        def __init__(self):
            self.images = {}
            self.fonts = {}
        def get_image(self, key):
            logger.debug(f"MockAssetManager: Requesting image with key '{key}'")
            return self.images.get(key)
        def get_font(self, key, size):
            cache_key = f"{key}_{size}"
            if cache_key in self.fonts:
                return self.fonts[cache_key]
            try: # Fallback to system font for testing
                font = pygame.font.Font(None, size)
                self.fonts[cache_key] = font
                return font
            except:
                return None
    
    mock_asset_manager = MockAssetManager()

    dummy_ring_configs = []
    ring_colors = [(255,100,100), (100,255,100), (100,100,255)]
    ring_base_size = 100
    for i in range(3):
        filename = f"ring{i+1}.png"
        segments = [6, 8, 10][i] 
        dummy_ring_configs.append((filename, segments))
        
        ring_size = ring_base_size + i * 80 
        img_surf = pygame.Surface((ring_size, ring_size), pygame.SRCALPHA)
        pygame.draw.circle(img_surf, ring_colors[i], (ring_size // 2, ring_size // 2), ring_size // 2 - 5, 10)
        marker_font = pygame.font.SysFont(None, int(ring_size*0.15))
        for seg_idx in range(segments):
            angle_deg = (seg_idx / segments) * 360; angle_rad = math.radians(angle_deg - 90) 
            radius_for_symbol = ring_size // 2 - 25 
            x_pos = ring_size // 2 + radius_for_symbol * math.cos(angle_rad)
            y_pos = ring_size // 2 + radius_for_symbol * math.sin(angle_rad)
            symbol_char = "●" if seg_idx == 0 else chr(65 + seg_idx)
            symbol_surf = marker_font.render(symbol_char, True, WHITE)
            symbol_rect = symbol_surf.get_rect(center=(int(x_pos), int(y_pos)))
            img_surf.blit(symbol_surf, symbol_rect)
        
        # Add the generated surface to the mock asset manager
        asset_key_for_test = f"ring_puzzle_ring{i+1}_img"
        mock_asset_manager.images[asset_key_for_test] = img_surf

    logger.info(f"Mock Asset Manager populated with {len(mock_asset_manager.images)} test images.")

    try:
        # Initialize the puzzle with the mock asset manager
        puzzle = RingPuzzle(screen_width, screen_height, dummy_ring_configs, asset_manager=mock_asset_manager)
        puzzle_active_in_game = True 
    except Exception as e:
        logger.error(f"Failed to initialize puzzle for testing: {e}")
        traceback.print_exc()
        pygame.quit()
        exit()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if event.key == pygame.K_r: 
                    logger.info("--- Resetting puzzle from test block ---")
                    puzzle.reset()
            if puzzle_active_in_game: puzzle.handle_input(event)

        if puzzle_active_in_game: puzzle.update()
        screen.fill(DARK_GREY) 
        if puzzle_active_in_game: puzzle.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()