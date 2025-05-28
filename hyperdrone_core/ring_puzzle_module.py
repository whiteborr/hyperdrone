# ring_puzzle_module.py
import pygame
import os
import math
import random
import traceback

# Define some colors (can be replaced with your game_settings if available)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
DARK_GREY = (50, 50, 50)
HIGHLIGHT_GREEN = (100, 255, 100, 100) # Semi-transparent for glow

class Ring:
    def __init__(self, image_filename, segments, screen_center, assets_path="assets/images/puzzles/"):
        self.image_filename = image_filename # For logging
        self.segments = segments
        if self.segments <= 0:
            raise ValueError("Ring segments must be a positive integer.")
        self.rotation_step = 360.0 / self.segments
        self.current_angle = 0.0
        self.screen_center = screen_center

        image_path = os.path.join(assets_path, image_filename)
        try:
            self.original_image = pygame.image.load(image_path).convert_alpha()
            print(f"Ring {self.image_filename}: Loaded image successfully from {image_path}")
        except pygame.error as e:
            print(f"Ring {self.image_filename}: Error loading image '{image_path}': {e}. Using fallback.")
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
        print(f"Ring {self.image_filename}: Rotated from {old_angle:.2f} to {self.current_angle:.2f} (step: {self.rotation_step:.2f})")
        
        self.image = pygame.transform.rotate(self.original_image, -self.current_angle)
        self.rect = self.image.get_rect(center=self.screen_center)

    def set_angle(self, angle):
        self.current_angle = angle % 360
        print(f"Ring {self.image_filename}: Angle set to {self.current_angle:.2f}")
        self.image = pygame.transform.rotate(self.original_image, -self.current_angle)
        self.rect = self.image.get_rect(center=self.screen_center)

    def is_aligned(self):
        angle_mod_360 = self.current_angle % 360
        aligned = math.isclose(angle_mod_360, 0.0, abs_tol=1e-5) or \
                  math.isclose(angle_mod_360, 360.0, abs_tol=1e-5)
        # print(f"Ring {self.image_filename}: is_aligned check: current_angle={self.current_angle:.2f}, angle_mod_360={angle_mod_360:.2f}, aligned={aligned}")
        return aligned

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class RingPuzzle:
    def __init__(self, screen_width, screen_height, ring_configurations, assets_path="assets/images/puzzles/"):
        self.screen_center = (screen_width // 2, screen_height // 2)
        self.assets_path = assets_path
        
        if not ring_configurations or len(ring_configurations) == 0:
            raise ValueError("Ring configurations cannot be empty.")
        if len(ring_configurations) > 9: 
            print("Warning: RingPuzzle supports up to 9 rings for direct key control (1-9).")

        self.rings = []
        print("RingPuzzle __init__: Creating rings...")
        for i, config in enumerate(ring_configurations):
            if len(config) != 2:
                raise ValueError(f"Invalid ring configuration for ring {i}: {config}. Expected (filename, segments).")
            image_filename, segments = config
            print(f"RingPuzzle __init__: Creating Ring {i} with image '{image_filename}' and {segments} segments.")
            self.rings.append(Ring(image_filename, segments, self.screen_center, self.assets_path))
        
        self.active = True 
        self.solved_once = False 

        try:
            self.font = pygame.font.Font(None, 48) 
            self.small_font = pygame.font.Font(None, 24)
        except Exception as e:
            print(f"Could not load default font for puzzle: {e}")
            self.font = pygame.font.SysFont('arial', 48) 
            self.small_font = pygame.font.SysFont('arial', 24)

        self.max_ring_dim = 0 
        if self.rings and self.rings[-1].original_image:
            try: 
                last_ring_rect = pygame.transform.rotate(self.rings[-1].original_image, 0).get_rect()
                self.max_ring_dim = max(last_ring_rect.width, last_ring_rect.height) * 1.1
            except AttributeError: 
                 print("Warning: Could not determine max_ring_dim from ring images, using default.")
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
        print(f"RingPuzzle __init__: Initial solved state after scramble: {self.is_solved()}")


    def scramble_rings(self): 
        if not self.rings: return
        print("RingPuzzle: Scrambling rings...")
        attempts = 0
        max_attempts = 20 # Increased attempts just in case

        while attempts < max_attempts:
            for ring_idx, ring in enumerate(self.rings):
                if ring.segments > 1:
                    random_steps = random.randint(1, ring.segments - 1) # Ensure it's not 0 initially
                    ring.set_angle(random_steps * ring.rotation_step)
                else: # Ring with 1 segment is always "aligned"
                    ring.set_angle(0) 
            
            if not self.is_solved(): 
                print(f"RingPuzzle: Rings scrambled. Final Angles: {[f'{r.image_filename}: {r.current_angle:.2f}' for r in self.rings]}")
                break
            else: 
                print(f"RingPuzzle: Attempt {attempts+1} - Accidentally scrambled to solved state, re-scrambling...")
            attempts += 1
        
        if self.is_solved() and self.rings: 
            print("RingPuzzle: Still solved after max scramble attempts, forcing one ring off.")
            if self.rings[0].segments > 1:
                self.rings[0].rotate() # Nudge the first ring off alignment
                print(f"RingPuzzle: Nudged ring 0. New Angles: {[f'{r.image_filename}: {r.current_angle:.2f}' for r in self.rings]}")


        self.active = True
        self.solved_once = False
        print("RingPuzzle: Scramble complete. Puzzle active.")


    def reset(self):
        self.scramble_rings()

    def handle_input(self, event):
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
                print(f"RingPuzzle: Key {event.key} pressed, rotating ring {ring_index_to_rotate}.")
                self.rings[ring_index_to_rotate].rotate(clockwise=True)
                
                if self.is_solved(): # Check solution immediately after rotation
                    self.active = False 
                    self.solved_once = True 
                    print("Ring Puzzle Solved! (from handle_input)")

    def update(self):
        pass 

    def is_solved(self):
        if not self.rings: 
            print("RingPuzzle is_solved: No rings to check.")
            return False
        
        # print("RingPuzzle is_solved check:")
        all_r_aligned = True
        for i, r in enumerate(self.rings):
            aligned_status = r.is_aligned()
            # print(f"  Ring {i} ({r.image_filename}): Angle={r.current_angle:.2f}, Aligned={aligned_status}")
            if not aligned_status:
                all_r_aligned = False
                # break # Optimization: if one is not aligned, no need to check others
        # print(f"RingPuzzle is_solved: Overall result = {all_r_aligned}")
        return all_r_aligned

    def draw(self, surface):
        for ring in self.rings:
            ring.draw(surface)

        marker_y_start, marker_y_end = 0,0 # Default values

        if self.rings and self.rings[-1].original_image: 
             outermost_ring_height = self.rings[-1].original_image.get_height()
             outermost_ring_radius = outermost_ring_height / 2 
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
            
            # Use self.max_ring_dim for positioning instructions
            current_max_ring_dim = self.max_ring_dim if hasattr(self, 'max_ring_dim') and self.max_ring_dim > 0 else 300
            bottom_of_puzzle_y = self.screen_center[1] + (int(current_max_ring_dim) // 2) + 20
            instr_rect = instr_surf.get_rect(center=(self.screen_center[0], bottom_of_puzzle_y + 20 ))
            surface.blit(instr_surf, instr_rect)

if __name__ == '__main__':
    pygame.init()
    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Ring Puzzle Test")
    clock = pygame.time.Clock()

    assets_base = "assets"
    puzzle_assets_path = os.path.join(assets_base, "images", "puzzles") 
    if not os.path.exists(puzzle_assets_path):
        os.makedirs(puzzle_assets_path)

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
            angle_deg = (seg_idx / segments) * 360
            angle_rad = math.radians(angle_deg - 90) 
            radius_for_symbol = ring_size // 2 - 25 
            x = ring_size // 2 + radius_for_symbol * math.cos(angle_rad)
            y = ring_size // 2 + radius_for_symbol * math.sin(angle_rad)
            symbol_char = chr(65 + seg_idx) 
            if seg_idx == 0: 
                symbol_surf = marker_font.render("●", True, WHITE)
            else:
                symbol_surf = marker_font.render(symbol_char, True, WHITE)
            symbol_rect = symbol_surf.get_rect(center=(int(x), int(y)))
            img_surf.blit(symbol_surf, symbol_rect)
        try:
            pygame.image.save(img_surf, os.path.join(puzzle_assets_path, filename))
        except Exception as e:
            print(f"Error saving dummy image {filename}: {e}")
            traceback.print_exc() # Add traceback here too

    print(f"Dummy ring images created/updated in {puzzle_assets_path} for testing.")

    try:
        puzzle = RingPuzzle(screen_width, screen_height, dummy_ring_configs, assets_path=puzzle_assets_path)
        puzzle_active_in_game = True 
    except Exception as e:
        print(f"Failed to initialize puzzle for testing: {e}")
        traceback.print_exc()
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
                if event.key == pygame.K_r: 
                    print("--- Resetting puzzle from test block ---")
                    puzzle.reset() # Calls scramble_rings again
                    print(f"Puzzle active after reset: {puzzle.active}")
            
            if puzzle_active_in_game: 
                puzzle.handle_input(event)

        if puzzle_active_in_game:
            puzzle.update()

        screen.fill(DARK_GREY) 
        if puzzle_active_in_game:
            puzzle.draw(screen)
        
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()