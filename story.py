# story.py
import logging
from hyperdrone_core.game_events import GameEvent, ItemCollectedEvent, BossDefeatedEvent

# Using the existing logger is great.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- NEW: Objective Class ---
# This class represents a single, trackable objective.
class Objective:
    """A specific, trackable goal within a chapter."""
    def __init__(self, objective_id, description, obj_type, target):
        """
        Initializes an objective.

        Args:
            objective_id (str): A unique ID for this objective (e.g., "collect_log_a").
            description (str): The text displayed to the player (e.g., "Find the corrupted data log").
            obj_type (str): The type of action required (e.g., 'collect', 'kill', 'reach_zone').
            target (str): The specific ID of the target (e.g., 'item_id_log_a', 'boss_id_guardian').
        """
        self.objective_id = objective_id
        self.description = description
        self.type = obj_type
        self.target = target
        self.is_complete = False

    def complete(self):
        """Marks the objective as complete."""
        if not self.is_complete:
            self.is_complete = True
            logging.info(f"Objective COMPLETED: '{self.description}' ({self.objective_id})")

# --- MODIFIED: Chapter Class ---
class Chapter:
    """Acts as a blueprint for a single chapter in our story."""
    def __init__(self, chapter_id, title, description, objectives, next_state_id=None):
        """
        Initializes a new Chapter.
        
        Args:
            chapter_id (str): A unique ID for this chapter.
            title (str): The title of the chapter.
            description (str): A paragraph of text describing the chapter's plot.
            objectives (list[Objective]): A list of Objective objects for this chapter.
            next_state_id (str, optional): The ID of the game state to transition to upon completion.
        """
        self.chapter_id = chapter_id
        self.title = title
        self.description = description
        self.objectives = objectives  # This is now a list of Objective objects
        self.next_state_id = next_state_id

    def is_complete(self):
        """Checks if all objectives in the chapter are complete."""
        return all(obj.is_complete for obj in self.objectives)

    def complete_objective_by_id(self, objective_id):
        """Finds and completes a specific objective by its ID."""
        for obj in self.objectives:
            if obj.objective_id == objective_id:
                obj.complete()
                return
        logging.warning(f"Chapter '{self.title}': Tried to complete non-existent objective ID: '{objective_id}'")

# --- MODIFIED: StoryManager Class ---
class StoryManager:
    """The main controller for the game's narrative."""
    def __init__(self, state_manager_ref=None):
        """Initializes the StoryManager."""
        self.chapters = []
        self.current_chapter_index = -1
        self.state_manager = state_manager_ref # Store a reference to the game's state manager

    def add_chapter(self, chapter):
        """Adds a Chapter object to the story sequence."""
        self.chapters.append(chapter)

    def start_story(self):
        """Begins the story by setting the current chapter to the first one."""
        if self.chapters:
            self.current_chapter_index = 0
            logging.info("Story has started!")
        else:
            logging.error("No chapters in the story to start.")

    def get_current_chapter(self):
        """Retrieves the chapter the player is currently on."""
        if 0 <= self.current_chapter_index < len(self.chapters):
            return self.chapters[self.current_chapter_index]
        return None

    def advance_chapter(self):
        """Moves the story to the next chapter and triggers a state change if necessary."""
        current_chap = self.get_current_chapter()
        if current_chap and current_chap.is_complete():
            if self.current_chapter_index < len(self.chapters) - 1:
                self.current_chapter_index += 1
                next_chap = self.get_current_chapter()
                logging.info(f"--- Advanced to Chapter: {next_chap.title} ---")
                
                # Use the stored state_manager reference to change the game state
                if next_chap.next_state_id and self.state_manager:
                    logging.info(f"Transitioning to game state: {next_chap.next_state_id}")
                    self.state_manager.set_state(next_chap.next_state_id)
            else:
                self.current_chapter_index = -1
                logging.info("--- Congratulations! You have completed the story! ---")
                if self.state_manager:
                    self.state_manager.set_state("MainMenuState") # Or a "CreditsState"
        elif current_chap:
            logging.warning("Cannot advance: Current chapter is not yet complete.")
        else:
            logging.warning("Story has not started or is already over.")

    def complete_objective_by_id(self, objective_id):
        """Finds and completes a specific objective by its ID in the current chapter."""
        current_chapter = self.get_current_chapter()
        if current_chapter:
            current_chapter.complete_objective_by_id(objective_id)
        else:
            logging.warning(f"No current chapter to complete objective: '{objective_id}'")

    def handle_game_event(self, event):
        """Processes game events to update objective status."""
        current_chapter = self.get_current_chapter()
        if not current_chapter:
            return

        logging.debug(f"StoryManager processing event: {type(event).__name__}")

        for objective in current_chapter.objectives:
            if objective.is_complete:
                continue

            # Check for item collection objectives (generic)
            if isinstance(event, ItemCollectedEvent) and objective.type == 'collect':
                # This now specifically checks for corrupted logs
                if event.item_type == 'corrupted_log' and objective.target == event.item_id:
                    objective.complete()

            # Check for boss kill objectives
            elif isinstance(event, BossDefeatedEvent) and objective.type == 'kill':
                if objective.target == event.boss_id:
                    objective.complete()
            
            # Note: The 'collect_all' and 'kill_all' objectives for Chapter 1
            # are handled directly in the PlayingState's update loop for now.
            # This event handler is for specific, event-driven objectives.
