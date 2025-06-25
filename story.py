# story.py
from logging import basicConfig, info, warning, error, debug, INFO
from hyperdrone_core.game_events import GameEvent, ItemCollectedEvent, BossDefeatedEvent
from settings_manager import get_setting

# Using the existing logger is great.
basicConfig(level=INFO, format='%(levelname)s: %(message)s')

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
            info(f"Objective COMPLETED: '{self.description}' ({self.objective_id})")

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
        warning(f"Chapter '{self.title}': Tried to complete non-existent objective ID: '{objective_id}'")

class StoryManager:
    """The main controller for the game's narrative."""
    def __init__(self, state_manager_ref=None, drone_system_ref=None): # <-- Add drone_system_ref
        """Initializes the StoryManager."""
        self.chapters = []
        self.current_chapter_index = -1
        self.state_manager = state_manager_ref
        self.drone_system = drone_system_ref # <-- Store the reference

    def add_chapter(self, chapter):
        """Adds a Chapter object to the story sequence."""
        self.chapters.append(chapter)

    def _apply_chapter_prerequisites(self, start_chapter_index):
        """Sets up the game state to match the starting chapter's requirements."""
        if not self.drone_system or start_chapter_index == 0:
            return

        info(f"Applying prerequisites for starting at Chapter {start_chapter_index + 1}.")
        # Mark all previous chapters as complete
        for i in range(start_chapter_index):
            for obj in self.chapters[i].objectives:
                obj.complete()

        # Grant fragments based on which chapters are being skipped
        if start_chapter_index >= 1: # Starting at Ch 2 or later, grant Earth
            self.drone_system.collect_core_fragment("cf_earth")
            self.drone_system.unlock_drone("VANTIS")
            # Grant basic weapons that would have been purchased in Chapter 1
            self.drone_system.add_owned_weapon(1)  # Tri-shot
            self.drone_system.add_owned_weapon(2)  # Rapid single
            
        if start_chapter_index >= 2: # Starting at Ch 3 or later, grant Fire
            self.drone_system.collect_core_fragment("cf_fire")
            self.drone_system.add_defeated_boss("MAZE_GUARDIAN") # Also mark boss as defeated
            self.drone_system.unlock_drone("STRIX")
            # Grant additional weapons
            self.drone_system.add_owned_weapon(3)  # Rapid tri
            self.drone_system.add_owned_weapon(4)  # Big shot
            
        if start_chapter_index >= 3: # Starting at Ch 4 or later, grant Air
            self.drone_system.collect_core_fragment("cf_air")
            # Grant more advanced weapons
            self.drone_system.add_owned_weapon(5)  # Bounce
            self.drone_system.add_owned_weapon(6)  # Pierce
            
        if start_chapter_index >= 4: # Starting at Ch 5 or later, grant Water
            self.drone_system.collect_core_fragment("cf_water")
            # Grant final weapons
            self.drone_system.add_owned_weapon(7)  # Heatseeker
            self.drone_system.add_owned_weapon(8)  # Heatseeker plus bullets

    def start_story(self):
        """Begins the story by setting the current chapter based on settings."""
        if not self.chapters:
            error("No chapters in the story to start.")
            return

        start_chapter_id = get_setting("testing", "START_CHAPTER", "chapter_1")
        try:
            # Chapter IDs are "chapter_1", "chapter_2", etc.
            start_index = int(start_chapter_id.split('_')[1]) - 1
            if not (0 <= start_index < len(self.chapters)):
                start_index = 0
        except (ValueError, IndexError):
            start_index = 0

        self.current_chapter_index = start_index
        self._apply_chapter_prerequisites(start_index)
        
        info(f"Story has started at Chapter {self.current_chapter_index + 1}!")

    def get_current_chapter(self):
        """Retrieves the chapter the player is currently on."""
        if 0 <= self.current_chapter_index < len(self.chapters):
            return self.chapters[self.current_chapter_index]
        return None

    def advance_chapter(self):
        """Moves the story to the next chapter and returns to StoryMapState."""
        current_chap = self.get_current_chapter()
        if current_chap and current_chap.is_complete():
            completed_chapter_title = current_chap.title
            
            if self.current_chapter_index < len(self.chapters) - 1:
                self.current_chapter_index += 1
                next_chap = self.get_current_chapter()
                info(f"--- Advanced to Chapter: {next_chap.title} ---")
                
                # Return to StoryMapState with completion info
                if self.state_manager:
                    self.state_manager.set_state("StoryMapState", 
                                                chapter_completed=True, 
                                                completed_chapter=completed_chapter_title)
            else:
                self.current_chapter_index = -1
                info("--- Congratulations! You have completed the story! ---")
                if self.state_manager:
                    self.state_manager.set_state("MainMenuState")
        elif current_chap:
            warning("Cannot advance: Current chapter is not yet complete.")
        else:
            warning("Story has not started or is already over.")

    def complete_objective_by_id(self, objective_id):
        """Finds and completes a specific objective by its ID in the current chapter."""
        current_chapter = self.get_current_chapter()
        if current_chapter:
            current_chapter.complete_objective_by_id(objective_id)
        else:
            warning(f"No current chapter to complete objective: '{objective_id}'")

    def handle_game_event(self, event):
        """Processes game events to update objective status."""
        current_chapter = self.get_current_chapter()
        if not current_chapter:
            return

        debug(f"StoryManager processing event: {type(event).__name__}")

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
    
    def check_and_advance_chapter(self):
        """Check if current chapter is complete and advance if so."""
        current_chapter = self.get_current_chapter()
        if current_chapter and current_chapter.is_complete():
            self.advance_chapter()
            return True
        return False
