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

        self.base_draw_radius = float(size) if not is_rectangular else float(max(size) if isinstance(size, tuple) else size)
        self.item_size = size
        self.is_rectangular = is_rectangular
        self.thickness = thickness
        self.pulse_radius_amplitude = self.base_draw_radius * 0.25

        max_main_pulse_dim = self.base_draw_radius + self.pulse_radius_amplitude
        max_secondary_pulse_dim = max_main_pulse_dim * 1.15
        required_diameter = (max_secondary_pulse_dim * 2) + self.thickness
        self.surface_size = int(math.ceil(required_diameter)) + 4
        
        min_practical_size_calc = self.base_draw_radius * 2 if not is_rectangular else (max(self.item_size) if isinstance(self.item_size, tuple) else self.item_size)

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
        else: # Rectangular collectible
            rect_w_val = self.item_size[0] if isinstance(self.item_size, tuple) else self.item_size
            rect_h_val = self.item_size[1] if isinstance(self.item_size, tuple) else self.item_size
            
            temp_rect = pygame.Rect(0,0, int(rect_w_val), int(rect_h_val))
            temp_rect.center = (surface_center_x, surface_center_y)
            pygame.draw.rect(self.image, self.current_color, temp_rect, self.thickness, border_radius=3)

        if self.icon_surface:
            if self.original_icon_surface and self.icon_rotation_speed > 0: 
                self.icon_angle = (self.icon_angle + self.icon_rotation_speed * (gs.FPS / 60.0)) % 360 # Adjust rotation for FPS
                rotated_icon_surface = pygame.transform.rotate(self.original_icon_surface, self.icon_angle)
                icon_rect = rotated_icon_surface.get_rect(center=(surface_center_x, surface_center_y))
                self.image.blit(rotated_icon_surface, icon_rect)
            else: 
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
        # Rings don't expire, so no item_lifetime_ms
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
            # print("Weapon Upgrade collected!")


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

    _load_icon = WeaponUpgradeItem._load_icon # Reuse the icon loading method

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=POWERUP_ITEM_LIFETIME):
            self.kill()
            return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'activate_shield'):
            player_drone.activate_shield(self.effect_duration_ms)
            # print("Shield collected!")


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

    _load_icon = WeaponUpgradeItem._load_icon # Reuse the icon loading method

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=POWERUP_ITEM_LIFETIME):
            self.kill()
            return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'arm_speed_boost'): # Player "arms" it, activates on thrust
            player_drone.arm_speed_boost(self.effect_duration_ms, self.speed_multiplier)
            # print("Speed Boost collected!")


class CoreFragmentItem(Collectible):
    def __init__(self, x, y, fragment_id, fragment_config_details):
        self.fragment_id = fragment_id
        self.fragment_name = fragment_config_details.get("name", "Core Fragment")

        item_color = fragment_config_details.get("display_color", PURPLE) # Use display_color if available
        icon_filename = fragment_config_details.get("icon_filename")
        loaded_original_icon = self._load_icon(icon_filename, CORE_FRAGMENT_VISUAL_SIZE * 0.8)

        super().__init__(x, y, base_color=item_color, size=CORE_FRAGMENT_VISUAL_SIZE, thickness=3, original_icon_surface=loaded_original_icon)

    def _load_icon(self, filename, icon_render_size):
        if not filename: return None
        try:
            # Assuming fragment icons are in 'collectibles' like other specific items
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
        if self.collected: # If already marked as collected by game logic
            self.kill()
            return True
        # Core fragments don't expire on their own
        self.update_collectible_state(item_lifetime_ms=None)
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        """Called when the player collides with the fragment."""
        if not self.collected: # Ensure it's applied only once
            if hasattr(game_controller_instance, 'drone_system') and \
               hasattr(game_controller_instance.drone_system, 'collect_core_fragment'):
                # Notify DroneSystem that this fragment was collected
                if game_controller_instance.drone_system.collect_core_fragment(self.fragment_id):
                    self.collected = True # Mark as collected internally
                    # print(f"Core Fragment '{self.fragment_name}' collected by player!")
                    # DroneSystem handles saving and lore unlocks related to fragment collection
                    return True # Successfully applied
            else:
                print(f"Error: Could not notify DroneSystem about collecting Core Fragment '{self.fragment_name}'.")
        return False # Already collected or error

class VaultLogItem(Collectible):
    """Represents a collectible Vault Log that unlocks lore."""
    def __init__(self, x, y, log_id, icon_filename=None):
        self.log_id = log_id
        item_size_tuple = (TILE_SIZE * 0.4, TILE_SIZE * 0.5) # Rectangular
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
        
        super().__init__(x, y, base_color=DARK_PURPLE, size=item_size_tuple, thickness=2,
                         original_icon_surface=loaded_icon_surface,
                         is_rectangular=True)

        if loaded_icon_surface is None: # If no image, create text/emoji icon
            try:
                font_path_to_use = gs.UI_FONT_PATH_EMOJI if hasattr(gs, 'UI_FONT_PATH_EMOJI') else None
                font_obj = pygame.font.Font(font_path_to_use, int(item_size_tuple[1] * 0.6))
            except: 
                font_obj = pygame.font.Font(None, int(item_size_tuple[1] * 0.6)) # Fallback

            text_surf = font_obj.render(self.default_icon_char, True, gs.CYAN)
            self.icon_surface = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
            self.icon_surface.blit(text_surf, (0,0))
            self.original_icon_surface = None # Ensure no rotation if it's a rendered icon
        
        self.icon_rotation_speed = 0 # Text/emoji icons usually don't rotate

    def update(self):
        if self.collected:
            self.kill()
            return True
        self.update_collectible_state(item_lifetime_ms=None) # Logs don't expire
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            # print(f"Vault Log '{self.log_id}' collected by player!")
            # DroneSystem handles lore unlock via event_trigger="collect_log_{log_id}"
            return True
        return False

class GlyphTabletItem(Collectible):
    """Represents a collectible Architect Glyph Tablet."""
    def __init__(self, x, y, tablet_id, icon_filename=None): # Allow specific icon
        self.tablet_id = tablet_id
        self.item_name = f"Glyph Tablet ({tablet_id.capitalize()})"
        item_size_tuple = (TILE_SIZE * 0.45, TILE_SIZE * 0.35) # Rectangular

        loaded_icon = None
        if icon_filename: # If an image filename is provided
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

        if loaded_icon is None: # Fallback to character-based icon
            glyph_char = "?" # Default
            if tablet_id == "alpha": glyph_char = "α"
            elif tablet_id == "beta": glyph_char = "β"
            elif tablet_id == "gamma": glyph_char = "γ"
            
            font_path = None # Determine font path (e.g., from game_settings)
            if hasattr(gs, 'FONT_PATH_EMOJI_FOR_COLLECTIBLES'): font_path = gs.FONT_PATH_EMOJI_FOR_COLLECTIBLES
            elif hasattr(gs, 'font_path_emoji'): font_path = gs.font_path_emoji
            font_size = int(item_size_tuple[1] * 0.7)
            try:
                font = pygame.font.Font(font_path, font_size) if font_path else pygame.font.Font(None, font_size)
            except: font = pygame.font.Font(None, font_size)

            text_surf = font.render(glyph_char, True, CYAN)
            temp_icon_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
            temp_icon_surf.blit(text_surf, (0,0))
            loaded_icon = temp_icon_surf
        
        super().__init__(x, y, base_color=gs.CYAN, size=item_size_tuple, thickness=2,
                         original_icon_surface=loaded_icon if icon_filename else None, # Pass original if loaded from file
                         is_rectangular=True)
        if not icon_filename and loaded_icon: # If icon was rendered (not from file)
            self.icon_surface = loaded_icon
            self.original_icon_surface = None # No rotation for rendered icons
        
        self.icon_rotation_speed = 0 # Glyphs usually don't spin

    def update(self):
        if self.collected:
            self.kill()
            return True
        self.update_collectible_state(item_lifetime_ms=None) # Tablets don't expire
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            # print(f"{self.item_name} collected by player!")
            # DroneSystem handles lore unlock via event_trigger="collect_glyph_tablet_{tablet_id}"
            # and adds to persistent list via game_controller_instance.drone_system.add_collected_glyph_tablet(self.tablet_id)
            return True
        return False

class AncientAlienTerminal(pygame.sprite.Sprite):
    """A terminal that triggers the Ring Puzzle."""
    def __init__(self, x, y, assets_path="assets/images/world/"):
        super().__init__()
        self.item_id = "ancient_alien_terminal_puzzle_trigger" # Generic ID, can be made more specific
        self.interacted = False

        image_filename = "ancient_terminal.png" 
        image_path = os.path.join(assets_path, image_filename)
        
        try:
            self.original_image = pygame.image.load(image_path).convert_alpha()
            # Scale to a reasonable size, e.g., slightly smaller than a tile or a bit larger
            self.original_image = pygame.transform.smoothscale(self.original_image, (int(TILE_SIZE * 0.8), int(TILE_SIZE * 1.0)))
        except pygame.error as e:
            print(f"Error loading ancient terminal image '{image_path}': {e}. Using fallback.")
            self.original_image = pygame.Surface((int(TILE_SIZE * 0.8), int(TILE_SIZE * 1.0)), pygame.SRCALPHA)
            fallback_color = gs.get_game_setting("ARCHITECT_VAULT_WALL_COLOR", (150, 120, 200)) # Use a distinct color
            self.original_image.fill(fallback_color)
            pygame.draw.rect(self.original_image, gs.CYAN, self.original_image.get_rect(), 3) # Border
            try: # Add fallback text
                font = pygame.font.SysFont(None, 24) # System font
                text_surf = font.render("TERM", True, gs.WHITE)
                text_rect = text_surf.get_rect(center=(self.original_image.get_width() // 2, self.original_image.get_height() // 2))
                self.original_image.blit(text_surf, text_rect)
            except Exception as font_e:
                print(f"Fallback font error for terminal: {font_e}")


        self.image = self.original_image # Current image to draw
        self.rect = self.image.get_rect(center=(x, y))
        
        # Could have an "active" image if needed, e.g., when puzzle is solved or terminal is used
        self.active_image = self.original_image.copy() # For now, same as original
        # Example: Tint active image
        # self.active_image.fill((0, 50, 0, 100), special_flags=pygame.BLEND_RGBA_ADD)


    def interact(self, game_controller_instance):
        """Called when the player interacts with the terminal."""
        if not self.interacted:
            self.interacted = True # Mark as interacted to prevent re-triggering
            self.image = self.active_image # Change appearance if needed
            # print(f"Ancient Alien Terminal interacted with ({self.rect.center}). Triggering ring puzzle.")
            
            # Trigger the ring puzzle game state
            if hasattr(game_controller_instance, 'scene_manager') and \
               hasattr(gs, 'GAME_STATE_RING_PUZZLE'):
                game_controller_instance.scene_manager.set_game_state(gs.GAME_STATE_RING_PUZZLE)
            else:
                print("ERROR: Cannot set game state to ring puzzle. SceneManager or GAME_STATE_RING_PUZZLE missing.")

            if hasattr(game_controller_instance, 'play_sound'):
                game_controller_instance.play_sound('ui_confirm') # Confirmation sound
            return True # Interaction successful
        return False # Already interacted

    def update(self):
        """Terminals might not need continuous updates unless they animate."""
        pass # No active update needed for a static terminal currently

    def draw(self, surface): 
        """Draws the terminal on the given surface."""
        surface.blit(self.image, self.rect)

# NEW CLASS: ArchitectEchoItem
class ArchitectEchoItem(Collectible):
    """Represents a collectible fragment of the Architect's consciousness or corrupted data."""
    def __init__(self, x, y, echo_id, associated_lore_id, icon_char="◈"):
        self.echo_id = echo_id # Unique ID for this specific echo, e.g., "echo_regret_01"
        self.associated_lore_id = associated_lore_id # The lore entry unlocked by this echo
        
        # Visuals: Pulsating, glitchy data fragment
        item_size = TILE_SIZE * 0.35
        base_color = (100, 220, 255, 180) # Glitchy cyan/blue with some transparency
        
        # Create a custom icon surface (e.g., a glitchy character or small sprite)
        # For simplicity, using a character here. Could be an image.
        icon_render_size = int(item_size * 0.7)
        icon_surface = None
        try:
            font_path_to_use = gs.UI_FONT_PATH_EMOJI if hasattr(gs, 'UI_FONT_PATH_EMOJI') else None
            font_obj = pygame.font.Font(font_path_to_use, icon_render_size)
            text_surf = font_obj.render(icon_char, True, WHITE) # White character
            icon_surface = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
            icon_surface.blit(text_surf, (0,0))
        except Exception as e:
            print(f"Error creating icon for ArchitectEchoItem: {e}")
            # Fallback if font fails, could be a small colored square
            icon_surface = pygame.Surface((icon_render_size, icon_render_size), pygame.SRCALPHA)
            icon_surface.fill(WHITE)

        super().__init__(x, y, base_color=base_color, size=item_size, thickness=2, 
                         original_icon_surface=icon_surface, # Pass the rendered icon as original for bob/pulse
                         is_rectangular=False) # Circular pulse for this item
        
        self.icon_rotation_speed = 0.5 # Slow rotation for the icon itself
        self.pulse_speed_factor = 0.008 # Faster, more erratic pulse
        self.pulse_radius_amplitude = self.base_draw_radius * 0.4 # More pronounced pulse
        self.bob_amplitude = 6 # More noticeable bob

    def update(self):
        if self.collected:
            self.kill()
            return True
        # Echo fragments don't expire on their own
        self.update_collectible_state(item_lifetime_ms=None)
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        """Called when the player collides with the echo fragment."""
        if not self.collected:
            self.collected = True
            # print(f"Architect Echo '{self.echo_id}' collected by player! Unlocks lore: '{self.associated_lore_id}'")
            
            # Unlock the associated lore entry
            if self.associated_lore_id and hasattr(game_controller_instance, 'drone_system'):
                unlocked_ids = game_controller_instance.drone_system.unlock_lore_entry_by_id(self.associated_lore_id)
                if unlocked_ids:
                    # Display the story message from the unlocked lore
                    lore_details = game_controller_instance.drone_system.get_lore_entry_details(self.associated_lore_id)
                    if lore_details and lore_details.get("content"):
                        # Use a specific field for the "echo message" if available, else use title
                        echo_message = lore_details.get("echo_message", lore_details.get("title", "Data Fragment Decrypted"))
                        game_controller_instance.set_story_message(f"ARCHITECT'S ECHO: \"{echo_message}\"")
                    else:
                        game_controller_instance.set_story_message("Corrupted Data Fragment Decrypted.")
            else:
                 game_controller_instance.set_story_message("Corrupted Data Fragment Collected.")

            if hasattr(game_controller_instance, 'play_sound'):
                game_controller_instance.play_sound('collect_fragment', 0.7) # Can use a unique sound later
            
            return True # Successfully applied
        return False # Already collected