# hyperdrone_core/level_manager.py
from pygame.time import get_ticks
from pygame.font import Font
from pygame.transform import smoothscale
from pygame.draw import rect as draw_rect
from logging import getLogger

from settings_manager import get_setting, set_setting, get_asset_path
from constants import (
    GAME_STATE_PLAYING, WHITE, BLUE, RED, HUD_RING_ICON_AREA_X_OFFSET,
    HUD_RING_ICON_AREA_Y_OFFSET, HUD_RING_ICON_SIZE, HUD_RING_ICON_SPACING
)
from entities import PlayerDrone, Maze

logger = getLogger(__name__)

class LevelManager:
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        
        # Level state variables
        self.level = 1
        self.score = 0
        
        # Chapter 1 specific tracking
        self.chapter1_level = 1
        self.chapter1_max_levels = get_setting("progression", "CHAPTER_1_MAX_LEVELS", 7)
        
        # Ring collection variables
        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.total_rings_per_level = get_setting("collectibles", "MAX_RINGS_PER_LEVEL", 5)
        self.animating_rings_to_hud = []
        
        # Level timer variables
        self.level_start_time = get_ticks()
        self.level_timer_duration = get_setting("progression", "LEVEL_TIMER_DURATION", 120000)
        self.level_timer_warning = get_setting("progression", "LEVEL_TIMER_WARNING_THRESHOLD", 30000)
        self.border_flash_state = False
        self.last_border_flash_time = 0
        self.border_flash_interval = 500  # Flash every 500ms when time is low
        
        # Timer pause functionality
        self.timer_paused = False
        self.pause_start_time = 0
        self.total_paused_time = 0
        
        # Level state variables
        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False
        self.level_clear_fragment_spawned_this_level = False
        self.boss_fight_triggered = False
        
        # Register for events
        if hasattr(game_controller_ref, 'event_manager'):
            from hyperdrone_core.game_events import EnemyDefeatedEvent
            game_controller_ref.event_manager.register_listener(EnemyDefeatedEvent, self.on_enemy_defeated)

    def on_level_completed(self, event):
        """
        Handles the logic for transitioning between chapters and to boss fights.
        This is a placeholder for the logic now implemented in check_level_clear_condition.
        """
        logger.info(f"LevelCompletedEvent received for level {event.level_index}")
        # This event handler can be expanded to manage more complex inter-level logic
        # For now, the main progression logic is in check_level_clear_condition
        pass

    def reset(self):
        """Reset level manager state for a new game"""
        self.level = 1
        self.score = 0
        self.chapter1_level = 1
        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.animating_rings_to_hud = []
        
        # Reset timer
        self.level_start_time = get_ticks()
        self.border_flash_state = False
        self.last_border_flash_time = 0
        self.timer_paused = False
        self.pause_start_time = 0
        self.total_paused_time = 0
        
        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False
        self.level_clear_fragment_spawned_this_level = False
        self.boss_fight_triggered = False
    
    def add_score(self, points):
        """Add points to the score"""
        self.score += points
        return self.score
        
    def on_enemy_defeated(self, event):
        """Handle enemy defeated event"""
        self.add_score(event.score_value)
    
    def collect_ring(self, ring_position):
        """Handle ring collection and animation"""
        current_game_state = self.game_controller.state_manager.get_current_state_id()
        if current_game_state in ["PlayingState", "EarthCoreState", "FireCoreState", "AirCoreState", "WaterCoreState", "OrichalcCoreState"]:
            self.collected_rings_count += 1
            self.score += 10
            self._animate_ring_to_hud(ring_position)
            return self.collected_rings_count
        return 0
    
    def _animate_ring_to_hud(self, start_pos):
        """Create an animation for a collected ring moving to the HUD"""
        ring_index = self.collected_rings_count - 1
        
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        bottom_panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        panel_y = height - bottom_panel_height
        
        hud_ring_icon_area_x_offset = get_setting("display", "HUD_RING_ICON_AREA_X_OFFSET", 150)
        hud_ring_icon_area_y_offset = get_setting("display", "HUD_RING_ICON_AREA_Y_OFFSET", 30)
        hud_ring_icon_size = get_setting("display", "HUD_RING_ICON_SIZE", 24)
        hud_ring_icon_spacing = get_setting("display", "HUD_RING_ICON_SPACING", 5)
        
        rings_x = width - hud_ring_icon_area_x_offset
        rings_y = panel_y + hud_ring_icon_area_y_offset
        
        icon_x = rings_x + ring_index * (hud_ring_icon_size + hud_ring_icon_spacing)
        target_x = icon_x + hud_ring_icon_size // 2
        target_y = rings_y + hud_ring_icon_size // 2
        
        if ring_index < self.total_rings_per_level:
            self.animating_rings_to_hud.append({
                'pos': list(start_pos),
                'start_time': get_ticks(),
                'duration': 1000,
                'start_pos': start_pos,
                'target_pos': (target_x, target_y)
            })
    
    def update_ring_animations(self, current_time):
        """Update ring animations and return completed animations count"""
        completed = 0
        for i in range(len(self.animating_rings_to_hud) - 1, -1, -1):
            ring_data = self.animating_rings_to_hud[i]
            elapsed = current_time - ring_data['start_time']
            progress = min(1.0, elapsed / ring_data['duration'])
            if progress >= 1.0:
                self.displayed_collected_rings_count += 1
                self.animating_rings_to_hud.pop(i)
                completed += 1
        return completed
    
    def draw_ring_animations(self, surface, ring_icon):
        """Draw ring animations on the surface"""
        current_time = get_ticks()
        current_game_state = self.game_controller.state_manager.get_current_state_id()
        if current_game_state in ["PlayingState", "EarthCoreState", "FireCoreState", "AirCoreState", "WaterCoreState", "OrichalcCoreState"]:
            self._draw_level_timer_border(surface, current_time)
            for i in range(len(self.animating_rings_to_hud) - 1, -1, -1):
                ring_data = self.animating_rings_to_hud[i]
                elapsed = current_time - ring_data['start_time']
                progress = min(1.0, elapsed / ring_data['duration'])
                if progress >= 1.0:
                    self.displayed_collected_rings_count += 1
                    self.animating_rings_to_hud.pop(i)
                    continue
                ease_progress = 1 - (1 - progress) ** 3
                x = ring_data['start_pos'][0] + (ring_data['target_pos'][0] - ring_data['start_pos'][0]) * ease_progress
                y = ring_data['start_pos'][1] + (ring_data['target_pos'][1] - ring_data['start_pos'][1]) * ease_progress
                if ring_icon:
                    tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                    icon_size = int(tile_size * 0.3 * (1 + 0.5 * (1 - progress)))
                    scaled_icon = smoothscale(ring_icon, (icon_size, icon_size))
                    icon_rect = scaled_icon.get_rect(center=(x, y))
                    surface.blit(scaled_icon, icon_rect)
                
    def pause_timer(self):
        """Pause the level timer"""
        if not self.timer_paused:
            self.timer_paused = True
            self.pause_start_time = get_ticks()
    
    def resume_timer(self):
        """Resume the level timer"""
        if self.timer_paused:
            self.timer_paused = False
            self.total_paused_time += get_ticks() - self.pause_start_time
            self.pause_start_time = 0
    
    def _draw_level_timer_border(self, surface, current_time):
        """Draw a border around the screen that shows the level timer"""
        elapsed_time = current_time - self.level_start_time - self.total_paused_time
        if self.timer_paused:
            elapsed_time -= current_time - self.pause_start_time
        remaining_time = max(0, self.level_timer_duration - elapsed_time)
        minutes = int(remaining_time / 60000)
        seconds = int((remaining_time % 60000) / 1000)
        time_str = f"{minutes:02}:{seconds:02}"
        
        font = Font(None, 36)
        text_surf = font.render(time_str, True, WHITE)
        width = get_setting("display", "WIDTH", 1920)
        text_rect = text_surf.get_rect(center=(width // 2, 30))
        surface.blit(text_surf, text_rect)
        
        border_color = BLUE
        if remaining_time < self.level_timer_warning:
            if current_time - self.last_border_flash_time > self.border_flash_interval:
                self.border_flash_state = not self.border_flash_state
                self.last_border_flash_time = current_time
            if self.border_flash_state:
                border_color = RED
        
        border_width = 4
        height = get_setting("display", "HEIGHT", 1080)
        draw_rect(surface, border_color, (0, 0, width, height), border_width)
    
    def check_level_clear_condition(self):
        """
        Check if the level has been cleared and progress to the next level if so.
        """
        current_time = get_ticks()
        current_game_state = self.game_controller.state_manager.get_current_state_id()

        elapsed_time = current_time - self.level_start_time - self.total_paused_time
        if self.timer_paused:
            elapsed_time -= current_time - self.pause_start_time
        if current_game_state == "PlayingState" and elapsed_time >= self.level_timer_duration:
            if self.game_controller.player and self.game_controller.player.alive:
                self.game_controller._handle_player_death_or_life_loss("Time's up!")
            return False
            
        rings_collected = len(self.game_controller.collectible_rings_group) == 0
        
        if rings_collected:
            if self.game_controller.player and hasattr(self.game_controller.player, 'is_cruising'):
                self.game_controller.player.is_cruising = False
            
            rings_animating = len(self.animating_rings_to_hud) > 0
            if rings_animating:
                return False

            # --- BOSS FIGHT TRANSITION LOGIC ---
            current_chapter = self.game_controller.story_manager.get_current_chapter()

            # After completing all levels in Chapter 1, trigger the Tempest boss fight.
            if current_chapter and current_chapter.chapter_id == "chapter_1" and self.chapter1_level >= self.chapter1_max_levels and not self.boss_fight_triggered:
                logger.info(f"Chapter 1 completed! Triggering Tempest boss fight.")
                self.boss_fight_triggered = True
                self.game_controller.story_manager.complete_objective_by_id("c1_clear_hostiles")
                # next_level is the level to go to *after* the boss fight.
                self.game_controller.state_manager.set_state('TempestFightState', next_level=self.level + 1)
                return True # Level progression handled by state change.

            # After completing all levels in Chapter 2, trigger the Maze Guardian boss fight.
            # (This is a placeholder for when Chapter 2 is fully implemented).
            # if current_chapter and current_chapter.chapter_id == "chapter_2" and self.chapter2_level >= self.chapter2_max_levels:
            #     logger.info(f"Chapter 2 completed! Triggering Maze Guardian boss fight.")
            #     self.game_controller.state_manager.set_state('BossFightState', boss_id='maze_guardian', next_level=self.level + 1)
            #     return True

            # If not a boss transition, advance to the next regular level.
            logger.info(f"Level {self.level} cleared! Advancing to next level.")
            return self._advance_to_next_level()
            
        return False
    
    def _advance_to_next_level(self):
        """Advance to the next regular maze level and set it up"""
        current_weapon_mode = self.game_controller.player.current_weapon_mode
        
        self.level += 1
        self.score += 100
        
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            self.chapter1_level += 1
        
        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.animating_rings_to_hud = []
        
        self.level_start_time = get_ticks()
        self.border_flash_state = False
        self.last_border_flash_time = 0
        self.timer_paused = False
        self.pause_start_time = 0
        self.total_paused_time = 0
        
        if hasattr(self.game_controller, 'item_manager'):
            self.game_controller.item_manager.clear_all_items()
        
        self.game_controller.maze = Maze()
        
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        spawn_x, spawn_y = self.game_controller._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
        drone_id = self.game_controller.drone_system.get_selected_drone_id()
        drone_stats = self.game_controller.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        self.game_controller.player = PlayerDrone(
            spawn_x, spawn_y, drone_id, drone_stats,
            self.game_controller.asset_manager, sprite_key, 'crash',
            self.game_controller.drone_system
        )
                                 
        while self.game_controller.player.current_weapon_mode != current_weapon_mode:
            self.game_controller.player.cycle_weapon_state()
        
        self.game_controller.combat_controller.set_active_entities(
            player=self.game_controller.player, 
            maze=self.game_controller.maze, 
            power_ups_group=self.game_controller.power_ups_group
        )
        self.game_controller.combat_controller.enemy_manager.spawn_enemies_for_level(self.level)
        
        if hasattr(self.game_controller, 'item_manager'):
            self.game_controller.item_manager.reset_for_level()
        
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            self.game_controller.set_story_message(f"Chapter 1 - Level {self.chapter1_level} of {self.chapter1_max_levels}", 3000)
        else:
            self.game_controller.set_story_message(f"Level {self.level} - Collect all rings!", 3000)
        
        self.game_controller.play_sound('level_up')
        
        return True

    def create_maze(self):
        """Create a new maze for the current level"""
        return Maze()
