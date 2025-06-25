# hyperdrone_core/story_map_state.py
from pygame.time import get_ticks
from pygame.font import Font
from pygame import Surface, KEYDOWN, K_SPACE, K_RETURN
from pygame.math import Vector2
from logging import getLogger
from json import load
from .state import State
from constants import GAME_STATE_PLAYING, GAME_STATE_BOSS_FIGHT, GAME_STATE_CORRUPTED_SECTOR, GAME_STATE_HARVEST_CHAMBER, GAME_STATE_MAZE_DEFENSE

logger = getLogger(__name__)

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
        self.animation_duration = 1500  # 1.5 seconds
        self.animation_start_pos = Vector2(0, 0)
        self.animation_end_pos = Vector2(0, 0)
        self.current_animation_pos = Vector2(0, 0)
        
        # Chapter data from lore_entries.json
        self.chapter_data = self._load_chapter_data()
        
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
            self._setup_animation()  # Setup animation positions
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
                        self.ready_to_transition = True
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
                self._setup_animation()  # Setup animation positions
                
        # Handle animation to next chapter
        elif self.animating_to_next_chapter:
            if current_time - self.animation_timer > self.animation_duration:
                self.animating_to_next_chapter = False
                # Don't auto-transition, wait for player input
            else:
                # Update animation position
                progress = (current_time - self.animation_timer) / self.animation_duration
                # Smooth easing function
                eased_progress = progress * progress * (3.0 - 2.0 * progress)
                self.current_animation_pos = self.animation_start_pos.lerp(self.animation_end_pos, eased_progress)
                
        # Only transition when player presses spacebar or Enter (and not during animations)
        elif self.ready_to_transition and not self.showing_completion_summary and not self.animating_to_next_chapter:
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
        
        # Draw next chapter introduction if animating
        if self.animating_to_next_chapter:
            self._draw_next_chapter_intro(surface)
            
    def _load_chapter_data(self):
        """Load chapter data from lore_entries.json"""
        try:
            with open('data/lore_entries.json', 'r', encoding='utf-8') as f:
                data = load(f)
                return {chapter['id']: chapter for chapter in data.get('chapters', [])}
        except Exception as e:
            logger.warning(f"Could not load chapter data: {e}")
            return {}
    
    def _setup_animation(self):
        """Setup animation positions for player cursor movement"""
        story_manager = self.game.story_manager
        if not story_manager:
            return
            
        # Get current and next chapter positions
        current_index = story_manager.current_chapter_index - 1  # Previous chapter (where we completed)
        next_index = story_manager.current_chapter_index  # Current chapter (where we're going)
        
        # Calculate positions based on chapter map layout
        width = self.game.ui_manager.screen.get_width()
        chapter_spacing = 150
        start_x = (width - (4 * chapter_spacing)) // 2
        map_y = 250
        
        if 0 <= current_index < 5:
            self.animation_start_pos = Vector2(start_x + (current_index * chapter_spacing) + 16, map_y - 40)
        if 0 <= next_index < 5:
            self.animation_end_pos = Vector2(start_x + (next_index * chapter_spacing) + 16, map_y - 40)
            
        self.current_animation_pos = Vector2(self.animation_start_pos)
    
    def _draw_completion_summary(self, surface):
        """Draw chapter completion summary with chapter details"""
        screen_width = surface.get_width()
        screen_height = surface.get_height()
        
        # Draw semi-transparent background
        overlay = Surface((screen_width, screen_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        
        # Get completed chapter data
        completed_chapter_id = self._get_chapter_id_from_title(self.completed_chapter)
        chapter_info = self.chapter_data.get(completed_chapter_id, {})
        
        # Title
        font_large = Font(None, 48)
        title_text = font_large.render("Chapter Completed!", True, (255, 215, 0))  # Gold
        title_rect = title_text.get_rect(center=(screen_width // 2, screen_height // 2 - 150))
        surface.blit(title_text, title_rect)
        
        # Chapter title
        font_medium = Font(None, 36)
        chapter_title = chapter_info.get('title', self.completed_chapter)
        chapter_text = font_medium.render(chapter_title, True, (255, 255, 255))
        chapter_rect = chapter_text.get_rect(center=(screen_width // 2, screen_height // 2 - 100))
        surface.blit(chapter_text, chapter_rect)
        
        # Reward text
        reward = chapter_info.get('reward', '')
        if reward:
            font_small = Font(None, 28)
            reward_text = font_small.render(f"Reward: {reward}", True, (0, 255, 255))  # Cyan
            reward_rect = reward_text.get_rect(center=(screen_width // 2, screen_height // 2 - 50))
            surface.blit(reward_text, reward_rect)
        
        # Continue instruction
        font_small = Font(None, 24)
        continue_text = font_small.render("Press SPACE to continue", True, (200, 200, 200))
        continue_rect = continue_text.get_rect(center=(screen_width // 2, screen_height // 2 + 50))
        surface.blit(continue_text, continue_rect)
    
    def _draw_next_chapter_intro(self, surface):
        """Draw introduction for the next chapter"""
        story_manager = self.game.story_manager
        if not story_manager:
            return
            
        current_chapter = story_manager.get_current_chapter()
        if not current_chapter:
            return
            
        chapter_info = self.chapter_data.get(current_chapter.chapter_id, {})
        
        screen_width = surface.get_width()
        screen_height = surface.get_height()
        
        # Draw semi-transparent background
        overlay = Surface((screen_width, screen_height))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 50))  # Dark blue tint
        surface.blit(overlay, (0, 0))
        
        # Next chapter title
        font_large = Font(None, 48)
        title = chapter_info.get('title', current_chapter.title)
        title_text = font_large.render(title, True, (255, 215, 0))  # Gold
        title_rect = title_text.get_rect(center=(screen_width // 2, screen_height // 2 - 100))
        surface.blit(title_text, title_rect)
        
        # Subtitle
        subtitle = chapter_info.get('subtitle', '')
        if subtitle:
            font_medium = Font(None, 32)
            subtitle_text = font_medium.render(subtitle, True, (200, 200, 255))  # Light blue
            subtitle_rect = subtitle_text.get_rect(center=(screen_width // 2, screen_height // 2 - 60))
            surface.blit(subtitle_text, subtitle_rect)
        
        # Story preview (first part)
        story = chapter_info.get('story', '')
        if story:
            font_small = Font(None, 24)
            # Take first sentence or first 100 characters
            preview = story.split('.')[0] + '...' if '.' in story else story[:100] + '...'
            
            # Wrap text
            words = preview.split(' ')
            lines = []
            current_line = ''
            max_width = screen_width - 200
            
            for word in words:
                test_line = current_line + word + ' '
                if font_small.size(test_line)[0] < max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + ' '
            if current_line:
                lines.append(current_line.strip())
            
            # Draw wrapped text
            for i, line in enumerate(lines[:3]):  # Max 3 lines
                line_text = font_small.render(line, True, (255, 255, 255))
                line_rect = line_text.get_rect(center=(screen_width // 2, screen_height // 2 + i * 30))
                surface.blit(line_text, line_rect)
    
    def _get_chapter_id_from_title(self, title):
        """Convert chapter title to chapter ID"""
        # Simple mapping based on common patterns
        if "1" in title or "Entrance" in title:
            return "chapter_1"
        elif "2" in title or "Guardian" in title:
            return "chapter_2"
        elif "3" in title or "Corruption" in title:
            return "chapter_3"
        elif "4" in title or "Harvest" in title:
            return "chapter_4"
        elif "5" in title or "Orichalc" in title:
            return "chapter_5"
        return "chapter_1"  # Default
