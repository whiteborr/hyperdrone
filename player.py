# player.py
import pygame
import math
import os
import random # For potential random elements in abilities if added later

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
    get_game_setting 
)
# Assuming bullet.py contains Bullet and Missile classes
try:
    from bullet import Bullet, Missile, LightningZap
except ImportError:
    print("Warning (player.py): Could not import Bullet, Missile, or LightningZap from bullet.py. Shooting will be affected.")
    # Define dummy classes if bullet.py is not available
    class Bullet(pygame.sprite.Sprite): pass
    class Missile(pygame.sprite.Sprite): pass
    class LightningZap(pygame.sprite.Sprite): pass


class Drone(pygame.sprite.Sprite):
    def __init__(self, x, y, drone_id, drone_stats, drone_sprite_path, crash_sound, drone_system):
        super().__init__()
        self.drone_id = drone_id
        self.drone_system = drone_system 
        
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.alive = True
        self.moving_forward = False

        # Load base stats from drone_stats dictionary
        self.base_hp = drone_stats.get("hp", 100)
        self.base_speed = drone_stats.get("speed", 3)
        self.base_turn_speed = drone_stats.get("turn_speed", 5)
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability") 

        self.max_health = self.base_hp
        self.health = self.max_health
        self.speed = self.base_speed
        self.current_speed = self.speed 
        self.rotation_speed = self.base_turn_speed
        
        self.original_image = None
        self.image = None
        self.rect = None
        self._load_sprite(drone_sprite_path) 

        # Weapon systems
        self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(get_game_setting("INITIAL_WEAPON_MODE"))
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
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0) 
        self._update_weapon_attributes()

        # Power-ups / Abilities
        self.active_powerup_type = None 
        self.shield_active = False
        self.shield_end_time = 0
        self.shield_duration = get_game_setting("SHIELD_POWERUP_DURATION") 
        self.shield_visual_radius = self.rect.width // 2 + 5 if self.rect else TILE_SIZE // 2
        self.shield_pulse_angle = 0

        self.speed_boost_active = False
        self.speed_boost_end_time = 0
        self.speed_boost_duration = get_game_setting("SPEED_BOOST_POWERUP_DURATION")
        self.speed_boost_multiplier = 1.0
        self.original_speed_before_boost = self.speed 

        self.cloak_active = False
        self.cloak_start_time = 0 
        self.cloak_end_time = 0
        self.last_cloak_activation_time = -float('inf') 
        self.cloak_cooldown_end_time = 0 
        self.is_cloaked_visual = False 
        self.phantom_cloak_alpha = get_game_setting("PHANTOM_CLOAK_ALPHA")
        self.phantom_cloak_duration_ms = get_game_setting("PHANTOM_CLOAK_DURATION_MS")
        self.phantom_cloak_cooldown_ms = get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS")


        self.crash_sound = crash_sound
        self.collision_rect_width = self.rect.width * 0.7 if self.rect else TILE_SIZE * 0.7
        self.collision_rect_height = self.rect.height * 0.7 if self.rect else TILE_SIZE * 0.7
        self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center if self.rect else (self.x, self.y)


    def _load_sprite(self, sprite_path):
        default_size = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 0.8))
        if sprite_path and os.path.exists(sprite_path):
            try:
                self.original_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(self.original_image, default_size)
            except pygame.error as e:
                print(f"Error loading player sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
                self.original_image.fill((0, 200, 0, 150)) # Greenish transparent fallback
                pygame.draw.circle(self.original_image, (255,255,255), (default_size[0]//2, default_size[1]//2), default_size[0]//3)
        else:
            if sprite_path: print(f"Warning: Player sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            self.original_image.fill((0, 200, 0, 150))
            pygame.draw.circle(self.original_image, (255,255,255), (default_size[0]//2, default_size[1]//2), default_size[0]//3)

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.collision_rect_width = self.rect.width * 0.7
        self.collision_rect_height = self.rect.height * 0.7
        self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center

    def _update_weapon_attributes(self):
        """Sets weapon parameters based on the current weapon mode."""
        if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
            self.bullet_size = get_game_setting("PLAYER_BIG_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") * 1.5 # Slower for big shot
        elif self.current_weapon_mode in [WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN")
        else: # Default, Tri-shot, Bounce, Pierce
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        
        self.current_shoot_cooldown /= self.base_fire_rate_multiplier
        self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") / self.base_fire_rate_multiplier
        self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") / self.base_fire_rate_multiplier


    def update(self, current_time, maze, enemies_group, game_area_x_offset=0):
        if not self.alive:
            return

        self._update_movement(maze, game_area_x_offset)
        
        self.bullets_group.update(maze) 
        self.missiles_group.update(enemies_group, maze) 
        self.lightning_zaps_group.update(current_time) 

        # Shield update
        if self.shield_active and current_time > self.shield_end_time:
            self.shield_active = False
            if self.active_powerup_type == "shield": self.active_powerup_type = None

        # Speed boost update
        if self.speed_boost_active and current_time > self.speed_boost_end_time:
            self.speed_boost_active = False
            self.current_speed = self.original_speed_before_boost 
            if self.active_powerup_type == "speed_boost": self.active_powerup_type = None
        
        # Cloak update
        if self.cloak_active and current_time > self.cloak_end_time:
            self.cloak_active = False
            self.is_cloaked_visual = False
            self.cloak_cooldown_end_time = current_time + self.phantom_cloak_cooldown_ms

        # Visual updates
        self.image = pygame.transform.rotate(self.original_image, -self.angle) # Pygame rotates CCW for positive
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.collision_rect.center = self.rect.center

        if self.is_cloaked_visual:
            self.image.set_alpha(self.phantom_cloak_alpha)
        else:
            self.image.set_alpha(255)


    def _update_movement(self, maze, game_area_x_offset):
        if self.moving_forward:
            rad_angle = math.radians(self.angle)
            dx = math.sin(rad_angle) * self.current_speed
            dy = -math.cos(rad_angle) * self.current_speed 

            temp_x = self.x + dx
            temp_y = self.y + dy
            
            temp_collision_rect = self.collision_rect.copy()
            temp_collision_rect.center = (temp_x, temp_y)

            collided_wall_type = None
            if maze: 
                collided_wall_type = maze.is_wall(temp_x, temp_y, self.collision_rect_width, self.collision_rect_height)

            if collided_wall_type:
                self._handle_wall_collision(collided_wall_type, dx, dy)
            else:
                self.x = temp_x
                self.y = temp_y
        
        half_width = self.rect.width / 2
        half_height = self.rect.height / 2
        
        min_x = game_area_x_offset + half_width
        max_x = WIDTH - half_width 
        min_y = half_height
        max_y = GAME_PLAY_AREA_HEIGHT - half_height

        self.x = max(min_x, min(self.x, max_x))
        self.y = max(min_y, min(self.y, max_y))
        
        self.rect.center = (self.x, self.y)
        self.collision_rect.center = self.rect.center


    def _handle_wall_collision(self, wall_type, dx, dy):
        if wall_type == "internal" and not self.shield_active: 
            self.take_damage(10, self.crash_sound) 
        
        self.x -= dx * 0.5 
        self.y -= dy * 0.5
        self.moving_forward = False 


    def rotate(self, direction, rotation_speed_override=None):
        effective_rotation_speed = rotation_speed_override if rotation_speed_override is not None else self.rotation_speed
        # To make left arrow visually rotate counter-clockwise (CCW):
        # Pygame's transform.rotate(image, angle) rotates CCW for positive angles.
        # We draw with -self.angle. So, for CCW visual, -self.angle must be positive.
        # This means self.angle must become more negative.
        #
        # If user reports "left arrow rotates opposite", it means they expect CCW for left, but get CW.
        # Current logic for "left": self.angle = (self.angle - effective_rotation_speed) -> self.angle becomes more negative -> -self.angle becomes more positive -> CCW. This is standard.
        # To reverse this (if user's "opposite" means they want left arrow to be CW):
        if direction == "left": 
            self.angle = (self.angle + effective_rotation_speed) % 360 # Changed from - to +
        elif direction == "right": 
            self.angle = (self.angle - effective_rotation_speed) % 360 # Changed from + to -

    def shoot(self, sound=None, missile_sound=None, maze=None, enemies_group=None):
        current_time = pygame.time.get_ticks()
        can_shoot_primary = (current_time - self.last_shot_time) > self.current_shoot_cooldown
        can_shoot_missile = (current_time - self.last_missile_shot_time) > self.current_missile_cooldown
        can_shoot_lightning = (current_time - self.last_lightning_time) > self.current_lightning_cooldown

        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING]: 
            if can_shoot_primary:
                if sound: sound.play()
                self.last_shot_time = current_time
                angles = [0]
                if self.current_weapon_mode == WEAPON_MODE_TRI_SHOT or self.current_weapon_mode == WEAPON_MODE_RAPID_TRI:
                    angles = [-15, 0, 15]
                
                for angle_offset in angles:
                    bullet_angle = self.angle + angle_offset
                    bullet_speed = get_game_setting("PLAYER_BULLET_SPEED")
                    bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME")
                    bullet_color = get_game_setting("PLAYER_BULLET_COLOR")
                    
                    bullet_damage = 10 * self.bullet_damage_multiplier 
                    if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT: bullet_damage *= 2.5

                    bounces = 0; pierces = 0
                    if self.current_weapon_mode == WEAPON_MODE_BOUNCE: bounces = get_game_setting("BOUNCING_BULLET_MAX_BOUNCES")
                    if self.current_weapon_mode == WEAPON_MODE_PIERCE: pierces = get_game_setting("PIERCING_BULLET_MAX_PIERCES")

                    new_bullet = Bullet(self.x, self.y, bullet_angle, bullet_speed, bullet_lifetime, 
                                        self.bullet_size, bullet_color, bullet_damage, bounces, pierces)
                    self.bullets_group.add(new_bullet)

        if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
            if can_shoot_missile:
                if missile_sound: missile_sound.play()
                self.last_missile_shot_time = current_time
                new_missile = Missile(self.x, self.y, self.angle, MISSILE_DAMAGE, enemies_group)
                self.missiles_group.add(new_missile)
        
        if self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            if can_shoot_lightning:
                if sound: sound.play() 
                self.last_lightning_time = current_time
                target = None
                if enemies_group:
                    closest_enemy = None
                    min_dist = float('inf')
                    for enemy in enemies_group:
                        dist = math.hypot(enemy.rect.centerx - self.x, enemy.rect.centery - self.y)
                        if dist < LIGHTNING_ZAP_RANGE and dist < min_dist:
                            min_dist = dist
                            closest_enemy = enemy
                    if closest_enemy:
                        target = closest_enemy.rect.center
                
                new_zap = LightningZap(self.rect.center, target, LIGHTNING_DAMAGE, LIGHTNING_LIFETIME)
                self.lightning_zaps_group.add(new_zap)


    def take_damage(self, amount, sound=None):
        if not self.alive or self.shield_active:
            if self.shield_active and amount > 0 : 
                if sound: sound.play() 
            return

        self.health -= amount
        if sound:
            sound.play()
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def activate_shield(self, duration, is_from_speed_boost=False): 
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration
        self.shield_duration = duration 
        self.active_powerup_type = "shield" 

    def arm_speed_boost(self, duration, multiplier):
        self.speed_boost_duration = duration
        self.speed_boost_multiplier = multiplier
        self.active_powerup_type = "speed_boost" 

    def attempt_speed_boost_activation(self):
        if self.active_powerup_type == "speed_boost" and not self.speed_boost_active and self.moving_forward:
            self.speed_boost_active = True
            self.speed_boost_end_time = pygame.time.get_ticks() + self.speed_boost_duration
            self.original_speed_before_boost = self.speed 
            self.current_speed = self.speed * self.speed_boost_multiplier


    def try_activate_cloak(self, current_time):
        if self.special_ability == "phantom_cloak" and not self.cloak_active and \
           current_time > self.cloak_cooldown_end_time:
            self.cloak_active = True
            self.is_cloaked_visual = True
            self.cloak_end_time = current_time + self.phantom_cloak_duration_ms
            self.last_cloak_activation_time = current_time 
            return True
        return False

    def cycle_weapon_state(self, force_cycle=True): 
        if not force_cycle and self.current_weapon_mode == WEAPON_MODES_SEQUENCE[-1]: 
            return False 
            
        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(WEAPON_MODES_SEQUENCE)
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_attributes()
        return True

    def reset(self, x, y, drone_id, drone_stats, drone_sprite_path, health_override=None):
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0 
        self.alive = True
        self.moving_forward = False

        self.base_hp = drone_stats.get("hp", 100)
        self.base_speed = drone_stats.get("speed", 3)
        self.base_turn_speed = drone_stats.get("turn_speed", 5)
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0)

        self.max_health = self.base_hp
        self.health = health_override if health_override is not None else self.max_health
        
        self.speed = self.base_speed
        self.current_speed = self.speed
        self.rotation_speed = self.base_turn_speed

        if self.drone_id != drone_id or not self.original_image: 
            self.drone_id = drone_id
            self._load_sprite(drone_sprite_path)
        
        self.rect.center = (self.x, self.y)
        self.collision_rect.center = self.rect.center

        self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(get_game_setting("INITIAL_WEAPON_MODE"))
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
        self.shield_active = False
        self.shield_end_time = 0
        self.speed_boost_active = False
        self.speed_boost_end_time = 0
        self.current_speed = self.speed 
        self.cloak_active = False
        self.is_cloaked_visual = False
        self.cloak_end_time = 0
        self.active_powerup_type = None 


    def get_position(self):
        return (self.x, self.y)

    def draw(self, surface):
        if not self.alive and not self.bullets_group and not self.missiles_group and not self.lightning_zaps_group: 
            return

        if self.alive: 
            surface.blit(self.image, self.rect)
            if self.shield_active:
                current_time = pygame.time.get_ticks()
                pulse = abs(math.sin(current_time * 0.005 + self.shield_pulse_angle)) 
                alpha = 50 + int(pulse * 70) 
                shield_base_color = POWERUP_TYPES.get("shield", {}).get("color", (173, 216, 230)) # Fallback color
                shield_color_with_alpha = (*shield_base_color[:3], alpha)
                
                for i in range(3): 
                    pygame.draw.circle(surface, shield_color_with_alpha, self.rect.center, self.shield_visual_radius + i, 2)
        
        self.bullets_group.draw(surface)
        self.missiles_group.draw(surface)
        self.lightning_zaps_group.draw(surface)

