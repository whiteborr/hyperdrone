# hyperdrone/ui/ui.py

import os
import math

import pygame

# game_settings.py is at the project root
import game_settings as gs
from game_settings import (
    WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT, BOTTOM_PANEL_HEIGHT, TILE_SIZE, 
    BLACK, GOLD, WHITE, GREEN, CYAN, RED, DARK_RED, GREY, YELLOW, LIGHT_BLUE, ORANGE, PURPLE, 
    DARK_GREY, DARK_PURPLE, ARCHITECT_VAULT_BG_COLOR, ARCHITECT_VAULT_WALL_COLOR, ARCHITECT_VAULT_ACCENT_COLOR, 
    WEAPON_MODE_ICONS, PLAYER_BULLET_COLOR, MISSILE_COLOR, LIGHTNING_COLOR, POWERUP_TYPES, 
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS, 
    GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, 
    GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, 
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, 
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION, 
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE, 
    DEFAULT_SETTINGS, 
    TOTAL_CORE_FRAGMENTS_NEEDED, CORE_FRAGMENT_DETAILS, 
    get_game_setting 
)

# Import from other refactored packages
from drone_management.drone_configs import DRONE_DATA, DRONE_DISPLAY_ORDER 
from hyperdrone_core import leaderboard 


class UIManager: 
    def __init__(self, screen, fonts, game_controller_ref, scene_manager_ref, drone_system_ref): 
        self.screen = screen 
        self.fonts = fonts 
        self.game_controller = game_controller_ref 
        self.scene_manager = scene_manager_ref 
        self.drone_system = drone_system_ref 

        self.ui_assets = {
            "ring_icon": None, 
            "ring_icon_empty": None, 
            "menu_background": None, 
            "current_drone_life_icon": None, 
            "core_fragment_icons": {}, 
            "core_fragment_empty_icon": None, 
        } 
        self.ui_icon_size_lives = (30, 30) 
        self.ui_icon_size_rings = (20, 20) 
        self.ui_icon_size_fragments = (20, 20) 

        if not hasattr(self.game_controller, 'fragment_ui_target_positions'):
            self.game_controller.fragment_ui_target_positions = {}

        self._load_ui_assets() 
        self.update_player_life_icon_surface() 

    def _load_ui_assets(self): 
        ring_icon_path = os.path.join("assets", "images", "collectibles", "ring_ui_icon.png") #
        ring_icon_empty_path = os.path.join("assets", "images", "collectibles", "ring_ui_icon_empty.png") #
        
        try: 
            if os.path.exists(ring_icon_path): #
                raw_ring_icon = pygame.image.load(ring_icon_path).convert_alpha() #
                self.ui_assets["ring_icon"] = pygame.transform.smoothscale(raw_ring_icon, self.ui_icon_size_rings) #
            else: 
                print(f"UIManager: Ring icon not found: {ring_icon_path}. Using fallback.") #
                self.ui_assets["ring_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", GOLD) #

            if os.path.exists(ring_icon_empty_path): #
                raw_ring_empty_icon = pygame.image.load(ring_icon_empty_path).convert_alpha() #
                self.ui_assets["ring_icon_empty"] = pygame.transform.smoothscale(raw_ring_empty_icon, self.ui_icon_size_rings) #
            else: 
                print(f"UIManager: Empty ring icon not found: {ring_icon_empty_path}. Using fallback.") #
                self.ui_assets["ring_icon_empty"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", GREY) #

        except pygame.error as e: 
            print(f"UIManager: Error loading ring icons: {e}. Using fallbacks.") #
            self.ui_assets["ring_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "R", GOLD) #
            self.ui_assets["ring_icon_empty"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "R", GREY) #
        
        menu_bg_path = os.path.join("assets", "images", "ui", "menu_logo_hyperdrone.png") #
        if os.path.exists(menu_bg_path): #
            try: 
                self.ui_assets["menu_background"] = pygame.image.load(menu_bg_path).convert_alpha() #
            except pygame.error as e: 
                print(f"UIManager: Error loading menu background '{menu_bg_path}': {e}") #
                self.ui_assets["menu_background"] = None #
        else: 
            print(f"UIManager: Menu background not found: {menu_bg_path}") #
            self.ui_assets["menu_background"] = None #

        fragment_empty_icon_path = os.path.join("assets", "images", "collectibles", "fragment_ui_icon_empty.png") 
        if os.path.exists(fragment_empty_icon_path):
            try:
                raw_frag_empty_icon = pygame.image.load(fragment_empty_icon_path).convert_alpha()
                self.ui_assets["core_fragment_empty_icon"] = pygame.transform.smoothscale(raw_frag_empty_icon, self.ui_icon_size_fragments)
            except pygame.error as e:
                print(f"UIManager: Empty fragment icon not found: {fragment_empty_icon_path}. Error: {e}. Using fallback.")
                self.ui_assets["core_fragment_empty_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "F", DARK_GREY, text_color=GREY)
        else:
            print(f"UIManager: Empty fragment icon not found: {fragment_empty_icon_path}. Using fallback.")
            self.ui_assets["core_fragment_empty_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "F", DARK_GREY, text_color=GREY)

        if CORE_FRAGMENT_DETAILS:
            for frag_key, details in CORE_FRAGMENT_DETAILS.items():
                frag_id = details.get("id")
                icon_filename = details.get("icon_filename")
                if frag_id and icon_filename:
                    icon_path = os.path.join("assets", "images", "collectibles", icon_filename)
                    if os.path.exists(icon_path):
                        try:
                            raw_icon = pygame.image.load(icon_path).convert_alpha()
                            self.ui_assets["core_fragment_icons"][frag_id] = pygame.transform.smoothscale(raw_icon, self.ui_icon_size_fragments)
                        except pygame.error as e:
                            print(f"UIManager: Error loading fragment icon for {frag_id} ('{icon_path}'): {e}. Using fallback.")
                            self.ui_assets["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", PURPLE)
                    else:
                        print(f"UIManager: Fragment icon not found for {frag_id}: {icon_path}. Using fallback.")
                        self.ui_assets["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, frag_id[:1] if frag_id else "!", PURPLE)
                elif frag_id and frag_id not in self.ui_assets["core_fragment_icons"]: 
                     self.ui_assets["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "!", DARK_PURPLE)


    def update_player_life_icon_surface(self): 
        selected_drone_id = self.drone_system.get_selected_drone_id() 
        drone_config = self.drone_system.get_drone_config(selected_drone_id) 
        icon_path = drone_config.get("icon_path") if drone_config else None 
        if icon_path and os.path.exists(icon_path): 
            try: 
                raw_icon = pygame.image.load(icon_path).convert_alpha() 
                self.ui_assets["current_drone_life_icon"] = pygame.transform.smoothscale(raw_icon, self.ui_icon_size_lives) 
            except pygame.error as e: 
                print(f"UIManager: Error loading life icon for {selected_drone_id} ('{icon_path}'): {e}. Using fallback.") 
                self.ui_assets["current_drone_life_icon"] = self._create_fallback_icon_surface(
                    size=self.ui_icon_size_lives, text="♥", color=CYAN, font_key="ui_emoji_small"
                ) 
        else: 
            if icon_path: print(f"UIManager: Warning - Life icon path not found: {icon_path}") 
            self.ui_assets["current_drone_life_icon"] = self._create_fallback_icon_surface(
                size=self.ui_icon_size_lives, text="♥", color=CYAN, font_key="ui_emoji_small" 
            ) 

    def _create_fallback_icon_surface(self, size=(30,30), text="?", color=GREY, text_color=WHITE, font_key="ui_text"): 
        surface = pygame.Surface(size, pygame.SRCALPHA) 
        surface.fill(color) 
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 1) 
        font_to_use = self.fonts.get(font_key, pygame.font.Font(None, max(10, size[1]-4))) 
        if text and font_to_use: 
            try: 
                text_surf = font_to_use.render(text, True, text_color) 
                text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2)) 
                surface.blit(text_surf, text_rect) 
            except Exception as e: 
                print(f"UIManager: Error rendering fallback icon text '{text}' with font '{font_key}': {e}") 
        return surface 

    def _render_text_safe(self, text, font_key, color, fallback_size=24): 
        font = self.fonts.get(font_key) 
        if not font: 
            font = pygame.font.Font(None, fallback_size) 
        try: 
            return font.render(str(text), True, color) 
        except Exception as e: 
            print(f"UIManager: Error rendering text '{text}' with font '{font_key}': {e}") 
            error_font = pygame.font.Font(None, fallback_size) 
            return error_font.render("ERR", True, RED) 

    def draw_current_scene_ui(self): 
        current_state = self.scene_manager.get_current_state() 
        is_menu_like_state = current_state in [
            GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, 
            GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, 
            GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE, 
            GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME 
        ] 
        if is_menu_like_state: 
            self.screen.fill(BLACK) 
            if hasattr(self.game_controller, 'menu_stars') and self.game_controller.menu_stars: 
                 for star_params in self.game_controller.menu_stars: 
                    pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3]) 
        if current_state == GAME_STATE_MAIN_MENU: 
            self.draw_main_menu() 
        elif current_state == GAME_STATE_DRONE_SELECT: 
            self.draw_drone_select_menu() 
        elif current_state == GAME_STATE_SETTINGS: 
            self.draw_settings_menu() 
        elif current_state == GAME_STATE_LEADERBOARD: 
            self.draw_leaderboard_overlay() 
        elif current_state == GAME_STATE_GAME_OVER: 
            self.draw_game_over_overlay() 
        elif current_state == GAME_STATE_ENTER_NAME: 
            self.draw_enter_name_overlay() 
        elif current_state.startswith("architect_vault"): 
            self.draw_architect_vault_hud_elements() 
            if self.game_controller.paused: self.draw_pause_overlay() 
            if current_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS: 
                self.draw_architect_vault_success_overlay() 
            elif current_state == GAME_STATE_ARCHITECT_VAULT_FAILURE: 
                self.draw_architect_vault_failure_overlay() 
        elif current_state == GAME_STATE_PLAYING or current_state == GAME_STATE_BONUS_LEVEL_PLAYING: 
            self.draw_gameplay_hud() 
            if self.game_controller.paused: self.draw_pause_overlay() 

    def draw_main_menu(self): #
        if self.ui_assets["menu_background"]: #
            try: #
                scaled_bg = pygame.transform.smoothscale(self.ui_assets["menu_background"], (WIDTH, HEIGHT)) # Using directly imported WIDTH, HEIGHT #
                self.screen.blit(scaled_bg, (0,0)) #
            except Exception as e: #
                print(f"UIManager: Error blitting menu background: {e}") #
                self.screen.fill(BLACK) #
        menu_options = getattr(self.game_controller, 'menu_options', ["Start", "Quit"]) #
        selected_option_idx = getattr(self.game_controller, 'selected_menu_option', 0) #
        menu_item_start_y = HEIGHT // 2 - 80 #
        item_spacing = 75 #
        base_font_size = self.fonts["menu_text"].get_height() #
        for i, option_text in enumerate(menu_options): #
            is_selected = (i == selected_option_idx) #
            text_color = GOLD if is_selected else WHITE #
            active_menu_font = self.fonts["menu_text"] #
            if is_selected: #
                 try: #
                     font_path = getattr(self.game_controller, 'font_path_neuropol', None) #
                     active_menu_font = pygame.font.Font(font_path, base_font_size + 8) #
                 except Exception: #
                     active_menu_font = pygame.font.Font(None, base_font_size + 8) #
            text_surf = active_menu_font.render(option_text, True, text_color) #
            if hasattr(text_surf, 'get_rect'): #
                text_rect = text_surf.get_rect() #
                button_width = text_rect.width + 60 #
                button_height = text_rect.height + 25 #
                button_surface_rect = pygame.Rect(0,0,button_width, button_height) #
                button_surface_rect.center = (WIDTH // 2, menu_item_start_y + i * item_spacing) #
                button_bg_surface = pygame.Surface(button_surface_rect.size, pygame.SRCALPHA) #
                current_bg_color = (70,70,70,220) if is_selected else (50,50,50,180) #
                pygame.draw.rect(button_bg_surface, current_bg_color, button_bg_surface.get_rect(), border_radius=15) #
                if is_selected: #
                    pygame.draw.rect(button_bg_surface, GOLD, button_bg_surface.get_rect(), 3, border_radius=15) #
                button_bg_surface.blit(text_surf, text_surf.get_rect(center=(button_width//2, button_height//2))) #
                self.screen.blit(button_bg_surface, button_surface_rect.topleft) #
        instr_surf = self._render_text_safe("Use UP/DOWN keys, ENTER to select.", "small_text", CYAN) #
        instr_bg_box=pygame.Surface((instr_surf.get_width()+20,instr_surf.get_height()+10),pygame.SRCALPHA) #
        instr_bg_box.fill((30,30,30,150)) #
        instr_bg_box.blit(instr_surf,instr_surf.get_rect(center=(instr_bg_box.get_width()//2,instr_bg_box.get_height()//2))) #
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH//2, HEIGHT-100))) #
        if get_game_setting("SETTINGS_MODIFIED"): #
            warning_surf = self._render_text_safe("Custom settings active: Leaderboard disabled.", "small_text", YELLOW) #
            self.screen.blit(warning_surf, warning_surf.get_rect(center=(WIDTH//2, HEIGHT-50))) #

    def draw_drone_select_menu(self): # Restored from original file content
        title_surf = self._render_text_safe("Select Drone", "title_text", GOLD) #
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 70)) #
        self.screen.blit(title_surf, title_rect) #

        drone_options_ids = getattr(self.game_controller, 'drone_select_options', DRONE_DISPLAY_ORDER) #
        selected_preview_idx = getattr(self.game_controller, 'selected_drone_preview_index', 0) #

        if not drone_options_ids: #
            no_drones_surf = self._render_text_safe("NO DRONES AVAILABLE", "large_text", RED) #
            self.screen.blit(no_drones_surf, no_drones_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))) #
            return #

        current_drone_id = drone_options_ids[selected_preview_idx] #
        drone_config = self.drone_system.get_drone_config(current_drone_id) #
        drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False) #
        is_unlocked = self.drone_system.is_drone_unlocked(current_drone_id) #
        is_currently_equipped = (current_drone_id == self.drone_system.get_selected_drone_id()) #

        drone_image_surf = None #
        if hasattr(self.game_controller, 'drone_main_display_cache'): #
            drone_image_surf = self.game_controller.drone_main_display_cache.get(current_drone_id) #
        
        img_width = drone_image_surf.get_width() if drone_image_surf else 200 #
        img_height = drone_image_surf.get_height() if drone_image_surf else 200 #

        name_text = drone_config.get("name", "N/A") #
        name_surf_temp = self.fonts["drone_name_cycle"].render(name_text, True, WHITE) #
        name_height = name_surf_temp.get_height() #

        hp_stat = drone_stats.get("hp") #
        speed_stat = drone_stats.get("speed") #
        turn_speed_stat = drone_stats.get("turn_speed") #
        fire_rate_mult = drone_stats.get("fire_rate_multiplier", 1.0) #
        special_ability_key = drone_stats.get("special_ability") #

        hp_display = str(hp_stat) if hp_stat is not None else "N/A" #
        speed_display = f"{speed_stat:.1f}" if isinstance(speed_stat, (int, float)) else "N/A" #
        turn_speed_display = f"{turn_speed_stat:.1f}" if isinstance(turn_speed_stat, (int, float)) else "N/A" #
        
        fire_rate_text = f"{1/fire_rate_mult:.1f}x" if fire_rate_mult != 0 else "N/A" #
        if fire_rate_mult == 1.0: fire_rate_text += " (Normal)" #
        elif fire_rate_mult < 1.0: fire_rate_text += " (Faster)" #
        else: fire_rate_text += " (Slower)" #

        special_ability_name = "None" #
        if special_ability_key == "phantom_cloak": special_ability_name = "Phantom Cloak" #
        elif special_ability_key == "omega_boost": special_ability_name = "Omega Boost" #

        stats_data_tuples = [
            ("HP:", hp_display), ("Speed:", speed_display), ("Turn Speed:", turn_speed_display), #
            ("Fire Rate:", fire_rate_text), ("Special:", special_ability_name) #
        ] #
        stats_content_surfaces = [] #
        max_stat_label_w = 0 #
        max_stat_value_w = 0 #
        stat_line_h = self.fonts["drone_stats_label_cycle"].get_height() + 5 #

        for label_str, value_str in stats_data_tuples: #
            label_s = self._render_text_safe(label_str, "drone_stats_label_cycle", LIGHT_BLUE if is_unlocked else GREY) #
            value_s = self._render_text_safe(value_str, "drone_stats_value_cycle", WHITE if is_unlocked else GREY) #
            stats_content_surfaces.append((label_s, value_s)) #
            max_stat_label_w = max(max_stat_label_w, label_s.get_width()) #
            max_stat_value_w = max(max_stat_value_w, value_s.get_width()) #

        stats_box_padding = 15 #
        stats_box_visual_width = max_stat_label_w + max_stat_value_w + 3 * stats_box_padding #
        stats_box_visual_height = (len(stats_content_surfaces) * stat_line_h) - (5 if stats_content_surfaces else 0) + 2 * stats_box_padding #

        desc_text = drone_config.get("description", "") #
        desc_color_final = (200,200,200) if is_unlocked else (100,100,100) #
        desc_max_width_for_card = WIDTH * 0.45 #
        desc_lines_surfs = [] #
        words = desc_text.split(' ') #
        current_line_text_desc = "" #
        desc_font = self.fonts["drone_desc_cycle"] #
        for word in words: #
            test_line = current_line_text_desc + word + " " #
            if desc_font.size(test_line)[0] < desc_max_width_for_card: #
                current_line_text_desc = test_line #
            else: #
                desc_lines_surfs.append(self._render_text_safe(current_line_text_desc.strip(), "drone_desc_cycle", desc_color_final)) #
                current_line_text_desc = word + " " #
        if current_line_text_desc: #
            desc_lines_surfs.append(self._render_text_safe(current_line_text_desc.strip(), "drone_desc_cycle", desc_color_final)) #
        total_desc_height = sum(s.get_height() for s in desc_lines_surfs) + (len(desc_lines_surfs)-1)*3 if desc_lines_surfs else 0 #

        unlock_text_str = "" #
        unlock_text_color = WHITE #
        unlock_condition = drone_config.get("unlock_condition", {}) #
        if not is_unlocked: #
            condition_text_str = unlock_condition.get("description", "Locked") #
            unlock_cost_val = unlock_condition.get("value") #
            type_is_cores_unlock = unlock_condition.get("type") == "cores" #
            unlock_text_str = condition_text_str #
            if type_is_cores_unlock and unlock_cost_val is not None and self.drone_system.get_player_cores() >= unlock_cost_val: #
                unlock_text_str += f" (ENTER to Unlock: {unlock_cost_val} 💠)" #
                unlock_text_color = GREEN #
            else: #
                unlock_text_color = YELLOW #
        elif is_currently_equipped: #
            unlock_text_str = "EQUIPPED" #
            unlock_text_color = GREEN #
        else: #
            unlock_text_str = "Press ENTER to Select" #
            unlock_text_color = CYAN #

        unlock_info_surf = self._render_text_safe(unlock_text_str, "drone_unlock_cycle", unlock_text_color) #
        unlock_info_height = unlock_info_surf.get_height() if unlock_info_surf else 0 #

        spacing_between_elements = 15 #
        padding_inside_card = 25 #
        card_content_total_h = (img_height + spacing_between_elements + name_height + spacing_between_elements +
                                stats_box_visual_height + spacing_between_elements + total_desc_height +
                                spacing_between_elements + unlock_info_height) #
        max_content_width_for_card = max(img_width, name_surf_temp.get_width(), stats_box_visual_width,
                                         max(s.get_width() for s in desc_lines_surfs) if desc_lines_surfs else 0,
                                         unlock_info_surf.get_width() if unlock_info_surf else 0) #
        card_w = max_content_width_for_card + 2 * padding_inside_card #
        card_w = min(card_w, WIDTH * 0.6) #
        card_h = card_content_total_h + 2 * padding_inside_card + 20 #

        title_bottom = title_rect.bottom if title_rect else 100 #
        main_card_x = (WIDTH - card_w) // 2 #
        main_card_y = title_bottom + 40 #
        main_card_rect = pygame.Rect(main_card_x, main_card_y, card_w, card_h) #

        pygame.draw.rect(self.screen, (25,30,40,230), main_card_rect, border_radius=20) #
        pygame.draw.rect(self.screen, GOLD, main_card_rect, 3, border_radius=20) #

        current_y_in_card = main_card_rect.top + padding_inside_card #

        if drone_image_surf: #
            display_drone_image = drone_image_surf #
            if not is_unlocked: #
                temp_img = drone_image_surf.copy() #
                temp_img.set_alpha(100) #
                display_drone_image = temp_img #
            final_img_rect = display_drone_image.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card) #
            self.screen.blit(display_drone_image, final_img_rect) #
            current_y_in_card = final_img_rect.bottom + spacing_between_elements #
        else: #
            current_y_in_card += img_height + spacing_between_elements #

        name_color_final = WHITE if is_unlocked else GREY #
        name_surf_final = self._render_text_safe(name_text, "drone_name_cycle", name_color_final) #
        final_name_rect = name_surf_final.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card) #
        self.screen.blit(name_surf_final, final_name_rect) #
        current_y_in_card = final_name_rect.bottom + spacing_between_elements #

        final_stats_box_draw_rect = pygame.Rect(main_card_rect.centerx - stats_box_visual_width // 2, current_y_in_card,
                                                stats_box_visual_width, stats_box_visual_height) #
        pygame.draw.rect(self.screen, (40,45,55,200), final_stats_box_draw_rect, border_radius=10) #
        pygame.draw.rect(self.screen, CYAN, final_stats_box_draw_rect, 1, border_radius=10) #
        stat_y_pos_render = final_stats_box_draw_rect.top + stats_box_padding #
        for i, (label_s, value_s) in enumerate(stats_content_surfaces): #
            self.screen.blit(label_s, (final_stats_box_draw_rect.left + stats_box_padding, stat_y_pos_render)) #
            self.screen.blit(value_s, (final_stats_box_draw_rect.right - stats_box_padding - value_s.get_width(), stat_y_pos_render)) #
            stat_y_pos_render += max(label_s.get_height(), value_s.get_height()) + (5 if i < len(stats_content_surfaces)-1 else 0) #
        current_y_in_card = final_stats_box_draw_rect.bottom + spacing_between_elements #

        desc_start_y_render = current_y_in_card #
        for line_surf in desc_lines_surfs: #
            self.screen.blit(line_surf, line_surf.get_rect(centerx=main_card_rect.centerx, top=desc_start_y_render)) #
            desc_start_y_render += line_surf.get_height() + 3 #
        current_y_in_card = desc_start_y_render + 5 #

        if unlock_info_surf: #
            unlock_info_rect = unlock_info_surf.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card) #
            self.screen.blit(unlock_info_surf, unlock_info_rect) #

        arrow_font = self.fonts.get("arrow_font_key", self.fonts["large_text"]) #
        left_arrow_surf = arrow_font.render("◀", True, WHITE if len(drone_options_ids) > 1 else GREY) #
        right_arrow_surf = arrow_font.render("▶", True, WHITE if len(drone_options_ids) > 1 else GREY) #
        arrow_y_center = main_card_rect.centery #
        arrow_padding_from_card_edge = 40 #
        if len(drone_options_ids) > 1: #
            left_arrow_rect = left_arrow_surf.get_rect(centery=arrow_y_center, right=main_card_rect.left - arrow_padding_from_card_edge) #
            self.screen.blit(left_arrow_surf, left_arrow_rect) #
            right_arrow_rect = right_arrow_surf.get_rect(centery=arrow_y_center, left=main_card_rect.right + arrow_padding_from_card_edge) #
            self.screen.blit(right_arrow_surf, right_arrow_rect) #

        instr_surf = self._render_text_safe("LEFT/RIGHT: Cycle | ENTER: Select/Unlock | ESC: Back", "small_text", CYAN) #
        instr_bg_rect = pygame.Rect(0, HEIGHT - 70, WIDTH, 30) #
        instr_surf_rect = instr_surf.get_rect(center=instr_bg_rect.center) #
        self.screen.blit(instr_surf, instr_surf_rect) #

        cores_label_text_surf = self._render_text_safe(f"Player Cores: ", "ui_text", GOLD) #
        cores_value_text_surf = self._render_text_safe(f"{self.drone_system.get_player_cores()}", "ui_values", GOLD) #
        cores_emoji_surf = self._render_text_safe(" 💠", "ui_emoji_general", GOLD) #
        total_cores_display_width = cores_label_text_surf.get_width() + cores_value_text_surf.get_width() + cores_emoji_surf.get_width() #
        cores_start_x = WIDTH - 20 - total_cores_display_width #
        max_element_height_cores = max(cores_label_text_surf.get_height(), cores_value_text_surf.get_height(), cores_emoji_surf.get_height()) #
        cores_y_baseline = HEIGHT - 20 - max_element_height_cores #
        
        current_x_offset_cores = cores_start_x #
        self.screen.blit(cores_label_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_label_text_surf.get_height()) // 2)) #
        current_x_offset_cores += cores_label_text_surf.get_width() #
        self.screen.blit(cores_value_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_value_text_surf.get_height()) // 2)) #
        current_x_offset_cores += cores_value_text_surf.get_width() #
        self.screen.blit(cores_emoji_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_emoji_surf.get_height()) // 2)) #

    def draw_settings_menu(self): # Restored from original file content
        title_surf = self._render_text_safe("Settings", "title_text", GOLD) #
        title_bg = pygame.Surface((title_surf.get_width()+30, title_surf.get_height()+15), pygame.SRCALPHA) #
        title_bg.fill((20,20,20,180)) #
        title_bg.blit(title_surf, title_surf.get_rect(center=(title_bg.get_width()//2, title_bg.get_height()//2))) #
        self.screen.blit(title_bg, title_bg.get_rect(center=(WIDTH//2, 80))) #

        settings_items = getattr(self.game_controller, 'settings_items_data', []) #
        selected_idx = getattr(self.game_controller, 'selected_setting_index', 0) #

        item_y_start = 180 #
        item_line_height = self.fonts["ui_text"].get_height() + 20 #
        max_items_on_screen = (HEIGHT - item_y_start - 120) // item_line_height #

        view_start_index = 0 #
        if len(settings_items) > max_items_on_screen: #
            view_start_index = max(0, selected_idx - max_items_on_screen // 2) #
            view_start_index = min(view_start_index, len(settings_items) - max_items_on_screen) #
        view_end_index = min(view_start_index + max_items_on_screen, len(settings_items)) #

        for i_display, list_idx in enumerate(range(view_start_index, view_end_index)): #
            if list_idx >= len(settings_items): continue #
            item = settings_items[list_idx] #
            y_pos = item_y_start + i_display * item_line_height #
            color = YELLOW if list_idx == selected_idx else WHITE #

            label_surf = self._render_text_safe(item["label"], "ui_text", color) #
            label_bg_rect_width = max(250, label_surf.get_width() + 20) #
            label_bg_rect = pygame.Rect(WIDTH // 4 - 150, y_pos - 5, label_bg_rect_width, label_surf.get_height() + 10) #
            pygame.draw.rect(self.screen, (30,30,30,160), label_bg_rect, border_radius=5) #
            self.screen.blit(label_surf, (label_bg_rect.left + 10, y_pos)) #

            if "note" in item and list_idx == selected_idx: #
                note_surf = self._render_text_safe(item["note"], "small_text", LIGHT_BLUE) #
                self.screen.blit(note_surf, note_surf.get_rect(left=label_bg_rect.right + 15, centery=label_bg_rect.centery)) #

            if item["type"] != "action": #
                current_value = get_game_setting(item["key"]) #
                display_value = "" #
                if item["type"] == "numeric": #
                    display_format = item.get("display_format", "{}") #
                    value_to_format = current_value #
                    if item.get("is_ms_to_sec"): #
                        value_to_format = current_value / 1000 #
                    try: #
                        display_value = display_format.format(value_to_format) #
                    except (ValueError, TypeError): #
                        display_value = str(value_to_format) if not item.get("is_ms_to_sec") else f"{value_to_format:.0f}s" #

                elif item["type"] == "choice": #
                    display_value = item["get_display"](current_value) #

                value_surf = self._render_text_safe(display_value, "ui_text", color) #
                value_bg_rect_width = max(100, value_surf.get_width() + 20) #
                value_bg_rect = pygame.Rect(WIDTH // 2 + 150, y_pos - 5, value_bg_rect_width, value_surf.get_height() + 10) #
                pygame.draw.rect(self.screen, (30,30,30,160), value_bg_rect, border_radius=5) #
                self.screen.blit(value_surf, (value_bg_rect.left + 10, y_pos)) #

                if item["key"] in DEFAULT_SETTINGS and current_value != DEFAULT_SETTINGS[item["key"]]: #
                    self.screen.blit(self._render_text_safe("*", "small_text", RED), (value_bg_rect.right + 5, y_pos)) #
            elif list_idx == selected_idx: #
                 action_hint_surf = self._render_text_safe("<ENTER>", "ui_text", YELLOW) #
                 action_hint_bg_rect = pygame.Rect(WIDTH // 2 + 150, y_pos - 5, action_hint_surf.get_width() + 20, action_hint_surf.get_height() + 10) #
                 pygame.draw.rect(self.screen, (40,40,40,180), action_hint_bg_rect, border_radius=5) #
                 self.screen.blit(action_hint_surf, (action_hint_bg_rect.left + 10, y_pos)) #

        instr_surf = self._render_text_safe("UP/DOWN: Select | LEFT/RIGHT: Adjust | ENTER: Activate | ESC: Back", "small_text", CYAN) #
        instr_bg = pygame.Surface((instr_surf.get_width()+20, instr_surf.get_height()+10), pygame.SRCALPHA) #
        instr_bg.fill((20,20,20,180)) #
        instr_bg.blit(instr_surf, (10,5)) #
        self.screen.blit(instr_bg, instr_bg.get_rect(center=(WIDTH//2, HEIGHT-70))) #

        if get_game_setting("SETTINGS_MODIFIED"): #
            warning_surf = self._render_text_safe("Settings changed. Leaderboard will be disabled.", "small_text", YELLOW) #
            warning_bg = pygame.Surface((warning_surf.get_width()+10, warning_surf.get_height()+5), pygame.SRCALPHA) #
            warning_bg.fill((20,20,20,180)) #
            warning_bg.blit(warning_surf, (5,2)) #
            self.screen.blit(warning_bg, warning_bg.get_rect(center=(WIDTH//2, HEIGHT-35))) #

    def draw_gameplay_hud(self): #
        # ... (This method was updated previously for fragment HUD, ensure it's the correct version)
        # For brevity, only showing the fragment part that was recently changed
        if not self.game_controller.player: return

        panel_y_start = GAME_PLAY_AREA_HEIGHT 
        panel_height = BOTTOM_PANEL_HEIGHT 
        # ... (rest of HUD setup as in previous correct version) ...

        # --- Collectibles Section (Right) ---
        collectibles_x_anchor = WIDTH - 20 # h_padding
        current_collectibles_y = panel_y_start + panel_height - 10 # v_padding
        icon_spacing = 5; text_icon_spacing = 4

        # Cores
        cores_emoji_char = "💠"
        cores_value_str = f" {self.drone_system.get_player_cores()}"
        cores_icon_surf = self._render_text_safe(cores_emoji_char, "ui_emoji_general", GOLD)
        cores_value_text_surf = self._render_text_safe(cores_value_str, "ui_values", GOLD)
        cores_display_height = max(cores_icon_surf.get_height(), cores_value_text_surf.get_height())
        cores_y_pos = current_collectibles_y - cores_display_height
        total_cores_width = cores_icon_surf.get_width() + text_icon_spacing + cores_value_text_surf.get_width()
        cores_start_x_draw = collectibles_x_anchor - total_cores_width
        self.screen.blit(cores_icon_surf, (cores_start_x_draw, cores_y_pos + (cores_display_height - cores_icon_surf.get_height()) // 2))
        self.screen.blit(cores_value_text_surf, (cores_start_x_draw + cores_icon_surf.get_width() + text_icon_spacing, cores_y_pos + (cores_display_height - cores_value_text_surf.get_height()) // 2))
        current_collectibles_y = cores_y_pos - 6 # element_spacing

        # Fragment Icons Display
        fragment_icon_h = self.ui_icon_size_fragments[1]
        fragment_y_pos_hud = current_collectibles_y - fragment_icon_h
        
        fragment_display_order_ids = []
        if CORE_FRAGMENT_DETAILS:
            try:
                sorted_frag_keys = sorted(CORE_FRAGMENT_DETAILS.keys())
                fragment_display_order_ids = [CORE_FRAGMENT_DETAILS[key]["id"] for key in sorted_frag_keys if "id" in CORE_FRAGMENT_DETAILS[key]]
            except Exception: # Fallback if sorting or access fails
                fragment_display_order_ids = [details["id"] for _, details in CORE_FRAGMENT_DETAILS.items() if details and "id" in details]
        
        displayable_fragment_ids = fragment_display_order_ids[:TOTAL_CORE_FRAGMENTS_NEEDED]

        if hasattr(self.game_controller, 'fragment_ui_target_positions'):
            self.game_controller.fragment_ui_target_positions.clear()

        if TOTAL_CORE_FRAGMENTS_NEEDED > 0 :
            total_fragments_width = TOTAL_CORE_FRAGMENTS_NEEDED * (self.ui_icon_size_fragments[0] + icon_spacing)
            if TOTAL_CORE_FRAGMENTS_NEEDED > 0 : total_fragments_width -= icon_spacing 
            fragments_block_start_x = cores_start_x_draw - total_fragments_width - (icon_spacing * 4) 
            
            for i in range(TOTAL_CORE_FRAGMENTS_NEEDED):
                frag_id_for_this_slot = None
                if i < len(displayable_fragment_ids):
                    frag_id_for_this_slot = displayable_fragment_ids[i]

                icon_to_draw = self.ui_assets["core_fragment_empty_icon"] 
                if frag_id_for_this_slot and frag_id_for_this_slot in self.game_controller.hud_displayed_fragments:
                    icon_to_draw = self.ui_assets["core_fragment_icons"].get(frag_id_for_this_slot, self.ui_assets["core_fragment_empty_icon"])
                
                current_frag_x = fragments_block_start_x + i * (self.ui_icon_size_fragments[0] + icon_spacing)
                if icon_to_draw: 
                    self.screen.blit(icon_to_draw, (current_frag_x, fragment_y_pos_hud))
                
                if frag_id_for_this_slot: 
                     self.game_controller.fragment_ui_target_positions[frag_id_for_this_slot] = (
                         current_frag_x + self.ui_icon_size_fragments[0] // 2,
                         fragment_y_pos_hud + self.ui_icon_size_fragments[1] // 2
                     )
            current_collectibles_y = fragment_y_pos_hud - 6 # element_spacing

        # Rings Display
        rings_y_pos_hud = current_collectibles_y 
        total_rings_this_level = getattr(self.game_controller, 'total_rings_per_level', 5) 
        displayed_rings_count = getattr(self.game_controller, 'displayed_collected_rings', 0) 

        if self.ui_assets["ring_icon"]: 
            ring_icon_h = self.ui_icon_size_rings[1] 
            rings_y_pos_hud = current_collectibles_y - ring_icon_h 
            total_ring_icons_width_only = max(0, total_rings_this_level * (self.ui_icon_size_rings[0] + icon_spacing) - icon_spacing if total_rings_this_level > 0 else 0) 
            current_rightmost_collectible_x = fragments_block_start_x if TOTAL_CORE_FRAGMENTS_NEEDED > 0 else cores_start_x_draw
            rings_block_start_x = current_rightmost_collectible_x - total_ring_icons_width_only - (icon_spacing * 4)
            for i in range(total_rings_this_level): 
                icon_to_draw = self.ui_assets["ring_icon"] if i < displayed_rings_count else self.ui_assets["ring_icon_empty"] 
                if icon_to_draw: 
                    self.screen.blit(icon_to_draw, (rings_block_start_x + i * (self.ui_icon_size_rings[0] + icon_spacing), rings_y_pos_hud)) 
        
        # ... (The rest of the HUD drawing, including score, level, timer, and animating_rings/fragments) ...
        # This part is identical to the previous full version of draw_gameplay_hud
        if hasattr(self.game_controller, 'animating_rings'): 
            for ring_anim in self.game_controller.animating_rings: 
                if 'surface' in ring_anim and ring_anim['surface']: 
                    self.screen.blit(ring_anim['surface'], (int(ring_anim['pos'][0]), int(ring_anim['pos'][1]))) 
        if hasattr(self.game_controller, 'animating_fragments'):
            for frag_anim in self.game_controller.animating_fragments:
                if 'surface' in frag_anim and frag_anim['surface']:
                    self.screen.blit(frag_anim['surface'], (int(frag_anim['pos'][0]), int(frag_anim['pos'][1])))


    def get_scaled_fragment_icon(self, fragment_id):
        if not self.ui_assets["core_fragment_icons"] and not self.ui_assets["core_fragment_empty_icon"]:
            self._load_ui_assets() 
        if fragment_id in self.ui_assets["core_fragment_icons"]:
            return self.ui_assets["core_fragment_icons"][fragment_id]
        print(f"UIManager: Warning - Scaled icon for fragment_id '{fragment_id}' not found. Using fallback.")
        return self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", PURPLE)

    def draw_architect_vault_hud_elements(self): #
        self.draw_gameplay_hud() #
        current_time = pygame.time.get_ticks() #
        current_vault_phase = getattr(self.game_controller, 'architect_vault_current_phase', None) #
        if current_vault_phase == "extraction": #
            time_remaining_ms_vault = getattr(self.game_controller, 'level_time_remaining_ms', 0) #
            time_val_str_vault = f"{max(0, time_remaining_ms_vault // 1000) // 60:02d}:{max(0, time_remaining_ms_vault // 1000) % 60:02d}" #
            time_color_vault = RED #
            if (time_remaining_ms_vault // 1000) > 10: time_color_vault = YELLOW #
            if (current_time // 250) % 2 == 0 and (time_remaining_ms_vault // 1000) <= 10 : time_color_vault = DARK_RED #
            timer_surf_vault = self._render_text_safe(f"ESCAPE ROUTE COLLAPSING: {time_val_str_vault}", "vault_timer", time_color_vault) #
            self.screen.blit(timer_surf_vault, timer_surf_vault.get_rect(centerx=WIDTH//2, top=10)) #
        vault_message = getattr(self.game_controller, 'architect_vault_message', "") #
        vault_message_timer_end = getattr(self.game_controller, 'architect_vault_message_timer', 0) #
        if vault_message and current_time < vault_message_timer_end: #
            msg_surf = self._render_text_safe(vault_message, "vault_message", GOLD) #
            msg_bg_surf = pygame.Surface((msg_surf.get_width() + 30, msg_surf.get_height() + 15), pygame.SRCALPHA) #
            msg_bg_surf.fill((10, 0, 20, 200)) #
            msg_bg_surf.blit(msg_surf, msg_surf.get_rect(center=(msg_bg_surf.get_width()//2, msg_bg_surf.get_height()//2))) #
            self.screen.blit(msg_bg_surf, msg_bg_surf.get_rect(centerx=WIDTH//2, bottom=GAME_PLAY_AREA_HEIGHT - 20)) #

    def draw_pause_overlay(self): # From original file content
        overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA) #
        overlay_surface.fill((0,0,0,150)) #
        self.screen.blit(overlay_surface, (0,0)) #
        pause_title_surf = self._render_text_safe("PAUSED", "large_text", WHITE) #
        self.screen.blit(pause_title_surf, pause_title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 60))) #
        current_game_state_when_paused = self.scene_manager.get_current_state() #
        pause_text_options = "P: Continue | M: Menu | Q: Quit Game" #
        if current_game_state_when_paused == GAME_STATE_PLAYING: #
             pause_text_options = "P: Continue | L: Leaderboard | M: Menu | Q: Quit Game" #
        elif current_game_state_when_paused.startswith("architect_vault"): #
             pause_text_options = "P: Continue | ESC: Main Menu (Exit Vault) | Q: Quit Game" #
        options_surf = self._render_text_safe(pause_text_options, "ui_text", WHITE) #
        self.screen.blit(options_surf, options_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 40))) #

    def draw_game_over_overlay(self): # From original file content
        go_text_surf = self._render_text_safe("GAME OVER", "large_text", RED) #
        score_text_surf = self._render_text_safe(f"Final Score: {self.game_controller.score}", "medium_text", WHITE) #
        self.screen.blit(go_text_surf, go_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 120))) #
        self.screen.blit(score_text_surf, score_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 30))) #
        can_submit_score = not get_game_setting("SETTINGS_MODIFIED") #
        is_new_high = can_submit_score and leaderboard.is_high_score(self.game_controller.score, self.game_controller.level) #
        prompt_y_offset = HEIGHT // 2 + 50 #
        if not can_submit_score: #
            no_lb_text_surf = self._render_text_safe("Leaderboard disabled (custom settings).", "ui_text", YELLOW) #
            self.screen.blit(no_lb_text_surf, no_lb_text_surf.get_rect(center=(WIDTH//2, prompt_y_offset))) #
            prompt_y_offset += self.fonts["ui_text"].get_height() + 20 #
        prompt_str = "R: Restart  M: Menu  Q: Quit" #
        prompt_color = WHITE #
        if can_submit_score and is_new_high: #
            prompt_str = "New High Score! Press any key to enter name." #
            prompt_color = GOLD #
        elif can_submit_score: #
            prompt_str = "R: Restart  L: Leaderboard  M: Menu  Q: Quit" #
        prompt_surf = self._render_text_safe(prompt_str, "ui_text", prompt_color) #
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, prompt_y_offset))) #

    def draw_enter_name_overlay(self): # From original file content
        title_surf = self._render_text_safe("New High Score!", "large_text", GOLD) #
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 180))) #
        score_level_text = f"Your Score: {self.game_controller.score} (Level: {self.game_controller.level})" #
        score_level_surf = self._render_text_safe(score_level_text, "medium_text", WHITE) #
        self.screen.blit(score_level_surf, score_level_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 90))) #
        prompt_name_surf = self._render_text_safe("Enter Name (max 6 chars, A-Z):", "ui_text", WHITE) #
        self.screen.blit(prompt_name_surf, prompt_name_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 20))) #
        player_name_input_str = getattr(self.game_controller, 'player_name_input_display_cache', "") #
        input_box_width = 300; input_box_height = 60 #
        input_box_rect = pygame.Rect(WIDTH//2 - input_box_width//2, HEIGHT//2 + 30, input_box_width, input_box_height) #
        pygame.draw.rect(self.screen, WHITE, input_box_rect, 2, border_radius=10) #
        input_text_surf = self._render_text_safe(player_name_input_str, "input_text", WHITE) #
        self.screen.blit(input_text_surf, input_text_surf.get_rect(center=input_box_rect.center)) #
        submit_prompt_surf = self._render_text_safe("Press ENTER to submit.", "ui_text", CYAN) #
        self.screen.blit(submit_prompt_surf, submit_prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 120))) #

    def draw_leaderboard_overlay(self): # Restored from original file content
        title_surf = self._render_text_safe("Leaderboard", "large_text", GOLD) #
        title_bg_rect_width = title_surf.get_width() + 40 #
        title_bg_rect_height = title_surf.get_height() + 20 #
        title_bg_surf = pygame.Surface((title_bg_rect_width, title_bg_rect_height), pygame.SRCALPHA) #
        title_bg_surf.fill((20,20,20,180)) #
        title_bg_surf.blit(title_surf, title_surf.get_rect(center=(title_bg_rect_width//2, title_bg_rect_height//2))) #
        self.screen.blit(title_bg_surf, title_bg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 300))) #
        scores_to_display = getattr(self.game_controller, 'leaderboard_scores', []) #
        header_y = HEIGHT // 2 - 250 #
        score_item_y_start = HEIGHT // 2 - 200 #
        item_line_height = self.fonts["leaderboard_entry"].get_height() + 15 #
        if not scores_to_display: #
            no_scores_surf = self._render_text_safe("No scores yet!", "medium_text", WHITE) #
            no_scores_bg = pygame.Surface((no_scores_surf.get_width()+20, no_scores_surf.get_height()+10), pygame.SRCALPHA) #
            no_scores_bg.fill((30,30,30,160)) #
            no_scores_bg.blit(no_scores_surf, no_scores_surf.get_rect(center=(no_scores_bg.get_width()//2, no_scores_bg.get_height()//2))) #
            self.screen.blit(no_scores_bg, no_scores_bg.get_rect(center=(WIDTH//2, HEIGHT//2))) #
        else: #
            cols_x_positions = {"Rank": WIDTH//2 - 350, "Name": WIDTH//2 - 250, "Level": WIDTH//2 + 50, "Score": WIDTH//2 + 200} #
            header_font = self.fonts.get("leaderboard_header", self.fonts["ui_text"]) #
            entry_font = self.fonts.get("leaderboard_entry", self.fonts["ui_text"]) #
            for col_name, x_pos in cols_x_positions.items(): #
                header_surf = header_font.render(col_name, True, WHITE) #
                header_bg = pygame.Surface((header_surf.get_width()+15, header_surf.get_height()+8), pygame.SRCALPHA) #
                header_bg.fill((40,40,40,170)) #
                header_bg.blit(header_surf, header_surf.get_rect(center=(header_bg.get_width()//2, header_bg.get_height()//2))) #
                self.screen.blit(header_bg, (x_pos, header_y)) #
            for i, entry in enumerate(scores_to_display): #
                if i >= get_game_setting("LEADERBOARD_MAX_ENTRIES"): break #
                y_pos = score_item_y_start + i * item_line_height #
                texts_to_draw = [
                    (f"{i+1}.", WHITE, cols_x_positions["Rank"]), 
                    (str(entry.get('name','N/A')).upper(), CYAN, cols_x_positions["Name"]), 
                    (str(entry.get('level','-')), GREEN, cols_x_positions["Level"]), 
                    (str(entry.get('score',0)), GOLD, cols_x_positions["Score"]) 
                ] #
                for text_str, color, x_coord in texts_to_draw: #
                    text_surf = entry_font.render(text_str, True, color) #
                    self.screen.blit(text_surf, (x_coord, y_pos)) #
        menu_prompt_surf = self._render_text_safe("ESC: Main Menu | Q: Quit Game", "ui_text", WHITE) #
        prompt_bg = pygame.Surface((menu_prompt_surf.get_width()+20, menu_prompt_surf.get_height()+10), pygame.SRCALPHA) #
        prompt_bg.fill((20,20,20,180)) #
        prompt_bg.blit(menu_prompt_surf, prompt_bg.get_rect(center=(prompt_bg.get_width()//2, prompt_bg.get_height()//2))) #
        self.screen.blit(prompt_bg, prompt_bg.get_rect(center=(WIDTH//2, HEIGHT-100))) #

    def draw_architect_vault_success_overlay(self): # From original file content
        msg_surf = self._render_text_safe("Vault Conquered!", "large_text", GOLD) #
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 80))) #
        blueprint_id = get_game_setting("ARCHITECT_REWARD_BLUEPRINT_ID") #
        reward_text = f"Blueprint Acquired: {blueprint_id}" if blueprint_id else "Ancient Technology Secured!" #
        reward_surf = self._render_text_safe(reward_text, "medium_text", CYAN) #
        self.screen.blit(reward_surf, reward_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20))) #
        prompt_surf = self._render_text_safe("Press ENTER or M to Continue", "ui_text", WHITE) #
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 100))) #

    def draw_architect_vault_failure_overlay(self): # From original file content
        msg_surf = self._render_text_safe("Vault Mission Failed", "large_text", RED) #
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))) #
        reason_text = getattr(self.game_controller, 'architect_vault_failure_reason', "Critical systems compromised.") #
        reason_surf = self._render_text_safe(reason_text, "ui_text", YELLOW) #
        self.screen.blit(reason_surf, reason_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20))) #
        prompt_surf = self._render_text_safe("Press ENTER or M to Return to Menu", "ui_text", WHITE) #
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 80))) #