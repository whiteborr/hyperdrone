import pygame
import math
import os # For os.path.exists

# Corrected import to use 'game_settings.py'
from game_settings import (
    PLAYER_SPEED, PLAYER_MAX_HEALTH, WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT, TILE_SIZE,
    GREEN, YELLOW, RED, BLACK, BLUE, CYAN, WHITE, LIGHT_BLUE, ORANGE, # Added ORANGE for consistency
    ROTATION_SPEED, 
    PLAYER_BASE_SHOOT_COOLDOWN, PLAYER_RAPID_FIRE_COOLDOWN, 
    POWERUP_TYPES, PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME,
    PLAYER_DEFAULT_BULLET_SIZE, PLAYER_BIG_BULLET_SIZE,
    WEAPON_MODES_SEQUENCE, INITIAL_WEAPON_MODE, WEAPON_MODE_ICONS, WEAPON_MODE_NAMES, # Added WEAPON_MODE_NAMES
    BOUNCING_BULLET_MAX_BOUNCES, PIERCING_BULLET_MAX_PIERCES,
    MISSILE_COOLDOWN, MISSILE_DAMAGE, MISSILE_COLOR, 
    LIGHTNING_COOLDOWN, LIGHTNING_DAMAGE, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE, LIGHTNING_COLOR, 
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, 
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING,
    PHANTOM_CLOAK_ALPHA_SETTING, PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS,
    SHIELD_POWERUP_DURATION, SPEED_BOOST_POWERUP_DURATION, 
    get_game_setting 
)
try:
    from bullet import Bullet, Missile, LightningZap
except ImportError:
    print("Warning (player.py): Could not import Bullet, Missile, or LightningZap from bullet.py. Shooting will be affected.")
    class Bullet(pygame.sprite.Sprite): pass
    class Missile(pygame.sprite.Sprite): pass
    class LightningZap(pygame.sprite.Sprite): pass

from base_drone import BaseDrone 

class Drone(BaseDrone):
    def __init__(self, x, y, drone_id, drone_stats, drone_sprite_path, crash_sound=None, drone_system=None):
        base_speed_from_stats = drone_stats.get("speed", PLAYER_SPEED)
        super().__init__(x, y, speed=base_speed_from_stats) 

        self.drone_id = drone_id
        self.drone_system = drone_system 

        self.base_hp = drone_stats.get("hp", PLAYER_MAX_HEALTH)
        self.base_turn_speed = drone_stats.get("turn_speed", ROTATION_SPEED) 
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0)

        self.max_health = self.base_hp
        self.health = self.max_health
        self.current_speed = self.speed 
        self.rotation_speed = self.base_turn_speed 

        self.original_image = None 
        self.image = None          
        self._load_sprite(drone_sprite_path) 

        initial_weapon_mode_setting = get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_setting)
        except ValueError: 
            print(f"Warning: Initial weapon mode '{initial_weapon_mode_setting}' not in sequence. Defaulting to first.")
            self.weapon_mode_index = 0
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]

        self.bullets_group = pygame.sprite.Group()
        self.missiles_group = pygame.sprite.Group()
        self.lightning_zaps_group = pygame.sprite.Group()
        self.last_shot_time = 0
        self.last_missile_shot_time = 0
        self.last_lightning_time = 0

        self.current_shoot_cooldown = PLAYER_BASE_SHOOT_COOLDOWN 
        self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") 
        self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") 
        self.bullet_size = PLAYER_DEFAULT_BULLET_SIZE 
        self._update_weapon_attributes() 

        self.active_powerup_type = None
        self.shield_active = False
        self.shield_end_time = 0
        self.shield_duration = get_game_setting("SHIELD_POWERUP_DURATION")
        self.shield_visual_radius = (self.rect.width // 2 + 5) if self.rect else (TILE_SIZE // 2 + 5)
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
        self.phantom_cloak_alpha = get_game_setting("PHANTOM_CLOAK_ALPHA_SETTING")
        self.phantom_cloak_duration_ms = get_game_setting("PHANTOM_CLOAK_DURATION_MS")
        self.phantom_cloak_cooldown_ms = get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS")

        self.crash_sound = crash_sound

        if self.rect: 
            self.collision_rect_width = self.rect.width * 0.7
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else: 
            self.collision_rect = pygame.Rect(self.x - TILE_SIZE*0.35, self.y - TILE_SIZE*0.35, TILE_SIZE*0.7, TILE_SIZE*0.7)


    def _load_sprite(self, sprite_path):
        """Loads the drone's visual sprite and updates self.image and self.rect."""
        default_sprite_size = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 0.8))

        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.smoothscale(loaded_image, default_sprite_size)
            except pygame.error as e:
                print(f"Player Log: Error loading sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None 
        else:
            if sprite_path: print(f"Player Log: Sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None: 
            self.original_image = pygame.Surface(default_sprite_size, pygame.SRCALPHA)
            self.original_image.fill((*GREEN, 180)) 
            pygame.draw.circle(self.original_image, WHITE, (default_sprite_size[0]//2, default_sprite_size[1]//2), default_sprite_size[0]//3, 2)

        self.image = self.original_image.copy() 
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect_width = self.rect.width * 0.7
        self.collision_rect_height = self.rect.height * 0.7
        self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center


    def _update_weapon_attributes(self):
        """Sets weapon parameters (cooldown, bullet size) based on the current weapon mode."""
        if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
            self.bullet_size = get_game_setting("PLAYER_BIG_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") * 1.5 
        elif self.current_weapon_mode in [WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN")
        else: 
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")

        if self.base_fire_rate_multiplier != 0: 
            self.current_shoot_cooldown /= self.base_fire_rate_multiplier
            self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") / self.base_fire_rate_multiplier
            self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") / self.base_fire_rate_multiplier
        else: 
            self.current_shoot_cooldown = 99999 
            self.current_missile_cooldown = 99999
            self.current_lightning_cooldown = 99999

    def get_position(self):
        return self.x, self.y

    def rotate(self, direction, rotation_speed_override=None):
        effective_rotation_speed = rotation_speed_override if rotation_speed_override is not None else self.rotation_speed
        if direction == "left":  
            self.angle -= effective_rotation_speed
        elif direction == "right":  
            self.angle += effective_rotation_speed
        self.angle %= 360

    def handle_input(self, keys): 
        if keys[pygame.K_LEFT]:
            self.rotate("left")
        if keys[pygame.K_RIGHT]:
            self.rotate("right")

    def update(self, current_time, maze, enemies_group, game_area_x_offset=0):
        if not self.alive:
            return

        self.update_powerups(current_time) 

        # MODIFIED: Call player's own _update_movement, not BaseDrone's
        self._update_movement(maze, game_area_x_offset) 

        self.bullets_group.update(maze, game_area_x_offset)
        self.missiles_group.update(enemies_group, maze, game_area_x_offset)
        self.lightning_zaps_group.update(current_time) 

        current_alpha = self.phantom_cloak_alpha if self.is_cloaked_visual else 255
        if self.original_image:
            rotated_image = pygame.transform.rotate(self.original_image, -self.angle)
            self.image = rotated_image.convert_alpha() 
            self.image.set_alpha(current_alpha)
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self.collision_rect: 
                self.collision_rect.center = self.rect.center
        else: 
            if self.rect: self.rect.center = (int(self.x), int(self.y))


    def _update_movement(self, maze, game_area_x_offset):
        """
        Player-specific movement logic, uses self.current_speed.
        """
        if self.moving_forward and self.alive:
            angle_rad = math.radians(self.angle)
            dx = math.cos(angle_rad) * self.current_speed 
            dy = math.sin(angle_rad) * self.current_speed 

            next_x = self.x + dx
            next_y = self.y + dy
            
            temp_collision_rect = self.collision_rect.copy()
            temp_collision_rect.center = (next_x, next_y)

            collided_wall_type = None
            if maze:
                collided_wall_type = maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery,
                                                self.collision_rect_width, self.collision_rect_height)

            if collided_wall_type:
                self._handle_wall_collision(collided_wall_type, dx, dy)
            else:
                self.x = next_x
                self.y = next_y

        half_col_width = self.collision_rect_width / 2
        half_col_height = self.collision_rect_height / 2
        min_x_bound = game_area_x_offset + half_col_width
        # Use directly imported GAME_PLAY_AREA_HEIGHT instead of get_game_setting
        max_x_bound = WIDTH - half_col_width # WIDTH is imported directly
        min_y_bound = half_col_height
        max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height # Use imported GAME_PLAY_AREA_HEIGHT

        self.x = max(min_x_bound, min(self.x, max_x_bound))
        self.y = max(min_y_bound, min(self.y, max_y_bound))

        if self.rect: self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect: self.collision_rect.center = (int(self.x), int(self.y))


    def _handle_wall_collision(self, wall_type, dx, dy):
        """Player's response to hitting a wall."""
        if not self.shield_active: 
            self.take_damage(10, self.crash_sound) 

        self.moving_forward = False 


    def shoot(self, sound=None, missile_sound=None, maze=None, enemies_group=None):
        current_time = pygame.time.get_ticks()
        can_shoot_primary = (current_time - self.last_shot_time) > self.current_shoot_cooldown
        can_shoot_missile = (current_time - self.last_missile_shot_time) > self.current_missile_cooldown
        can_shoot_lightning = (current_time - self.last_lightning_time) > self.current_lightning_cooldown

        nose_offset_factor = (self.rect.height / 2 if self.rect else TILE_SIZE * 0.4) * 0.7 
        rad_angle_shoot = math.radians(self.angle) 
        bullet_start_x = self.x + math.cos(rad_angle_shoot) * nose_offset_factor
        bullet_start_y = self.y + math.sin(rad_angle_shoot) * nose_offset_factor

        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING]:
            if can_shoot_primary:
                if sound: sound.play()
                self.last_shot_time = current_time
                angles_to_fire = [0] 
                if self.current_weapon_mode == WEAPON_MODE_TRI_SHOT or self.current_weapon_mode == WEAPON_MODE_RAPID_TRI:
                    angles_to_fire = [-15, 0, 15]

                for angle_offset in angles_to_fire:
                    effective_bullet_angle = self.angle + angle_offset
                    bullet_speed = get_game_setting("PLAYER_BULLET_SPEED")
                    bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME")
                    bullet_color = get_game_setting("PLAYER_BULLET_COLOR")
                    current_bullet_damage = 10 * self.bullet_damage_multiplier 
                    if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
                        current_bullet_damage *= 2.5

                    max_b = get_game_setting("BOUNCING_BULLET_MAX_BOUNCES") if self.current_weapon_mode == WEAPON_MODE_BOUNCE else 0
                    max_p = get_game_setting("PIERCING_BULLET_MAX_PIERCES") if self.current_weapon_mode == WEAPON_MODE_PIERCE else 0

                    new_bullet = Bullet(bullet_start_x, bullet_start_y, effective_bullet_angle,
                                        bullet_speed, bullet_lifetime, self.bullet_size, bullet_color,
                                        current_bullet_damage, max_b, max_p)
                    self.bullets_group.add(new_bullet)

        if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or \
           self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
            if can_shoot_missile:
                if missile_sound: missile_sound.play()
                self.last_missile_shot_time = current_time
                missile_dmg = get_game_setting("MISSILE_DAMAGE") * self.bullet_damage_multiplier
                new_missile = Missile(bullet_start_x, bullet_start_y, self.angle, missile_dmg, enemies_group)
                self.missiles_group.add(new_missile)

        if self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            if can_shoot_lightning:
                if sound: sound.play() 
                self.last_lightning_time = current_time
                target_enemy_pos = None
                if enemies_group:
                    closest_enemy = None; min_dist_sq = float('inf')
                    zap_range_sq = get_game_setting("LIGHTNING_ZAP_RANGE") ** 2
                    for enemy in enemies_group:
                        if not enemy.alive: continue
                        dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
                        if dist_sq < zap_range_sq and dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq; closest_enemy = enemy
                    if closest_enemy: target_enemy_pos = closest_enemy.rect.center
                
                lightning_dmg = get_game_setting("LIGHTNING_DAMAGE") * self.bullet_damage_multiplier
                new_zap = LightningZap(self.rect.center, target_enemy_pos, lightning_dmg, get_game_setting("LIGHTNING_LIFETIME"))
                self.lightning_zaps_group.add(new_zap)


    def take_damage(self, amount, sound=None):
        if not self.alive: return
        if self.shield_active:
            if amount > 0 and sound: sound.play() 
            return

        self.health -= amount
        if sound: sound.play()
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def draw_health_bar(self, surface):
        if not self.alive or not self.rect: return

        bar_width = self.rect.width * 0.8
        bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 3

        health_percentage = max(0, self.health / self.max_health)
        filled_width = bar_width * health_percentage

        pygame.draw.rect(surface, (80,0,0) if health_percentage < 0.3 else (50,50,50), (bar_x, bar_y, bar_width, bar_height))
        fill_color = RED
        if health_percentage >= 0.6: fill_color = GREEN
        elif health_percentage >= 0.3: fill_color = YELLOW
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

    def activate_shield(self, duration_ms, is_from_speed_boost=False):
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration_ms
        self.shield_duration = duration_ms 
        if not is_from_speed_boost: 
            self.active_powerup_type = "shield"

    def arm_speed_boost(self, duration_ms, multiplier_val):
        self.speed_boost_duration = duration_ms
        self.speed_boost_multiplier = multiplier_val
        self.active_powerup_type = "speed_boost" 

    def attempt_speed_boost_activation(self): 
        if self.active_powerup_type == "speed_boost" and not self.speed_boost_active and self.moving_forward:
            self.speed_boost_active = True
            self.speed_boost_end_time = pygame.time.get_ticks() + self.speed_boost_duration
            self.original_speed_before_boost = self.speed 
            self.current_speed = self.speed * self.speed_boost_multiplier 
            co_shield_duration = self.speed_boost_duration // 2 
            self.activate_shield(co_shield_duration, is_from_speed_boost=True)

    def try_activate_cloak(self, current_time_ms):
        if self.special_ability == "phantom_cloak" and \
           not self.cloak_active and \
           current_time_ms > self.cloak_cooldown_end_time: 
            self.cloak_active = True
            self.is_cloaked_visual = True 
            self.cloak_start_time = current_time_ms
            self.cloak_end_time = current_time_ms + self.phantom_cloak_duration_ms
            print(f"Player: Cloak ON at {current_time_ms}, ends {self.cloak_end_time}")
            return True
        return False

    def cycle_weapon_state(self, force_cycle=True):
        if not WEAPON_MODES_SEQUENCE: return False
        if not force_cycle and self.weapon_mode_index == len(WEAPON_MODES_SEQUENCE) - 1:
            return False 

        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(WEAPON_MODES_SEQUENCE)
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_attributes()
        print(f"Player: Weapon cycled to {WEAPON_MODE_NAMES.get(self.current_weapon_mode, 'Unknown')}")
        return True

    def update_powerups(self, current_time_ms):
        if self.shield_active and current_time_ms > self.shield_end_time:
            self.shield_active = False
            if self.active_powerup_type == "shield": self.active_powerup_type = None

        if self.speed_boost_active and current_time_ms > self.speed_boost_end_time:
            self.speed_boost_active = False
            self.current_speed = self.speed 
            if self.active_powerup_type == "speed_boost": self.active_powerup_type = None

        if self.cloak_active and current_time_ms > self.cloak_end_time:
            self.cloak_active = False
            self.is_cloaked_visual = False
            self.cloak_cooldown_end_time = current_time_ms + self.phantom_cloak_cooldown_ms
            print(f"Player: Cloak OFF at {current_time_ms}, cooldown until {self.cloak_cooldown_end_time}")


    def reset(self, x, y, drone_id, drone_stats, drone_sprite_path, health_override=None):
        base_speed_from_stats = drone_stats.get("speed", PLAYER_SPEED)
        super().__init__(x, y, speed=base_speed_from_stats) 

        self.drone_id = drone_id
        self.base_hp = drone_stats.get("hp", PLAYER_MAX_HEALTH)
        self.base_turn_speed = drone_stats.get("turn_speed", ROTATION_SPEED)
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0)

        self.max_health = self.base_hp
        self.health = health_override if health_override is not None else self.max_health

        self.current_speed = self.speed 
        self.rotation_speed = self.base_turn_speed

        self._load_sprite(drone_sprite_path) 

        initial_weapon_mode_setting = get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_setting)
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
        self.shield_active = False; self.shield_end_time = 0
        self.speed_boost_active = False; self.speed_boost_end_time = 0
        self.current_speed = self.speed 
        self.original_speed_before_boost = self.speed 

        self.cloak_active = False; self.is_cloaked_visual = False; self.cloak_end_time = 0
        self.active_powerup_type = None


    def draw(self, surface):
        if not self.alive and not (self.bullets_group or self.missiles_group or self.lightning_zaps_group):
            return 

        if self.alive and self.image: 
            surface.blit(self.image, self.rect) 
            if self.shield_active: 
                current_time_ticks = pygame.time.get_ticks()
                pulse = abs(math.sin(current_time_ticks * 0.005 + self.shield_pulse_angle))
                alpha = int(50 + pulse * 70)
                shield_base_color = POWERUP_TYPES.get("shield", {}).get("color", LIGHT_BLUE)
                shield_draw_color = (*shield_base_color[:3], alpha)
                for i in range(1, 4):
                    pygame.draw.circle(surface, shield_draw_color, self.rect.center,
                                     int(self.shield_visual_radius + i * 2 - pulse * 3), 2)
        
        self.bullets_group.draw(surface)
        self.missiles_group.draw(surface)
        self.lightning_zaps_group.draw(surface)

        if self.alive: 
            self.draw_health_bar(surface)


if __name__ == '__main__':
    pygame.init()
    try:
        from game_settings import WIDTH as SCREEN_WIDTH, HEIGHT as SCREEN_HEIGHT, FPS as GAME_FPS
        from game_settings import PLAYER_MAX_HEALTH, PLAYER_SPEED, ROTATION_SPEED, PLAYER_DEFAULT_BULLET_SIZE
        from game_settings import INITIAL_WEAPON_MODE, PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS, PHANTOM_CLOAK_ALPHA_SETTING
        # Ensure GAME_PLAY_AREA_HEIGHT is available for the test if used directly
        from game_settings import GAME_PLAY_AREA_HEIGHT as TEST_GAME_PLAY_AREA_HEIGHT 

    except ImportError: 
        SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600; GAME_FPS = 60
        PLAYER_MAX_HEALTH, PLAYER_SPEED, ROTATION_SPEED, PLAYER_DEFAULT_BULLET_SIZE = 100,3,5,4
        INITIAL_WEAPON_MODE = 0; PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS, PHANTOM_CLOAK_ALPHA_SETTING = 5000,15000,70
        TEST_GAME_PLAY_AREA_HEIGHT = SCREEN_HEIGHT # Fallback for test


    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Player Drone Test")

    class MockSound:
        def play(self): pass
    mock_crash_sound = MockSound()
    mock_shoot_sound = MockSound()
    mock_missile_sound = MockSound()

    mock_drone_stats = {
        "hp": PLAYER_MAX_HEALTH, "speed": PLAYER_SPEED, "turn_speed": ROTATION_SPEED,
        "fire_rate_multiplier": 1.0, "special_ability": "phantom_cloak", 
        "bullet_damage_multiplier": 1.0
    }
    mock_drone_id = "TEST_PHANTOM"
    mock_sprite_path = os.path.join("assets", "drones", "phantom_2d.png") 
    if not os.path.exists(mock_sprite_path):
        print(f"Test Warning: Sprite {mock_sprite_path} not found, will use fallback.")
        mock_sprite_path = None


    player_drone = Drone(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                         mock_drone_id, mock_drone_stats, mock_sprite_path,
                         mock_crash_sound, None) 

    clock = pygame.time.Clock()
    running = True

    class MockMaze:
        def is_wall(self, x, y, width, height): return False
    mock_maze = MockMaze()
    mock_enemies_group = pygame.sprite.Group()

    while running:
        current_tick_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP: player_drone.moving_forward = True
                if event.key == pygame.K_DOWN: player_drone.moving_forward = False # For toggle movement test
                if event.key == pygame.K_SPACE: player_drone.shoot(mock_shoot_sound, mock_missile_sound, mock_maze, mock_enemies_group)
                if event.key == pygame.K_c: player_drone.try_activate_cloak(current_tick_time)
                if event.key == pygame.K_s: player_drone.cycle_weapon_state()
                if event.key == pygame.K_h: player_drone.take_damage(20) 
                if event.key == pygame.K_p: 
                    player_drone.activate_shield(5000) 
                if event.key == pygame.K_o: 
                    player_drone.arm_speed_boost(3000, 2.0) 

        keys = pygame.key.get_pressed()
        player_drone.handle_input(keys) 
        
        if player_drone.moving_forward and player_drone.active_powerup_type == "speed_boost" and not player_drone.speed_boost_active:
             player_drone.attempt_speed_boost_activation()


        player_drone.update(current_tick_time, mock_maze, mock_enemies_group)

        screen.fill(BLACK)
        player_drone.draw(screen)
        pygame.display.flip()
        clock.tick(GAME_FPS)

    pygame.quit()
