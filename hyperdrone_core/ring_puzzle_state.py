# hyperdrone_core/ring_puzzle_state.py
from pygame.font import Font
from pygame import KEYDOWN, K_ESCAPE
from .state import State
from settings_manager import get_setting

class RingPuzzleState(State):
    def enter(self, previous_state=None, **kwargs):
        # Initialize puzzle controller if needed
        if hasattr(self.game.puzzle_controller, 'initialize_ring_puzzle'):
            self.game.puzzle_controller.initialize_ring_puzzle()
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.game.puzzle_controller.exit_ring_puzzle(puzzle_was_solved=False)
                else:
                    self.game.puzzle_controller.handle_input(event, "ring_puzzle_active")
    
    def update(self, delta_time):
        if hasattr(self.game.puzzle_controller, 'update_ring_puzzle'):
            self.game.puzzle_controller.update_ring_puzzle(delta_time)
    
    def draw(self, surface):
        # Check if puzzle is active
        if not (self.game.puzzle_controller and self.game.puzzle_controller.ring_puzzle_active_flag):
            dark_grey = get_setting("colors", "DARK_GREY", (50, 50, 50))
            white = get_setting("colors", "WHITE", (255, 255, 255))
            width = get_setting("display", "WIDTH", 1920)
            height = get_setting("display", "HEIGHT", 1080)
            
            surface.fill(dark_grey)
            font = self.game.asset_manager.get_font("medium_text", 48) or Font(None, 48)
            fallback_surf = font.render("Loading Puzzle...", True, white)
            surface.blit(fallback_surf, fallback_surf.get_rect(
                center=(width // 2, height // 2)))
        else:
            # Let the puzzle controller draw the puzzle
            self.game.puzzle_controller.draw_ring_puzzle(surface)
