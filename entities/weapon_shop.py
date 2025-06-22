# entities/weapon_shop.py
from pygame.sprite import Sprite
from pygame.font import Font
from pygame import Surface, SRCALPHA
from pygame.draw import rect as draw_rect
from constants import (
    WHITE, CYAN, GREEN, YELLOW, RED, GOLD, GREY, WEAPON_MODE_NAMES,
    WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
    WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
    WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS, WEAPON_MODE_LIGHTNING
)
from settings_manager import get_setting

class WeaponShop(Sprite):
    """A weapon shop that spawns on level 1 and allows purchasing weapons with orichalc fragments"""
    
    def __init__(self, x, y, asset_manager):
        super().__init__()
        self.asset_manager = asset_manager
        self.center_x = x
        self.center_y = y
        
        # Load the shop image
        self.image = self.asset_manager.get_image("images/powerups/weapons_upgrade_shop.png")
        if not self.image:
            # Fallback if image not found
            tile_size = get_setting("gameplay", "TILE_SIZE", 80)
            self.image = Surface((tile_size, tile_size), SRCALPHA)
            draw_rect(self.image, GOLD, self.image.get_rect(), 3)
            font_obj = Font(None, 24)
            text = font_obj.render("SHOP", True, WHITE)
            self.image.blit(text, text.get_rect(center=(tile_size//2, tile_size//2)))
        
        self.rect = self.image.get_rect(center=(x, y))
        
        # Weapon prices in orichalc fragments
        self.weapon_prices = {
            WEAPON_MODE_TRI_SHOT: 5,
            WEAPON_MODE_RAPID_SINGLE: 8,
            WEAPON_MODE_RAPID_TRI: 12,
            WEAPON_MODE_BIG_SHOT: 10,
            WEAPON_MODE_BOUNCE: 15,
            WEAPON_MODE_PIERCE: 18,
            WEAPON_MODE_HEATSEEKER: 20,
            WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: 25,
            WEAPON_MODE_LIGHTNING: 30
        }
        
        # Track purchased weapons
        self.purchased_weapons = set()
        
        # Shop interaction state
        self.is_active = False
        self.interaction_range = get_setting("gameplay", "TILE_SIZE", 80) * 1.5
        
    def get_weapon_price(self, weapon_mode):
        """Get the price of a weapon in orichalc fragments"""
        return self.weapon_prices.get(weapon_mode, 999)
        
    def is_purchased(self, weapon_mode):
        """Check if a weapon has been purchased"""
        return weapon_mode in self.purchased_weapons
        
    def purchase_weapon(self, weapon_mode, current_fragments):
        """Attempt to purchase a weapon. Returns cost if successful, 0 if failed"""
        if weapon_mode in self.purchased_weapons:
            return 0  # Already purchased
            
        cost = self.get_weapon_price(weapon_mode)
        if current_fragments >= cost:
            self.purchased_weapons.add(weapon_mode)
            return cost
        return 0  # Not enough fragments
        
    def can_interact(self, player_pos):
        """Check if player is close enough to interact with shop"""
        if not player_pos:
            return False
        distance = ((player_pos[0] - self.center_x) ** 2 + (player_pos[1] - self.center_y) ** 2) ** 0.5
        return distance <= self.interaction_range
    
    def get_weapon_stats(self, weapon_mode):
        """Get weapon stats for display"""
        stats = {
            WEAPON_MODE_TRI_SHOT: {"damage": "1x3", "rate": "Medium", "special": "Triple Shot"},
            WEAPON_MODE_RAPID_SINGLE: {"damage": "1x", "rate": "Fast", "special": "Rapid Fire"},
            WEAPON_MODE_RAPID_TRI: {"damage": "1x3", "rate": "Fast", "special": "Rapid Triple"},
            WEAPON_MODE_BIG_SHOT: {"damage": "3x", "rate": "Slow", "special": "Heavy Damage"},
            WEAPON_MODE_BOUNCE: {"damage": "1x", "rate": "Medium", "special": "Bouncing"},
            WEAPON_MODE_PIERCE: {"damage": "2x", "rate": "Medium", "special": "Piercing"},
            WEAPON_MODE_HEATSEEKER: {"damage": "2x", "rate": "Slow", "special": "Homing"},
            WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: {"damage": "2x+1x", "rate": "Medium", "special": "Homing+Bullets"},
            WEAPON_MODE_LIGHTNING: {"damage": "4x", "rate": "Very Slow", "special": "Chain Lightning"}
        }
        return stats.get(weapon_mode, {"damage": "1x", "rate": "Medium", "special": "Standard"})
        
    def update(self):
        """Update shop state"""
        pass
        
    def draw(self, surface, camera=None):
        """Draw the weapon shop"""
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            if screen_rect.colliderect(surface.get_rect()):
                surface.blit(self.image, screen_rect)
        else:
            surface.blit(self.image, self.rect)