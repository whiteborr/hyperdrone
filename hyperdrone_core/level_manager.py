# hyperdrone_core/level_manager.py
from pygame.time import get_ticks
from pygame.font import Font
from pygame.transform import smoothscale
from pygame.draw import rect as draw_rect
from logging import getLogger

from settings_manager import get_setting
from constants import WHITE, BLUE, RED
from entities import PlayerDrone, Maze

logger = getLogger(__name__)

class LevelManager:
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        
        # Level state
        self.level = 1
        self.score = 0
        self.chapter1_level = 1
        self.chapter1_max_levels = get_setting("progression", "CHAPTER_1_MAX_LEVELS", 7)
        
        # Ring collection
        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.total_rings_per_level = get_setting("collectibles", "MAX_RINGS_PER_LEVEL", 5)
        self.animating_rings_to_hud = []
        
        # Timer
        self.level_start_time = get_ticks()
        self.level_timer_duration = get_setting("progression", "LEVEL_TIMER_DURATION", 120000)
        self.level_timer_warning = get_setting("progression", "LEVEL_TIMER_WARNING_THRESHOLD", 30000)
        self.border_flash_state = False
        self.last_border_flash_time = 0
        self.border_flash_interval = 500
        
        # Timer pause
        self.timer_paused = False
        self.pause_start_time = 0
        self.total_paused_time = 0
        
        # Level flags
        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False
        self.level_clear_fragment_spawned_this_level = False
        self.boss_fight_triggered = False
        
        # Register events
        if hasattr(game_controller_ref, 'event_manager'):
            from hyperdrone_core.game_events import EnemyDefeatedEvent
            game_controller_ref.event_manager.register_listener(EnemyDefeatedEvent, self.on_enemy_defeated)

    def on_level_completed(self, event):
        logger.info(f"LevelCompletedEvent received for level {event.level_index}")

    def reset(self):
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
        self.score += points
        return self.score
        
    def on_enemy_defeated(self, event):
        self.add_score(event.score_value)
    
    def collect_ring(self, ring_position):
        current_state = self.game_controller.state_manager.get_current_state_id()
        valid_states = ["PlayingState", "EarthCoreState", "FireCoreState", "AirCoreState", "WaterCoreState", "OrichalcCoreState"]
        
        if current_state in valid_states:
            self.collected_rings_count += 1
            self.score += 10
            self._animate_ring_to_hud(ring_position)
            return self.collected_rings_count
        return 0
    
    def _animate_ring_to_hud(self, start_pos):
        ring_index = self.collected_rings_count - 1
        
        # Calculate HUD position
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        bottom_panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        panel_y = height - bottom_panel_height
        
        hud_x_offset = get_setting("display", "HUD_RING_ICON_AREA_X_OFFSET", 150)
        hud_y_offset = get_setting("display", "HUD_RING_ICON_AREA_Y_OFFSET", 30)
        icon_size = get_setting("display", "HUD_RING_ICON_SIZE", 24)
        icon_spacing = get_setting("display", "HUD_RING_ICON_SPACING", 5)
        
        rings_x = width - hud_x_offset
        rings_y = panel_y + hud_y_offset
        
        target_x = rings_x + ring_index * (icon_size + icon_spacing) + icon_size // 2
        target_y = rings_y + icon_size // 2
        
        if ring_index < self.total_rings_per_level:
            self.animating_rings_to_hud.append({
                'pos': list(start_pos),
                'start_time': get_ticks(),
                'duration': 1000,
                'start_pos': start_pos,
                'target_pos': (target_x, target_y)
            })
    
    def update_ring_animations(self, current_time):
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
        current_time = get_ticks()
        current_state = self.game_controller.state_manager.get_current_state_id()
        valid_states = ["PlayingState", "EarthCoreState", "FireCoreState", "AirCoreState", "WaterCoreState", "OrichalcCoreState"]
        
        if current_state in valid_states:
            self._draw_level_timer_border(surface, current_time)
            
            for i in range(len(self.animating_rings_to_hud) - 1, -1, -1):
                ring_data = self.animating_rings_to_hud[i]
                elapsed = current_time - ring_data['start_time']
                progress = min(1.0, elapsed / ring_data['duration'])
                
                if progress >= 1.0:
                    self.displayed_collected_rings_count += 1
                    self.animating_rings_to_hud.pop(i)
                    continue
                    
                # Animate ring to HUD
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
        if not self.timer_paused:
            self.timer_paused = True
            self.pause_start_time = get_ticks()
    
    def resume_timer(self):
        if self.timer_paused:
            self.timer_paused = False
            self.total_paused_time += get_ticks() - self.pause_start_time
            self.pause_start_time = 0
    
    def _get_elapsed_time(self, current_time):
        """Calculate elapsed time accounting for pauses"""
        elapsed = current_time - self.level_start_time - self.total_paused_time
        if self.timer_paused:
            elapsed -= current_time - self.pause_start_time
        return elapsed
    
    def _draw_level_timer_border(self, surface, current_time):
        elapsed_time = self._get_elapsed_time(current_time)
        remaining_time = max(0, self.level_timer_duration - elapsed_time)
        
        # Draw timer text
        minutes = int(remaining_time / 60000)
        seconds = int((remaining_time % 60000) / 1000)
        time_str = f"{minutes:02}:{seconds:02}"
        
        font = Font(None, 36)
        text_surf = font.render(time_str, True, WHITE)
        width = get_setting("display", "WIDTH", 1920)
        text_rect = text_surf.get_rect(center=(width // 2, 30))
        surface.blit(text_surf, text_rect)
        
        # Draw border with warning flash
        border_color = BLUE
        if remaining_time < self.level_timer_warning:
            if current_time - self.last_border_flash_time > self.border_flash_interval:
                self.border_flash_state = not self.border_flash_state
                self.last_border_flash_time = current_time
            if self.border_flash_state:
                border_color = RED
        
        height = get_setting("display", "HEIGHT", 1080)
        draw_rect(surface, border_color, (0, 0, width, height), 4)
    
    def check_level_clear_condition(self):
        current_time = get_ticks()
        current_state = self.game_controller.state_manager.get_current_state_id()

        # Check time limit
        elapsed_time = self._get_elapsed_time(current_time)
        if current_state == "PlayingState" and elapsed_time >= self.level_timer_duration:
            if self.game_controller.player and self.game_controller.player.alive:
                self.game_controller._handle_player_death_or_life_loss("Time's up!")
            return False
            
        # Check ring collection
        rings_collected = len(self.game_controller.collectible_rings_group) == 0
        
        if rings_collected:
            if self.game_controller.player and hasattr(self.game_controller.player, 'is_cruising'):
                self.game_controller.player.is_cruising = False
            
            # Wait for ring animations to complete
            if len(self.animating_rings_to_hud) > 0:
                return False

            # Check for boss fight transition
            current_chapter = self.game_controller.story_manager.get_current_chapter()

            # Chapter 1 completion -> Tempest boss fight
            if (current_chapter and current_chapter.chapter_id == "chapter_1" and 
                self.chapter1_level >= self.chapter1_max_levels and not self.boss_fight_triggered):
                logger.info("Chapter 1 completed! Triggering Tempest boss fight")
                self.boss_fight_triggered = True
                self.game_controller.story_manager.complete_objective_by_id("c1_clear_hostiles")
                self.game_controller.state_manager.set_state('TempestFightState', next_level=self.level + 1)
                return True

            # Regular level advancement
            logger.info(f"Level {self.level} cleared! Advancing to next level")
            return self._advance_to_next_level()
            
        return False
    
    def _advance_to_next_level(self):
        # Save current weapon
        current_weapon_mode = self.game_controller.player.current_weapon_mode
        
        # Update level state
        self.level += 1
        self.score += 100
        
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            self.chapter1_level += 1
        
        # Reset level variables
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
        
        # Clear items and create new maze
        if hasattr(self.game_controller, 'item_manager'):
            self.game_controller.item_manager.clear_all_items()
        
        self.game_controller.maze = Maze()
        
        # Create new player
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
        
        # Restore weapon mode
        while self.game_controller.player.current_weapon_mode != current_weapon_mode:
            self.game_controller.player.cycle_weapon_state()
        
        # Setup combat and spawn entities
        self.game_controller.combat_controller.set_active_entities(
            player=self.game_controller.player, 
            maze=self.game_controller.maze, 
            power_ups_group=self.game_controller.power_ups_group
        )
        self.game_controller.combat_controller.enemy_manager.spawn_enemies_for_level(self.level)
        
        # Reset items for new level
        if hasattr(self.game_controller, 'item_manager'):
            self.game_controller.item_manager.reset_for_level()
        
        # Show level message
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            message = f"Chapter 1 - Level {self.chapter1_level} of {self.chapter1_max_levels}"
        else:
            message = f"Level {self.level} - Collect all rings!"
        
        self.game_controller.set_story_message(message, 3000)
        self.game_controller.play_sound('level_up')
        
        return True

    def create_maze(self):
        return Maze()