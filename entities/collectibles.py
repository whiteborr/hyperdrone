# entities/collectibles.py
import os
import math
import random

import pygame

import game_settings as gs
from game_settings import (
    GOLD, PURPLE, BLUE, LIGHT_BLUE, GREEN, DARK_PURPLE, CYAN, WHITE,
    POWERUP_TYPES, TILE_SIZE, POWERUP_SIZE, CORE_FRAGMENT_VISUAL_SIZE,
    WEAPON_UPGRADE_ITEM_LIFETIME, POWERUP_ITEM_LIFETIME,
    ARCHITECT_VAULT_WALL_COLOR
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
        self.icon_surface = original_icon_surface
        
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
        self.icon_rotation_speed = 0.3 if original_icon_surface else 0
        
        # Initial draw and positioning
        self._update_pulse_effect()
        self.rect = self.image.get_rect(center=(self.center_x, self.center_y))
        self._update_bob_effect()
        self._render_to_image()

    def _update_pulse_effect(self):
        # (This method's logic remains the same)
        time_ticks = pygame.time.get_ticks()
        pulse_wave = math.sin(time_ticks * self.pulse_speed_factor + self.pulse_time_offset)
        self.current_pulse_radius = self.base_draw_radius + pulse_wave * self.pulse_radius_amplitude
        self.current_pulse_radius = max(self.base_draw_radius * 0.65, self.current_pulse_radius)
        alpha_normalized = (pulse_wave + 1) / 2
        alpha = int(150 + alpha_normalized * self.pulse_alpha_amplitude)
        alpha = max(100, min(255, alpha))
        lerp_factor_color = (pulse_wave + 1) / 2
        r_base, g_base, b_base = self.base_color[:3]
        brightness_increase = 35
        r_bright, g_bright, b_bright = min(255, r_base + brightness_increase), min(255, g_base + brightness_increase), min(255, b_base + brightness_increase)
        r_pulsed, g_pulsed, b_pulsed = int(r_base + (r_bright - r_base) * lerp_factor_color), int(g_base + (g_bright - g_base) * lerp_factor_color), int(b_base + (b_bright - b_base) * lerp_factor_color)
        self.current_color = (r_pulsed, g_pulsed, b_pulsed, alpha)

    def _update_bob_effect(self):
        # (This method's logic remains the same)
        time_ticks = pygame.time.get_ticks()
        self.current_y_offset = math.sin(time_ticks * self.bob_speed + self.bob_time_offset) * self.bob_amplitude
        if hasattr(self, 'rect') and self.rect is not None:
            self.rect.centery = int(self.center_y + self.current_y_offset)
            self.rect.centerx = int(self.center_x)

    def _render_to_image(self):
        # (This method's logic remains the same)
        self.image.fill((0, 0, 0, 0))
        surface_center_x, surface_center_y = self.surface_size // 2, self.surface_size // 2
        if not self.is_rectangular:
            pygame.draw.circle(self.image, self.current_color, (surface_center_x, surface_center_y), int(self.current_pulse_radius), self.thickness)
            if self.current_pulse_radius > self.base_draw_radius * 0.8:
                secondary_radius = int(self.current_pulse_radius * 1.15)
                current_alpha_component = self.current_color[3] if len(self.current_color) == 4 else 255
                denominator = self.pulse_radius_amplitude * 1.2
                normalized_expansion = (self.current_pulse_radius - self.base_draw_radius * 0.8) / denominator if denominator != 0 else 1.0
                normalized_expansion = max(0, min(1, normalized_expansion))
                secondary_alpha = int(current_alpha_component * 0.4 * normalized_expansion)
                if secondary_alpha > 20:
                    secondary_color = (*self.current_color[:3], secondary_alpha)
                    pygame.draw.circle(self.image, secondary_color, (surface_center_x, surface_center_y), secondary_radius, max(1, self.thickness // 2))
        else:
            rect_w = self.item_size[0] if isinstance(self.item_size, tuple) else self.item_size
            rect_h = self.item_size[1] if isinstance(self.item_size, tuple) else self.item_size
            temp_rect = pygame.Rect(0,0, int(rect_w), int(rect_h)); temp_rect.center = (surface_center_x, surface_center_y)
            pygame.draw.rect(self.image, self.current_color, temp_rect, self.thickness, border_radius=3)
        if self.icon_surface:
            if self.original_icon_surface and self.icon_rotation_speed > 0: 
                fps_ratio = gs.get_game_setting("FPS", 60) / 60.0 # Adjust rotation for FPS
                self.icon_angle = (self.icon_angle + self.icon_rotation_speed * fps_ratio) % 360
                rotated_icon = pygame.transform.rotate(self.original_icon_surface, self.icon_angle)
                icon_rect = rotated_icon.get_rect(center=(surface_center_x, surface_center_y))
                self.image.blit(rotated_icon, icon_rect)
            else: 
                icon_rect = self.icon_surface.get_rect(center=(surface_center_x, surface_center_y))
                self.image.blit(self.icon_surface, icon_rect)

    def update_collectible_state(self, item_lifetime_ms=None):
        # (This method's logic remains the same)
        if self.collected or self.expired: return True
        if item_lifetime_ms is not None:
            if not hasattr(self, 'creation_time'): self.creation_time = pygame.time.get_ticks()
            if pygame.time.get_ticks() - self.creation_time > item_lifetime_ms:
                self.expired = True; return True
        self._update_pulse_effect(); self._update_bob_effect(); self._render_to_image()
        return False

    def update(self):
        # (This method's logic remains the same)
        if self.update_collectible_state():
            self.kill()
            return True
        return False


class Ring(Collectible):
    # This class is procedural and does not load assets, so no change is needed.
    def __init__(self, x, y):
        ring_size = TILE_SIZE // 4
        super().__init__(x, y, base_color=GOLD, size=ring_size, thickness=3)

    def update(self):
        if self.collected: self.kill(); return True
        self.update_collectible_state(item_lifetime_ms=None)
        return False


class WeaponUpgradeItem(Collectible):
    def __init__(self, x, y, asset_manager):
        self.powerup_type_key = "weapon_upgrade"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", BLUE)
        
        # Use asset_manager to get the icon
        icon_asset_key = "weapon_upgrade_powerup_icon" # Must match manifest key
        # GameController preload should handle scaling, so we don't scale here
        loaded_original_icon = asset_manager.get_image(icon_asset_key)

        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = pygame.time.get_ticks()

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=WEAPON_UPGRADE_ITEM_LIFETIME):
            self.kill(); return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'cycle_weapon_state'):
            player_drone.cycle_weapon_state(force_cycle=True)


class ShieldItem(Collectible):
    def __init__(self, x, y, asset_manager):
        self.powerup_type_key = "shield"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", LIGHT_BLUE)
        
        icon_asset_key = "shield_powerup_icon"
        loaded_original_icon = asset_manager.get_image(icon_asset_key)
        
        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration_ms = details.get("duration", 10000)

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=POWERUP_ITEM_LIFETIME):
            self.kill(); return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'activate_shield'):
            player_drone.activate_shield(self.effect_duration_ms)


class SpeedBoostItem(Collectible):
    def __init__(self, x, y, asset_manager):
        self.powerup_type_key = "speed_boost"
        details = POWERUP_TYPES.get(self.powerup_type_key, {})
        item_color = details.get("color", GREEN)

        icon_asset_key = "speed_boost_powerup_icon"
        loaded_original_icon = asset_manager.get_image(icon_asset_key)

        super().__init__(x, y, base_color=item_color, size=POWERUP_SIZE, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration_ms = details.get("duration", 7000)
        self.speed_multiplier = details.get("multiplier", 1.5)

    def update(self):
        if self.update_collectible_state(item_lifetime_ms=POWERUP_ITEM_LIFETIME):
            self.kill(); return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'arm_speed_boost'):
            player_drone.arm_speed_boost(self.effect_duration_ms, self.speed_multiplier)


class CoreFragmentItem(Collectible):
    def __init__(self, x, y, fragment_id, fragment_config_details, asset_manager):
        self.fragment_id = fragment_id
        self.fragment_name = fragment_config_details.get("name", "Core Fragment")
        item_color = fragment_config_details.get("display_color", PURPLE)
        
        # Construct asset key from fragment_id
        icon_asset_key = f"fragment_{self.fragment_id}_icon"
        
        # --- START FIX ---
        # Define the target size as a tuple based on the game setting.
        target_icon_size = (int(CORE_FRAGMENT_VISUAL_SIZE), int(CORE_FRAGMENT_VISUAL_SIZE))
        # Request the scaled image from the AssetManager.
        loaded_original_icon = asset_manager.get_image(icon_asset_key, scale_to_size=target_icon_size)
        # --- END FIX ---

        super().__init__(x, y, base_color=item_color, size=CORE_FRAGMENT_VISUAL_SIZE, thickness=3, original_icon_surface=loaded_original_icon)

    def update(self):
        if self.collected: self.kill(); return True
        self.update_collectible_state(item_lifetime_ms=None)
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            if hasattr(game_controller_instance, 'drone_system') and \
               hasattr(game_controller_instance.drone_system, 'collect_core_fragment'):
                if game_controller_instance.drone_system.collect_core_fragment(self.fragment_id):
                    self.collected = True
                    return True
            else:
                print(f"Error: Could not notify DroneSystem about collecting Core Fragment '{self.fragment_name}'.")
        return False


class VaultLogItem(Collectible):
    def __init__(self, x, y, log_id, icon_filename=None, asset_manager=None):
        self.log_id = log_id
        item_size_tuple = (TILE_SIZE * 0.4, TILE_SIZE * 0.5)
        
        # VaultLogItem is rectangular, with a small icon in the center
        # For this, we'll get the icon from asset manager and blit it onto our procedural base in _render_to_image
        # The base Collectible class can handle this if we pass the icon surface.
        
        # For simplicity, we assume VaultLogItem is procedural for now and doesn't load a base sprite,
        # but if it did, we'd get it from asset_manager here.
        
        super().__init__(x, y, base_color=DARK_PURPLE, size=item_size_tuple, thickness=2,
                         original_icon_surface=None, # No spinning main icon
                         is_rectangular=True)
        
        # Create the fixed inner icon (e.g., emoji)
        self.icon_rotation_speed = 0 # No rotation
        font_key = "ui_emoji_general" # Font key for fallback emoji
        font_size = int(item_size_tuple[1] * 0.6)
        
        font = asset_manager.get_font(font_key, font_size) if asset_manager else pygame.font.Font(None, font_size)
        if not font: font = pygame.font.Font(None, font_size)

        text_surf = font.render("📝", True, gs.CYAN)
        self.icon_surface = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        self.icon_surface.blit(text_surf, (0,0))


    def update(self):
        if self.collected: self.kill(); return True
        self.update_collectible_state(item_lifetime_ms=None)
        return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True; return True
        return False


class AncientAlienTerminal(pygame.sprite.Sprite):
    def __init__(self, x, y, asset_manager):
        super().__init__()
        self.asset_manager = asset_manager
        self.item_id = "ancient_alien_terminal_puzzle_trigger"
        self.interacted = False
        self.image_asset_key = "ancient_terminal_sprite_img" # Key from manifest
        self.size = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 1.0))

        # Load images from AssetManager
        self.original_image = self.asset_manager.get_image(self.image_asset_key)
        
        if self.original_image:
            self.original_image = pygame.transform.smoothscale(self.original_image, self.size)
            self.active_image = self.original_image.copy()
            # Example tint for active state
            self.active_image.fill((0, 50, 0, 100), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            # Fallback procedural sprite
            self.original_image = self.asset_manager._create_fallback_surface(
                size=self.size, color=ARCHITECT_VAULT_WALL_COLOR, text="TERM", text_color=WHITE
            )
            self.active_image = self.original_image # No visual change for fallback active state

        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))

    def interact(self, game_controller_instance):
        if not self.interacted:
            self.interacted = True
            self.image = self.active_image
            
            if hasattr(game_controller_instance, 'scene_manager') and hasattr(gs, 'GAME_STATE_RING_PUZZLE'):
                game_controller_instance.scene_manager.set_game_state(gs.GAME_STATE_RING_PUZZLE, triggering_terminal=self)
            else:
                print("ERROR: Cannot set game state to ring puzzle. SceneManager or GAME_STATE_RING_PUZZLE missing.")

            if hasattr(game_controller_instance, 'play_sound'):
                game_controller_instance.play_sound('ui_confirm')
            return True
        return False

    def update(self):
        pass # Static for now


# These classes were not present in the original file, so their refactoring is based on
# a similar pattern to the other collectibles.
class GlyphTabletItem(Collectible):
    def __init__(self, x, y, tablet_id, asset_manager, icon_filename=None):
        self.tablet_id = tablet_id
        item_size_tuple = (TILE_SIZE * 0.45, TILE_SIZE * 0.35)
        
        loaded_icon = asset_manager.get_image(f"glyph_tablet_{tablet_id}_icon") if not icon_filename else asset_manager.get_image(icon_filename)
        
        if loaded_icon is None:
            glyph_char = {"alpha": "α", "beta": "β", "gamma": "γ"}.get(tablet_id, "?")
            font = asset_manager.get_font("ui_emoji_general", int(item_size_tuple[1] * 0.7)) or pygame.font.Font(None, int(item_size_tuple[1] * 0.7))
            text_surf = font.render(glyph_char, True, CYAN)
            loaded_icon = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
            loaded_icon.blit(text_surf, (0,0))

        super().__init__(x, y, base_color=CYAN, size=item_size_tuple, thickness=2,
                         original_icon_surface=loaded_icon, is_rectangular=True)
        self.icon_rotation_speed = 0

    def update(self):
        if self.collected: self.kill(); return True
        self.update_collectible_state(); return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected: self.collected = True; return True
        return False

class ArchitectEchoItem(Collectible):
    def __init__(self, x, y, echo_id, associated_lore_id, asset_manager, icon_char="◈"):
        self.echo_id = echo_id
        self.associated_lore_id = associated_lore_id
        item_size = TILE_SIZE * 0.35
        base_color = (100, 220, 255, 180)
        
        font_size = int(item_size * 0.7)
        font = asset_manager.get_font("ui_emoji_general", font_size) or pygame.font.Font(None, font_size)
        text_surf = font.render(icon_char, True, WHITE)
        icon_surface = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        icon_surface.blit(text_surf, (0,0))

        super().__init__(x, y, base_color=base_color, size=item_size, thickness=2, 
                         original_icon_surface=icon_surface, is_rectangular=False)
        
        self.icon_rotation_speed = 0.5; self.pulse_speed_factor = 0.008
        self.pulse_radius_amplitude = self.base_draw_radius * 0.4
        self.bob_amplitude = 6

    def update(self):
        if self.collected: self.kill(); return True
        self.update_collectible_state(); return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            if self.associated_lore_id and hasattr(game_controller_instance, 'drone_system'):
                unlocked_ids = game_controller_instance.drone_system.unlock_lore_entry_by_id(self.associated_lore_id)
                if unlocked_ids:
                    lore_details = game_controller_instance.drone_system.get_lore_entry_details(self.associated_lore_id)
                    if lore_details and lore_details.get("content"):
                        echo_message = lore_details.get("echo_message", lore_details.get("title", "Data Fragment Decrypted"))
                        game_controller_instance.set_story_message(f"ARCHITECT'S ECHO: \"{echo_message}\"")
                    else:
                        game_controller_instance.set_story_message("Corrupted Data Fragment Decrypted.")
            else:
                 game_controller_instance.set_story_message("Corrupted Data Fragment Collected.")
            if hasattr(game_controller_instance, 'play_sound'):
                game_controller_instance.play_sound('collect_fragment', 0.7)
            return True
        return False
