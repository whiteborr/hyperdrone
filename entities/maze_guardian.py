import pygame
import math
import random
import os

from .enemy import Enemy
from .bullet import LightningZap # For laser sweep effect, can be specialized later
from .enemy import Bullet # For basic ranged shot

import game_settings as gs
from game_settings import (
    TILE_SIZE, WIDTH, GAME_PLAY_AREA_HEIGHT,
    DARK_GREY, YELLOW, GREEN, RED,

    MAZE_GUARDIAN_HEALTH, MAZE_GUARDIAN_SPEED, MAZE_GUARDIAN_COLOR,
    MAZE_GUARDIAN_LASER_DAMAGE, MAZE_GUARDIAN_LASER_COOLDOWN, MAZE_GUARDIAN_LASER_SWEEP_ARC,
    MAZE_GUARDIAN_SHIELD_DURATION_MS, MAZE_GUARDIAN_SHIELD_COOLDOWN_MS,
    MAZE_GUARDIAN_ARENA_SHIFT_INTERVAL_MS, MAZE_GUARDIAN_ARENA_SHIFT_DURATION_MS,
    MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS,
    SENTINEL_DRONE_HEALTH, SENTINEL_DRONE_SPEED, SENTINEL_DRONE_SPRITE_PATH,
    MAZE_GUARDIAN_BULLET_SPEED, MAZE_GUARDIAN_BULLET_LIFETIME,
    MAZE_GUARDIAN_BULLET_COLOR, MAZE_GUARDIAN_BULLET_DAMAGE,
    ARCHITECT_VAULT_ACCENT_COLOR, LIGHT_BLUE,
    RED, DARK_RED, WHITE,
    TOTAL_CORE_FRAGMENTS_NEEDED # Needed for Vault Core reward check (if it's a fragment)
)

class MazeGuardian(Enemy):
    def __init__(self, x, y, player_ref, maze_ref, game_controller_ref, boss_id="MAZE_GUARDIAN"):
        # Define image_size BEFORE calling super().__init__ so _load_sprite (called by Enemy.__init__) can access it
        self.image_size = (int(TILE_SIZE * 2.5), int(TILE_SIZE * 2.5)) # Boss is larger

        # Initialize as a large enemy, overriding default Enemy stats
        super().__init__(
            x=x, y=y,
            player_bullet_size_base=gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE"), # Just a placeholder value
            shoot_sound=game_controller_ref.sounds.get('enemy_shoot'), # Reuse enemy shoot sound
            sprite_path=gs.get_game_setting("MAZE_GUARDIAN_SPRITE_PATH"),
            target_player_ref=player_ref
        )

        self.boss_id = boss_id
        self.player_ref = player_ref
        self.maze_ref = maze_ref
        self.game_controller_ref = game_controller_ref # Reference to main game controller for state changes/spawns

        self.original_x = x
        self.original_y = y

        self.max_health = gs.get_game_setting("MAZE_GUARDIAN_HEALTH")
        self.health = self.max_health
        self.speed = gs.get_game_setting("MAZE_GUARDIAN_SPEED") # Boss can move

        self.current_phase = 1 # 1: Ranged+Laser, 2: Minions+Shield, 3: Arena Collapse+Aggressive
        self.last_phase_change_time = pygame.time.get_ticks()

        # Attack Cooldowns and Timers
        self.last_shot_time = pygame.time.get_ticks()
        self.basic_shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN") * 1.5 # Slower than regular enemy
        self.enhanced_shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN") * 0.8 # Faster when enhanced

        self.last_laser_time = pygame.time.get_ticks() - gs.get_game_setting("MAZE_GUARDIAN_LASER_COOLDOWN") // 2 # Ready to fire soon
        self.laser_cooldown = gs.get_game_setting("MAZE_GUARDIAN_LASER_COOLDOWN")
        self.laser_active = False # Flag for laser attack animation/duration
        self.laser_end_time = 0

        # Shield Mechanic
        self.shield_active = False
        self.shield_end_time = 0
        self.last_shield_activate_time = pygame.time.get_ticks()
        self.shield_duration = gs.get_game_setting("MAZE_GUARDIAN_SHIELD_DURATION_MS")
        self.shield_cooldown = gs.get_game_setting("MAZE_GUARDIAN_SHIELD_COOLDOWN_MS")
        self.shield_glow_pulse_time_offset = random.uniform(0, 2 * math.pi) # For visual pulse

        # Minion Summoning
        self.last_minion_spawn_time = pygame.time.get_ticks()
        self.minion_spawn_cooldown = gs.get_game_setting("MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS")
        self.max_active_minions = 3 # Can define in game_settings

        # Arena Shift Mechanic (Phase 3)
        self.last_arena_shift_time = pygame.time.get_ticks()
        self.arena_shift_interval = gs.get_game_setting("MAZE_GUARDIAN_ARENA_SHIFT_INTERVAL_MS")
        self.arena_shift_duration = gs.get_game_setting("MAZE_GUARDIAN_ARENA_SHIFT_DURATION_MS")
        self.arena_shifting_active = False
        self.arena_shift_end_time = 0

        # Boss Specific Visuals
        # self.image_size is now defined at the top of __init__
        # self._load_sprite is called by super().__init__ (Enemy class)
        
        # Adjust collision rect to be proportional, this should be fine here as rect is set by Enemy's _load_sprite
        if self.rect: # Ensure rect exists from super().__init__ call
            self.collision_rect_width = self.rect.width * 0.7
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else: # Fallback if rect wasn't set, though unlikely if super().__init__ worked
            print("Warning (MazeGuardian): self.rect not set after super().__init__.")
            self.collision_rect_width = self.image_size[0] * 0.7
            self.collision_rect_height = self.image_size[1] * 0.7
            self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = (self.x, self.y)


        # Projectile groups for consistency (Enemy already has self.bullets)
        self.laser_beams = pygame.sprite.Group() # For laser sweep effect

    def _load_sprite(self, sprite_path):
        # This method is called by Enemy's __init__ via super()
        # self.image_size should already be defined by MazeGuardian's __init__
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(loaded_image, self.image_size)
            except pygame.error as e:
                print(f"Error loading MAZE_GUARDIAN sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None
        else:
            if sprite_path: # Only print warning if a path was provided but not found
                print(f"Warning: MAZE_GUARDIAN sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None:
            # Fallback to a distinctive shape if sprite not found
            self.original_image = pygame.Surface(self.image_size, pygame.SRCALPHA)
            pygame.draw.circle(self.original_image, MAZE_GUARDIAN_COLOR,
                               (self.image_size[0] // 2, self.image_size[1] // 2),
                               self.image_size[0] // 2 - 5)
            pygame.draw.rect(self.original_image, RED, self.original_image.get_rect(), 5) # Outline

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def update(self, player_pos_pixels, maze, current_time, game_area_x_offset=0):
        if not self.alive:
            # Clean up projectiles if boss is dead
            self.bullets.update(maze, game_area_x_offset)
            self.laser_beams.update(current_time)
            if not self.bullets and not self.laser_beams:
                self.kill() # Remove from sprite groups if no projectiles left
            return

        # Phase Transition Logic
        self._check_phase_transition(current_time)

        # Update position (boss can move, but might be stationary in Phase 1)
        # Use A* pathfinding towards player, but with lower recalc interval to make it less twitchy
        self.PATH_RECALC_INTERVAL = 2000 # Boss recalculates path every 2 seconds
        self._update_ai_with_astar(player_pos_pixels, maze, current_time, game_area_x_offset)
        self._update_movement_along_path(maze, game_area_x_offset)


        # Rotate sprite to face player (only if actively moving towards player)
        if self.player_ref and self.player_ref.alive:
            dx_player = self.player_ref.x - self.x
            dy_player = self.player_ref.y - self.y
            self.angle = math.degrees(math.atan2(dy_player, dx_player))

        # Update boss sprite and rect
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        if self.collision_rect: # Ensure collision_rect is updated
            self.collision_rect.center = self.rect.center


        # Update internal attack/mechanic states
        self._update_shield_state(current_time)
        self._update_arena_shift_state(current_time, maze)
        self.bullets.update(maze, game_area_x_offset)
        self.laser_beams.update(current_time)


        # Phase-specific AI behavior
        if self.current_phase == 1:
            self._perform_basic_ranged_attack(current_time)
            self._try_laser_sweep(current_time) # Removed player_pos from here, laser uses self.angle or target
        elif self.current_phase == 2:
            self._perform_basic_ranged_attack(current_time, enhanced=True)
            self._try_laser_sweep(current_time)
            self._try_summon_mini_drones(current_time, player_pos_pixels, maze, game_area_x_offset)
            self._try_activate_shield(current_time)
        elif self.current_phase == 3:
            self._perform_basic_ranged_attack(current_time, enhanced=True, triple_shot=True)
            self._try_laser_sweep(current_time, wide_sweep=True)
            self._try_arena_shift_initiate(current_time) # Initiate arena shift
            # Boss moves more aggressively in phase 3
            self.speed = gs.get_game_setting("MAZE_GUARDIAN_SPEED") * 1.2 # Faster movement

    def _check_phase_transition(self, current_time):
        health_ratio = self.health / self.max_health
        if health_ratio <= 0.3 and self.current_phase != 3:
            self.current_phase = 3
            print("MAZE_GUARDIAN: Phase 3: Critical Lockdown!")
            self.game_controller_ref.play_sound('vault_alarm', 0.7)
            self.game_controller_ref.architect_vault_message = "MAZE GUARDIAN: CRITICAL LOCKDOWN! ARENA COLLAPSE!"
            self.game_controller_ref.architect_vault_message_timer = current_time + 4000
            self.last_arena_shift_time = current_time + 1000 # Delay first shift slightly
        elif health_ratio <= 0.65 and self.current_phase == 1: # Changed from <=0.6 and !=2 to <=0.65 and ==1 to ensure it only triggers once from 1 to 2
            self.current_phase = 2
            print("MAZE_GUARDIAN: Phase 2: Defensive Protocols Activated!")
            self.game_controller_ref.play_sound('ui_confirm')
            self.game_controller_ref.architect_vault_message = "MAZE GUARDIAN: DEFENSIVE SYSTEMS ONLINE!"
            self.game_controller_ref.architect_vault_message_timer = current_time + 3000

    def _perform_basic_ranged_attack(self, current_time, enhanced=False, triple_shot=False):
        cooldown_to_use = self.enhanced_shoot_cooldown if enhanced else self.basic_shoot_cooldown
        if current_time - self.last_shot_time > cooldown_to_use:
            if self.player_ref and self.player_ref.alive:
                dx = self.player_ref.x - self.x
                dy = self.player_ref.y - self.y
                angle_to_player = math.degrees(math.atan2(dy, dx))

                fire_angles = [angle_to_player]
                if triple_shot:
                    fire_angles = [angle_to_player - 15, angle_to_player, angle_to_player + 15]

                for angle in fire_angles:
                    bullet_speed = gs.get_game_setting("MAZE_GUARDIAN_BULLET_SPEED")
                    bullet_lifetime = gs.get_game_setting("MAZE_GUARDIAN_BULLET_LIFETIME")
                    bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE") // 1.5 # Smaller than player
                    bullet_color = gs.get_game_setting("MAZE_GUARDIAN_BULLET_COLOR")
                    bullet_damage = gs.get_game_setting("MAZE_GUARDIAN_BULLET_DAMAGE")

                    # Calculate bullet spawn point slightly outside boss's rect
                    fire_offset = self.rect.width / 2 + 10 # Offset from center to "muzzle"
                    spawn_x = self.x + math.cos(math.radians(angle)) * fire_offset
                    spawn_y = self.y + math.sin(math.radians(angle)) * fire_offset

                    new_bullet = Bullet(spawn_x, spawn_y, angle, bullet_speed,
                                        bullet_lifetime, int(bullet_size), bullet_color, bullet_damage) # Ensure size is int
                    self.bullets.add(new_bullet)
                if self.shoot_sound:
                    self.shoot_sound.play()
            self.last_shot_time = current_time

    def _try_laser_sweep(self, current_time, wide_sweep=False): # Removed player_pos argument
        if not self.laser_active and current_time - self.last_laser_time > self.laser_cooldown:
            self.laser_active = True
            self.laser_end_time = current_time + gs.get_game_setting("LIGHTNING_LIFETIME") # Duration of laser
            self.last_laser_time = current_time # Start cooldown for next laser after this one is active
            self.game_controller_ref.play_sound('laser_charge')


            # The laser will use the boss's current angle (self.angle)
            # The LightningZap's _calculate_potential_target_pos will use this angle
            # if no specific enemy target is provided.
            laser_zap = LightningZap(
                player_ref=self, # Pass boss as "player_ref" for LightningZap
                initial_target_enemy_ref=None, # No specific enemy, it's an area attack based on boss angle
                damage=gs.get_game_setting("MAZE_GUARDIAN_LASER_DAMAGE"),
                lifetime_frames=gs.get_game_setting("LIGHTNING_LIFETIME"), 
                maze_ref=self.maze_ref,
                game_area_x_offset = self.game_controller_ref.maze.game_area_x_offset if self.game_controller_ref.maze else 0
                # color_override=gs.get_game_setting("RED") # Laser color - LightningZap uses its own color
            )
            self.laser_beams.add(laser_zap) 
            self.game_controller_ref.play_sound('laser_fire')


    def _update_laser_state(self, current_time): # Renamed from _update_laser_state to avoid conflict if Enemy has it
        if self.laser_active and current_time > self.laser_end_time:
            self.laser_active = False

    def _try_summon_mini_drones(self, current_time, player_pos_pixels, maze, game_area_x_offset):
        active_minions_count = sum(1 for e in self.game_controller_ref.enemies if isinstance(e, SentinelDrone) and e.alive)

        if active_minions_count < self.max_active_minions and \
           current_time - self.last_minion_spawn_time > self.minion_spawn_cooldown:
            
            spawn_x, spawn_y = self.game_controller_ref._get_safe_spawn_point(TILE_SIZE, TILE_SIZE) 
            if spawn_x is not None:
                new_minion = SentinelDrone(
                    x=spawn_x, y=spawn_y,
                    player_bullet_size_base=gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE"),
                    shoot_sound=self.game_controller_ref.sounds.get('enemy_shoot'),
                    sprite_path=gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH"),
                    target_player_ref=self.player_ref
                )
                self.game_controller_ref.enemies.add(new_minion) 
                self.game_controller_ref.play_sound('minion_spawn') 
                self.last_minion_spawn_time = current_time
                print(f"MAZE_GUARDIAN: Summoned Sentinel Drone at ({spawn_x}, {spawn_y})")

    def _try_activate_shield(self, current_time):
        if not self.shield_active and current_time - self.last_shield_activate_time > self.shield_cooldown:
            self.shield_active = True
            self.shield_end_time = current_time + self.shield_duration
            self.last_shield_activate_time = current_time
            self.game_controller_ref.play_sound('shield_activate') 
            print("MAZE_GUARDIAN: Shield Activated!")

    def _update_shield_state(self, current_time):
        if self.shield_active and current_time > self.shield_end_time:
            self.shield_active = False
            print("MAZE_GUARDIAN: Shield Deactivated.")

    def _try_arena_shift_initiate(self, current_time):
        if not self.arena_shifting_active and current_time - self.last_arena_shift_time > self.arena_shift_interval:
            self.arena_shifting_active = True
            self.arena_shift_end_time = current_time + self.arena_shift_duration
            self.last_arena_shift_time = current_time
            self.game_controller_ref.play_sound('wall_shift') 
            if hasattr(self.maze_ref, 'toggle_dynamic_walls'):
                self.maze_ref.toggle_dynamic_walls(activate=True) 
            print("MAZE_GUARDIAN: Initiating Arena Shift!")

    def _update_arena_shift_state(self, current_time, maze):
        if self.arena_shifting_active and current_time > self.arena_shift_end_time:
            self.arena_shifting_active = False
            if hasattr(maze, 'toggle_dynamic_walls'):
                maze.toggle_dynamic_walls(activate=False) 
            print("MAZE_GUARDIAN: Arena Shift Ended.")

    def take_damage(self, amount):
        if not self.alive:
            return

        if self.shield_active:
            self.game_controller_ref.play_sound('ui_denied', 0.5) # Sound for shield hit
            return

        self.health -= amount
        self.game_controller_ref.play_sound('boss_hit') 
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.game_controller_ref.play_sound('boss_death') 
            print("MAZE_GUARDIAN: Defeated!")
            if hasattr(self.game_controller_ref, '_maze_guardian_defeated'):
                 self.game_controller_ref._maze_guardian_defeated()


    def draw(self, surface):
        if not self.alive:
            pass # Handled by explosion particles in GameController

        if self.alive and self.image:
            surface.blit(self.image, self.rect)
            self._draw_health_bar(surface)
            if self.shield_active:
                self._draw_shield_effect(surface)

        self.bullets.draw(surface)
        self.laser_beams.draw(surface) 

    def _draw_health_bar(self, surface):
        bar_width = self.rect.width * 1.2
        bar_height = 10 # Made slightly thicker
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 15 # Further above
        health_percentage = max(0, self.health / self.max_health) if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage

        pygame.draw.rect(surface, DARK_GREY, (bar_x, bar_y, bar_width, bar_height))
        fill_color = RED
        if health_percentage >= 0.66: fill_color = GREEN
        elif health_percentage >= 0.33: fill_color = YELLOW
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 2) # Thicker border

        phase_text_surf = None
        font_key = "small_text" 
        phase_color = WHITE
        if self.current_phase == 1:
            phase_text_surf = self.game_controller_ref.ui_manager._render_text_safe("Phase I", font_key, phase_color)
        elif self.current_phase == 2:
            phase_color = YELLOW
            phase_text_surf = self.game_controller_ref.ui_manager._render_text_safe("Phase II", font_key, phase_color)
        elif self.current_phase == 3:
            phase_color = RED
            phase_text_surf = self.game_controller_ref.ui_manager._render_text_safe("Phase III", font_key, phase_color)

        if phase_text_surf:
            text_rect = phase_text_surf.get_rect(midbottom=(bar_x + bar_width / 2, bar_y - 5))
            surface.blit(phase_text_surf, text_rect)

    def _draw_shield_effect(self, surface):
        if not self.shield_active: return
        current_time = pygame.time.get_ticks()
        pulse_factor = (math.sin(current_time * 0.008 + self.shield_glow_pulse_time_offset) + 1) / 2 
        glow_alpha = int(100 + pulse_factor * 60) # Slightly less intense than player's for differentiation
        glow_scale = 1.15 + (pulse_factor * 0.1) 
        glow_color_tuple = ARCHITECT_VAULT_ACCENT_COLOR # Using a distinct vault color

        glow_width = int(self.image.get_width() * glow_scale)
        glow_height = int(self.image.get_height() * glow_scale)

        if glow_width > 0 and glow_height > 0:
            # Create a temporary surface for the glow, using the original_image for shape
            # This avoids issues if self.image is already rotated or modified
            temp_glow_base = pygame.transform.smoothscale(self.original_image, (glow_width, glow_height))
            
            # Rotate this scaled base image to match the boss's current angle
            rotated_glow_base = pygame.transform.rotate(temp_glow_base, -self.angle)
            
            try:
                glow_shape_mask = pygame.mask.from_surface(rotated_glow_base)
                glow_shape_surface = glow_shape_mask.to_surface(setcolor=glow_color_tuple, unsetcolor=(0,0,0,0))
                glow_shape_surface.set_alpha(glow_alpha)
                glow_rect = glow_shape_surface.get_rect(center=self.rect.center)
                surface.blit(glow_shape_surface, glow_rect)
            except (pygame.error, ValueError) as e: # Catch potential errors during mask/surface creation
                # print(f"Debug: Error creating shield mask/surface: {e}")
                # Fallback to drawing a simple circle shield if mask creation fails
                fallback_glow_radius = int((self.rect.width / 2) * glow_scale)
                if fallback_glow_radius > 0:
                    fallback_glow_surface = pygame.Surface((fallback_glow_radius * 2, fallback_glow_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(fallback_glow_surface, (*glow_color_tuple[:3], glow_alpha),
                                    (fallback_glow_radius, fallback_glow_radius), fallback_glow_radius)
                    surface.blit(fallback_glow_surface, fallback_glow_surface.get_rect(center=self.rect.center))

# Sentinel Drone (Mini-drone summoned by MazeGuardian)
class SentinelDrone(Enemy):
    def __init__(self, x, y, player_bullet_size_base, shoot_sound=None, sprite_path=None, target_player_ref=None):
        # Define image_size specific to SentinelDrone before calling super().__init__
        self.image_size = (int(TILE_SIZE * 0.6), int(TILE_SIZE * 0.6)) # Smaller than regular enemies

        super().__init__(
            x=x, y=y,
            player_bullet_size_base=player_bullet_size_base,
            shoot_sound=shoot_sound,
            sprite_path=sprite_path or gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH"),
            target_player_ref=target_player_ref
        )
        self.max_health = gs.get_game_setting("SENTINEL_DRONE_HEALTH")
        self.health = self.max_health
        self.speed = gs.get_game_setting("SENTINEL_DRONE_SPEED")
        self.shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN") * 0.7 # Faster shooting

    def _load_sprite(self, sprite_path): # Override Enemy's _load_sprite to use Sentinel's image_size
        default_size = self.image_size # Use the size defined in SentinelDrone's __init__
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(loaded_image, default_size)
            except pygame.error as e:
                print(f"Error loading sentinel sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None
        else:
            if sprite_path: print(f"Warning: Sentinel sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None:
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            # Simple diamond shape for fallback sentinel
            points = [
                (default_size[0] // 2, 0), (default_size[0], default_size[1] // 2),
                (default_size[0] // 2, default_size[1]), (0, default_size[1] // 2)
            ]
            pygame.draw.polygon(self.original_image, gs.get_game_setting("DARK_PURPLE",(70,0,100)), points) # Sentinel color
            pygame.draw.polygon(self.original_image, WHITE, points, 1)


        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(self.x, self.y))
        # Collision rect for SentinelDrone (can be smaller if visual is more detailed)
        self.collision_rect_width = self.rect.width * 0.8
        self.collision_rect_height = self.rect.height * 0.8
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center


    def update(self, player_pos_pixels, maze, current_time, game_area_x_offset=0):
        if not self.alive:
            if not self.bullets:
                self.kill()
            self.bullets.update(maze, game_area_x_offset)
            return

        if self.player_ref and self.player_ref.alive:
            dx = self.player_ref.x - self.x
            dy = self.player_ref.y - self.y
            distance = math.hypot(dx, dy)

            if distance > 0: # Avoid division by zero if already on top of player
                self.angle = math.degrees(math.atan2(dy, dx))
                move_x = (dx / distance) * self.speed
                move_y = (dy / distance) * self.speed
                
                prev_x, prev_y = self.x, self.y
                self.x += move_x
                self.y += move_y

                # Basic wall collision check (more robust than just boundary check)
                if maze and self.collision_rect:
                     # Update collision_rect position before checking
                    self.collision_rect.center = (self.x, self.y)
                    if maze.is_wall(self.collision_rect.centerx, self.collision_rect.centery, self.collision_rect.width, self.collision_rect.height):
                        self.x = prev_x # Revert x
                        self.y = prev_y # Revert y
                        # Optionally, try to slide or just stop
                        self.angle += 180 # Simple turn around on collision
                        self.angle %= 360


            # Keep within game boundaries (redundant if wall collision is perfect, but good fallback)
            half_width = self.rect.width / 2 if self.rect else TILE_SIZE * 0.3
            half_height = self.rect.height / 2 if self.rect else TILE_SIZE * 0.3
            min_x_bound = game_area_x_offset + half_width
            max_x_bound = WIDTH - half_width
            min_y_bound = half_height
            max_y_bound = GAME_PLAY_AREA_HEIGHT - half_height
            self.x = max(min_x_bound, min(self.x, max_x_bound))
            self.y = max(min_y_bound, min(self.y, max_y_bound))


            if current_time - self.last_shot_time > self.shoot_cooldown and distance < TILE_SIZE * 8:
                self.shoot(self.angle) 
                self.last_shot_time = current_time

        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        if self.collision_rect:
            self.collision_rect.center = self.rect.center

        self.bullets.update(maze, game_area_x_offset)
