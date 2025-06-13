# hyperdrone_core/constants.py
# This file imports constants from the root constants.py file to make them available
# within the hyperdrone_core package

# Import all constants from the root constants.py
from constants import *

# Define additional constants needed by hyperdrone_core modules
POWERUP_TYPES = {
    "weapon_upgrade": "weapon_upgrade",
    "shield": "shield",
    "speed_boost": "speed_boost"
}

# HUD constants
HUD_RING_ICON_AREA_X_OFFSET = 150
HUD_RING_ICON_AREA_Y_OFFSET = 30
HUD_RING_ICON_SIZE = 24
HUD_RING_ICON_SPACING = 5