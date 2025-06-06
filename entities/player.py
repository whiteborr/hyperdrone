# entities/player.py
import pygame
import math
import os # Keep os for potential path joining if asset_manager needed more complex logic, though unlikely now
import random
import logging 

import game_settings as gs
from game_settings import (
    TILE_SIZE, WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT,
    WEAPON_MODES_SEQUENCE, INITIAL_WEAPON_MODE,
    PLAYER_DEFAULT_BULLET_SIZE, PLAYER_BIG_BULLET_SIZE,
    PLAYER_BASE_SHOOT_COOLDOWN, PLAYER_RAPID_FIRE_COOLDOWN,
    BOUNCING_BULLET_MAX_BOUNCES, PIERCING_BULLET_MAX_PIERCES,
    MISSILE_COOLDOWN, MISSILE_DAMAGE,
    LIGHTNING_COOLDOWN, LIGHTNING_DAMAGE, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE,
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE,
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING, POWERUP_TYPES,
    PHANTOM_CLOAK_ALPHA_SETTING, PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS,
    GREEN, YELLOW, RED, WHITE, LIGHT_BLUE, ORANGE, CYAN, ELECTRIC_BLUE,
    PLAYER_SPEED, PLAYER_MAX_HEALTH, ROTATION_SPEED,
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME,
    MISSILE_COLOR,
    LIGHTNING_COLOR, CORE_FRAGMENT_DETAILS,
    SPEED_BOOST_POWERUP_DURATION, SHIELD_POWERUP_DURATION,
    FLAME_COLORS,
    THRUST_PARTICLE_SPREAD_ANGLE,
    THRUST_PARTICLE_LIFETIME_BLAST,
    THRUST_PARTICLE_START_SIZE_BLAST_MIN,
    THRUST_PARTICLE_START_SIZE_BLAST_MAX,
    THRUST_PARTICLE_SPEED_MIN_BLAST,
    THRUST_PARTICLE_SPEED_MAX_BLAST,
    THRUST_PARTICLE_SHRINK_RATE_BLAST,
    get_game_setting 
)
# Import projectile classes
try:
    from .bullet import Bullet, Missile, LightningZap
    from .particle import Particle
except ImportError:
    # Minimal placeholder if these classes are not found
    class Bullet(pygame.sprite.Sprite): pass
    class Missile(pygame.sprite.Sprite): pass
    class LightningZap(pygame.sprite.Sprite): pass 
    class Particle(pygame.sprite.Sprite): pass

# Import BaseDrone
try:
    from .base_drone import BaseDrone
except ImportError:
    # Minimal placeholder for BaseDrone
    class BaseDrone(pygame.sprite.Sprite):
        def __init__(self, x,y,speed, size=None):
            super().__init__()
            self.x = x; self.y = y; self.speed = speed; self.angle = 0.0
            self.moving_forward = False; self.alive = True
            self.size = size if size is not None else TILE_SIZE * 0.8
            self.rect = pygame.Rect(x - self.size / 2, y - self.size / 2, self.size, self.size)
            self.collision_rect = self.rect.copy()
        def update_movement(self, maze=None, game_area_x_offset=0): pass

logger = logging.getLogger(__name__)


class PlayerDrone(BaseDrone): 
    def __init__(self, x, y, drone_id, drone_stats, asset_manager, sprite_asset_key, crash_sound_key, drone_system):
        base_speed_from_stats = drone_stats.get("speed", get_game_setting("PLAYER_SPEED"))
        self.drone_visual_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7))
        super().__init__(x, y, size=self.drone_visual_size[0], speed=base_speed_from_stats)
        
        self.drone_id = drone_id
        self.drone_system = drone_system  
        self.asset_manager = asset_manager
        self.sprite_asset_key = sprite_asset_key
        self.crash_sound_key = crash_sound_key

        self.x = float(x) 
        self.y = float(y)
        
        self.base_hp = drone_stats.get("hp", get_game_setting("PLAYER_MAX_HEALTH"))
        self.base_speed = base_speed_from_stats
        self.base_turn_speed = drone_stats.get("turn_speed", get_game_setting("ROTATION_SPEED"))
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")  
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0) 
        
        self.max_health = self.base_hp
        self.health = self.max_health
        self.rotation_speed = self.base_turn_speed
        
        # <<< NEW STATE FOR CRUISE CONTROL >>>
        self.is_cruising = False

        self.original_image = None
        self.image = None
        self._load_sprite()
        
        initial_weapon_mode_gs = get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
        except ValueError:
            self.weapon_mode_index = 0 
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        
        self.bullets_group = pygame.sprite.Group() 
        self.missiles_group = pygame.sprite.Group() 
        self.lightning_zaps_group = pygame.sprite.Group() 
        
        self.last_shot_time = 0 
        self.last_missile_shot_time = 0 
        self.last_lightning_time = 0 
        
        self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN")
        self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN")
        self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        self._update_weapon_attributes()
        
        self.active_powerup_type = None 
        self.shield_active = False
        self.shield_end_time = 0
        self.shield_duration = get_game_setting("SHIELD_POWERUP_DURATION")  
        self.shield_glow_pulse_time_offset = random.uniform(0, 2 * math.pi) 
        
        self.speed_boost_active = False
        self.speed_boost_end_time = 0
        self.speed_boost_duration = get_game_setting("SPEED_BOOST_POWERUP_DURATION")
        self.speed_boost_multiplier = POWERUP_TYPES.get("speed_boost", {}).get("multiplier", 1.8)
        self.original_speed_before_boost = self.speed 
        self.shield_tied_to_speed_boost = False 
        
        self.thrust_particles = pygame.sprite.Group()
        self.thrust_particle_spawn_timer = 0
        self.THRUST_PARTICLE_SPAWN_INTERVAL = 25 
        self.PARTICLES_PER_EMISSION = random.randint(2, 4) 
        self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4 
        
        self.cloak_active = False 
        self.cloak_start_time = 0  
        self.cloak_end_time = 0 
        self.last_cloak_activation_time = -float('inf')
        self.cloak_cooldown_end_time = 0  
        self.is_cloaked_visual = False
        self.phantom_cloak_alpha = get_game_setting("PHANTOM_CLOAK_ALPHA_SETTING")
        self.phantom_cloak_duration_ms = get_game_setting("PHANTOM_CLOAK_DURATION_MS")
        self.phantom_cloak_cooldown_ms = get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS")
        
        if self.rect:
            self.collision_rect_width = self.rect.width * 0.7 
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else:
            col_size = self.size * 0.7
            self.collision_rect = pygame.Rect(self.x - col_size/2, self.y - col_size/2, col_size, col_size)

    def _load_sprite(self):
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)
        if loaded_image:
            try:
                self.original_image = pygame.transform.smoothscale(loaded_image, self.drone_visual_size)
            except (ValueError, pygame.error) as e:
                logger.error(f"PlayerDrone: Error scaling sprite '{self.sprite_asset_key}': {e}")
                self.original_image = None
        else:
            logger.warning(f"PlayerDrone: Sprite for key '{self.sprite_asset_key}' not found in AssetManager.")
            self.original_image = None
        if self.original_image is None:
            self.original_image = self.asset_manager._create_fallback_surface(
                size=self.drone_visual_size, text=self.drone_id[:1], color=(0,200,0,150)
            )
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.drone_visual_size = self.rect.size
        self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4
        self.collision_rect_width = self.rect.width * 0.7
        self.collision_rect_height = self.rect.height * 0.7
        self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center

    def _update_weapon_attributes(self):
        # (This method's logic remains largely the same as it deals with game settings and internal state)
        if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
            self.bullet_size = get_game_setting("PLAYER_BIG_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") * 1.5 
        elif self.current_weapon_mode in [WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN")
        else: 
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        
        if self.base_fire_rate_multiplier != 0: # Avoid division by zero
            effective_fr_mult = self.base_fire_rate_multiplier
            # Apply core fragment buffs if drone_system is available
            if self.drone_system and hasattr(self.drone_system, 'get_collected_fragments_ids') and CORE_FRAGMENT_DETAILS:
                for frag_id in self.drone_system.get_collected_fragments_ids():
                    frag_conf = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                    if frag_conf and frag_conf.get("buff", {}).get("type") == "fire_rate":
                        effective_fr_mult *= frag_conf["buff"]["value"] 
            
            self.current_shoot_cooldown /= effective_fr_mult 
            self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") / effective_fr_mult
            self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") / effective_fr_mult
        else: # Safety for zero multiplier
            self.current_shoot_cooldown = float('inf')
            self.current_missile_cooldown = float('inf')
            self.current_lightning_cooldown = float('inf')

    def _emit_thrust_particles(self, current_time_ms):
        # (This method's logic for particle creation remains the same)
        if self.speed_boost_active and self.moving_forward:
            if current_time_ms > self.thrust_particle_spawn_timer:
                self.thrust_particle_spawn_timer = current_time_ms + self.THRUST_PARTICLE_SPAWN_INTERVAL
                num_particles_to_spawn = self.PARTICLES_PER_EMISSION
                emission_base_angle_deg = (self.angle + 180) % 360 
                emission_angle_rad_for_offset = math.radians(self.angle + 180) # Angle for offset from center
                
                # Calculate offset from drone center to flame port
                offset_x = math.cos(emission_angle_rad_for_offset) * self.flame_port_offset_distance
                offset_y = math.sin(emission_angle_rad_for_offset) * self.flame_port_offset_distance

                for _ in range(num_particles_to_spawn):
                    particle = Particle(
                        x=self.x, y=self.y, # Initial position is drone center, offset applied internally by Particle
                        color_list=FLAME_COLORS, 
                        min_speed=get_game_setting("THRUST_PARTICLE_SPEED_MIN_BLAST"),
                        max_speed=get_game_setting("THRUST_PARTICLE_SPEED_MAX_BLAST"),
                        min_size=get_game_setting("THRUST_PARTICLE_START_SIZE_BLAST_MIN"),
                        max_size=get_game_setting("THRUST_PARTICLE_START_SIZE_BLAST_MAX"),
                        lifetime_frames=get_game_setting("THRUST_PARTICLE_LIFETIME_BLAST"),
                        base_angle_deg=emission_base_angle_deg, # Angle for particle velocity
                        spread_angle_deg=get_game_setting("THRUST_PARTICLE_SPREAD_ANGLE"),
                        x_offset=offset_x, y_offset=offset_y, # Offset from drone center for spawn point
                        blast_mode=True 
                    )
                    self.thrust_particles.add(particle)

    def _update_thrust_particles(self):
        # (This method's logic remains the same)
        self.thrust_particles.update()

    def update_movement(self, maze=None, game_area_x_offset=0):
        # (This method uses self.speed, self.angle which are part of PlayerDrone)
        # (No direct asset loading here)
        super().update_movement(maze, game_area_x_offset) # Call BaseDrone's movement logic

    def update(self, current_time_ms, maze, enemies_group, game_area_x_offset=0):
        if not self.alive:
            self.bullets_group.update(maze, game_area_x_offset)
            self.missiles_group.update(enemies_group, maze, game_area_x_offset) 
            self.lightning_zaps_group.update(current_time_ms)
            self._update_thrust_particles()
            return
        
        # <<< USE is_cruising TO DRIVE MOVEMENT >>>
        # Set the moving_forward flag for the BaseDrone's movement logic based on the new state
        self.moving_forward = self.is_cruising

        self.update_powerups(current_time_ms) 
        self.update_movement(maze, game_area_x_offset) 
        
        if self.speed_boost_active and self.moving_forward:
            self._emit_thrust_particles(current_time_ms)
        self._update_thrust_particles()
        
        self.bullets_group.update(maze, game_area_x_offset)
        self.missiles_group.update(enemies_group, maze, game_area_x_offset) 
        self.lightning_zaps_group.update(current_time_ms)

        current_alpha_to_set = 255
        if self.is_cloaked_visual:
            current_alpha_to_set = self.phantom_cloak_alpha
        
        if self.original_image:
            rotated_image = pygame.transform.rotate(self.original_image, -self.angle) 
            self.image = rotated_image.convert_alpha()
            self.image.set_alpha(current_alpha_to_set)
            if self.rect:
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                if self.collision_rect:
                    self.collision_rect.center = self.rect.center
            else:
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                if self.collision_rect: self.collision_rect.center = self.rect.center
        elif self.rect:
             self.rect.center = (int(self.x), int(self.y))
             if self.collision_rect: self.collision_rect.center = self.rect.center

    def _handle_wall_collision(self, wall_hit, dx, dy):
        """
        Overrides the BaseDrone method. This is now called every frame
        from update_movement in the parent class.
        """
        # Call the parent's logic first to stop movement
        super()._handle_wall_collision(wall_hit, dx, dy)
        
        # Now, add the player-specific damage logic
        is_invincible_setting = get_game_setting("PLAYER_INVINCIBILITY", False)
        if wall_hit and not self.shield_active and not is_invincible_setting:
            self.take_damage(10, self.crash_sound_key)
            self.is_cruising = False # Also stop cruise control on collision

    def rotate(self, direction, rotation_speed_override=None):
        # (This method's logic remains the same)
        effective_rotation_speed = rotation_speed_override if rotation_speed_override is not None else self.rotation_speed
        if direction == "left":
            self.angle -= effective_rotation_speed
        elif direction == "right":
            self.angle += effective_rotation_speed
        self.angle %= 360  # Keep angle between 0 and 359

    def shoot(self, sound_asset_key=None, missile_sound_asset_key=None, maze=None, enemies_group=None):
        """ Shoots projectiles based on current weapon mode. Projectile classes might need asset_manager if they use sprites. """
        # (The core logic for weapon modes remains, but sound playing uses keys)
        current_time_ms = pygame.time.get_ticks()
        can_shoot_primary = (current_time_ms - self.last_shot_time) > self.current_shoot_cooldown
        can_shoot_missile = (current_time_ms - self.last_missile_shot_time) > self.current_missile_cooldown
        can_shoot_lightning = (current_time_ms - self.last_lightning_time) > self.current_lightning_cooldown
        
        # Calculate bullet spawn position
        nose_offset_factor = (self.rect.height / 2 if self.rect else TILE_SIZE * 0.4) * 0.7 # Offset from center
        rad_angle_shoot = math.radians(self.angle)
        raw_bullet_start_x = self.x + math.cos(rad_angle_shoot) * nose_offset_factor
        raw_bullet_start_y = self.y + math.sin(rad_angle_shoot) * nose_offset_factor
        
        bullet_start_x = raw_bullet_start_x
        bullet_start_y = raw_bullet_start_y
        
        # Adjust spawn if inside a wall (simple check)
        projectile_check_diameter = self.bullet_size * 2 
        if maze:
            if maze.is_wall(raw_bullet_start_x, raw_bullet_start_y, projectile_check_diameter, projectile_check_diameter):
                max_steps_back = 10 
                step_dist = nose_offset_factor / max_steps_back if max_steps_back > 0 else 0
                found_clear_spawn = False
                for i in range(1, max_steps_back + 1):
                    current_offset = nose_offset_factor - (i * step_dist)
                    if current_offset < 0: current_offset = 0 # Don't go behind player center
                    test_x = self.x + math.cos(rad_angle_shoot) * current_offset
                    test_y = self.y + math.sin(rad_angle_shoot) * current_offset
                    if not maze.is_wall(test_x, test_y, projectile_check_diameter, projectile_check_diameter):
                        bullet_start_x = test_x
                        bullet_start_y = test_y
                        found_clear_spawn = True
                        break
                    if current_offset == 0: # Last attempt at drone center
                        bullet_start_x = test_x
                        bullet_start_y = test_y
                        break
                if not found_clear_spawn: # Fallback to player center if still in wall
                    bullet_start_x = self.x
                    bullet_start_y = self.y

        # Standard Bullet Firing
        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING]: # Exclude missile/lightning only modes
            if can_shoot_primary:
                if sound_asset_key and self.asset_manager: 
                    sound = self.asset_manager.get_sound(sound_asset_key)
                    if sound: sound.play()
                self.last_shot_time = current_time_ms
                angles_to_fire = [0] 
                if self.current_weapon_mode == WEAPON_MODE_TRI_SHOT or self.current_weapon_mode == WEAPON_MODE_RAPID_TRI:
                    angles_to_fire = [-15, 0, 15] 
                
                for angle_offset in angles_to_fire:
                    effective_bullet_angle = self.angle + angle_offset
                    bullet_speed = get_game_setting("PLAYER_BULLET_SPEED")
                    bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME")
                    bullet_color = get_game_setting("PLAYER_BULLET_COLOR")
                    current_bullet_damage = 15 * self.bullet_damage_multiplier # Base damage
                    if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT: current_bullet_damage *= 2.5 
                    
                    bounces = get_game_setting("BOUNCING_BULLET_MAX_BOUNCES") if self.current_weapon_mode == WEAPON_MODE_BOUNCE else 0
                    pierces = get_game_setting("PIERCING_BULLET_MAX_PIERCES") if self.current_weapon_mode == WEAPON_MODE_PIERCE else 0
                    can_pierce_walls_flag = (self.current_weapon_mode == WEAPON_MODE_PIERCE) 
                    
                    # Bullet constructor doesn't need asset_manager as it's procedural
                    new_bullet = Bullet(bullet_start_x, bullet_start_y, effective_bullet_angle,
                                        bullet_speed, bullet_lifetime, self.bullet_size, bullet_color,
                                        int(current_bullet_damage), bounces, pierces, 
                                        can_pierce_walls=can_pierce_walls_flag)
                    self.bullets_group.add(new_bullet)

        # Missile Firing
        if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
            if can_shoot_missile:
                if missile_sound_asset_key and self.asset_manager: 
                    sound = self.asset_manager.get_sound(missile_sound_asset_key)
                    if sound: sound.play()
                self.last_missile_shot_time = current_time_ms
                missile_dmg = get_game_setting("MISSILE_DAMAGE") * self.bullet_damage_multiplier
                # Missile constructor may need asset_manager if it uses a sprite
                new_missile = Missile(bullet_start_x, bullet_start_y, self.angle, int(missile_dmg), enemies_group) 
                self.missiles_group.add(new_missile)
            
            # Extra bullets for WEAPON_MODE_HEATSEEKER_PLUS_BULLETS
            if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS and can_shoot_primary:
                if sound_asset_key and self.asset_manager: 
                    sound = self.asset_manager.get_sound(sound_asset_key)
                    if sound: sound.play()
                self.last_shot_time = current_time_ms # Separate cooldown for bullets
                std_bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
                std_bullet_speed = get_game_setting("PLAYER_BULLET_SPEED")
                std_bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME")
                std_bullet_color = get_game_setting("PLAYER_BULLET_COLOR")
                std_bullet_damage = 10 * self.bullet_damage_multiplier 
                new_bullet = Bullet(bullet_start_x, bullet_start_y, self.angle, 
                                    std_bullet_speed, std_bullet_lifetime, std_bullet_size, std_bullet_color,
                                    int(std_bullet_damage)) 
                self.bullets_group.add(new_bullet)
        
        # Lightning Firing
        if self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            if can_shoot_lightning:
                # Assuming lightning sound is same as primary shoot sound for now
                if sound_asset_key and self.asset_manager: 
                    sound = self.asset_manager.get_sound(sound_asset_key)
                    if sound: sound.play()
                self.last_lightning_time = current_time_ms
                
                closest_enemy_for_zap = None
                if enemies_group: # Find closest enemy in range
                    min_dist = float('inf')
                    for enemy_sprite in enemies_group:
                        if not hasattr(enemy_sprite, 'alive') or not enemy_sprite.alive or not hasattr(enemy_sprite, 'rect'): continue
                        dist = math.hypot(enemy_sprite.rect.centerx - self.x, enemy_sprite.rect.centery - self.y)
                        if dist < get_game_setting("LIGHTNING_ZAP_RANGE") and dist < min_dist:
                            min_dist = dist
                            closest_enemy_for_zap = enemy_sprite
                
                lightning_dmg_val = get_game_setting("LIGHTNING_DAMAGE") * self.bullet_damage_multiplier
                if maze is None: logger.critical("PlayerDrone.shoot() called for LightningZap with maze=None, which is required by LightningZap.")
                
                zap_lifetime = get_game_setting("LIGHTNING_LIFETIME", 30) # Default lifetime from settings
                
                # LightningZap constructor might need asset_manager if it creates particles that use sprites
                game_area_x_offset = maze.game_area_x_offset if maze and hasattr(maze, 'game_area_x_offset') else 0
                new_zap = LightningZap(self, closest_enemy_for_zap, int(lightning_dmg_val), 
                                       zap_lifetime, 
                                       maze, game_area_x_offset=game_area_x_offset) 
                self.lightning_zaps_group.add(new_zap)

    def take_damage(self, amount, sound_key_on_hit=None): # Use sound_key
        # (This method's logic for damage calculation remains, sound playing uses key)
        is_invincible_setting = get_game_setting("PLAYER_INVINCIBILITY", False)
        if is_invincible_setting: return # No damage if invincible setting is ON

        effective_amount = amount
        # Apply damage reduction from core fragments if drone_system is available
        if self.drone_system and hasattr(self.drone_system, 'get_collected_fragments_ids') and CORE_FRAGMENT_DETAILS:
            for frag_id in self.drone_system.get_collected_fragments_ids():
                frag_conf = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                if frag_conf and frag_conf.get("buff_alt", {}).get("type") == "damage_reduction":
                    effective_amount *= (1.0 - frag_conf["buff_alt"]["value"]) 
        
        if not self.alive: return # Can't take damage if already dead
        
        if self.shield_active: # Shield absorbs damage
            if sound_key_on_hit and self.asset_manager: 
                 sound = self.asset_manager.get_sound(sound_key_on_hit)
                 if sound: sound.play() 
            return # No damage taken

        self.health -= effective_amount
        if sound_key_on_hit and self.asset_manager:
            sound = self.asset_manager.get_sound(sound_key_on_hit)
            if sound: sound.play()
        
        if self.health <= 0:
            self.health = 0
            self.alive = False
            # Death handling (e.g. explosion, game over logic) is usually managed by GameController

    def activate_shield(self, duration, is_from_speed_boost=False):
        # (This method's logic remains the same)
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration
        self.shield_duration = duration
        self.shield_glow_pulse_time_offset = pygame.time.get_ticks() * 0.005 # Sync pulse with activation time
        if is_from_speed_boost:
            self.shield_tied_to_speed_boost = True 
        else:
            self.active_powerup_type = "shield" # Set current powerup type
            self.shield_tied_to_speed_boost = False

    def arm_speed_boost(self, duration, multiplier):
        # (This method's logic remains the same)
        self.speed_boost_duration = duration
        self.speed_boost_multiplier = multiplier
        self.active_powerup_type = "speed_boost"  # Mark that speed boost is armed

    def attempt_speed_boost_activation(self):
        # --- START FIX ---
        if self.active_powerup_type == "speed_boost" and not self.speed_boost_active and self.moving_forward:
            self.speed_boost_active = True
            self.speed_boost_end_time = pygame.time.get_ticks() + self.speed_boost_duration
            self.original_speed_before_boost = self.speed # Store current base speed
            self.speed = self.speed * self.speed_boost_multiplier # Directly modify the speed attribute used for movement
            self.activate_shield(self.speed_boost_duration, is_from_speed_boost=True)
        # --- END FIX ---

    def try_activate_cloak(self, current_time_ms):
        # (This method's logic remains the same for cloak activation timing)
        # Sound for cloak activation is played by GameController or PlayerActions
        if self.special_ability == "phantom_cloak" and not self.cloak_active and \
           current_time_ms > self.cloak_cooldown_end_time: # Check cooldown
            self.cloak_active = True
            self.is_cloaked_visual = True # For rendering
            self.cloak_end_time = current_time_ms + self.phantom_cloak_duration_ms
            self.last_cloak_activation_time = current_time_ms  # Record activation time
            return True # Successfully activated
        return False # Not available or on cooldown

    def cycle_weapon_state(self, force_cycle=True):
        # (This method's logic remains the same)
        if not force_cycle and self.current_weapon_mode == WEAPON_MODES_SEQUENCE[-1]:
            return False  # Already at the last weapon, no wrap-around unless forced
        
        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(WEAPON_MODES_SEQUENCE)
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_attributes() # Recalculate cooldowns, bullet size etc.
        return True

    def update_powerups(self, current_time_ms):
        # --- START FIX ---
        # Shield
        if self.shield_active and current_time_ms > self.shield_end_time:
            if not (self.shield_tied_to_speed_boost and self.speed_boost_active and current_time_ms <= self.speed_boost_end_time):
                self.shield_active = False
                if self.active_powerup_type == "shield": self.active_powerup_type = None
                self.shield_tied_to_speed_boost = False
        
        # Speed Boost
        if self.speed_boost_active and current_time_ms > self.speed_boost_end_time:
            self.speed_boost_active = False
            self.speed = self.original_speed_before_boost # Restore original speed
            if self.active_powerup_type == "speed_boost": self.active_powerup_type = None
            if self.shield_tied_to_speed_boost: 
                self.shield_active = False
                self.shield_tied_to_speed_boost = False
        # --- END FIX ---
        
        # Cloak
        if self.cloak_active and current_time_ms > self.cloak_end_time:
            self.cloak_active = False
            self.is_cloaked_visual = False # Stop rendering transparently
            self.cloak_cooldown_end_time = current_time_ms + self.phantom_cloak_cooldown_ms # Start cooldown

    def reset(self, x, y, drone_id, drone_stats, asset_manager, sprite_asset_key, preserve_weapon=False):
        previous_drone_id = self.drone_id
        super().reset(x,y)
        
        self.drone_id = drone_id
        self.asset_manager = asset_manager
        self.sprite_asset_key = sprite_asset_key
        
        self.base_hp = drone_stats.get("hp", get_game_setting("PLAYER_MAX_HEALTH"))
        self.base_speed = drone_stats.get("speed", get_game_setting("PLAYER_SPEED"))
        self.speed = self.base_speed
        self.original_speed_before_boost = self.speed

        self.base_turn_speed = drone_stats.get("turn_speed", get_game_setting("ROTATION_SPEED"))
        self.rotation_speed = self.base_turn_speed
        
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0)
        
        self.max_health = self.base_hp
        self.health = self.max_health
        
        # <<< RESET is_cruising STATE >>>
        self.is_cruising = False

        if previous_drone_id != self.drone_id or self.original_image is None:
            self._load_sprite()
        else:
            if self.original_image:
                self.image = pygame.transform.rotate(self.original_image, -self.angle)
                if self.rect: self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        
        if self.image and not self.rect:
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        elif self.rect:
            self.rect.center = (int(self.x), int(self.y))
        
        if self.rect and self.collision_rect:
            self.collision_rect.center = self.rect.center
        elif self.rect and not self.collision_rect:
            self.collision_rect = pygame.Rect(0,0, self.rect.width * 0.7, self.rect.height * 0.7)
            self.collision_rect.center = self.rect.center

        if not preserve_weapon: 
            initial_weapon_mode_gs = get_game_setting("INITIAL_WEAPON_MODE")
            try: self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
            except ValueError: self.weapon_mode_index = 0
            self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_attributes()
        
        self.bullets_group.empty()
        self.missiles_group.empty()
        self.lightning_zaps_group.empty()
        self.last_shot_time = 0
        self.last_missile_shot_time = 0
        self.last_lightning_time = 0
        
        self.reset_active_powerups()

    def reset_active_powerups(self):
        # --- START FIX ---
        self.shield_active = False; self.shield_end_time = 0
        self.speed_boost_active = False; self.speed_boost_end_time = 0
        self.speed = self.base_speed # Reset to base speed from current drone stats
        self.original_speed_before_boost = self.base_speed
        self.cloak_active = False; self.is_cloaked_visual = False; self.cloak_end_time = 0
        self.active_powerup_type = None
        self.thrust_particles.empty()
        self.shield_tied_to_speed_boost = False
        # --- END FIX ---

    def get_position(self):
        # (This method's logic remains the same)
        return (self.x, self.y)

    def draw(self, surface):
        # (This method's drawing logic remains largely the same, using self.image)
        if not self.alive and not self.bullets_group and not self.missiles_group and not self.lightning_zaps_group and not self.thrust_particles:
            return # Nothing to draw if dead and no lingering effects
        
        self.thrust_particles.draw(surface) # Draw thrust particles first (behind drone)
        
        if self.alive and self.image and self.original_image: # Ensure images are loaded  
            surface.blit(self.image, self.rect) # self.image is the rotated, alpha-set version
            
            # Shield visual effect
            if self.shield_active:
                current_time = pygame.time.get_ticks()
                # Sinusoidal pulse for shield alpha and size
                pulse_factor = (math.sin(current_time * 0.012 + self.shield_glow_pulse_time_offset) + 1) / 2 # Ranges 0 to 1
                shield_alpha = int(180 + pulse_factor * 75) # Pulse alpha between 180 and 255
                shield_color_tuple = POWERUP_TYPES.get("shield", {}).get("color", LIGHT_BLUE) # Get base color
                final_shield_color = (*shield_color_tuple[:3], shield_alpha) # Apply alpha
                
                # Draw shield outline using mask (more precise than just drawing a circle around rect)
                try:
                    if self.image.get_width() > 0 and self.image.get_height() > 0: # Ensure image has dimensions
                        drone_mask = pygame.mask.from_surface(self.image) # Use current image (could be cloaked)
                        outline_points = drone_mask.outline(1) # Get outline points of the drone sprite
                        if outline_points:
                            # Translate outline points to screen coordinates
                            screen_outline_points = [(p[0] + self.rect.left, p[1] + self.rect.top) for p in outline_points]
                            line_thickness = int(2 + pulse_factor * 2) # Pulse line thickness
                            pygame.draw.polygon(surface, final_shield_color, screen_outline_points, line_thickness)
                except pygame.error as e: # Catch potential errors from mask creation or drawing
                    # logger.warning(f"PlayerDrone: Error drawing shield effect: {e}")
                    # Fallback: draw a simple circle if mask fails
                    shield_radius = max(self.rect.width, self.rect.height) / 2 * 1.1 # Slightly larger than drone
                    pygame.draw.circle(surface, final_shield_color, self.rect.center, int(shield_radius), 3)
        
        # Draw projectiles
        self.bullets_group.draw(surface)
        self.missiles_group.draw(surface)
        
        if self.lightning_zaps_group:
            for zap in list(self.lightning_zaps_group): # Iterate over a copy if zaps can be removed during draw
                if hasattr(zap, 'draw') and callable(getattr(zap, 'draw')):
                    if hasattr(zap, 'alive') and zap.alive: # Only draw if zap is alive
                        zap.draw(surface) # LightningZap has its own complex draw method
            
        # Draw health bar only if alive
        if self.alive:
            self.draw_health_bar(surface)

    def draw_health_bar(self, surface):
        # (This method's logic remains the same)
        if not self.alive or not self.rect: return 
        
        bar_width = self.rect.width * 0.8; bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2; bar_y = self.rect.top - bar_height - 3 # Position above drone
        
        health_percentage = max(0, self.health / self.max_health) if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage
        
        pygame.draw.rect(surface, (80,0,0) if health_percentage < 0.3 else (50,50,50), (bar_x, bar_y, bar_width, bar_height)) # Background
        
        fill_color = RED
        if health_percentage >= 0.6: fill_color = GREEN
        elif health_percentage >= 0.3: fill_color = YELLOW
        
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height)) # Filled portion
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1) # Border
