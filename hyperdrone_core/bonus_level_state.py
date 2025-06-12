# hyperdrone_core/bonus_level_state.py
import pygame
from .state import State

class BonusLevelStartState(State):
    def enter(self, previous_state=None, **kwargs):
        # Initialize bonus level start display
        self.game.bonus_level_start_display_end_time = pygame.time.get_ticks() + 3000  # 3 seconds display
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Skip timer and go directly to bonus level
                    self.game.state_manager.set_state("BonusLevelPlayingState")
    
    def update(self, delta_time):
        current_time = pygame.time.get_ticks()
        if current_time > self.game.bonus_level_start_display_end_time:
            self.game.state_manager.set_state("BonusLevelPlayingState")
    
    def draw(self, surface):
        surface.fill(self.game.gs.BLACK)
        
        # Draw bonus level announcement
        font = self.game.asset_manager.get_font("large_text", 64) or pygame.font.Font(None, 64)
        title_surf = font.render("BONUS LEVEL", True, self.game.gs.GOLD)
        surface.blit(title_surf, title_surf.get_rect(
            center=(self.game.gs.WIDTH // 2, self.game.gs.HEIGHT // 2 - 50)))
        
        # Draw instructions
        font = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
        instr_surf = font.render("Collect all rings before time runs out!", True, self.game.gs.WHITE)
        surface.blit(instr_surf, instr_surf.get_rect(
            center=(self.game.gs.WIDTH // 2, self.game.gs.HEIGHT // 2 + 50)))
        
        # Draw "Press SPACE to start" prompt
        font = self.game.asset_manager.get_font("ui_text", 24) or pygame.font.Font(None, 24)
        prompt_surf = font.render("Press SPACE to start", True, self.game.gs.CYAN)
        surface.blit(prompt_surf, prompt_surf.get_rect(
            center=(self.game.gs.WIDTH // 2, self.game.gs.HEIGHT // 2 + 150)))


class BonusLevelPlayingState(State):
    def enter(self, previous_state=None, **kwargs):
        # Initialize bonus level gameplay
        self.game.combat_controller.reset_combat_state()
        self.game.puzzle_controller.reset_puzzles_state()
        
        # Create maze for bonus level
        self.game.maze = self.game.Maze(is_bonus_level=True)
        
        # Initialize player
        spawn_x, spawn_y = self.game._get_safe_spawn_point(self.game.gs.TILE_SIZE * 0.7, self.game.gs.TILE_SIZE * 0.7)
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        
        self.game.player = self.game.PlayerDrone(
            spawn_x, spawn_y, drone_id, drone_stats, 
            self.game.asset_manager, sprite_key, 'crash', 
            self.game.drone_system
        )
        
        # Set up controllers
        self.game.combat_controller.set_active_entities(
            player=self.game.player, 
            maze=self.game.maze, 
            power_ups_group=self.game.power_ups_group
        )
        
        self.game.puzzle_controller.set_active_entities(
            player=self.game.player, 
            drone_system=self.game.drone_system, 
            scene_manager=self.game.state_manager
        )
        
        # Start bonus level timer
        self.game.bonus_level_timer_start = pygame.time.get_ticks()
        self.game.bonus_level_duration_ms = self.game.gs.get_game_setting("BONUS_LEVEL_DURATION_MS")
        
        # Spawn bonus level collectibles
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.reset_for_level()
            self.game.item_manager.spawn_bonus_level_collectibles(self.game.maze)
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.toggle_pause()
                elif event.key == pygame.K_ESCAPE:
                    self.game.toggle_pause()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        current_time_ms = pygame.time.get_ticks()
        
        # Update player
        if self.game.player:
            self.game.player.update(
                current_time_ms, 
                self.game.maze, 
                self.game.combat_controller.enemy_manager.get_sprites(), 
                self.game.player_actions, 
                self.game.maze.game_area_x_offset if self.game.maze else 0
            )
        
        # Update combat
        self.game.combat_controller.update(current_time_ms, delta_time)
        
        # Update item manager
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.update(current_time_ms, self.game.maze)
        
        # Handle collectible collisions
        self.game._handle_collectible_collisions()
        
        # Check if all rings are collected
        if self.game.level_manager.all_rings_collected():
            self.game.level_manager.complete_bonus_level(success=True)
            self.game.state_manager.set_state("PlayingState")
        
        # Check if time is up
        time_elapsed = current_time_ms - self.game.bonus_level_timer_start
        if time_elapsed >= self.game.bonus_level_duration_ms:
            self.game.level_manager.complete_bonus_level(success=False)
            self.game.state_manager.set_state("PlayingState")
        
        # Update continuous player movement and actions
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
    
    def draw(self, surface):
        surface.fill(self.game.gs.BLACK)
        
        # Draw maze
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        # Draw collectibles and powerups
        for item_group in [
            self.game.collectible_rings_group, 
            self.game.power_ups_group
        ]:
            for item in item_group:
                item.draw(surface, self.game.camera)
        
        # Draw player
        if self.game.player:
            self.game.player.draw(surface)
        
        # Draw timer
        current_time_ms = pygame.time.get_ticks()
        time_elapsed = current_time_ms - self.game.bonus_level_timer_start
        time_remaining = max(0, self.game.bonus_level_duration_ms - time_elapsed)
        seconds_remaining = int(time_remaining / 1000)
        
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        timer_surf = font.render(f"Time: {seconds_remaining}s", True, 
                               self.game.gs.RED if seconds_remaining <= 10 else self.game.gs.WHITE)
        surface.blit(timer_surf, timer_surf.get_rect(center=(self.game.gs.WIDTH // 2, 50)))