import pygame
import os
import math
import random

# Import necessary constants from game_settings.py
try:
    from game_settings import (
        GOLD, PURPLE, BLUE, LIGHT_BLUE, GREEN, # Colors
        POWERUP_TYPES, TILE_SIZE, POWERUP_SIZE, CORE_FRAGMENT_VISUAL_SIZE, # Sizes and type definitions
        WEAPON_UPGRADE_ITEM_LIFETIME, POWERUP_ITEM_LIFETIME, # Lifetimes
        # get_game_setting might be needed if some behaviors are dynamic, but usually not for collectibles
    )
except ImportError:
    print("Warning (collectibles.py): Could not import all constants from game_settings. Using fallbacks.")
    # Fallback values
    GOLD = (255, 215, 0)
    PURPLE = (128, 0, 128)
    BLUE = (0, 0, 255)
    LIGHT_BLUE = (173, 216, 230)
    GREEN = (0, 255, 0)
    POWERUP_TYPES = { # Minimal fallback
        "shield": {"color": LIGHT_BLUE, "image_filename": "shield_icon.png", "duration": 10000},
        "speed_boost": {"color": GREEN, "image_filename": "speed_icon.png", "duration": 7000, "multiplier": 1.5},
        "weapon_upgrade": {"color": BLUE, "image_filename": "weapon_icon.png"}
    }
    TILE_SIZE = 80
    POWERUP_SIZE = TILE_SIZE // 3
    CORE_FRAGMENT_VISUAL_SIZE = TILE_SIZE // 2.5
    WEAPON_UPGRADE_ITEM_LIFETIME = 15000
    POWERUP_ITEM_LIFETIME = 12000


class Collectible(pygame.sprite.Sprite):
    """Base class for collectible items with a pulsing shine effect."""
    def __init__(self, x, y, base_color, size, thickness=3, icon_surface=None):
        super().__init__()
        # The main surface for the collectible, made larger to accommodate pulsing effect
        self.surface_size = int(size * 1.5) # Adjusted for better visual of pulse
        self.image = pygame.Surface((self.surface_size, self.surface_size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        
        self.icon_surface = icon_surface # Pre-rendered icon (e.g., shield, speed boost)
        self.collected = False # Flag to mark if collected
        self.expired = False   # Flag for timed items if they expire

        self.base_color = base_color       # The core color of the collectible's pulse
        self.current_color = base_color    # Color used for drawing, might include alpha
        self.base_draw_radius = float(size) # The standard drawing radius of the collectible
        self.thickness = thickness         # Thickness of the circle outline for pulse

        # Pulse effect parameters
        self.current_pulse_radius = self.base_draw_radius
        self.pulse_speed_factor = 0.005  # How fast the pulse animates
        self.pulse_radius_amplitude = self.base_draw_radius * 0.20 # How much the radius changes
        self.pulse_alpha_amplitude = 90   # How much the alpha changes
        self.pulse_time_offset = random.uniform(0, 2 * math.pi) # Randomize start of pulse

        self._render_to_image() # Initial render

    def _render_to_image(self):
        """Renders the collectible (pulse and icon) to its self.image surface."""
        self.image.fill((0, 0, 0, 0)) # Clear the surface (transparent)
        
        surface_center_x = self.surface_size // 2
        surface_center_y = self.surface_size // 2

        # Draw the pulsing circle
        pygame.draw.circle(self.image, self.current_color,
                           (surface_center_x, surface_center_y),
                           int(self.current_pulse_radius), self.thickness)
        
        # Blit the icon on top if it exists
        if self.icon_surface:
            icon_rect = self.icon_surface.get_rect(center=(surface_center_x, surface_center_y))
            self.image.blit(self.icon_surface, icon_rect)

    def _update_pulse_effect(self):
        """Updates the parameters for the pulsing shine effect."""
        time_ticks = pygame.time.get_ticks()
        # Sin wave for smooth pulsing: ranges from -1 to 1
        pulse_wave = math.sin(time_ticks * self.pulse_speed_factor + self.pulse_time_offset)

        # Update radius based on pulse
        self.current_pulse_radius = self.base_draw_radius + pulse_wave * self.pulse_radius_amplitude
        self.current_pulse_radius = max(self.base_draw_radius * 0.7, self.current_pulse_radius) # Ensure min radius

        # Update alpha for the color
        # (pulse_wave + 1) / 2 maps -1..1 to 0..1
        alpha_normalized = (pulse_wave + 1) / 2
        # Base alpha (e.g., 160) + variation (e.g., 0-90)
        alpha = int(160 + alpha_normalized * self.pulse_alpha_amplitude)
        alpha = max(100, min(255, alpha)) # Clamp alpha

        # Update current drawing color with new alpha
        rgb_base = self.base_color[:3] if len(self.base_color) == 4 else self.base_color
        self.current_color = (*rgb_base, alpha)

    def update_collectible_state(self, item_lifetime_ms=None):
        """
        Base update logic for collectibles. Handles expiration and calls pulse effect.
        Returns True if the item should be removed (collected or expired), False otherwise.
        """
        if self.collected or self.expired:
            return True # Already processed, should be removed

        # Handle expiration for timed items
        if item_lifetime_ms is not None:
            current_time = pygame.time.get_ticks()
            if not hasattr(self, 'creation_time'): # Initialize if not set
                self.creation_time = current_time
            if current_time - self.creation_time > item_lifetime_ms:
                self.expired = True
                return True # Expired, should be removed
        
        self._update_pulse_effect()
        self._render_to_image() # Re-render with new pulse state
        return False # Still active

    def update(self):
        """
        Generic update method. Subclasses should override this to call
        update_collectible_state with their specific lifetime or just update visuals.
        """
        # Default behavior: just update visuals if not timed
        if self.update_collectible_state(): # Pass None for lifetime if not timed by default
            self.kill() # Remove from sprite groups if collected/expired
            return True
        return False


class Ring(Collectible):
    """Represents a collectible ring."""
    def __init__(self, x, y):
        # Rings don't have a specific icon surface, just the pulsing circle.
        # Size is typically smaller than power-ups.
        ring_size = TILE_SIZE // 4 
        super().__init__(x, y, base_color=GOLD, size=ring_size, thickness=3, icon_surface=None)
        # Rings typically don't expire on their own, only when collected.

    def update(self):
        """Rings only update their visual pulse unless collected."""
        if self.collected: # If marked as collected by game logic
            self.kill()
            return True
        # Call base update_collectible_state without a lifetime, so it only updates visuals
        self.update_collectible_state(item_lifetime_ms=None)
        return False


class WeaponUpgradeItem(Collectible):
    """Represents a weapon upgrade power-up."""
    def __init__(self, x, y):
        self.powerup_type_key = "weapon_upgrade"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", BLUE) # Fallback color
        icon_filename = details.get("image_filename")
        loaded_icon_surface = self._load_icon(icon_filename, POWERUP_SIZE * 0.9) # Slightly smaller icon

        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon_surface)
        self.creation_time = pygame.time.get_ticks() # For expiration

    def _load_icon(self, filename, icon_render_size):
        if not filename: return None
        try:
            # Standardized path for power-up icons
            image_path = os.path.join("assets", "images", "powerups", filename)
            if os.path.exists(image_path):
                raw_icon = pygame.image.load(image_path).convert_alpha()
                return pygame.transform.smoothscale(raw_icon, (int(icon_render_size), int(icon_render_size)))
            else:
                print(f"Warning: Icon not found for {self.powerup_type_key}: {image_path}")
        except pygame.error as e:
            print(f"Error loading icon for {self.powerup_type_key} ('{filename}'): {e}")
        return None # Fallback if loading fails

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=WEAPON_UPGRADE_ITEM_LIFETIME):
            self.kill() # Remove from sprite groups if collected/expired
            return True
        return False

    def apply_effect(self, player_drone):
        """Applies the weapon upgrade effect to the player drone."""
        if hasattr(player_drone, 'cycle_weapon_state'):
            player_drone.cycle_weapon_state(force_cycle=True) # True to ensure it cycles
            print("Weapon Upgrade collected!")


class ShieldItem(Collectible):
    """Represents a shield power-up."""
    def __init__(self, x, y):
        self.powerup_type_key = "shield"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", LIGHT_BLUE)
        icon_filename = details.get("image_filename")
        loaded_icon_surface = self._load_icon(icon_filename, POWERUP_SIZE * 0.9)
        
        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon_surface)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration_ms = details.get("duration", 10000) # Default 10s

    _load_icon = WeaponUpgradeItem._load_icon # Reuse icon loading logic

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=POWERUP_ITEM_LIFETIME):
            self.kill()
            return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'activate_shield'):
            player_drone.activate_shield(self.effect_duration_ms)
            print("Shield collected!")


class SpeedBoostItem(Collectible):
    """Represents a speed boost power-up."""
    def __init__(self, x, y):
        self.powerup_type_key = "speed_boost"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", GREEN)
        icon_filename = details.get("image_filename")
        loaded_icon_surface = self._load_icon(icon_filename, POWERUP_SIZE * 0.9)

        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon_surface)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration_ms = details.get("duration", 7000) # Default 7s
        self.speed_multiplier = details.get("multiplier", 1.5) # Default 1.5x speed

    _load_icon = WeaponUpgradeItem._load_icon # Reuse icon loading logic

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=POWERUP_ITEM_LIFETIME):
            self.kill()
            return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'arm_speed_boost'): # Player arms it, activates on movement
            player_drone.arm_speed_boost(self.effect_duration_ms, self.speed_multiplier)
            print("Speed Boost collected!")


class CoreFragmentItem(Collectible):
    """Represents a collectible Core Fragment."""
    def __init__(self, x, y, fragment_id, fragment_config_details):
        self.fragment_id = fragment_id
        self.fragment_name = fragment_config_details.get("name", "Core Fragment")
        # self.description = fragment_config_details.get("description", "") # Not used directly in this class

        item_color = fragment_config_details.get("display_color", PURPLE) # Allow custom color from config
        icon_filename = fragment_config_details.get("icon_filename")
        loaded_icon_surface = self._load_icon(icon_filename, CORE_FRAGMENT_VISUAL_SIZE * 0.8) # Icon slightly smaller than pulse

        super().__init__(x, y, base_color=item_color, size=CORE_FRAGMENT_VISUAL_SIZE, thickness=3, icon_surface=loaded_icon_surface)
        # Core fragments typically don't expire on their own.
        # self.creation_time = pygame.time.get_ticks() # Not needed if no expiration

    def _load_icon(self, filename, icon_render_size): # Specific loader for fragments
        if not filename: return None
        try:
            # Fragments might have icons in a different subfolder or same as powerups
            # Assuming a "collectibles" subfolder for fragment icons for organization
            image_path_primary = os.path.join("assets", "images", "collectibles", filename)
            image_path_alt = os.path.join("assets", "images", "powerups", filename) # Fallback path
            
            actual_path = None
            if os.path.exists(image_path_primary):
                actual_path = image_path_primary
            elif os.path.exists(image_path_alt):
                actual_path = image_path_alt
            else:
                print(f"Warning: Icon not found for Core Fragment '{self.fragment_name}': {filename}")
                return None

            raw_icon = pygame.image.load(actual_path).convert_alpha()
            return pygame.transform.smoothscale(raw_icon, (int(icon_render_size), int(icon_render_size)))
        except pygame.error as e:
            print(f"Error loading icon for Core Fragment '{self.fragment_name}' ('{filename}'): {e}")
        return None

    def update(self):
        """Core Fragments only update their visual pulse unless collected."""
        if self.collected: # If marked as collected by game logic
            self.kill()
            return True
        self.update_collectible_state(item_lifetime_ms=None) # No expiration
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        """
        Applies the effect of collecting the fragment.
        This usually means notifying the DroneSystem via the game_controller.
        """
        if not self.collected:
            if hasattr(game_controller_instance, 'drone_system') and \
               hasattr(game_controller_instance.drone_system, 'collect_core_fragment'):
                if game_controller_instance.drone_system.collect_core_fragment(self.fragment_id):
                    self.collected = True # Mark as collected internally
                    print(f"Core Fragment '{self.fragment_name}' collected by player!")
                    # Buffs from fragments are typically applied by DroneSystem when calculating effective stats
                    return True # Successfully collected and processed
            else:
                print(f"Error: Could not notify DroneSystem about collecting Core Fragment '{self.fragment_name}'.")
        return False # Already collected or system error

