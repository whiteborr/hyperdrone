# hyperdrone_core/state_transition_viewer.pyAdd commentMore actions
import pygame
import time
from datetime import datetime

class StateTransitionViewer:
    """
    A utility class to visualize state transitions for debugging and development.
    Can be used to display the state transition history in a graphical format.
    """
    def __init__(self, registry, screen_width=800, screen_height=600):
        """
        Initialize the state transition viewer.
        
        Args:
            registry: The state registry instance
            screen_width: Width of the viewer window
            screen_height: Height of the viewer window
        """
        self.registry = registry
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = None
        self.font = None
        self.title_font = None
        self.initialized = False
        
    def initialize(self):
        """Initialize pygame and create the viewer window"""
        if not pygame.get_init():
            pygame.init()
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("HYPERDRONE State Transition Viewer")
        
        self.font = pygame.font.SysFont("Arial", 14)
        self.title_font = pygame.font.SysFont("Arial", 24, bold=True)
        
        self.initialized = True
        
    def show(self):
        """Show the state transition history in a graphical window"""
        if not self.initialized:
            self.initialize()
            
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            self.screen.fill((30, 30, 40))
            self._draw_transition_history()
            self._draw_state_graph()
            pygame.display.flip()
            
        pygame.quit()
        
    def _draw_transition_history(self):
        """Draw the transition history as a list"""
        # Draw title
        title = self.title_font.render("State Transition History", True, (255, 255, 255))
        self.screen.blit(title, (20, 20))
        
        # Get the transition history
        history = self.registry.get_transition_history()
        
        # Draw the history entries
        y_pos = 60
        for i, (from_state, to_state, timestamp) in enumerate(reversed(history[-20:])):
            time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            text = f"{time_str}: {from_state or 'None'} -> {to_state}"
            color = (200, 200, 200) if i % 2 == 0 else (170, 170, 170)
            text_surface = self.font.render(text, True, color)
            self.screen.blit(text_surface, (20, y_pos))
            y_pos += 25
            
    def _draw_state_graph(self):
        """Draw a simple graph of state transitions"""
        # Draw title
        title = self.title_font.render("State Transition Graph", True, (255, 255, 255))
        self.screen.blit(title, (self.screen_width // 2, 20))
        
        # This is a placeholder for a more sophisticated graph visualization
        # In a real implementation, you would use a graph layout algorithm
        # to position the states and draw connections between them
        
        # For now, just list the allowed transitions
        y_pos = 60
        x_pos = self.screen_width // 2
        
        for state_id in sorted(self.registry.states.keys()):
            allowed = self.registry.get_allowed_transitions(state_id)
            if allowed:
                text = f"{state_id} -> {', '.join(allowed)}"
                text_surface = self.font.render(text, True, (170, 200, 220))
                self.screen.blit(text_surface, (x_pos, y_pos))
                y_pos += 20

def show_transition_viewer():
    """
    Convenience function to show the state transition viewer.
    Can be called from the game to display the viewer for debugging.
    """
    from .state_registry import state_registry
    viewer = StateTransitionViewer(state_registry)
    viewer.show()
