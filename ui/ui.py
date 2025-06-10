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
        else: self.ui_asset_surfaces["reactor_icon_placeholder"] = self._create_fallback_icon_surface(self.ui_icon_size_reactor, "⚛", (50,50,200), font_key="ui_emoji_general")

    def update_player_life_icon_surface(self):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        life_icon_asset_key = f"drone_{selected_drone_id}_hud_icon" 
        loaded_icon = self.asset_manager.get_image(life_icon_asset_key, scale_to_size=self.ui_icon_size_lives)
        
        if loaded_icon: self.ui_asset_surfaces["current_drone_life_icon"] = loaded_icon
        else:
            logger.warning(f"UIManager: Life icon for drone '{selected_drone_id}' (key: '{life_icon_asset_key}') not found. Using fallback.")
            self.ui_asset_surfaces["current_drone_life_icon"] = self._create_fallback_icon_surface(size=self.ui_icon_size_lives, text="♥", color=gs.CYAN, font_key="ui_emoji_small")

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
        pass

    def draw_game_intro_scroll(self):
        pass

    def draw_story_message_overlay(self, message):
        pass

    def draw_codex_screen(self):
        pass

    def draw_main_menu(self):
        pass

    def draw_drone_select_menu(self):
        pass

    def draw_gameplay_hud(self):
        pass

    def get_scaled_fragment_icon_surface(self, fragment_id):
        icon_surface = self.ui_asset_surfaces["core_fragment_icons"].get(fragment_id)
        if icon_surface:
            return icon_surface
        
        logger.warning(f"UIManager: Scaled icon surface for fragment_id '{fragment_id}' not found. Using fallback.")
        return self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", gs.PURPLE)

    def draw_settings_menu(self):
        pass

    def draw_leaderboard_overlay(self):
        pass

    def draw_game_over_overlay(self):
        pass

    def draw_enter_name_overlay(self):
        pass

    def draw_architect_vault_success_overlay(self):
        pass

    def draw_architect_vault_failure_overlay(self):
        pass

    def draw_maze_defense_hud(self):
        pass

    def draw_pause_overlay(self):
        pass