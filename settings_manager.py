# settings_manager.py
from json import load, dump
from os.path import join, exists, dirname
from os import makedirs
import logging

logger = logging.getLogger(__name__)

class SettingsManager:
    """
    Manages game settings loaded from JSON files and provides access to them.
    
    Centralized settings management system that loads configuration from JSON files
    and provides a clean API for accessing and modifying game parameters. Supports
    categorized settings, asset path management, and automatic saving of changes.
    
    Key Features:
    - Hierarchical settings organization by category
    - Asset manifest management for centralized asset paths
    - Automatic change tracking and saving
    - Default value support for missing settings
    - Type-safe setting access with fallbacks
    
    Attributes:
        settings (dict): Hierarchical dictionary of all game settings
        asset_manifest (dict): Dictionary mapping asset keys to file paths
        settings_modified (bool): Flag indicating if settings need saving
    """
    def __init__(self):
        self.settings = {}
        self.asset_manifest = {}
        self.settings_modified = False
        self._load_settings()
        self._load_asset_manifest()
        
    def _load_settings(self):
        """Load settings from settings.json"""
        try:
            settings_path = join("data", "settings.json")
            if exists(settings_path):
                with open(settings_path, 'r') as f:
                    self.settings = load(f)
                logger.info("Settings loaded successfully")
            else:
                logger.warning(f"Settings file not found at {settings_path}")
                self.settings = {}
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self.settings = {}
    
    def _load_asset_manifest(self):
        """Load asset paths from asset_manifest.json"""
        try:
            manifest_path = join("data", "asset_manifest.json")
            if exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    self.asset_manifest = load(f)
                logger.info("Asset manifest loaded successfully")
            else:
                logger.warning(f"Asset manifest file not found at {manifest_path}")
                self.asset_manifest = {}
        except Exception as e:
            logger.error(f"Error loading asset manifest: {e}")
            self.asset_manifest = {}
    
    def save_settings(self):
        """Save current settings to settings.json"""
        if not self.settings_modified:
            return
            
        try:
            settings_path = join("data", "settings.json")
            makedirs(dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w') as f:
                dump(self.settings, f, indent=2)
            logger.info("Settings saved successfully")
            self.settings_modified = False
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def get_setting(self, category, key, default=None):
        """
        Get a setting value from the specified category with fallback support.
        
        Provides safe access to hierarchical settings with automatic fallback
        to default values when settings are missing. This prevents crashes
        from missing configuration and allows for graceful degradation.
        
        Args:
            category (str): The settings category (e.g., 'display', 'gameplay', 'weapons')
            key (str): The setting key within the category
            default (Any, optional): Default value returned if setting is not found
            
        Returns:
            Any: The setting value if found, otherwise the default value
            
        Example:
            fps = settings_manager.get_setting("display", "FPS", 60)
            player_speed = settings_manager.get_setting("gameplay", "PLAYER_SPEED", 3.0)
        """
        if category in self.settings and key in self.settings[category]:
            return self.settings[category][key]
        return default
    
    def set_setting(self, category, key, value):
        """
        Set a setting value in the specified category.
        
        Args:
            category: The settings category (e.g., 'display', 'gameplay')
            key: The setting key
            value: The value to set
        """
        if category not in self.settings:
            self.settings[category] = {}
        
        if self.settings[category].get(key) != value:
            self.settings[category][key] = value
            self.settings_modified = True
    
    def get_asset_path(self, category, key):
        """
        Get an asset path from the manifest.
        
        Args:
            category: The asset category (e.g., 'sounds', 'images')
            key: The asset key
            
        Returns:
            The asset path or None if not found
        """
        if category in self.asset_manifest and key in self.asset_manifest[category]:
            return self.asset_manifest[category][key]
        return None
    
    def get_core_fragment_details(self):
        """Get core fragment details from the asset manifest"""
        if "core_fragments" in self.asset_manifest:
            return self.asset_manifest["core_fragments"]
        return {}
    
    def get_weapon_icon_path(self, weapon_mode):
        """Get weapon icon path for the specified weapon mode"""
        if "weapon_icons" in self.asset_manifest and str(weapon_mode) in self.asset_manifest["weapon_icons"]:
            return self.asset_manifest["weapon_icons"][str(weapon_mode)]
        return None
        
    def get_weapon_icon_paths(self):
        """Get all weapon icon paths as a dictionary"""
        if "weapon_icons" in self.asset_manifest:
            return self.asset_manifest["weapon_icons"]
        return {}

# Create a global instance for easy access
settings_manager = SettingsManager()

# Convenience functions
def get_setting(category, key, default=None):
    return settings_manager.get_setting(category, key, default)

def set_setting(category, key, value):
    settings_manager.set_setting(category, key, value)

def get_asset_path(category, key):
    return settings_manager.get_asset_path(category, key)

def save_settings():
    settings_manager.save_settings()
    
def reset_all_settings_to_default():
    """Reset all settings to their default values."""
    # Define default settings structure
    default_settings = {
        "display": {
            "FULLSCREEN_MODE": False,
            "MUSIC_VOLUME_MULTIPLIER": 0.5,
            "SFX_VOLUME_MULTIPLIER": 0.7
        },
        "gameplay": {
            "PLAYER_MAX_HEALTH": 100,
            "PLAYER_LIVES": 3,
            "PLAYER_SPEED": 3,
            "PLAYER_INVINCIBILITY": False,
            "INITIAL_WEAPON_MODE": 0
        },
        "enemies": {
            "ENEMY_SPEED": 1.5,
            "ENEMY_HEALTH": 25
        },
        "powerups": {
            "SHIELD_POWERUP_DURATION": 10000,
            "SPEED_BOOST_POWERUP_DURATION": 7000
        },
        "progression": {
            "LEVEL_TIMER_DURATION": 120000
        },
        "weapons": {
            "weapons": 50
        },
        "weapon_modes": {
            "WEAPON_MODES_SEQUENCE": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "WEAPON_MODE_NAMES": {
                "0": "Single Shot",
                "1": "Tri-Shot", 
                "2": "Rapid Single",
                "3": "Rapid Tri-Shot",
                "4": "Big Shot",
                "5": "Bounce Shot",
                "6": "Pierce Shot",
                "7": "Heatseeker",
                "8": "Seeker + Rapid",
                "9": "Chain Lightning"
            }
        }
    }
    
    # Reset to defaults
    settings_manager.settings = default_settings
    settings_manager.settings_modified = True
    settings_manager.save_settings()
    logger.info("Game settings have been reset to defaults.")