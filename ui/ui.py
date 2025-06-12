# hyperdrone/ui/ui.py
import os
import math
import random
import logging

import pygame

# Corrected import style
import game_settings as gs

try:
    from .build_menu import BuildMenu
except ImportError:
    logging.warning("UIManager: Could not import BuildMenu. Build UI will not be available.")
    BuildMenu = None 

logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')


class UIManager:
    def __init__(self, screen, asset_manager, game_controller_ref, scene_manager_ref, drone_system_ref):
        self.screen = screen
        self.asset_manager = asset_manager
        self.game_controller = game_controller_ref 
        self.scene_manager = scene_manager_ref
        self.drone_system = drone_system_ref
        
        self.ui_asset_surfaces = {
            "ring_icon": None, "ring_icon_empty": None, "menu_background": None,
            "current_drone_life_icon": None, "core_fragment_icons": {},
            "core_fragment_empty_icon": None, "reactor_icon_placeholder": None
        }
        self.ui_icon_size_lives = (30, 30)
        self.ui_icon_size_rings = (20, 20)
        self.ui_icon_size_fragments = (28, 28)
        self.ui_icon_size_reactor = (32, 32)

        self.codex_list_item_height = 0
        self.codex_max_visible_items_list = 0
        self.codex_max_visible_lines_content = 0

        self.BOTTOM_INSTRUCTION_CENTER_Y = gs.get_game_setting("HEIGHT") - 50
        self.SECONDARY_INSTRUCTION_CENTER_Y = gs.get_game_setting("HEIGHT") - 80
        self.INSTRUCTION_TEXT_COLOR = gs.CYAN
        self.INSTRUCTION_BG_COLOR = (30, 30, 30, 150)
        self.INSTRUCTION_PADDING_X = 20
        self.INSTRUCTION_PADDING_Y = 10

        if BuildMenu:
            self.build_menu = BuildMenu(self.game_controller, self, self.asset_manager) 
        else:
            self.build_menu = None

        self._load_ui_assets_from_manager()
        self.update_player_life_icon_surface()
        logger.info("UIManager initialized and UI assets loaded via AssetManager.")

    def _load_ui_assets_from_manager(self):
        self.ui_asset_surfaces["ring_icon"] = self.asset_manager.get_image("ring_ui_icon", scale_to_size=self.ui_icon_size_rings)
        if not self.ui_asset_surfaces["ring_icon"]: self.ui_asset_surfaces["ring_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", gs.GOLD)

        self.ui_asset_surfaces["ring_icon_empty"] = self.asset_manager.get_image("ring_ui_icon_empty", scale_to_size=self.ui_icon_size_rings)
        if not self.ui_asset_surfaces["ring_icon_empty"]: self.ui_asset_surfaces["ring_icon_empty"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", gs.GREY)

        self.ui_asset_surfaces["menu_background"] = self.asset_manager.get_image("menu_logo_hyperdrone")
        if not self.ui_asset_surfaces["menu_background"]: logger.warning("UIManager: Menu background 'menu_logo_hyperdrone' not found in AssetManager.")

        self.ui_asset_surfaces["core_fragment_empty_icon"] = self.asset_manager.get_image("core_fragment_empty_icon", scale_to_size=self.ui_icon_size_fragments)
        if not self.ui_asset_surfaces["core_fragment_empty_icon"]: self.ui_asset_surfaces["core_fragment_empty_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "F", gs.DARK_GREY, text_color=gs.GREY)

        if gs.CORE_FRAGMENT_DETAILS:
            for _, details in gs.CORE_FRAGMENT_DETAILS.items():
                frag_id = details.get("id")
                if frag_id:
                    asset_key = f"fragment_{frag_id}_icon"
                    loaded_icon = self.asset_manager.get_image(asset_key, scale_to_size=self.ui_icon_size_fragments)
                    if loaded_icon: self.ui_asset_surfaces["core_fragment_icons"][frag_id] = loaded_icon
                    else:
                        logger.warning(f"UIManager: Core fragment icon for ID '{frag_id}' (key: '{asset_key}') not found. Using fallback.")
                        self.ui_asset_surfaces["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, frag_id[:1] if frag_id else "!", gs.PURPLE)
        
        reactor_icon_asset = self.asset_manager.get_image("reactor_hud_icon_key", scale_to_size=self.ui_icon_size_reactor)
        if reactor_icon_asset: self.ui_asset_surfaces["reactor_icon_placeholder"] = reactor_icon_asset
        else: self.ui_asset_surfaces["reactor_icon_placeholder"] = self._create_fallback_icon_surface(self.ui_icon_size_reactor, "R", (50,50,200))

    def update_player_life_icon_surface(self):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        life_icon_asset_key = f"drone_{selected_drone_id}_hud_icon" 
        loaded_icon = self.asset_manager.get_image(life_icon_asset_key, scale_to_size=self.ui_icon_size_lives)
        
        if loaded_icon:
            # Rotate the drone icon 90 degrees counterclockwise
            rotated_icon = pygame.transform.rotate(loaded_icon, 90)
            self.ui_asset_surfaces["current_drone_life_icon"] = rotated_icon
        else:
            logger.warning(f"UIManager: Life icon for drone '{selected_drone_id}' (key: '{life_icon_asset_key}') not found. Using fallback.")
            self.ui_asset_surfaces["current_drone_life_icon"] = self._create_fallback_icon_surface(size=self.ui_icon_size_lives, text="L", color=gs.CYAN)

    def _create_fallback_icon_surface(self, size=(30,30), text="?", color=gs.GREY, text_color=gs.WHITE, font_key="ui_text"):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)
        pygame.draw.rect(surface, gs.WHITE, surface.get_rect(), 1)
        font_to_use = self.asset_manager.get_font(font_key, max(10, size[1]-4)) or pygame.font.Font(None, max(10, size[1]-4))
        if text and font_to_use:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                surface.blit(text_surf, text_surf.get_rect(center=(size[0] // 2, size[1] // 2)))
            except Exception as e: logger.error(f"UIManager: Error rendering fallback icon text '{text}' with font key '{font_key}': {e}")
        return surface

    def _render_text_safe(self, text, font_key, color, fallback_size=24):
        font = self.asset_manager.get_font(font_key, fallback_size)
        if not font: font = pygame.font.Font(None, fallback_size)
        try: return font.render(str(text), True, color)
        except Exception as e:
            logger.error(f"UIManager: Error rendering text '{text}' with font key '{font_key}': {e}")
            return pygame.font.Font(None, fallback_size).render("ERR", True, gs.RED)

    def _wrap_text(self, text, font_key_for_size_calc, size_for_font, max_width):
        font = self.asset_manager.get_font(font_key_for_size_calc, size_for_font) or pygame.font.Font(None, size_for_font)
        words, lines, current_line = text.split(' '), [], ""
        for word in words:
            if font.size(current_line + word + " ")[0] <= max_width: current_line += word + " "
            else:
                if current_line: lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip()); return lines

    def _wrap_text_with_font_obj(self, text, font_object, max_width):
        if not font_object: return [text]
        words, lines, current_line = text.split(' '), [], ""
        for word in words:
            if font_object.size(current_line + word + " ")[0] <= max_width: current_line += word + " "
            else:
                if current_line: lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip()); return lines

    def draw_current_scene_ui(self):
        current_state = self.scene_manager.get_current_state()
        ui_flow_ctrl = self.game_controller.ui_flow_controller 
        
        is_menu_like_state = current_state in [
            gs.GAME_STATE_MAIN_MENU, gs.GAME_STATE_DRONE_SELECT, gs.GAME_STATE_SETTINGS,
            gs.GAME_STATE_LEADERBOARD, gs.GAME_STATE_CODEX,
            gs.GAME_STATE_ARCHITECT_VAULT_SUCCESS, gs.GAME_STATE_ARCHITECT_VAULT_FAILURE,
            gs.GAME_STATE_GAME_OVER, gs.GAME_STATE_ENTER_NAME
        ]
        
        if is_menu_like_state: 
            self.screen.fill(gs.BLACK)
            if ui_flow_ctrl and hasattr(ui_flow_ctrl, 'menu_stars') and ui_flow_ctrl.menu_stars:
                 for star_params in ui_flow_ctrl.menu_stars:
                    pygame.draw.circle(self.screen, gs.WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

        state_draw_map = {
            gs.GAME_STATE_MAIN_MENU: self.draw_main_menu,
            gs.GAME_STATE_DRONE_SELECT: self.draw_drone_select_menu,
            gs.GAME_STATE_SETTINGS: self.draw_settings_menu,
            gs.GAME_STATE_LEADERBOARD: self.draw_leaderboard_overlay,
            gs.GAME_STATE_CODEX: self.draw_codex_screen,
            gs.GAME_STATE_GAME_OVER: self.draw_game_over_overlay,
            gs.GAME_STATE_ENTER_NAME: self.draw_enter_name_overlay,
            gs.GAME_STATE_GAME_INTRO_SCROLL: self.draw_game_intro_scroll,
            gs.GAME_STATE_ARCHITECT_VAULT_SUCCESS: self.draw_architect_vault_success_overlay,
            gs.GAME_STATE_ARCHITECT_VAULT_FAILURE: self.draw_architect_vault_failure_overlay
        }

        if current_state in state_draw_map:
            state_draw_map[current_state]()
        
        elif current_state.startswith("architect_vault"):
            self.draw_architect_vault_hud_elements()
            if self.game_controller.paused: self.draw_pause_overlay()
        
        elif current_state in [gs.GAME_STATE_PLAYING, gs.GAME_STATE_BONUS_LEVEL_PLAYING]:
            self.draw_gameplay_hud()
            if self.game_controller.paused: self.draw_pause_overlay()
        
        elif current_state == gs.GAME_STATE_MAZE_DEFENSE: 
            self.draw_maze_defense_hud()
            if self.game_controller.paused: self.draw_pause_overlay()
            if self.build_menu and self.build_menu.is_active and \
               hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase:
                self.build_menu.draw(self.screen)
        
        elif current_state == gs.GAME_STATE_RING_PUZZLE:
            if not (self.game_controller.puzzle_controller and self.game_controller.puzzle_controller.ring_puzzle_active_flag):
                self.screen.fill(gs.DARK_GREY)
                fallback_surf = self._render_text_safe("Loading Puzzle...", "medium_text", gs.WHITE, fallback_size=48)
                self.screen.blit(fallback_surf, fallback_surf.get_rect(center=(gs.get_game_setting("WIDTH") // 2, gs.get_game_setting("HEIGHT") // 2)))

        if hasattr(self.game_controller, 'story_message_active') and self.game_controller.story_message_active and \
           hasattr(self.game_controller, 'story_message') and self.game_controller.story_message:
            if current_state != gs.GAME_STATE_GAME_INTRO_SCROLL:
                self.draw_story_message_overlay(self.game_controller.story_message)
    
    def draw_architect_vault_hud_elements(self):
        title_surf = self._render_text_safe("Architect's Vault", "large_text", gs.GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.get_game_setting("WIDTH") // 2, 50)))

    def draw_game_intro_scroll(self):
        ui_flow = self.game_controller.ui_flow_controller
        if not ui_flow.intro_screens_data or ui_flow.current_intro_screen_index >= len(ui_flow.intro_screens_data):
            return

        current_screen_data = ui_flow.intro_screens_data[ui_flow.current_intro_screen_index]
        image_key = current_screen_data.get("image_path_key")
        text = current_screen_data.get("text", "")
        
        screen_width = gs.get_game_setting("WIDTH")
        screen_height = gs.get_game_setting("HEIGHT")

        if image_key:
            bg_image = self.asset_manager.get_image(image_key)
            if bg_image:
                bg_surf = pygame.transform.scale(bg_image, (screen_width, screen_height))
                self.screen.blit(bg_surf, (0, 0))

        lines = text.split('\n')
        font = self.asset_manager.get_font("medium_text", 36)
        start_y = screen_height - (len(lines) * 40) - 100

        for i, line in enumerate(lines):
            line_surf = font.render(line, True, gs.WHITE)
            self.screen.blit(line_surf, line_surf.get_rect(center=(screen_width / 2, start_y + i * 40)))
            
        prompt_surf = self._render_text_safe("Press SPACE to continue...", "ui_text", gs.GOLD, fallback_size=24)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(screen_width / 2, screen_height - 50)))

    def draw_story_message_overlay(self, message):
        font = self.asset_manager.get_font("ui_text", 28) or pygame.font.Font(None, 28)
        text_surf = font.render(message, True, gs.CYAN)
        bg_rect = text_surf.get_rect(center=(gs.get_game_setting("WIDTH") // 2, gs.get_game_setting("HEIGHT") - 150))
        bg_rect.inflate_ip(40, 20)
        
        bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        bg_surface.fill((30, 30, 30, 180))
        self.screen.blit(bg_surface, bg_rect.topleft)
        pygame.draw.rect(self.screen, gs.CYAN, bg_rect, 1)
        self.screen.blit(text_surf, text_surf.get_rect(center=bg_rect.center))

    def draw_codex_screen(self):
        ui_flow = self.game_controller.ui_flow_controller
        font_title = self.asset_manager.get_font("large_text", 52)
        font_cat = self.asset_manager.get_font("medium_text", 36)
        font_entry = self.asset_manager.get_font("ui_text", 28)
        font_content = self.asset_manager.get_font("ui_text", 24)
        
        title_surf = font_title.render("CODEX", True, gs.GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.WIDTH / 2, 60)))
        
        if ui_flow.codex_current_view == "categories":
            start_y = 150
            for i, cat_name in enumerate(ui_flow.codex_categories_list):
                color = gs.YELLOW if i == ui_flow.codex_selected_category_index else gs.WHITE
                cat_surf = font_cat.render(cat_name, True, color)
                self.screen.blit(cat_surf, cat_surf.get_rect(center=(gs.WIDTH/2, start_y + i * 50)))
        
        elif ui_flow.codex_current_view == "entries":
            cat_title_surf = font_cat.render(f"Category: {ui_flow.codex_current_category_name}", True, gs.CYAN)
            self.screen.blit(cat_title_surf, cat_title_surf.get_rect(center=(gs.WIDTH/2, 140)))
            start_y = 220
            for i, entry_data in enumerate(ui_flow.codex_entries_in_category_list):
                color = gs.YELLOW if i == ui_flow.codex_selected_entry_index_in_category else gs.WHITE
                entry_surf = font_entry.render(entry_data.get("title", "Unknown"), True, color)
                self.screen.blit(entry_surf, (100, start_y + i * 40))
                
        elif ui_flow.codex_current_view == "content":
            entry_details = self.drone_system.get_lore_entry_details(ui_flow.codex_selected_entry_id)
            if entry_details:
                content_title_surf = font_cat.render(entry_details.get("title", ""), True, gs.GOLD)
                self.screen.blit(content_title_surf, content_title_surf.get_rect(center=(gs.WIDTH/2, 140)))
                
                content_text = entry_details.get("content", "No content available.")
                wrapped_lines = self._wrap_text_with_font_obj(content_text, font_content, gs.WIDTH - 200)
                ui_flow.codex_current_entry_total_lines = len(wrapped_lines)

                start_y, line_height = 220, font_content.get_linesize()
                for i, line in enumerate(wrapped_lines[ui_flow.codex_content_scroll_offset:]):
                    line_surf = font_content.render(line, True, gs.WHITE)
                    line_y = start_y + i * line_height
                    if line_y > gs.HEIGHT - 100: break
                    self.screen.blit(line_surf, (100, line_y))

    def draw_main_menu(self):
        if self.ui_asset_surfaces["menu_background"]:
            logo_surf = self.ui_asset_surfaces["menu_background"]
            screen_width, screen_height = gs.get_game_setting("WIDTH"), gs.get_game_setting("HEIGHT")
            scaled_bg_surf = pygame.transform.scale(logo_surf, (screen_width, screen_height))
            self.screen.blit(scaled_bg_surf, (0, 0))

        ui_flow_ctrl = self.game_controller.ui_flow_controller
        if ui_flow_ctrl and hasattr(ui_flow_ctrl, 'menu_stars') and ui_flow_ctrl.menu_stars:
            for star_params in ui_flow_ctrl.menu_stars:
                pygame.draw.circle(self.screen, gs.WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

        options, selected_index = ui_flow_ctrl.menu_options, ui_flow_ctrl.selected_menu_option
        start_y, option_height = gs.get_game_setting("HEIGHT") * 0.55, 60
        font_menu = self.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)

        for i, option_text in enumerate(options):
            color = gs.GOLD if i == selected_index else gs.WHITE
            text_surf = font_menu.render(option_text, True, color)
            text_rect = text_surf.get_rect(center=(gs.get_game_setting("WIDTH") // 2, start_y + i * option_height))
            self.screen.blit(text_surf, text_rect)

    def draw_drone_select_menu(self):
        title_surf = self._render_text_safe("Select Drone", "large_text", gs.GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.WIDTH // 2, 80)))
        
        ui_flow = self.game_controller.ui_flow_controller
        if not ui_flow.drone_select_options: return

        selected_drone_id = ui_flow.drone_select_options[ui_flow.selected_drone_preview_index]
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        is_unlocked = self.drone_system.is_drone_unlocked(selected_drone_id)

        sprite_asset_key = drone_config.get("sprite_path", "").replace("assets/","")
        sprite_surf = self.asset_manager.get_image(sprite_asset_key, scale_to_size=(256, 256))
        if sprite_surf: self.screen.blit(sprite_surf, sprite_surf.get_rect(center=(gs.WIDTH/2, gs.HEIGHT/2 - 100)))

        name_surf = self._render_text_safe(drone_config.get("name"), "medium_text", gs.WHITE if is_unlocked else gs.GREY, fallback_size=48)
        self.screen.blit(name_surf, name_surf.get_rect(center=(gs.WIDTH/2, gs.HEIGHT/2 + 100)))
        
        desc_surf = self._render_text_safe(drone_config.get("description"), "ui_text", gs.CYAN, fallback_size=24)
        self.screen.blit(desc_surf, desc_surf.get_rect(center=(gs.WIDTH/2, gs.HEIGHT/2 + 150)))
        
        if not is_unlocked:
            unlock_cond = drone_config.get("unlock_condition", {})
            unlock_desc = unlock_cond.get("description", "Locked")
            unlock_surf = self._render_text_safe(unlock_desc, "ui_text", gs.RED, fallback_size=28)
            self.screen.blit(unlock_surf, unlock_surf.get_rect(center=(gs.WIDTH/2, gs.HEIGHT/2 + 200)))

    def draw_gameplay_hud(self):
        player = self.game_controller.player
        if not player: return
        panel_height, panel_y = gs.get_game_setting("BOTTOM_PANEL_HEIGHT"), gs.get_game_setting("HEIGHT") - gs.get_game_setting("BOTTOM_PANEL_HEIGHT")
        panel_bg_color = (*gs.DARK_GREY[:3], 220)
        panel_surface = pygame.Surface((gs.WIDTH, panel_height), pygame.SRCALPHA)
        panel_surface.fill(panel_bg_color)
        self.screen.blit(panel_surface, (0, panel_y))
        pygame.draw.line(self.screen, gs.CYAN, (0, panel_y), (gs.WIDTH, panel_y), 2)
        font_ui, font_small, font_large_val = self.asset_manager.get_font("ui_text", 28), self.asset_manager.get_font("ui_text", 24), self.asset_manager.get_font("ui_values", 30)
        
        life_icon = self.ui_asset_surfaces.get("current_drone_life_icon")
        if life_icon: self.screen.blit(life_icon, (30, panel_y + 20))
        self.screen.blit(font_large_val.render(f"x {self.game_controller.lives}", True, gs.WHITE), (30 + self.ui_icon_size_lives[0] + 10, panel_y + 25))
        score_label = font_ui.render("Score:", True, gs.CYAN)
        self.screen.blit(score_label, (30, panel_y + 65))
        self.screen.blit(font_large_val.render(f"{self.game_controller.level_manager.score}", True, gs.WHITE), (30 + score_label.get_width() + 10, panel_y + 65))
        
        # Health bar removed from HUD
        
        # Center the weapon bar horizontally
        wpn_x, wpn_y = (gs.WIDTH / 2) - 125, panel_y + 20  # Centered position
        wpn_mode, wpn_name = player.current_weapon_mode, gs.WEAPON_MODE_NAMES.get(player.current_weapon_mode, "N/A")
        wpn_icon_path = gs.WEAPON_MODE_ICONS.get(wpn_mode)
        weapon_label = font_ui.render("Weapon", True, gs.CYAN)
        self.screen.blit(weapon_label, ((gs.WIDTH / 2) - (weapon_label.get_width() / 2), wpn_y - 20))  # Center the label
        if wpn_icon_path:
            asset_key = wpn_icon_path.replace("assets/", "").replace("\\", "/")
            icon_surf = self.asset_manager.get_image(asset_key, scale_to_size=(64, 64))
            if icon_surf:
                # Rotate the weapon icon 90 degrees counterclockwise
                rotated_icon = pygame.transform.rotate(icon_surf, 90)
                icon_rect = rotated_icon.get_rect(topleft=(wpn_x, wpn_y))
                self.screen.blit(rotated_icon, icon_rect)
                text_x, cooldown_bar_y = icon_rect.right + 15, wpn_y + 40
                self.screen.blit(font_small.render(wpn_name, True, gs.WHITE), (text_x, wpn_y + 5))
                time_since = pygame.time.get_ticks() - player.last_shot_time
                progress = min(1.0, time_since / player.current_shoot_cooldown) if player.current_shoot_cooldown > 0 else 1.0
                pygame.draw.rect(self.screen, gs.DARK_GREY, (text_x, cooldown_bar_y, 150, 10))
                pygame.draw.rect(self.screen, gs.YELLOW, (text_x, cooldown_bar_y, 150 * progress, 10))
                pygame.draw.rect(self.screen, gs.WHITE, (text_x, cooldown_bar_y, 150, 10), 1)

        # Position rings and fragments at the right side of the screen
        rings_x = gs.WIDTH - gs.HUD_RING_ICON_AREA_X_OFFSET
        rings_y = panel_y + gs.HUD_RING_ICON_AREA_Y_OFFSET
        frags_x = gs.WIDTH - 150
        frags_y = panel_y + 65
        
        # Only display rings in regular Maze levels (not in MazeChapter2)
        current_game_state = self.scene_manager.get_current_state()
        if current_game_state == gs.GAME_STATE_PLAYING:
            ring_icon, ring_empty = self.ui_asset_surfaces.get("ring_icon"), self.ui_asset_surfaces.get("ring_icon_empty")
            if ring_icon and ring_empty:
                for i in range(self.game_controller.level_manager.total_rings_per_level): 
                    # Show filled icon only for rings that have completed their animation
                    show_filled = i < self.game_controller.level_manager.displayed_collected_rings_count
                    icon_x = rings_x + i * (gs.HUD_RING_ICON_SIZE + gs.HUD_RING_ICON_SPACING)
                    self.screen.blit(ring_icon if show_filled else ring_empty, (icon_x, rings_y))
        collected, required = self.drone_system.get_collected_fragments_ids(), sorted([d['id'] for d in gs.CORE_FRAGMENT_DETAILS.values() if d.get('required_for_vault')])
        for i, frag_id in enumerate(required):
            icon = self.ui_asset_surfaces["core_fragment_icons"].get(frag_id) if frag_id in collected else self.ui_asset_surfaces["core_fragment_empty_icon"]
            if icon: self.screen.blit(icon, (frags_x + i * (self.ui_icon_size_fragments[0] + 5), frags_y))

    def get_scaled_fragment_icon_surface(self, fragment_id):
        icon_surface = self.ui_asset_surfaces["core_fragment_icons"].get(fragment_id)
        if icon_surface: return icon_surface
        logger.warning(f"UIManager: Scaled icon surface for fragment_id '{fragment_id}' not found. Using fallback.")
        return self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", gs.PURPLE)

    def draw_settings_menu(self):
        title_surf = self._render_text_safe("Settings", "large_text", gs.GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.WIDTH // 2, 80)))
        
        ui_flow = self.game_controller.ui_flow_controller
        settings_items, selected_index = ui_flow.settings_items_data, ui_flow.selected_setting_index
        font_setting = self.asset_manager.get_font("ui_text", 28)
        
        start_y = 200
        for i, item in enumerate(settings_items):
            y_pos = start_y + i * 50
            color = gs.YELLOW if i == selected_index else gs.WHITE
            label_surf = font_setting.render(item['label'], True, color)
            self.screen.blit(label_surf, (200, y_pos))
            
            val_text = ""
            if item['type'] != 'action':
                current_val = gs.get_game_setting(item['key'])
                val_to_format = current_val
                if item.get("is_ms_to_sec"): val_to_format /= 1000
                
                if 'display_format' in item:
                    val_text = item['display_format'].format(val_to_format)
                elif 'get_display' in item:
                    val_text = item['get_display'](current_val)
                else:
                    val_text = str(current_val)
                    
                if item['type'] in ["numeric", "choice"]: val_text = f"< {val_text} >"
            else: val_text = "[PRESS ENTER]"
            
            val_surf = font_setting.render(val_text, True, color)
            self.screen.blit(val_surf, (gs.WIDTH - 200 - val_surf.get_width(), y_pos))

    def draw_leaderboard_overlay(self):
        title_surf = self._render_text_safe("Leaderboard", "large_text", gs.GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.WIDTH // 2, 80)))
        
        scores = self.game_controller.ui_flow_controller.leaderboard_scores
        font_header = self.asset_manager.get_font("medium_text", 36)
        font_score = self.asset_manager.get_font("ui_text", 28)
        
        headers, header_positions = ["RANK", "NAME", "SCORE", "LEVEL"], [gs.WIDTH*0.2, gs.WIDTH*0.35, gs.WIDTH*0.6, gs.WIDTH*0.8]
        
        for i, header in enumerate(headers):
            header_surf = font_header.render(header, True, gs.CYAN)
            self.screen.blit(header_surf, header_surf.get_rect(center=(header_positions[i], 180)))
            
        for i, score_entry in enumerate(scores):
            y_pos = 250 + i * 50
            color = gs.GOLD if i == 0 else gs.WHITE
            rank_surf = font_score.render(f"{i+1}", True, color)
            name_surf = font_score.render(score_entry.get('name', 'N/A'), True, color)
            score_surf = font_score.render(str(score_entry.get('score', 0)), True, color)
            level_surf = font_score.render(str(score_entry.get('level', 0)), True, color)
            self.screen.blit(rank_surf, rank_surf.get_rect(center=(header_positions[0], y_pos)))
            self.screen.blit(name_surf, name_surf.get_rect(center=(header_positions[1], y_pos)))
            self.screen.blit(score_surf, score_surf.get_rect(center=(header_positions[2], y_pos)))
            self.screen.blit(level_surf, level_surf.get_rect(center=(header_positions[3], y_pos)))

    def draw_game_over_overlay(self):
        overlay = pygame.Surface((gs.WIDTH, gs.HEIGHT), pygame.SRCALPHA); overlay.fill((50, 0, 0, 180))
        self.screen.blit(overlay, (0,0))
        title_surf = self._render_text_safe("DRONE DESTROYED", "title_text", gs.RED, fallback_size=90)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.WIDTH // 2, gs.HEIGHT // 2 - 100)))
        prompt_surf = self._render_text_safe("Press 'R' to Restart or 'M' for Menu", "medium_text", gs.WHITE, fallback_size=48)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(gs.WIDTH//2, gs.HEIGHT//2 + 50)))

    def draw_enter_name_overlay(self):
        title_surf = self._render_text_safe("High Score!", "large_text", gs.GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.WIDTH // 2, gs.HEIGHT//2 - 100)))
        prompt_surf = self._render_text_safe("Enter Your Name:", "medium_text", gs.WHITE, fallback_size=48)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(gs.WIDTH // 2, gs.HEIGHT//2)))
        name_input = self.game_controller.ui_flow_controller.player_name_input_cache
        name_surf = self._render_text_safe(f"{name_input}_", "large_text", gs.CYAN, fallback_size=48)
        self.screen.blit(name_surf, name_surf.get_rect(center=(gs.WIDTH//2, gs.HEIGHT//2 + 80)))

    def draw_architect_vault_success_overlay(self):
        title_surf = self._render_text_safe("Vault Conquered", "large_text", gs.GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.get_game_setting("WIDTH") // 2, gs.get_game_setting("HEIGHT")//2)))

    def draw_architect_vault_failure_overlay(self):
        title_surf = self._render_text_safe("Mission Failed", "large_text", gs.RED, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.get_game_setting("WIDTH") // 2, gs.get_game_setting("HEIGHT")//2)))

    def draw_maze_defense_hud(self):
        title_surf = self._render_text_safe("Maze Defense", "large_text", gs.CYAN, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(gs.get_game_setting("WIDTH") // 2, 50)))

    def draw_pause_overlay(self):
        overlay = pygame.Surface((gs.get_game_setting("WIDTH"), gs.get_game_setting("HEIGHT")), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        pause_text = self._render_text_safe("PAUSED", "title_text", gs.WHITE, fallback_size=90)
        self.screen.blit(pause_text, pause_text.get_rect(center=(gs.get_game_setting("WIDTH")//2, gs.get_game_setting("HEIGHT")//2)))