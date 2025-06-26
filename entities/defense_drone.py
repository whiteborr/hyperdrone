# entities/defense_drone.py
from pygame.sprite import Sprite
from pygame import Surface, SRCALPHA
from pygame.transform import rotate
from pygame.draw import rect as draw_rect
from logging import getLogger

from settings_manager import get_setting
from constants import GREEN, YELLOW, RED, WHITE

logger = getLogger(__name__)

class DefenseDrone(Sprite):
    def __init__(self, x, y, asset_manager, config, path_to_core=None, **kwargs):
        super().__init__()
        self.x, self.y = float(x), float(y)
        self.asset_manager = asset_manager
        
        # Extract sprite key from config - ensure it's a string
        assets = config.get("assets", {})
        self.sprite_asset_key = str(assets.get("sprite_asset_key", "defense_drone_sprite"))
        
        # Initialize pathfinder
        from ai.pathfinding_component import PathfinderComponent
        self.pathfinder = PathfinderComponent(self)
        
        # Set path if provided
        if path_to_core:
            self.pathfinder.path = path_to_core
            self.pathfinder.current_path_index = 1 if path_to_core and len(path_to_core) > 1 else -1
        
        self.angle = 0
        
        # Get stats from config
        stats = config.get("stats", {})
        self.speed = stats.get("speed", 1.5)
        self.health = stats.get("health", 100)
        self.max_health = self.health
        self.contact_damage = stats.get("contact_damage", 25)
        self.alive = True
        self._load_sprite()

    def _load_sprite(self):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        default_size = (int(tile_size * 0.7), int(tile_size * 0.7))
        self.original_image = self.asset_manager.get_image(self.sprite_asset_key, scale_to_size=default_size)
        if self.original_image is None:
            logger.warning(f"DefenseDrone: Could not load sprite with key '{self.sprite_asset_key}'")
            self.original_image = Surface(default_size, SRCALPHA)
            self.original_image.fill((255, 0, 0, 180))
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)

    def update(self, _, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=True):
        if not self.alive:
            return
        
        self.pathfinder.update_movement(maze, current_time_ms, delta_time_ms, game_area_x_offset)
        
        if self.image and self.original_image:
            self.image = rotate(self.original_image, -self.angle)
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self.collision_rect:
                self.collision_rect.center = self.rect.center

    def take_damage(self, amount):
        if self.alive:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False
                # Create explosion effect when enemy dies
                if hasattr(self.asset_manager, 'game_controller') and self.asset_manager.game_controller:
                    x, y = self.rect.center
                    self.asset_manager.game_controller._create_enemy_explosion(x, y)

    def draw(self, surface, camera=None):
        if not self.alive or not self.image:
            return
            
        # Always use direct drawing without camera
        surface.blit(self.image, self.rect)
            
        # Draw health bar
        if self.alive:
            self._draw_health_bar(surface, None)

    def _draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect:
            return
            
        bar_w, bar_h = self.rect.width * 0.8, 5
        
        # Always use direct rect without camera
        screen_rect = self.rect
            
        bar_x = screen_rect.centerx - bar_w / 2
        bar_y = screen_rect.top - bar_h - 3
        
        fill_w = bar_w * (self.health / self.max_health if self.max_health > 0 else 0)
        
        if self.health / self.max_health > 0.6:
            fill_color = GREEN
        elif self.health / self.max_health > 0.3:
            fill_color = YELLOW
        else:
            fill_color = RED
            
        draw_rect(surface, (80, 0, 0), (bar_x, bar_y, bar_w, bar_h))
        
        if fill_w > 0:
            draw_rect(surface, fill_color, (bar_x, bar_y, int(fill_w), bar_h))
            
        draw_rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)
