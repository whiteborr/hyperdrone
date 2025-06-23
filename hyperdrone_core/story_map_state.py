# hyperdrone_core/story_map_state.py
from pygame.time import get_ticks
from pygame.font import Font
from pygame import Surface, KEYDOWN, K_SPACE, K_RETURN
import logging
from .state import State
from constants import GAME_STATE_PLAYING, GAME_STATE_BOSS_FIGHT, GAME_STATE_CORRUPTED_SECTOR, GAME_STATE_HARVEST_CHAMBER, GAME_STATE_MAZE_DEFENSE

logger = logging.getLogger(__name__)

class StoryMapState(State):
    """
    State that displays a visual map of the game's chapters and the player's progression.
    This state is shown before the start of a gameplay level.
    """
    def __init__(self, game_controller):
        super().__init__(game_controller)
        self.display_timer = 0
        self.display_duration = 4000  # 4 seconds
        self.ready_to_transition = False
        
        # Chapter completion handling
        self.showing_completion_summary = False
        self.completed_chapter = None
        self.summary_timer = 0
        self.summary_duration = 3000  # 3 seconds
        
        # Animation state
        self.animating_to_next_chapter = False
        self.animation_timer = 0
        self.animation_duration = 2000  # 2 seconds
        
    def enter(self, previous_state=None, **kwargs):
        """Called when entering this state"""
        logger.info("Entering StoryMapState")
        self.display_timer = get_ticks()
        self.ready_to_transition = False
        
        # Check if we're returning from a completed chapter
        chapter_completed = kwargs.get('chapter_completed', False)
        if chapter_completed:
            self.completed_chapter = kwargs.get('completed_chapter')
            self.showing_completion_summary = True
            self.summary_timer = get_ticks()
            logger.info(f"Showing completion summary for {self.completed_chapter}")
        else:
            self.showing_completion_summary = False
            self.completed_chapter = None
        
    def exit(self, next_state=None):
        """Called when exiting this state"""
        logger.info(f"Exiting StoryMapState to {next_state}")
        
    def handle_events(self, events):
        """Handle discrete events like key presses"""
        for event in events:
            if event.type == KEYDOWN:
                if event.key in (K_SPACE, K_RETURN):
                    if self.showing_completion_summary:
                        # Skip summary display
                        self.showing_completion_summary = False
                        self.animating_to_next_chapter = True
                        self.animation_timer = get_ticks()
                    elif self.animating_to_next_chapter:
                        # Skip animation
                        self.animating_to_next_chapter = False
                    else:
                        self.ready_to_transition = True
                    
    def update(self, delta_time):
        """Handle continuous updates"""
        current_time = get_ticks()
        
        # Handle completion summary display
        if self.showing_completion_summary:
            if current_time - self.summary_timer > self.summary_duration:
                self.showing_completion_summary = False
                self.animating_to_next_chapter = True
                self.animation_timer = current_time
                
        # Handle animation to next chapter
        elif self.animating_to_next_chapter:
            if current_time - self.animation_timer > self.animation_duration:
                self.animating_to_next_chapter = False
                
        # Only transition when player presses spacebar or Enter (and not during animations)
        elif self.ready_to_transition and not self.showing_completion_summary:
            self._transition_to_gameplay()
            
    def _transition_to_gameplay(self):
        """Transition to the appropriate gameplay state based on the current chapter"""
        story_manager = self.game.story_manager
        current_chapter = story_manager.get_current_chapter()
        
        if not current_chapter:
            logger.warning("No current chapter found, defaulting to PlayingState")
            self.game.state_manager.set_state(GAME_STATE_PLAYING)
            return
            
        # Determine the appropriate state based on the chapter ID
        chapter_id = current_chapter.chapter_id
        
        # Map chapter IDs to their corresponding game states
        chapter_state_map = {
            "chapter_1": GAME_STATE_PLAYING,
            "chapter_2": GAME_STATE_BOSS_FIGHT,
            "chapter_3": GAME_STATE_CORRUPTED_SECTOR,
            "chapter_4": GAME_STATE_HARVEST_CHAMBER,
            "chapter_5": GAME_STATE_MAZE_DEFENSE,
            "bonus": GAME_STATE_PLAYING      # Placeholder
        }
        
        # Get the appropriate state for the current chapter
        next_state = chapter_state_map.get(chapter_id, GAME_STATE_PLAYING)
        logger.info(f"Transitioning from StoryMapState to {next_state} for chapter {chapter_id}")
        self.game.state_manager.set_state(next_state, from_story_map=True)
            
    def draw(self, surface):
        """Draw the story map screen"""
        # The actual drawing is handled by the UIManager's draw_story_map method
        self.game.ui_manager.draw_story_map()
        
        # Draw completion summary if showing
        if self.showing_completion_summary and self.completed_chapter:
            self._draw_completion_summary(surface)
            
    def _draw_completion_summary(self, surface):
        """Draw chapter completion summary"""
        # Simple text overlay for chapter completion
        font = Font(None, 48)
        title_text = font.render(f"Chapter Completed: {self.completed_chapter}", True, (255, 255, 255))
        
        # Center the text
        screen_width = surface.get_width()
        screen_height = surface.get_height()
        title_rect = title_text.get_rect(center=(screen_width // 2, screen_height // 2 - 50))
        
        # Draw semi-transparent background
        overlay = Surface((screen_width, screen_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        
        # Draw text
        surface.blit(title_text, title_rect)
        
        # Draw "Press SPACE to continue" text
        small_font = Font(None, 24)
        continue_text = small_font.render("Press SPACE to continue", True, (200, 200, 200))
        continue_rect = continue_text.get_rect(center=(screen_width // 2, screen_height // 2 + 50))
        surface.blit(continue_text, continue_rect)
