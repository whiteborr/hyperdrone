# game_settings.py
# This is a compatibility layer for the refactored settings system
# It allows existing code to continue working without major changes
# This file is deprecated and will be removed in a future version
# Please use settings_manager.get_setting() instead

import logging
from constants import *
from settings_manager import get_setting, set_setting, save_settings

logger = logging.getLogger(__name__)

# Re-export all constants from constants.py
# This ensures backward compatibility with code that imports from game_settings

# Compatibility function to get any setting
def get_game_setting(key, default_override=None):
    """
    Get a game setting by key, searching through all categories.
    
    Args:
        key: The setting key
        default_override: Default value if setting is not found
        
    Returns:
        The setting value or default if not found
    """
    # Try common categories in order of likelihood
    categories = ["gameplay", "display", "weapons", "enemies", "powerups", 
                 "bosses", "collectibles", "progression", "architect_vault", 
                 "defense_mode", "abilities", "colors", "assets", "game_states", 
                 "weapon_modes"]
    
    for category in categories:
        value = get_setting(category, key, None)
        if value is not None:
            return value
            
    return default_override

# Compatibility function to set any setting
def set_game_setting(key, value):
    """
    Set a game setting by key, updating the appropriate category.
    
    Args:
        key: The setting key
        value: The value to set
    """
    # Try to find which category the key belongs to
    categories = ["gameplay", "display", "weapons", "enemies", "powerups", 
                 "bosses", "collectibles", "progression", "architect_vault", 
                 "defense_mode", "abilities", "colors", "assets", "game_states", 
                 "weapon_modes"]
    
    for category in categories:
        if get_setting(category, key, None) is not None:
            set_setting(category, key, value)
            return
    
    # If key wasn't found in any category, add it to 'gameplay' as a fallback
    set_setting("gameplay", key, value)

# Function to reset all settings to defaults
def reset_all_settings_to_default():
    """Reset all settings to their default values."""
    from settings_manager import settings_manager
    settings_manager._load_settings()  # Reload settings from file
    logger.info("Game settings have been reset to defaults.")