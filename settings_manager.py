# settings_manager.py
import json
import os
import logging
from constants import *

logger = logging.getLogger(__name__)

class SettingsManager:
    """
    Manages game settings loaded from JSON files and provides access to them.
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
            settings_path = os.path.join("data", "settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    self.settings = json.load(f)
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
            manifest_path = os.path.join("data", "asset_manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    self.asset_manifest = json.load(f)
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
            settings_path = os.path.join("data", "settings.json")
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.info("Settings saved successfully")
            self.settings_modified = False
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def get_setting(self, category, key, default=None):
        """
        Get a setting value from the specified category.
        
        Args:
            category: The settings category (e.g., 'display', 'gameplay')
            key: The setting key
            default: Default value if setting is not found
            
        Returns:
            The setting value or default if not found
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