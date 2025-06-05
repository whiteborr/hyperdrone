# entities/maze_guardian.py
import pygame
import math
import random
import os

import game_settings as gs
from game_settings import (
    TILE_SIZE, WIDTH, GAME_PLAY_AREA_HEIGHT,
    MAZE_GUARDIAN_SPRITE_PATH, MAZE_GUARDIAN_COLOR,
    MAZE_GUARDIAN_SPEED, MAZE_GUARDIAN_HEALTH,
    MAZE_GUARDIAN_LASER_COOLDOWN, MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS,
    SENTINEL_DRONE_SPRITE_PATH, SENTINEL_DRONE_HEALTH, SENTINEL_DRONE_SPEED,
    RED, YELLOW, ORANGE, DARK_GREY, BLACK, WHITE, GOLD, GREEN
)
from .base_drone import BaseDrone # Assuming MazeGuardian might inherit or use its principles
from .enemy import SentinelDrone # For spawning minions
# Bullet class might not be needed if it only shoots lasers/special projectiles now
# from .bullet import Bullet, LightningZap # LightningZap for laser

class MazeGuardian(BaseDrone):
    def __init__(self, x, y, player_ref, maze_ref, game_controller_ref):
        self.visual_size = (int(TILE_SIZE * 2.8), int(TILE_SIZE * 2.8)) # Larger boss sprite
        super().__init__(x, y, size=self.visual_size[0], speed=gs.get_game_setting("MAZE_GUARDIAN_SPEED"))

        self.player_ref = player_ref
        self.maze_ref = maze_ref
        self.game_controller_ref = game_controller_ref # For sounds, etc.
        self.total_health_points = gs.get_game_setting("MAZE_GUARDIAN_HEALTH")
        self.alive = True

        self.original_image = None
        self.image = None
        self._load_sprite(gs.get_game_setting("MAZE_GUARDIAN_SPRITE_PATH"))

        self.rect = self.image.get_rect(center=(x, y))
        # Collision rect for physical interaction, if any (can be same as visual or smaller)
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.1, -self.rect.height * 0.1)

        # Corner targets
        self.corner_size = (int(self.visual_size[0] * 0.25), int(self.visual_size[1] * 0.25)) # Size of each corner
        self.health_per_corner = self.total_health_points / 4
        self.corners = []
        self._initialize_corners()

        # Timers for other abilities (laser, minions) - can remain
        self.last_laser_time = pygame.time.get_ticks() + 3000 # Delay initial laser
        self.laser_cooldown = gs.get_game_setting("MAZE_GUARDIAN_LASER_COOLDOWN")
        self.laser_beams = pygame.sprite.Group() # Assuming lasers are sprite-based

        self.last_minion_spawn_time = pygame.time.get_ticks()
        self.minion_spawn_cooldown = gs.get_game_setting("MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS")
        
        # State for movement/AI - can remain
        self.target_pos = None
        self.move_timer = 0
        self.MOVE_INTERVAL = 3000 # milliseconds, time between choosing new target position

        # Bullets group (will be empty if not shooting bullets anymore)
        self.bullets = pygame.sprite.Group()


    def _load_sprite(self, sprite_path):
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.smoothscale(loaded_image, self.visual_size)
            except pygame.error as e:
                pass # Error loading sprite
        
        if self.original_image is None: # Fallback if sprite loading failed
            self.original_image = pygame.Surface(self.visual_size, pygame.SRCALPHA)
            self.original_image.fill(gs.get_game_setting("MAZE_GUARDIAN_COLOR", (80,0,120)))
            pygame.draw.rect(self.original_image, WHITE, self.original_image.get_rect(), 3) # Border
        
        self.image = self.original_image.copy()


    def _initialize_corners(self):
        self.corners = []
        # Define relative offsets from the boss's center to each corner's center
        # Using half main width/height for offsets to place corners at the visual edges
        half_main_w = self.rect.width / 2
        half_main_h = self.rect.height / 2
        corner_half_w = self.corner_size[0] / 2
        corner_half_h = self.corner_size[1] / 2

        # Adjusted offsets to place corner centers more accurately at the boss's visual corners
        offsets = [
            (-half_main_w + corner_half_w, -half_main_h + corner_half_h), # Top-Left
            ( half_main_w - corner_half_w, -half_main_h + corner_half_h), # Top-Right
            (-half_main_w + corner_half_w,  half_main_h - corner_half_h), # Bottom-Left
            ( half_main_w - corner_half_w,  half_main_h - corner_half_h)  # Bottom-Right
        ]

        for i in range(4):
            corner_rect = pygame.Rect(0, 0, self.corner_size[0], self.corner_size[1])
            # Initial position will be updated in the first update call
            self.corners.append({
                'id': i,
                'relative_offset': offsets[i], # Store offset from boss center
                'rect': corner_rect.copy(),    # Absolute rect, updated in update()
                'health': self.health_per_corner,
                'max_health': self.health_per_corner,
                'status': 'intact', # 'intact', 'damaged', 'destroyed'
                'color': DARK_GREY # Default color for intact
            })
        self._update_corner_positions() # Set initial positions

    def _update_corner_positions(self):
        for corner in self.corners:
            offset_x, offset_y = corner['relative_offset']
            corner['rect'].center = (self.rect.centerx + offset_x, self.rect.centery + offset_y)

    def damage_corner(self, corner_id, damage_amount):
        if not self.alive: return False
        
        for corner in self.corners:
            if corner['id'] == corner_id:
                if corner['status'] == 'destroyed':
                    return False # Already destroyed

                corner['health'] -= damage_amount
                
                if self.game_controller_ref: # Play hit sound via game_controller
                    self.game_controller_ref.play_sound('boss_hit', 0.7)

                if corner['health'] <= 0:
                    corner['health'] = 0
                    corner['status'] = 'destroyed'
                    corner['color'] = BLACK # Visually destroyed
                    if self.game_controller_ref:
                         self.game_controller_ref._create_explosion(corner['rect'].centerx, corner['rect'].centery, num_particles=30, specific_sound='prototype_drone_explode')
                elif corner['status'] == 'intact': # First time damaged
                    corner['status'] = 'damaged'
                    corner['color'] = ORANGE # "Visible" when damaged
                elif corner['status'] == 'damaged': # Already damaged, change color further if desired
                     # Intensity color based on remaining health percentage for 'damaged' state
                    health_perc = corner['health'] / corner['max_health']
                    if health_perc < 0.33:
                        corner['color'] = RED # Critically damaged
                    elif health_perc < 0.66:
                        corner['color'] = YELLOW # Moderately damaged
                    else: # > 0.66 health but < max_health
                        corner['color'] = ORANGE # Initially damaged
                return True
        return False

    def take_damage(self, amount, sound=None):
        # This method is now largely bypassed for projectile damage,
        # as damage is applied to corners.
        # It could be used for physical collision damage or special vulnerabilities.
        # For now, let's make it do nothing or minimal effect.
        # if self.game_controller_ref and sound:
        #     self.game_controller_ref.play_sound(sound, 0.5) # Quieter for body hits
        pass


    def _choose_new_target_position(self, maze, game_area_x_offset):
        """Chooses a new random valid position within the maze to move to."""
        if not maze: return self.rect.center # Stay put if no maze
        
        path_cells = []
        if hasattr(maze, 'get_path_cells_abs'):
            path_cells = maze.get_path_cells_abs()
        elif hasattr(maze, 'get_path_cells'): # Fallback
            path_cells_rel = maze.get_path_cells()
            path_cells = [(x + game_area_x_offset, y) for x,y in path_cells_rel]

        if not path_cells: return self.rect.center

        # Try to find a point somewhat away from current position
        attempts = 0
        max_attempts = 10
        min_dist_from_self = TILE_SIZE * 3

        while attempts < max_attempts:
            potential_target = random.choice(path_cells)
            if math.hypot(potential_target[0] - self.x, potential_target[1] - self.y) > min_dist_from_self:
                self.target_pos = potential_target
                return
            attempts += 1
        
        self.target_pos = random.choice(path_cells) # Fallback if far point not found


    def update(self, player_pos, maze, current_time_ms, game_area_x_offset=0):
        if not self.alive:
            # If not alive, potentially handle an explosion/death animation here
            # For now, just stop updating further if main 'alive' is false
            return

        # Movement AI (simplified example, can be expanded)
        if self.target_pos is None or current_time_ms > self.move_timer:
            self._choose_new_target_position(maze, game_area_x_offset)
            self.move_timer = current_time_ms + self.MOVE_INTERVAL

        if self.target_pos:
            dx = self.target_pos[0] - self.x
            dy = self.target_pos[1] - self.y
            dist = math.hypot(dx, dy)
            if dist > self.speed: # Only move if not already at target
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed
            else: # Reached target
                self.x = self.target_pos[0]
                self.y = self.target_pos[1]
                self.target_pos = None # Pick new target next cycle

        # Update main rect and collision_rect (from BaseDrone logic, simplified)
        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect : self.collision_rect.center = self.rect.center
        
        # Boundary checks (ensure it stays within game play area)
        # These should ideally use collision_rect for more accuracy if it's different from visual rect
        min_x_bound = game_area_x_offset + self.rect.width / 2
        max_x_bound = WIDTH - self.rect.width / 2
        min_y_bound = self.rect.height / 2
        max_y_bound = GAME_PLAY_AREA_HEIGHT - self.rect.height / 2

        self.x = max(min_x_bound, min(self.x, max_x_bound))
        self.y = max(min_y_bound, min(self.y, max_y_bound))
        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect: self.collision_rect.center = self.rect.center

        # Update corner positions based on main boss position
        self._update_corner_positions()

        # --- Abilities (Laser, Minions) ---
        # Laser Attack (Example - keep if desired)
        if current_time_ms - self.last_laser_time > self.laser_cooldown:
            self.last_laser_time = current_time_ms
            # self.shoot_laser_barrage(player_pos) # Implement this method if lasers are kept

        # Minion Spawning (Example - keep if desired)
        if current_time_ms - self.last_minion_spawn_time > self.minion_spawn_cooldown:
            self.last_minion_spawn_time = current_time_ms
            # self.spawn_minions(maze, game_area_x_offset) # Implement this method if minions are kept

        # --- Bullet Shooting (REMOVED) ---
        # self.bullets.update(maze, game_area_x_offset) # Update bullets if any (should be none)
        # if current_time_ms - self.last_shot_time > self.shoot_cooldown:
        #     if player_pos and self.can_see_player(player_pos, maze):
        #         self.shoot_projectiles(player_pos) # This method will be modified/emptied for bullets

        # Check if all corners are destroyed
        all_corners_destroyed = all(c['status'] == 'destroyed' for c in self.corners)
        if all_corners_destroyed:
            self.alive = False # Game loop will pick this up
            # Death effects can be triggered here or in game_loop after this flag is set
            if self.game_controller_ref:
                self.game_controller_ref.play_sound('boss_death', 1.0) # Play main boss death sound

    def shoot_projectiles(self, target_pos):
        """
        Handles shooting. For Maze Guardian, this is now modified to NOT shoot standard bullets.
        Laser or other special attacks could be initiated here if they are not on separate cooldowns.
        """
        # Standard bullet shooting logic is removed.
        # If you want the boss to still shoot other types of projectiles (e.g., a special attack),
        # that logic would go here or be handled by a separate method like shoot_laser_barrage.
        pass # No standard bullets

    def shoot_laser_barrage(self, player_pos):
        """Example: Fires a laser attack."""
        # Placeholder for laser logic.
        # This would create LaserBeam sprites and add them to self.laser_beams
        if self.game_controller_ref:
            self.game_controller_ref.play_sound('laser_fire', 0.8)
        # Example: Create a dummy laser effect for now
        # Note: LightningZap is used as a placeholder for laser sprite in game_loop. Adjust if a real Laser class exists.
        # if self.game_controller_ref and hasattr(self.game_controller_ref, 'LightningZap'): # Check if class available
        #    zap = self.game_controller_ref.LightningZap(self, self.player_ref, 10, 30, self.maze_ref, color_override=gs.RED)
        #    self.laser_beams.add(zap)
        pass


    def spawn_minions(self, maze, game_area_x_offset):
        """Spawns Sentinel Drones as minions."""
        if not self.game_controller_ref or not self.game_controller_ref.enemy_manager:
            return

        num_minions_to_spawn = random.randint(1, 2)
        for _ in range(num_minions_to_spawn):
            # Find a spawn point near the boss but not on top of it
            angle = random.uniform(0, 2 * math.pi)
            spawn_dist = self.rect.width * 0.7 # Spawn just outside the boss
            spawn_x = self.rect.centerx + math.cos(angle) * spawn_dist
            spawn_y = self.rect.centery + math.sin(angle) * spawn_dist
            
            # Ensure spawn is within bounds and not in a wall (simplified check)
            if maze and not maze.is_wall(spawn_x, spawn_y, TILE_SIZE * 0.5, TILE_SIZE * 0.5):
                 # Ensure enemy_manager is accessible and has the add_enemy method or similar
                if hasattr(self.game_controller_ref.enemy_manager, 'spawn_specific_enemy_at_location'):
                    self.game_controller_ref.enemy_manager.spawn_sentinel_drone_at_location(spawn_x, spawn_y)
                elif hasattr(self.game_controller_ref.enemy_manager, 'add_enemy'):
                    # CORRECTED: The call to SentinelDrone now uses the correct arguments.
                    minion = SentinelDrone(x=spawn_x, y=spawn_y,
                                           player_bullet_size_base=gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE"),
                                           shoot_sound=self.game_controller_ref.sounds.get('enemy_shoot'),
                                           sprite_path=gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH"),
                                           target_player_ref=self.player_ref)
                    self.game_controller_ref.enemy_manager.add_enemy(minion)

                if self.game_controller_ref:
                    self.game_controller_ref.play_sound('minion_spawn', 0.6)
                    

    def draw(self, surface):
        if not self.image or not self.rect: return # Safety check

        # Draw main boss sprite
        surface.blit(self.image, self.rect)

        # Draw corners
        for corner in self.corners:
            # Simple visual representation for corners based on status
            # Color can be stored in corner dict and updated on status change
            pygame.draw.rect(surface, corner['color'], corner['rect'])
            # Add border for visibility
            border_color = WHITE if corner['status'] != 'destroyed' else DARK_GREY
            pygame.draw.rect(surface, border_color, corner['rect'], 2)

            # Optional: Draw health bar for each corner if desired
            if corner['status'] != 'destroyed' and corner['health'] < corner['max_health']:
                bar_width = corner['rect'].width * 0.8
                bar_height = 4
                bar_x = corner['rect'].centerx - bar_width / 2
                bar_y = corner['rect'].top - bar_height - 2
                health_perc = corner['health'] / corner['max_health']
                filled_width = bar_width * health_perc
                
                fill_c = RED
                if health_perc >= 0.6: fill_c = GREEN
                elif health_perc >= 0.3: fill_c = YELLOW
                
                pygame.draw.rect(surface, (50,50,50), (bar_x, bar_y, bar_width, bar_height))
                if filled_width > 0: pygame.draw.rect(surface, fill_c, (bar_x, bar_y, filled_width, bar_height))
                pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)


        # Draw laser beams if any
        self.laser_beams.draw(surface)
        # Note: If lasers have custom draw methods (like LightningZap), iterate and call draw.
        # for laser in self.laser_beams:
        #    laser.draw(surface)

        # No standard bullets to draw from self.bullets anymore
