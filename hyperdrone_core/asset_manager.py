# hyperdrone_core/asset_manager.py
from pygame.image import load as image_load
from pygame.mixer import Sound
from pygame.font import Font
from pygame.transform import smoothscale
from pygame.draw import rect as draw_rect
from pygame import Surface, SRCALPHA, error as pygame_error
from os.path import dirname, abspath, join, exists, normpath, splitext
from logging import getLogger, error, warning, info
from settings_manager import get_asset_path

logger = getLogger(__name__)

class AssetManager:
    def __init__(self, base_asset_folder_name="assets"):
        script_dir = dirname(abspath(__file__))
        project_root = dirname(script_dir)
        self.base_path = join(project_root, base_asset_folder_name)
        
        self.images = {}
        self.sounds = {}
        self.fonts = {}
        self.music_paths = {}

        if not exists(self.base_path):
            error(f"Base asset path does not exist: '{self.base_path}'")
        info(f"AssetManager initialized: '{self.base_path}'")

    def _get_full_path(self, relative_path):
        if not isinstance(relative_path, str) or not splitext(relative_path)[1]:
            return None
        return normpath(join(self.base_path, relative_path))

    def load_image(self, relative_path, key=None, use_convert_alpha=True, colorkey=None):
        if key is None: 
            key = relative_path
        if key in self.images: 
            return self.images[key]
        
        full_path = self._get_full_path(relative_path)
        if not full_path or not exists(full_path):
            error(f"Image not found: '{full_path}' for key '{key}'")
            return None
            
        try:
            image = image_load(full_path)
            image = image.convert_alpha() if use_convert_alpha else image.convert()
            if colorkey: 
                image.set_colorkey(colorkey)
            self.images[key] = image
            return image
        except pygame_error as e:
            error(f"Error loading image '{full_path}': {e}")
            return None

    def get_image(self, key, scale_to_size=None, default_surface_params=None):
        image = self.images.get(key)
        
        if not image:
            from settings_manager import settings_manager
            manifest_path = settings_manager.get_asset_path("images", key)
            if manifest_path:
                image = self.load_image(manifest_path, key)
            elif exists(self._get_full_path(key) or ""):
                image = self.load_image(key)
            else:
                warning(f"Image not found: '{key}'")
                if default_surface_params: 
                    return self._create_fallback_surface(**default_surface_params)
                return None

        if not scale_to_size:
            return image

        try:
            scaled_key = f"{key}_scaled_{int(scale_to_size[0])}x{int(scale_to_size[1])}"
            if scaled_key in self.images: 
                return self.images[scaled_key]
            
            w, h = int(scale_to_size[0]), int(scale_to_size[1])
            if w <= 0 or h <= 0: 
                raise ValueError("Scaling dimensions must be positive")
            
            scaled_image = smoothscale(image, (w, h))
            self.images[scaled_key] = scaled_image
            return scaled_image
        except (ValueError, TypeError, pygame_error) as e:
            error(f"Error scaling image '{key}' to {scale_to_size}: {e}")
            return image
        
    def _create_fallback_surface(self, size=(32,32), color=(128,0,128), text=None, text_color=(255,255,255), font_key=None, font_size=20):
        surface = Surface(size, SRCALPHA)
        surface.fill(color)
        
        if text:
            try:
                font = self.get_font(font_key, font_size) if font_key else Font(None, font_size)
                if not font: 
                    font = Font(None, font_size)
                text_surf = font.render(str(text), True, text_color)
                surface.blit(text_surf, text_surf.get_rect(center=(size[0]//2, size[1]//2)))
            except Exception as e: 
                error(f"Error rendering fallback text '{text}': {e}")
        
        draw_rect(surface, (200,200,200), surface.get_rect(), 1)
        return surface

    def load_sound(self, relative_path, key=None):
        if key is None: 
            key = relative_path
        if key in self.sounds: 
            return self.sounds[key]
        
        full_path = self._get_full_path(relative_path)
        if not full_path or not exists(full_path):
            error(f"Sound not found: '{full_path}'")
            return None
            
        try:
            sound = Sound(full_path)
            self.sounds[key] = sound
            return sound
        except pygame_error as e: 
            error(f"Error loading sound '{full_path}': {e}")
            return None

    def get_sound(self, key):
        sound = self.sounds.get(key)
        if not sound: 
            warning(f"Sound not found: '{key}'")
        return sound

    def load_font(self, relative_path, size, base_key):
        cache_key = f"{base_key}_{size}"
        if cache_key in self.fonts:
            return self.fonts[cache_key]

        full_path = self._get_full_path(relative_path) if relative_path else None
        
        try:
            font = Font(full_path, size)
            self.fonts[cache_key] = font
            return font
        except (pygame_error, FileNotFoundError) as e:
            error(f"Error loading font '{full_path or 'System Font'}' size {size}: {e}")
            try:
                font = Font(None, size)
                self.fonts[cache_key] = font
                return font
            except pygame_error as e_sys:
                error(f"Error loading system font fallback: {e_sys}")
                return None

    def get_font(self, base_key, size):
        cache_key = f"{base_key}_{size}"
        font = self.fonts.get(cache_key)
        if not font:
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
            return self._get_full_path(relative_path)
        warning(f"Music path not found: '{key}'")
        return None
    
    def get_weapon_icon(self, weapon_mode):
        from settings_manager import settings_manager
        weapon_icons = settings_manager.get_weapon_icon_paths()
        icon_path = weapon_icons.get(str(weapon_mode))
        if icon_path:
            return self.get_image(icon_path.replace("assets/", "").replace("\\", "/"))
        return None

    def preload_manifest(self, manifest_dict):
        info("Starting asset preload...")
        
        if "images" in manifest_dict:
            for key, config in manifest_dict["images"].items():
                if not config.get("path"): 
                    continue
                self.load_image(config["path"], key=key)
        
        if "sounds" in manifest_dict:
            for key, path in manifest_dict["sounds"].items():
                if path: 
                    self.load_sound(path, key=key)
        
        if "fonts" in manifest_dict:
            for base_key, config in manifest_dict["fonts"].items():
                font_path = config.get("path")
                sizes = config.get("sizes", [])
                if isinstance(sizes, list):
                    for size in sizes:
                        self.load_font(font_path, size, base_key=base_key)

        if "music" in manifest_dict:
            for key, path in manifest_dict["music"].items():
                if path: 
                    self.add_music_path(key, path)
                
        info("Asset preload complete")
        
    def preload_game_assets(self):
        from drone_management.drone_configs import DRONE_DATA
        from settings_manager import settings_manager
        
        # Core assets
        images = {
            "ring_ui_icon": get_asset_path("images", "RING_UI_ICON"),
            "ring_ui_icon_empty": get_asset_path("images", "RING_UI_ICON_EMPTY"),
            "menu_logo_hyperdrone": get_asset_path("images", "MENU_LOGO"),
            "core_fragment_empty_icon": get_asset_path("images", "CORE_FRAGMENT_EMPTY_ICON"),
            "reactor_hud_icon_key": get_asset_path("images", "REACTOR_HUD_ICON"),
            "core_reactor_image": get_asset_path("images", "CORE_REACTOR_IMAGE"),
            "shield_powerup_icon": get_asset_path("images", "SHIELD_POWERUP_ICON"),
            "speed_boost_powerup_icon": get_asset_path("images", "SPEED_BOOST_POWERUP_ICON"),
            "weapon_upgrade_powerup_icon": get_asset_path("images", "WEAPON_UPGRADE_POWERUP_ICON"),
            "regular_enemy_sprite_key": get_asset_path("sprites", "REGULAR_ENEMY_SPRITE_PATH"),
            "prototype_drone_sprite_key": get_asset_path("sprites", "PROTOTYPE_DRONE_SPRITE_PATH"),
            "sentinel_drone_sprite_key": get_asset_path("sprites", "SENTINEL_DRONE_SPRITE_PATH"),
            "maze_guardian_sprite_key": get_asset_path("sprites", "MAZE_GUARDIAN_SPRITE_PATH"),
            "ability_icon_placeholder": "images/ui/ability_icon_placeholder.png",
        }
        
        # Defense drones
        for i in range(1, 6):
            images[f"defense_drone_{i}_sprite_key"] = get_asset_path("images", f"DEFENSE_DRONE_{i}_SPRITE")
        
        # Lore scenes
        for i in range(1, 5):
            images[f"images/lore/scene{i}.png"] = get_asset_path("images", f"LORE_SCENE_{i}")
        
        # Weapon-specific drones
        drone_types = ["default", "tri_shot", "rapid_single", "rapid_tri_shot", "big_shot", 
                      "bounce", "pierce", "heatseeker", "heatseeker_plus_bullets", "lightning"]
        for drone_type in drone_types:
            images[f"drone_{drone_type}"] = f"images/drones/drone_{drone_type}.png"
        
        # Turrets
        turret_types = ["default", "tri_shot", "rapid_single", "rapid_tri", "big_shot", 
                       "bounce", "pierce", "heatseeker", "heatseeker_plus", "lightning"]
        for turret_type in turret_types:
            images[f"turret_{turret_type}"] = f"images/level_elements/turret_{turret_type}.png"
        
        sounds = {
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
            'lore_unlock': "sounds/lore_unlock.ogg",
        }
        
        fonts = {
            "ui_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [16, 20, 24, 28, 32, 56]},
            "ui_values": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [30]},
            "small_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [24]},
            "medium_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [24, 36, 48]},
            "large_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [24, 48, 52, 74]},
            "title_text": {"path": get_asset_path("fonts", "UI_TEXT_FONT"), "sizes": [90]},
        }
        
        music = {
            "menu_theme": get_asset_path("music", "MENU_THEME_MUSIC"),
            "gameplay_theme": get_asset_path("music", "GAMEPLAY_THEME_MUSIC"),
            "defense_theme": get_asset_path("music", "DEFENSE_THEME_MUSIC"),
            "boss_theme": get_asset_path("music", "BOSS_THEME_MUSIC"),
            "corrupted_theme": get_asset_path("music", "CORRUPTED_THEME_MUSIC"),
            "shmup_theme": get_asset_path("music", "SHMUP_THEME_MUSIC"),
            "architect_vault_theme": get_asset_path("music", "ARCHITECT_VAULT_THEME_MUSIC")
        }
        
        # Add core fragment icons
        core_fragments = settings_manager.get_core_fragment_details()
        if core_fragments:
            for _, details in core_fragments.items():
                if details and "id" in details and "icon_filename" in details:
                    images[f"{details['id']}_icon"] = details['icon_filename']

        # Add drone sprites
        for drone_id, config in DRONE_DATA.items():
            if config.get("ingame_sprite_path"): 
                images[f"drone_{drone_id}_ingame_sprite"] = config["ingame_sprite_path"].replace("assets/", "")
            if config.get("icon_path"):
                images[f"drone_{drone_id}_hud_icon"] = config["icon_path"].replace("assets/", "")

        # Add weapon icons
        weapon_icons = settings_manager.get_weapon_icon_paths()
        for weapon_path in weapon_icons.values():
            if weapon_path and isinstance(weapon_path, str):
                asset_key = weapon_path.replace("assets/", "").replace("\\", "/")
                images[asset_key] = asset_key
        
        # Create manifest and preload
        manifest = {
            "images": {k: {"path": v, "alpha": True} for k, v in images.items() if v},
            "sounds": sounds,
            "fonts": fonts,
            "music": music
        }
        
        self.preload_manifest(manifest)
        info("All game assets preloaded")