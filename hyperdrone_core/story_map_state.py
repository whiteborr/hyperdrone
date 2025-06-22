# hyperdrone_core/story_map_state.pyAdd commentMore actions
import pygame
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
        
    def enter(self, previous_state=None, **kwargs):
        """Called when entering this state"""
        logger.info("Entering StoryMapState")
        self.display_timer = pygame.time.get_ticks()
        self.ready_to_transition = False
        
    def exit(self, next_state=None):
        """Called when exiting this state"""
        logger.info(f"Exiting StoryMapState to {next_state}")
        
    def handle_events(self, events):
        """Handle discrete events like key presses"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.ready_to_transition = True
                    
    def update(self, delta_time):
        """Handle continuous updates"""
        # Only transition when player presses spacebar or Enter
        if self.ready_to_transition:
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
        self.game.state_manager.set_state(next_state)
            
    def draw(self, surface):
        """Draw the story map screen"""
        # The actual drawing is handled by the UIManager's draw_story_map method
        self.game.ui_manager.draw_story_map()
