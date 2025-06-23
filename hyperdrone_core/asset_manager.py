# hyperdrone_core/asset_manager.py
from pygame.image import load as image_load
from pygame.mixer import Sound
from pygame.font import Font
from pygame.transform import smoothscale
from pygame.draw import rect as draw_rect
from pygame import Surface, SRCALPHA, error as pygame_error
import os
import logging
from settings_manager import get_asset_path, get_setting

logger = logging.getLogger(__name__)

class AssetManager:
    """
    Manages loading and caching of game assets like images, sounds, and fonts.
    """
    def __init__(self, base_asset_folder_name="assets"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        self.base_asset_path = os.path.join(project_root, base_asset_folder_name)
        
        self.images = {}
        self.sounds = {}
        self.fonts = {}
        self.music_paths = {}

        if not os.path.exists(self.base_asset_path):
            logger.error(f"AssetManager: CRITICAL - Base asset path does not exist at '{self.base_asset_path}'!")
        logger.info(f"AssetManager initialized with absolute base path: '{self.base_asset_path}'")

    def _get_full_path(self, relative_path):
        # A simple check to ensure the relative_path is a string and could be a path
        if not isinstance(relative_path, str) or not os.path.splitext(relative_path)[1]:
            # If it's not a string or has no file extension, it's probably not a valid asset path.
            # This will prevent emojis or other non-path strings from being processed.
            logger.warning(f"AssetManager: '{relative_path}' was passed as a relative path but is not a valid file path string. Skipping.")
            return None

        # Join the paths and normalize them for the current OS to fix mixed separators
        full_path = os.path.join(self.base_asset_path, relative_path)
        return os.path.normpath(full_path)

    def load_image(self, relative_path, key=None, use_convert_alpha=True, colorkey=None):
        """Loads an image and caches its original, unscaled version."""
        if key is None: key = relative_path
        if key in self.images: return self.images[key]
        
        full_path = self._get_full_path(relative_path)
        if full_path is None: # The check in _get_full_path determined it's not a valid path
            return None

        if not os.path.exists(full_path):
            logger.error(f"AssetManager: Image file not found at '{full_path}' for key '{key}'.")
            return None
        try:
            image = image_load(full_path)
            image = image.convert_alpha() if use_convert_alpha else image.convert()
            if colorkey: image.set_colorkey(colorkey)
            self.images[key] = image
            return image
        except pygame_error as e:
            logger.error(f"AssetManager: Pygame error loading image '{full_path}': {e}")
            return None

    def get_image(self, key, scale_to_size=None, default_surface_params=None):
        original_image = self.images.get(key)
        
        if not original_image:
            # Check if it's a manifest key first
            from settings_manager import settings_manager
            manifest_path = settings_manager.get_asset_path("images", key)
            if manifest_path:
                original_image = self.load_image(manifest_path, key)
            elif os.path.exists(self._get_full_path(key) or ""):
                original_image = self.load_image(key)
            else:
                logger.warning(f"AssetManager: Image with key or path '{key}' not found.")
                if default_surface_params: return self._create_fallback_surface(**default_surface_params)
                return None

        if not scale_to_size:
            return original_image

        try:
            scaled_key = f"{key}_scaled_{int(scale_to_size[0])}x{int(scale_to_size[1])}"
            if scaled_key in self.images: return self.images[scaled_key]
            
            scaled_w, scaled_h = int(scale_to_size[0]), int(scale_to_size[1])
            if scaled_w <= 0 or scaled_h <= 0: raise ValueError("Image scaling dimensions must be positive.")
            
            scaled_image = smoothscale(original_image, (scaled_w, scaled_h))
            self.images[scaled_key] = scaled_image
            return scaled_image
        except (ValueError, TypeError, pygame_error) as e:
            logger.error(f"AssetManager: Error scaling image for key '{key}' to {scale_to_size}: {e}")
            return original_image
        
    def _create_fallback_surface(self, size=(32,32), color=(128,0,128), text=None, text_color=(255,255,255), font_key=None, font_size=20):
        surface = Surface(size, SRCALPHA); surface.fill(color)
        if text:
            try:
                font = self.get_font(font_key, font_size) if font_key else Font(None, font_size)
                if not font: font = Font(None, font_size)
                text_surf = font.render(str(text), True, text_color)
                surface.blit(text_surf, text_surf.get_rect(center=(size[0]//2, size[1]//2)))
            except Exception as e: logger.error(f"AssetManager: Error rendering fallback text '{text}': {e}")
        draw_rect(surface, (200,200,200), surface.get_rect(), 1); return surface

    def load_sound(self, relative_path, key=None):
        if key is None: key = relative_path
        if key in self.sounds: return self.sounds[key]
        
        full_path = self._get_full_path(relative_path)
        if full_path is None:
            return None

        if not os.path.exists(full_path):
            logger.error(f"AssetManager: Sound file not found: '{full_path}'.")
            return None
        try:
            sound = Sound(full_path); self.sounds[key] = sound; return sound
        except pygame_error as e: logger.error(f"AssetManager: Error loading sound '{full_path}': {e}"); return None

    def get_sound(self, key):
        sound = self.sounds.get(key)
        if not sound: logger.warning(f"AssetManager: Sound with key '{key}' not found.")
        return sound

    def load_font(self, relative_path, size, base_key):
        """Loads a font of a specific size and caches it using a composite key."""
        font_cache_key = f"{base_key}_{size}"
        if font_cache_key in self.fonts:
            return self.fonts[font_cache_key]

        full_path = self._get_full_path(relative_path) if relative_path else None
        
        try:
            # Use full_path directly, which can be None for system default font
            font = Font(full_path, size)
            self.fonts[font_cache_key] = font
            logger.debug(f"AssetManager: Loaded font '{full_path or 'System Font'}' size {size} as '{font_cache_key}'.")
            return font
        except (pygame_error, FileNotFoundError) as e: # Catch FileNotFoundError as well
            logger.error(f"AssetManager: Pygame error loading font '{full_path or 'System Font'}' size {size}: {e}")
            try:
                logger.warning(f"AssetManager: Attempting fallback to system font for key '{base_key}' size {size}.")
                font = Font(None, size)
                self.fonts[font_cache_key] = font
                return font
            except pygame_error as e_sys:
                logger.error(f"AssetManager: Pygame error loading system font as fallback: {e_sys}")
                return None

    def get_font(self, base_key, size):
        """Retrieves a pre-loaded font by its base key and size."""
        cache_key = f"{base_key}_{size}"
        font = self.fonts.get(cache_key)
        if not font:
            logger.warning(f"AssetManager: Font '{cache_key}' not found. Check manifest or use load_font first.")
            try:
                return Font(None, size)
            except pygame_error:
                return None
        return font

    def add_music_path(self, key, relative_path):
        self.music_paths[key] = relative_path

    def get_music_path(self, key):
        relative_path = self.music_paths.get(key)
        if relative_path:
            full_path = self._get_full_path(relative_path)
            return full_path
        logger.warning(f"AssetManager: Music path for key '{key}' not found.")
        return None
    
    def get_weapon_icon(self, weapon_mode):
        """Get weapon icon by weapon mode ID"""
        from settings_manager import settings_manager
        weapon_icons = settings_manager.get_weapon_icon_paths()
        icon_path = weapon_icons.get(str(weapon_mode))
        if icon_path:
            return self.get_image(icon_path.replace("assets/", "").replace("\\", "/"))
        return None

    def preload_manifest(self, manifest_dict):
        logger.info("AssetManager: Starting preload from manifest...")
        if "images" in manifest_dict:
            for key, config in manifest_dict["images"].items():
                if not config.get("path"): 
                    logger.error(f"AssetManager (Manifest): Path missing for image key '{key}'."); continue
                self.load_image(config["path"], key=key)
        
        if "sounds" in manifest_dict:
            for key, path in manifest_dict["sounds"].items():
                if not path: 
                    logger.error(f"AssetManager (Manifest): Path missing for sound key '{key}'."); continue
                self.load_sound(path, key=key)
        
        if "fonts" in manifest_dict:
            for base_key, config in manifest_dict["fonts"].items():
                font_path = config.get("path")
                sizes_to_load = config.get("sizes", [])
                if not isinstance(sizes_to_load, list):
                    logger.error(f"AssetManager (Manifest): 'sizes' for font key '{base_key}' must be a list of integers.")
                    continue
                for size in sizes_to_load:
                    self.load_font(font_path, size, base_key=base_key)

        if "music" in manifest_dict:
            for key, path in manifest_dict["music"].items():
                if not path: 
                    logger.error(f"AssetManager (Manifest): Path missing for music key '{key}'."); continue
                self.add_music_path(key, path)
                
        logger.info("AssetManager: Preload from manifest complete.")
        
    def preload_game_assets(self):
        """Preloads all game assets needed for HYPERDRONE."""
        # Import locally to avoid circular imports
        from drone_management.drone_configs import DRONE_DATA
        from settings_manager import settings_manager
        
        asset_manifest = {
            "images": {
                "ring_ui_icon": {"path": get_asset_path("images", "RING_UI_ICON"), "alpha": True},
                "ring_ui_icon_empty": {"path": get_asset_path("images", "RING_UI_ICON_EMPTY"), "alpha": True},
                "menu_logo_hyperdrone": {"path": get_asset_path("images", "MENU_LOGO"), "alpha": True},
                "core_fragment_empty_icon": {"path": get_asset_path("images", "CORE_FRAGMENT_EMPTY_ICON"), "alpha": True},
                "reactor_hud_icon_key": {"path": get_asset_path("images", "REACTOR_HUD_ICON"), "alpha": True},
                "core_reactor_image": {"path": get_asset_path("images", "CORE_REACTOR_IMAGE"), "alpha": True},
                "shield_powerup_icon": {"path": get_asset_path("images", "SHIELD_POWERUP_ICON"), "alpha": True},
                "speed_boost_powerup_icon": {"path": get_asset_path("images", "SPEED_BOOST_POWERUP_ICON"), "alpha": True},
                "weapon_upgrade_powerup_icon": {"path": get_asset_path("images", "WEAPON_UPGRADE_POWERUP_ICON"), "alpha": True},
                "regular_enemy_sprite_key": {"path": get_asset_path("sprites", "REGULAR_ENEMY_SPRITE_PATH"), "alpha": True},
                "prototype_drone_sprite_key": {"path": get_asset_path("sprites", "PROTOTYPE_DRONE_SPRITE_PATH"), "alpha": True},
                "sentinel_drone_sprite_key": {"path": get_asset_path("sprites", "SENTINEL_DRONE_SPRITE_PATH"), "alpha": True},
                "maze_guardian_sprite_key": {"path": get_asset_path("sprites", "MAZE_GUARDIAN_SPRITE_PATH"), "alpha": True},
                "defense_drone_1_sprite_key": {"path": get_asset_path("images", "DEFENSE_DRONE_1_SPRITE"), "alpha": True},
                "defense_drone_2_sprite_key": {"path": get_asset_path("images", "DEFENSE_DRONE_2_SPRITE"), "alpha": True},
                "defense_drone_3_sprite_key": {"path": get_asset_path("images", "DEFENSE_DRONE_3_SPRITE"), "alpha": True},
                "defense_drone_4_sprite_key": {"path": get_asset_path("images", "DEFENSE_DRONE_4_SPRITE"), "alpha": True},
                "defense_drone_5_sprite_key": {"path": get_asset_path("images", "DEFENSE_DRONE_5_SPRITE"), "alpha": True},
                "images/lore/scene1.png": {"path": get_asset_path("images", "LORE_SCENE_1"), "alpha": True},
                "images/lore/scene2.png": {"path": get_asset_path("images", "LORE_SCENE_2"), "alpha": True},
                "images/lore/scene3.png": {"path": get_asset_path("images", "LORE_SCENE_3"), "alpha": True},
                "images/lore/scene4.png": {"path": get_asset_path("images", "LORE_SCENE_4"), "alpha": True},
                "ability_icon_placeholder": {"path": "images/ui/ability_icon_placeholder.png", "alpha": True},
                
                # Add weapon-specific drone sprites
                "drone_default": {"path": "images/drones/drone_default.png", "alpha": True},
                "drone_tri_shot": {"path": "images/drones/drone_tri_shot.png", "alpha": True},
                "drone_rapid_single": {"path": "images/drones/drone_rapid_single.png", "alpha": True},
                "drone_rapid_tri_shot": {"path": "images/drones/drone_rapid_tri_shot.png", "alpha": True},
                "drone_big_shot": {"path": "images/drones/drone_big_shot.png", "alpha": True},
                "drone_bounce": {"path": "images/drones/drone_bounce.png", "alpha": True},
                "drone_pierce": {"path": "images/drones/drone_pierce.png", "alpha": True},
                "drone_heatseeker": {"path": "images/drones/drone_heatseeker.png", "alpha": True},
                "drone_heatseeker_plus_bullets": {"path": "images/drones/drone_heatseeker_plus_bullets.png", "alpha": True},
                "drone_lightning": {"path": "images/drones/drone_lightning.png", "alpha": True},
                
                # Add turret images
                "turret_default": {"path": "images/level_elements/turret_default.png", "alpha": True},
                "turret_tri_shot": {"path": "images/level_elements/turret_tri_shot.png", "alpha": True},
                "turret_rapid_single": {"path": "images/level_elements/turret_rapid_single.png", "alpha": True},
                "turret_rapid_tri": {"path": "images/level_elements/turret_rapid_tri_shot.png", "alpha": True},
                "turret_big_shot": {"path": "images/level_elements/turret_big_shot.png", "alpha": True},
                "turret_bounce": {"path": "images/level_elements/turret_bounce.png", "alpha": True},
                "turret_pierce": {"path": "images/level_elements/turret_pierce.png", "alpha": True},
                "turret_heatseeker": {"path": "images/level_elements/turret_heatseeker.png", "alpha": True},
                "turret_heatseeker_plus": {"path": "images/level_elements/turret_heatseeker_plus_bullets.png", "alpha": True},
                "turret_lightning": {"path": "images/level_elements/turret_lightning.png", "alpha": True},
            },
            "sounds": {
                'collect_ring': get_asset_path("sounds", "COLLECT_RING_SOUND"),
                'weapon_upgrade_collect': get_asset_path("sounds", "WEAPON_UPGRADE_COLLECT_SOUND"),
                'collect_fragment': get_asset_path("sounds", "COLLECT_FRAGMENT_SOUND"),
                'shoot': get_asset_path("sounds", "SHOOT_SOUND"),
                'enemy_shoot': get_asset_path("sounds", "ENEMY_SHOOT_SOUND"),
                'crash': get_asset_path("sounds", "CRASH_SOUND"),
                'level_up': get_asset_path("sounds", "LEVEL_UP_SOUND"),
                'ui_select': get_asset_path("sounds", "UI_SELECT_SOUND"),
                'ui_confirm': get_asset_path("sounds", "UI_CONFIRM_SOUND"),
                'ui_denied': get_asset_path("sounds", "UI_DENIED_SOUND"),
                'missile_launch': get_asset_path("sounds", "MISSILE_LAUNCH_SOUND"),
                'prototype_drone_explode': get_asset_path("sounds", "PROTOTYPE_DRONE_EXPLODE_SOUND"),
                'turret_placement': get_asset_path("sounds", "TURRET_PLACE_SOUND"),
            },
            "fonts": {
                "ui_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [28, 24, 20, 16, 32, 56]},
                "ui_values": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [30]},
                "small_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [24]},
                "medium_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [48, 36]},
                "large_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [74, 52, 48]},
                "title_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [90]},
            },
            "music": {
                "menu_theme": get_asset_path("music", "MENU_THEME_MUSIC"),
                "gameplay_theme": get_asset_path("music", "GAMEPLAY_THEME_MUSIC"),
                "defense_theme": get_asset_path("music", "DEFENSE_THEME_MUSIC"),
                "boss_theme": get_asset_path("music", "BOSS_THEME_MUSIC"),
                "corrupted_theme": get_asset_path("music", "CORRUPTED_THEME_MUSIC"),
                "shmup_theme": get_asset_path("music", "SHMUP_THEME_MUSIC"),
                "architect_vault_theme": get_asset_path("music", "ARCHITECT_VAULT_THEME_MUSIC")
            }
        }
        
        # Add core fragment icons
        core_fragments = settings_manager.get_core_fragment_details()
        if core_fragments:
            for _, details in core_fragments.items():
                if details and "id" in details and "icon_filename" in details:
                    asset_manifest["images"][f"{details['id']}_icon"] = {"path": details['icon_filename']}

        # Add drone sprites
        for drone_id, config in DRONE_DATA.items():
            if config.get("ingame_sprite_path"): 
                asset_manifest["images"][f"drone_{drone_id}_ingame_sprite"] = {
                    "path": config["ingame_sprite_path"].replace("assets/", ""), 
                    "alpha": True
                }
            if config.get("icon_path"):
                asset_manifest["images"][f"drone_{drone_id}_hud_icon"] = {
                    "path": config["icon_path"].replace("assets/", ""), 
                    "alpha": True
                }

        # Add weapon mode icons
        weapon_icons = settings_manager.get_weapon_icon_paths()
            
        for weapon_path in weapon_icons.values():
            if weapon_path and isinstance(weapon_path, str):
                asset_key = weapon_path.replace("assets/", "").replace("\\", "/")
                asset_manifest["images"][asset_key] = {"path": asset_key, "alpha": True}
        
        self.preload_manifest(asset_manifest)
        logger.info("AssetManager: All game assets preloaded.")
