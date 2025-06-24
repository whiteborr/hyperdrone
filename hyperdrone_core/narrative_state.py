# hyperdrone_core/narrative_state.py
from pygame.time import get_ticks
from pygame.font import Font
from pygame import Surface, KEYDOWN, K_SPACE, K_RETURN
import logging
import json
from .state import State

logger = logging.getLogger(__name__)

class NarrativeState(State):
    """
    Non-interactive state for displaying Memory Echoes and story beats.
    Provides smooth narrative transitions between major gameplay events.
    """
    def __init__(self, game_controller):
        super().__init__(game_controller)
        self.narrative_data = None
        self.current_line_index = 0
        self.text_lines = []
        self.title = ""
        self.next_state = None
        self.typewriter_timer = 0
        self.typewriter_speed = 50  # ms per character
        self.current_char_index = 0
        self.line_complete = False
        self.waiting_for_input = False
        
    def enter(self, previous_state=None, **kwargs):
        """Initialize narrative display with event data"""
        logger.info("Entering NarrativeState")
        
        narrative_event_id = kwargs.get('narrative_event_id')
        self.next_state = kwargs.get('next_state', 'StoryMapState')
        
        if not narrative_event_id:
            logger.warning("No narrative_event_id provided, transitioning to next state")
            self.game.state_manager.set_state(self.next_state)
            return
            
        self.narrative_data = self._load_narrative_data(narrative_event_id)
        if not self.narrative_data:
            logger.warning(f"Narrative event '{narrative_event_id}' not found")
            self.game.state_manager.set_state(self.next_state)
            return
            
        self._setup_text_display()
        
    def _load_narrative_data(self, event_id):
        """Load narrative event from lore_entries.json"""
        try:
            with open('data/lore_entries.json', 'r') as f:
                data = json.load(f)
                
            # Check memory echoes
            for echo in data.get('narrative_events', {}).get('memory_echoes', []):
                if echo['id'] == event_id:
                    return {
                        'title': echo['title'],
                        'lines': echo['lines']
                    }
                    
            # Check story beats
            for beat in data.get('narrative_events', {}).get('story_beats', []):
                if beat['id'] == event_id:
                    return {
                        'title': beat['title'],
                        'lines': [beat['description']]
                    }
                    
        except Exception as e:
            logger.error(f"Error loading narrative data: {e}")
            
        return None
        
    def _setup_text_display(self):
        """Setup text display parameters"""
        self.title = self.narrative_data['title']
        self.text_lines = self.narrative_data['lines']
        self.current_line_index = 0
        self.current_char_index = 0
        self.line_complete = False
        self.waiting_for_input = False
        self.typewriter_timer = get_ticks()
        
    def handle_events(self, events):
        """Handle user input to advance text"""
        for event in events:
            if event.type == KEYDOWN:
                if event.key in (K_SPACE, K_RETURN):
                    if self.waiting_for_input:
                        self._advance_text()
                    elif not self.line_complete:
                        # Skip typewriter effect
                        self.current_char_index = len(self.text_lines[self.current_line_index])
                        self.line_complete = True
                        self.waiting_for_input = True
                        
    def _advance_text(self):
        """Advance to next line or complete narrative"""
        self.current_line_index += 1
        if self.current_line_index >= len(self.text_lines):
            # Narrative complete, transition to next state
            self.game.state_manager.set_state(self.next_state)
        else:
            # Setup next line
            self.current_char_index = 0
            self.line_complete = False
            self.waiting_for_input = False
            self.typewriter_timer = get_ticks()
            
    def update(self, delta_time):
        """Update typewriter effect"""
        if self.line_complete or self.current_line_index >= len(self.text_lines):
            return
            
        current_time = get_ticks()
        if current_time - self.typewriter_timer > self.typewriter_speed:
            current_line = self.text_lines[self.current_line_index]
            if self.current_char_index < len(current_line):
                self.current_char_index += 1
                self.typewriter_timer = current_time
            else:
                self.line_complete = True
                self.waiting_for_input = True
                
    def draw(self, surface):
        """Draw narrative text with typewriter effect"""
        # Fill background
        surface.fill((10, 10, 20))
        
        screen_width = surface.get_width()
        screen_height = surface.get_height()
        
        # Draw title
        title_font = Font(None, 48)
        title_surf = title_font.render(self.title, True, (255, 215, 0))  # Gold
        title_rect = title_surf.get_rect(center=(screen_width // 2, 150))
        surface.blit(title_surf, title_rect)
        
        # Draw current line with typewriter effect
        if self.current_line_index < len(self.text_lines):
            text_font = Font(None, 32)
            current_line = self.text_lines[self.current_line_index]
            displayed_text = current_line[:self.current_char_index]
            
            # Wrap text if needed
            max_width = screen_width - 200
            words = displayed_text.split(' ')
            lines = []
            current_text_line = ''
            
            for word in words:
                test_line = current_text_line + word + ' '
                if text_font.size(test_line)[0] < max_width:
                    current_text_line = test_line
                else:
                    if current_text_line:
                        lines.append(current_text_line.strip())
                    current_text_line = word + ' '
            if current_text_line:
                lines.append(current_text_line.strip())
                
            # Draw wrapped lines
            start_y = screen_height // 2 - (len(lines) * 20)
            for i, line in enumerate(lines):
                line_surf = text_font.render(line, True, (255, 255, 255))
                line_rect = line_surf.get_rect(center=(screen_width // 2, start_y + i * 40))
                surface.blit(line_surf, line_rect)
                
        # Draw continue prompt
        if self.waiting_for_input:
            prompt_font = Font(None, 24)
            if self.current_line_index < len(self.text_lines) - 1:
                prompt_text = "Press SPACE to continue..."
            else:
                prompt_text = "Press SPACE to finish..."
            prompt_surf = prompt_font.render(prompt_text, True, (200, 200, 200))
            prompt_rect = prompt_surf.get_rect(center=(screen_width // 2, screen_height - 100))
            surface.blit(prompt_surf, prompt_rect)