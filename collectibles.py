# collectibles.py
import pygame
import os
import math
import random

# It's good practice for modules to import only what they need.
# game_settings is needed for POWERUP_TYPES, TILE_SIZE, etc.
from game_settings import (
    GOLD, PURPLE, POWERUP_TYPES, TILE_SIZE, POWERUP_SIZE,
    WEAPON_UPGRADE_ITEM_LIFETIME, POWERUP_ITEM_LIFETIME,
    CORE_FRAGMENT_VISUAL_SIZE,
    get_game_setting # If any collectible behavior depends on a dynamic game setting
)

class Collectible(pygame.sprite.Sprite):
    """Base class for collectible items with a pulsing shine effect."""
    def __init__(self, x, y, base_color, size, thickness=3, icon_surface=None):
        super().__init__()
        self.surface_size = int(size * 2.5) 
        self.image = pygame.Surface((self.surface_size, self.surface_size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.icon_surface = icon_surface
        self.collected = False
        self.expired = False 
        self.base_color = base_color
        self.current_color = base_color
        self.size = float(size) 
        self.thickness = thickness
        self.current_radius = float(self.size) 
        self.pulse_speed = 0.005 
        self.pulse_magnitude_radius = float(self.size * 0.15) 
        self.pulse_magnitude_alpha = 90 
        self.pulse_offset = random.uniform(0, 2 * math.pi) 
        self._render_to_image() 

    def _render_to_image(self):
        self.image.fill((0,0,0,0)) 
        surface_center_x = self.surface_size // 2
        surface_center_y = self.surface_size // 2
        pygame.draw.circle(self.image, self.current_color,
                           (surface_center_x, surface_center_y),
                           int(self.current_radius), self.thickness)
        if self.icon_surface:
            icon_rect = self.icon_surface.get_rect(center=(surface_center_x, surface_center_y))
            self.image.blit(self.icon_surface, icon_rect)

    def update_shine_and_render(self):
        time_ticks = pygame.time.get_ticks()
        pulse_wave = math.sin(time_ticks * self.pulse_speed + self.pulse_offset)
        alpha_change = (pulse_wave + 1) / 2 
        alpha = int(160 + alpha_change * self.pulse_magnitude_alpha) 
        alpha = max(100, min(255, alpha)) 
        self.current_radius = self.size + pulse_wave * self.pulse_magnitude_radius
        self.current_radius = max(self.size * 0.8, self.current_radius) 
        rgb_base = self.base_color[:3] if len(self.base_color) == 4 else self.base_color
        self.current_color = (*rgb_base, alpha)
        self._render_to_image()

    def base_update(self, item_lifetime_constant): 
        if self.collected or self.expired:
            return True 
        current_time = pygame.time.get_ticks()
        if hasattr(self, 'creation_time') and current_time - self.creation_time > item_lifetime_constant:
            self.expired = True
            return True
        self.update_shine_and_render()
        return False

class Ring(Collectible):
    def __init__(self, x, y):
        super().__init__(x, y, base_color=GOLD, size=TILE_SIZE // 4, thickness=3, icon_surface=None)
    def update(self):
        if self.collected:
            return True 
        self.update_shine_and_render()
        return False

class WeaponUpgradeItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type = "weapon_upgrade"
        # POWERUP_TYPES should be imported or passed if this class needs it directly
        details = POWERUP_TYPES.get(self.powerup_type, {"color": (0,0,255), "image_filename": None}) # Default if not found
        loaded_icon = None
        if "image_filename" in details and details["image_filename"]:
            try:
                image_path = os.path.join("assets", "images", "powerups", details["image_filename"])
                if os.path.exists(image_path):
                    raw_icon = pygame.image.load(image_path).convert_alpha()
                    icon_display_size = int(POWERUP_SIZE * 1.5) 
                    loaded_icon = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
                else:
                    print(f"Warning: WeaponUpgradeItem icon not found: {image_path}")
            except pygame.error as e:
                print(f"Error loading icon for {self.powerup_type} ('{details.get('image_filename')}'): {e}")
        super().__init__(x, y, base_color=details["color"], size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon)
        self.creation_time = pygame.time.get_ticks()

    def update(self):
        if self.base_update(WEAPON_UPGRADE_ITEM_LIFETIME): 
            self.kill() 

    def apply_effect(self, player): # Player object passed from game logic
        if hasattr(player, 'cycle_weapon_state'):
            player.cycle_weapon_state(force_cycle=True)

class ShieldItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type = "shield"
        details = POWERUP_TYPES.get(self.powerup_type, {"color": (173,216,230), "image_filename": None, "duration": 30000})
        loaded_icon = None
        if "image_filename" in details and details["image_filename"]:
            try:
                image_path = os.path.join("assets", "images", "powerups", details["image_filename"])
                if os.path.exists(image_path):
                    raw_icon = pygame.image.load(image_path).convert_alpha()
                    icon_display_size = int(POWERUP_SIZE * 1.5)
                    loaded_icon = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
                else:
                    print(f"Warning: ShieldItem icon not found: {image_path}")
            except pygame.error as e:
                print(f"Error loading icon for {self.powerup_type} ('{details.get('image_filename')}'): {e}")
        super().__init__(x, y, base_color=details["color"], size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration = details["duration"] # Use duration from details

    def update(self):
        if self.base_update(POWERUP_ITEM_LIFETIME):
            self.kill()

    def apply_effect(self, player):
        if hasattr(player, 'activate_shield'):
            player.activate_shield(self.effect_duration)

class SpeedBoostItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type = "speed_boost"
        details = POWERUP_TYPES.get(self.powerup_type, {"color": (0,255,0), "image_filename": None, "duration": 10000, "multiplier": 1.5})
        loaded_icon = None
        if "image_filename" in details and details["image_filename"]:
            try:
                image_path = os.path.join("assets", "images", "powerups", details["image_filename"])
                if os.path.exists(image_path):
                    raw_icon = pygame.image.load(image_path).convert_alpha()
                    icon_display_size = int(POWERUP_SIZE * 1.5)
                    loaded_icon = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
                else:
                    print(f"Warning: SpeedBoostItem icon not found: {image_path}")
            except pygame.error as e:
                print(f"Error loading icon for {self.powerup_type} ('{details.get('image_filename')}'): {e}")
        super().__init__(x, y, base_color=details["color"], size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration = details["duration"]
        self.multiplier = details["multiplier"]

    def update(self):
        if self.base_update(POWERUP_ITEM_LIFETIME):
            self.kill()

    def apply_effect(self, player):
        if hasattr(player, 'arm_speed_boost'):
            player.arm_speed_boost(self.effect_duration, self.multiplier)


class CoreFragmentItem(Collectible):
    def __init__(self, x, y, fragment_id, fragment_config): # fragment_config passed in
        self.fragment_id = fragment_id
        self.fragment_name = fragment_config.get("name", "Core Fragment")
        self.description = fragment_config.get("description", "") 
        base_color = PURPLE 
        icon_surface = None
        icon_filename = fragment_config.get("icon_filename")
        if icon_filename:
            try:
                primary_path = os.path.join("assets", "images", "collectibles", icon_filename)
                alt_path = os.path.join("assets", "drones", icon_filename) 
                image_path_to_load = None
                if os.path.exists(primary_path): image_path_to_load = primary_path
                elif os.path.exists(alt_path): image_path_to_load = alt_path

                if image_path_to_load:
                    raw_icon = pygame.image.load(image_path_to_load).convert_alpha()
                    icon_display_size = int(CORE_FRAGMENT_VISUAL_SIZE * 0.8) 
                    icon_surface = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
                else: print(f"CoreFragment icon not found: {icon_filename}")
            except pygame.error as e: print(f"Error loading icon for CF '{self.fragment_name}': {e}")
        
        super().__init__(x, y, base_color=base_color, size=CORE_FRAGMENT_VISUAL_SIZE, thickness=3, icon_surface=icon_surface)
        self.creation_time = pygame.time.get_ticks() 

    def update(self):
        if self.collected: return True 
        self.update_shine_and_render()
        return False 

    def apply_effect(self, player, game_instance): # Game instance for drone_system
        if not self.collected:
            # Access drone_system via game_instance
            if hasattr(game_instance, 'drone_system') and \
               hasattr(game_instance.drone_system, 'collect_core_fragment'):
                if game_instance.drone_system.collect_core_fragment(self.fragment_id):
                    self.collected = True
                    return True
            else:
                print("Error: game_instance or drone_system not properly configured for CoreFragmentItem.")
        return False
