# entities/collectibles.py
from math import sin, pi, ceil
from random import uniform
from pygame.sprite import Sprite
from pygame import Surface, SRCALPHA, Rect
from pygame.draw import circle, rect as draw_rect
from pygame.time import get_ticks
from pygame.transform import rotate, scale, smoothscale
from pygame.font import Font

from constants import (
    GOLD, PURPLE, BLUE, LIGHT_BLUE, GREEN, DARK_PURPLE, CYAN, WHITE,
    ARCHITECT_VAULT_WALL_COLOR
)
from settings_manager import get_setting, get_asset_path

class Collectible(Sprite):
    """Base class for collectible items with a pulsing shine effect, bobbing, and icon spin."""
    def __init__(self, x, y, base_color, size, thickness=3, original_icon_surface=None, is_rectangular=False):
        super().__init__()
        self.center_x, self.center_y = float(x), float(y)
        self.item_size, self.is_rectangular = size, is_rectangular
        self.base_draw_radius = float(max(size) if isinstance(size, tuple) else size) if is_rectangular else float(size)
        self.thickness = thickness
        self.pulse_radius_amplitude = self.base_draw_radius * 0.25
        required_diameter = ((self.base_draw_radius + self.pulse_radius_amplitude) * 1.15 * 2) + self.thickness
        self.surface_size = max(int(ceil(required_diameter)) + 4, 32)
        self.image = Surface((self.surface_size, self.surface_size), SRCALPHA)
        self.original_icon_surface, self.icon_surface = original_icon_surface, original_icon_surface
        self.collected, self.expired = False, False
        self.base_color = base_color
        self.pulse_speed_factor, self.pulse_alpha_amplitude = 0.005, 100
        self.pulse_time_offset = uniform(0, 2 * pi)
        self.bob_speed, self.bob_amplitude = 0.003, 4
        self.bob_time_offset = uniform(0, 2 * pi)
        self.current_y_offset = 0
        self.icon_angle = 0
        self.icon_rotation_speed = 0.3 if original_icon_surface else 0
        self._update_pulse_effect()
        self.rect = self.image.get_rect(center=(self.center_x, self.center_y))
        self._update_bob_effect()
        self._render_to_image()

    def _update_pulse_effect(self):
        pulse_wave = sin(get_ticks() * self.pulse_speed_factor + self.pulse_time_offset)
        self.current_pulse_radius = max(self.base_draw_radius * 0.65, self.base_draw_radius + pulse_wave * self.pulse_radius_amplitude)
        alpha = int(150 + ((pulse_wave + 1) / 2) * self.pulse_alpha_amplitude)
        r, g, b = self.base_color[:3]
        r_b, g_b, b_b = min(255, r + 35), min(255, g + 35), min(255, b + 35)
        lerp = (pulse_wave + 1) / 2
        r_p, g_p, b_p = int(r + (r_b-r)*lerp), int(g + (g_b-g)*lerp), int(b + (b_b-b)*lerp)
        self.current_color = (r_p, g_p, b_p, max(100, min(255, alpha)))

    def _update_bob_effect(self):
        self.current_y_offset = sin(get_ticks() * self.bob_speed + self.bob_time_offset) * self.bob_amplitude
        if hasattr(self, 'rect') and self.rect: self.rect.centery = int(self.center_y + self.current_y_offset); self.rect.centerx = int(self.center_x)

    def _render_to_image(self):
        self.image.fill((0,0,0,0))
        center = self.surface_size // 2
        if not self.is_rectangular:
            circle(self.image, self.current_color, (center, center), int(self.current_pulse_radius), self.thickness)
            if self.current_pulse_radius > self.base_draw_radius * 0.8:
                sec_radius = int(self.current_pulse_radius * 1.15)
                norm_exp = (self.current_pulse_radius - self.base_draw_radius * 0.8) / (self.pulse_radius_amplitude * 1.2) if self.pulse_radius_amplitude != 0 else 1
                sec_alpha = int(self.current_color[3] * 0.4 * max(0, min(1, norm_exp)))
                if sec_alpha > 20: circle(self.image, (*self.current_color[:3], sec_alpha), (center,center), sec_radius, max(1, self.thickness//2))
        else:
            w = self.item_size[0] if isinstance(self.item_size, tuple) else self.item_size
            h = self.item_size[1] if isinstance(self.item_size, tuple) else self.item_size
            temp_rect_info = Rect(0,0,int(w),int(h))
            temp_rect_info.center = (center,center)
            draw_rect(self.image, self.current_color, temp_rect_info, self.thickness, border_radius=3)
        if self.icon_surface:
            if self.original_icon_surface and self.icon_rotation_speed > 0: 
                self.icon_angle = (self.icon_angle + self.icon_rotation_speed * (get_setting("display", "FPS", 60)/60.0)) % 360
                rot_icon = rotate(self.original_icon_surface, self.icon_angle)
                self.image.blit(rot_icon, rot_icon.get_rect(center=(center, center)))
            else: self.image.blit(self.icon_surface, self.icon_surface.get_rect(center=(center,center)))

    def update_collectible_state(self, item_lifetime_ms=None):
        if self.collected or self.expired: return True
        if item_lifetime_ms and not hasattr(self, 'creation_time'): self.creation_time = get_ticks()
        if item_lifetime_ms and (get_ticks() - self.creation_time > item_lifetime_ms): self.expired = True; return True
        self._update_pulse_effect(); self._update_bob_effect(); self._render_to_image()
        return False

    def update(self):
        if self.update_collectible_state(): self.kill(); return True
        return False

    def draw(self, surface, camera=None):
        if not self.image or not self.rect: return
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            if not screen_rect.colliderect(surface.get_rect()): return
            if screen_rect.width > 0 and screen_rect.height > 0:
                scaled_image = scale(self.image, screen_rect.size)
                surface.blit(scaled_image, screen_rect.topleft)
        else:
            surface.blit(self.image, self.rect)

class Ring(Collectible):
    def __init__(self, x, y):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        super().__init__(x, y, base_color=GOLD, size=tile_size // 4, thickness=3)

    def update(self):
        if self.collected: self.kill(); return True
        self.update_collectible_state(); return False

class WeaponUpgradeItem(Collectible):
    def __init__(self, x, y, *, asset_manager):
        powerup_types = {
            "weapon_upgrade": {"weight": 0.4, "duration": 0, "color": BLUE}
        }
        powerup_size = get_setting("powerups", "POWERUP_SIZE", 26)
        icon_asset_key = "weapon_upgrade_powerup_icon"
        loaded_original_icon = asset_manager.get_image(icon_asset_key)
        super().__init__(x, y, base_color=BLUE, size=powerup_size, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = get_ticks()

    def update(self):
        weapon_upgrade_lifetime = get_setting("powerups", "WEAPON_UPGRADE_ITEM_LIFETIME", 15000)
        if self.update_collectible_state(item_lifetime_ms=weapon_upgrade_lifetime): self.kill(); return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'cycle_weapon_state'): player_drone.cycle_weapon_state()

class ShieldItem(Collectible):
    def __init__(self, x, y, *, asset_manager):
        powerup_size = get_setting("powerups", "POWERUP_SIZE", 26)
        loaded_original_icon = asset_manager.get_image("shield_powerup_icon")
        super().__init__(x, y, base_color=LIGHT_BLUE, size=powerup_size, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = get_ticks()
        self.effect_duration_ms = get_setting("powerups", "SHIELD_POWERUP_DURATION", 10000)

    def update(self):
        powerup_lifetime = get_setting("powerups", "POWERUP_ITEM_LIFETIME", 12000)
        if self.update_collectible_state(item_lifetime_ms=powerup_lifetime): self.kill(); return True
        return False

    def apply_effect(self, player_drone):
        if hasattr(player_drone, 'activate_shield'): player_drone.activate_shield(self.effect_duration_ms)

class SpeedBoostItem(Collectible):
    def __init__(self, x, y, *, asset_manager):
        powerup_size = get_setting("powerups", "POWERUP_SIZE", 26)
        loaded_original_icon = asset_manager.get_image("speed_boost_powerup_icon")
        super().__init__(x, y, base_color=GREEN, size=powerup_size, thickness=4, original_icon_surface=loaded_original_icon)
        self.creation_time = get_ticks()
        self.effect_duration_ms = get_setting("powerups", "SPEED_BOOST_POWERUP_DURATION", 7000)
        self.speed_multiplier = 1.5  # Could be moved to settings if needed

    def update(self):
        powerup_lifetime = get_setting("powerups", "POWERUP_ITEM_LIFETIME", 12000)
        if self.update_collectible_state(item_lifetime_ms=powerup_lifetime): self.kill(); return True
        return False

    def apply_effect(self, player_drone, game_controller=None):
        if hasattr(player_drone, 'arm_speed_boost'): 
            player_drone.arm_speed_boost(self.effect_duration_ms, self.speed_multiplier)
            # Don't auto-activate - wait for UP key press

class CoreFragmentItem(Collectible):
    def __init__(self, x, y, fragment_id, fragment_config_details, *, asset_manager):
        self.fragment_id = fragment_id
        self.fragment_name = fragment_config_details.get("name", "Core Fragment")
        self.associated_ability = fragment_config_details.get("associated_ability", None) # NEW: Store associated ability
        icon_filename = fragment_config_details.get("icon_filename")
        fragment_size = 32
        loaded_original_icon = None
        if icon_filename:
            loaded_original_icon = asset_manager.get_image(icon_filename)
        
        if not loaded_original_icon:
            icon_asset_key = f"{self.fragment_id}_icon"
            loaded_original_icon = asset_manager.get_image(icon_asset_key)
            
        if not loaded_original_icon:
            fallback_size = (fragment_size, fragment_size)
            fallback_surface = Surface(fallback_size, SRCALPHA)
            circle(fallback_surface, (128, 0, 255), (fragment_size//2, fragment_size//2), fragment_size//2)
            loaded_original_icon = fallback_surface
        
        # Explicitly resize the icon to the desired size
        if loaded_original_icon:
            icon_size = (fragment_size, fragment_size)
            loaded_original_icon = scale(loaded_original_icon, icon_size)
            
        super().__init__(x, y, base_color=fragment_config_details.get("display_color", (128, 0, 255)), size=fragment_size, thickness=3, original_icon_surface=loaded_original_icon)

    def update(self):
        if self.collected: self.kill(); return True
        self.update_collectible_state(); return False

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected and hasattr(game_controller_instance, 'drone_system'):
            if game_controller_instance.drone_system.collect_core_fragment(self.fragment_id):
                self.collected = True
                # NEW: Unlock the associated ability
                if self.associated_ability and hasattr(player_drone, 'unlock_ability'):
                    # Call player_drone's method to unlock ability, which also checks drone_system
                    if player_drone.unlock_ability(self.associated_ability):
                        # This means it's the *first time* this ability is unlocked for the player session
                        game_controller_instance.set_story_message(
                            f"{self.fragment_name} collected! Press 'F' to activate {self.associated_ability.replace('_', ' ').title()}.",
                            5000 # Message duration
                        )

                # Play collection sound
                if hasattr(game_controller_instance, 'play_sound'):
                    game_controller_instance.play_sound('collect_fragment')
                return True
        return False

class VaultLogItem(Collectible):
    """A collectible that represents a log entry from the Architect's Vault."""
    def __init__(self, x, y, log_id, *, asset_manager):
        self.log_id = log_id
        item_size = (int(get_setting("gameplay", "TILE_SIZE", 80) * 0.4), int(get_setting("gameplay", "TILE_SIZE", 80) * 0.5))

        # Create a simple icon for the vault log
        icon_surface = Surface(item_size, SRCALPHA)
        draw_rect(icon_surface, (200, 200, 50, 50), icon_surface.get_rect(), border_radius=3)
        font = Font(None, int(item_size[1] * 0.7))
        text_surf = font.render("!", True, (255, 255, 150))
        icon_surface.blit(text_surf, text_surf.get_rect(center=(item_size[0]//2, item_size[1]//2)))

        super().__init__(x, y, base_color=GOLD, size=item_size, thickness=2, original_icon_surface=icon_surface, is_rectangular=True)
        self.icon_rotation_speed = 0  # Logs don't need to spin

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected and hasattr(game_controller_instance, 'event_manager'):
            self.collected = True
            
            from hyperdrone_core.game_events import ItemCollectedEvent
            event = ItemCollectedEvent(item_id=self.log_id, item_type='vault_log')
            game_controller_instance.event_manager.dispatch(event)
            
            game_controller_instance.play_sound('collect_fragment')
            game_controller_instance.set_story_message(f"Vault Log '{self.log_id}' Acquired.")
            return True
        return False

class CorruptedLogItem(Collectible):
    """A collectible that represents a piece of lore or a story objective."""
    def __init__(self, x, y, log_id, *, asset_manager):
        self.log_id = log_id
        item_size = (int(get_setting("gameplay", "TILE_SIZE", 80) * 0.4), int(get_setting("gameplay", "TILE_SIZE", 80) * 0.5))

        # Create a simple icon for the corrupted log
        icon_surface = Surface(item_size, SRCALPHA)
        draw_rect(icon_surface, (50, 255, 150, 50), icon_surface.get_rect(), border_radius=3)
        font = Font(None, int(item_size[1] * 0.7))
        text_surf = font.render("?", True, (150, 255, 200))
        icon_surface.blit(text_surf, text_surf.get_rect(center=(item_size[0]//2, item_size[1]//2)))

        super().__init__(x, y, base_color=DARK_PURPLE, size=item_size, thickness=2, original_icon_surface=icon_surface, is_rectangular=True)
        self.icon_rotation_speed = 0 # Logs don't need to spin

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected and hasattr(game_controller_instance, 'event_manager'):
            self.collected = True
            
            from hyperdrone_core.game_events import ItemCollectedEvent
            event = ItemCollectedEvent(item_id=self.log_id, item_type='corrupted_log')
            game_controller_instance.event_manager.dispatch(event)
            
            game_controller_instance.play_sound('collect_fragment')
            game_controller_instance.set_story_message(f"Corrupted Log '{self.log_id}' Acquired.")
            return True
        return False

class QuantumCircuitryItem(Collectible):
    """The main objective collectible for the Harvest Chamber (Chapter 4)."""
    def __init__(self, x, y, *, asset_manager):
        self.item_id = "quantum_circuitry"
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        item_size = int(tile_size * 0.8)

        # Create a unique icon for the Quantum Circuitry
        icon_surface = Surface((item_size, item_size), SRCALPHA)
        # A series of concentric, glowing blue rectangles
        for i in range(4):
            rect_size = item_size * (1 - i * 0.2)
            alpha = 200 - i * 40
            color = (*LIGHT_BLUE[:3], alpha)
            rect = Rect(0, 0, rect_size, rect_size)
            rect.center = (item_size // 2, item_size // 2)
            draw_rect(icon_surface, color, rect, 2, border_radius=3)
        
        super().__init__(x, y, base_color=CYAN, size=item_size, thickness=4, original_icon_surface=icon_surface, is_rectangular=True)
        self.icon_rotation_speed = 0.5 # A slow, steady spin

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected and hasattr(game_controller_instance, 'event_manager'):
            self.collected = True
            from hyperdrone_core.game_events import ItemCollectedEvent
            event = ItemCollectedEvent(item_id=self.item_id, item_type='quantum_circuitry')
            game_controller_instance.event_manager.dispatch(event)
            game_controller_instance.play_sound('level_up')
            game_controller_instance.set_story_message("Quantum Circuitry Payload Secured!", 5000)
            return True
        return False

class AncientAlienTerminal(Sprite):
    def __init__(self, x, y, *, asset_manager):
        super().__init__()
        self.asset_manager = asset_manager
        self.item_id = "ancient_alien_terminal_puzzle_trigger"; self.interacted = False
        self.image_asset_key = "ancient_terminal_sprite_img"; 
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.size = (int(tile_size * 0.8), int(tile_size * 1.0))
        self.original_image = self.asset_manager.get_image(self.image_asset_key)
        if self.original_image:
            self.original_image = smoothscale(self.original_image, self.size)
            from pygame import BLEND_RGBA_ADD
            self.active_image = self.original_image.copy(); self.active_image.fill((0, 50, 0, 100), special_flags=BLEND_RGBA_ADD)
        else:
            self.original_image = self.asset_manager._create_fallback_surface(size=self.size, color=ARCHITECT_VAULT_WALL_COLOR, text="TERM", text_color=WHITE)
            self.active_image = self.original_image
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y)) if self.image else Rect(x - self.size[0]//2, y - self.size[1]//2, self.size[0], self.size[1])

    def interact(self, game_controller_instance):
        if not self.interacted:
            self.interacted = True; self.image = self.active_image
            if hasattr(game_controller_instance, 'puzzle_controller'):
                game_controller_instance.puzzle_controller.start_ring_puzzle(self)
            if hasattr(game_controller_instance, 'play_sound'): game_controller_instance.play_sound('ui_confirm')
            return True
        return False

    def update(self): pass
    
    def draw(self, surface, camera=None):
        if not self.image or not self.rect: return
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            if self.image.get_size() != screen_rect.size and screen_rect.width > 0 and screen_rect.height > 0:
                surface.blit(smoothscale(self.image, screen_rect.size), screen_rect)
            else: surface.blit(self.image, screen_rect)
        else: surface.blit(self.image, self.rect)

class GlyphTabletItem(Collectible):
    def __init__(self, x, y, tablet_id, *, asset_manager, icon_filename=None):
        self.tablet_id = tablet_id
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        item_size_tuple = (tile_size * 0.45, tile_size * 0.35)
        loaded_icon = asset_manager.get_image(f"glyph_tablet_{tablet_id}_icon") if not icon_filename else asset_manager.get_image(icon_filename)
        if loaded_icon is None:
            font = asset_manager.get_font("ui_emoji_general", int(item_size_tuple[1] * 0.7)) or Font(None, int(item_size_tuple[1] * 0.7))
            text_surf = font.render({"alpha": "α", "beta": "β", "gamma": "γ"}.get(tablet_id, "?"), True, CYAN)
            loaded_icon = Surface(text_surf.get_size(), SRCALPHA); loaded_icon.blit(text_surf, (0,0))
        super().__init__(x, y, base_color=CYAN, size=item_size_tuple, thickness=2, original_icon_surface=loaded_icon, is_rectangular=True)
        self.icon_rotation_speed = 0

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected: self.collected = True; return True
        return False

class WeaponsUpgradeShopItem(Collectible):
    def __init__(self, x, y, *, asset_manager):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        shop_size = int(tile_size * 1.2)
        loaded_original_icon = asset_manager.get_image("WEAPONS_UPGRADE_SHOP")
        if loaded_original_icon:
            loaded_original_icon = scale(loaded_original_icon, (shop_size, shop_size))
        super().__init__(x, y, base_color=PURPLE, size=shop_size, thickness=0, original_icon_surface=loaded_original_icon)
        self.icon_rotation_speed = 0  # Shop doesn't rotate
        self.pulse_speed_factor = 0  # No pulsing animation
        self.pulse_radius_amplitude = 0  # No pulse effect

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            # Mark shop as used for current level
            current_level = game_controller_instance.level_manager.level
            if current_level == 2:
                game_controller_instance.weapon_shop_used_level_2 = True
            elif current_level == 7:
                game_controller_instance.weapon_shop_used_level_7 = True
            # Launch weapons upgrade shop
            if hasattr(game_controller_instance, 'state_manager'):
                game_controller_instance.state_manager.set_state("WeaponsUpgradeShopState")
            if hasattr(game_controller_instance, 'play_sound'):
                game_controller_instance.play_sound('ui_confirm')
            return True
        return False

class ArchitectEchoItem(Collectible):
    def __init__(self, x, y, echo_id, associated_lore_id, *, asset_manager, icon_char="◈"):
        self.echo_id, self.associated_lore_id = echo_id, associated_lore_id
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        item_size = tile_size * 0.35
        font = asset_manager.get_font("ui_emoji_general", int(item_size * 0.7)) or Font(None, int(item_size*0.7))
        text_surf = font.render(icon_char, True, WHITE)
        icon_surface = Surface(text_surf.get_size(), SRCALPHA); icon_surface.blit(text_surf, (0,0))
        super().__init__(x, y, base_color=(100, 220, 255, 180), size=item_size, thickness=2, original_icon_surface=icon_surface, is_rectangular=False)
        self.icon_rotation_speed, self.pulse_speed_factor, self.pulse_radius_amplitude, self.bob_amplitude = 0.5, 0.008, self.base_draw_radius*0.4, 6

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            if self.associated_lore_id and hasattr(game_controller_instance, 'drone_system'):
                if game_controller_instance.drone_system.unlock_lore_entry_by_id(self.associated_lore_id):
                    if lore := game_controller_instance.drone_system.get_lore_entry_details(self.associated_lore_id):
                        game_controller_instance.set_story_message(f"ARCHITECT'S ECHO: \"{lore.get('echo_message', 'Data Fragment Decrypted')}\"")
            if hasattr(game_controller_instance, 'play_sound'): game_controller_instance.play_sound('collect_fragment', 0.7)
            return True
        return False

class CoreFragmentAssemblerItem(Collectible):
    """A special item that combines the 4 elemental core fragments."""
    def __init__(self, x, y, *, asset_manager):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        item_size = int(tile_size * 0.6)
        
        # Create a unique icon with 4 colored segments representing the fragments
        icon_surface = Surface((item_size, item_size), SRCALPHA)
        center = item_size // 2
        quarter_size = item_size // 4
        
        # Draw 4 colored quarters representing fire, water, earth, air
        colors = [(255, 100, 100), (100, 150, 255), (150, 100, 50), (200, 255, 200)]  # Fire, Water, Earth, Air
        for i, color in enumerate(colors):
            angle_start = i * 90
            quarter_rect = Rect(0, 0, quarter_size, quarter_size)
            if i == 0:  # Top-left
                quarter_rect.topleft = (center - quarter_size, center - quarter_size)
            elif i == 1:  # Top-right
                quarter_rect.topleft = (center, center - quarter_size)
            elif i == 2:  # Bottom-left
                quarter_rect.topleft = (center - quarter_size, center)
            else:  # Bottom-right
                quarter_rect.topleft = (center, center)
            draw_rect(icon_surface, color, quarter_rect)
        
        # Add a central circle
        circle(icon_surface, WHITE, (center, center), quarter_size // 2, 2)
        
        super().__init__(x, y, base_color=PURPLE, size=item_size, thickness=3, original_icon_surface=icon_surface)
        self.icon_rotation_speed = 1.0

    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            if hasattr(game_controller_instance, 'drone_system'):
                # Check if player has all 4 core fragments and combine them
                fragments = ['core_fragment_fire', 'core_fragment_water', 'core_fragment_earth', 'core_fragment_air']
                if all(game_controller_instance.drone_system.has_core_fragment(frag) for frag in fragments):
                    game_controller_instance.set_story_message("Core Fragments Combined! Ultimate Power Unlocked!", 5000)
                    if hasattr(game_controller_instance, 'play_sound'):
                        game_controller_instance.play_sound('level_up', 1.0)
                else:
                    game_controller_instance.set_story_message("Core Fragment Assembler acquired. Collect all 4 elemental fragments to use.", 5000)
                    if hasattr(game_controller_instance, 'play_sound'):
                        game_controller_instance.play_sound('collect_fragment', 0.8)
            return True
        return False
