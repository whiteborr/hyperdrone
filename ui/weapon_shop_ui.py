# ui/weapon_shop_ui.py
import os
from pygame import Surface, Rect, SRCALPHA, K_y, K_n, K_ESCAPE, K_LEFT, K_RIGHT, K_RETURN
from pygame.display import get_surface
from pygame.font import Font
from pygame.draw import rect as draw_rect, polygon, circle
from pygame.transform import scale, flip, rotate
from pygame.time import get_ticks
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
        self.corner_overlay = None
        
    def show(self, weapon_shop, fragments_count, game_controller=None):
        """Show weapon shop with available weapons"""
        self.visible = True
        self.weapon_shop = weapon_shop
        self.fragments_count = fragments_count
        self.game_controller = game_controller
        all_weapons = [WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI, 
                      WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE, 
                      WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS, WEAPON_MODE_LIGHTNING]
        
        # Check both weapon shop purchases and drone system owned weapons
        owned_weapons = set()
        if game_controller and hasattr(game_controller, 'drone_system'):
            owned_weapons = set(game_controller.drone_system.get_owned_weapons())
        
        self.available_weapons = [w for w in all_weapons if not weapon_shop.is_purchased(w) and w not in owned_weapons]
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
            if key == K_y:
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
            elif key == K_n or key == K_ESCAPE:
                self.show_confirmation = False
            return None
            
        if not self.available_weapons:
            return None
            
        if key == K_LEFT:
            self.selected_weapon = (self.selected_weapon - 1) % len(self.available_weapons)
        elif key == K_RIGHT:
            self.selected_weapon = (self.selected_weapon + 1) % len(self.available_weapons)
        elif key == K_RETURN:
            self.show_confirmation = True
        elif key == K_ESCAPE:
            self.hide()
            if hasattr(self, 'game_controller'):
                self.game_controller.paused = False
        return None
    
    def handle_mouse(self, mouse_pos, mouse_pressed):
        """Handle mouse input"""
        if not self.visible or self.show_confirmation:
            return
        
        self.mouse_pos = mouse_pos
        width, height = get_surface().get_size()
        shop_width, shop_height = 600, 450
        shop_x = (width - shop_width) // 2
        shop_y = (height - shop_height) // 2
        
        # Check for mouse clicks on weapon area
        weapon_area = Rect(shop_x + 50, shop_y + 100, shop_width - 100, 200)
        if weapon_area.collidepoint(mouse_pos) and mouse_pressed[0]:
            self.show_confirmation = True
        
    def draw(self, screen):
        """Draw weapon shop interface"""
        if not self.visible:
            return
            
        width = screen.get_width()
        height = screen.get_height()
        
        # Background
        overlay = Surface((width, height), SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Inventory panel (left side)
        inv_width = 400
        inv_height = 600
        inv_x = (width - 750 - inv_width - 20) // 2
        inv_y = (height - inv_height) // 2
        
        inv_surface = Surface((inv_width, inv_height), SRCALPHA)
        inv_surface.fill((20, 20, 40, 240))
        screen.blit(inv_surface, (inv_x, inv_y))
        draw_rect(screen, GOLD, (inv_x, inv_y, inv_width, inv_height), 2)
        
        # Shop window (right side)
        shop_width = 750
        shop_height = 550
        shop_x = inv_x + inv_width + 20
        shop_y = (height - shop_height) // 2
        
        shop_surface = Surface((shop_width, shop_height), SRCALPHA)
        shop_surface.fill((30, 30, 50, 240))
        screen.blit(shop_surface, (shop_x, shop_y))
        draw_rect(screen, CYAN, (shop_x, shop_y, shop_width, shop_height), 2)
        
        # HUD-like frame over panels
        frame_surface = Surface((width, height), SRCALPHA)
        draw_rect(frame_surface, (50, 200, 255, 40), (inv_x - 5, inv_y - 5, inv_width + 10, inv_height + 10), border_radius=12)
        draw_rect(frame_surface, (50, 200, 255, 40), (shop_x - 5, shop_y - 5, shop_width + 10, shop_height + 10), border_radius=12)
        screen.blit(frame_surface, (0, 0))
        
        # Draw inventory panel content
        self._draw_inventory_panel(screen, inv_x, inv_y, inv_width, inv_height)
        
        # Draw corner borders on shop panel
        self._draw_corner_borders(screen, shop_x, shop_y, shop_width, shop_height)
        
        # Title with drop shadow
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "neuropol.otf")
        font_title = Font(font_path, 32)
        # Shadow
        title_shadow = font_title.render("WEAPON SHOP", True, (0, 0, 0))
        screen.blit(title_shadow, (shop_x + 22, shop_y + 22))
        # Text
        title_surf = font_title.render("WEAPON SHOP", True, GOLD)
        screen.blit(title_surf, (shop_x + 20, shop_y + 20))
        

        
        if self.show_confirmation:
            self._draw_confirmation(screen, shop_x, shop_y, shop_width, shop_height)
        else:
            self._draw_weapon_page(screen, shop_x, shop_y, shop_width, shop_height)
            self._draw_instructions(screen, shop_x, shop_y, shop_width, shop_height)
    
    def _draw_weapon_page(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw single weapon page"""
        import math
        
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "neuropol.otf")
        
        if not self.available_weapons:
            font_ui = Font(font_path, 24)
            no_weapons_surf = font_ui.render("All weapons purchased!", True, GREEN)
            screen.blit(no_weapons_surf, (shop_x + 20, shop_y + 80))
            return
            
        weapon_mode = self.available_weapons[self.selected_weapon]
        weapon_name = WEAPON_MODE_NAMES.get(weapon_mode, "Unknown")
        price = self.weapon_shop.get_weapon_price(weapon_mode)
        can_afford = self.fragments_count >= price
        stats = self.weapon_shop.get_weapon_stats(weapon_mode)
        
        # Pulsing glow for selected weapon panel
        pulse_alpha = int(128 + 127 * math.sin(get_ticks() * 0.005))
        glow_surface = Surface((shop_width - 40, 200), SRCALPHA)
        draw_rect(glow_surface, (255, 215, 0, pulse_alpha), glow_surface.get_rect(), 4, border_radius=10)
        screen.blit(glow_surface, (shop_x + 20, shop_y + 100))
        
        # Arrow buttons for navigation
        arrow_color = CYAN
        arrow_size = 30
        # Left arrow
        polygon(screen, arrow_color, [
            (shop_x + 10, shop_y + 200),
            (shop_x + 10 + arrow_size, shop_y + 200 - arrow_size//2),
            (shop_x + 10 + arrow_size, shop_y + 200 + arrow_size//2)
        ])
        # Right arrow
        polygon(screen, arrow_color, [
            (shop_x + shop_width - 10, shop_y + 200),
            (shop_x + shop_width - 10 - arrow_size, shop_y + 200 - arrow_size//2),
            (shop_x + shop_width - 10 - arrow_size, shop_y + 200 + arrow_size//2)
        ])
        
        # Page indicator
        font_small = Font(font_path, 18)
        page_text = f"{self.selected_weapon + 1} / {len(self.available_weapons)}"
        page_surf = font_small.render(page_text, True, WHITE)
        screen.blit(page_surf, (shop_x + shop_width - 80, shop_y + 60))
        
        # Large weapon icon with glow
        icon = self.asset_manager.get_weapon_icon(weapon_mode)
        if icon:
            # Glow behind icon
            glow = Surface((90, 90), SRCALPHA)
            circle(glow, (255, 255, 100, 80), (45, 45), 40)
            screen.blit(glow, (shop_x + 45, shop_y + 95))
            
            icon_scaled = scale(icon, (80, 80))
            screen.blit(icon_scaled, (shop_x + 50, shop_y + 100))
        
        # Weapon name with drop shadow
        font_title = Font(font_path, 36)
        name_color = GOLD if can_afford else RED
        # Shadow
        shadow = font_title.render(weapon_name, True, (0, 0, 0))
        screen.blit(shadow, (shop_x + 152, shop_y + 112))
        # Text
        name_surf = font_title.render(weapon_name, True, name_color)
        screen.blit(name_surf, (shop_x + 150, shop_y + 110))
        
        # Price with drop shadow
        font_sub = Font(font_path, 24)
        price_color = GREEN if can_afford else RED
        price_text = f"Cost: {price} cores"
        # Shadow
        price_shadow = font_sub.render(price_text, True, (0, 0, 0))
        screen.blit(price_shadow, (shop_x + 152, shop_y + 152))
        # Text
        price_surf = font_sub.render(price_text, True, price_color)
        screen.blit(price_surf, (shop_x + 150, shop_y + 150))
        
        # Stats with drop shadows
        font_stats = Font(font_path, 20)
        stats_y = shop_y + 220
        
        # Stats title
        stats_shadow = font_stats.render("Stats:", True, (0, 0, 0))
        screen.blit(stats_shadow, (shop_x + 52, stats_y + 2))
        stats_title = font_stats.render("Stats:", True, CYAN)
        screen.blit(stats_title, (shop_x + 50, stats_y))
        
        stats_lines = [
            f"Damage: {stats['damage']}",
            f"Fire Rate: {stats['rate']}",
            f"Special: {stats['special']}"
        ]
        
        for i, line in enumerate(stats_lines):
            # Shadow
            line_shadow = font_stats.render(line, True, (0, 0, 0))
            screen.blit(line_shadow, (shop_x + 52, stats_y + 32 + i * 25))
            # Text
            line_surf = font_stats.render(line, True, WHITE)
            screen.blit(line_surf, (shop_x + 50, stats_y + 30 + i * 25))
    
    def _draw_confirmation(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw purchase confirmation popup with fade-in"""
        weapon_mode = self.available_weapons[self.selected_weapon]
        weapon_name = WEAPON_MODE_NAMES.get(weapon_mode, "Unknown")
        price = self.weapon_shop.get_weapon_price(weapon_mode)
        
        # Confirmation box with fade-in
        conf_width, conf_height = 400, 150
        conf_x = shop_x + (shop_width - conf_width) // 2
        conf_y = shop_y + (shop_height - conf_height) // 2
        
        # Fade-in effect
        elapsed = get_ticks() % 500
        fade_alpha = min(255, int((elapsed / 500) * 255))
        
        conf_surface = Surface((conf_width, conf_height), SRCALPHA)
        conf_surface.fill((50, 50, 80, 250))
        conf_surface.set_alpha(fade_alpha)
        screen.blit(conf_surface, (conf_x, conf_y))
        draw_rect(screen, YELLOW, (conf_x, conf_y, conf_width, conf_height), 2)
        
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "neuropol.otf")
        font_ui = Font(font_path, 20)
        
        # Confirmation text with drop shadows
        lines = [
            "Confirm purchase of",
            f"{weapon_name}",
            f"for {price} cores?",
            "",
            "Y - Yes    N - No"
        ]
        
        for i, line in enumerate(lines):
            color = GOLD if i == 1 else WHITE
            # Shadow
            shadow_surf = font_ui.render(line, True, (0, 0, 0))
            shadow_rect = shadow_surf.get_rect(center=(conf_x + conf_width // 2 + 1, conf_y + 31 + i * 25))
            screen.blit(shadow_surf, shadow_rect)
            # Text
            line_surf = font_ui.render(line, True, color)
            text_rect = line_surf.get_rect(center=(conf_x + conf_width // 2, conf_y + 30 + i * 25))
            screen.blit(line_surf, text_rect)
    
    def _draw_instructions(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw control instructions"""
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "neuropol.otf")
        font_small = Font(font_path, 18)
        instructions = [
            "LEFT/RIGHT: Navigate",
            "ENTER: Purchase",
            "Mouse: Click to purchase",
            "ESC: Exit"
        ]
        
        for i, instruction in enumerate(instructions):
            instr_surf = font_small.render(instruction, True, WHITE)
            screen.blit(instr_surf, (shop_x + 20, shop_y + shop_height - 90 + i * 18))
    
    def _draw_inventory_panel(self, screen, inv_x, inv_y, inv_width, inv_height):
        """Draw drone and weapon inventory panel with enhanced visuals"""
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "neuropol.otf")
        font_title = Font(font_path, 24)
        font_ui = Font(font_path, 18)
        
        # Panel title with drop shadow
        title_shadow = font_title.render("INVENTORY", True, (0, 0, 0))
        screen.blit(title_shadow, (inv_x + 12, inv_y + 12))
        title_surf = font_title.render("INVENTORY", True, GOLD)
        screen.blit(title_surf, (inv_x + 10, inv_y + 10))
        
        # Cores display with icon and glow
        cores_icon = self.asset_manager.get_image('images/collectibles/orichalc_fragment_container.png')
        if cores_icon:
            # Glow behind icon
            glow = Surface((30, 30), SRCALPHA)
            circle(glow, (255, 255, 100, 60), (15, 15), 12)
            screen.blit(glow, (inv_x + inv_width - 85, inv_y + 7))
            
            icon_scaled = scale(cores_icon, (20, 20))
            screen.blit(icon_scaled, (inv_x + inv_width - 80, inv_y + 12))
        
        # Cores text with shadow - get current cores from drone system
        current_cores = self.fragments_count
        if hasattr(self, 'game_controller') and hasattr(self.game_controller, 'drone_system'):
            current_cores = self.game_controller.drone_system.get_cores()
        cores_shadow = font_ui.render(f"{current_cores}", True, (0, 0, 0))
        screen.blit(cores_shadow, (inv_x + inv_width - 53, inv_y + 17))
        cores_surf = font_ui.render(f"{current_cores}", True, YELLOW)
        screen.blit(cores_surf, (inv_x + inv_width - 55, inv_y + 15))
        
        # Current drone section with shadows
        drone_shadow = font_ui.render("Current Drone:", True, (0, 0, 0))
        screen.blit(drone_shadow, (inv_x + 12, inv_y + 52))
        drone_title = font_ui.render("Current Drone:", True, CYAN)
        screen.blit(drone_title, (inv_x + 10, inv_y + 50))
        
        if hasattr(self, 'game_controller') and hasattr(self.game_controller, 'drone_system'):
            drone_id = self.game_controller.drone_system.get_selected_drone_id()
            # Drone name with shadow
            name_shadow = font_ui.render(drone_id, True, (0, 0, 0))
            screen.blit(name_shadow, (inv_x + 12, inv_y + 77))
            drone_name = font_ui.render(drone_id, True, WHITE)
            screen.blit(drone_name, (inv_x + 10, inv_y + 75))
            
            # Display drone image with glow
            drone_image_key = f"{drone_id.upper()}_IMAGE"
            drone_image = self.asset_manager.get_image(drone_image_key)
            if drone_image:
                # Glow behind drone image
                glow = Surface((70, 70), SRCALPHA)
                circle(glow, (100, 150, 255, 60), (35, 35), 30)
                screen.blit(glow, (inv_x + 5, inv_y + 95))
                
                drone_scaled = scale(drone_image, (60, 60))
                screen.blit(drone_scaled, (inv_x + 10, inv_y + 100))
        
        # Owned weapons section with shadows
        weapons_shadow = font_ui.render("Owned Weapons:", True, (0, 0, 0))
        screen.blit(weapons_shadow, (inv_x + 12, inv_y + 182))
        weapons_title = font_ui.render("Owned Weapons:", True, CYAN)
        screen.blit(weapons_title, (inv_x + 10, inv_y + 180))
        
        if hasattr(self, 'game_controller') and hasattr(self.game_controller, 'drone_system'):
            owned_weapons = self.game_controller.drone_system.get_owned_weapons()
            y_offset = 205
            
            for weapon_mode in owned_weapons:
                weapon_name = WEAPON_MODE_NAMES.get(weapon_mode, f"Mode {weapon_mode}")
                
                # Draw weapon icon with glow
                weapon_icon = self.asset_manager.get_weapon_icon(weapon_mode)
                if weapon_icon:
                    # Small glow behind weapon icon
                    glow = Surface((30, 30), SRCALPHA)
                    circle(glow, (100, 255, 100, 40), (15, 15), 12)
                    screen.blit(glow, (inv_x + 10, inv_y + y_offset - 7))
                    
                    icon_scaled = scale(weapon_icon, (24, 24))
                    screen.blit(icon_scaled, (inv_x + 15, inv_y + y_offset - 2))
                
                # Draw weapon name with shadow
                weapon_shadow = font_ui.render(weapon_name, True, (0, 0, 0))
                screen.blit(weapon_shadow, (inv_x + 47, inv_y + y_offset + 2))
                weapon_surf = font_ui.render(weapon_name, True, GREEN)
                screen.blit(weapon_surf, (inv_x + 45, inv_y + y_offset))
                y_offset += 28
                
                if y_offset > inv_y + inv_height - 50:
                    break
    
    def _draw_corner_borders(self, screen, x, y, width, height):
        """Draw corner borders on the shop panel"""
        if not self.corner_overlay:
            self.corner_overlay = self.asset_manager.get_image("images/ui/weapons_shop_border.png")
        
        if not self.corner_overlay:
            return
        
        # Create rotated versions with SRCALPHA
        top_left = self.corner_overlay
        top_right = flip(self.corner_overlay, True, False)
        bottom_left = flip(self.corner_overlay, False, True)
        bottom_right = rotate(self.corner_overlay, 180)
        
        # Draw corners
        screen.blit(top_left, (x, y))
        screen.blit(top_right, (x + width - top_right.get_width(), y))
        screen.blit(bottom_left, (x, y + height - bottom_left.get_height()))
        screen.blit(bottom_right, (x + width - bottom_right.get_width(), y + height - bottom_right.get_height()))