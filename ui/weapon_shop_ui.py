# ui/weapon_shop_ui.py
from math import sin
from pygame import Surface, Rect, SRCALPHA, K_y, K_n, K_ESCAPE, K_LEFT, K_RIGHT, K_RETURN
from pygame.display import get_surface
from pygame.font import Font
from pygame.draw import rect as draw_rect, polygon, circle, line as draw_line
from pygame.transform import scale, rotate
from pygame.time import get_ticks
from constants import (
    WHITE, CYAN, GREEN, YELLOW, RED, GOLD, GREY, WeaponModes, get_weapon_mode_names
)
from .ui_common import UICommon

class WeaponShopUI:
    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self.visible = False
        self.selected_weapon = 0
        self.available_weapons = []
        self.show_confirmation = False
        self.weapon_shop = None
        self.fragments_count = 0
        self.game_controller = None

        fonts = UICommon.load_fonts()
        self.font_title = fonts['title']
        self.font_subtitle = fonts['subtitle']
        self.font_ui = fonts['ui']
        self.font_small = fonts['small']

    def show(self, weapon_shop, fragments_count, game_controller=None):
        self.visible = True
        self.weapon_shop = weapon_shop
        self.fragments_count = fragments_count
        self.game_controller = game_controller
        
        # Get weapon trees for shop
        all_weapons = [
            WeaponModes.BIG_SHOT_FIRE, WeaponModes.BOUNCE, 
            WeaponModes.HEATSEEKER, WeaponModes.ARC_SPARK
        ]

        # Filter out max level weapons
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
        if not self.visible:
            return None

        if self.show_confirmation:
            return self._handle_confirmation_input(key)

        if not self.available_weapons:
            if key == K_ESCAPE:
                self._exit_shop()
            return None

        if key == K_LEFT:
            self.selected_weapon = (self.selected_weapon - 1) % len(self.available_weapons)
        elif key == K_RIGHT:
            self.selected_weapon = (self.selected_weapon + 1) % len(self.available_weapons)
        elif key == K_RETURN:
            self.show_confirmation = True
        elif key == K_ESCAPE:
            self._exit_shop()
        return None

    def _handle_confirmation_input(self, key):
        if key == K_y:
            return self._purchase_weapon()
        elif key in (K_n, K_ESCAPE):
            self.show_confirmation = False
        return None

    def _purchase_weapon(self):
        weapon_mode = self.available_weapons[self.selected_weapon]
        current_level = self._get_weapon_level(weapon_mode)
        fragments = self._get_fragments()

        cost = self.weapon_shop.upgrade_weapon(weapon_mode, current_level, fragments)
        if cost > 0:
            self._process_purchase(weapon_mode, cost, current_level)
            self.show_confirmation = False
            return cost
        return None

    def _process_purchase(self, weapon_mode, cost, current_level):
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            self.game_controller.drone_system.spend_orichalc_fragments(cost)
            self.game_controller.drone_system.upgrade_weapon(weapon_mode)
            self.fragments_count = self.game_controller.drone_system.get_orichalc_fragments()
            
            # Unlock weapon for player if first time
            if current_level == 0 and self.game_controller.player:
                self.game_controller.player.unlock_weapon_mode(weapon_mode)
        else:
            self.fragments_count -= cost

        # Remove from available list if maxed
        new_level = current_level + 1
        if new_level >= self.weapon_shop.get_max_weapon_level():
            self.available_weapons.remove(weapon_mode)
            if self.selected_weapon >= len(self.available_weapons):
                self.selected_weapon = max(0, len(self.available_weapons) - 1)

    def _get_weapon_level(self, weapon_mode):
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            return self.game_controller.drone_system.get_weapon_level(weapon_mode)
        return 0

    def _get_fragments(self):
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            return self.game_controller.drone_system.get_orichalc_fragments()
        return self.fragments_count

    def _exit_shop(self):
        self.hide()
        if self.game_controller:
            self.game_controller.paused = False

    def handle_mouse(self, mouse_pos, mouse_pressed):
        if not self.visible or self.show_confirmation or not mouse_pressed[0]:
            return

        width, height = get_surface().get_size()
        shop_width, shop_height = 1000, 600
        shop_x = (width - shop_width) // 2
        shop_y = (height - shop_height) // 2

        # Arrow click areas
        left_arrow = Rect(shop_x + 370, shop_y + 300, 40, 40)
        right_arrow = Rect(shop_x + shop_width - 410, shop_y + 300, 40, 40)
        weapon_area = Rect(shop_x + 350, shop_y + 100, shop_width - 700, 400)

        if left_arrow.collidepoint(mouse_pos):
            self.selected_weapon = (self.selected_weapon - 1) % len(self.available_weapons)
        elif right_arrow.collidepoint(mouse_pos):
            self.selected_weapon = (self.selected_weapon + 1) % len(self.available_weapons)
        elif weapon_area.collidepoint(mouse_pos):
            self.show_confirmation = True

    def draw(self, screen):
        if not self.visible:
            return

        width, height = screen.get_size()
        UICommon.draw_background(screen)

        # Main shop panel
        shop_width, shop_height = 1100, 650
        shop_x = (width - shop_width) // 2
        shop_y = (height - shop_height) // 2
        
        UICommon.draw_main_frame(screen, shop_x, shop_y, shop_width, shop_height)

        # Animated divider
        self._draw_divider(screen, shop_x + 350, shop_y, shop_height)

        # Draw panels
        self._draw_inventory_panel(screen, shop_x + 20, shop_y + 20, 310, shop_height - 40)

        if self.show_confirmation:
            self._draw_confirmation(screen, shop_x, shop_y, shop_width, shop_height)
        else:
            self._draw_weapon_page(screen, shop_x + 370, shop_y + 20, shop_width - 390, shop_height - 40)
            self._draw_instructions(screen, shop_x, shop_y, shop_width, shop_height)

        UICommon.draw_scanlines(screen)

    def _draw_divider(self, screen, divider_x, shop_y, shop_height):
        time_factor = get_ticks() * 0.003
        
        # Animated lines
        for i in range(3):
            alpha = int(80 + 60 * sin(time_factor + i * 0.5))
            offset = int(2 * sin(time_factor * 2 + i))
            draw_line(screen, (0, 200 + i * 20, 255, alpha), 
                     (divider_x + offset, shop_y + 20), 
                     (divider_x + offset, shop_y + shop_height - 20), 2 - i)
        
        # Glowing dots
        for y in range(shop_y + 50, shop_y + shop_height - 50, 80):
            dot_alpha = int(120 + 100 * sin(time_factor * 3 + y * 0.01))
            circle(screen, (0, 255, 255, dot_alpha), (divider_x, y), 4)

    def _draw_weapon_page(self, screen, shop_x, shop_y, shop_width, shop_height):
        if not self.available_weapons:
            UICommon.draw_text_with_shadow(screen, "All weapons fully upgraded!", self.font_subtitle, GREEN, 
                                        (shop_x + shop_width // 2 - 250, shop_y + shop_height // 2 - 20))
            return

        weapon_mode = self.available_weapons[self.selected_weapon]
        weapon_names = get_weapon_mode_names()
        weapon_name = weapon_names.get(weapon_mode, "Unknown")
        
        # Get weapon data
        current_level = self._get_weapon_level(weapon_mode)
        fragments = self._get_fragments()
        price = self.weapon_shop.get_weapon_upgrade_price(weapon_mode, current_level)
        can_afford = fragments >= price
        stats = self.weapon_shop.get_weapon_stats(weapon_mode, current_level + 1)
        max_level = self.weapon_shop.get_max_weapon_level()

        # Title
        UICommon.draw_text_with_shadow(screen, "WEAPON UPGRADE", self.font_title, GOLD, (shop_x + 90, shop_y + 10))

        # Selection glow
        self._draw_selection_glow(screen, shop_x, shop_y, shop_width)

        # Navigation arrows
        self._draw_arrow_button(screen, (shop_x, shop_y + 160), 'left')
        self._draw_arrow_button(screen, (shop_x + shop_width - 30, shop_y + 160), 'right')
        
        # Weapon icon with glow
        self._draw_weapon_icon(screen, weapon_mode, (shop_x + 70, shop_y + 110))
        
        # Weapon info
        name_color = GOLD if can_afford else RED
        UICommon.draw_text_with_shadow(screen, weapon_name, self.font_subtitle, name_color, (shop_x + 200, shop_y + 100))
        
        level_text = f"Level: {current_level} / {max_level}"
        UICommon.draw_text_with_shadow(screen, level_text, self.font_ui, CYAN, (shop_x + 200, shop_y + 140))

        # Price
        if current_level >= max_level:
            price_text, price_color = "MAX LEVEL", GREY
        else:
            price_text = f"Upgrade Cost: {price}"
            price_color = GREEN if can_afford else RED
        UICommon.draw_text_with_shadow(screen, price_text, self.font_ui, price_color, (shop_x + 200, shop_y + 170))

        # Stats
        UICommon.draw_text_with_shadow(screen, "Next Level Stats:", self.font_subtitle, CYAN, (shop_x + 40, shop_y + 300))
        stats_lines = [
            f"Damage: {stats['damage']}",
            f"Fire Rate: {stats['rate']}",
            f"Special: {stats['special']}"
        ]
        for i, line in enumerate(stats_lines):
            UICommon.draw_text_with_shadow(screen, line, self.font_ui, WHITE, (shop_x + 40, shop_y + 350 + i * 35))

    def _draw_selection_glow(self, screen, shop_x, shop_y, shop_width):
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

    def _draw_weapon_icon(self, screen, weapon_mode, icon_pos):
        icon = self.asset_manager.get_weapon_icon(weapon_mode)
        if not icon:
            return
            
        time_factor = get_ticks() * 0.005
        
        # Multi-layer glow
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
        
        # Icon with rotation
        rotation = sin(time_factor * 0.5) * 2
        icon_scaled = scale(icon, (90, 90))
        if rotation != 0:
            icon_scaled = rotate(icon_scaled, rotation)
        screen.blit(icon_scaled, (icon_pos[0] - 5, icon_pos[1] - 5))

    def _draw_arrow_button(self, screen, pos, direction):
        time_factor = get_ticks() * 0.01
        glow_alpha = int(100 + 80 * sin(time_factor))
        
        if direction == 'left':
            poly = [(pos[0] + 35, pos[1]), (pos[0], pos[1] + 25), (pos[0] + 35, pos[1] + 50)]
            glow_poly = [(pos[0] + 40, pos[1] - 5), (pos[0] - 5, pos[1] + 25), (pos[0] + 40, pos[1] + 55)]
        else:
            poly = [(pos[0], pos[1]), (pos[0] + 35, pos[1] + 25), (pos[0], pos[1] + 50)]
            glow_poly = [(pos[0] - 5, pos[1] - 5), (pos[0] + 40, pos[1] + 25), (pos[0] - 5, pos[1] + 55)]
        
        # Glow and arrow
        polygon(screen, (*CYAN, glow_alpha), glow_poly)
        polygon(screen, CYAN, poly)
        draw_line(screen, WHITE, poly[0], poly[1], 2)
        draw_line(screen, (200, 255, 255), poly[1], poly[2], 1)

    def _draw_confirmation(self, screen, shop_x, shop_y, shop_width, shop_height):
        weapon_mode = self.available_weapons[self.selected_weapon]
        weapon_names = get_weapon_mode_names()
        weapon_name = weapon_names.get(weapon_mode, "Unknown")
        
        current_level = self._get_weapon_level(weapon_mode)
        price = self.weapon_shop.get_weapon_upgrade_price(weapon_mode, current_level)
        action_text = "Acquire" if current_level == 0 else "Upgrade"

        # Confirmation box
        conf_width, conf_height = 500, 250
        conf_x = shop_x + (shop_width - conf_width) // 2
        conf_y = shop_y + (shop_height - conf_height) // 2
        
        draw_rect(screen, (30, 40, 60, 250), (conf_x, conf_y, conf_width, conf_height), border_radius=10)
        draw_rect(screen, YELLOW, (conf_x, conf_y, conf_width, conf_height), 2, border_radius=10)

        # Text
        UICommon.draw_text_with_shadow(screen, f"Confirm {action_text}", self.font_subtitle, WHITE, 
                                    (conf_x + 130, conf_y + 40))
        UICommon.draw_text_with_shadow(screen, weapon_name, self.font_subtitle, GOLD, 
                                    (conf_x + 150, conf_y + 80))
        UICommon.draw_text_with_shadow(screen, f"for {price} fragments?", self.font_subtitle, WHITE,
                                    (conf_x + 100, conf_y + 120))
        
        # Options
        UICommon.draw_text_with_shadow(screen, "[Y] Yes", self.font_ui, GREEN, (conf_x + 100, conf_y + 190))
        UICommon.draw_text_with_shadow(screen, "[N] No", self.font_ui, RED, (conf_x + 300, conf_y + 190))

    def _draw_instructions(self, screen, shop_x, shop_y, shop_width, shop_height):
        instructions = "Use [LEFT]/[RIGHT] to Navigate  |  [ENTER] to Upgrade  |  [ESC] to Exit"
        UICommon.draw_text_with_shadow(screen, instructions, self.font_small, WHITE,
                                    (shop_x + shop_width // 2 - 350, shop_y + shop_height - 50))

    def _draw_inventory_panel(self, screen, inv_x, inv_y, inv_width, inv_height):
        # Title
        UICommon.draw_text_with_shadow(screen, "INVENTORY", self.font_subtitle, GOLD, (inv_x + 70, inv_y + 10))

        # Fragments
        fragments_icon = self.asset_manager.get_image('images/collectibles/orichalc_fragment.png')
        if fragments_icon:
            icon_scaled = scale(fragments_icon, (24, 24))
            screen.blit(icon_scaled, (inv_x + 10, inv_y + 60))
        
        current_fragments = self._get_fragments()
        UICommon.draw_text_with_shadow(screen, f"{current_fragments} Fragments", self.font_ui, (255, 0, 255), (inv_x + 45, inv_y + 60))

        # Current drone
        UICommon.draw_text_with_shadow(screen, "Active Drone:", self.font_ui, CYAN, (inv_x + 10, inv_y + 110))
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            drone_id = self.game_controller.drone_system.get_selected_drone_id()
            UICommon.draw_text_with_shadow(screen, drone_id, self.font_ui, WHITE, (inv_x + 10, inv_y + 140))
            
            drone_image = self.asset_manager.get_image(f"{drone_id.upper()}_IMAGE")
            if drone_image:
                drone_scaled = scale(drone_image, (80, 80))
                screen.blit(drone_scaled, (inv_x + 200, inv_y + 110))

        # Owned weapons
        UICommon.draw_text_with_shadow(screen, "Owned Weapons:", self.font_ui, CYAN, (inv_x + 10, inv_y + 220))
        
        if self.game_controller and hasattr(self.game_controller, 'drone_system'):
            self._draw_owned_weapons(screen, inv_x, inv_y + 260, inv_height)

    def _draw_owned_weapons(self, screen, inv_x, start_y, inv_height):
        owned_weapons = self.game_controller.drone_system.get_owned_weapons()
        y_offset = start_y
        max_level = 5

        for weapon_mode, level in owned_weapons.items():
            if y_offset > start_y + inv_height - 100:
                break
                
            weapon_names = get_weapon_mode_names()
            weapon_name = weapon_names.get(int(weapon_mode), "Unknown Weapon")
            
            # Weapon icon
            weapon_icon = self.asset_manager.get_weapon_icon(weapon_mode)
            if weapon_icon:
                icon_scaled = scale(weapon_icon, (24, 24))
                screen.blit(icon_scaled, (inv_x + 10, y_offset))
            
            UICommon.draw_text_with_shadow(screen, weapon_name, self.font_small, GREEN, (inv_x + 40, y_offset + 2))
            
            # Progress bar
            bar_width, bar_height = 150, 12
            filled_width = int((level / max_level) * bar_width)
            bar_x, bar_y = inv_x + 40, y_offset + 25
            
            draw_rect(screen, (0, 0, 0, 150), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
            draw_rect(screen, GREEN, (bar_x, bar_y, filled_width, bar_height), border_radius=4)
            draw_rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1, border_radius=4)

            level_text = f"Lv {level}"
            UICommon.draw_text_with_shadow(screen, level_text, self.font_small, WHITE, (bar_x + bar_width + 10, bar_y - 2))
            
            y_offset += 50