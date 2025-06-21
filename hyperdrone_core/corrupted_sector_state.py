# hyperdrone_core/corrupted_sector_state.py
import pygame
from .state import State
from settings_manager import get_setting
from entities import Maze # We can create a new Maze type for this chapter later

class CorruptedSectorState(State):
    """
    Manages the gameplay for Chapter 3: The Corrupted Sector.
    This state will feature environmental puzzles, hazards, and lore collection.
    """
    def enter(self, previous_state=None, **kwargs):
        """Initializes the corrupted sector level."""
        print("Entering CorruptedSectorState...")
        self.game.maze = Maze(maze_type="corrupted") 

        if self.game.player:
            spawn_x, spawn_y = self.game._get_safe_spawn_point(
                self.game.player.rect.width, self.game.player.rect.height
            )
            self.game.player.reset(spawn_x, spawn_y)
        
        # Spawn the corrupted logs for this chapter's objectives
        log_ids = ["log_alpha", "log_beta"] # As defined in the StoryManager
        self.game.item_manager.spawn_corrupted_logs(self.game.maze, log_ids)

        current_chapter = self.game.story_manager.get_current_chapter()
        if not (current_chapter and current_chapter.chapter_id == "chapter_3"):
             print("Warning: Entered CorruptedSectorState but not on Chapter 3 in story.")

    def update(self, delta_time):
        """Update game logic for the corrupted sector."""
        current_time = pygame.time.get_ticks()

        if not self.game.player:
            self.game.state_manager.set_state("MainMenuState")
            return
            
        self.game.player.update(current_time, self.game.maze, self.game.combat_controller.enemy_manager.get_sprites(), self.game.player_actions, self.game.maze.game_area_x_offset if self.game.maze else 0)
        self.game.combat_controller.update(current_time, delta_time)

        # Check for player collection of logs
        self.game._handle_collectible_collisions()
        
        # Check if all objectives for Chapter 3 are complete
        current_chapter = self.game.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_3" and current_chapter.is_complete():
            # In the future, this will transition to Chapter 4
            self.game.state_manager.set_state("MainMenuState") # Placeholder transition
            print("Chapter 3 Complete! Transitioning...")

        if not self.game.player.alive:
            self.game.state_manager.set_state("GameOverState")

    def handle_events(self, events):
        """Handle player input."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)

    def draw(self, surface):
        """Render the corrupted sector."""
        surface.fill((30, 10, 30))
        
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
            
        # Draw the corrupted logs
        if self.game.corrupted_logs_group:
            self.game.corrupted_logs_group.draw(surface)

        if self.game.player:
            self.game.player.draw(surface)
            
        self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        self.game.ui_manager.draw_gameplay_hud()
