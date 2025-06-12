# hyperdrone_core/ring_puzzle_state.py
import pygame
from .state import State

class RingPuzzleState(State):
    def enter(self, previous_state=None, **kwargs):
        # Initialize puzzle controller if needed
        if hasattr(self.game.puzzle_controller, 'initialize_ring_puzzle'):
            self.game.puzzle_controller.initialize_ring_puzzle()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.puzzle_controller.exit_ring_puzzle(puzzle_was_solved=False)
                else:
                    self.game.puzzle_controller.handle_input(event, "ring_puzzle_active")
    
    def update(self, delta_time):
        if hasattr(self.game.puzzle_controller, 'update_ring_puzzle'):
            self.game.puzzle_controller.update_ring_puzzle(delta_time)
    
    def draw(self, surface):
        # Check if puzzle is active
        if not (self.game.puzzle_controller and self.game.puzzle_controller.ring_puzzle_active_flag):
            surface.fill(self.game.gs.DARK_GREY)
            font = self.game.asset_manager.get_font("medium_text", 48) or pygame.font.Font(None, 48)
            fallback_surf = font.render("Loading Puzzle...", True, self.game.gs.WHITE)
            surface.blit(fallback_surf, fallback_surf.get_rect(
                center=(self.game.gs.get_game_setting("WIDTH") // 2, 
                       self.game.gs.get_game_setting("HEIGHT") // 2)))
        else:
            # Let the puzzle controller draw the puzzle
            self.game.puzzle_controller.draw_ring_puzzle(surface)