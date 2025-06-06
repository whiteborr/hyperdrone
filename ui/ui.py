# hyperdrone/ui/ui.py
import os
import math
import random
import logging

import pygame

import game_settings as gs
from game_settings import (
    WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT, BOTTOM_PANEL_HEIGHT, TILE_SIZE,
    BLACK, GOLD, WHITE, GREEN, CYAN, RED, DARK_RED, GREY, YELLOW, LIGHT_BLUE, ORANGE, PURPLE,
    DARK_GREY, DARK_PURPLE, ARCHITECT_VAULT_BG_COLOR,
    WEAPON_MODE_ICONS, PLAYER_BULLET_COLOR, MISSILE_COLOR, LIGHTNING_COLOR, POWERUP_TYPES,
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
    GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, GAME_STATE_CODEX,
    GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_GAME_INTRO_SCROLL, GAME_STATE_RING_PUZZLE, GAME_STATE_MAZE_DEFENSE,
    DEFAULT_SETTINGS,
    TOTAL_CORE_FRAGMENTS_NEEDED, CORE_FRAGMENT_DETAILS,
    get_game_setting
)

# Import BuildMenu
try:
    from .build_menu import BuildMenu
except ImportError:
    logging.warning("UIManager: Could not import BuildMenu. Build UI will not be available.")
    BuildMenu = None 

logger = logging.getLogger(__name__)
# BasicConfig should ideally be called once at the application entry point.
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

        self.BOTTOM_INSTRUCTION_CENTER_Y = HEIGHT - 50
        self.SECONDARY_INSTRUCTION_CENTER_Y = HEIGHT - 80
        self.INSTRUCTION_TEXT_COLOR = CYAN
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
        if not self.ui_asset_surfaces["ring_icon"]: self.ui_asset_surfaces["ring_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", GOLD)

        self.ui_asset_surfaces["ring_icon_empty"] = self.asset_manager.get_image("ring_ui_icon_empty", scale_to_size=self.ui_icon_size_rings)
        if not self.ui_asset_surfaces["ring_icon_empty"]: self.ui_asset_surfaces["ring_icon_empty"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", GREY)

        self.ui_asset_surfaces["menu_background"] = self.asset_manager.get_image("menu_logo_hyperdrone")
        if not self.ui_asset_surfaces["menu_background"]: logger.warning("UIManager: Menu background 'menu_logo_hyperdrone' not found in AssetManager.")

        self.ui_asset_surfaces["core_fragment_empty_icon"] = self.asset_manager.get_image("core_fragment_empty_icon", scale_to_size=self.ui_icon_size_fragments)
        if not self.ui_asset_surfaces["core_fragment_empty_icon"]: self.ui_asset_surfaces["core_fragment_empty_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "F", DARK_GREY, text_color=GREY)

        if CORE_FRAGMENT_DETAILS:
            for _, details in CORE_FRAGMENT_DETAILS.items():
                frag_id = details.get("id")
                if frag_id:
                    asset_key = f"fragment_{frag_id}_icon"
                    loaded_icon = self.asset_manager.get_image(asset_key, scale_to_size=self.ui_icon_size_fragments)
                    if loaded_icon: self.ui_asset_surfaces["core_fragment_icons"][frag_id] = loaded_icon
                    else:
                        logger.warning(f"UIManager: Core fragment icon for ID '{frag_id}' (key: '{asset_key}') not found. Using fallback.")
                        self.ui_asset_surfaces["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, frag_id[:1] if frag_id else "!", PURPLE)
        
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
            self.ui_asset_surfaces["current_drone_life_icon"] = self._create_fallback_icon_surface(size=self.ui_icon_size_lives, text="♥", color=CYAN, font_key="ui_emoji_small")

    def _create_fallback_icon_surface(self, size=(30,30), text="?", color=GREY, text_color=WHITE, font_key="ui_text"):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 1)
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
            return pygame.font.Font(None, fallback_size).render("ERR", True, RED)

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
        """Main drawing router for the UI."""
        current_state = self.scene_manager.get_current_state()
        ui_flow_ctrl = self.game_controller.ui_flow_controller 

        is_menu_like_state = current_state in [
            GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
            GAME_STATE_LEADERBOARD, GAME_STATE_CODEX,
            GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
            GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME
        ]
        
        if is_menu_like_state: 
            self.screen.fill(BLACK)
            if ui_flow_ctrl and hasattr(ui_flow_ctrl, 'menu_stars') and ui_flow_ctrl.menu_stars:
                 for star_params in ui_flow_ctrl.menu_stars:
                    pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

        # Route to specific draw methods
        if current_state == GAME_STATE_MAIN_MENU: self.draw_main_menu()
        elif current_state == GAME_STATE_DRONE_SELECT: self.draw_drone_select_menu()
        elif current_state == GAME_STATE_SETTINGS: self.draw_settings_menu()
        elif current_state == GAME_STATE_LEADERBOARD: self.draw_leaderboard_overlay()
        elif current_state == GAME_STATE_CODEX: self.draw_codex_screen()
        elif current_state == GAME_STATE_GAME_OVER: self.draw_game_over_overlay()
        elif current_state == GAME_STATE_ENTER_NAME: self.draw_enter_name_overlay()
        elif current_state == GAME_STATE_GAME_INTRO_SCROLL: self.draw_game_intro_scroll() 
        
        # <<< FIX: Added call to missing method >>>
        elif current_state.startswith("architect_vault"):
            self.draw_architect_vault_hud_elements()
            if self.game_controller.paused: self.draw_pause_overlay()
            if current_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS: self.draw_architect_vault_success_overlay()
            elif current_state == GAME_STATE_ARCHITECT_VAULT_FAILURE: self.draw_architect_vault_failure_overlay()
        
        elif current_state == GAME_STATE_PLAYING or current_state == GAME_STATE_BONUS_LEVEL_PLAYING:
            self.draw_gameplay_hud()
            if self.game_controller.paused: self.draw_pause_overlay()
        
        elif current_state == GAME_STATE_MAZE_DEFENSE: 
            self.draw_maze_defense_hud()
            if self.game_controller.paused: self.draw_pause_overlay()
            if self.build_menu and self.build_menu.is_active and \
               hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase:
                self.build_menu.draw(self.screen)
        
        elif current_state == GAME_STATE_RING_PUZZLE:
            # Ring puzzle draws itself, so this can be a simple fallback
            if not (self.game_controller.puzzle_controller and self.game_controller.puzzle_controller.ring_puzzle_active_flag):
                self.screen.fill(DARK_GREY)
                fallback_surf = self._render_text_safe("Loading Puzzle...", "medium_text", WHITE, fallback_size=48)
                self.screen.blit(fallback_surf, fallback_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        if hasattr(self.game_controller, 'story_message_active') and self.game_controller.story_message_active and \
           hasattr(self.game_controller, 'story_message') and self.game_controller.story_message:
            if current_state != GAME_STATE_GAME_INTRO_SCROLL:
                self.draw_story_message_overlay(self.game_controller.story_message)
    
    def draw_architect_vault_hud_elements(self):
        """Draws HUD elements specific to the Architect's Vault mode."""
        gc = self.game_controller
        if not gc: return

        panel_y_start = GAME_PLAY_AREA_HEIGHT
        
        # Display a phase timer if relevant
        if gc.architect_vault_current_phase in ["gauntlet_wave_1", "extraction"]:
            time_left_ms = gc.level_time_remaining_ms
            time_left_sec = time_left_ms / 1000.0
            timer_text = f"TIMER: {time_left_sec:.1f}s"
            timer_color = RED if time_left_sec < 10 else YELLOW
            timer_surf = self._render_text_safe(timer_text, "vault_timer", timer_color, fallback_size=48)
            
            timer_rect = timer_surf.get_rect(centerx=WIDTH / 2, top=15)
            bg_rect = timer_rect.inflate(20, 10)
            bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surf.fill((0,0,0,150))
            self.screen.blit(bg_surf, bg_rect)
            self.screen.blit(timer_surf, timer_rect)

        # Display current wave or phase message
        if gc.architect_vault_message:
            msg_surf = self._render_text_safe(gc.architect_vault_message, "vault_message", CYAN, fallback_size=36)
            msg_rect = msg_surf.get_rect(centerx=WIDTH / 2, bottom=panel_y_start - 20)
            self.screen.blit(msg_surf, msg_rect)

        # Re-use the standard gameplay HUD for common elements like health, score, etc.
        self.draw_gameplay_hud()

    def draw_game_intro_scroll(self):
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        self.screen.fill(BLACK)

        # Get current image from GameController (which got it from UIFlowController, which got key from JSON)
        # GameController's self.current_intro_image_surface is now an asset KEY.
        image_asset_key = self.game_controller.current_intro_image_asset_key # This should be the key
        current_image_surface = None
        if image_asset_key:
            current_image_surface = self.asset_manager.get_image(image_asset_key)

        # Text surfaces are prepared by GameController, UIManager just blits them.
        # Font for these texts is handled when GameController prepares them.
        current_text_surfaces = self.game_controller.intro_screen_text_surfaces_current

        if current_image_surface: 
            # ... (image scaling and blitting logic remains the same) ...
            img_w, img_h = current_image_surface.get_size()
            aspect_ratio = img_h / img_w if img_w > 0 else 1
            scaled_w = WIDTH; scaled_h = int(scaled_w * aspect_ratio)
            pos_y = (HEIGHT - scaled_h) // 2; pos_x = 0
            if scaled_h > HEIGHT:
                scaled_h = HEIGHT; scaled_w = int(scaled_h / aspect_ratio if aspect_ratio > 0 else WIDTH)
                pos_x = (WIDTH - scaled_w) // 2; pos_y = 0
            try: 
                self.screen.blit(pygame.transform.smoothscale(current_image_surface, (scaled_w, scaled_h)), (pos_x, pos_y))
            except pygame.error as e:
                logger.error(f"UIManager: Error scaling/blitting intro image (key: {image_asset_key}): {e}")
                if ui_flow_ctrl and ui_flow_ctrl.menu_stars:
                    for star_params in ui_flow_ctrl.menu_stars: 
                        pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])
        else: 
            if ui_flow_ctrl and ui_flow_ctrl.menu_stars:
                for star_params in ui_flow_ctrl.menu_stars: 
                    pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])
        
        if not current_text_surfaces: 
            if ui_flow_ctrl.intro_sequence_finished:
                prompt_font = self.asset_manager.get_font("small_text", 24) # Request font
                if not prompt_font: prompt_font = pygame.font.Font(None, 24)
                prompt_surf = prompt_font.render("Press SPACE or ENTER to Continue", True, CYAN)
                self.screen.blit(prompt_surf, prompt_surf.get_rect(centerx=WIDTH // 2, bottom=HEIGHT - 30))
            return
        
        # ... (text positioning and fading logic remains the same) ...
        total_text_height = 0; line_spacing = 0
        # GameController stores intro_font_key ("codex_category_font") and size (e.g. 38)
        # Font for text surfaces is handled by GC when creating them.
        # For spacing calculation, ideally use the same font.
        font_for_spacing = self.asset_manager.get_font(self.game_controller.intro_font_key, 38) # Example size
        if not font_for_spacing: font_for_spacing = pygame.font.Font(None, 36)
        
        line_spacing = int(font_for_spacing.get_linesize() * 0.4)
        for i, surf in enumerate(current_text_surfaces):
            total_text_height += surf.get_height()
            if i < len(current_text_surfaces) - 1: total_text_height += line_spacing
        
        start_y = (HEIGHT - total_text_height) // 2; current_y = start_y; fade_alpha = 255
        
        if hasattr(ui_flow_ctrl, 'intro_screen_start_time'):
            elapsed_time = pygame.time.get_ticks() - ui_flow_ctrl.intro_screen_start_time
            fade_duration = 1000 
            intro_duration = gs.get_game_setting("INTRO_SCREEN_DURATION_MS", 6000)
            if elapsed_time < fade_duration: fade_alpha = int(255 * (elapsed_time / fade_duration))
            elif intro_duration - elapsed_time < fade_duration: fade_alpha = int(255 * ((intro_duration - elapsed_time) / fade_duration))
            fade_alpha = max(0, min(255, fade_alpha))

        for i, text_surf in enumerate(current_text_surfaces):
            text_rect = text_surf.get_rect(centerx=WIDTH // 2, top=current_y)
            temp_surf = text_surf.copy(); temp_surf.set_alpha(fade_alpha)
            self.screen.blit(temp_surf, text_rect)
            current_y += text_surf.get_height() + line_spacing
        
        if ui_flow_ctrl.intro_sequence_finished:
            prompt_font = self.asset_manager.get_font("small_text", 24)
            if not prompt_font: prompt_font = pygame.font.Font(None, 24)
            prompt_surf = prompt_font.render("Press SPACE or ENTER to Continue", True, CYAN)
            self.screen.blit(prompt_surf, prompt_surf.get_rect(centerx=WIDTH // 2, bottom=HEIGHT - 30))

    def draw_story_message_overlay(self, message):
        # Use _render_text_safe which uses AssetManager
        # Assuming "story_message_font" is a key preloaded by AssetManager (e.g., "neuropol_26")
        # Default size for fallback in _render_text_safe will be used if key lookup fails.
        # Need to pass the size for the font when calling _wrap_text and _render_text_safe.
        story_font_key = "story_message_font"
        story_font_size = 26 # Match the size defined in GameController manifest for this key
        
        font_for_wrap = self.asset_manager.get_font(story_font_key, story_font_size)
        if not font_for_wrap: font_for_wrap = pygame.font.Font(None, story_font_size)

        max_width = WIDTH * 0.7; padding = 20; line_spacing_ratio = 0.2

        wrapped_lines_text = self._wrap_text(message, story_font_key, story_font_size, max_width - 2 * padding)
        
        rendered_lines = [self._render_text_safe(line, story_font_key, WHITE, fallback_size=story_font_size) for line in wrapped_lines_text]
        if not rendered_lines: return

        line_height = font_for_wrap.get_linesize() # Use the actual font for line height
        # ... (rest of positioning logic remains the same) ...
        effective_line_spacing = line_height * line_spacing_ratio
        total_text_height = sum(surf.get_height() for surf in rendered_lines) + (len(rendered_lines) - 1) * effective_line_spacing
        max_line_width = max(surf.get_width() for surf in rendered_lines) if rendered_lines else 0
        
        box_width = max_line_width + 2 * padding
        box_height = total_text_height + 2 * padding
        box_x = (WIDTH - box_width) // 2
        box_y = GAME_PLAY_AREA_HEIGHT - box_height - 20 
        
        overlay_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        overlay_surf.fill((10, 20, 40, 220))
        pygame.draw.rect(overlay_surf, GOLD, overlay_surf.get_rect(), 2, border_radius=10)
        
        current_text_y = padding
        for line_surf in rendered_lines:
            overlay_surf.blit(line_surf, line_surf.get_rect(centerx=box_width // 2, top=current_text_y))
            current_text_y += line_surf.get_height() + effective_line_spacing
            
        self.screen.blit(overlay_surf, (box_x, box_y))

    def draw_codex_screen(self):
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        self.screen.fill(BLACK)
        if ui_flow_ctrl.menu_stars:
            for star_params in ui_flow_ctrl.menu_stars: 
                pygame.draw.circle(self.screen, (50,50,50), (int(star_params[0]), int(star_params[1])), star_params[3])
        
        # Define font keys and sizes (must match manifest)
        codex_title_font_key = "codex_title_font"; codex_title_font_size = 60
        codex_category_font_key = "codex_category_font"; codex_category_font_size = 38
        codex_entry_font_key = "codex_entry_font"; codex_entry_font_size = 30
        codex_content_font_key = "codex_content_font"; codex_content_font_size = 24
        small_text_font_key = "small_text"; small_text_font_size = 24
        medium_text_font_key = "medium_text"; medium_text_font_size = 48
        
        title_surf = self._render_text_safe("Lore Codex", codex_title_font_key, GOLD, fallback_size=codex_title_font_size)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 60))
        self.screen.blit(title_surf, title_rect)
        
        # ... (rest of the layout logic for panels remains similar) ...
        current_view = ui_flow_ctrl.codex_current_view 
        padding = 50
        list_panel_width = WIDTH // 3 - padding * 1.5
        list_panel_x = padding
        content_panel_x = list_panel_x + list_panel_width + padding / 2
        content_panel_width = WIDTH - content_panel_x - padding
        top_y_start = title_rect.bottom + 30
        bottom_y_end = HEIGHT - 80

        # Get actual font objects for measurements if needed, or rely on _render_text_safe for rendering
        font_category = self.asset_manager.get_font(codex_category_font_key, codex_category_font_size)
        font_entry = self.asset_manager.get_font(codex_entry_font_key, codex_entry_font_size)
        font_content = self.asset_manager.get_font(codex_content_font_key, codex_content_font_size)

        if not all([font_category, font_entry, font_content]): # Check if fonts were loaded
            fallback_surf = self._render_text_safe("Codex fonts loading...", medium_text_font_key, WHITE, fallback_size=medium_text_font_size)
            self.screen.blit(fallback_surf, fallback_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            return

        if self.codex_list_item_height == 0:
             self.codex_list_item_height = font_entry.get_height() + 15
             if self.codex_list_item_height > 0: self.codex_max_visible_items_list = (bottom_y_end - top_y_start) // self.codex_list_item_height
             else: self.codex_max_visible_items_list = 1
        
        content_line_height = font_content.get_linesize()
        if self.codex_max_visible_lines_content == 0 and content_line_height > 0:
             available_height_for_content_text_calc = bottom_y_end - (top_y_start + font_category.get_height() + 20)
             self.codex_max_visible_lines_content = available_height_for_content_text_calc // content_line_height if content_line_height > 0 else 1
        
        nav_instr = ""; current_list_y = top_y_start + 20 

        if current_view == "categories":
            # ... (logic uses _render_text_safe with category_font_key and size) ...
            categories = ui_flow_ctrl.codex_categories_list
            selected_category_idx = ui_flow_ctrl.codex_selected_category_index
            if not categories: 
                no_lore_surf = self._render_text_safe("No lore unlocked.", medium_text_font_key, WHITE, fallback_size=medium_text_font_size)
                self.screen.blit(no_lore_surf, no_lore_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            else:
                max_visible = self.codex_max_visible_items_list if self.codex_max_visible_items_list > 0 else 1
                start_idx = max(0, selected_category_idx - max_visible // 2)
                start_idx = min(start_idx, max(0, len(categories) - max_visible))
                end_idx = min(len(categories), start_idx + max_visible)
                for i_display, i_actual in enumerate(range(start_idx, end_idx)):
                    category_name = categories[i_actual]
                    y_pos = current_list_y + i_display * self.codex_list_item_height
                    color = YELLOW if i_actual == selected_category_idx else WHITE
                    cat_name_surf = self._render_text_safe(category_name, codex_category_font_key, color, fallback_size=codex_category_font_size)
                    self.screen.blit(cat_name_surf, (list_panel_x + 10, y_pos))
            nav_instr = "UP/DOWN: Select | ENTER: View Entries | ESC: Main Menu"

        elif current_view == "entries":
            # ... (logic uses _render_text_safe with entry_font_key and size) ...
            category_name = ui_flow_ctrl.codex_current_category_name
            entries = ui_flow_ctrl.codex_entries_in_category_list
            selected_entry_idx = ui_flow_ctrl.codex_selected_entry_index_in_category
            
            cat_title_surf = self._render_text_safe(f"{category_name}", codex_category_font_key, GOLD, fallback_size=codex_category_font_size)
            self.screen.blit(cat_title_surf, (list_panel_x + 10, top_y_start))
            current_list_y = top_y_start + cat_title_surf.get_height() + 15
            
            if not entries: 
                no_entries_surf = self._render_text_safe("No entries here.", codex_entry_font_key, GREY, fallback_size=codex_entry_font_size)
                self.screen.blit(no_entries_surf, (list_panel_x + 20, current_list_y))
            else:
                max_visible = self.codex_max_visible_items_list if self.codex_max_visible_items_list > 0 else 1
                start_idx = max(0, selected_entry_idx - max_visible // 2)
                start_idx = min(start_idx, max(0, len(entries) - max_visible))
                end_idx = min(len(entries), start_idx + max_visible)
                for i_display, i_actual in enumerate(range(start_idx, end_idx)):
                    entry_data = entries[i_actual]
                    y_pos = current_list_y + i_display * self.codex_list_item_height
                    color = YELLOW if i_actual == selected_entry_idx else WHITE
                    entry_title_surf = self._render_text_safe(entry_data.get("title", "Untitled"), codex_entry_font_key, color, fallback_size=codex_entry_font_size)
                    self.screen.blit(entry_title_surf, (list_panel_x + 20, y_pos))
            nav_instr = "UP/DOWN: Select | ENTER: Read | ESC: Back to Categories"

        elif current_view == "content":
            # ... (logic uses _render_text_safe with content_font_key and size) ...
            selected_entry_id = ui_flow_ctrl.codex_selected_entry_id
            entry_data = self.drone_system.get_lore_entry_details(selected_entry_id) if selected_entry_id else None
            category_name_reminder = ui_flow_ctrl.codex_current_category_name
            is_drone_entry = entry_data.get("category") == "Drones" if entry_data else False
            is_race_entry = entry_data.get("category") == "Alien Races" if entry_data else False
            
            # Image path from lore data becomes asset key
            image_asset_key_from_lore = entry_data.get("image") if entry_data else None
            # AssetManager keys are relative to "assets", lore paths might be "assets/images/..."
            if image_asset_key_from_lore and image_asset_key_from_lore.startswith("assets/"):
                image_asset_key_from_lore = image_asset_key_from_lore[len("assets/"):]
            
            current_image_y_pos = top_y_start + 20

            if category_name_reminder:
                cat_reminder_surf = self._render_text_safe(f"{category_name_reminder}", codex_entry_font_key, DARK_GREY, fallback_size=codex_entry_font_size)
                self.screen.blit(cat_reminder_surf, (list_panel_x +10 , top_y_start ))
                current_image_y_pos = top_y_start + cat_reminder_surf.get_height() + 20

            if entry_data:
                content_title_surf = self._render_text_safe(entry_data.get("title", "Untitled"), codex_category_font_key, GOLD, fallback_size=codex_category_font_size)
                self.screen.blit(content_title_surf, (content_panel_x, top_y_start))
                content_text_render_y = top_y_start + content_title_surf.get_height() + 20
                text_area_width = content_panel_width - 20

                # Get image from AssetManager
                codex_image_surf = None
                if image_asset_key_from_lore:
                    # Determine scale for drone/race images if needed, or load as is
                    img_max_w_drone = list_panel_width - 20
                    img_max_h_drone = HEIGHT * 0.3
                    img_max_w_race = content_panel_width * 0.6
                    img_max_h_race = HEIGHT * 0.25
                    
                    # Temporarily get original to calculate scaled dimensions, then get scaled from AssetManager
                    # Or, AssetManager could have a get_image_scaled_to_fit(key, max_w, max_h)
                    # For now, let's assume GameController preloaded with appropriate keys if specific scaling is always needed,
                    # or we load unscaled and scale here.
                    # To keep it simple: UIManager fetches unscaled, then scales. AssetManager caches unscaled.
                    
                    unscaled_codex_image = self.asset_manager.get_image(image_asset_key_from_lore)
                    if unscaled_codex_image:
                        if is_drone_entry:
                            original_w, original_h = unscaled_codex_image.get_size()
                            aspect = original_h / original_w if original_w > 0 else 1
                            scaled_w = img_max_w_drone; scaled_h = int(scaled_w * aspect)
                            if scaled_h > img_max_h_drone: scaled_h = int(img_max_h_drone); scaled_w = int(scaled_h / aspect if aspect > 0 else img_max_w_drone)
                            if scaled_w > 0 and scaled_h > 0:
                                try: codex_image_surf = pygame.transform.smoothscale(unscaled_codex_image, (scaled_w, scaled_h))
                                except pygame.error as e: logger.error(f"UIManager: Error scaling Drone Codex image '{image_asset_key_from_lore}': {e}")
                        elif is_race_entry: # For race image (drawn below text)
                            original_w_race, original_h_race = unscaled_codex_image.get_size()
                            aspect_race = original_h_race / original_w_race if original_w_race > 0 else 1
                            scaled_w_race = img_max_w_race; scaled_h_race = int(scaled_w_race * aspect_race)
                            if scaled_h_race > img_max_h_race: scaled_h_race = int(img_max_h_race); scaled_w_race = int(scaled_h_race / aspect_race if aspect_race > 0 else img_max_w_race)
                            if scaled_w_race > 0 and scaled_h_race > 0:
                                try: codex_image_surf = pygame.transform.smoothscale(unscaled_codex_image, (scaled_w_race, scaled_h_race))
                                except pygame.error as e: logger.error(f"UIManager: Error scaling Race Codex image '{image_asset_key_from_lore}': {e}")
                
                # Draw Drone image
                if is_drone_entry and codex_image_surf:
                     self.screen.blit(codex_image_surf, (list_panel_x + (list_panel_width - codex_image_surf.get_width()) // 2, current_image_y_pos))

                # Display content text
                content_text = entry_data.get("content", "No content available.")
                scroll_offset_lines = ui_flow_ctrl.codex_content_scroll_offset
                wrapped_lines = self._wrap_text(content_text, codex_content_font_key, codex_content_font_size, text_area_width)
                ui_flow_ctrl.codex_current_entry_total_lines = len(wrapped_lines)
                
                text_content_area_available_height = bottom_y_end - content_text_render_y - 10
                race_image_to_draw_below_text_surf = None # This will hold the scaled surface for race image
                scaled_race_img_h_val = 0
                if is_race_entry and codex_image_surf: # If it's a race entry, codex_image_surf holds the scaled race image
                    race_image_to_draw_below_text_surf = codex_image_surf
                    scaled_race_img_h_val = race_image_to_draw_below_text_surf.get_height()
                    text_content_area_available_height -= (scaled_race_img_h_val + 20)
                
                max_lines = text_content_area_available_height // content_line_height if content_line_height > 0 else 0
                if max_lines <= 0 and wrapped_lines: max_lines = 1
                
                lines_drawn_y_end = content_text_render_y
                for i in range(max_lines):
                    line_idx = scroll_offset_lines + i
                    if 0 <= line_idx < len(wrapped_lines):
                        line_surf = self._render_text_safe(wrapped_lines[line_idx], codex_content_font_key, WHITE, fallback_size=codex_content_font_size)
                        self.screen.blit(line_surf, (content_panel_x + 10, content_text_render_y + i * content_line_height))
                        lines_drawn_y_end = content_text_render_y + (i + 1) * content_line_height
                
                if race_image_to_draw_below_text_surf:
                    race_img_y_pos = lines_drawn_y_end + 20
                    if race_img_y_pos + scaled_race_img_h_val < bottom_y_end:
                        self.screen.blit(race_image_to_draw_below_text_surf, 
                                         (content_panel_x + (text_area_width - race_image_to_draw_below_text_surf.get_width()) // 2, race_img_y_pos))
                
                # Scroll indicators
                if len(wrapped_lines) > max_lines: 
                    up_arrow_surf = self._render_text_safe("▲ Up", small_text_font_key, YELLOW, fallback_size=small_text_font_size)
                    down_arrow_surf = self._render_text_safe("▼ Down", small_text_font_key, YELLOW, fallback_size=small_text_font_size)
                    if scroll_offset_lines > 0: 
                        self.screen.blit(up_arrow_surf, (content_panel_x + text_area_width - up_arrow_surf.get_width(), content_text_render_y - 25))
                    if scroll_offset_lines + max_lines < len(wrapped_lines):
                        scroll_down_y_pos = lines_drawn_y_end + 5 
                        if race_image_to_draw_below_text_surf and (race_img_y_pos + scaled_race_img_h_val + down_arrow_surf.get_height() > bottom_y_end -5):
                            scroll_down_y_pos = lines_drawn_y_end + 5 
                        elif not race_image_to_draw_below_text_surf: 
                            scroll_down_y_pos = bottom_y_end - down_arrow_surf.get_height() -5
                        self.screen.blit(down_arrow_surf, (content_panel_x + text_area_width - down_arrow_surf.get_width(), scroll_down_y_pos ))
                nav_instr = "UP/DOWN: Scroll | ESC: Back to Entries List"
            else: 
                error_surf = self._render_text_safe("Error: Could not load entry content.", medium_text_font_key, RED, fallback_size=medium_text_font_size)
                self.screen.blit(error_surf, error_surf.get_rect(center=(content_panel_x + content_panel_width // 2, HEIGHT // 2)))
                nav_instr = "ESC: Back"
        else: 
            nav_instr = "ESC: Main Menu"
        
        # Navigation instructions at the bottom
        nav_surf = self._render_text_safe(nav_instr, small_text_font_key, self.INSTRUCTION_TEXT_COLOR, fallback_size=small_text_font_size)
        # ... (background box for nav instructions remains the same) ...
        nav_bg_box = pygame.Surface((nav_surf.get_width() + self.INSTRUCTION_PADDING_X, nav_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        nav_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        nav_bg_box.blit(nav_surf, nav_surf.get_rect(center=(nav_bg_box.get_width() // 2, nav_bg_box.get_height() // 2)))
        self.screen.blit(nav_bg_box, nav_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))

    def draw_main_menu(self):
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        menu_bg_surface = self.ui_asset_surfaces.get("menu_background")
        if menu_bg_surface:
            try: 
                self.screen.blit(pygame.transform.smoothscale(menu_bg_surface, (WIDTH, HEIGHT)), (0,0))
            except Exception as e: 
                logger.error(f"UIManager: Error blitting menu background: {e}")
                self.screen.fill(BLACK)
        else: 
            self.screen.fill(BLACK) 
        
        if ui_flow_ctrl.menu_stars:
            for star_params in ui_flow_ctrl.menu_stars: 
                pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])
        
        selected_option_idx = ui_flow_ctrl.selected_menu_option
        menu_item_start_y = HEIGHT // 2 - 80 
        item_spacing = 85 
        unselected_label_font_size = 48
        selected_label_font_size = 54
        # Font for icons (emoji or symbols) - use key from manifest
        temp_icon_font = self.asset_manager.get_font("ui_emoji_general", 32) # Example size, adjust as needed
        if not temp_icon_font: temp_icon_font = self.asset_manager.get_font("menu_text", 60) # Fallback
        if not temp_icon_font: temp_icon_font = pygame.font.Font(None, 32) # Final fallback

        # Menu font path is no longer needed here, GameController preloads "neuropol_title" etc.
        # font_path_neuropol = self.game_controller.font_path_neuropol # REMOVE

        menu_options_with_icons = { 
            "Start Game": "🛸 Start Game", "Maze Defense": "🧱 Maze Defense", 
            "Select Drone": "\U0001F579 Select Drone", "Codex": "📜 Codex", 
            "Settings": "\u2699 Settings", "Leaderboard": "🏆 Leaderboard", "Quit": "❌ Quit" 
        }
        actual_menu_options = ui_flow_ctrl.menu_options
        max_combined_width = 0; max_content_height = 0; icon_label_spacing = 10

        for option_key_calc in actual_menu_options:
            full_label_calc = menu_options_with_icons.get(option_key_calc, option_key_calc)
            icon_char_calc = ""; label_text_calc = full_label_calc
            if len(full_label_calc) >= 2 and full_label_calc[1] == " " and not full_label_calc[0].isalnum(): 
                icon_char_calc = full_label_calc[0]; label_text_calc = full_label_calc[2:]
            
            # Font for label text - key "menu_text" from manifest, with specific size
            temp_label_font_for_calc = self.asset_manager.get_font("menu_text", selected_label_font_size)
            if not temp_label_font_for_calc: temp_label_font_for_calc = pygame.font.Font(None, selected_label_font_size)
            
            icon_surf_calc = temp_icon_font.render(icon_char_calc, True, WHITE) if icon_char_calc else None
            label_surf_calc = temp_label_font_for_calc.render(label_text_calc, True, WHITE)
            
            current_combined_width = 0; current_content_height = 0
            if icon_surf_calc: 
                current_combined_width += icon_surf_calc.get_width() + icon_label_spacing
                current_content_height = max(current_content_height, icon_surf_calc.get_height())
            current_combined_width += label_surf_calc.get_width()
            current_content_height = max(current_content_height, label_surf_calc.get_height())
            
            max_combined_width = max(max_combined_width, current_combined_width)
            max_content_height = max(max_content_height, current_content_height)
        
        horizontal_padding = 30; vertical_padding = 15; min_button_width = 280
        fixed_button_width = max(min_button_width, max_combined_width + horizontal_padding)
        fixed_button_height = max_content_height + vertical_padding

        for i, option_key in enumerate(actual_menu_options):
            full_label = menu_options_with_icons.get(option_key, option_key)
            is_selected = (i == selected_option_idx)
            text_color = GOLD if is_selected else WHITE
            
            icon_char = ""; label_text = full_label
            if len(full_label) >= 2 and full_label[1] == " " and not full_label[0].isalnum(): 
                icon_char = full_label[0]; label_text = full_label[2:]
            
            current_label_font_size = selected_label_font_size if is_selected else unselected_label_font_size
            # Use the same "menu_text" key but with dynamic size
            label_font = self.asset_manager.get_font("menu_text", current_label_font_size)
            if not label_font: label_font = pygame.font.Font(None, current_label_font_size) # Fallback
            
            icon_font = temp_icon_font # Already fetched
            icon_surf = icon_font.render(icon_char, True, text_color) if icon_char else None
            label_surf = label_font.render(label_text, True, text_color)
            
            button_surface = pygame.Surface((fixed_button_width, fixed_button_height), pygame.SRCALPHA)
            bg_color = (70, 70, 70, 220) if is_selected else (50, 50, 50, 180)
            pygame.draw.rect(button_surface, bg_color, button_surface.get_rect(), border_radius=15)
            if is_selected: pygame.draw.rect(button_surface, GOLD, button_surface.get_rect(), 3, border_radius=15)
            
            content_start_x = horizontal_padding // 2 ; y_center_content = fixed_button_height // 2
            if icon_surf: 
                icon_rect = icon_surf.get_rect(centery=y_center_content); icon_rect.left = content_start_x
                button_surface.blit(icon_surf, icon_rect); content_start_x = icon_rect.right + icon_label_spacing

            label_rect = label_surf.get_rect(centery=y_center_content); label_rect.left = content_start_x
            button_surface.blit(label_surf, label_rect)
            
            current_button_y = menu_item_start_y + i * item_spacing
            button_screen_rect = button_surface.get_rect(center=(WIDTH // 2, current_button_y))
            self.screen.blit(button_surface, button_screen_rect)
                   
        if gs.SETTINGS_MODIFIED:
            warning_surf = self._render_text_safe("Custom settings active: Leaderboard disabled.", "small_text", YELLOW, fallback_size=24)
            # ... (background box for warning remains the same) ...
            warning_bg_box = pygame.Surface((warning_surf.get_width() + self.INSTRUCTION_PADDING_X, warning_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
            warning_bg_box.fill(self.INSTRUCTION_BG_COLOR)
            warning_bg_box.blit(warning_surf, warning_surf.get_rect(center=(warning_bg_box.get_width() // 2, warning_bg_box.get_height() // 2)))
            self.screen.blit(warning_bg_box, warning_bg_box.get_rect(center=(WIDTH // 2, self.SECONDARY_INSTRUCTION_CENTER_Y)))

    def draw_drone_select_menu(self):
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        # Use specific font keys and sizes for rendering
        title_surf = self._render_text_safe("Select Drone", "title_text", GOLD, fallback_size=90)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 70))
        self.screen.blit(title_surf, title_rect)

        drone_options_ids = ui_flow_ctrl.drone_select_options
        selected_preview_idx = ui_flow_ctrl.selected_drone_preview_index

        if not drone_options_ids:
            no_drones_surf = self._render_text_safe("NO DRONES AVAILABLE", "large_text", RED, fallback_size=74)
            self.screen.blit(no_drones_surf, no_drones_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            return

        current_drone_id = drone_options_ids[selected_preview_idx]
        drone_config = self.drone_system.get_drone_config(current_drone_id)
        drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False)
        is_unlocked = self.drone_system.is_drone_unlocked(current_drone_id)
        is_currently_equipped = (current_drone_id == self.drone_system.get_selected_drone_id())
        
        # Get drone image from AssetManager (GameController preloads these)
        # Key for main display images: e.g., "drone_DRONE_select_preview"
        drone_image_asset_key = f"drone_{current_drone_id}_select_preview"
        # Drone select screen might want a specific size, or load unscaled and scale here
        # For now, assuming GameController preloaded with a suitable size or UIManager scales it.
        # Let's assume GameController's manifest does not scale these and UIManager scales as needed.
        unscaled_drone_image_surf = self.asset_manager.get_image(drone_image_asset_key)
        drone_image_surf_display = None
        target_display_size = (200,200) # Target display size for drone image on this screen

        if unscaled_drone_image_surf:
            try:
                # Scale to fit target_display_size while maintaining aspect
                original_w, original_h = unscaled_drone_image_surf.get_size()
                aspect = original_w / original_h if original_h > 0 else 1
                scaled_w, scaled_h = target_display_size
                if aspect > 1: scaled_h = int(target_display_size[0] / aspect)
                else: scaled_w = int(target_display_size[1] * aspect)
                scaled_w = max(1, scaled_w); scaled_h = max(1, scaled_h)
                drone_image_surf_display = pygame.transform.smoothscale(unscaled_drone_image_surf, (scaled_w, scaled_h))
            except pygame.error as e:
                logger.error(f"UIManager: Error scaling drone image '{drone_image_asset_key}': {e}")
        
        if not drone_image_surf_display: # Fallback if loading or scaling failed
            drone_image_surf_display = self.asset_manager._create_fallback_surface(size=target_display_size, text=current_drone_id[:1], font_key="medium_text", font_size=74) # Use AssetManager's fallback

        img_width = drone_image_surf_display.get_width()
        img_height = drone_image_surf_display.get_height()

        name_text = drone_config.get("name", "N/A")
        # Using font key "drone_name_cycle" with its defined size (e.g., 42)
        name_surf_temp = self._render_text_safe(name_text, "drone_name_cycle", WHITE, fallback_size=42)
        name_height = name_surf_temp.get_height()
        
        # Stats display
        # ... (stats calculation remains similar) ...
        hp_stat = drone_stats.get("hp"); speed_stat = drone_stats.get("speed")
        turn_speed_stat = drone_stats.get("turn_speed"); fire_rate_mult = drone_stats.get("fire_rate_multiplier", 1.0)
        special_ability_key = drone_stats.get("special_ability")
        hp_display = str(hp_stat) if hp_stat is not None else "N/A"
        speed_display = f"{speed_stat:.1f}" if isinstance(speed_stat, (int, float)) else "N/A"
        turn_speed_display = f"{turn_speed_stat:.1f}" if isinstance(turn_speed_stat, (int, float)) else "N/A"
        fire_rate_text = f"{fire_rate_mult:.2f}x mult";
        if fire_rate_mult == 1.0: fire_rate_text = "Normal"
        elif fire_rate_mult < 1.0: fire_rate_text += " (Faster)"
        else: fire_rate_text += " (Slower)"
        special_ability_name = "None"
        if special_ability_key == "phantom_cloak": special_ability_name = "Phantom Cloak"
        elif special_ability_key == "omega_boost": special_ability_name = "Omega Boost"
        elif special_ability_key == "energy_shield_pulse": special_ability_name = "Shield Pulse"
        
        stats_data_tuples = [("HP:", hp_display), ("Speed:", speed_display), ("Turn Speed:", turn_speed_display), ("Fire Rate:", fire_rate_text), ("Special:", special_ability_name)]
        stats_content_surfaces = []; max_stat_label_w = 0; max_stat_value_w = 0
        # Font for stats labels and values
        font_stats_label = self.asset_manager.get_font("drone_stats_label_cycle", 26)
        if not font_stats_label: font_stats_label = pygame.font.Font(None, 26)
        stat_line_h = font_stats_label.get_height() + 5

        for label_str, value_str in stats_data_tuples:
            label_s = self._render_text_safe(label_str, "drone_stats_label_cycle", LIGHT_BLUE if is_unlocked else GREY, fallback_size=26)
            value_s = self._render_text_safe(value_str, "drone_stats_value_cycle", WHITE if is_unlocked else GREY, fallback_size=28)
            stats_content_surfaces.append((label_s, value_s))
            max_stat_label_w = max(max_stat_label_w, label_s.get_width()); max_stat_value_w = max(max_stat_value_w, value_s.get_width())
        
        stats_box_padding = 15
        stats_box_visual_width = max_stat_label_w + max_stat_value_w + 3 * stats_box_padding
        stats_box_visual_height = (len(stats_content_surfaces) * stat_line_h) - (5 if stats_content_surfaces else 0) + 2 * stats_box_padding

        # Description
        desc_text = drone_config.get("description", "")
        desc_color_final = (200,200,200) if is_unlocked else (100,100,100)
        desc_max_width_for_card = WIDTH * 0.45
        desc_lines_surfs = []
        # Font for description
        desc_font_for_wrap = self.asset_manager.get_font("drone_desc_cycle", 22)
        if not desc_font_for_wrap: desc_font_for_wrap = pygame.font.Font(None, 22)

        # Use the actual font object for text wrapping size calculation
        wrapped_desc_lines = self._wrap_text_with_font_obj(desc_text, desc_font_for_wrap, desc_max_width_for_card)
        for line_text in wrapped_desc_lines:
            desc_lines_surfs.append(self._render_text_safe(line_text, "drone_desc_cycle", desc_color_final, fallback_size=22))
        
        total_desc_height = sum(s.get_height() for s in desc_lines_surfs) + (len(desc_lines_surfs)-1)*3 if desc_lines_surfs else 0

        # Unlock/Select Info Text
        # ... (unlock text logic remains similar) ...
        unlock_text_str = ""; unlock_text_color = WHITE
        unlock_condition = drone_config.get("unlock_condition", {})
        if not is_unlocked:
            condition_text_str = unlock_condition.get("description", "Locked"); unlock_cost_val = unlock_condition.get("value")
            type_is_cores_unlock = unlock_condition.get("type") == "cores"; unlock_text_str = condition_text_str
            if type_is_cores_unlock and unlock_cost_val is not None:
                 can_afford = self.drone_system.get_player_cores() >= unlock_cost_val
                 unlock_text_str = f"Unlock: {unlock_cost_val}c (ENTER)" if can_afford else f"Unlock: {unlock_cost_val}c (Not Enough)"
                 unlock_text_color = GREEN if can_afford else YELLOW
            else: unlock_text_color = YELLOW
        elif is_currently_equipped: unlock_text_str = "EQUIPPED"; unlock_text_color = GREEN
        else: unlock_text_str = "Press ENTER to Select"; unlock_text_color = CYAN
        
        unlock_info_surf = self._render_text_safe(unlock_text_str, "drone_unlock_cycle", unlock_text_color, fallback_size=20)
        unlock_info_height = unlock_info_surf.get_height() if unlock_info_surf else 0

        # ... (card dimension calculation and drawing remains similar, using rendered surfaces) ...
        spacing_between_elements = 15; padding_inside_card = 25
        card_content_total_h = (img_height + spacing_between_elements + name_height + 
                                spacing_between_elements + stats_box_visual_height + 
                                spacing_between_elements + total_desc_height + 
                                spacing_between_elements + unlock_info_height)
        max_content_width_for_card = max(img_width, name_surf_temp.get_width(), stats_box_visual_width, 
                                         max(s.get_width() for s in desc_lines_surfs) if desc_lines_surfs else 0, 
                                         unlock_info_surf.get_width() if unlock_info_surf else 0)
        card_w = max(max_content_width_for_card + 2 * padding_inside_card, WIDTH * 0.5); card_w = min(card_w, WIDTH * 0.65)
        card_h = card_content_total_h + 2 * padding_inside_card + 20
        title_bottom = title_rect.bottom if title_rect else 100
        main_card_x = (WIDTH - card_w) // 2; main_card_y = title_bottom + 30 # Slightly less gap
        main_card_rect = pygame.Rect(main_card_x, main_card_y, card_w, card_h)
        
        pygame.draw.rect(self.screen, (25,30,40,230), main_card_rect, border_radius=20)
        pygame.draw.rect(self.screen, GOLD, main_card_rect, 3, border_radius=20)

        current_y_in_card = main_card_rect.top + padding_inside_card
        # Drone Image
        if drone_image_surf_display:
            display_img_to_blit = drone_image_surf_display
            if not is_unlocked: temp_img = drone_image_surf_display.copy(); temp_img.set_alpha(100); display_img_to_blit = temp_img
            final_img_rect = display_img_to_blit.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(display_img_to_blit, final_img_rect)
            current_y_in_card = final_img_rect.bottom + spacing_between_elements
        else: current_y_in_card += target_display_size[1] + spacing_between_elements

        # Drone Name
        name_color_final = WHITE if is_unlocked else GREY
        name_surf_final = self._render_text_safe(name_text, "drone_name_cycle", name_color_final, fallback_size=42)
        final_name_rect = name_surf_final.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
        self.screen.blit(name_surf_final, final_name_rect); current_y_in_card = final_name_rect.bottom + spacing_between_elements

        # Stats Box
        final_stats_box_draw_rect = pygame.Rect(main_card_rect.centerx - stats_box_visual_width // 2, current_y_in_card, stats_box_visual_width, stats_box_visual_height)
        pygame.draw.rect(self.screen, (40,45,55,200), final_stats_box_draw_rect, border_radius=10)
        pygame.draw.rect(self.screen, CYAN, final_stats_box_draw_rect, 1, border_radius=10)
        stat_y_pos_render = final_stats_box_draw_rect.top + stats_box_padding
        for i, (label_s, value_s) in enumerate(stats_content_surfaces):
            self.screen.blit(label_s, (final_stats_box_draw_rect.left + stats_box_padding, stat_y_pos_render))
            self.screen.blit(value_s, (final_stats_box_draw_rect.right - stats_box_padding - value_s.get_width(), stat_y_pos_render))
            stat_y_pos_render += max(label_s.get_height(), value_s.get_height()) + (5 if i < len(stats_content_surfaces)-1 else 0)
        current_y_in_card = final_stats_box_draw_rect.bottom + spacing_between_elements
        
        # Description
        desc_start_y_render = current_y_in_card
        for line_surf in desc_lines_surfs:
            self.screen.blit(line_surf, line_surf.get_rect(centerx=main_card_rect.centerx, top=desc_start_y_render))
            desc_start_y_render += line_surf.get_height() + 3
        current_y_in_card = desc_start_y_render + 5 
        
        if unlock_info_surf:
            unlock_info_rect = unlock_info_surf.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(unlock_info_surf, unlock_info_rect)

        # Navigation Arrows
        arrow_font = self.asset_manager.get_font("arrow_font_key", 60) # Default size defined in manifest
        if not arrow_font: arrow_font = self.asset_manager.get_font("large_text", 74) # Fallback
        if not arrow_font: arrow_font = pygame.font.Font(None, 60) # Final fallback
        
        left_arrow_surf = arrow_font.render("◀", True, WHITE if len(drone_options_ids) > 1 else GREY)
        right_arrow_surf = arrow_font.render("▶", True, WHITE if len(drone_options_ids) > 1 else GREY)
        arrow_y_center = main_card_rect.centery; arrow_padding_from_card_edge = 40
        if len(drone_options_ids) > 1:
            left_arrow_rect = left_arrow_surf.get_rect(centery=arrow_y_center, right=main_card_rect.left - arrow_padding_from_card_edge)
            self.screen.blit(left_arrow_surf, left_arrow_rect)
            right_arrow_rect = right_arrow_surf.get_rect(centery=arrow_y_center, left=main_card_rect.right + arrow_padding_from_card_edge)
            self.screen.blit(right_arrow_surf, right_arrow_rect)
        
        instr_text = "LEFT/RIGHT: Cycle | ENTER: Select/Unlock | ESC: Back"
        instr_surf = self._render_text_safe(instr_text, "small_text", self.INSTRUCTION_TEXT_COLOR, fallback_size=24)
        # ... (background box for instructions remains the same) ...
        instr_bg_box = pygame.Surface((instr_surf.get_width() + self.INSTRUCTION_PADDING_X, instr_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        instr_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        instr_bg_box.blit(instr_surf, instr_surf.get_rect(center=(instr_bg_box.get_width() // 2, instr_bg_box.get_height() // 2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))
        
        # Player Cores Display
        cores_label_text_surf = self._render_text_safe(f"Player Cores: ", "ui_text", GOLD, fallback_size=28)
        cores_value_text_surf = self._render_text_safe(f"{self.drone_system.get_player_cores()}", "ui_values", GOLD, fallback_size=30)
        cores_emoji_surf = self._render_text_safe(" 💠", "ui_emoji_general", GOLD, fallback_size=32)
        
        # ... (cores display positioning remains the same) ...
        total_cores_display_width = cores_label_text_surf.get_width() + cores_value_text_surf.get_width() + cores_emoji_surf.get_width()
        cores_start_x = WIDTH - 20 - total_cores_display_width
        max_element_height_cores = max(cores_label_text_surf.get_height(), cores_value_text_surf.get_height(), cores_emoji_surf.get_height())
        cores_y_baseline = self.BOTTOM_INSTRUCTION_CENTER_Y - (instr_bg_box.get_height() // 2) - 10 - max_element_height_cores 
        current_x_offset_cores = cores_start_x
        self.screen.blit(cores_label_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_label_text_surf.get_height()) // 2))
        current_x_offset_cores += cores_label_text_surf.get_width()
        self.screen.blit(cores_value_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_value_text_surf.get_height()) // 2))
        current_x_offset_cores += cores_value_text_surf.get_width()
        self.screen.blit(cores_emoji_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_emoji_surf.get_height()) // 2))

    def _wrap_text_with_font_obj(self, text, font_object, max_width):
        """Wraps text to fit within a maximum width, using a pre-fetched font object."""
        # This is a helper variation of _wrap_text, useful when the font object is already available
        if not font_object: # Fallback if font_object is None
            logger.warning("UIManager: _wrap_text_with_font_obj called with None font_object. Text may not wrap correctly.")
            return [text] # Return original text as a single line

        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font_object.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip())
        return lines

    def draw_gameplay_hud(self):
        if not self.game_controller.player: return

        panel_y_start = GAME_PLAY_AREA_HEIGHT; panel_height = BOTTOM_PANEL_HEIGHT
        panel_surf = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA)
        panel_surf.fill((20,25,35,220)); pygame.draw.line(panel_surf, (80,120,170,200), (0,0), (WIDTH,0), 2)
        self.screen.blit(panel_surf, (0, panel_y_start))

        h_padding = 20; v_padding = 10; element_spacing = 6; bar_height = 18
        icon_to_bar_gap = 10; icon_spacing = 5; text_icon_spacing = 2
        current_time_ticks = pygame.time.get_ticks()
        
        # Font keys and sizes (match manifest)
        ui_text_font_key = "ui_text"; ui_text_font_size = 28
        ui_values_font_key = "ui_values"; ui_values_font_size = 30
        ui_emoji_general_key = "ui_emoji_general"; ui_emoji_general_size = 32
        ui_emoji_small_key = "ui_emoji_small"; ui_emoji_small_size = 20
        small_text_font_key = "small_text"; small_text_font_size = 24
        
        # --- Left Side ---
        vitals_x_start = h_padding; current_vitals_y = panel_y_start + panel_height - v_padding
        vitals_section_width = int(WIDTH / 3.2)
        max_icon_width_left = 0
        player_obj = self.game_controller.player
        
        # Weapon Icon (using _render_text_safe for emoji)
        weapon_icon_char = WEAPON_MODE_ICONS.get(player_obj.current_weapon_mode, "💥")
        temp_weapon_icon_surf = self._render_text_safe(weapon_icon_char, ui_emoji_small_key, ORANGE, fallback_size=ui_emoji_small_size)
        if temp_weapon_icon_surf: max_icon_width_left = max(max_icon_width_left, temp_weapon_icon_surf.get_width())
        
        # Player Lives Icon (from ui_asset_surfaces, loaded via AssetManager)
        life_icon_surf = self.ui_asset_surfaces.get("current_drone_life_icon")
        if life_icon_surf: max_icon_width_left = max(max_icon_width_left, life_icon_surf.get_width())
        
        if life_icon_surf:
            lives_y_pos = current_vitals_y - self.ui_icon_size_lives[1]
            lives_draw_x = vitals_x_start
            for i in range(self.game_controller.lives):
                self.screen.blit(life_icon_surf, (lives_draw_x + i * (self.ui_icon_size_lives[0] + icon_spacing), lives_y_pos))
            current_vitals_y = lives_y_pos - element_spacing
        
        # Weapon Charge Bar
        weapon_bar_y_pos = current_vitals_y - bar_height
        if temp_weapon_icon_surf:
             self.screen.blit(temp_weapon_icon_surf, (vitals_x_start, weapon_bar_y_pos + (bar_height - temp_weapon_icon_surf.get_height()) // 2))
             bar_start_x_weapon = vitals_x_start + temp_weapon_icon_surf.get_width() + icon_to_bar_gap
        else: # Fallback if icon surface failed to render
             bar_start_x_weapon = vitals_x_start 
        
        min_bar_segment_width = 25 
        bar_segment_reduction_factor = 0.85
        available_width_for_bar = vitals_section_width - (bar_start_x_weapon - vitals_x_start) # Width from bar start to section end
        bar_segment_width_weapon = max(min_bar_segment_width, int(available_width_for_bar * bar_segment_reduction_factor))
        
        # ... (weapon charge calculation logic remains the same) ...
        charge_fill_pct = 0.0; weapon_ready_color = PLAYER_BULLET_COLOR
        cooldown_duration = player_obj.current_shoot_cooldown; time_since_last_shot = current_time_ticks - player_obj.last_shot_time
        if player_obj.current_weapon_mode == gs.WEAPON_MODE_HEATSEEKER or player_obj.current_weapon_mode == gs.WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
            weapon_ready_color = MISSILE_COLOR; time_since_last_shot = current_time_ticks - player_obj.last_missile_shot_time; cooldown_duration = player_obj.current_missile_cooldown
        elif player_obj.current_weapon_mode == gs.WEAPON_MODE_LIGHTNING:
            weapon_ready_color = LIGHTNING_COLOR; time_since_last_shot = current_time_ticks - player_obj.last_lightning_time; cooldown_duration = player_obj.current_lightning_cooldown
        if cooldown_duration > 0: charge_fill_pct = min(1.0, time_since_last_shot / cooldown_duration)
        else: charge_fill_pct = 1.0
        charge_bar_fill_color = weapon_ready_color if charge_fill_pct >= 1.0 else ORANGE
        weapon_bar_width_fill = int(bar_segment_width_weapon * charge_fill_pct)
        
        pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_weapon, weapon_bar_y_pos, bar_segment_width_weapon, bar_height))
        if weapon_bar_width_fill > 0: pygame.draw.rect(self.screen, charge_bar_fill_color, (bar_start_x_weapon, weapon_bar_y_pos, weapon_bar_width_fill, bar_height))
        pygame.draw.rect(self.screen, WHITE, (bar_start_x_weapon, weapon_bar_y_pos, bar_segment_width_weapon, bar_height), 1)
        current_vitals_y = weapon_bar_y_pos - element_spacing

        # Active Power-up Bar
        # ... (power-up bar logic remains, using _render_text_safe for emoji icons) ...
        active_powerup_for_ui = player_obj.active_powerup_type
        if active_powerup_for_ui and (player_obj.shield_active or player_obj.speed_boost_active):
            powerup_bar_y_pos = current_vitals_y - bar_height
            powerup_icon_char = ""; powerup_bar_fill_color = WHITE; powerup_fill_percentage = 0.0
            powerup_details_config = POWERUP_TYPES.get(active_powerup_for_ui, {})

            if active_powerup_for_ui == "shield" and player_obj.shield_active:
                powerup_icon_char = "🛡️"; powerup_bar_fill_color = powerup_details_config.get("color", LIGHT_BLUE)
                remaining_time = player_obj.shield_end_time - current_time_ticks
                if player_obj.shield_duration > 0 and remaining_time > 0: powerup_fill_percentage = remaining_time / player_obj.shield_duration
            elif active_powerup_for_ui == "speed_boost" and player_obj.speed_boost_active:
                powerup_icon_char = "💨"; powerup_bar_fill_color = powerup_details_config.get("color", GREEN)
                remaining_time = player_obj.speed_boost_end_time - current_time_ticks
                if player_obj.speed_boost_duration > 0 and remaining_time > 0: powerup_fill_percentage = remaining_time / player_obj.speed_boost_duration
            
            powerup_fill_percentage = max(0, min(1, powerup_fill_percentage))
            
            if powerup_icon_char:
                powerup_icon_surf = self._render_text_safe(powerup_icon_char, ui_emoji_small_key, WHITE, fallback_size=ui_emoji_small_size)
                if powerup_icon_surf:
                    self.screen.blit(powerup_icon_surf, (vitals_x_start, powerup_bar_y_pos + (bar_height - powerup_icon_surf.get_height()) // 2))
                    bar_start_x_powerup = vitals_x_start + powerup_icon_surf.get_width() + icon_to_bar_gap
                    available_width_powerup_bar = vitals_section_width - (powerup_icon_surf.get_width() + icon_to_bar_gap)
                else: # Fallback if icon surface failed
                    bar_start_x_powerup = vitals_x_start
                    available_width_powerup_bar = vitals_section_width
                
                bar_segment_width_powerup = max(min_bar_segment_width, int(available_width_powerup_bar * bar_segment_reduction_factor))
                bar_width_fill_powerup = int(bar_segment_width_powerup * powerup_fill_percentage)
                
                pygame.draw.rect(self.screen, DARK_GREY, (bar_start_x_powerup, powerup_bar_y_pos, bar_segment_width_powerup, bar_height))
                if bar_width_fill_powerup > 0: pygame.draw.rect(self.screen, powerup_bar_fill_color, (bar_start_x_powerup, powerup_bar_y_pos, bar_width_fill_powerup, bar_height))
                pygame.draw.rect(self.screen, WHITE, (bar_start_x_powerup, powerup_bar_y_pos, bar_segment_width_powerup, bar_height), 1)
        
        # --- Right Side of HUD ---
        # ... (Collectible display logic uses self.ui_asset_surfaces for icons) ...
        # ... (and _render_text_safe for text like core count) ...
        collectibles_x_anchor = WIDTH - h_padding; current_collectibles_y_right = panel_y_start + panel_height - v_padding
        core_milestone_data = [{'threshold': 1000, 'color': LIGHT_BLUE, 'label': '1K'}, {'threshold': 5000, 'color': GREEN, 'label': '5K'}, {'threshold': 10000, 'color': ORANGE, 'label': '10K'}, {'threshold': 20000, 'color': RED, 'label': '20K'}, {'threshold': 50000, 'color': PURPLE, 'label': '50K'}, {'threshold': 100000, 'color': GOLD, 'label': 'MAX'}]
        current_cores = self.drone_system.get_player_cores(); lower_bound = 0; upper_bound = core_milestone_data[0]['threshold']
        bar_color = core_milestone_data[0]['color']; milestone_label_str = core_milestone_data[0]['label']
        for i in range(len(core_milestone_data)):
            tier_info = core_milestone_data[i]
            if current_cores < tier_info['threshold']:
                upper_bound = tier_info['threshold']; bar_color = tier_info['color']; milestone_label_str = tier_info['label']
                if i > 0: lower_bound = core_milestone_data[i-1]['threshold']
                break
        else:
            tier_info = core_milestone_data[-1]; lower_bound = tier_info['threshold']; upper_bound = lower_bound
            bar_color = tier_info['color']; milestone_label_str = tier_info['label']
        tier_range = upper_bound - lower_bound; progress_in_tier = current_cores - lower_bound; progress_percentage = 1.0
        if tier_range > 0: progress_percentage = min(1.0, progress_in_tier / tier_range)
        core_bar_width = 150; core_bar_height = bar_height; core_bar_filled_width = int(core_bar_width * progress_percentage)
        milestone_label_surf = self._render_text_safe(milestone_label_str, small_text_font_key, bar_color, fallback_size=small_text_font_size)
        core_icon_surf = self._render_text_safe("💠", ui_emoji_small_key, GOLD, fallback_size=ui_emoji_small_size)
        core_bar_y_pos = current_collectibles_y_right - core_bar_height
        label_x = collectibles_x_anchor - milestone_label_surf.get_width()
        core_bar_x_pos = label_x - core_bar_width - 5 
        icon_x = core_bar_x_pos - core_icon_surf.get_width() - icon_to_bar_gap
        self.screen.blit(core_icon_surf, (icon_x, core_bar_y_pos + (core_bar_height - core_icon_surf.get_height()) // 2))
        pygame.draw.rect(self.screen, DARK_GREY, (core_bar_x_pos, core_bar_y_pos, core_bar_width, core_bar_height))
        if core_bar_filled_width > 0: pygame.draw.rect(self.screen, bar_color, (core_bar_x_pos, core_bar_y_pos, core_bar_filled_width, core_bar_height))
        pygame.draw.rect(self.screen, WHITE, (core_bar_x_pos, core_bar_y_pos, core_bar_width, core_bar_height), 1)
        self.screen.blit(milestone_label_surf, (label_x, core_bar_y_pos + (core_bar_height - milestone_label_surf.get_height()) // 2))
        current_collectibles_y_right = core_bar_y_pos - element_spacing

        fragment_icon_h = self.ui_icon_size_fragments[1]; fragment_y_pos_hud = current_collectibles_y_right - fragment_icon_h
        fragment_display_order_ids = []
        if CORE_FRAGMENT_DETAILS:
            try: 
                sorted_frag_keys = sorted([k for k in CORE_FRAGMENT_DETAILS.keys() if k != "fragment_vault_core"])
                fragment_display_order_ids = [CORE_FRAGMENT_DETAILS[key]["id"] for key in sorted_frag_keys if "id" in CORE_FRAGMENT_DETAILS[key]]
            except Exception as e: 
                logger.error(f"UIManager: Error creating fragment display order: {e}. Using unsorted.")
                fragment_display_order_ids = [details["id"] for _, details in CORE_FRAGMENT_DETAILS.items() if details and "id" in details and details.get("id") != "vault_core"]
        displayable_fragment_ids = fragment_display_order_ids[:TOTAL_CORE_FRAGMENTS_NEEDED]
        
        # Draw animating collectibles (rings, fragments) - logic remains, surfaces are already scaled if needed
        if hasattr(self.game_controller, 'animating_rings_to_hud'):
            for ring_anim in self.game_controller.animating_rings_to_hud:
                if 'surface' in ring_anim and ring_anim['surface']:
                    anim_surf = ring_anim['surface']
                    draw_x = int(ring_anim['pos'][0] - anim_surf.get_width() / 2)
                    draw_y = int(ring_anim['pos'][1] - anim_surf.get_height() / 2)
                    self.screen.blit(anim_surf, (draw_x, draw_y))
        if hasattr(self.game_controller, 'animating_fragments_to_hud'):
            for frag_anim in self.game_controller.animating_fragments_to_hud:
                if 'surface' in frag_anim and frag_anim['surface']:
                    anim_surf = frag_anim['surface']
                    draw_x = int(frag_anim['pos'][0] - anim_surf.get_width() / 2)
                    draw_y = int(frag_anim['pos'][1] - anim_surf.get_height() / 2)
                    self.screen.blit(anim_surf, (draw_x, draw_y))

        if TOTAL_CORE_FRAGMENTS_NEEDED > 0 :
            total_fragments_width = TOTAL_CORE_FRAGMENTS_NEEDED * self.ui_icon_size_fragments[0] + max(0, TOTAL_CORE_FRAGMENTS_NEEDED - 1) * icon_spacing
            fragments_block_start_x = collectibles_x_anchor - total_fragments_width
            for i in range(TOTAL_CORE_FRAGMENTS_NEEDED):
                frag_id_for_this_slot = displayable_fragment_ids[i] if i < len(displayable_fragment_ids) else None
                icon_to_draw_surf = self.ui_asset_surfaces["core_fragment_empty_icon"]
                if frag_id_for_this_slot and frag_id_for_this_slot in self.game_controller.hud_displayed_fragments:
                    icon_to_draw_surf = self.ui_asset_surfaces["core_fragment_icons"].get(frag_id_for_this_slot, self.ui_asset_surfaces["core_fragment_empty_icon"])
                current_frag_x = fragments_block_start_x + i * (self.ui_icon_size_fragments[0] + icon_spacing)
                if icon_to_draw_surf: self.screen.blit(icon_to_draw_surf, (current_frag_x, fragment_y_pos_hud))
                if frag_id_for_this_slot and hasattr(self.game_controller, 'fragment_ui_target_positions'):
                    self.game_controller.fragment_ui_target_positions[frag_id_for_this_slot] = \
                        (current_frag_x + self.ui_icon_size_fragments[0] // 2, fragment_y_pos_hud + self.ui_icon_size_fragments[1] // 2)
            current_collectibles_y_right = fragment_y_pos_hud - element_spacing

        total_rings_this_level = self.game_controller.total_rings_per_level
        displayed_rings_count = self.game_controller.displayed_collected_rings_count
        ring_icon_surface = self.ui_asset_surfaces.get("ring_icon")
        ring_icon_empty_surface = self.ui_asset_surfaces.get("ring_icon_empty")

        if ring_icon_surface and total_rings_this_level > 0:
            ring_icon_h = self.ui_icon_size_rings[1]
            rings_y_pos_hud = current_collectibles_y_right - ring_icon_h
            total_ring_icons_width_only = total_rings_this_level * self.ui_icon_size_rings[0] + max(0, total_rings_this_level - 1) * icon_spacing
            rings_block_start_x = collectibles_x_anchor - total_ring_icons_width_only
            for i in range(total_rings_this_level):
                icon_to_draw_ring = ring_icon_surface if i < displayed_rings_count else ring_icon_empty_surface
                if icon_to_draw_ring: self.screen.blit(icon_to_draw_ring, (rings_block_start_x + i * (self.ui_icon_size_rings[0] + icon_spacing), rings_y_pos_hud))
            _next_ring_slot_index = max(0, min(displayed_rings_count, total_rings_this_level - 1))
            target_slot_x_offset = _next_ring_slot_index * (self.ui_icon_size_rings[0] + icon_spacing)
            target_slot_center_x = rings_block_start_x + target_slot_x_offset + self.ui_icon_size_rings[0] // 2
            target_slot_center_y = rings_y_pos_hud + self.ui_icon_size_rings[1] // 2
            if hasattr(self.game_controller, 'ring_ui_target_pos'): self.game_controller.ring_ui_target_pos = (target_slot_center_x, target_slot_center_y)

    def get_scaled_fragment_icon_surface(self, fragment_id): # Renamed to avoid conflict if used elsewhere
        """Returns a pre-loaded and scaled icon surface for a given fragment ID."""
        # Assumes icons are loaded by _load_ui_assets_from_manager into self.ui_asset_surfaces["core_fragment_icons"]
        icon_surface = self.ui_asset_surfaces["core_fragment_icons"].get(fragment_id)
        if icon_surface:
            return icon_surface
        
        logger.warning(f"UIManager: Scaled icon surface for fragment_id '{fragment_id}' not found in preloaded assets. Using fallback.")
        return self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", PURPLE) # Fallback if not found

    def draw_settings_menu(self):
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        title_font_key = "title_text"; title_font_size = 90
        ui_text_font_key = "ui_text"; ui_text_font_size = 28
        small_text_font_key = "small_text"; small_text_font_size = 24

        title_surf = self._render_text_safe("Settings", title_font_key, GOLD, fallback_size=title_font_size)
        # ... (rest of settings menu drawing logic, using _render_text_safe and font keys/sizes) ...
        title_bg = pygame.Surface((title_surf.get_width()+30, title_surf.get_height()+15), pygame.SRCALPHA)
        title_bg.fill((20,20,20,180)); title_bg.blit(title_surf, title_surf.get_rect(center=(title_bg.get_width()//2, title_bg.get_height()//2)))
        self.screen.blit(title_bg, title_bg.get_rect(center=(WIDTH//2, 80)))
        settings_items = ui_flow_ctrl.settings_items_data; selected_idx = ui_flow_ctrl.selected_setting_index
        item_y_start = 180
        
        # Get font for line height calculation
        ui_font_obj = self.asset_manager.get_font(ui_text_font_key, ui_text_font_size)
        if not ui_font_obj: ui_font_obj = pygame.font.Font(None, ui_text_font_size) # Fallback
        item_line_height = ui_font_obj.get_height() + 20
        
        max_items_on_screen = (HEIGHT - item_y_start - 120) // item_line_height if item_line_height > 0 else 1
        view_start_index = 0
        if settings_items and len(settings_items) > max_items_on_screen :
            view_start_index = max(0, selected_idx - max_items_on_screen // 2)
            view_start_index = min(view_start_index, len(settings_items) - max_items_on_screen)
        view_end_index = min(view_start_index + max_items_on_screen, len(settings_items) if settings_items else 0)

        for i_display, list_idx in enumerate(range(view_start_index, view_end_index)):
            if not settings_items or list_idx >= len(settings_items): continue
            item = settings_items[list_idx]; y_pos = item_y_start + i_display * item_line_height
            color = YELLOW if list_idx == selected_idx else WHITE
            label_surf = self._render_text_safe(item["label"], ui_text_font_key, color, fallback_size=ui_text_font_size)
            label_bg_rect_width = max(250, label_surf.get_width() + 20)
            label_bg_rect = pygame.Rect(WIDTH // 4 - 150, y_pos - 5, label_bg_rect_width, label_surf.get_height() + 10)
            pygame.draw.rect(self.screen, (30,30,30,160), label_bg_rect, border_radius=5)
            self.screen.blit(label_surf, (label_bg_rect.left + 10, y_pos))
            if "note" in item and list_idx == selected_idx:
                note_surf = self._render_text_safe(item["note"], small_text_font_key, LIGHT_BLUE, fallback_size=small_text_font_size)
                self.screen.blit(note_surf, note_surf.get_rect(left=label_bg_rect.right + 15, centery=label_bg_rect.centery))
            if item["type"] != "action":
                current_value = get_game_setting(item["key"]); display_value = ""
                if item["type"] == "numeric":
                    display_format = item.get("display_format", "{}"); value_to_format = current_value
                    if item.get("is_ms_to_sec"): value_to_format = current_value / 1000
                    try: display_value = display_format.format(value_to_format)
                    except (ValueError, TypeError): display_value = str(value_to_format) if not item.get("is_ms_to_sec") else f"{value_to_format:.0f}s"
                elif item["type"] == "choice": display_value = item["get_display"](current_value)
                value_surf = self._render_text_safe(display_value, ui_text_font_key, color, fallback_size=ui_text_font_size)
                value_bg_rect_width = max(100, value_surf.get_width() + 20)
                value_bg_rect = pygame.Rect(WIDTH // 2 + 150, y_pos - 5, value_bg_rect_width, value_surf.get_height() + 10)
                pygame.draw.rect(self.screen, (30,30,30,160), value_bg_rect, border_radius=5)
                self.screen.blit(value_surf, (value_bg_rect.left + 10, y_pos))
                if item["key"] in DEFAULT_SETTINGS and current_value != DEFAULT_SETTINGS[item["key"]]:
                    mod_surf = self._render_text_safe("*", small_text_font_key, RED, fallback_size=small_text_font_size)
                    self.screen.blit(mod_surf, (value_bg_rect.right + 5, y_pos))
            elif list_idx == selected_idx:
                 action_hint_surf = self._render_text_safe("<ENTER>", ui_text_font_key, YELLOW, fallback_size=ui_text_font_size)
                 action_hint_bg_rect = pygame.Rect(WIDTH // 2 + 150, y_pos - 5, action_hint_surf.get_width() + 20, action_hint_surf.get_height() + 10)
                 pygame.draw.rect(self.screen, (40,40,40,180), action_hint_bg_rect, border_radius=5)
                 self.screen.blit(action_hint_surf, (action_hint_bg_rect.left + 10, y_pos))
        instr_text = "UP/DOWN: Select | LEFT/RIGHT: Adjust | ENTER: Activate | ESC: Back"
        instr_surf = self._render_text_safe(instr_text, small_text_font_key, self.INSTRUCTION_TEXT_COLOR, fallback_size=small_text_font_size)
        instr_bg_box = pygame.Surface((instr_surf.get_width() + self.INSTRUCTION_PADDING_X, instr_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        instr_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        instr_bg_box.blit(instr_surf, instr_surf.get_rect(center=(instr_bg_box.get_width() // 2, instr_bg_box.get_height() // 2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))
        if gs.SETTINGS_MODIFIED:
            warning_text = "Leaderboard disabled: settings changed from default values!"
            warning_surf = self._render_text_safe(warning_text, small_text_font_key, RED, fallback_size=small_text_font_size)
            warning_bg_box = pygame.Surface((warning_surf.get_width() + self.INSTRUCTION_PADDING_X, warning_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
            warning_bg_box.fill(self.INSTRUCTION_BG_COLOR)
            warning_bg_box.blit(warning_surf, warning_surf.get_rect(center=(warning_bg_box.get_width() // 2, warning_bg_box.get_height() // 2)))
            self.screen.blit(warning_bg_box, warning_bg_box.get_rect(center=(WIDTH // 2, self.SECONDARY_INSTRUCTION_CENTER_Y)))

    def draw_leaderboard_overlay(self):
        # Replace self.fonts.get with self.asset_manager.get_font or self._render_text_safe
        # ...
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        title_surf = self._render_text_safe("Leaderboard", "large_text", GOLD, fallback_size=74) # Example
        title_bg_rect_width = title_surf.get_width() + 40
        title_bg_rect_height = title_surf.get_height() + 20
        title_bg_surf = pygame.Surface((title_bg_rect_width, title_bg_rect_height), pygame.SRCALPHA)
        title_bg_surf.fill((20,20,20,180)) # Title background
        title_bg_surf.blit(title_surf, title_surf.get_rect(center=(title_bg_rect_width//2, title_bg_rect_height//2)))
        self.screen.blit(title_bg_surf, title_bg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 300)))
        
        scores_to_display = ui_flow_ctrl.leaderboard_scores
        header_y = HEIGHT // 2 - 250
        score_item_y_start = HEIGHT // 2 - 200
        
        entry_font_obj = self.asset_manager.get_font("leaderboard_entry", 28) # Example size
        if not entry_font_obj: entry_font_obj = pygame.font.Font(None, 28)
        item_line_height = entry_font_obj.get_height() + 15

        if not scores_to_display:
            no_scores_surf = self._render_text_safe("No scores yet!", "medium_text", WHITE, fallback_size=48)
            # ... (bg box for no_scores_surf) ...
            no_scores_bg = pygame.Surface((no_scores_surf.get_width()+20, no_scores_surf.get_height()+10), pygame.SRCALPHA)
            no_scores_bg.fill((30,30,30,160))
            no_scores_bg.blit(no_scores_surf, no_scores_surf.get_rect(center=(no_scores_bg.get_width()//2, no_scores_bg.get_height()//2)))
            self.screen.blit(no_scores_bg, no_scores_bg.get_rect(center=(WIDTH//2, HEIGHT//2)))
        else:
            cols_x_positions = {"Rank": WIDTH//2 - 460, "Name": WIDTH//2 - 300, "Level": WIDTH//2 + 100, "Score": WIDTH//2 + 280}
            header_font_key = "leaderboard_header"; header_font_size = 32
            entry_font_key = "leaderboard_entry"; entry_font_size = 28
            
            for col_name, x_pos in cols_x_positions.items():
                header_surf = self._render_text_safe(col_name, header_font_key, WHITE, fallback_size=header_font_size)
                self.screen.blit(header_surf, (x_pos, header_y))
            
            for i, entry in enumerate(scores_to_display):
                if i >= get_game_setting("LEADERBOARD_MAX_ENTRIES"): break
                y_pos = score_item_y_start + i * item_line_height
                texts_to_draw = [
                    (f"{i+1}.", WHITE, cols_x_positions["Rank"]), 
                    (str(entry.get('name','N/A')).upper(), CYAN, cols_x_positions["Name"]), 
                    (str(entry.get('level','-')), GREEN, cols_x_positions["Level"]), 
                    (str(entry.get('score',0)), GOLD, cols_x_positions["Score"])
                ]
                for text_str, color, x_coord in texts_to_draw:
                    text_surf = self._render_text_safe(text_str, entry_font_key, color, fallback_size=entry_font_size)
                    self.screen.blit(text_surf, (x_coord, y_pos))
        
        instr_text = "ESC: Main Menu | Q: Quit Game"
        instr_surf = self._render_text_safe(instr_text, "ui_text", self.INSTRUCTION_TEXT_COLOR, fallback_size=28) 
        # ... (bg box for instr_surf) ...
        instr_bg_box = pygame.Surface((instr_surf.get_width() + self.INSTRUCTION_PADDING_X, instr_surf.get_height() + self.INSTRUCTION_PADDING_Y), pygame.SRCALPHA)
        instr_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        instr_bg_box.blit(instr_surf, instr_surf.get_rect(center=(instr_bg_box.get_width() // 2, instr_bg_box.get_height() // 2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))

    def draw_game_over_overlay(self):
        # ... similar refactoring needed ...
        go_text_surf = self._render_text_safe("GAME OVER", "large_text", RED, fallback_size=74)
        score_text_surf = self._render_text_safe(f"Final Score: {self.game_controller.score}", "medium_text", WHITE, fallback_size=48)
        self.screen.blit(go_text_surf, go_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 120)))
        self.screen.blit(score_text_surf, score_text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 30)))
        can_submit_score = not gs.SETTINGS_MODIFIED
        is_high = self.game_controller.is_current_score_a_high_score()
        prompt_y_offset = HEIGHT // 2 + 50; prompt_str = ""; prompt_color = WHITE
        ui_text_font_key = "ui_text"; ui_text_font_size = 28
        if not can_submit_score:
            no_lb_text_surf = self._render_text_safe("Leaderboard disabled (custom settings active).", ui_text_font_key, YELLOW, fallback_size=ui_text_font_size)
            self.screen.blit(no_lb_text_surf, no_lb_text_surf.get_rect(center=(WIDTH//2, prompt_y_offset)))
            prompt_y_offset += no_lb_text_surf.get_height() + 20 # Use actual height
            prompt_str = "R: Restart  M: Menu  Q: Quit"
        elif is_high:
            prompt_str = "New High Score! Press any key to enter name."
            prompt_color = GOLD
        else:
            prompt_str = "R: Restart  L: Leaderboard  M: Menu  Q: Quit"
        prompt_surf = self._render_text_safe(prompt_str, ui_text_font_key, prompt_color, fallback_size=ui_text_font_size)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, prompt_y_offset)))

    def draw_enter_name_overlay(self):
        # ... similar refactoring needed ...
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        title_surf = self._render_text_safe("New High Score!", "large_text", GOLD, fallback_size=74)
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 180)))
        score_level_text = f"Your Score: {self.game_controller.score} (Level: {self.game_controller.level})"
        score_level_surf = self._render_text_safe(score_level_text, "medium_text", WHITE, fallback_size=48)
        self.screen.blit(score_level_surf, score_level_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 90)))
        prompt_name_surf = self._render_text_safe("Enter Name (max 6 chars, A-Z):", "ui_text", WHITE, fallback_size=28)
        self.screen.blit(prompt_name_surf, prompt_name_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 20)))
        player_name_input_str = ui_flow_ctrl.player_name_input_cache
        input_box_width = 300; input_box_height = 60
        input_box_rect = pygame.Rect(WIDTH//2 - input_box_width//2, HEIGHT//2 + 30, input_box_width, input_box_height)
        pygame.draw.rect(self.screen, WHITE, input_box_rect, 2, border_radius=10)
        input_text_surf = self._render_text_safe(player_name_input_str, "input_text", WHITE, fallback_size=50)
        self.screen.blit(input_text_surf, input_text_surf.get_rect(center=input_box_rect.center))
        submit_prompt_surf = self._render_text_safe("Press ENTER to submit.", "ui_text", CYAN, fallback_size=28)
        self.screen.blit(submit_prompt_surf, submit_prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 120)))

    def draw_architect_vault_success_overlay(self):
        # ... similar refactoring needed ...
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        msg_surf = self._render_text_safe(ui_flow_ctrl.architect_vault_result_message, "large_text", ui_flow_ctrl.architect_vault_result_message_color, fallback_size=74)
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 80)))
        prompt_surf = self._render_text_safe("Press ENTER or M to Continue", "ui_text", WHITE, fallback_size=28)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 100)))

    def draw_architect_vault_failure_overlay(self):
        # ... similar refactoring needed ...
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        msg_surf = self._render_text_safe(ui_flow_ctrl.architect_vault_result_message, "large_text", ui_flow_ctrl.architect_vault_result_message_color, fallback_size=74)
        self.screen.blit(msg_surf, msg_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
        if hasattr(self.game_controller, 'architect_vault_failure_reason') and self.game_controller.architect_vault_failure_reason:
            reason_surf = self._render_text_safe(self.game_controller.architect_vault_failure_reason, "ui_text", YELLOW, fallback_size=28)
            self.screen.blit(reason_surf, reason_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))
        prompt_surf = self._render_text_safe("Press ENTER or M to Return to Menu", "ui_text", WHITE, fallback_size=28)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 80)))

    def draw_maze_defense_hud(self):
        # ... similar refactoring needed for all text rendering ...
        panel_y_start = GAME_PLAY_AREA_HEIGHT; panel_height = BOTTOM_PANEL_HEIGHT
        panel_surf = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA); panel_surf.fill((20, 25, 35, 220)) 
        pygame.draw.line(panel_surf, (80, 120, 170, 200), (0, 0), (WIDTH, 0), 2); self.screen.blit(panel_surf, (0, panel_y_start))
        h_padding = 20; v_padding = 10; element_spacing = 8; text_icon_spacing = 3; icon_spacing = 5
        current_hud_y = panel_y_start + panel_height - v_padding
        ui_text_font_key = "ui_text"; ui_text_size = 28
        ui_values_font_key = "ui_values"; ui_values_size = 30
        ui_emoji_general_key = "ui_emoji_general"; ui_emoji_size = 32
        small_text_key = "small_text"; small_text_size = 24

        cores_emoji_char = "💠"; cores_value_str = str(self.drone_system.get_player_cores())
        cores_icon_surf = self._render_text_safe(cores_emoji_char, ui_emoji_general_key, GOLD, fallback_size=ui_emoji_size)
        cores_value_text_surf = self._render_text_safe(cores_value_str, ui_values_font_key, GOLD, fallback_size=ui_values_size)
        core_display_element_height = max(cores_icon_surf.get_height(), cores_value_text_surf.get_height())
        cores_y_pos = current_hud_y - core_display_element_height; cores_x_pos = h_padding
        self.screen.blit(cores_icon_surf, (cores_x_pos, cores_y_pos + (core_display_element_height - cores_icon_surf.get_height()) // 2))
        self.screen.blit(cores_value_text_surf, (cores_x_pos + cores_icon_surf.get_width() + text_icon_spacing, cores_y_pos + (core_display_element_height - cores_value_text_surf.get_height()) // 2))
        current_hud_y = cores_y_pos - element_spacing
        
        if self.game_controller.player:
            life_icon_surf = self.ui_asset_surfaces.get("current_drone_life_icon") # Already loaded
            if life_icon_surf:
                lives_y_pos = current_hud_y - self.ui_icon_size_lives[1]
                for i in range(self.game_controller.lives):
                    self.screen.blit(life_icon_surf, (h_padding + i * (self.ui_icon_size_lives[0] + icon_spacing), lives_y_pos))
        
        center_hud_x = WIDTH // 2; combat_ctrl = self.game_controller.combat_controller
        if combat_ctrl and combat_ctrl.wave_manager:
            wave_manager = combat_ctrl.wave_manager; wave_text_str = wave_manager.get_current_wave_display()
            wave_surf = self._render_text_safe(wave_text_str, ui_text_font_key, CYAN, fallback_size=ui_text_size)
            wave_rect = wave_surf.get_rect(centerx=center_hud_x, top=panel_y_start + v_padding); self.screen.blit(wave_surf, wave_rect)
            prompt_y_start = wave_rect.bottom + 5
            if wave_manager.is_build_phase_active:
                build_time_str = wave_manager.get_build_phase_time_remaining_display()
                build_time_surf = self._render_text_safe(build_time_str, ui_text_font_key, YELLOW, fallback_size=ui_text_size)
                build_time_rect = build_time_surf.get_rect(centerx=center_hud_x, top=prompt_y_start); self.screen.blit(build_time_surf, build_time_rect)
                prompt_y_start = build_time_rect.bottom + 3
                turret_prompt_surf = self._render_text_safe("T: Place Turret", small_text_key, GREEN, fallback_size=small_text_size)
                start_wave_prompt_surf = self._render_text_safe("SPACE: Start Wave", small_text_key, GREEN, fallback_size=small_text_size)
                total_width_prompts = turret_prompt_surf.get_width() + start_wave_prompt_surf.get_width() + 20
                start_x_prompts = center_hud_x - total_width_prompts // 2
                turret_prompt_rect = turret_prompt_surf.get_rect(topleft=(start_x_prompts, prompt_y_start)); self.screen.blit(turret_prompt_surf, turret_prompt_rect)
                start_wave_prompt_rect = start_wave_prompt_surf.get_rect(left=turret_prompt_rect.right + 20, centery=turret_prompt_rect.centery)
                self.screen.blit(start_wave_prompt_surf, start_wave_prompt_rect)
            else: 
                wave_prog_surf = self._render_text_safe("Wave In Progress!", ui_text_font_key, ORANGE, fallback_size=ui_text_size)
                self.screen.blit(wave_prog_surf, wave_prog_surf.get_rect(centerx=center_hud_x, top=prompt_y_start))
        else:
            loading_defense_surf = self._render_text_safe("Loading Defense...", ui_text_font_key, GREY, fallback_size=ui_text_size)
            self.screen.blit(loading_defense_surf, loading_defense_surf.get_rect(centerx=center_hud_x, centery=panel_y_start + panel_height // 2))
        
        reactor = combat_ctrl.core_reactor if combat_ctrl else None
        if reactor and (reactor.alive or reactor.current_health > 0):
            bar_width = WIDTH * 0.35; bar_height_reactor = 22; bar_x = (WIDTH - bar_width) / 2; bar_y = 15
            health_percentage = reactor.current_health / reactor.max_health if reactor.max_health > 0 else 0
            filled_width = bar_width * health_percentage
            pygame.draw.rect(self.screen, DARK_GREY, (bar_x, bar_y, bar_width, bar_height_reactor), border_radius=3)
            fill_color = RED; 
            if health_percentage > 0.66: fill_color = GREEN
            elif health_percentage > 0.33: fill_color = YELLOW
            if filled_width > 0: pygame.draw.rect(self.screen, fill_color, (bar_x, bar_y, int(filled_width), bar_height_reactor), border_radius=3)
            pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, bar_width, bar_height_reactor), 2, border_radius=3)
            reactor_label_icon_surf = self.ui_asset_surfaces.get("reactor_icon_placeholder") # Already loaded
            if reactor_label_icon_surf: self.screen.blit(reactor_label_icon_surf, reactor_label_icon_surf.get_rect(midright=(bar_x - 10, bar_y + bar_height_reactor // 2)))
            health_text_surf = self._render_text_safe(f"{int(reactor.current_health)}/{int(reactor.max_health)}", small_text_key, WHITE, fallback_size=small_text_size)
            self.screen.blit(health_text_surf, health_text_surf.get_rect(midleft=(bar_x + bar_width + 10, bar_y + bar_height_reactor // 2)))
        
        score_x_anchor = WIDTH - h_padding; score_emoji_char = "🏆 "; score_text_str = f"Score: {self.game_controller.score}"
        score_emoji_surf = self._render_text_safe(score_emoji_char, ui_emoji_general_key, GOLD, fallback_size=ui_emoji_size)
        score_text_surf = self._render_text_safe(score_text_str, ui_text_font_key, GOLD, fallback_size=ui_text_size)
        score_total_width = score_emoji_surf.get_width() + text_icon_spacing + score_text_surf.get_width()
        score_start_x = score_x_anchor - score_total_width
        score_max_height = max(score_emoji_surf.get_height(), score_text_surf.get_height())
        score_y_pos = panel_y_start + panel_height - v_padding - score_max_height
        self.screen.blit(score_emoji_surf, (score_start_x, score_y_pos + (score_max_height - score_emoji_surf.get_height()) // 2))
        self.screen.blit(score_text_surf, (score_start_x + score_emoji_surf.get_width() + text_icon_spacing, score_y_pos + (score_max_height - score_text_surf.get_height()) // 2))

    def draw_pause_overlay(self):
        # ... similar refactoring needed ...
        overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay_surface.fill((0,0,0,150))
        self.screen.blit(overlay_surface, (0,0))
        pause_title_surf = self._render_text_safe("PAUSED", "large_text", WHITE, fallback_size=74)
        self.screen.blit(pause_title_surf, pause_title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))
        current_game_state_when_paused = self.scene_manager.get_current_state()
        pause_text_options = "P: Continue | M: Menu | Q: Quit Game"
        if current_game_state_when_paused == GAME_STATE_PLAYING: pause_text_options = "P: Continue | L: Leaderboard | M: Menu | Q: Quit Game"
        elif current_game_state_when_paused.startswith("architect_vault"): pause_text_options = "P: Continue | ESC: Main Menu (Exit Vault) | Q: Quit Game"
        elif current_game_state_when_paused == GAME_STATE_MAZE_DEFENSE: pause_text_options = "P: Resume | M: Menu (End Defense) | Q: Quit"
        options_surf = self._render_text_safe(pause_text_options, "ui_text", WHITE, fallback_size=28)
        self.screen.blit(options_surf, options_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))