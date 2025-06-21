# ui/weapon_shop_ui.py
import pygame
from constants import (
    WHITE, CYAN, GREEN, YELLOW, RED, GOLD, GREY, WEAPON_MODE_NAMES,
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, 
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, 
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS, 
    WEAPON_MODE_LIGHTNING
)

class WeaponShopUI:
    """UI for purchasing weapons with rings"""
    
    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self.visible = False
        self.selected_weapon = 0
        self.available_weapons = []
        
    def show(self, weapon_shop, fragments_count, game_controller=None):
        """Show weapon shop with available weapons"""
        self.visible = True
        self.weapon_shop = weapon_shop
        self.fragments_count = fragments_count
        self.game_controller = game_controller
        all_weapons = [WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI, 
                      WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE, 
                      WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS, WEAPON_MODE_LIGHTNING]
        self.available_weapons = [w for w in all_weapons if not weapon_shop.is_purchased(w)]
        self.selected_weapon = 0
        
    def hide(self):
        self.visible = False
        
    def handle_input(self, key):
        """Handle keyboard input for weapon shop"""
        if not self.visible or not self.available_weapons:
            return None
            
        if key == pygame.K_UP:
            self.selected_weapon = (self.selected_weapon - 1) % len(self.available_weapons)
        elif key == pygame.K_DOWN:
            self.selected_weapon = (self.selected_weapon + 1) % len(self.available_weapons)
        elif key == pygame.K_RETURN:
            weapon_mode = self.available_weapons[self.selected_weapon]
            cost = self.weapon_shop.purchase_weapon(weapon_mode, self.fragments_count)
            if cost > 0:
                self.fragments_count -= cost
                self.available_weapons.remove(weapon_mode)
                if self.selected_weapon >= len(self.available_weapons):
                    self.selected_weapon = max(0, len(self.available_weapons) - 1)
                # Give the weapon to the player immediately
                if hasattr(self, 'game_controller') and self.game_controller.player:
                    self.game_controller.player.unlock_weapon_mode(weapon_mode)
                return cost
        elif key == pygame.K_ESCAPE:
            self.hide()
            # Resume game when exiting shop
            if hasattr(self, 'game_controller'):
                self.game_controller.paused = False
            
        return None
        
    def draw(self, screen):
        """Draw weapon shop interface"""
        if not self.visible:
            return
            
        width = screen.get_width()
        height = screen.get_height()
        
        # Background
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Shop window
        shop_width = 400
        shop_height = 300
        shop_x = (width - shop_width) // 2
        shop_y = (height - shop_height) // 2
        
        shop_surface = pygame.Surface((shop_width, shop_height), pygame.SRCALPHA)
        shop_surface.fill((30, 30, 50, 240))
        screen.blit(shop_surface, (shop_x, shop_y))
        pygame.draw.rect(screen, CYAN, (shop_x, shop_y, shop_width, shop_height), 2)
        
        # Title
        font_title = pygame.font.Font(None, 32)
        title_surf = font_title.render("WEAPON SHOP", True, GOLD)
        screen.blit(title_surf, (shop_x + 20, shop_y + 20))
        
        # Orichalc fragments count
        font_ui = pygame.font.Font(None, 24)
        fragments_surf = font_ui.render(f"Fragments: {self.fragments_count}", True, YELLOW)
        screen.blit(fragments_surf, (shop_x + shop_width - 140, shop_y + 25))
        
        # Weapons list
        if not self.available_weapons:
            no_weapons_surf = font_ui.render("All weapons purchased!", True, GREEN)
            screen.blit(no_weapons_surf, (shop_x + 20, shop_y + 80))
        else:
            for i, weapon_mode in enumerate(self.available_weapons):
                y_pos = shop_y + 80 + i * 30
                weapon_name = WEAPON_MODE_NAMES.get(weapon_mode, "Unknown")
                price = self.weapon_shop.get_weapon_price(weapon_mode)
                can_afford = self.fragments_count >= price
                
                # Highlight selected weapon
                if i == self.selected_weapon:
                    pygame.draw.rect(screen, (50, 50, 100), (shop_x + 10, y_pos - 5, shop_width - 20, 25))
                
                # Weapon name
                color = WHITE if can_afford else GREY
                if i == self.selected_weapon:
                    color = CYAN if can_afford else RED
                    
                weapon_surf = font_ui.render(weapon_name, True, color)
                screen.blit(weapon_surf, (shop_x + 20, y_pos))
                
                # Price
                price_surf = font_ui.render(f"{price} frags", True, color)
                screen.blit(price_surf, (shop_x + shop_width - 100, y_pos))
        
        # Instructions
        font_small = pygame.font.Font(None, 20)
        instructions = [
            "UP/DOWN: Navigate",
            "ENTER: Purchase",
            "ESC: Exit"
        ]
        
        for i, instruction in enumerate(instructions):
            instr_surf = font_small.render(instruction, True, WHITE)
            screen.blit(instr_surf, (shop_x + 20, shop_y + shop_height - 80 + i * 20))
