# story.py
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class Chapter:
    """
    Acts as a blueprint for a single chapter in our story. It holds all
    the necessary information and logic for one part of the narrative.
    """
    def __init__(self, title, description, objectives):
        """
        Initializes a new Chapter.
        """
        self.title = title
        self.description = description
        self.objectives = objectives
        self.completed_objectives = []

    def is_complete(self):
        """
        Checks if the chapter is complete.
        """
        return set(self.objectives) == set(self.completed_objectives)

    def complete_objective(self, objective_name):
        """
        Marks a specific objective as complete.
        """
        if objective_name in self.objectives and objective_name not in self.completed_objectives:
            # Use INFO for routine, expected events.
            logging.info(f"Objective completed: '{objective_name}'")
            self.completed_objectives.append(objective_name)
        else:
            # Use WARNING for unexpected situations that don't crash the game.
            logging.warning(f"Tried to complete an invalid or already completed objective: '{objective_name}'")


class StoryManager:
    """
    The main controller for the game's narrative.
    """
    def __init__(self):
        """
        Initializes the StoryManager.
        """
        self.chapters = []
        self.current_chapter_index = -1

    def add_chapter(self, chapter):
        """
        Adds a Chapter object to the story sequence.
        """
        self.chapters.append(chapter)

    def start_story(self):
        """
        Begins the story.
        """
        if self.chapters:
            self.current_chapter_index = 0
            logging.info("Story has started!")
        else:
            # Use ERROR for problems that prevent a part of the game from working.
            logging.error("No chapters in the story to start.")

    def get_current_chapter(self):
        """
        Retrieves the chapter the player is currently on.
        """
        if 0 <= self.current_chapter_index < len(self.chapters):
            return self.chapters[self.current_chapter_index]
        return None

    def advance_chapter(self):
        """
        Moves the story to the next chapter.
        """
        current_chap = self.get_current_chapter()
        if current_chap and current_chap.is_complete():
            if self.current_chapter_index < len(self.chapters) - 1:
                self.current_chapter_index += 1
                next_chap = self.get_current_chapter()
                logging.info(f"--- Advanced to next chapter: {next_chap.title} ---")
            else:
                self.current_chapter_index = -1
                logging.info("--- Congratulations! You have completed the story! ---")
        elif current_chap:
            logging.warning("Cannot advance: The current chapter is not yet complete.")
        else:
            logging.warning("Cannot advance: The story is not started or is already over.")


# --- Example Usage (for testing) ---
if __name__ == "__main__":
    # 1. Create our chapters
    chapter1 = Chapter(
        title="A Faint Signal",
        description="Your ship's long-range sensors pick up a faint, repeating signal from a nearby uncharted moon.",
        objectives=["Investigate the signal's origin", "Scan the moon for lifeforms"]
    )
    chapter2 = Chapter(
        title="The Crash Site",
        description="The signal leads you to a crashed vessel of unknown design. It's old, alien, and silent.",
        objectives=["Explore the wreckage", "Retrieve the ship's log"]
    )

    # 2. Create and set up the Story Manager
    story_manager = StoryManager()
    story_manager.add_chapter(chapter1)
    story_manager.add_chapter(chapter2)
    
    # 4. Start the story
    story_manager.start_story()

    # 5. Get the current chapter
    current_chapter = story_manager.get_current_chapter()
    if current_chapter:
        # We can still use print here for direct test output, or switch to logging
        logging.info(f"Current Chapter: {current_chapter.title}")
        logging.info(f"Objectives: {current_chapter.objectives}")

    # 6. Try to advance (should fail with a warning)
    story_manager.advance_chapter()

    # 7. Complete objectives for chapter 1
    current_chapter.complete_objective("Investigate the signal's origin")
    current_chapter.complete_objective("Scan the moon for lifeforms")

    # 8. Try to advance again (should succeed with an info message)
    story_manager.advance_chapter()