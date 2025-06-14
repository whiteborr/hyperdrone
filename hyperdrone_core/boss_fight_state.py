# hyperdrone_core/boss_fight_state.py
import pygame
from .state import State
from settings_manager import get_setting
from entities import Maze, MazeGuardian, PlayerDrone
from drone_management import DRONE_DATA

class BossFightState(State):
    """
    Manages the entire boss battle sequence against the Maze Guardian.
    This state sets up a special arena and controls the win/loss conditions
    for the boss fight.
    """
    def enter(self, previous_state=None, **kwargs):
        """Initializes the boss arena, the player, and the Maze Guardian."""
        print("Entering BossFightState...")
        # Create a specific arena for the boss fight (more open layout)
        self.game.maze = Maze(maze_type="boss_arena")

        # Spawn the player at a designated starting position
        player_spawn_pos = (self.game.maze.game_area_x_offset + 150, get_setting("display", "HEIGHT", 1080) / 2)
        
        # We need to re-initialize the player or reset its position
        if not self.game.player:
            drone_id = self.game.drone_system.get_selected_drone_id()
            drone_stats = self.game.drone_system.get_drone_stats(drone_id)
            sprite_key = drone_config.get("ingame_sprite_path") if (drone_config := DRONE_DATA.get(drone_id)) else None
            self.game.player = PlayerDrone(
                player_spawn_pos[0], player_spawn_pos[1], drone_id, drone_stats,
                self.game.asset_manager, sprite_key, 'crash', self.game.drone_system
            )
        else:
            self.game.player.reset(player_spawn_pos[0], player_spawn_pos[1])
        
        # Spawn the Maze Guardian
        boss_spawn_pos = (get_setting("display", "WIDTH", 1920) - 300, get_setting("display", "HEIGHT", 1080) / 2)
        self.game.combat_controller.maze_guardian = MazeGuardian(
            boss_spawn_pos[0], boss_spawn_pos[1],
            self.game.player,
            self.game.maze,
            self.game.combat_controller, # Pass combat_controller instead of game_controller
            self.game.asset_manager
        )
        self.game.combat_controller.boss_active = True

        # Set up combat controller for the boss fight
        self.game.combat_controller.set_active_entities(
            player=self.game.player,
            maze=self.game.maze
        )
        # Ensure enemy group is clear before boss minions are spawned
        self.game.combat_controller.enemy_manager.reset_all()

    def update(self, delta_time):
        """Update all entities and check for the end of the fight."""
        current_time = pygame.time.get_ticks()

        # If player doesn't exist, something is wrong, exit to prevent crash.
        if not self.game.player:
            self.game.state_manager.set_state("MainMenuState")
            return
            
        self.game.player.update(current_time, self.game.maze, self.game.combat_controller.enemy_manager.get_sprites(), self.game.player_actions, self.game.maze.game_area_x_offset if self.game.maze else 0)
        self.game.combat_controller.update(current_time, delta_time)

        # Check if the boss has been defeated
        if self.game.combat_controller.boss_active and not self.game.combat_controller.maze_guardian.alive:
            self.game.story_manager.complete_objective_by_id("c2_defeat_guardian")
            # For now, let's go back to the main menu after winning.
            # In the future, this will transition to Chapter 3.
            self.game.state_manager.set_state("MainMenuState")
            return

        # Check if the player has been defeated
        if not self.game.player.alive:
            self.game.state_manager.set_state("GameOverState")

    def handle_events(self, events):
        """Handle player input during the boss fight."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)

    def draw(self, surface):
        """Render the boss fight scene."""
        surface.fill(get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30)))
        
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        if self.game.player:
            self.game.player.draw(surface)
            
        if self.game.combat_controller.boss_active:
            self.game.combat_controller.maze_guardian.draw(surface)
            
        self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        self.game.ui_manager.draw_gameplay_hud()
