# hyperdrone_core/story_manager.py
import json
from logging import getLogger
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = getLogger(__name__)

@dataclass
class Chapter:
    """Represents a game chapter with its metadata and progression state"""
    chapter_id: str
    title: str
    subtitle: str
    story: str
    gameplay: str
    reward: str
    emotion: str
    completed: bool = False
    unlocked: bool = False

@dataclass
class StoryBeat:
    """Represents a story beat event"""
    beat_id: str
    trigger: str
    title: str
    description: str
    triggered: bool = False

class StoryManager:
    """
    Manages the overall story progression, chapter unlocking, and narrative events.
    Handles the 5-chapter structure with elemental cores and story beats.
    """
    
    def __init__(self):
        self.chapters: Dict[str, Chapter] = {}
        self.story_beats: Dict[str, StoryBeat] = {}
        self.current_chapter_index = 0
        self.completed_chapters = set()
        self.unlocked_lore = set()
        self.ending_choice = None
        self.true_ending_intel = False
        
        # Load story data
        self._load_story_data()
        
        # Initialize first chapter as unlocked
        if self.chapters:
            first_chapter = list(self.chapters.values())[0]
            first_chapter.unlocked = True
    
    def _load_story_data(self):
        """Load story data from lore_entries.json"""
        try:
            with open('data/lore_entries.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Load chapters
                for chapter_data in data.get('chapters', []):
                    chapter = Chapter(
                        chapter_id=chapter_data['id'],
                        title=chapter_data['title'],
                        subtitle=chapter_data['subtitle'],
                        story=chapter_data['story'],
                        gameplay=chapter_data['gameplay'],
                        reward=chapter_data['reward'],
                        emotion=chapter_data['emotion']
                    )
                    self.chapters[chapter.chapter_id] = chapter
                
                # Load story beats
                for beat_data in data.get('narrative_events', {}).get('story_beats', []):
                    beat = StoryBeat(
                        beat_id=beat_data['id'],
                        trigger=beat_data['trigger'],
                        title=beat_data['title'],
                        description=beat_data['description']
                    )
                    self.story_beats[beat.beat_id] = beat
                    
                logger.info(f"Loaded {len(self.chapters)} chapters and {len(self.story_beats)} story beats")
                
        except Exception as e:
            logger.error(f"Failed to load story data: {e}")
            self._create_default_chapters()
    
    def _create_default_chapters(self):
        """Create default chapters if loading fails"""
        default_chapters = [
            {
                'id': 'chapter_1',
                'title': 'Chapter 1: The Entrance',
                'subtitle': 'Earth Core – Top-Down Puzzle Maze',
                'story': 'The drone answers a mysterious signal and discovers the sealed Vault entrance.',
                'gameplay': 'Navigate a collapsing maze, collect energy rings, solve gravity puzzles.',
                'reward': 'Earth Fragment - The foundation of your journey.',
                'emotion': 'Awe and trepidation at entering an ancient protector of Earth.'
            },
            {
                'id': 'chapter_2',
                'title': 'Chapter 2: The Guardian',
                'subtitle': 'Fire Core - Top-Down Boss Fight',
                'story': 'A colossal MazeGuardian awakens to test intruders.',
                'gameplay': 'Engage in boss fight, dodge attacks, strike weak points.',
                'reward': 'Fire Fragment - Raw power earned through combat.',
                'emotion': 'Tension and exhilaration in combat against an ancient guardian.'
            },
            {
                'id': 'chapter_3',
                'title': 'Chapter 3: Corruption Sector',
                'subtitle': 'Air Core - Top-Down Puzzle Maze',
                'story': 'Navigate a decaying sector where corridors shift and logic glitches.',
                'gameplay': 'Solve spatial puzzles, decode glyphs, navigate shifting walls.',
                'reward': 'Air Fragment - Intellect and adaptability.',
                'emotion': 'Unease as the Vault\'s corrupted AI glitches around you.'
            },
            {
                'id': 'chapter_4',
                'title': 'Chapter 4: The Harvest Chamber',
                'subtitle': 'Water Core - Vertical Scrolling Shmup',
                'story': 'Descend into a flooded chamber where harvested wreckage has been repurposed.',
                'gameplay': 'Navigate downward through wreckage, blast corrupted drones.',
                'reward': 'Water Fragment - Deep secrets of the Vault.',
                'emotion': 'Shock and horror at discovering the plane wreckage.'
            },
            {
                'id': 'chapter_5',
                'title': 'Chapter 5: The Orichalc Core',
                'subtitle': 'Tower Defense + Boss Fight',
                'story': 'Reach the Vault\'s heart and face the final choice.',
                'gameplay': 'Defend the core with turrets, face the final boss, make the ultimate choice.',
                'reward': 'The final choice that determines Earth\'s fate.',
                'emotion': 'Tense resolve as you embody humanity\'s last hope.'
            }
        ]
        
        for chapter_data in default_chapters:
            chapter = Chapter(
                chapter_id=chapter_data['id'],
                title=chapter_data['title'],
                subtitle=chapter_data['subtitle'],
                story=chapter_data['story'],
                gameplay=chapter_data['gameplay'],
                reward=chapter_data['reward'],
                emotion=chapter_data['emotion']
            )
            self.chapters[chapter.chapter_id] = chapter
    
    def get_current_chapter(self) -> Optional[Chapter]:
        """Get the currently active chapter"""
        chapter_ids = list(self.chapters.keys())
        if 0 <= self.current_chapter_index < len(chapter_ids):
            chapter_id = chapter_ids[self.current_chapter_index]
            return self.chapters[chapter_id]
        return None
    
    def get_chapter_by_id(self, chapter_id: str) -> Optional[Chapter]:
        """Get a specific chapter by ID"""
        return self.chapters.get(chapter_id)
    
    def complete_chapter(self, chapter_id: str):
        """Mark a chapter as completed and unlock the next one"""
        if chapter_id in self.chapters:
            chapter = self.chapters[chapter_id]
            chapter.completed = True
            self.completed_chapters.add(chapter_id)
            
            # Unlock next chapter
            chapter_ids = list(self.chapters.keys())
            try:
                current_index = chapter_ids.index(chapter_id)
                if current_index + 1 < len(chapter_ids):
                    next_chapter_id = chapter_ids[current_index + 1]
                    self.chapters[next_chapter_id].unlocked = True
                    logger.info(f"Chapter {chapter_id} completed, unlocked {next_chapter_id}")
            except ValueError:
                logger.warning(f"Chapter {chapter_id} not found in chapter list")
    
    def advance_chapter(self):
        """Advance to the next chapter"""
        chapter_ids = list(self.chapters.keys())
        if self.current_chapter_index < len(chapter_ids) - 1:
            self.current_chapter_index += 1
            logger.info(f"Advanced to chapter index {self.current_chapter_index}")
    
    def is_chapter_unlocked(self, chapter_id: str) -> bool:
        """Check if a chapter is unlocked"""
        chapter = self.chapters.get(chapter_id)
        return chapter.unlocked if chapter else False
    
    def is_chapter_completed(self, chapter_id: str) -> bool:
        """Check if a chapter is completed"""
        return chapter_id in self.completed_chapters
    
    def get_completion_percentage(self) -> float:
        """Get overall story completion percentage"""
        if not self.chapters:
            return 0.0
        return (len(self.completed_chapters) / len(self.chapters)) * 100
    
    def trigger_story_beat(self, trigger_id: str) -> Optional[StoryBeat]:
        """Trigger a story beat by its trigger ID"""
        for beat in self.story_beats.values():
            if beat.trigger == trigger_id and not beat.triggered:
                beat.triggered = True
                logger.info(f"Story beat triggered: {beat.title}")
                return beat
        return None
    
    def get_triggered_story_beats(self) -> List[StoryBeat]:
        """Get all triggered story beats"""
        return [beat for beat in self.story_beats.values() if beat.triggered]
    
    def unlock_lore(self, lore_id: str):
        """Unlock a lore entry"""
        self.unlocked_lore.add(lore_id)
        logger.info(f"Lore unlocked: {lore_id}")
    
    def is_lore_unlocked(self, lore_id: str) -> bool:
        """Check if a lore entry is unlocked"""
        return lore_id in self.unlocked_lore
    
    def set_ending(self, ending_choice: str):
        """Set the player's ending choice"""
        self.ending_choice = ending_choice
        logger.info(f"Ending choice set: {ending_choice}")
    
    def unlock_true_ending_intel(self):
        """Unlock intel required for the true ending (from bonus chapter)"""
        self.true_ending_intel = True
        logger.info("True ending intel unlocked!")
    
    def can_access_true_ending(self) -> bool:
        """Check if player can access the true ending"""
        return (self.true_ending_intel and 
                len(self.completed_chapters) >= len(self.chapters))
    
    def get_available_chapters(self) -> List[Chapter]:
        """Get all unlocked chapters"""
        return [chapter for chapter in self.chapters.values() if chapter.unlocked]
    
    def get_chapter_progress_text(self) -> str:
        """Get a text representation of chapter progress"""
        completed = len(self.completed_chapters)
        total = len(self.chapters)
        return f"Chapters: {completed}/{total} completed"
    
    def reset_progress(self):
        """Reset all story progress (for new game)"""
        self.current_chapter_index = 0
        self.completed_chapters.clear()
        self.unlocked_lore.clear()
        self.ending_choice = None
        self.true_ending_intel = False
        
        # Reset all chapters
        for chapter in self.chapters.values():
            chapter.completed = False
            chapter.unlocked = False
        
        # Reset all story beats
        for beat in self.story_beats.values():
            beat.triggered = False
        
        # Unlock first chapter
        if self.chapters:
            first_chapter = list(self.chapters.values())[0]
            first_chapter.unlocked = True
        
        logger.info("Story progress reset")
    
    def save_progress(self) -> Dict[str, Any]:
        """Save story progress to a dictionary"""
        return {
            'current_chapter_index': self.current_chapter_index,
            'completed_chapters': list(self.completed_chapters),
            'unlocked_lore': list(self.unlocked_lore),
            'ending_choice': self.ending_choice,
            'true_ending_intel': self.true_ending_intel,
            'chapter_states': {
                chapter_id: {
                    'completed': chapter.completed,
                    'unlocked': chapter.unlocked
                }
                for chapter_id, chapter in self.chapters.items()
            },
            'story_beat_states': {
                beat_id: beat.triggered
                for beat_id, beat in self.story_beats.items()
            }
        }
    
    def load_progress(self, progress_data: Dict[str, Any]):
        """Load story progress from a dictionary"""
        try:
            self.current_chapter_index = progress_data.get('current_chapter_index', 0)
            self.completed_chapters = set(progress_data.get('completed_chapters', []))
            self.unlocked_lore = set(progress_data.get('unlocked_lore', []))
            self.ending_choice = progress_data.get('ending_choice')
            self.true_ending_intel = progress_data.get('true_ending_intel', False)
            
            # Load chapter states
            chapter_states = progress_data.get('chapter_states', {})
            for chapter_id, state in chapter_states.items():
                if chapter_id in self.chapters:
                    self.chapters[chapter_id].completed = state.get('completed', False)
                    self.chapters[chapter_id].unlocked = state.get('unlocked', False)
            
            # Load story beat states
            beat_states = progress_data.get('story_beat_states', {})
            for beat_id, triggered in beat_states.items():
                if beat_id in self.story_beats:
                    self.story_beats[beat_id].triggered = triggered
            
            logger.info("Story progress loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load story progress: {e}")
    
    def get_chapter_summary(self) -> str:
        """Get a summary of the current story state"""
        current = self.get_current_chapter()
        if not current:
            return "Story complete"
        
        return f"Current: {current.title} | Progress: {self.get_chapter_progress_text()}"