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

    def draw_main_menu(self): # From original file content
        if self.ui_assets["menu_background"]: #
            try: #
                scaled_bg = pygame.transform.smoothscale(self.ui_assets["menu_background"], (WIDTH, HEIGHT)) #
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

    def draw_drone_select_menu(self): # From original file content (abbreviated for response length)
        # ... (Full implementation from original file is assumed here)
        title_surf = self._render_text_safe("Select Drone", "title_text", GOLD) #
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 70)) #
        self.screen.blit(title_surf, title_rect) #
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


    def draw_settings_menu(self): # From original file content (abbreviated)
        # ... (Full implementation from original file is assumed here)
        title_surf = self._render_text_safe("Settings", "title_text", GOLD) #
        title_bg = pygame.Surface((title_surf.get_width()+30, title_surf.get_height()+15), pygame.SRCALPHA) #
        title_bg.fill((20,20,20,180)) #
        title_bg.blit(title_surf, title_surf.get_rect(center=(title_bg.get_width()//2, title_bg.get_height()//2))) #
        self.screen.blit(title_bg, title_bg.get_rect(center=(WIDTH//2, 80))) #
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


    def draw_gameplay_hud(self): 
        if not self.game_controller.player: return 

        panel_y_start = GAME_PLAY_AREA_HEIGHT 
        panel_height = BOTTOM_PANEL_HEIGHT 
        panel_surf = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA) 
        panel_surf.fill((20,25,35,220)) 
        pygame.draw.line(panel_surf, (80,120,170,200), (0,0), (WIDTH,0), 2) 
        self.screen.blit(panel_surf, (0, panel_y_start)) 

        h_padding = 20; v_padding = 10; element_spacing = 6; bar_height = 18; 
        icon_to_bar_gap = 10; icon_spacing = 5; text_icon_spacing = 4 
        current_time_ticks = pygame.time.get_ticks() 

        label_font = self.fonts["ui_text"] 
        value_font = self.fonts["ui_values"] 
        emoji_general_font = self.fonts["ui_emoji_general"] 

        # --- Vitals Section (Left) ---
        vitals_x_start = h_padding 
        current_vitals_y = panel_y_start + panel_height - v_padding 
        vitals_section_width = int(WIDTH / 3.2) 
        min_bar_segment_width = 25 
        bar_segment_reduction_factor = 0.85 

        life_icon_surf = self.ui_assets.get("current_drone_life_icon") 
        if life_icon_surf: 
            lives_y_pos = current_vitals_y - self.ui_icon_size_lives[1] 
            lives_draw_x = vitals_x_start 
            for i in range(self.game_controller.lives): 
                self.screen.blit(life_icon_surf, (lives_draw_x + i * (self.ui_icon_size_lives[0] + icon_spacing), lives_y_pos)) 
            current_vitals_y = lives_y_pos - element_spacing 

        player_obj = self.game_controller.player 
        health_bar_y_pos = current_vitals_y - bar_height 
        health_icon_char = "❤️" 
        health_icon_surf = self._render_text_safe(health_icon_char, "ui_emoji_small", RED) 
        self.screen.blit(health_icon_surf, (vitals_x_start, health_bar_y_pos + (bar_height - health_icon_surf.get_height()) // 2)) 
        
        bar_start_x_health = vitals_x_start + health_icon_surf.get_width() + icon_to_bar_gap 
        available_width_for_health_bar = vitals_section_width - (health_icon_surf.get_width() + icon_to_bar_gap) 
        bar_segment_width_health = max(min_bar_segment_width, int(available_width_for_health_bar * bar_segment_reduction_factor)) 
        health_percentage = player_obj.health / player_obj.max_health if player_obj.max_health > 0 else 0 
        health_bar_width_fill = int(bar_segment_width_health * health_percentage) 
        health_fill_color = GREEN if health_percentage > 0.6 else YELLOW if health_percentage > 0.3 else RED 
        pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_health, health_bar_y_pos, bar_segment_width_health, bar_height)) 
        if health_bar_width_fill > 0: 
            pygame.draw.rect(self.screen, health_fill_color, (bar_start_x_health, health_bar_y_pos, health_bar_width_fill, bar_height)) 
        pygame.draw.rect(self.screen, WHITE, (bar_start_x_health, health_bar_y_pos, bar_segment_width_health, bar_height), 1) 
        current_vitals_y = health_bar_y_pos - element_spacing 

        weapon_bar_y_pos = current_vitals_y - bar_height 
        weapon_icon_char = WEAPON_MODE_ICONS.get(player_obj.current_weapon_mode, "💥") 
        weapon_icon_surf = self._render_text_safe(weapon_icon_char, "ui_emoji_small", ORANGE) 
        self.screen.blit(weapon_icon_surf, (vitals_x_start, weapon_bar_y_pos + (bar_height - weapon_icon_surf.get_height()) // 2)) 
        bar_start_x_weapon = vitals_x_start + weapon_icon_surf.get_width() + icon_to_bar_gap 
        bar_segment_width_weapon = max(min_bar_segment_width, int((vitals_section_width - (weapon_icon_surf.get_width() + icon_to_bar_gap)) * bar_segment_reduction_factor)) 
        charge_fill_pct = 0.0 
        weapon_ready_color = PLAYER_BULLET_COLOR 
        cooldown_duration = player_obj.current_shoot_cooldown 
        time_since_last_shot = current_time_ticks - player_obj.last_shot_time 
        if player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER") or \
           player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS"): 
            weapon_ready_color = MISSILE_COLOR 
            time_since_last_shot = current_time_ticks - player_obj.last_missile_shot_time 
            cooldown_duration = player_obj.current_missile_cooldown 
        elif player_obj.current_weapon_mode == get_game_setting("WEAPON_MODE_LIGHTNING"): 
            weapon_ready_color = LIGHTNING_COLOR 
            time_since_last_shot = current_time_ticks - player_obj.last_lightning_time 
            cooldown_duration = player_obj.current_lightning_cooldown 
        if cooldown_duration > 0: 
            charge_fill_pct = min(1.0, time_since_last_shot / cooldown_duration) 
        else: 
            charge_fill_pct = 1.0 
        charge_bar_fill_color = weapon_ready_color if charge_fill_pct >= 1.0 else ORANGE 
        weapon_bar_width_fill = int(bar_segment_width_weapon * charge_fill_pct) 
        pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_weapon, weapon_bar_y_pos, bar_segment_width_weapon, bar_height)) 
        if weapon_bar_width_fill > 0: 
            pygame.draw.rect(self.screen, charge_bar_fill_color, (bar_start_x_weapon, weapon_bar_y_pos, weapon_bar_width_fill, bar_height)) 
        pygame.draw.rect(self.screen, WHITE, (bar_start_x_weapon, weapon_bar_y_pos, bar_segment_width_weapon, bar_height), 1) 
        current_vitals_y = weapon_bar_y_pos - element_spacing 

        active_powerup_for_ui = player_obj.active_powerup_type 
        if active_powerup_for_ui and (player_obj.shield_active or player_obj.speed_boost_active): 
            powerup_bar_y_pos = current_vitals_y - bar_height 
            powerup_icon_char = "" 
            powerup_bar_fill_color = WHITE 
            powerup_fill_percentage = 0.0 
            powerup_details_config = POWERUP_TYPES.get(active_powerup_for_ui, {}) 
            if active_powerup_for_ui == "shield" and player_obj.shield_active: 
                powerup_icon_char = "🛡️" 
                powerup_bar_fill_color = powerup_details_config.get("color", LIGHT_BLUE) 
                remaining_time = player_obj.shield_end_time - current_time_ticks 
                if player_obj.shield_duration > 0 and remaining_time > 0: 
                    powerup_fill_percentage = remaining_time / player_obj.shield_duration 
            elif active_powerup_for_ui == "speed_boost" and player_obj.speed_boost_active: 
                powerup_icon_char = "💨" 
                powerup_bar_fill_color = powerup_details_config.get("color", GREEN) 
                remaining_time = player_obj.speed_boost_end_time - current_time_ticks 
                if player_obj.speed_boost_duration > 0 and remaining_time > 0: 
                    powerup_fill_percentage = remaining_time / player_obj.speed_boost_duration 
            powerup_fill_percentage = max(0, min(1, powerup_fill_percentage)) 
            if powerup_icon_char: 
                powerup_icon_surf = self._render_text_safe(powerup_icon_char, "ui_emoji_small", WHITE) 
                self.screen.blit(powerup_icon_surf, (vitals_x_start, powerup_bar_y_pos + (bar_height - powerup_icon_surf.get_height()) // 2)) 
                bar_start_x_powerup = vitals_x_start + powerup_icon_surf.get_width() + icon_to_bar_gap 
                bar_segment_width_powerup = max(min_bar_segment_width, int((vitals_section_width - (powerup_icon_surf.get_width() + icon_to_bar_gap)) * bar_segment_reduction_factor)) 
                bar_width_fill_powerup = int(bar_segment_width_powerup * powerup_fill_percentage) 
                pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_powerup, powerup_bar_y_pos, bar_segment_width_powerup, bar_height)) 
                if bar_width_fill_powerup > 0: 
                    pygame.draw.rect(self.screen, powerup_bar_fill_color, (bar_start_x_powerup, powerup_bar_y_pos, bar_width_fill_powerup, bar_height)) 
                pygame.draw.rect(self.screen, WHITE, (bar_start_x_powerup, powerup_bar_y_pos, bar_segment_width_powerup, bar_height), 1) 

        # --- Collectibles Section (Right) ---
        collectibles_x_anchor = WIDTH - h_padding 
        current_collectibles_y = panel_y_start + panel_height - v_padding 
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
        current_collectibles_y = cores_y_pos - element_spacing 

        fragment_icon_h = self.ui_icon_size_fragments[1]
        fragment_y_pos_hud = current_collectibles_y - fragment_icon_h
        
        fragment_display_order_ids = []
        if CORE_FRAGMENT_DETAILS:
            try:
                sorted_frag_keys = sorted(CORE_FRAGMENT_DETAILS.keys())
                fragment_display_order_ids = [CORE_FRAGMENT_DETAILS[key]["id"] for key in sorted_frag_keys if "id" in CORE_FRAGMENT_DETAILS[key]]
            except Exception as e:
                print(f"UIManager: Error creating fragment display order: {e}. Using unsorted.")
                fragment_display_order_ids = [details["id"] for _, details in CORE_FRAGMENT_DETAILS.items() if details and "id" in details]
        
        displayable_fragment_ids = fragment_display_order_ids[:TOTAL_CORE_FRAGMENTS_NEEDED]

        self.game_controller.fragment_ui_target_positions.clear()

        if TOTAL_CORE_FRAGMENTS_NEEDED > 0 :
            total_fragments_width = TOTAL_CORE_FRAGMENTS_NEEDED * (self.ui_icon_size_fragments[0] + icon_spacing)
            if TOTAL_CORE_FRAGMENTS_NEEDED > 0 : total_fragments_width -= icon_spacing 
            fragments_block_start_x = cores_start_x_draw - total_fragments_width - (icon_spacing * 4) 
            
            for i in range(TOTAL_CORE_FRAGMENTS_NEEDED):
                frag_id_for_this_slot = None
                if i < len(displayable_fragment_ids):
                    frag_id_for_this_slot = displayable_fragment_ids[i]

                icon_to_draw = self.ui_assets["core_fragment_empty_icon"] # Always start with empty

                # Check if this fragment's animation is complete and it should be shown as filled
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
            current_collectibles_y = fragment_y_pos_hud - element_spacing

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
        
        info_y_pos = panel_y_start + (panel_height - label_font.get_height()) // 2 
        score_emoji_char = "🏆 " 
        score_text_str = f"Score: {self.game_controller.score}" 
        score_emoji_surf = self._render_text_safe(score_emoji_char, "ui_emoji_general", GOLD) 
        score_text_surf = self._render_text_safe(score_text_str, "ui_text", GOLD) 
        level_emoji_char = "🎯 " 
        level_text_str = f"Level: {self.game_controller.level}" 
        current_scene_state = self.scene_manager.get_current_state() 
        if current_scene_state == GAME_STATE_BONUS_LEVEL_PLAYING: level_text_str = "Bonus!" 
        elif current_scene_state.startswith("architect_vault"): level_text_str = "Architect's Vault" 
        level_emoji_surf = self._render_text_safe(level_emoji_char, "ui_emoji_general", CYAN) 
        level_text_surf = self._render_text_safe(level_text_str, "ui_text", CYAN) 
        time_icon_char = "⏱ " 
        time_ms_to_display = self.game_controller.level_time_remaining_ms 
        if current_scene_state == GAME_STATE_BONUS_LEVEL_PLAYING: 
            elapsed_bonus_time_ms = current_time_ticks - getattr(self.game_controller, 'bonus_level_timer_start', current_time_ticks) 
            bonus_duration_ms = getattr(self.game_controller, 'bonus_level_duration_ms', 60000) 
            time_ms_to_display = max(0, bonus_duration_ms - elapsed_bonus_time_ms) 
        time_seconds_total = max(0, time_ms_to_display // 1000) 
        time_value_str = f"{time_seconds_total // 60:02d}:{time_seconds_total % 60:02d}" 
        time_color = WHITE 
        is_vault_extraction = (current_scene_state.startswith("architect_vault") and \
                               getattr(self.game_controller, 'architect_vault_current_phase', None) == "extraction") 
        if not is_vault_extraction: 
            if time_seconds_total <= 10: time_color = RED if (current_time_ticks // 250) % 2 == 0 else DARK_RED 
            elif time_seconds_total <= 30: time_color = YELLOW 
        time_icon_surf = self._render_text_safe(time_icon_char, "ui_emoji_general", time_color) 
        time_value_surf = self._render_text_safe(time_value_str, self.fonts["ui_values"], time_color) 
        spacing_between_center_elements = 25 
        center_elements_total_width = (
            score_emoji_surf.get_width() + text_icon_spacing + score_text_surf.get_width() + 
            spacing_between_center_elements + 
            level_emoji_surf.get_width() + text_icon_spacing + level_text_surf.get_width() + 
            spacing_between_center_elements + 
            time_icon_surf.get_width() + text_icon_spacing + time_value_surf.get_width() 
        ) 
        current_info_x = (WIDTH - center_elements_total_width) // 2 
        self.screen.blit(score_emoji_surf, (current_info_x, info_y_pos + (score_text_surf.get_height() - score_emoji_surf.get_height()) // 2)) 
        current_info_x += score_emoji_surf.get_width() + text_icon_spacing 
        self.screen.blit(score_text_surf, (current_info_x, info_y_pos)) 
        current_info_x += score_text_surf.get_width() + spacing_between_center_elements 
        self.screen.blit(level_emoji_surf, (current_info_x, info_y_pos + (level_text_surf.get_height() - level_emoji_surf.get_height()) // 2)) 
        current_info_x += level_emoji_surf.get_width() + text_icon_spacing 
        self.screen.blit(level_text_surf, (current_info_x, info_y_pos)) 
        current_info_x += level_text_surf.get_width() + spacing_between_center_elements 
        if not is_vault_extraction: 
            self.screen.blit(time_icon_surf, (current_info_x, info_y_pos + (time_value_surf.get_height() - time_icon_surf.get_height()) // 2)) 
            current_info_x += time_icon_surf.get_width() + text_icon_spacing 
            self.screen.blit(time_value_surf, (current_info_x, info_y_pos)) 

        if total_rings_this_level > 0 and self.ui_assets["ring_icon"]: 
            _total_ring_icons_display_width = max(0, total_rings_this_level * (self.ui_icon_size_rings[0] + icon_spacing) - icon_spacing) 
            _rings_block_start_x_no_text = rings_block_start_x 
            _target_ring_row_y_for_anim = rings_y_pos_hud 
            _next_ring_slot_index = max(0, min(displayed_rings_count, total_rings_this_level - 1)) 
            target_slot_x_offset = _next_ring_slot_index * (self.ui_icon_size_rings[0] + icon_spacing) 
            target_slot_center_x = _rings_block_start_x_no_text + target_slot_x_offset + self.ui_icon_size_rings[0] // 2 
            target_slot_center_y = _target_ring_row_y_for_anim + self.ui_icon_size_rings[1] // 2 
            if hasattr(self.game_controller, 'ring_ui_target_pos'): 
                self.game_controller.ring_ui_target_pos = (target_slot_center_x, target_slot_center_y) 

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

    def draw_architect_vault_hud_elements(self): # From original file content
        self.draw_gameplay_hud() 
        current_time = pygame.time.get_ticks() 
        current_vault_phase = getattr(self.game_controller, 'architect_vault_current_phase', None) 
        if current_vault_phase == "extraction": 
            time_remaining_ms_vault = getattr(self.game_controller, 'level_time_remaining_ms', 0) 
            time_val_str_vault = f"{max(0, time_remaining_ms_vault // 1000) // 60:02d}:{max(0, time_remaining_ms_vault // 1000) % 60:02d}" 
            time_color_vault = RED 
            if (time_remaining_ms_vault // 1000) > 10: time_color_vault = YELLOW 
            if (current_time // 250) % 2 == 0 and (time_remaining_ms_vault // 1000) <= 10 : time_color_vault = DARK_RED 
            timer_surf_vault = self._render_text_safe(f"ESCAPE ROUTE COLLAPSING: {time_val_str_vault}", "vault_timer", time_color_vault) 
            self.screen.blit(timer_surf_vault, timer_surf_vault.get_rect(centerx=WIDTH//2, top=10)) 
        vault_message = getattr(self.game_controller, 'architect_vault_message', "") 
        vault_message_timer_end = getattr(self.game_controller, 'architect_vault_message_timer', 0) 
        if vault_message and current_time < vault_message_timer_end: 
            msg_surf = self._render_text_safe(vault_message, "vault_message", GOLD) 
            msg_bg_surf = pygame.Surface((msg_surf.get_width() + 30, msg_surf.get_height() + 15), pygame.SRCALPHA) 
            msg_bg_surf.fill((10, 0, 20, 200)) 
            msg_bg_surf.blit(msg_surf, msg_surf.get_rect(center=(msg_bg_surf.get_width()//2, msg_bg_surf.get_height()//2))) 
            self.screen.blit(msg_bg_surf, msg_bg_surf.get_rect(centerx=WIDTH//2, bottom=GAME_PLAY_AREA_HEIGHT - 20)) 

    def draw_pause_overlay(self): # From original file content
        overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA) 
        overlay_surface.fill((0,0,0,150)) 
        self.screen.blit(overlay_surface, (0,0)) 
        pause_title_surf = self._render_text_safe("PAUSED", "large_text", WHITE) 
        self.screen.blit(pause_title_surf, pause_title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 60))) 
        current_game_state_when_paused = self.scene_manager.get_current_state() 
        pause_text_options = "P: Continue | M: Menu | Q: Quit Game" 
        if current_game_state_when_paused == GAME_STATE_PLAYING: 
             pause_text_options = "P: Continue | L: Leaderboard | M: Menu | Q: Quit Game" 
        elif current_game_state_when_paused.startswith("architect_vault"): 
             pause_text_options = "P: Continue | ESC: Main Menu (Exit Vault) | Q: Quit Game" 
        options_surf = self._render_text_safe(pause_text_options, "ui_text", WHITE) 
        self.screen.blit(options_surf, options_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 40))) 

    def draw_game_over_overlay(self): # From original file content
        go_text_surf = self._render_text_safe("GAME OVER", "large_text", RED) 
        score_text_surf = self._render_text_safe(f"Final Score: {self.game_controller.score}", "medium_text", WHITE) 
        self.screen.blit(go_text_surf, go_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 120))) 
        self.screen.blit(score_text_surf, score_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 30))) 
        can_submit_score = not get_game_setting("SETTINGS_MODIFIED") 
        is_new_high = can_submit_score and leaderboard.is_high_score(self.game_controller.score, self.game_controller.level) 
        prompt_y_offset = HEIGHT // 2 + 50 
        if not can_submit_score: 
            no_lb_text_surf = self._render_text_safe("Leaderboard disabled (custom settings).", "ui_text", YELLOW) 
            self.screen.blit(no_lb_text_surf, no_lb_text_surf.get_rect(center=(WIDTH//2, prompt_y_offset))) 
            prompt_y_offset += self.fonts["ui_text"].get_height() + 20 
        prompt_str = "R: Restart  M: Menu  Q: Quit" 
        prompt_color = WHITE 
        if can_submit_score and is_new_high: 
            prompt_str = "New High Score! Press any key to enter name." 
            prompt_color = GOLD 
        elif can_submit_score: 
            prompt_str = "R: Restart  L: Leaderboard  M: Menu  Q: Quit" 
        prompt_surf = self._render_text_safe(prompt_str, "ui_text", prompt_color) 
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, prompt_y_offset))) 

    def draw_enter_name_overlay(self): # From original file content
        title_surf = self._render_text_safe("New High Score!", "large_text", GOLD) 
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 180))) 
        score_level_text = f"Your Score: {self.game_controller.score} (Level: {self.game_controller.level})" 
        score_level_surf = self._render_text_safe(score_level_text, "medium_text", WHITE) 
        self.screen.blit(score_level_surf, score_level_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 90))) 
        prompt_name_surf = self._render_text_safe("Enter Name (max 6 chars, A-Z):", "ui_text", WHITE) 
        self.screen.blit(prompt_name_surf, prompt_name_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 20))) 
        player_name_input_str = getattr(self.game_controller, 'player_name_input_display_cache', "") 
        input_box_width = 300; input_box_height = 60 
        input_box_rect = pygame.Rect(WIDTH//2 - input_box_width//2, HEIGHT//2 + 30, input_box_width, input_box_height) 
        pygame.draw.rect(self.screen, WHITE, input_box_rect, 2, border_radius=10) 
        input_text_surf = self._render_text_safe(player_name_input_str, "input_text", WHITE) 
        self.screen.blit(input_text_surf, input_text_surf.get_rect(center=input_box_rect.center)) 
        submit_prompt_surf = self._render_text_safe("Press ENTER to submit.", "ui_text", CYAN) 
        self.screen.blit(submit_prompt_surf, submit_prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 120))) 

    def draw_leaderboard_overlay(self): # From original file content (abbreviated)
        title_surf = self._render_text_safe("Leaderboard", "large_text", GOLD) 
        title_bg_rect_width = title_surf.get_width() + 40 
        title_bg_rect_height = title_surf.get_height() + 20 
        title_bg_surf = pygame.Surface((title_bg_rect_width, title_bg_rect_height), pygame.SRCALPHA) 
        title_bg_surf.fill((20,20,20,180)) 
        title_bg_surf.blit(title_surf, title_surf.get_rect(center=(title_bg_rect_width//2, title_bg_rect_height//2))) 
        self.screen.blit(title_bg_surf, title_bg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 300))) 
        # ... (Full original leaderboard drawing logic)
        menu_prompt_surf = self._render_text_safe("ESC: Main Menu | Q: Quit Game", "ui_text", WHITE) 
        prompt_bg = pygame.Surface((menu_prompt_surf.get_width()+20, menu_prompt_surf.get_height()+10), pygame.SRCALPHA) 
        prompt_bg.fill((20,20,20,180)) 
        prompt_bg.blit(menu_prompt_surf, prompt_bg.get_rect(center=(prompt_bg.get_width()//2, prompt_bg.get_height()//2))) 
        self.screen.blit(prompt_bg, prompt_bg.get_rect(center=(WIDTH//2, HEIGHT-100))) 

    def draw_architect_vault_success_overlay(self): # From original file content
        msg_surf = self._render_text_safe("Vault Conquered!", "large_text", GOLD) 
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 80))) 
        blueprint_id = get_game_setting("ARCHITECT_REWARD_BLUEPRINT_ID") 
        reward_text = f"Blueprint Acquired: {blueprint_id}" if blueprint_id else "Ancient Technology Secured!" 
        reward_surf = self._render_text_safe(reward_text, "medium_text", CYAN) 
        self.screen.blit(reward_surf, reward_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20))) 
        prompt_surf = self._render_text_safe("Press ENTER or M to Continue", "ui_text", WHITE) 
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 100))) 

    def draw_architect_vault_failure_overlay(self): # From original file content
        msg_surf = self._render_text_safe("Vault Mission Failed", "large_text", RED) 
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))) 
        reason_text = getattr(self.game_controller, 'architect_vault_failure_reason', "Critical systems compromised.") 
        reason_surf = self._render_text_safe(reason_text, "ui_text", YELLOW) 
        self.screen.blit(reason_surf, reason_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20))) 
        prompt_surf = self._render_text_safe("Press ENTER or M to Return to Menu", "ui_text", WHITE) 
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 80)))