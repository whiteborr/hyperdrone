# entities/elemental_core.py
from pygame import Surface, SRCALPHA
from pygame.sprite import Sprite
from pygame.draw import circle
from math import sin
from settings_manager import get_setting
from logging import getLogger

logger = getLogger(__name__)

class ElementalCore(Sprite):
    """
    Represents an elemental core that can be collected by the player.
    Each core type unlocks different abilities and progression paths.
    """
    
    # Core types
    EARTH = "earth"
    FIRE = "fire"
    AIR = "air"
    WATER = "water"
    
    def __init__(self, x, y, core_type, asset_manager):
        super().__init__()
        self.core_type = core_type
        self.asset_manager = asset_manager
        self.collected = False
        
        # Create fallback sprite since assets don't exist
        self.image = Surface((32, 32), SRCALPHA)
        color = self._get_core_color()
        circle(self.image, color, (16, 16), 16)
        circle(self.image, (255, 255, 255), (16, 16), 16, 2)
        
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        
        # Animation properties
        self.float_offset = 0
        self.float_speed = 0.05
        self.glow_alpha = 128
        self.glow_direction = 1
        
        # Core properties
        self.abilities = self._get_core_abilities()
        
    def _get_core_color(self):
        """Get the color associated with this core type"""
        colors = {
            self.EARTH: (139, 69, 19),    # Brown
            self.FIRE: (255, 69, 0),      # Red-Orange
            self.AIR: (135, 206, 235),    # Sky Blue
            self.WATER: (0, 191, 255)     # Deep Sky Blue
        }
        return colors.get(self.core_type, (255, 255, 255))
    
    def _get_core_abilities(self):
        """Get the abilities unlocked by this core type"""
        abilities = {
            self.EARTH: {
                "stability": True,
                "gravity_control": True,
                "wall_phase": False,
                "description": "Stabilizes collapsing structures and enables gravity-based puzzles"
            },
            self.FIRE: {
                "purge_corruption": True,
                "weapon_boost": True,
                "firewall_breach": True,
                "description": "Burns corrupted logic and boosts weapon systems"
            },
            self.AIR: {
                "logic_shift": True,
                "enhanced_sensors": True,
                "glyph_decode": True,
                "description": "Enables logic-shifting puzzles and enhanced drone interpretation"
            },
            self.WATER: {
                "memory_access": True,
                "flow_control": True,
                "archive_unlock": True,
                "description": "Unlocks submerged archives and memory fragments"
            }
        }
        return abilities.get(self.core_type, {})
    
    def update(self, delta_time):
        """Update core animation"""
        if self.collected:
            return
            
        # Floating animation
        self.float_offset += self.float_speed * delta_time
        float_y = 5 * sin(self.float_offset)
        
        # Update position
        original_center = self.rect.center
        self.rect.centery = original_center[1] + int(float_y)
        
        # Glow animation
        self.glow_alpha += self.glow_direction * 2
        if self.glow_alpha >= 255:
            self.glow_alpha = 255
            self.glow_direction = -1
        elif self.glow_alpha <= 64:
            self.glow_alpha = 64
            self.glow_direction = 1
    
    def draw(self, surface, camera_offset=(0, 0)):
        """Draw the core with glow effect"""
        if self.collected:
            return
            
        # Draw glow effect
        glow_surface = Surface((self.rect.width + 20, self.rect.height + 20), SRCALPHA)
        glow_color = (*self._get_core_color(), self.glow_alpha // 4)
        circle(glow_surface, glow_color, 
                         (glow_surface.get_width() // 2, glow_surface.get_height() // 2), 
                         self.rect.width // 2 + 10)
        
        glow_rect = glow_surface.get_rect()
        glow_rect.center = (self.rect.centerx - camera_offset[0], self.rect.centery - camera_offset[1])
        surface.blit(glow_surface, glow_rect)
        
        # Draw core
        draw_rect = self.rect.copy()
        draw_rect.x -= camera_offset[0]
        draw_rect.y -= camera_offset[1]
        surface.blit(self.image, draw_rect)
    
    def collect(self):
        """Mark this core as collected"""
        if not self.collected:
            self.collected = True
            logger.info(f"Collected {self.core_type} elemental core")
            return True
        return False
    
    def get_description(self):
        """Get a description of this core's abilities"""
        return self.abilities.get("description", f"{self.core_type.title()} elemental core")


class CipherCore:
    """
    The Cipher Core artifact that holds all elemental cores and unlocks the Vault's secrets.
    """
    
    def __init__(self):
        self.cores = {
            ElementalCore.EARTH: None,
            ElementalCore.FIRE: None,
            ElementalCore.AIR: None,
            ElementalCore.WATER: None
        }
        self.active_abilities = set()
        
    def insert_core(self, core_type, core):
        """Insert an elemental core into the cipher"""
        if core_type in self.cores and self.cores[core_type] is None:
            self.cores[core_type] = core
            self._update_abilities()
            logger.info(f"Inserted {core_type} core into Cipher Core")
            return True
        return False
    
    def has_core(self, core_type):
        """Check if a specific core type is inserted"""
        return self.cores.get(core_type) is not None
    
    def get_completion_percentage(self):
        """Get the percentage of cores inserted"""
        inserted = sum(1 for core in self.cores.values() if core is not None)
        return (inserted / len(self.cores)) * 100
    
    def is_complete(self):
        """Check if all cores are inserted"""
        return all(core is not None for core in self.cores.values())
    
    def _update_abilities(self):
        """Update active abilities based on inserted cores"""
        self.active_abilities.clear()
        for core in self.cores.values():
            if core:
                for ability, enabled in core.abilities.items():
                    if enabled and ability != "description":
                        self.active_abilities.add(ability)
    
    def has_ability(self, ability_name):
        """Check if a specific ability is active"""
        return ability_name in self.active_abilities
    
    def get_active_abilities(self):
        """Get list of all active abilities"""
        return list(self.active_abilities)
    
    def get_status_text(self):
        """Get status text for UI display"""
        inserted = sum(1 for core in self.cores.values() if core is not None)
        total = len(self.cores)
        return f"Cipher Core: {inserted}/{total} cores inserted"