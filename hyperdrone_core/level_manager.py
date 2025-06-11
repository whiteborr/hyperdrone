# hyperdrone_core/level_manager.py
import pygame
import random
import logging

import game_settings as gs
from entities import PlayerDrone, Maze

logger = logging.getLogger(__name__)

class LevelManager:
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        
        # Level state variables
        self.level = 1
        self.score = 0
        
        # Ring collection variables
        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.total_rings_per_level = gs.get_game_setting("MAX_RINGS_PER_LEVEL", 5)
        self.animating_rings_to_hud = []
        
        # Position rings at the right side of the screen to match UI
        self.ring_ui_base_pos = (
            gs.get_game_setting("WIDTH") - gs.HUD_RING_ICON_AREA_X_OFFSET,
            gs.get_game_setting("HEIGHT") - gs.get_game_setting("BOTTOM_PANEL_HEIGHT") + gs.HUD_RING_ICON_AREA_Y_OFFSET
        )
        
        # Level timer variables
        self.level_start_time = pygame.time.get_ticks()
        self.level_timer_duration = gs.get_game_setting("LEVEL_TIMER_DURATION", 120000)
        self.level_timer_warning = gs.get_game_setting("LEVEL_TIMER_WARNING_THRESHOLD", 30000)
        self.border_flash_state = False
        self.last_border_flash_time = 0
        self.border_flash_interval = 500  # Flash every 500ms when time is low
        
        # Level state variables
        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False
        self.level_clear_fragment_spawned_this_level = False
    
    def reset(self):
        """Reset level manager state for a new game"""
        self.level = 1
        self.score = 0
        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.animating_rings_to_hud = []
        
        # Reset timer
        self.level_start_time = pygame.time.get_ticks()
        self.border_flash_state = False
        self.last_border_flash_time = 0
        
        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False
        self.level_clear_fragment_spawned_this_level = False
    
    def add_score(self, points):
        """Add points to the score"""
        self.score += points
        return self.score
    
    def collect_ring(self, ring_position):
        """Handle ring collection and animation"""
        self.collected_rings_count += 1
        self.score += 10
        self._animate_ring_to_hud(ring_position)
        return self.collected_rings_count
    
    def _animate_ring_to_hud(self, start_pos):
        """Create an animation for a collected ring moving to the HUD"""
        # Calculate the exact position of the collected ring in the HUD
        collected_count = self.collected_rings_count - 1  # -1 because we already incremented the count
        
        # Use the exact same calculation as in the UI
        rings_x = self.ring_ui_base_pos[0]
        rings_y = self.ring_ui_base_pos[1]
        
        # Calculate the center of the target icon
        target_x = rings_x + collected_count * (gs.HUD_RING_ICON_SIZE + gs.HUD_RING_ICON_SPACING) + gs.HUD_RING_ICON_SIZE // 2
        target_y = rings_y + gs.HUD_RING_ICON_SIZE // 2
        
        self.animating_rings_to_hud.append({
            'pos': list(start_pos),
            'start_time': pygame.time.get_ticks(),
            'duration': 1000,  # 1 second animation
            'start_pos': start_pos,
            'target_pos': (target_x, target_y)
        })
    
    def update_ring_animations(self, current_time):
        """Update ring animations and return completed animations count"""
        completed = 0
        
        # Process each animating ring
        for i in range(len(self.animating_rings_to_hud) - 1, -1, -1):
            ring_data = self.animating_rings_to_hud[i]
            elapsed = current_time - ring_data['start_time']
            progress = min(1.0, elapsed / ring_data['duration'])
            
            if progress >= 1.0:
                # Animation complete
                self.displayed_collected_rings_count += 1
                self.animating_rings_to_hud.pop(i)
                completed += 1
                
        return completed
    
    def draw_ring_animations(self, surface, ring_icon):
        """Draw ring animations on the surface"""
        current_time = pygame.time.get_ticks()
        
        # Draw level border with timer
        self._draw_level_timer_border(surface, current_time)
        
        # Process each animating ring
        for i in range(len(self.animating_rings_to_hud) - 1, -1, -1):
            ring_data = self.animating_rings_to_hud[i]
            elapsed = current_time - ring_data['start_time']
            progress = min(1.0, elapsed / ring_data['duration'])
            
            if progress >= 1.0:
                # Animation complete
                self.displayed_collected_rings_count += 1
                self.animating_rings_to_hud.pop(i)
                continue
                
            # Calculate current position using easing
            ease_progress = 1 - (1 - progress) ** 3  # Cubic ease out
            x = ring_data['start_pos'][0] + (ring_data['target_pos'][0] - ring_data['start_pos'][0]) * ease_progress
            y = ring_data['start_pos'][1] + (ring_data['target_pos'][1] - ring_data['start_pos'][1]) * ease_progress
            
            # Draw the ring icon
            if ring_icon:
                icon_size = int(gs.TILE_SIZE * 0.3 * (1 + 0.5 * (1 - progress)))  # Shrink as it moves
                scaled_icon = pygame.transform.smoothscale(ring_icon, (icon_size, icon_size))
                icon_rect = scaled_icon.get_rect(center=(x, y))
                surface.blit(scaled_icon, icon_rect)
                
    def _draw_level_timer_border(self, surface, current_time):
        """Draw a border around the screen that shows the level timer"""
        # Calculate remaining time
        elapsed_time = current_time - self.level_start_time
        remaining_time = max(0, self.level_timer_duration - elapsed_time)
        
        # Format time as MM:SS
        minutes = int(remaining_time / 60000)
        seconds = int((remaining_time % 60000) / 1000)
        time_str = f"{minutes:02}:{seconds:02}"
        
        # Draw timer text
        font = pygame.font.Font(None, 36)
        text_surf = font.render(time_str, True, gs.WHITE)
        text_rect = text_surf.get_rect(center=(gs.WIDTH // 2, 30))
        surface.blit(text_surf, text_rect)
        
        # Determine border color
        border_color = gs.BLUE
        
        # Flash red when time is running low
        if remaining_time < self.level_timer_warning:
            # Update flash state
            if current_time - self.last_border_flash_time > self.border_flash_interval:
                self.border_flash_state = not self.border_flash_state
                self.last_border_flash_time = current_time
                
            if self.border_flash_state:
                border_color = gs.RED
        
        # Draw border (4 lines around the screen)
        border_width = 4
        pygame.draw.rect(surface, border_color, (0, 0, gs.WIDTH, gs.HEIGHT), border_width)
    
    def check_level_clear_condition(self):
        """Check if the level has been cleared and progress to the next level if so"""
        current_time = pygame.time.get_ticks()
        
        # Check if time has run out
        if current_time - self.level_start_time >= self.level_timer_duration:
            # Time's up - player loses a life
            if self.game_controller.player and self.game_controller.player.alive:
                self.game_controller._handle_player_death_or_life_loss("Time's up!")
            return False
            
        # Check if all rings are collected and all enemies are defeated
        all_rings_collected = self.collected_rings_count >= self.total_rings_per_level
        all_enemies_defeated = self.game_controller.combat_controller.enemy_manager.get_active_enemies_count() == 0
        
        # Only stop player movement when both conditions are met
        if all_rings_collected and all_enemies_defeated:
            # Stop the player drone when all conditions are met
            if self.game_controller.player and hasattr(self.game_controller.player, 'is_cruising'):
                self.game_controller.player.is_cruising = False
                
            # Wait for all ring animations to complete before progressing
            if len(self.animating_rings_to_hud) > 0:
                return False
                
            return self._advance_to_next_level()
        return False
    
    def _advance_to_next_level(self):
        """Advance to the next level and set up the new level"""
        # Store current weapon mode before creating new player
        current_weapon_mode = self.game_controller.player.current_weapon_mode
        
        # Progress to the next level
        self.level += 1
        self.score += 100  # Bonus for clearing the level
        
        # Reset for the next level
        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.animating_rings_to_hud = []
        
        # Reset level timer
        self.level_start_time = pygame.time.get_ticks()
        self.border_flash_state = False
        self.last_border_flash_time = 0
        
        # Clear all items
        if hasattr(self.game_controller, 'item_manager'):
            self.game_controller.item_manager.clear_all_items()
        
        # Create a new maze
        self.game_controller.maze = Maze()
        
        # Spawn the player at a safe location
        spawn_x, spawn_y = self.game_controller._get_safe_spawn_point(gs.TILE_SIZE * 0.7, gs.TILE_SIZE * 0.7)
        drone_id = self.game_controller.drone_system.get_selected_drone_id()
        drone_stats = self.game_controller.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        self.game_controller.player = PlayerDrone(
            spawn_x, spawn_y, drone_id, drone_stats,
            self.game_controller.asset_manager, sprite_key, 'crash',
            self.game_controller.drone_system
        )
                                 
        # Restore weapon mode from previous level
        while self.game_controller.player.current_weapon_mode != current_weapon_mode:
            self.game_controller.player.cycle_weapon_state()
        
        # Set up the new level
        self.game_controller.combat_controller.set_active_entities(
            player=self.game_controller.player, 
            maze=self.game_controller.maze, 
            power_ups_group=self.game_controller.power_ups_group
        )
        self.game_controller.combat_controller.enemy_manager.spawn_enemies_for_level(self.level)
        
        # Spawn rings for the new level
        if hasattr(self.game_controller, 'item_manager'):
            self.game_controller.item_manager.reset_for_level()
        
        # Display a message
        self.game_controller.set_story_message(f"Level {self.level} - Collect all rings!", 3000)
        
        # Play a sound
        self.game_controller.play_sound('level_up')
        
        return True