# entities/collectibles.py
import os
import math
import random

import pygame

import game_settings as gs # Assuming game_settings.py is accessible
from game_settings import (
    GOLD, PURPLE, BLUE, LIGHT_BLUE, GREEN, DARK_PURPLE, CYAN, WHITE, # Added WHITE
    POWERUP_TYPES, TILE_SIZE, POWERUP_SIZE, CORE_FRAGMENT_VISUAL_SIZE,
    WEAPON_UPGRADE_ITEM_LIFETIME, POWERUP_ITEM_LIFETIME,
    ARCHITECT_VAULT_WALL_COLOR # For terminal fallback
)

class Collectible(pygame.sprite.Sprite):
    """Base class for collectible items with a pulsing shine effect, bobbing, and icon spin."""
    def __init__(self, x, y, base_color, size, thickness=3, original_icon_surface=None, is_rectangular=False):
        super().__init__()
        self.center_x = float(x)
        self.center_y = float(y)

        self.base_draw_radius = float(size) if not is_rectangular else float(max(size))
        self.item_size = size
        self.is_rectangular = is_rectangular
        self.thickness = thickness
        self.pulse_radius_amplitude = self.base_draw_radius * 0.25

        max_main_pulse_dim = self.base_draw_radius + self.pulse_radius_amplitude
        max_secondary_pulse_dim = max_main_pulse_dim * 1.15
        required_diameter = (max_secondary_pulse_dim * 2) + self.thickness
        self.surface_size = int(math.ceil(required_diameter)) + 4
        
        min_practical_size_calc = self.base_draw_radius * 2 if not is_rectangular else max(self.item_size)
        min_practical_size = int(math.ceil(min_practical_size_calc) + self.thickness + 4)
        self.surface_size = max(self.surface_size, min_practical_size, 32)
        
        self.image = pygame.Surface((self.surface_size, self.surface_size), pygame.SRCALPHA)
        
        self.original_icon_surface = original_icon_surface
        self.icon_surface = original_icon_surface # This will be the surface actually blitted
        
        self.collected = False
        self.expired = False  

        self.base_color = base_color
        
        self.current_pulse_radius = self.base_draw_radius
        self.pulse_speed_factor = 0.005 
        self.pulse_alpha_amplitude = 100  
        self.pulse_time_offset = random.uniform(0, 2 * math.pi)

        self.bob_speed = 0.003
        self.bob_amplitude = 4
        self.bob_time_offset = random.uniform(0, 2 * math.pi)
        self.current_y_offset = 0

        self.icon_angle = 0
        self.icon_rotation_speed = 0.3 if original_icon_surface else 0 # Only rotate if there's an original image icon

        self._update_pulse_effect()
        self.rect = self.image.get_rect(center=(self.center_x, self.center_y))
        self._update_bob_effect()
        self._render_to_image()

    def _update_pulse_effect(self):
        time_ticks = pygame.time.get_ticks()
        pulse_wave = math.sin(time_ticks * self.pulse_speed_factor + self.pulse_time_offset)

        self.current_pulse_radius = self.base_draw_radius + pulse_wave * self.pulse_radius_amplitude
        self.current_pulse_radius = max(self.base_draw_radius * 0.65, self.current_pulse_radius)

        alpha_normalized = (pulse_wave + 1) / 2
        alpha = int(150 + alpha_normalized * self.pulse_alpha_amplitude)
        alpha = max(100, min(255, alpha))

        lerp_factor_color = (pulse_wave + 1) / 2
        
        if len(self.base_color) == 4:
            r_base, g_base, b_base, _ = self.base_color
        else:
            r_base, g_base, b_base = self.base_color
        
        brightness_increase = 35
        r_bright = min(255, r_base + brightness_increase)
        g_bright = min(255, g_base + brightness_increase)
        b_bright = min(255, b_base + brightness_increase)
        
        r_pulsed = int(r_base + (r_bright - r_base) * lerp_factor_color)
        g_pulsed = int(g_base + (g_bright - g_base) * lerp_factor_color)
        b_pulsed = int(b_base + (b_bright - b_base) * lerp_factor_color)
        
        self.current_color = (r_pulsed, g_pulsed, b_pulsed, alpha)

    def _update_bob_effect(self):
        time_ticks = pygame.time.get_ticks()
        self.current_y_offset = math.sin(time_ticks * self.bob_speed + self.bob_time_offset) * self.bob_amplitude
        if hasattr(self, 'rect') and self.rect is not None:
            self.rect.centery = int(self.center_y + self.current_y_offset)
            self.rect.centerx = int(self.center_x)

    def _render_to_image(self):
        self.image.fill((0, 0, 0, 0))
        
        surface_center_x = self.surface_size // 2
        surface_center_y = self.surface_size // 2

        if not self.is_rectangular:
            pygame.draw.circle(self.image, self.current_color,
                               (surface_center_x, surface_center_y),
                               int(self.current_pulse_radius), self.thickness)
            
            if self.current_pulse_radius > self.base_draw_radius * 0.8:
                secondary_radius_factor = 1.15
                secondary_radius = int(self.current_pulse_radius * secondary_radius_factor)
                current_alpha_component = self.current_color[3] if len(self.current_color) == 4 else 255
                
                denominator = self.pulse_radius_amplitude * 1.2
                if denominator == 0:
                    normalized_expansion = 1.0
                else:
                    normalized_expansion = (self.current_pulse_radius - self.base_draw_radius * 0.8) / denominator
                normalized_expansion = max(0, min(1, normalized_expansion))

                secondary_alpha = int(current_alpha_component * 0.4 * normalized_expansion)
                secondary_alpha = max(0, min(255, secondary_alpha))

                if secondary_alpha > 20 :
                    secondary_color = (*self.current_color[:3], secondary_alpha)
                    pygame.draw.circle(self.image, secondary_color,
                                       (surface_center_x, surface_center_y),
                                       secondary_radius, max(1, self.thickness // 2))
        else: # Rectangular collectible (like VaultLogItem or GlyphTabletItem)
            rect_width, rect_height = self.item_size
            pulse_factor = (math.sin(pygame.time.get_ticks() * self.pulse_speed_factor + self.pulse_time_offset) + 1) / 2
            # Rectangular items might not need to visually pulse in size, or only slightly
            current_width = rect_width # + pulse_factor * (self.pulse_radius_amplitude * 0.2 * (rect_width / self.base_draw_radius)) if self.base_draw_radius > 0 else rect_width
            current_height = rect_height # + pulse_factor * (self.pulse_radius_amplitude * 0.2 * (rect_height / self.base_draw_radius)) if self.base_draw_radius > 0 else rect_height
            
            temp_rect = pygame.Rect(0,0, int(current_width), int(current_height))
            temp_rect.center = (surface_center_x, surface_center_y)
            pygame.draw.rect(self.image, self.current_color, temp_rect, self.thickness, border_radius=3)

        # Blit the icon_surface (which could be an image or a rendered emoji)
        if self.icon_surface:
            if self.original_icon_surface and self.icon_rotation_speed > 0: # Only rotate if it's an image-based icon meant to rotate
                self.icon_angle = (self.icon_angle + self.icon_rotation_speed) % 360
                rotated_icon_surface = pygame.transform.rotate(self.original_icon_surface, self.icon_angle)
                icon_rect = rotated_icon_surface.get_rect(center=(surface_center_x, surface_center_y))
                self.image.blit(rotated_icon_surface, icon_rect)
            else: # For non-rotating icons (like rendered text/emoji)
                icon_rect = self.icon_surface.get_rect(center=(surface_center_x, surface_center_y))
                self.image.blit(self.icon_surface, icon_rect)


    def update_collectible_state(self, item_lifetime_ms=None):
        if self.collected or self.expired:
            return True

        if item_lifetime_ms is not None:
            current_time = pygame.time.get_ticks()
            if not hasattr(self, 'creation_time'):
                self.creation_time = current_time
            if current_time - self.creation_time > item_lifetime_ms:
                self.expired = True
                return True
        
        self._update_pulse_effect()
        self._update_bob_effect()
        self._render_to_image()
        
        return False

    def update(self):
        if self.update_collectible_state():
            self.kill()
            return True
        return False


class Ring(Collectible):
    def __init__(self, x, y):
        ring_size = TILE_SIZE // 4
        super().__init__(x, y, base_color=GOLD, size=ring_size, thickness=3)

    def update(self):
        if self.collected:
            self.kill()
            return True
        self.update_collectible_state(item_lifetime_ms=None)
        return False


class WeaponUpgradeItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type_key = "weapon_upgrade"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", BLUE)
        icon_filename = details.get("image_filename")
        loaded_original_icon = self._load_icon(icon_filename, POWERUP_SIZE * 0.9)

        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = pygame.time.get_ticks()

    def _load_icon(self, filename, icon_render_size):
        if not filename: return None
        try:
            image_path = os.path.join("assets", "images", "powerups", filename)
            if os.path.exists(image_path):
                raw_icon = pygame.image.load(image_path).convert_alpha()
                return pygame.transform.smoothscale(raw_icon, (int(icon_render_size), int(icon_render_size)))
            else:
                print(f"Warning: Icon not found for {getattr(self, 'powerup_type_key', 'collectible')}: {image_path}")
        except pygame.error as e:
            print(f"Error loading icon for {getattr(self, 'powerup_type_key', 'collectible')} ('{filename}'): {e}")
        return None

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=WEAPON_UPGRADE_ITEM_LIFETIME):
            self.kill()
            return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'cycle_weapon_state'):
            player_drone.cycle_weapon_state(force_cycle=True)
            print("Weapon Upgrade collected!")


class ShieldItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type_key = "shield"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", LIGHT_BLUE)
        icon_filename = details.get("image_filename")
        loaded_original_icon = self._load_icon(icon_filename, POWERUP_SIZE * 0.9)
        
        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration_ms = details.get("duration", 10000)

    _load_icon = WeaponUpgradeItem._load_icon

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
    def __init__(self, x, y):
        self.powerup_type_key = "speed_boost"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", GREEN)
        icon_filename = details.get("image_filename")
        loaded_original_icon = self._load_icon(icon_filename, POWERUP_SIZE * 0.9)

        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration_ms = details.get("duration", 7000)
        self.speed_multiplier = details.get("multiplier", 1.5)

    _load_icon = WeaponUpgradeItem._load_icon

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=POWERUP_ITEM_LIFETIME):
            self.kill()
            return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'arm_speed_boost'):
            player_drone.arm_speed_boost(self.effect_duration_ms, self.speed_multiplier)
            print("Speed Boost collected!")


class CoreFragmentItem(Collectible):
    def __init__(self, x, y, fragment_id, fragment_config_details):
        self.fragment_id = fragment_id
        self.fragment_name = fragment_config_details.get("name", "Core Fragment")

        item_color = fragment_config_details.get("display_color", PURPLE)
        icon_filename = fragment_config_details.get("icon_filename")
        loaded_original_icon = self._load_icon(icon_filename, CORE_FRAGMENT_VISUAL_SIZE * 0.8)

        super().__init__(x, y, base_color=item_color, size=CORE_FRAGMENT_VISUAL_SIZE, thickness=3, original_icon_surface=loaded_original_icon)

    def _load_icon(self, filename, icon_render_size):
        if not filename: return None
        try:
            image_path_primary = os.path.join("assets", "images", "collectibles", filename)
            image_path_alt = os.path.join("assets", "images", "powerups", filename)
            
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
        if self.collected:
            self.kill()
            return True
        self.update_collectible_state(item_lifetime_ms=None)
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            if hasattr(game_controller_instance, 'drone_system') and \
               hasattr(game_controller_instance.drone_system, 'collect_core_fragment'):
                if game_controller_instance.drone_system.collect_core_fragment(self.fragment_id):
                    self.collected = True
                    print(f"Core Fragment '{self.fragment_name}' collected by player!")
                    return True
            else:
                print(f"Error: Could not notify DroneSystem about collecting Core Fragment '{self.fragment_name}'.")
        return False

class VaultLogItem(Collectible):
    """Represents a collectible Vault Log that unlocks lore."""
    def __init__(self, x, y, log_id, icon_filename=None): # Added icon_filename parameter
        self.log_id = log_id
        item_size_tuple = (TILE_SIZE * 0.4, TILE_SIZE * 0.5)
        self.icon_font_key = "ui_emoji_general" # Font key for emoji
        self.default_icon_char = "📝" # Memo emoji as default

        loaded_icon_surface = None
        if icon_filename: # If an image filename is provided, try to load it
            try:
                image_path = os.path.join("assets", "images", "collectibles", icon_filename)
                if os.path.exists(image_path):
                    raw_icon = pygame.image.load(image_path).convert_alpha()
                    icon_render_w = int(item_size_tuple[0] * 0.8)
                    icon_render_h = int(item_size_tuple[1] * 0.8)
                    loaded_icon_surface = pygame.transform.smoothscale(raw_icon, (icon_render_w, icon_render_h))
                else:
                    print(f"Warning: Icon not found for VaultLogItem: {image_path}")
            except pygame.error as e:
                print(f"Error loading icon for VaultLogItem ('{icon_filename}'): {e}")
        
        # Call super with the loaded image icon (if any)
        super().__init__(x, y, base_color=DARK_PURPLE, size=item_size_tuple, thickness=2,
                         original_icon_surface=loaded_icon_surface, # This is for image-based icons
                         is_rectangular=True)

        # If no image icon was loaded, create a text/emoji based one
        if loaded_icon_surface is None:
            # Attempt to get the font from game_settings (passed via UIManager or GameController)
            # This part requires access to the fonts dictionary, which is usually in UIManager.
            # For simplicity here, we'll assume a fallback if fonts aren't directly accessible.
            # In a real scenario, you'd pass the font object or a font rendering function.
            try:
                # This is a conceptual access. In practice, you'd need to pass the font object.
                # For now, we'll create a temporary font if not available.
                font_obj = pygame.font.Font(gs.UI_FONT_PATH_EMOJI, int(item_size_tuple[1] * 0.6)) # Example access
            except: # Fallback if font path is not directly in gs or not loaded
                font_obj = pygame.font.Font(None, int(item_size_tuple[1] * 0.6))

            text_surf = font_obj.render(self.default_icon_char, True, gs.CYAN) # Use CYAN for visibility
            self.icon_surface = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
            self.icon_surface.blit(text_surf, (0,0))
            self.original_icon_surface = None # Ensure this is None if we are using rendered text/emoji
        
        self.icon_rotation_speed = 0 # Text/emoji icons usually don't rotate

    def update(self):
        if self.collected:
            self.kill()
            return True
        self.update_collectible_state(item_lifetime_ms=None)
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            print(f"Vault Log '{self.log_id}' collected by player!")
            return True
        return False

class GlyphTabletItem(Collectible):
    """Represents a collectible Architect Glyph Tablet."""
    def __init__(self, x, y, tablet_id, icon_filename=None):
        self.tablet_id = tablet_id
        self.item_name = f"Glyph Tablet ({tablet_id.capitalize()})"
        item_size_tuple = (TILE_SIZE * 0.45, TILE_SIZE * 0.35)

        loaded_icon = None
        if icon_filename:
            try:
                image_path = os.path.join("assets", "images", "collectibles", icon_filename)
                if os.path.exists(image_path):
                    raw_icon = pygame.image.load(image_path).convert_alpha()
                    icon_render_w = int(item_size_tuple[0] * 0.8)
                    icon_render_h = int(item_size_tuple[1] * 0.8)
                    loaded_icon = pygame.transform.smoothscale(raw_icon, (icon_render_w, icon_render_h))
                else:
                    print(f"Warning: Icon not found for GlyphTabletItem: {image_path}")
            except pygame.error as e:
                print(f"Error loading icon for GlyphTabletItem ('{icon_filename}'): {e}")

        if loaded_icon is None:
            glyph_char = "?"
            if tablet_id == "alpha": glyph_char = "α"
            elif tablet_id == "beta": glyph_char = "β"
            elif tablet_id == "gamma": glyph_char = "γ"
            
            font_path = None
            if hasattr(gs, 'FONT_PATH_EMOJI_FOR_COLLECTIBLES'): 
                 font_path = gs.FONT_PATH_EMOJI_FOR_COLLECTIBLES
            elif hasattr(gs, 'font_path_emoji'): 
                 font_path = gs.font_path_emoji

            font_size = int(item_size_tuple[1] * 0.7) 
            
            try:
                font = pygame.font.Font(font_path, font_size) if font_path else pygame.font.Font(None, font_size)
            except:
                font = pygame.font.Font(None, font_size) 

            text_surf = font.render(glyph_char, True, CYAN)
            temp_icon_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
            temp_icon_surf.blit(text_surf, (0,0))
            loaded_icon = temp_icon_surf
        
        super().__init__(x, y, base_color=gs.CYAN, size=item_size_tuple, thickness=2,
                         original_icon_surface=loaded_icon if icon_filename else None,
                         is_rectangular=True)
        if not icon_filename and loaded_icon:
            self.icon_surface = loaded_icon
            self.original_icon_surface = None
        
        self.icon_rotation_speed = 0

    def update(self):
        if self.collected:
            self.kill()
            return True
        self.update_collectible_state(item_lifetime_ms=None)
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            print(f"{self.item_name} collected by player!")
            return True
        return False

# --- NEW CLASS ---
class AncientAlienTerminal(pygame.sprite.Sprite):
    def __init__(self, x, y, assets_path="assets/images/world/"):
        super().__init__()
        self.item_id = "ancient_alien_terminal_puzzle_trigger"
        self.interacted = False

        image_filename = "ancient_terminal.png" 
        image_path = os.path.join(assets_path, image_filename)
        
        try:
            self.original_image = pygame.image.load(image_path).convert_alpha()
            self.original_image = pygame.transform.smoothscale(self.original_image, (int(TILE_SIZE * 0.8), int(TILE_SIZE * 1.0)))
        except pygame.error as e:
            print(f"Error loading ancient terminal image '{image_path}': {e}. Using fallback.")
            self.original_image = pygame.Surface((int(TILE_SIZE * 0.8), int(TILE_SIZE * 1.0)), pygame.SRCALPHA)
            fallback_color = gs.get_game_setting("ARCHITECT_VAULT_WALL_COLOR", (150, 120, 200))
            self.original_image.fill(fallback_color)
            pygame.draw.rect(self.original_image, gs.CYAN, self.original_image.get_rect(), 3)
            try: 
                font = pygame.font.SysFont(None, 24)
                text_surf = font.render("TERM", True, gs.WHITE)
                text_rect = text_surf.get_rect(center=(self.original_image.get_width() // 2, self.original_image.get_height() // 2))
                self.original_image.blit(text_surf, text_rect)
            except Exception as font_e:
                print(f"Fallback font error for terminal: {font_e}")


        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        
        self.active_image = self.original_image.copy() 


    def interact(self, game_controller_instance):
        if not self.interacted:
            self.interacted = True
            self.image = self.active_image 
            print(f"Ancient Alien Terminal interacted with ({self.rect.center}). Triggering ring puzzle.")
            
            if hasattr(game_controller_instance, 'scene_manager') and \
               hasattr(gs, 'GAME_STATE_RING_PUZZLE'):
                game_controller_instance.scene_manager.set_game_state(gs.GAME_STATE_RING_PUZZLE)
            else:
                print("ERROR: Cannot set game state to ring puzzle. SceneManager or GAME_STATE_RING_PUZZLE missing.")

            if hasattr(game_controller_instance, 'play_sound'):
                game_controller_instance.play_sound('ui_confirm') 
            return True
        return False

    def update(self):
        pass

    def draw(self, surface): 
        surface.blit(self.image, self.rect)
