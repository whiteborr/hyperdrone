# hyperdrone_core/asset_manager.py
import pygame
import os
import logging

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
        if not isinstance(relative_path, str):
            return relative_path
        return os.path.join(self.base_asset_path, relative_path)

    def load_image(self, relative_path, key=None, use_convert_alpha=True, colorkey=None):
        """Loads an image and caches its original, unscaled version."""
        if key is None: key = relative_path
        if key in self.images: return self.images[key]
        full_path = self._get_full_path(relative_path)
        if not os.path.exists(full_path):
            logger.error(f"AssetManager: Image file not found at '{full_path}' for key '{key}'.")
            return None
        try:
            image = pygame.image.load(full_path)
            image = image.convert_alpha() if use_convert_alpha else image.convert()
            if colorkey: image.set_colorkey(colorkey)
            self.images[key] = image
            return image
        except pygame.error as e:
            logger.error(f"AssetManager: Pygame error loading image '{full_path}': {e}")
            return None

    def get_image(self, key, scale_to_size=None, default_surface_params=None):
        original_image = self.images.get(key)
        
        if not original_image:
            # If key not in cache, the key IS the path for non-manifest assets.
            # This prevents treating a key name like a file path.
            if os.path.exists(self._get_full_path(key)):
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
            
            scaled_image = pygame.transform.smoothscale(original_image, (scaled_w, scaled_h))
            self.images[scaled_key] = scaled_image
            return scaled_image
        except (ValueError, TypeError, pygame.error) as e:
            logger.error(f"AssetManager: Error scaling image for key '{key}' to {scale_to_size}: {e}")
            return original_image
        
    def _create_fallback_surface(self, size=(32,32), color=(128,0,128), text=None, text_color=(255,255,255), font_key=None, font_size=20):
        surface = pygame.Surface(size, pygame.SRCALPHA); surface.fill(color)
        if text:
            try:
                font = self.get_font(font_key, font_size) if font_key else pygame.font.Font(None, font_size)
                if not font: font = pygame.font.Font(None, font_size)
                text_surf = font.render(str(text), True, text_color)
                surface.blit(text_surf, text_surf.get_rect(center=(size[0]//2, size[1]//2)))
            except Exception as e: logger.error(f"AssetManager: Error rendering fallback text '{text}': {e}")
        pygame.draw.rect(surface, (200,200,200), surface.get_rect(), 1); return surface

    def load_sound(self, relative_path, key=None):
        if key is None: key = relative_path
        if key in self.sounds: return self.sounds[key]
        full_path = self._get_full_path(relative_path)
        if not os.path.exists(full_path):
            logger.error(f"AssetManager: Sound file not found: '{full_path}'.")
            return None
        try:
            sound = pygame.mixer.Sound(full_path); self.sounds[key] = sound; return sound
        except pygame.error as e: logger.error(f"AssetManager: Error loading sound '{full_path}': {e}"); return None

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
            font = pygame.font.Font(full_path, size)
            self.fonts[font_cache_key] = font
            logger.debug(f"AssetManager: Loaded font '{full_path or 'System Font'}' size {size} as '{font_cache_key}'.")
            return font
        except pygame.error as e:
            logger.error(f"AssetManager: Pygame error loading font '{full_path or 'System Font'}' size {size}: {e}")
            try:
                logger.warning(f"AssetManager: Attempting fallback to system font for key '{base_key}' size {size}.")
                font = pygame.font.Font(None, size)
                self.fonts[font_cache_key] = font
                return font
            except pygame.error as e_sys:
                logger.error(f"AssetManager: Pygame error loading system font as fallback: {e_sys}")
                return None

    def get_font(self, base_key, size):
        """Retrieves a pre-loaded font by its base key and size."""
        cache_key = f"{base_key}_{size}"
        font = self.fonts.get(cache_key)
        if not font:
            logger.warning(f"AssetManager: Font '{cache_key}' not found. Check manifest or use load_font first.")
            try:
                return pygame.font.Font(None, size)
            except pygame.error:
                return None
        return font

    def add_music_path(self, key, relative_path):
        self.music_paths[key] = relative_path

    def get_music_path(self, key):
        relative_path = self.music_paths.get(key)
        if relative_path: return self._get_full_path(relative_path)
        logger.warning(f"AssetManager: Music path for key '{key}' not found.")
        return None

    def preload_manifest(self, manifest_dict):
        logger.info("AssetManager: Starting preload from manifest...")
        if "images" in manifest_dict:
            for key, config in manifest_dict["images"].items():
                if not config.get("path"): logger.error(f"AssetManager (Manifest): Path missing for image key '{key}'."); continue
                self.load_image(config["path"], key=key)
        
        if "sounds" in manifest_dict:
            for key, path in manifest_dict["sounds"].items():
                if not path: logger.error(f"AssetManager (Manifest): Path missing for sound key '{key}'."); continue
                self.load_sound(path, key=key)
        
        # <<< CORRECTED FONT PRELOADING LOGIC >>>
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
                if not path: logger.error(f"AssetManager (Manifest): Path missing for music key '{key}'."); continue
                self.add_music_path(key, path)
                
        logger.info("AssetManager: Preload from manifest complete.")
