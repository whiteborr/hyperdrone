# entities/enemy.py
from math import hypot, degrees, atan2
from random import randint, random
import logging

from pygame.sprite import Sprite
from pygame.time import get_ticks
from pygame import Surface, SRCALPHA
from pygame.draw import polygon

try:
    from .bullet import Bullet 
except ImportError:
    class Bullet(Sprite): pass

# Import from settings_manager for settings access
from settings_manager import get_setting
from constants import GREEN, YELLOW, RED, WHITE, DARK_PURPLE

# Import behaviors and pathfinding component
from ai.behaviors import ChasePlayerBehavior, RetreatBehavior # NEW: Import RetreatBehavior
from ai.pathfinding_component import PathfinderComponent

logger = logging.getLogger(__name__)

class Enemy(Sprite):
    def __init__(self, x, y, asset_manager, config, target_player_ref=None):
        super().__init__()
        self.x, self.y, self.angle = float(x), float(y), 0.0
        self.config = config
        self.alive = True
        self.asset_manager = asset_manager
        
        # Set attributes from the config dictionary
        stats = self.config.get("stats", {})
        self.health = stats.get("health", 100)
        self.max_health = self.health
        self.speed = stats.get("speed", 1.5)
        self.contact_damage = stats.get("contact_damage", 25)
        
        # Get tile size for calculations
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.aggro_radius = tile_size * stats.get("aggro_radius_tiles", 9)
        
        # Asset keys
        assets = self.config.get("assets", {})
        self.sprite_asset_key = assets.get("sprite_asset_key", "regular_enemy_sprite_key")
        self.shoot_sound_key = assets.get("shoot_sound_key")
        
        # Player reference
        self.player_ref = target_player_ref
        
        # Initialize sprite
        self.original_image, self.image, self.rect, self.collision_rect = None, None, None, None
        self._load_sprite()
        
        # Bullet system
        from pygame.sprite import Group
        self.bullets = Group()
        self.last_shot_time = get_ticks() + randint(0, 1500)
        
        # Weapon configuration
        weapon_config = self.config.get("weapon", {})
        if weapon_config:
            self.shoot_cooldown = weapon_config.get("shoot_cooldown", 1500)
            player_bullet_size_base = get_setting("weapons", "PLAYER_DEFAULT_BULLET_SIZE", 4)
            bullet_size_ratio = weapon_config.get("bullet_size_ratio", 0.67)
            self.enemy_bullet_size = int(player_bullet_size_base * bullet_size_ratio)
        else:
            self.shoot_cooldown = 0
            self.enemy_bullet_size = 0
        
        # Initialize pathfinder component
        self.pathfinder = PathfinderComponent(self)
        
        # Behavior system
        self.behavior = None
        ai_config = self.config.get("ai", {})
        initial_behavior = ai_config.get("initial_behavior", "ChasePlayerBehavior")
        
        # Set default behavior
        self.default_behavior = ChasePlayerBehavior
        self.set_behavior(ChasePlayerBehavior(self))

        # NEW: Retreat behavior attributes
        self.retreat_health_threshold = self.max_health * get_setting("enemies", "RETREAT_HEALTH_THRESHOLD", 0.3)
        self.can_retreat = get_setting("enemies", "CAN_RETREAT", True) # Global setting for enemy retreat behavior


    def _load_sprite(self):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        default_size = (int(tile_size * 0.7), int(tile_size * 0.7)) 
        self.original_image = self.asset_manager.get_image(self.sprite_asset_key, scale_to_size=default_size)
        if self.original_image is None: self.original_image = self.asset_manager._create_fallback_surface(size=default_size, color=(255, 0, 0)) 
        self.image = self.original_image.copy(); self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)



    def set_behavior(self, new_behavior):
        """Change the current behavior of the enemy"""
        # Only change behavior if it's different from the current one
        if not isinstance(self.behavior, type(new_behavior)):
            self.behavior = new_behavior
        
    def update(self, primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=False):
        if not self.alive:
            self.bullets.update(maze, game_area_x_offset)
            if not self.bullets: self.kill()
            return

        # NEW: Retreat Logic - check before executing current behavior
        if self.can_retreat and self.player_ref and self.player_ref.alive:
            player_dist = hypot(self.x - self.player_ref.x, self.y - self.player_ref.y)
            if self.health <= self.retreat_health_threshold and player_dist < self.aggro_radius * 1.5:
                if not isinstance(self.behavior, RetreatBehavior):
                    self.set_behavior(RetreatBehavior(self))
                    logger.debug(f"Enemy {self.config.get('name')} (ID: {id(self)}) switching to RETREAT behavior.")
        
        # Execute current behavior
        if self.behavior:
            self.behavior.execute(maze, current_time_ms, delta_time_ms, game_area_x_offset)
        
        # Update sprite rotation and position
        from pygame.transform import rotate
        self.image = rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect.center = self.rect.center
        
        # Update bullets
        self.bullets.update(maze, game_area_x_offset)



    def shoot(self, direct_angle_to_target, maze): 
        if not self.alive: return
        from math import radians, cos, sin
        rad_fire_angle = radians(direct_angle_to_target) 
        tip_offset_distance = (self.rect.width / 2) if self.rect else (get_setting("gameplay", "TILE_SIZE", 80) * 0.35)
        
        fire_origin_x, fire_origin_y = self.x, self.y
        raw_fire_origin_x = self.x + cos(rad_fire_angle) * tip_offset_distance
        raw_fire_origin_y = self.y + sin(rad_fire_angle) * tip_offset_distance

        if maze and not maze.is_wall(raw_fire_origin_x, raw_fire_origin_y, self.enemy_bullet_size, self.enemy_bullet_size):
            fire_origin_x, fire_origin_y = raw_fire_origin_x, raw_fire_origin_y
        
        new_bullet = Bullet(
            x=fire_origin_x, y=fire_origin_y, angle=direct_angle_to_target, 
            speed=get_setting("enemies", "ENEMY_BULLET_SPEED", 5),
            lifetime=get_setting("enemies", "ENEMY_BULLET_LIFETIME", 75),
            size=self.enemy_bullet_size,
            color=get_setting("enemies", "ENEMY_BULLET_COLOR", (255,165,0)),
            damage=get_setting("enemies", "ENEMY_BULLET_DAMAGE", 10)
        )
        self.bullets.add(new_bullet)
        
        if self.shoot_sound_key and self.asset_manager:
            self.asset_manager.get_sound(self.shoot_sound_key).play()

    def take_damage(self, amount):
        if self.alive: 
            self.health -= amount
            # Create small hit effect
            if hasattr(self, 'rect') and self.rect:
                if random() < 0.3:  # 30% chance for spark on hit
                    x, y = self.rect.center
                    if hasattr(self.asset_manager, 'game_controller') and self.asset_manager.game_controller:
                        self.asset_manager.game_controller._create_explosion(x, y, 3, None)
            
            if self.health <= 0: 
                self.health = 0
                self.alive = False
                # Create explosion effect when enemy dies
                if hasattr(self.asset_manager, 'game_controller') and self.asset_manager.game_controller:
                        self.asset_manager.game_controller.on_enemy_defeated_effects(
                            type('EnemyDefeatedEvent', (object,), {'score_value': 0, 'position': (self.x, self.y), 'enemy_id': id(self)})()
                        )


    def draw(self, surface, camera=None):
        if self.alive and self.image:
            if camera:
                screen_rect = camera.apply_to_rect(self.rect)
                surface.blit(self.image, screen_rect)
            else: surface.blit(self.image, self.rect)
        for proj in self.bullets: proj.draw(surface, camera)

    def _draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect: return
        bar_w, bar_h = self.rect.width*0.8, 5
        screen_rect = camera.apply_to_rect(self.rect) if camera else self.rect
        bar_x, bar_y = screen_rect.centerx - bar_w/2, screen_rect.top - bar_h - 3
        fill_w = bar_w * (self.health / self.max_health if self.max_health > 0 else 0)
        fill_color = GREEN if self.health/self.max_health > 0.6 else YELLOW if self.health/self.max_health > 0.3 else RED
        from pygame.draw import rect as draw_rect
        draw_rect(surface, (80,0,0), (bar_x, bar_y, bar_w, bar_h))
        if fill_w > 0: draw_rect(surface, fill_color, (bar_x, bar_y, int(fill_w), bar_h)) 
        draw_rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1) 

class DefenseDrone(Enemy):
    def __init__(self, x, y, asset_manager, config, path_to_core=None):
        super().__init__(x, y, asset_manager, config)
        if path_to_core:
            self.pathfinder.path = path_to_core
            self.pathfinder.current_path_index = 1 if path_to_core and len(path_to_core) > 1 else -1

    def update(self, _, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=True):
        if not self.alive: return
        self.pathfinder.update_movement(maze, current_time_ms, delta_time_ms, game_area_x_offset)
        if self.image and self.original_image:
            from pygame.transform import rotate
            self.image = rotate(self.original_image, -self.angle)
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self.collision_rect: self.collision_rect.center = self.rect.center

class SentinelDrone(Enemy): 
    def __init__(self, x, y, asset_manager, config, target_player_ref=None):
        super().__init__(x, y, asset_manager, config, target_player_ref)
        # Set wall following behavior after a short delay to avoid circular import
        self._set_wall_follow_behavior()
        
        # Increase contact damage since this is the primary attack method
        self.contact_damage = get_setting("enemies", "SENTINEL_CONTACT_DAMAGE", 40)
        
        # Increase speed for better chase capability
        self.speed = get_setting("enemies", "SENTINEL_SPEED", 2.5)
        
        # Disable shooting by setting cooldown to infinity
        self.shoot_cooldown = float('inf')

    def _set_wall_follow_behavior(self):
        """Set wall following behavior after initialization to avoid circular import"""
        # Use a timer to delay behavior setting
        self._behavior_timer = get_ticks()
        self._behavior_set = False

    def update(self, primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=False):
        # Set wall following behavior if not already set
        if not getattr(self, '_behavior_set', False) and current_time_ms - getattr(self, '_behavior_timer', 0) > 100:
            from ai.behaviors import WallFollowBehavior
            self.default_behavior = WallFollowBehavior
            self.set_behavior(WallFollowBehavior(self))
            self._behavior_set = True
            
        # Call parent update method
        super().update(primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset, is_defense_mode)
    
    # Override shoot method to do nothing
    def shoot(self, direct_angle_to_target, maze):
        pass

    def _load_sprite(self): 
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        default_size = (int(tile_size * 0.6), int(tile_size * 0.6)) 
        self.original_image = self.asset_manager.get_image(self.sprite_asset_key, scale_to_size=default_size)
        if self.original_image is None:
            self.original_image = Surface(default_size, SRCALPHA)
            points = [(default_size[0]//2,0),(default_size[0],default_size[1]//2),(default_size[0]//2,default_size[1]),(0,default_size[1]//2)]
            polygon(self.original_image, DARK_PURPLE, points); polygon(self.original_image, WHITE, points, 1)
        self.image = self.original_image.copy(); self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        if self.rect: self.collision_rect = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)