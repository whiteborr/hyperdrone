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
    """UI for purchasing weapons with fragments"""
    
    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self.visible = False
        self.selected_weapon = 0
        self.available_weapons = []
        self.show_confirmation = False
        self.mouse_pos = (0, 0)
        
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
        self.show_confirmation = False
        
    def hide(self):
        self.visible = False
        self.show_confirmation = False
        
    def handle_input(self, key):
        """Handle keyboard input for weapon shop"""
        if not self.visible:
            return None
            
        if self.show_confirmation:
            if key == pygame.K_y:
                weapon_mode = self.available_weapons[self.selected_weapon]
                cost = self.weapon_shop.purchase_weapon(weapon_mode, self.fragments_count)
                if cost > 0:
                    self.fragments_count -= cost
                    self.available_weapons.remove(weapon_mode)
                    if self.selected_weapon >= len(self.available_weapons):
                        self.selected_weapon = max(0, len(self.available_weapons) - 1)
                    # Add weapon to player's owned weapons
                    if hasattr(self, 'game_controller'):
                        if hasattr(self.game_controller, 'drone_system'):
                            self.game_controller.drone_system.add_owned_weapon(weapon_mode)
                        if self.game_controller.player:
                            self.game_controller.player.unlock_weapon_mode(weapon_mode)
                    self.show_confirmation = False
                    return cost
            elif key == pygame.K_n or key == pygame.K_ESCAPE:
                self.show_confirmation = False
            return None
            
        if not self.available_weapons:
            return None
            
        if key == pygame.K_LEFT:
            self.selected_weapon = (self.selected_weapon - 1) % len(self.available_weapons)
        elif key == pygame.K_RIGHT:
            self.selected_weapon = (self.selected_weapon + 1) % len(self.available_weapons)
        elif key == pygame.K_RETURN:
            self.show_confirmation = True
        elif key == pygame.K_ESCAPE:
            self.hide()
            if hasattr(self, 'game_controller'):
                self.game_controller.paused = False
        return None
    
    def handle_mouse(self, mouse_pos, mouse_pressed):
        """Handle mouse input"""
        if not self.visible or self.show_confirmation:
            return
        
        self.mouse_pos = mouse_pos
        width, height = pygame.display.get_surface().get_size()
        shop_width, shop_height = 600, 450
        shop_x = (width - shop_width) // 2
        shop_y = (height - shop_height) // 2
        
        # Check for mouse clicks on weapon area
        weapon_area = pygame.Rect(shop_x + 50, shop_y + 100, shop_width - 100, 200)
        if weapon_area.collidepoint(mouse_pos) and mouse_pressed[0]:
            self.show_confirmation = True
        
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
        shop_width = 600
        shop_height = 450
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
        
        # Fragments count
        font_ui = pygame.font.Font(None, 24)
        fragments_surf = font_ui.render(f"Fragments: {self.fragments_count}", True, YELLOW)
        screen.blit(fragments_surf, (shop_x + shop_width - 140, shop_y + 25))
        
        if self.show_confirmation:
            self._draw_confirmation(screen, shop_x, shop_y, shop_width, shop_height)
        else:
            self._draw_weapon_page(screen, shop_x, shop_y, shop_width, shop_height)
            self._draw_instructions(screen, shop_x, shop_y, shop_width, shop_height)
    
    def _draw_weapon_page(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw single weapon page"""
        if not self.available_weapons:
            font_ui = pygame.font.Font(None, 24)
            no_weapons_surf = font_ui.render("All weapons purchased!", True, GREEN)
            screen.blit(no_weapons_surf, (shop_x + 20, shop_y + 80))
            return
            
        weapon_mode = self.available_weapons[self.selected_weapon]
        weapon_name = WEAPON_MODE_NAMES.get(weapon_mode, "Unknown")
        price = self.weapon_shop.get_weapon_price(weapon_mode)
        can_afford = self.fragments_count >= price
        stats = self.weapon_shop.get_weapon_stats(weapon_mode)
        
        # Page indicator
        font_small = pygame.font.Font(None, 20)
        page_text = f"{self.selected_weapon + 1} / {len(self.available_weapons)}"
        page_surf = font_small.render(page_text, True, WHITE)
        screen.blit(page_surf, (shop_x + shop_width - 80, shop_y + 60))
        
        # Large weapon icon
        icon = self.asset_manager.get_weapon_icon(weapon_mode)
        if icon:
            icon_scaled = pygame.transform.scale(icon, (80, 80))
            screen.blit(icon_scaled, (shop_x + 50, shop_y + 100))
        
        # Weapon name
        font_title = pygame.font.Font(None, 36)
        name_color = GOLD if can_afford else RED
        name_surf = font_title.render(weapon_name, True, name_color)
        screen.blit(name_surf, (shop_x + 150, shop_y + 110))
        
        # Price
        font_ui = pygame.font.Font(None, 28)
        price_color = GREEN if can_afford else RED
        price_surf = font_ui.render(f"Cost: {price} fragments", True, price_color)
        screen.blit(price_surf, (shop_x + 150, shop_y + 150))
        
        # Stats
        font_stats = pygame.font.Font(None, 24)
        stats_y = shop_y + 220
        
        stats_title = font_stats.render("Stats:", True, CYAN)
        screen.blit(stats_title, (shop_x + 50, stats_y))
        
        stats_lines = [
            f"Damage: {stats['damage']}",
            f"Fire Rate: {stats['rate']}",
            f"Special: {stats['special']}"
        ]
        
        for i, line in enumerate(stats_lines):
            line_surf = font_stats.render(line, True, WHITE)
            screen.blit(line_surf, (shop_x + 50, stats_y + 30 + i * 25))
    
    def _draw_confirmation(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw purchase confirmation popup"""
        weapon_mode = self.available_weapons[self.selected_weapon]
        weapon_name = WEAPON_MODE_NAMES.get(weapon_mode, "Unknown")
        price = self.weapon_shop.get_weapon_price(weapon_mode)
        
        # Confirmation box
        conf_width, conf_height = 400, 150
        conf_x = shop_x + (shop_width - conf_width) // 2
        conf_y = shop_y + (shop_height - conf_height) // 2
        
        conf_surface = pygame.Surface((conf_width, conf_height), pygame.SRCALPHA)
        conf_surface.fill((50, 50, 80, 250))
        screen.blit(conf_surface, (conf_x, conf_y))
        pygame.draw.rect(screen, YELLOW, (conf_x, conf_y, conf_width, conf_height), 2)
        
        font_ui = pygame.font.Font(None, 24)
        
        # Confirmation text
        lines = [
            "Confirm purchase of",
            f"{weapon_name}",
            f"for {price} fragments?",
            "",
            "Y - Yes    N - No"
        ]
        
        for i, line in enumerate(lines):
            color = GOLD if i == 1 else WHITE
            line_surf = font_ui.render(line, True, color)
            text_rect = line_surf.get_rect(center=(conf_x + conf_width // 2, conf_y + 30 + i * 25))
            screen.blit(line_surf, text_rect)
    
    def _draw_instructions(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw control instructions"""
        font_small = pygame.font.Font(None, 18)
        instructions = [
            "LEFT/RIGHT: Navigate",
            "ENTER: Purchase",
            "Mouse: Click to purchase",
            "ESC: Exit"
        ]
        
        for i, instruction in enumerate(instructions):
            instr_surf = font_small.render(instruction, True, WHITE)
            screen.blit(instr_surf, (shop_x + 20, shop_y + shop_height - 90 + i * 18))
