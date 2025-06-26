# ui/weapon_shop_ui.py
from os.path import join, dirname
from math import sin, cos
from pygame import Surface, Rect, SRCALPHA, K_y, K_n, K_ESCAPE, K_LEFT, K_RIGHT, K_RETURN
from pygame.display import get_surface
from pygame.font import Font
from pygame.draw import rect as draw_rect, polygon, circle, line as draw_line
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
        self.scanline_alpha = 50
        self.scanline_offset = 0

        # Load fonts - it's better to load them once
        font_path = join(dirname(dirname(__file__)), "assets", "fonts", "neuropol.otf")
        self.font_title = Font(font_path, 40)
        self.font_subtitle = Font(font_path, 28)
        self.font_ui = Font(font_path, 22)
        self.font_small = Font(font_path, 18)


    def show(self, weapon_shop, fragments_count, game_controller=None):
        """Show weapon shop with available weapons"""
        self.visible = True
        self.weapon_shop = weapon_shop
        self.fragments_count = fragments_count
        self.game_controller = game_controller
        all_weapons = [WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
                      WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
                      WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS, WEAPON_MODE_LIGHTNING]

        # Show all weapons for upgrade (filter out max level ones)
        max_level = weapon_shop.get_max_weapon_level()
        self.available_weapons = []
        if game_controller and hasattr(game_controller, 'drone_system'):
            for weapon in all_weapons:
                current_level = game_controller.drone_system.get_weapon_level(weapon)
                if current_level < max_level:
                    self.available_weapons.append(weapon)
        else:
            self.available_weapons = all_weapons

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
                current_level = 0
                if hasattr(self, 'game_controller') and hasattr(self.game_controller, 'drone_system'):
                    current_level = self.game_controller.drone_system.get_weapon_level(weapon_mode)
                    fragments = self.game_controller.drone_system.get_orichalc_fragments()
                else:
                    fragments = self.fragments_count

                cost = self.weapon_shop.upgrade_weapon(weapon_mode, current_level, fragments)
                if cost > 0:
                    # Deduct fragments and upgrade weapon
                    if hasattr(self, 'game_controller') and hasattr(self.game_controller, 'drone_system'):
                        self.game_controller.drone_system.spend_orichalc_fragments(cost)
                        self.game_controller.drone_system.upgrade_weapon(weapon_mode)
                        # Update fragments count for display
                        self.fragments_count = self.game_controller.drone_system.get_orichalc_fragments()
                        # Unlock weapon for player if first time
                        if current_level == 0 and self.game_controller.player:
                            self.game_controller.player.unlock_weapon_mode(weapon_mode)
                    else:
                        self.fragments_count -= cost

                    # Check if weapon is now at max level and remove from available list
                    new_level = current_level + 1
                    if new_level >= self.weapon_shop.get_max_weapon_level():
                        self.available_weapons.remove(weapon_mode)
                        if self.selected_weapon >= len(self.available_weapons):
                            self.selected_weapon = max(0, len(self.available_weapons) - 1)

                    self.show_confirmation = False
                    return cost
            elif key == K_n or key == K_ESCAPE:
                self.show_confirmation = False
            return None

        if not self.available_weapons:
            if key == K_ESCAPE:
                self.hide()
                if hasattr(self, 'game_controller'):
                    self.game_controller.paused = False
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
        shop_width, shop_height = 1000, 600
        shop_x = (width - shop_width) // 2
        shop_y = (height - shop_height) // 2

        # Define clickable areas for arrows
        left_arrow_rect = Rect(shop_x + 370, shop_y + 300, 40, 40)
        right_arrow_rect = Rect(shop_x + shop_width - 410, shop_y + 300, 40, 40)

        if mouse_pressed[0]:
            if left_arrow_rect.collidepoint(mouse_pos):
                self.selected_weapon = (self.selected_weapon - 1) % len(self.available_weapons)
            elif right_arrow_rect.collidepoint(mouse_pos):
                self.selected_weapon = (self.selected_weapon + 1) % len(self.available_weapons)
            else:
                # Check for mouse clicks on weapon area to open confirmation
                weapon_area = Rect(shop_x + 350, shop_y + 100, shop_width - 700, 400)
                if weapon_area.collidepoint(mouse_pos):
                    self.show_confirmation = True


    def draw(self, screen):
        """Draw weapon shop interface"""
        if not self.visible:
            return

        width = screen.get_width()
        height = screen.get_height()

        # New: Draw a more interesting background
        self._draw_background(screen)

        # Main shop panel
        shop_width = 1100
        shop_height = 650
        shop_x = (width - shop_width) // 2
        shop_y = (height - shop_height) // 2
        
        # Main frame
        self._draw_main_frame(screen, shop_x, shop_y, shop_width, shop_height)

        # Enhanced animated divider line
        divider_x = shop_x + 350
        time_factor = get_ticks() * 0.003
        
        # Multiple animated lines for depth
        for i in range(3):
            alpha = int(80 + 60 * sin(time_factor + i * 0.5))
            offset = int(2 * sin(time_factor * 2 + i))
            draw_line(screen, (0, 200 + i * 20, 255, alpha), 
                     (divider_x + offset, shop_y + 20), 
                     (divider_x + offset, shop_y + shop_height - 20), 2 - i)
        
        # Glowing dots along the line
        for y in range(shop_y + 50, shop_y + shop_height - 50, 80):
            dot_alpha = int(120 + 100 * sin(time_factor * 3 + y * 0.01))
            circle(screen, (0, 255, 255, dot_alpha), (divider_x, y), 4)


        # Draw inventory panel content
        self._draw_inventory_panel(screen, shop_x + 20, shop_y + 20, 310, shop_height - 40)

        # Draw weapon details
        if self.show_confirmation:
            self._draw_confirmation(screen, shop_x, shop_y, shop_width, shop_height)
        else:
            self._draw_weapon_page(screen, shop_x + 370, shop_y + 20, shop_width - 390, shop_height - 40)
            self._draw_instructions(screen, shop_x, shop_y, shop_width, shop_height)

        # New: Add scanlines for a cool retro effect
        self._draw_scanlines(screen)
        
    def _draw_text_with_shadow(self, screen, text, font, color, pos, shadow_color=(0,0,0), offset=(2,2)):
        """Helper to draw text with a drop shadow."""
        text_surf = font.render(text, True, shadow_color)
        screen.blit(text_surf, (pos[0] + offset[0], pos[1] + offset[1]))
        text_surf = font.render(text, True, color)
        screen.blit(text_surf, pos)

    def _draw_background(self, screen):
        """Draws the main background with animated grid and overlay."""
        width, height = screen.get_size()
        
        # Animated background overlay
        overlay = Surface((width, height), SRCALPHA)
        time_factor = get_ticks() * 0.001
        bg_alpha = int(200 + 30 * sin(time_factor))
        overlay.fill((5, 15, 35, bg_alpha))
        
        # Animated grid pattern
        grid_offset = int(get_ticks() * 0.02) % 50
        for x in range(-grid_offset, width + 50, 50):
            alpha = int(60 + 40 * sin(time_factor + x * 0.01))
            draw_line(overlay, (20, 60, 120, alpha), (x, 0), (x, height))
        for y in range(-grid_offset, height + 50, 50):
            alpha = int(60 + 40 * cos(time_factor + y * 0.01))
            draw_line(overlay, (20, 60, 120, alpha), (0, y), (width, y))
            
        screen.blit(overlay, (0, 0))

    def _draw_main_frame(self, screen, x, y, width, height):
        """Draw an enhanced stylized frame for the shop."""
        # Animated main background
        panel_surface = Surface((width, height), SRCALPHA)
        time_factor = get_ticks() * 0.002
        bg_alpha = int(220 + 20 * sin(time_factor))
        panel_surface.fill((20, 35, 60, bg_alpha))
        screen.blit(panel_surface, (x, y))
        
        # Animated border glow
        border_alpha = int(120 + 80 * sin(time_factor * 2))
        draw_rect(screen, (0, 200, 255, border_alpha), (x-1, y-1, width+2, height+2), 3, border_radius=12)
        draw_rect(screen, (0, 255, 255, 150), (x, y, width, height), 2, border_radius=10)
        
        # Enhanced corner details with glow
        corner_size = 40
        glow_alpha = int(150 + 100 * sin(time_factor * 3))
        
        # Top-left corner
        draw_line(screen, (*GOLD, glow_alpha), (x-2, y + corner_size), (x-2, y-2), 5)
        draw_line(screen, (*GOLD, glow_alpha), (x-2, y-2), (x + corner_size, y-2), 5)
        draw_line(screen, GOLD, (x, y + corner_size), (x, y), 3)
        draw_line(screen, GOLD, (x, y), (x + corner_size, y), 3)
        
        # Top-right corner
        draw_line(screen, (*GOLD, glow_alpha), (x + width - corner_size, y-2), (x + width+2, y-2), 5)
        draw_line(screen, (*GOLD, glow_alpha), (x + width+2, y-2), (x + width+2, y + corner_size), 5)
        draw_line(screen, GOLD, (x + width - corner_size, y), (x + width, y), 3)
        draw_line(screen, GOLD, (x + width, y), (x + width, y + corner_size), 3)

        # Bottom-left corner
        draw_line(screen, (*GOLD, glow_alpha), (x-2, y + height - corner_size), (x-2, y + height+2), 5)
        draw_line(screen, (*GOLD, glow_alpha), (x-2, y + height+2), (x + corner_size, y + height+2), 5)
        draw_line(screen, GOLD, (x, y + height - corner_size), (x, y + height), 3)
        draw_line(screen, GOLD, (x, y + height), (x + corner_size, y + height), 3)
        
        # Bottom-right corner
        draw_line(screen, (*GOLD, glow_alpha), (x + width - corner_size, y + height+2), (x + width+2, y + height+2), 5)
        draw_line(screen, (*GOLD, glow_alpha), (x + width+2, y + height+2), (x + width+2, y + height - corner_size), 5)
        draw_line(screen, GOLD, (x + width - corner_size, y + height), (x + width, y + height), 3)
        draw_line(screen, GOLD, (x + width, y + height), (x + width, y + height - corner_size), 3)

    def _draw_weapon_page(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw single weapon page with improved visuals."""
        if not self.available_weapons:
            self._draw_text_with_shadow(screen, "All weapons fully upgraded!", self.font_subtitle, GREEN, 
                                        (shop_x + shop_width // 2 - 250, shop_y + shop_height // 2 - 20))
            return

        weapon_mode = self.available_weapons[self.selected_weapon]
        weapon_name = WEAPON_MODE_NAMES.get(weapon_mode, "Unknown")
        
        # Get weapon data
        current_level = self.game_controller.drone_system.get_weapon_level(weapon_mode) if self.game_controller else 0
        fragments = self.game_controller.drone_system.get_orichalc_fragments() if self.game_controller else self.fragments_count
        price = self.weapon_shop.get_weapon_upgrade_price(weapon_mode, current_level)
        can_afford = fragments >= price
        stats = self.weapon_shop.get_weapon_stats(weapon_mode, current_level + 1)
        max_level = self.weapon_shop.get_max_weapon_level()
        is_maxed = current_level >= max_level

        # Title
        self._draw_text_with_shadow(screen, "WEAPON UPGRADE", self.font_title, GOLD, (shop_x + 90, shop_y + 10))

        # Enhanced pulsing selection glow with multiple layers
        pulse_alpha = int(100 + 100 * sin(get_ticks() * 0.008))
        pulse_alpha2 = int(60 + 60 * sin(get_ticks() * 0.012))
        
        # Outer glow
        glow_surface = Surface((shop_width - 60, 220), SRCALPHA)
        draw_rect(glow_surface, (*GOLD, pulse_alpha2), glow_surface.get_rect(), 6, border_radius=15)
        screen.blit(glow_surface, (shop_x + 30, shop_y + 70))
        
        # Inner glow
        glow_surface2 = Surface((shop_width - 80, 200), SRCALPHA)
        draw_rect(glow_surface2, (*GOLD, pulse_alpha), glow_surface2.get_rect(), 4, border_radius=12)
        screen.blit(glow_surface2, (shop_x + 40, shop_y + 80))

        # Arrow buttons for navigation
        self._draw_arrow_button(screen, (shop_x, shop_y + 160), 'left')
        self._draw_arrow_button(screen, (shop_x + shop_width - 30, shop_y + 160), 'right')
        
        # Enhanced Weapon Icon with animated glow
        icon = self.asset_manager.get_weapon_icon(weapon_mode)
        if icon:
            icon_pos = (shop_x + 70, shop_y + 110)
            time_factor = get_ticks() * 0.005
            
            # Multi-layer glow effect
            glow_alpha1 = int(60 + 40 * sin(time_factor))
            glow_alpha2 = int(40 + 30 * sin(time_factor * 1.5))
            
            # Outer glow
            glow1 = Surface((140, 140), SRCALPHA)
            circle(glow1, (255, 200, 50, glow_alpha1), (70, 70), 65)
            screen.blit(glow1, (icon_pos[0] - 30, icon_pos[1] - 30))
            
            # Inner glow
            glow2 = Surface((120, 120), SRCALPHA)
            circle(glow2, (255, 255, 100, glow_alpha2), (60, 60), 55)
            screen.blit(glow2, (icon_pos[0] - 20, icon_pos[1] - 20))
            
            # Icon with subtle rotation
            rotation = sin(time_factor * 0.5) * 2
            icon_scaled = scale(icon, (90, 90))
            if rotation != 0:
                icon_scaled = rotate(icon_scaled, rotation)
            screen.blit(icon_scaled, (icon_pos[0] - 5, icon_pos[1] - 5))
            
        # Weapon Name
        name_color = GOLD if can_afford else RED
        self._draw_text_with_shadow(screen, weapon_name, self.font_subtitle, name_color, (shop_x + 200, shop_y + 100))

        # Level display
        level_text = f"Level: {current_level} / {max_level}"
        self._draw_text_with_shadow(screen, level_text, self.font_ui, CYAN, (shop_x + 200, shop_y + 140))

        # Price
        if is_maxed:
            price_text = "MAX LEVEL"
            price_color = GREY
        else:
            price_text = f"Upgrade Cost: {price}"
            price_color = GREEN if can_afford else RED
        self._draw_text_with_shadow(screen, price_text, self.font_ui, price_color, (shop_x + 200, shop_y + 170))

        # Stats
        self._draw_text_with_shadow(screen, "Next Level Stats:", self.font_subtitle, CYAN, (shop_x + 40, shop_y + 300))
        stats_lines = [
            f"Damage: {stats['damage']}",
            f"Fire Rate: {stats['rate']}",
            f"Special: {stats['special']}"
        ]
        for i, line in enumerate(stats_lines):
            self._draw_text_with_shadow(screen, line, self.font_ui, WHITE, (shop_x + 40, shop_y + 350 + i * 35))

    def _draw_arrow_button(self, screen, pos, direction):
        """Draws enhanced stylized arrow buttons with glow effects."""
        time_factor = get_ticks() * 0.01
        glow_alpha = int(100 + 80 * sin(time_factor))
        
        # Arrow polygons
        if direction == 'left':
            poly = [(pos[0] + 35, pos[1]), (pos[0], pos[1] + 25), (pos[0] + 35, pos[1] + 50)]
            glow_poly = [(pos[0] + 40, pos[1] - 5), (pos[0] - 5, pos[1] + 25), (pos[0] + 40, pos[1] + 55)]
        else:
            poly = [(pos[0], pos[1]), (pos[0] + 35, pos[1] + 25), (pos[0], pos[1] + 50)]
            glow_poly = [(pos[0] - 5, pos[1] - 5), (pos[0] + 40, pos[1] + 25), (pos[0] - 5, pos[1] + 55)]
        
        # Glow effect
        polygon(screen, (*CYAN, glow_alpha), glow_poly)
        # Main arrow
        polygon(screen, CYAN, poly)
        # Highlight edge
        draw_line(screen, WHITE, poly[0], poly[1], 2)
        draw_line(screen, (200, 255, 255), poly[1], poly[2], 1)


    def _draw_confirmation(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw purchase confirmation popup with improved visuals."""
        weapon_mode = self.available_weapons[self.selected_weapon]
        weapon_name = WEAPON_MODE_NAMES.get(weapon_mode, "Unknown")
        
        current_level = self.game_controller.drone_system.get_weapon_level(weapon_mode) if self.game_controller else 0
        price = self.weapon_shop.get_weapon_upgrade_price(weapon_mode, current_level)
        action_text = "Acquire" if current_level == 0 else "Upgrade"

        # Confirmation box
        conf_width, conf_height = 500, 250
        conf_x = shop_x + (shop_width - conf_width) // 2
        conf_y = shop_y + (shop_height - conf_height) // 2
        
        # Box with border
        draw_rect(screen, (30, 40, 60, 250), (conf_x, conf_y, conf_width, conf_height), border_radius=10)
        draw_rect(screen, YELLOW, (conf_x, conf_y, conf_width, conf_height), 2, border_radius=10)

        # Confirmation Text
        self._draw_text_with_shadow(screen, f"Confirm {action_text}", self.font_subtitle, WHITE, 
                                    (conf_x + 130, conf_y + 40))
        self._draw_text_with_shadow(screen, weapon_name, self.font_subtitle, GOLD, 
                                    (conf_x + 150, conf_y + 80))
        self._draw_text_with_shadow(screen, f"for {price} fragments?", self.font_subtitle, WHITE,
                                    (conf_x + 100, conf_y + 120))
        
        # Yes/No options
        self._draw_text_with_shadow(screen, "[Y] Yes", self.font_ui, GREEN, (conf_x + 100, conf_y + 190))
        self._draw_text_with_shadow(screen, "[N] No", self.font_ui, RED, (conf_x + 300, conf_y + 190))


    def _draw_instructions(self, screen, shop_x, shop_y, shop_width, shop_height):
        """Draw control instructions at the bottom."""
        instructions = "Use [LEFT]/[RIGHT] to Navigate  |  [ENTER] to Upgrade  |  [ESC] to Exit"
        self._draw_text_with_shadow(screen, instructions, self.font_small, WHITE,
                                    (shop_x + shop_width // 2 - 350, shop_y + shop_height - 50))


    def _draw_inventory_panel(self, screen, inv_x, inv_y, inv_width, inv_height):
        """Draw drone and weapon inventory panel with enhanced visuals."""
        
        # Panel Title
        self._draw_text_with_shadow(screen, "INVENTORY", self.font_subtitle, GOLD, (inv_x + 70, inv_y + 10))

        # Fragments display
        fragments_icon = self.asset_manager.get_image('images/collectibles/orichalc_fragment.png')
        if fragments_icon:
            icon_scaled = scale(fragments_icon, (24, 24))
            screen.blit(icon_scaled, (inv_x + 10, inv_y + 60))
        
        current_fragments = self.game_controller.drone_system.get_orichalc_fragments() if self.game_controller else self.fragments_count
        self._draw_text_with_shadow(screen, f"{current_fragments} Fragments", self.font_ui, (255, 0, 255), (inv_x + 45, inv_y + 60))

        # Current Drone
        self._draw_text_with_shadow(screen, "Active Drone:", self.font_ui, CYAN, (inv_x + 10, inv_y + 110))
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            drone_id = self.game_controller.drone_system.get_selected_drone_id()
            self._draw_text_with_shadow(screen, drone_id, self.font_ui, WHITE, (inv_x + 10, inv_y + 140))
            
            drone_image_key = f"{drone_id.upper()}_IMAGE"
            drone_image = self.asset_manager.get_image(drone_image_key)
            if drone_image:
                drone_scaled = scale(drone_image, (80, 80))
                screen.blit(drone_scaled, (inv_x + 200, inv_y + 110))

        # Owned Weapons
        self._draw_text_with_shadow(screen, "Owned Weapons:", self.font_ui, CYAN, (inv_x + 10, inv_y + 220))
        
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            owned_weapons = self.game_controller.drone_system.get_owned_weapons()
            y_offset = inv_y + 260
            max_level = 5

            for weapon_mode, level in owned_weapons.items():
                weapon_name = WEAPON_MODE_NAMES.get(int(weapon_mode), "Unknown Weapon")
                
                weapon_icon = self.asset_manager.get_weapon_icon(weapon_mode)
                if weapon_icon:
                    icon_scaled = scale(weapon_icon, (24, 24))
                    screen.blit(icon_scaled, (inv_x + 10, y_offset))
                
                self._draw_text_with_shadow(screen, weapon_name, self.font_small, GREEN, (inv_x + 40, y_offset + 2))
                
                # Progress Bar
                bar_width = 150
                bar_height = 12
                filled_width = int((level / max_level) * bar_width)
                bar_x = inv_x + 40
                bar_y = y_offset + 25
                
                draw_rect(screen, (0,0,0,150), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
                draw_rect(screen, GREEN, (bar_x, bar_y, filled_width, bar_height), border_radius=4)
                draw_rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1, border_radius=4)

                level_text = f"Lv {level}"
                self._draw_text_with_shadow(screen, level_text, self.font_small, WHITE, (bar_x + bar_width + 10, bar_y - 2))
                
                y_offset += 50
                if y_offset > inv_y + inv_height - 50:
                    break
                    
    def _draw_scanlines(self, screen):
        """Draws enhanced moving scanlines for a retro CRT effect."""
        width, height = screen.get_size()
        scanline_surface = Surface((width, height), SRCALPHA)
        
        self.scanline_offset = (self.scanline_offset + 0.5) % 6
        time_factor = get_ticks() * 0.001
        
        # Variable intensity scanlines
        for y in range(int(self.scanline_offset), height, 6):
            alpha = int(self.scanline_alpha + 20 * sin(time_factor + y * 0.1))
            alpha = max(10, min(80, alpha))
            draw_line(scanline_surface, (0, 20, 40, alpha), (0, y), (width, y), 1)
            
        # Occasional bright scanline
        bright_line_y = int((get_ticks() * 0.1) % height)
        draw_line(scanline_surface, (0, 100, 200, 60), (0, bright_line_y), (width, bright_line_y), 2)
            
        screen.blit(scanline_surface, (0, 0))