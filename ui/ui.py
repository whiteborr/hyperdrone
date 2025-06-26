# ui/ui.py
from os.path import exists
from math import ceil
from random import random
from logging import getLogger, warning, error, basicConfig, INFO

from pygame import Surface, SRCALPHA, Rect
from pygame.draw import rect as draw_rect, circle, line as draw_line
from pygame.font import Font
from pygame.time import get_ticks
from pygame.transform import rotate, scale

from settings_manager import get_setting, set_setting, get_asset_path, settings_manager
from constants import (
    WHITE, BLACK, CYAN, YELLOW, GREEN, RED, DARK_GREY, GOLD, GREY, PURPLE,
    HUD_RING_ICON_AREA_X_OFFSET, HUD_RING_ICON_AREA_Y_OFFSET,
    HUD_RING_ICON_SIZE, HUD_RING_ICON_SPACING
)

from .build_menu import BuildMenu
from .leaderboard_ui import LeaderboardUI
from .settings_ui import SettingsUI

logger = getLogger(__name__)
if not getLogger().hasHandlers():
    basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')


class UIManager:
    # NEW: Add player_active_abilities_data parameter to draw_current_scene_ui
    def __init__(self, screen, asset_manager, game_controller_ref, scene_manager_ref, drone_system_ref):
        self.screen = screen
        self.asset_manager = asset_manager
        self.game_controller = game_controller_ref 
        self.scene_manager = scene_manager_ref
        self.drone_system = drone_system_ref
        
        # Cache frequently accessed settings
        self._cached_width = get_setting("display", "WIDTH", 1920)
        self._cached_height = get_setting("display", "HEIGHT", 1080)
        
        self.ui_asset_surfaces = {
            "ring_icon": None, "ring_icon_empty": None, "menu_background": None,
            "current_drone_life_icon": None, "core_fragment_icons": {},
            "core_fragment_empty_icon": None, "reactor_icon_placeholder": None,
            "ability_icon_placeholder": None # NEW: Placeholder for ability icon
        }
        self.ui_icon_size_lives = (48, 48)
        self.ui_icon_size_rings = (20, 20)
        self.ui_icon_size_fragments = (28, 28)
        self.ui_icon_size_reactor = (32, 32)
        ability_icon_size = get_setting("display", "HUD_ABILITY_ICON_SIZE", 60)
        self.ui_icon_size_ability = (ability_icon_size, ability_icon_size) # NEW

        self.codex_list_item_height = 0
        self.codex_max_visible_items_list = 0
        self.codex_max_visible_lines_content = 0

        self.BOTTOM_INSTRUCTION_CENTER_Y = self._cached_height - 50
        self.SECONDARY_INSTRUCTION_CENTER_Y = self._cached_height - 80
        self.INSTRUCTION_TEXT_COLOR = CYAN
        self.INSTRUCTION_BG_COLOR = (30, 30, 30, 150)
        self.INSTRUCTION_PADDING_X = 20
        self.INSTRUCTION_PADDING_Y = 10

        if BuildMenu:
            self.build_menu = BuildMenu(self.game_controller, self, self.asset_manager) 
        else:
            self.build_menu = None
            
        if LeaderboardUI:
            self.leaderboard_ui = LeaderboardUI()
        else:
            self.leaderboard_ui = None
            
        if SettingsUI:
            self.settings_ui = SettingsUI(self.asset_manager)
        else:
            self.settings_ui = None

        self._load_ui_assets_from_manager()
        self.update_player_life_icon_surface()
        from logging import info
        info("UIManager initialized and UI assets loaded via AssetManager.")

    def _load_ui_assets_from_manager(self):
        self.ui_asset_surfaces["ring_icon"] = self.asset_manager.get_image("ring_ui_icon", scale_to_size=self.ui_icon_size_rings)
        if not self.ui_asset_surfaces["ring_icon"]: self.ui_asset_surfaces["ring_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", GOLD)

        self.ui_asset_surfaces["ring_icon_empty"] = self.asset_manager.get_image("ring_ui_icon_empty", scale_to_size=self.ui_icon_size_rings)
        if not self.ui_asset_surfaces["ring_icon_empty"]: self.ui_asset_surfaces["ring_icon_empty"] = self._create_fallback_icon_surface(self.ui_icon_size_rings, "O", GREY)

        self.ui_asset_surfaces["menu_background"] = self.asset_manager.get_image("menu_logo_hyperdrone")
        if not self.ui_asset_surfaces["menu_background"]: warning("UIManager: Menu background 'menu_logo_hyperdrone' not found in AssetManager.")

        self.ui_asset_surfaces["core_fragment_empty_icon"] = self.asset_manager.get_image("core_fragment_empty_icon", scale_to_size=self.ui_icon_size_fragments)
        if not self.ui_asset_surfaces["core_fragment_empty_icon"]: self.ui_asset_surfaces["core_fragment_empty_icon"] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, "F", DARK_GREY, text_color=GREY)

        core_fragment_details = settings_manager.get_core_fragment_details()
        if core_fragment_details:
            for _, details in core_fragment_details.items():
                frag_id = details.get("id")
                if frag_id:
                    # Try to load using icon_filename from details first
                    loaded_icon = None
                    if "icon_filename" in details:
                        loaded_icon = self.asset_manager.get_image(details["icon_filename"], scale_to_size=self.ui_icon_size_fragments)
                    
                    # If that fails, try the old key pattern
                    if not loaded_icon:
                        asset_key = f"{frag_id}_icon"
                        loaded_icon = self.asset_manager.get_image(asset_key, scale_to_size=self.ui_icon_size_fragments)
                    
                    if loaded_icon: 
                        self.ui_asset_surfaces["core_fragment_icons"][frag_id] = loaded_icon
                    else:
                        warning(f"UIManager: Core fragment icon for ID '{frag_id}' not found. Using fallback.")
                        self.ui_asset_surfaces["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, frag_id[:1] if frag_id else "!", PURPLE)
        
        reactor_icon_asset = self.asset_manager.get_image("reactor_hud_icon_key", scale_to_size=self.ui_icon_size_reactor)
        if reactor_icon_asset: self.ui_asset_surfaces["reactor_icon_placeholder"] = reactor_icon_asset
        else: self.ui_asset_surfaces["reactor_icon_placeholder"] = self._create_fallback_icon_surface(self.ui_icon_size_reactor, "R", (50,50,200))

        # NEW: Load ability icon
        self.ui_asset_surfaces["ability_icon_placeholder"] = self.asset_manager.get_image("ability_icon_placeholder", scale_to_size=self.ui_icon_size_ability)
        if not self.ui_asset_surfaces["ability_icon_placeholder"]:
            warning("UIManager: Ability icon placeholder not found. Using fallback.")
            self.ui_asset_surfaces["ability_icon_placeholder"] = self._create_fallback_icon_surface(self.ui_icon_size_ability, "A", (100, 200, 255))

    def update_player_life_icon_surface(self):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        life_icon_asset_key = f"drone_{selected_drone_id}_hud_icon" 
        loaded_icon = self.asset_manager.get_image(life_icon_asset_key, scale_to_size=self.ui_icon_size_lives)
        
        if loaded_icon:
            # Rotate the drone icon 90 degrees counterclockwise
            rotated_icon = rotate(loaded_icon, 90)
            self.ui_asset_surfaces["current_drone_life_icon"] = rotated_icon
        else:
            warning(f"UIManager: Life icon for drone '{selected_drone_id}' (key: '{life_icon_asset_key}') not found. Using fallback.")
            self.ui_asset_surfaces["current_drone_life_icon"] = self._create_fallback_icon_surface(size=self.ui_icon_size_lives, text="L", color=CYAN)
            
    def update_weapon_icon_surface(self, weapon_mode):
        """Update the weapon icon in the HUD based on the current weapon mode"""
        selected_drone_id = self.drone_system.get_selected_drone_id()
        
        # Try to load drone-specific weapon sprite from asset manifest
        weapon_sprite_key = f"{selected_drone_id}_WEAPON_{weapon_mode}"
        loaded_icon = self.asset_manager.get_image(weapon_sprite_key, scale_to_size=(64, 64))
        
        # If not found, use the generic weapon icon
        if not loaded_icon:
            loaded_icon = self.asset_manager.get_image("weapon_upgrade_powerup_icon", scale_to_size=(64, 64))
            
        # Store the icon for use in the HUD
        if loaded_icon:
            self.ui_asset_surfaces["current_weapon_icon"] = loaded_icon
        else:
            warning(f"UIManager: Weapon icon for drone '{selected_drone_id}' mode '{weapon_mode}' not found. Using fallback.")
            self.ui_asset_surfaces["current_weapon_icon"] = self._create_fallback_icon_surface(size=(64, 64), text="W", color=CYAN)

    def _create_fallback_icon_surface(self, size=(30,30), text="?", color=GREY, text_color=WHITE, font_key="ui_text"):
        surface = Surface(size, SRCALPHA)
        surface.fill(color)
        draw_rect(surface, WHITE, surface.get_rect(), 1)
        font_to_use = self.asset_manager.get_font(font_key, max(10, size[1]-4)) or Font(None, max(10, size[1]-4))
        if text and font_to_use:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                surface.blit(text_surf, text_surf.get_rect(center=(size[0] // 2, size[1] // 2)))
            except Exception as e: error(f"UIManager: Error rendering fallback icon text '{text}' with font key '{font_key}': {e}")
        return surface

    def _render_text_safe(self, text, font_key, color, fallback_size=24):
        font = self.asset_manager.get_font(font_key, fallback_size)
        if not font: font = Font(None, fallback_size)
        try: return font.render(str(text), True, color)
        except Exception as e:
            error(f"UIManager: Error rendering text '{text}' with font key '{font_key}': {e}")
            return Font(None, fallback_size).render("ERR", True, RED)

    def _wrap_text(self, text, font_key_for_size_calc, size_for_font, max_width):
        font = self.asset_manager.get_font(font_key_for_size_calc, size_for_font) or Font(None, size_for_font)
        return self._wrap_text_with_font_obj(text, font, max_width)

    def _wrap_text_with_font_obj(self, text, font_object, max_width):
        if not font_object: return [text]
        words, lines, current_line = text.split(' '), [], ""
        for word in words:
            if font_object.size(current_line + word + " ")[0] <= max_width: current_line += word + " "
            else:
                if current_line: lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip()); return lines

    def _draw_star_background(self):
        """Helper function to draw the animated starfield background."""
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        if ui_flow_ctrl and hasattr(ui_flow_ctrl, 'menu_stars') and ui_flow_ctrl.menu_stars:
            for star_params in ui_flow_ctrl.menu_stars:
                circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

    def draw_current_scene_ui(self, player_active_abilities_data=None):
        if not hasattr(self, 'state_manager') or self.state_manager is None:
            return
            
        current_state = self.state_manager.get_current_state_id() if self.state_manager else None
        
        is_menu_like_state = current_state in [
            "MainMenuState", "DroneSelectState", "SettingsState",
            "LeaderboardState", "CodexState",
            "ArchitectVaultSuccessState", "ArchitectVaultFailureState",
            "GameOverState", "EnterNameState", "StoryMapState", "NarrativeState"
        ]
        
        if is_menu_like_state: 
            self.screen.fill(BLACK)

        state_draw_map = {
            "MainMenuState": self.draw_main_menu,
            "DroneSelectState": self.draw_drone_select_menu,
            "SettingsState": self.draw_settings_menu,
            "LeaderboardState": self.draw_leaderboard_ui,
            "CodexState": self.draw_codex_screen,
            "GameOverState": self.draw_game_over_overlay,
            "EnterNameState": self.draw_enter_name_overlay,
            "GameIntroScrollState": self.draw_game_intro_scroll,
            "StoryMapState": self.draw_story_map,
            "ArchitectVaultSuccessState": self.draw_architect_vault_success_overlay,
            "ArchitectVaultFailureState": self.draw_architect_vault_failure_overlay,
            "NarrativeState": self.draw_narrative_state
        }

        if current_state in state_draw_map:
            state_draw_map[current_state]()
        
        elif current_state and current_state.startswith("ArchitectVault"):
            self.draw_architect_vault_hud_elements()
            if self.game_controller.paused: self.draw_pause_overlay()
        
        elif current_state in ["PlayingState", "BonusLevelPlayingState", "EarthCoreState", "FireCoreState", "AirCoreState", "WaterCoreState", "OrichalcCoreState"]:
            self.draw_gameplay_hud(player_active_abilities_data)
            if self.game_controller.paused: self.draw_pause_overlay()
        
        elif current_state == "MazeDefenseState": 
            self.draw_maze_defense_hud()
            if self.game_controller.paused: self.draw_pause_overlay()
            if self.build_menu and self.build_menu.is_active and \
               hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase:
                self.build_menu.draw(self.screen)
        
        elif current_state == "RingPuzzleState":
            if not (self.game_controller.puzzle_controller and self.game_controller.puzzle_controller.ring_puzzle_active_flag):
                self.screen.fill(DARK_GREY)
                fallback_surf = self._render_text_safe("Loading Puzzle...", "medium_text", WHITE, fallback_size=48)
                width = get_setting("display", "WIDTH", 1920)
                height = get_setting("display", "HEIGHT", 1080)
                self.screen.blit(fallback_surf, fallback_surf.get_rect(center=(width // 2, height // 2)))

        if hasattr(self.game_controller, 'story_message_active') and self.game_controller.story_message_active and \
           hasattr(self.game_controller, 'story_message') and self.game_controller.story_message:
            if current_state != "game_intro_scroll":
                self.draw_story_message_overlay(self.game_controller.story_message)
    
    def draw_story_map(self):
        """Draw a story map screen with chapter progression"""
        self._draw_star_background()
        width, height = self._cached_width, self._cached_height
        
        # Try to get background from asset manager, fallback to solid color
        bg_path = get_asset_path('images', 'STORY_MAP_BACKGROUND')
        if bg_path:
            bg = self.asset_manager.get_image(bg_path)
            if bg:
                scaled_bg = scale(bg, (width, height))
                self.screen.blit(scaled_bg, (0, 0))
            else:
                self.screen.fill((10, 20, 40))
        else:
            self.screen.fill((10, 20, 40))
        
        title_surf = self._render_text_safe("Story Map", "large_text", GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 100)))
        
        # Draw chapter map line
        self._draw_chapter_map_line(width, height)
        
        # Draw current chapter details below the map (only if not showing overlays)
        current_state = self.state_manager.get_current_state() if self.state_manager else None
        show_chapter_details = True
        if (hasattr(current_state, 'showing_completion_summary') and current_state.showing_completion_summary) or \
           (hasattr(current_state, 'animating_to_next_chapter') and current_state.animating_to_next_chapter):
            show_chapter_details = False
            
        if show_chapter_details:
            current_chapter = None
            if hasattr(self.game_controller, 'story_manager') and self.game_controller.story_manager:
                current_chapter = self.game_controller.story_manager.get_current_chapter()
            
            if current_chapter:
                chapter_title_surf = self._render_text_safe(current_chapter.title, "ui_text", CYAN, fallback_size=32)
                self.screen.blit(chapter_title_surf, chapter_title_surf.get_rect(center=(width // 2, 450)))
                
                desc_font = Font(None, 24)
                wrapped_desc = self._wrap_text_with_font_obj(current_chapter.description, desc_font, width - 200)
                for i, line in enumerate(wrapped_desc):
                    desc_surf = desc_font.render(line, True, WHITE)
                    self.screen.blit(desc_surf, desc_surf.get_rect(center=(width // 2, 490 + i * 30)))
                
                obj_y = 490 + len(wrapped_desc) * 30 + 50
                obj_font = Font(None, 24)
                
                for obj in current_chapter.objectives:
                    obj_color = GREEN if obj.is_complete else WHITE
                    obj_text = f"• {obj.description}"
                    obj_surf = obj_font.render(obj_text, True, obj_color)
                    self.screen.blit(obj_surf, obj_surf.get_rect(center=(width // 2, obj_y)))
                    obj_y += 30
        
        # Show instruction if not in overlay mode OR if animation is complete
        current_state = self.state_manager.get_current_state() if self.state_manager else None
        animation_complete = (hasattr(current_state, 'animating_to_next_chapter') and 
                            not current_state.animating_to_next_chapter and 
                            hasattr(current_state, 'animation_timer'))
        
        if show_chapter_details or animation_complete:
            instruction_surf = self._render_text_safe("Press SPACE or ENTER to continue", "ui_text", CYAN, fallback_size=24)
            self.screen.blit(instruction_surf, instruction_surf.get_rect(center=(width // 2, height - 50)))
    
    def _draw_chapter_map_line(self, width, height):
        """Draw the chapter progression map with icons"""
        # Load chapter icons
        chapter_unlocked_icon = self.asset_manager.get_image("CHAPTER_ICON_UNLOCKED", scale_to_size=(64, 64))
        chapter_locked_icon = self.asset_manager.get_image("CHAPTER_ICON_LOCKED", scale_to_size=(64, 64))
        player_cursor_icon = self.asset_manager.get_image("PLAYER_MAP_CURSOR", scale_to_size=(32, 32))
        
        # Fallback icons if assets not found
        if not chapter_unlocked_icon:
            chapter_unlocked_icon = self._create_fallback_icon_surface((64, 64), "✓", GREEN)
        if not chapter_locked_icon:
            chapter_locked_icon = self._create_fallback_icon_surface((64, 64), "✗", GREY)
        if not player_cursor_icon:
            player_cursor_icon = self._create_fallback_icon_surface((32, 32), "►", GOLD)
        
        # Chapter positions along a horizontal line
        map_y = 250
        chapter_spacing = 150
        start_x = (width - (4 * chapter_spacing)) // 2  # Center 5 chapters
        
        # Get current chapter info
        current_chapter_index = -1
        story_manager = None
        if hasattr(self.game_controller, 'story_manager') and self.game_controller.story_manager:
            story_manager = self.game_controller.story_manager
            current_chapter_index = story_manager.current_chapter_index
        
        # Draw connecting line
        line_start_x = start_x + 32  # Center of first icon
        line_end_x = start_x + (4 * chapter_spacing) + 32  # Center of last icon
        draw_line(self.screen, WHITE, (line_start_x, map_y + 32), (line_end_x, map_y + 32), 3)
        
        # Draw chapters 1-5
        for i in range(5):
            chapter_x = start_x + (i * chapter_spacing)
            
            # Determine if chapter is unlocked (current or previous chapters)
            is_unlocked = i <= current_chapter_index
            
            # Choose appropriate icon
            icon = chapter_unlocked_icon if is_unlocked else chapter_locked_icon
            
            # Draw chapter icon
            self.screen.blit(icon, (chapter_x, map_y))
            
            # Draw chapter number
            chapter_num_surf = self._render_text_safe(f"{i + 1}", "ui_text", WHITE, fallback_size=24)
            num_rect = chapter_num_surf.get_rect(center=(chapter_x + 32, map_y + 80))
            self.screen.blit(chapter_num_surf, num_rect)
        
        # Draw player cursor - check if we're in animation mode
        current_state = self.state_manager.get_current_state() if self.state_manager else None
        if (hasattr(current_state, 'animating_to_next_chapter') and 
            current_state.animating_to_next_chapter and 
            hasattr(current_state, 'current_animation_pos')):
            # Use animated position
            cursor_pos = current_state.current_animation_pos
            self.screen.blit(player_cursor_icon, (int(cursor_pos.x), int(cursor_pos.y)))
        elif current_chapter_index >= 0 and current_chapter_index < 5:
            # Use static position for current chapter
            # If we just completed a chapter, show cursor at previous position initially
            display_index = current_chapter_index
            if (hasattr(current_state, 'showing_completion_summary') and 
                current_state.showing_completion_summary):
                display_index = max(0, current_chapter_index - 1)
            
            cursor_x = start_x + (display_index * chapter_spacing) + 16
            cursor_y = map_y - 40
            self.screen.blit(player_cursor_icon, (cursor_x, cursor_y))

    def draw_architect_vault_hud_elements(self):
        title_surf = self._render_text_safe("Architect's Vault", "large_text", GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(self._cached_width // 2, 50)))

    def draw_game_intro_scroll(self):
        self._draw_star_background()
        ui_flow = self.game_controller.ui_flow_controller
        if not ui_flow.intro_screens_data or ui_flow.current_intro_screen_index >= len(ui_flow.intro_screens_data):
            return

        current_screen_data = ui_flow.intro_screens_data[ui_flow.current_intro_screen_index]
        image_key = current_screen_data.get("image_path_key")
        text = current_screen_data.get("text", "")
        
        screen_width, screen_height = self._cached_width, self._cached_height

        if image_key:
            bg_image = self.asset_manager.get_image(image_key)
            if bg_image:
                bg_surf = scale(bg_image, (screen_width, screen_height))
                self.screen.blit(bg_surf, (0, 0))

        lines = text.split('\n')
        font = self.asset_manager.get_font("medium_text", 36)
        start_y = screen_height - (len(lines) * 40) - 100

        for i, line in enumerate(lines):
            line_surf = font.render(line, True, WHITE)
            self.screen.blit(line_surf, line_surf.get_rect(center=(screen_width / 2, start_y + i * 40)))
            
        prompt_surf = self._render_text_safe("Press SPACE to continue...", "ui_text", GOLD, fallback_size=28)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(screen_width / 2, screen_height - 50)))

    def draw_story_message_overlay(self, message):
        font = self.asset_manager.get_font("ui_text", 28) or Font(None, 28)
        text_surf = font.render(message, True, CYAN)
        width, height = self._cached_width, self._cached_height
        bg_rect = text_surf.get_rect(center=(width // 2, height - 150))
        bg_rect.inflate_ip(40, 20)
        
        bg_surface = Surface(bg_rect.size, SRCALPHA)
        bg_surface.fill((30, 30, 30, 180))
        self.screen.blit(bg_surface, bg_rect.topleft)
        draw_rect(self.screen, CYAN, bg_rect, 1)
        self.screen.blit(text_surf, text_surf.get_rect(center=bg_rect.center))

    def draw_codex_screen(self):
        self.screen.fill(BLACK)
        if hasattr(self.game_controller, 'menu_stars') and self.game_controller.menu_stars:
            for star_params in self.game_controller.menu_stars:
                circle(self.screen, (50,50,50), (int(star_params[0]), int(star_params[1])), star_params[3])
        title_surf = self._render_text_safe("Lore Codex", "large_text", GOLD)
        title_rect = title_surf.get_rect(center=(self._cached_width // 2, 60)); self.screen.blit(title_surf, title_rect)
        current_view = getattr(self.game_controller, 'codex_current_view', "categories")
        padding = 50; list_panel_width = self._cached_width // 3 - padding * 1.5; list_panel_x = padding
        content_panel_x = list_panel_x + list_panel_width + padding / 2
        content_panel_width = self._cached_width - content_panel_x - padding
        top_y_start = title_rect.bottom + 30; bottom_y_end = self._cached_height - 80
        category_font = self.asset_manager.get_font("ui_text", 32) or Font(None, 32)
        entry_font = self.asset_manager.get_font("ui_text", 28) or Font(None, 28)
        content_font = self.asset_manager.get_font("ui_text", 24) or Font(None, 24)
        current_list_item_height_val = self.codex_list_item_height if self.codex_list_item_height > 0 else entry_font.get_height() + 15
        content_line_height = content_font.get_linesize()
        if self.codex_list_item_height == 0 and current_list_item_height_val > 0 :
             self.codex_list_item_height = current_list_item_height_val
             if self.codex_list_item_height > 0: self.codex_max_visible_items_list = (bottom_y_end - top_y_start) // self.codex_list_item_height
             else: self.codex_max_visible_items_list = 1
        available_height_for_content_text_calc = bottom_y_end - (top_y_start + category_font.get_height() + 20)
        if self.codex_max_visible_lines_content == 0 and content_line_height > 0:
             self.codex_max_visible_lines_content = available_height_for_content_text_calc // content_line_height if content_line_height > 0 else 1
        nav_instr = ""; list_panel_rect = Rect(list_panel_x, top_y_start, list_panel_width, bottom_y_end - top_y_start)
        current_list_y = top_y_start + 20 
        if current_view == "categories":
            categories = getattr(self.game_controller, 'codex_categories_list', [])
            selected_category_idx = getattr(self.game_controller, 'codex_selected_category_index', 0)
            if not categories:
                no_lore_surf = self._render_text_safe("No lore unlocked.", "medium_text", WHITE)
                self.screen.blit(no_lore_surf, no_lore_surf.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))
            else:
                max_visible = self.codex_max_visible_items_list if self.codex_max_visible_items_list > 0 else 1
                start_idx = max(0, selected_category_idx - max_visible // 2); start_idx = min(start_idx, max(0, len(categories) - max_visible))
                end_idx = min(len(categories), start_idx + max_visible)
                for i_display, i_actual in enumerate(range(start_idx, end_idx)):
                    category_name = categories[i_actual]; y_pos = current_list_y + i_display * self.codex_list_item_height
                    color = YELLOW if i_actual == selected_category_idx else WHITE
                    cat_surf = self._render_text_safe(category_name, "ui_text", color)
                    self.screen.blit(cat_surf, (list_panel_x + 10, y_pos))
            nav_instr = "UP/DOWN: Select | ENTER: View Entries | ESC: Main Menu"
        elif current_view == "entries":
            category_name = getattr(self.game_controller, 'codex_current_category_name', "Entries")
            entries = getattr(self.game_controller, 'codex_entries_in_category_list', [])
            selected_entry_idx = getattr(self.game_controller, 'codex_selected_entry_index_in_category', 0)
            cat_title_surf = self._render_text_safe(f"{category_name}", "ui_text", GOLD)
            self.screen.blit(cat_title_surf, (list_panel_x + 10, top_y_start))
            current_list_y = top_y_start + cat_title_surf.get_height() + 15
            if not entries:
                no_entries_surf = self._render_text_safe("No entries here.", "ui_text", GREY)
                self.screen.blit(no_entries_surf, (list_panel_x + 20, current_list_y))
            else:
                max_visible = self.codex_max_visible_items_list if self.codex_max_visible_items_list > 0 else 1
                start_idx = max(0, selected_entry_idx - max_visible // 2); start_idx = min(start_idx, max(0, len(entries) - max_visible))
                end_idx = min(len(entries), start_idx + max_visible)
                for i_display, i_actual in enumerate(range(start_idx, end_idx)):
                    entry_data = entries[i_actual]; y_pos = current_list_y + i_display * self.codex_list_item_height
                    color = YELLOW if i_actual == selected_entry_idx else WHITE
                    entry_title_surf = self._render_text_safe(entry_data.get("title", "Untitled"), "ui_text", color)
                    self.screen.blit(entry_title_surf, (list_panel_x + 20, y_pos))
            nav_instr = "UP/DOWN: Select | ENTER: Read | ESC: Back to Categories"
        elif current_view == "content":
            selected_entry_id = getattr(self.game_controller, 'codex_selected_entry_id', None)
            entry_data = self.drone_system.get_lore_entry_details(selected_entry_id) if selected_entry_id else None
            category_name_reminder = getattr(self.game_controller, 'codex_current_category_name', "")
            is_drone_entry = entry_data.get("category") == "Drones" if entry_data else False
            is_race_entry = entry_data.get("category") == "Alien Races" if entry_data else False
            image_path = entry_data.get("image") if entry_data else None
            current_image_y_pos = top_y_start + 20
            if category_name_reminder:
                cat_reminder_surf = self._render_text_safe(f"{category_name_reminder}", "ui_text", DARK_GREY)
                self.screen.blit(cat_reminder_surf, (list_panel_x +10 , top_y_start )); current_image_y_pos = top_y_start + cat_reminder_surf.get_height() + 20
            if entry_data:
                content_title_surf = self._render_text_safe(entry_data.get("title", "Untitled"), "ui_text", GOLD)
                self.screen.blit(content_title_surf, (content_panel_x, top_y_start))
                content_text_render_y = top_y_start + content_title_surf.get_height() + 20; text_area_width = content_panel_width - 20
                if is_drone_entry and image_path:
                    if not hasattr(self, 'codex_image_cache'):
                        self.codex_image_cache = {}
                    if image_path not in self.codex_image_cache:
                        try: 
                            from pygame.image import load as image_load
                            self.codex_image_cache[image_path] = image_load(image_path).convert_alpha()
                        except Exception as e: 
                            print(f"UIManager: Error loading Codex image '{image_path}': {e}")
                            self.codex_image_cache[image_path] = None
                    cached_image = self.codex_image_cache.get(image_path)
                    if cached_image:
                        img_max_width = list_panel_width - 20; img_max_height = self._cached_height * 0.3
                        original_w, original_h = cached_image.get_size(); aspect_ratio = original_h / original_w if original_w > 0 else 1
                        scaled_w = img_max_width; scaled_h = int(scaled_w * aspect_ratio)
                        if scaled_h > img_max_height: scaled_h = int(img_max_height); scaled_w = int(scaled_h / aspect_ratio if aspect_ratio > 0 else img_max_width)
                        try:
                            from pygame.transform import smoothscale
                            display_image = smoothscale(cached_image, (scaled_w, scaled_h))
                            self.screen.blit(display_image, (list_panel_x + (list_panel_width - scaled_w) // 2, current_image_y_pos))
                        except Exception as e: print(f"UIManager: Error scaling Drone Codex image '{image_path}': {e}")
                content_text = entry_data.get("content", "No content available."); scroll_offset_lines = getattr(self.game_controller, 'codex_content_scroll_offset', 0)
                wrapped_lines = self._wrap_text(content_text, content_font, text_area_width)
                if hasattr(self.game_controller, 'codex_current_entry_total_lines'): self.game_controller.codex_current_entry_total_lines = len(wrapped_lines)
                text_content_area_available_height = bottom_y_end - content_text_render_y - 10; race_image_to_draw_below_text = None; scaled_race_img_h = 0
                if is_race_entry and image_path:
                    if not hasattr(self, 'codex_image_cache'):
                        self.codex_image_cache = {}
                    if image_path not in self.codex_image_cache:
                        try: 
                            from pygame.image import load as image_load
                            self.codex_image_cache[image_path] = image_load(image_path).convert_alpha()
                        except Exception as e: 
                            print(f"UIManager: Error loading Race Codex image '{image_path}': {e}")
                            self.codex_image_cache[image_path] = None
                    cached_race_image = self.codex_image_cache.get(image_path)
                    if cached_race_image:
                        img_max_width = content_panel_width * 0.6; img_max_height_race = self._cached_height * 0.25
                        original_w, original_h = cached_race_image.get_size(); aspect_ratio = original_h / original_w if original_w > 0 else 1
                        scaled_w = img_max_width; scaled_h = int(scaled_w * aspect_ratio)
                        if scaled_h > img_max_height_race: scaled_h = int(img_max_height_race); scaled_w = int(scaled_h / aspect_ratio if aspect_ratio > 0 else img_max_width)
                        if scaled_w > 0 and scaled_h > 0:
                            try: 
                                from pygame.transform import smoothscale
                                race_image_to_draw_below_text = smoothscale(cached_race_image, (scaled_w, scaled_h))
                                scaled_race_img_h = scaled_h
                                text_content_area_available_height -= (scaled_race_img_h + 20)
                            except Exception as e: print(f"UIManager: Error scaling Race Codex image '{image_path}': {e}")
                max_lines = text_content_area_available_height // content_line_height if content_line_height > 0 else 0
                if max_lines <= 0 and wrapped_lines: max_lines = 1
                lines_drawn_y_end = content_text_render_y
                for i in range(max_lines):
                    line_idx = scroll_offset_lines + i
                    if 0 <= line_idx < len(wrapped_lines):
                        line_surf = content_font.render(wrapped_lines[line_idx], True, WHITE)
                        self.screen.blit(line_surf, (content_panel_x + 10, content_text_render_y + i * content_line_height))
                        lines_drawn_y_end = content_text_render_y + (i + 1) * content_line_height
                if race_image_to_draw_below_text:
                    race_img_y_pos = lines_drawn_y_end + 20
                    if race_img_y_pos + scaled_race_img_h < bottom_y_end:
                        self.screen.blit(race_image_to_draw_below_text, (content_panel_x + (text_area_width - race_image_to_draw_below_text.get_width()) // 2, race_img_y_pos))
                if len(wrapped_lines) > max_lines:
                    if scroll_offset_lines > 0:
                        scroll_up_surf = self._render_text_safe("▲ Up", "small_text", YELLOW)
                        self.screen.blit(scroll_up_surf, (content_panel_x + text_area_width - scroll_up_surf.get_width(), content_text_render_y - 25))
                    if scroll_offset_lines + max_lines < len(wrapped_lines):
                        scroll_down_surf = self._render_text_safe("▼ Down", "small_text", YELLOW); scroll_down_y_pos = lines_drawn_y_end + 5
                        if race_image_to_draw_below_text and (race_img_y_pos + scaled_race_img_h + scroll_down_surf.get_height() > bottom_y_end -5): scroll_down_y_pos = lines_drawn_y_end + 5
                        elif not race_image_to_draw_below_text: scroll_down_y_pos = bottom_y_end - scroll_down_surf.get_height() -5
                        self.screen.blit(scroll_down_surf, (content_panel_x + text_area_width - scroll_down_surf.get_width(), scroll_down_y_pos ))
                nav_instr = "UP/DOWN: Scroll | ESC: Back to Entries List"
            else:
                no_content_surf = self._render_text_safe("Error: Could not load entry content.", "medium_text", RED)
                self.screen.blit(no_content_surf, no_content_surf.get_rect(center=(content_panel_x + content_panel_width // 2, self._cached_height // 2)))
                nav_instr = "ESC: Back"
        else: nav_instr = "ESC: Main Menu"
        nav_surf = self._render_text_safe(nav_instr, "small_text", self.INSTRUCTION_TEXT_COLOR)
        nav_bg_box = Surface((nav_surf.get_width() + self.INSTRUCTION_PADDING_X, nav_surf.get_height() + self.INSTRUCTION_PADDING_Y), SRCALPHA)
        nav_bg_box.fill(self.INSTRUCTION_BG_COLOR); nav_bg_box.blit(nav_surf, nav_surf.get_rect(center=(nav_bg_box.get_width() // 2, nav_bg_box.get_height() // 2)))
        self.screen.blit(nav_bg_box, nav_bg_box.get_rect(center=(self._cached_width // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))

    def draw_main_menu(self):
        # Draw the main menu logo first.
        if self.ui_asset_surfaces["menu_background"]:
            logo_surf = self.ui_asset_surfaces["menu_background"]
            scaled_bg_surf = scale(logo_surf, (self._cached_width, self._cached_height))
            self.screen.blit(scaled_bg_surf, (0, 0))

        # Then draw the stars on TOP of the logo.
        self._draw_star_background()

        # Draw the menu options last, on top of everything.
        ui_flow_ctrl = self.game_controller.ui_flow_controller
        options, selected_index = ui_flow_ctrl.menu_options, ui_flow_ctrl.selected_menu_option
        start_y, option_height = self._cached_height * 0.55, 60
        font_menu = self.asset_manager.get_font("large_text", 48) or Font(None, 48)

        for i, option_text in enumerate(options):
            color = GOLD if i == selected_index else WHITE
            text_surf = font_menu.render(option_text, True, color)
            text_rect = text_surf.get_rect(center=(self._cached_width // 2, start_y + i * option_height))
            self.screen.blit(text_surf, text_rect)

    def draw_drone_select_menu(self):
        from pygame import Rect
        from pygame.draw import rect as draw_rect
        
        self._draw_star_background()
        title_surf = self._render_text_safe("Select Drone", "large_text", GOLD, fallback_size=48)
        title_rect = title_surf.get_rect(center=(self._cached_width // 2, 70))
        self.screen.blit(title_surf, title_rect)
        
        ui_flow = self.game_controller.ui_flow_controller
        drone_options_ids = getattr(ui_flow, 'drone_select_options', [])
        selected_preview_idx = getattr(ui_flow, 'selected_drone_preview_index', 0)
        
        if not drone_options_ids:
            no_drones_surf = self._render_text_safe("NO DRONES AVAILABLE", "large_text", RED, fallback_size=48)
            self.screen.blit(no_drones_surf, no_drones_surf.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))
            return
        
        current_drone_id = drone_options_ids[selected_preview_idx]
        drone_config = self.drone_system.get_drone_config(current_drone_id)
        drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False)
        is_unlocked = self.drone_system.is_drone_unlocked(current_drone_id)
        is_currently_equipped = (current_drone_id == self.drone_system.get_selected_drone_id())
        
        # Get drone image
        drone_image_surf = None
        if hasattr(self.game_controller, 'drone_main_display_cache'):
            drone_image_surf = self.game_controller.drone_main_display_cache.get(current_drone_id)
        
        if not drone_image_surf:
            sprite_asset_key = drone_config.get("sprite_path", "").replace("assets/", "")
            drone_image_surf = self.asset_manager.get_image(sprite_asset_key, scale_to_size=(200, 200))
        
        img_width = drone_image_surf.get_width() if drone_image_surf else 200
        img_height = drone_image_surf.get_height() if drone_image_surf else 200
        
        # Drone name
        name_text = drone_config.get("name", "N/A")
        name_surf_temp = self._render_text_safe(name_text, "medium_text", WHITE, fallback_size=36)
        name_height = name_surf_temp.get_height()
        
        # Stats
        hp_stat = drone_stats.get("hp")
        speed_stat = drone_stats.get("speed")
        turn_speed_stat = drone_stats.get("turn_speed")
        fire_rate_mult = drone_stats.get("fire_rate_multiplier", 1.0)
        special_ability_key = drone_stats.get("special_ability")
        
        hp_display = str(hp_stat) if hp_stat is not None else "N/A"
        speed_display = f"{speed_stat:.1f}" if isinstance(speed_stat, (int, float)) else "N/A"
        turn_speed_display = f"{turn_speed_stat:.1f}" if isinstance(turn_speed_stat, (int, float)) else "N/A"
        
        fire_rate_text = f"{fire_rate_mult:.2f}x mult"
        if fire_rate_mult == 1.0:
            fire_rate_text = "Normal"
        elif fire_rate_mult < 1.0:
            fire_rate_text += " (Faster)"
        else:
            fire_rate_text += " (Slower)"
        
        special_ability_name = "None"
        if special_ability_key == "phantom_cloak":
            special_ability_name = "Phantom Cloak"
        elif special_ability_key == "omega_boost":
            special_ability_name = "Omega Boost"
        elif special_ability_key == "energy_shield_pulse":
            special_ability_name = "Shield Pulse"
        
        stats_data_tuples = [
            ("HP:", hp_display),
            ("Speed:", speed_display),
            ("Turn Speed:", turn_speed_display),
            ("Fire Rate:", fire_rate_text),
            ("Special:", special_ability_name)
        ]
        
        # Create stats surfaces
        stats_content_surfaces = []
        max_stat_label_w = 0
        max_stat_value_w = 0
        stat_line_h = 30
        
        for label_str, value_str in stats_data_tuples:
            label_color = (173, 216, 230) if is_unlocked else GREY  # LIGHT_BLUE equivalent
            value_color = WHITE if is_unlocked else GREY
            label_s = self._render_text_safe(label_str, "ui_text", label_color, fallback_size=24)
            value_s = self._render_text_safe(value_str, "ui_text", value_color, fallback_size=24)
            stats_content_surfaces.append((label_s, value_s))
            max_stat_label_w = max(max_stat_label_w, label_s.get_width())
            max_stat_value_w = max(max_stat_value_w, value_s.get_width())
        
        # Stats box dimensions
        stats_box_padding = 15
        stats_box_visual_width = max_stat_label_w + max_stat_value_w + 3 * stats_box_padding
        stats_box_visual_height = (len(stats_content_surfaces) * stat_line_h) + 2 * stats_box_padding
        
        # Description
        desc_text = drone_config.get("description", "")
        desc_color_final = (200, 200, 200) if is_unlocked else (100, 100, 100)
        desc_max_width_for_card = self._cached_width * 0.45
        desc_lines_surfs = []
        
        words = desc_text.split(' ')
        current_line_text_desc = ""
        desc_font = self.asset_manager.get_font("ui_text", 24) or Font(None, 24)
        
        for word in words:
            test_line = current_line_text_desc + word + " "
            if desc_font.size(test_line)[0] < desc_max_width_for_card:
                current_line_text_desc = test_line
            else:
                if current_line_text_desc:
                    desc_lines_surfs.append(self._render_text_safe(current_line_text_desc.strip(), "ui_text", desc_color_final, fallback_size=24))
                current_line_text_desc = word + " "
        
        if current_line_text_desc:
            desc_lines_surfs.append(self._render_text_safe(current_line_text_desc.strip(), "ui_text", desc_color_final, fallback_size=24))
        
        total_desc_height = sum(s.get_height() for s in desc_lines_surfs) + (len(desc_lines_surfs) - 1) * 3 if desc_lines_surfs else 0
        
        # Unlock text
        unlock_text_str = ""
        unlock_text_color = WHITE
        unlock_condition = drone_config.get("unlock_condition", {})
        
        if not is_unlocked:
            condition_text_str = unlock_condition.get("description", "Locked")
            unlock_cost_val = unlock_condition.get("value")
            type_is_cores_unlock = unlock_condition.get("type") == "cores"
            unlock_text_str = condition_text_str
            
            if type_is_cores_unlock and unlock_cost_val is not None:
                can_afford = self.drone_system.get_cores() >= unlock_cost_val
                unlock_text_str = f"Unlock: {unlock_cost_val} 💠 "
                unlock_text_str += "(ENTER)" if can_afford else "(Not Enough Cores)"
                unlock_text_color = GREEN if can_afford else YELLOW
            else:
                unlock_text_color = YELLOW
        elif is_currently_equipped:
            unlock_text_str = "EQUIPPED"
            unlock_text_color = GREEN
        else:
            unlock_text_str = "Press ENTER to Select"
            unlock_text_color = CYAN
        
        unlock_info_surf = self._render_text_safe(unlock_text_str, "ui_text", unlock_text_color, fallback_size=28)
        unlock_info_height = unlock_info_surf.get_height() if unlock_info_surf else 0
        
        # Card layout
        spacing_between_elements = 15
        padding_inside_card = 25
        
        card_content_total_h = (img_height + spacing_between_elements + name_height + spacing_between_elements + 
                               stats_box_visual_height + spacing_between_elements + total_desc_height + 
                               spacing_between_elements + unlock_info_height)
        
        max_content_width_for_card = max(
            img_width,
            name_surf_temp.get_width(),
            stats_box_visual_width,
            max(s.get_width() for s in desc_lines_surfs) if desc_lines_surfs else 0,
            unlock_info_surf.get_width() if unlock_info_surf else 0
        )
        
        card_w = max_content_width_for_card + 2 * padding_inside_card
        card_w = min(card_w, self._cached_width * 0.6)
        card_h = card_content_total_h + 2 * padding_inside_card + 20
        
        title_bottom = title_rect.bottom if title_rect else 100
        main_card_x = (self._cached_width - card_w) // 2
        main_card_y = title_bottom + 40
        
        main_card_rect = Rect(main_card_x, main_card_y, card_w, card_h)
        
        # Draw card background
        card_bg = Surface((card_w, card_h), SRCALPHA)
        card_bg.fill((25, 30, 40, 230))
        self.screen.blit(card_bg, main_card_rect.topleft)
        draw_rect(self.screen, GOLD, main_card_rect, 3)
        
        current_y_in_card = main_card_rect.top + padding_inside_card
        
        # Draw drone image
        if drone_image_surf:
            display_drone_image = drone_image_surf
            if not is_unlocked:
                temp_img = drone_image_surf.copy()
                temp_img.set_alpha(100)
                display_drone_image = temp_img
            
            final_img_rect = display_drone_image.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(display_drone_image, final_img_rect)
            current_y_in_card = final_img_rect.bottom + spacing_between_elements
        else:
            current_y_in_card += img_height + spacing_between_elements
        
        # Draw name
        name_color_final = WHITE if is_unlocked else GREY
        name_surf_final = self._render_text_safe(name_text, "medium_text", name_color_final, fallback_size=36)
        final_name_rect = name_surf_final.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
        self.screen.blit(name_surf_final, final_name_rect)
        current_y_in_card = final_name_rect.bottom + spacing_between_elements
        
        # Draw stats box
        final_stats_box_draw_rect = Rect(main_card_rect.centerx - stats_box_visual_width // 2, current_y_in_card, 
                                        stats_box_visual_width, stats_box_visual_height)
        
        stats_bg = Surface((stats_box_visual_width, stats_box_visual_height), SRCALPHA)
        stats_bg.fill((40, 45, 55, 200))
        self.screen.blit(stats_bg, final_stats_box_draw_rect.topleft)
        draw_rect(self.screen, CYAN, final_stats_box_draw_rect, 1)
        
        stat_y_pos_render = final_stats_box_draw_rect.top + stats_box_padding
        for i, (label_s, value_s) in enumerate(stats_content_surfaces):
            self.screen.blit(label_s, (final_stats_box_draw_rect.left + stats_box_padding, stat_y_pos_render))
            self.screen.blit(value_s, (final_stats_box_draw_rect.right - stats_box_padding - value_s.get_width(), stat_y_pos_render))
            stat_y_pos_render += max(label_s.get_height(), value_s.get_height()) + (5 if i < len(stats_content_surfaces) - 1 else 0)
        
        current_y_in_card = final_stats_box_draw_rect.bottom + spacing_between_elements
        
        # Draw description
        desc_start_y_render = current_y_in_card
        for line_surf in desc_lines_surfs:
            self.screen.blit(line_surf, line_surf.get_rect(centerx=main_card_rect.centerx, top=desc_start_y_render))
            desc_start_y_render += line_surf.get_height() + 3
        
        current_y_in_card = desc_start_y_render + 5
        
        # Draw unlock info
        if unlock_info_surf:
            unlock_info_rect = unlock_info_surf.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(unlock_info_surf, unlock_info_rect)
        
        # Draw navigation arrows
        arrow_font = self.asset_manager.get_font("large_text", 48) or Font(None, 48)
        left_arrow_surf = arrow_font.render("◀", True, WHITE if len(drone_options_ids) > 1 else GREY)
        right_arrow_surf = arrow_font.render("▶", True, WHITE if len(drone_options_ids) > 1 else GREY)
        
        arrow_y_center = main_card_rect.centery
        arrow_padding_from_card_edge = 40
        
        if len(drone_options_ids) > 1:
            left_arrow_rect = left_arrow_surf.get_rect(centery=arrow_y_center, right=main_card_rect.left - arrow_padding_from_card_edge)
            self.screen.blit(left_arrow_surf, left_arrow_rect)
            right_arrow_rect = right_arrow_surf.get_rect(centery=arrow_y_center, left=main_card_rect.right + arrow_padding_from_card_edge)
            self.screen.blit(right_arrow_surf, right_arrow_rect)
        
        # Instructions
        instr_text = "LEFT/RIGHT: Cycle | ENTER: Select/Unlock | ESC: Back"
        instr_surf = self._render_text_safe(instr_text, "ui_text", self.INSTRUCTION_TEXT_COLOR, fallback_size=24)
        instr_bg_box = Surface((instr_surf.get_width() + self.INSTRUCTION_PADDING_X, 
                              instr_surf.get_height() + self.INSTRUCTION_PADDING_Y), SRCALPHA)
        instr_bg_box.fill(self.INSTRUCTION_BG_COLOR)
        instr_bg_box.blit(instr_surf, instr_surf.get_rect(center=(instr_bg_box.get_width() // 2, instr_bg_box.get_height() // 2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(self._cached_width // 2, self.BOTTOM_INSTRUCTION_CENTER_Y)))
        
        # Player cores display
        cores_label_text_surf = self._render_text_safe(f"Player Cores: ", "ui_text", GOLD, fallback_size=24)
        cores_value_text_surf = self._render_text_safe(f"{self.drone_system.get_cores()}", "ui_text", GOLD, fallback_size=24)
        cores_emoji_surf = self._render_text_safe(" 💠", "ui_text", GOLD, fallback_size=24)
        
        total_cores_display_width = cores_label_text_surf.get_width() + cores_value_text_surf.get_width() + cores_emoji_surf.get_width()
        cores_start_x = self._cached_width - 20 - total_cores_display_width
        
        max_element_height_cores = max(cores_label_text_surf.get_height(), cores_value_text_surf.get_height(), cores_emoji_surf.get_height())
        cores_y_baseline = self.BOTTOM_INSTRUCTION_CENTER_Y - (instr_bg_box.get_height() // 2) - 10 - max_element_height_cores
        current_x_offset_cores = cores_start_x
        
        self.screen.blit(cores_label_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_label_text_surf.get_height()) // 2))
        current_x_offset_cores += cores_label_text_surf.get_width()
        self.screen.blit(cores_value_text_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_value_text_surf.get_height()) // 2))
        current_x_offset_cores += cores_value_text_surf.get_width()
        self.screen.blit(cores_emoji_surf, (current_x_offset_cores, cores_y_baseline + (max_element_height_cores - cores_emoji_surf.get_height()) // 2))

    def draw_gameplay_hud(self, player_active_abilities_data=None):
        player = self.game_controller.player
        if not player: return
        panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        height, width = self._cached_height, self._cached_width
        panel_y = height - panel_height
        panel_bg_color = (*DARK_GREY[:3], 220)
        panel_surface = Surface((width, panel_height), SRCALPHA)
        panel_surface.fill(panel_bg_color)
        self.screen.blit(panel_surface, (0, panel_y))
        draw_line(self.screen, CYAN, (0, panel_y), (width, panel_y), 2)
        font_ui, font_small = self.asset_manager.get_font("ui_text", 28), self.asset_manager.get_font("ui_text", 24)
        
        # Left side - Weapon and lives
        wpn_x, wpn_y = 30, panel_y + 20
        wpn_mode = player.current_weapon_mode
        self.update_weapon_icon_surface(wpn_mode)
        
        weapon_icon = self.ui_asset_surfaces.get("current_weapon_icon")
        if weapon_icon:
            # Display lives using weapon icons
            self._draw_lives_icons(weapon_icon, wpn_x, wpn_y)
            
            # Draw weapon cooldown bar
            rotated_icon = rotate(weapon_icon, 90)
            icon_height = rotated_icon.get_size()[1]
            self._draw_weapon_cooldown_bar(player, wpn_x, wpn_y + icon_height + 10)

        # Draw powerup bars above weapon bar
        self._draw_powerup_bars(wpn_x, wpn_y - 30, 200)

        # Right side - Rings and fragments
        self._draw_rings_hud(width, panel_y)
        self._draw_fragments_hud(width, panel_y)
        
        # NEW: Draw active abilities (if player_active_abilities_data is passed)
        if player_active_abilities_data:
            self._draw_active_abilities_hud(player_active_abilities_data)
        
        # Draw chapter objectives in the middle of the HUD
        self._draw_chapter_objectives_hud()

    def get_scaled_fragment_icon_surface(self, fragment_id):
        # Normalize fragment ID
        normalized_id = self._normalize_fragment_id(fragment_id)
        
        # Check cache first
        icon_surface = self.ui_asset_surfaces["core_fragment_icons"].get(normalized_id)
        if icon_surface: 
            return icon_surface
        
        # Try loading from asset manager
        icon_surface = self._load_fragment_icon(normalized_id)
        if icon_surface:
            self.ui_asset_surfaces["core_fragment_icons"][normalized_id] = icon_surface
            return icon_surface
        
        warning(f"UIManager: Scaled icon surface for fragment_id '{fragment_id}' not found. Using fallback.")
        return self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", PURPLE)
    
    def _normalize_fragment_id(self, fragment_id):
        if fragment_id.startswith("fragment_level_"):
            level_num = fragment_id.split("_")[-1]
            level_map = {"1": "alpha", "2": "beta", "3": "gamma"}
            return level_map.get(level_num, fragment_id)
        return fragment_id
    
    def _load_fragment_icon(self, fragment_id):
        if fragment_id in ["alpha", "beta", "gamma"]:
            direct_key = f"images/collectibles/core_fragment_{fragment_id}.png"
            return self.asset_manager.get_image(direct_key, scale_to_size=self.ui_icon_size_fragments)
        elif fragment_id == "orichalc_fragment_container":
            icon = self.asset_manager.get_image("ORICHALC_FRAGMENT_CONTAINER", scale_to_size=self.ui_icon_size_fragments)
            if icon:
                # Remove transparency by converting to RGB
                non_transparent_icon = Surface(self.ui_icon_size_fragments).convert()
                non_transparent_icon.fill(BLACK)
                non_transparent_icon.blit(icon, (0, 0))
                return non_transparent_icon
            return icon
        return None

    def _draw_active_abilities_hud(self, active_abilities_data):
        ability_icon_x = get_setting("display", "HUD_ABILITY_ICON_X_OFFSET", 100)
        ability_icon_y = get_setting("display", "HUD_ABILITY_ICON_Y_OFFSET", 20)
        ability_icon_size = self.ui_icon_size_ability
        font_small = self.asset_manager.get_font("small_text", 24) or Font(None, 24)
        current_time_ms = get_ticks()

        # Assuming only one active ability is tracked for now for simplicity in UI placement
        # If multiple abilities are to be displayed, this loop would iterate over them
        for ability_id, status in active_abilities_data.items():
            if not self.drone_system.has_ability_unlocked(ability_id):
                continue

            icon = self.ui_asset_surfaces["ability_icon_placeholder"]
            icon_rect = icon.get_rect(topleft=(ability_icon_x, ability_icon_y))
            self.screen.blit(icon, icon_rect)

            # Draw cooldown overlay
            if 'cooldown_end_time' in status:
                total_cooldown = self.game_controller.player.ability_cooldowns.get(ability_id, 1) # Get total cooldown
                time_remaining = status['cooldown_end_time'] - current_time_ms
                
                if time_remaining > 0:
                    cooldown_ratio = time_remaining / total_cooldown
                    
                    # Darken the icon for cooldown
                    cooldown_overlay = Surface(icon_rect.size, SRCALPHA)
                    cooldown_overlay.fill((0, 0, 0, 150)) # Dark transparent overlay
                    self.screen.blit(cooldown_overlay, icon_rect)

                    # Draw cooldown number
                    cooldown_text = f"{ceil(time_remaining / 1000)}s"
                    text_surf = font_small.render(cooldown_text, True, WHITE)
                    self.screen.blit(text_surf, text_surf.get_rect(center=icon_rect.center))
                else:
                    # Not on cooldown, but ensure it's not partially active
                    pass # Icon is drawn normally

            # Draw key reminder
            key_text_y_offset = ability_icon_size[1] + 5 # Below the icon
            key_text = f"F: {ability_id.replace('_', ' ').title()}"
            key_surf = font_small.render(key_text, True, WHITE)
            self.screen.blit(key_surf, (ability_icon_x, ability_icon_y + key_text_y_offset))

    def _draw_chapter_objectives_hud(self):
        """Draw chapter objectives in the middle of the HUD"""
        if not hasattr(self.game_controller, 'story_manager') or not self.game_controller.story_manager:
            return
            
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if not current_chapter or not current_chapter.objectives:
            return
            
        width, height = self._cached_width, self._cached_height
        panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        panel_y = height - panel_height
        
        # Position objectives in the center of the HUD panel
        objectives_x = width // 2
        objectives_y = panel_y + 30
        
        font = self.asset_manager.get_font("ui_text", 24) or Font(None, 24)
        
        for i, objective in enumerate(current_chapter.objectives):
            obj_color = YELLOW if objective.is_complete else WHITE
            obj_text = f"• {objective.description}"
            obj_surf = font.render(obj_text, True, obj_color)
            obj_rect = obj_surf.get_rect(center=(objectives_x, objectives_y + i * 25))
            self.screen.blit(obj_surf, obj_rect)
            obj_surf = font.render(obj_text, True, obj_color)
            obj_rect = obj_surf.get_rect(center=(objectives_x, objectives_y + i * 25))
            self.screen.blit(obj_surf, obj_rect)

    def draw_settings_menu(self):
        if self.settings_ui:
            self.settings_ui.draw(self.screen, self.game_controller.ui_flow_controller)
        else:
            # Fallback to old method if SettingsUI not available
            self._draw_star_background()
            title_surf = self._render_text_safe("Settings", "large_text", GOLD, fallback_size=48)
            self.screen.blit(title_surf, title_surf.get_rect(center=(self._cached_width // 2, 80)))

    def draw_leaderboard_ui(self):
        if self.leaderboard_ui:
            self.leaderboard_ui.draw(self.screen)
        else:
            # Fallback to old method if LeaderboardUI not available
            self._draw_star_background()
            title_surf = self._render_text_safe("Leaderboard", "large_text", GOLD, fallback_size=48)
            width = get_setting("display", "WIDTH", 1920)
            self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 80)))
            
            scores = self.game_controller.ui_flow_controller.leaderboard_scores
            font_header = self.asset_manager.get_font("medium_text", 36) or Font(None, 36)
            font_score = self.asset_manager.get_font("ui_text", 28) or Font(None, 28)
            
            headers, header_positions = ["RANK", "NAME", "SCORE", "LEVEL"], [width*0.2, width*0.35, width*0.6, width*0.8]
            
            for i, header in enumerate(headers):
                header_surf = font_header.render(header, True, CYAN)
                self.screen.blit(header_surf, header_surf.get_rect(center=(header_positions[i], 180)))
                
            for i, score_entry in enumerate(scores):
                y_pos = 250 + i * 50
                color = GOLD if i == 0 else WHITE
                rank_surf = font_score.render(f"{i+1}", True, color)
                name_surf = font_score.render(score_entry.get('name', 'N/A'), True, color)
                score_surf = font_score.render(str(score_entry.get('score', 0)), True, color)
                level_surf = font_score.render(str(score_entry.get('level', 0)), True, color)
                self.screen.blit(rank_surf, rank_surf.get_rect(center=(header_positions[0], y_pos)))
                self.screen.blit(name_surf, name_surf.get_rect(center=(header_positions[1], y_pos)))
                self.screen.blit(score_surf, score_surf.get_rect(center=(header_positions[2], y_pos)))
                self.screen.blit(level_surf, level_surf.get_rect(center=(header_positions[3], y_pos)))

    def draw_game_over_overlay(self):
        self._draw_star_background()
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        overlay = Surface((width, height), SRCALPHA); overlay.fill((50, 0, 0, 180))
        self.screen.blit(overlay, (0,0))
        title_surf = self._render_text_safe("DRONE DESTROYED", "title_text", RED, fallback_size=90)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, height // 2 - 100)))
        
        # Get the current state from the game controller
        current_state = self.game_controller.state_manager.get_current_state()
        
        # Check if the current state has the options and selected_option attributes
        if hasattr(current_state, 'options') and hasattr(current_state, 'selected_option'):
            options = current_state.options
            selected_option = current_state.selected_option
            
            # Draw the options
            option_y_start = height // 2 + 20
            option_spacing = 50
            font = self.asset_manager.get_font("medium_text", 36) or Font(None, 36)
            
            for i, option in enumerate(options):
                color = GOLD if i == selected_option else WHITE
                option_surf = font.render(option, True, color)
                self.screen.blit(option_surf, option_surf.get_rect(center=(width // 2, option_y_start + i * option_spacing)))
            
            # Draw navigation instructions
            instruction_surf = self._render_text_safe("Use UP/DOWN arrows and ENTER to select", "ui_text", CYAN, fallback_size=24)
            self.screen.blit(instruction_surf, instruction_surf.get_rect(center=(width // 2, height // 2 + 150)))
        else:
            # Fallback to old prompt if the state doesn't have the new attributes
            prompt_surf = self._render_text_safe("Press 'R' to Restart or 'M' for Menu", "medium_text", WHITE, fallback_size=48)
            self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(width//2, height//2 + 50)))

    def draw_enter_name_overlay(self):
        self._draw_star_background()
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        title_surf = self._render_text_safe("High Score!", "large_text", GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, height//2 - 100)))
        prompt_surf = self._render_text_safe("Enter Your Name:", "medium_text", WHITE, fallback_size=48)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(width // 2, height//2)))
        name_input = self.game_controller.ui_flow_controller.player_name_input_cache
        name_surf = self._render_text_safe(f"{name_input}_", "large_text", CYAN, fallback_size=48)
        self.screen.blit(name_surf, name_surf.get_rect(center=(width//2, height//2 + 80)))

    def draw_architect_vault_success_overlay(self):
        self._draw_star_background()
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        title_surf = self._render_text_safe("Vault Conquered", "large_text", GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, height//2)))

    def draw_architect_vault_failure_overlay(self):
        self._draw_star_background()
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        title_surf = self._render_text_safe("Mission Failed", "large_text", RED, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, height//2)))
    
    def draw_narrative_state(self):
        """Draw method for NarrativeState - handled by the state itself"""
        # The NarrativeState handles its own drawing in its draw() method
        # This is just a placeholder to satisfy the UI manager's state mapping
        pass

    def draw_maze_defense_hud(self):
        width = get_setting("display", "WIDTH", 1920)
        title_surf = self._render_text_safe("Maze Defense", "large_text", CYAN, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 50)))
        
        # Display player cores
        if self.drone_system:
            cores = self.drone_system.get_cores()
            cores_surf = self._render_text_safe(f"Cores: {cores}", "ui_text", GOLD, fallback_size=28)
            self.screen.blit(cores_surf, (20, 20))

    def draw_pause_overlay(self):
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        overlay = Surface((width, height), SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        pause_text = self._render_text_safe("PAUSED", "title_text", WHITE, fallback_size=90)
        self.screen.blit(pause_text, pause_text.get_rect(center=(width//2, height//2)))

    def _draw_powerup_bars(self, x, y, width):
        """Draw powerup status bars above weapon bar"""
        player = self.game_controller.player
        if not player or not hasattr(player, 'powerup_manager'):
            return
            
        bar_height = 8
        bar_spacing = 12
        current_y = y
        
        # Shield bar
        if hasattr(player.powerup_manager, 'shield_active') and player.powerup_manager.shield_active:
            remaining_time = player.powerup_manager.shield_end_time - get_ticks()
            if remaining_time > 0:
                progress = remaining_time / player.powerup_manager.shield_duration
                draw_rect(self.screen, DARK_GREY, (x, current_y, width, bar_height))
                draw_rect(self.screen, CYAN, (x, current_y, width * progress, bar_height))
                draw_rect(self.screen, WHITE, (x, current_y, width, bar_height), 1)
                current_y -= bar_spacing
        
        # Speed boost bar
        if hasattr(player.powerup_manager, 'speed_boost_active') and player.powerup_manager.speed_boost_active:
            remaining_time = player.powerup_manager.speed_boost_end_time - get_ticks()
            if remaining_time > 0:
                progress = remaining_time / player.powerup_manager.speed_boost_duration
                draw_rect(self.screen, DARK_GREY, (x, current_y, width, bar_height))
                draw_rect(self.screen, GREEN, (x, current_y, width * progress, bar_height))
                draw_rect(self.screen, WHITE, (x, current_y, width, bar_height), 1)

    def _draw_lives_icons(self, weapon_icon, x, y):
        """Draw player lives using weapon icons"""
        rotated_icon = rotate(weapon_icon, 90)
        scaled_weapon_icon = scale(rotated_icon, self.ui_icon_size_lives)
        current_lives = self.game_controller.lives
        icon_spacing = 10

        for i in range(current_lives):
            icon_x = x + (i * (self.ui_icon_size_lives[0] + icon_spacing))
            self.screen.blit(scaled_weapon_icon, (icon_x, y))
    
    def _draw_weapon_cooldown_bar(self, player, x, y):
        """Draw weapon cooldown progress bar"""
        time_since = get_ticks() - player.last_shot_time
        progress = min(1.0, time_since / player.current_shoot_cooldown) if player.current_shoot_cooldown > 0 else 1.0
        cooldown_width = 200
        draw_rect(self.screen, DARK_GREY, (x, y, cooldown_width, 10))
        draw_rect(self.screen, YELLOW, (x, y, cooldown_width * progress, 10))
        draw_rect(self.screen, WHITE, (x, y, cooldown_width, 10), 1)
    
    def _draw_rings_hud(self, width, panel_y):
        """Draw ring collection indicators"""
        hud_ring_icon_area_x_offset = get_setting("display", "HUD_RING_ICON_AREA_X_OFFSET", 150)
        hud_ring_icon_area_y_offset = get_setting("display", "HUD_RING_ICON_AREA_Y_OFFSET", 30)
        hud_ring_icon_size = get_setting("display", "HUD_RING_ICON_SIZE", 24)
        hud_ring_icon_spacing = get_setting("display", "HUD_RING_ICON_SPACING", 5)
        
        rings_x = width - hud_ring_icon_area_x_offset
        rings_y = panel_y + hud_ring_icon_area_y_offset
        
        current_game_state = self.state_manager.get_current_state_id() if self.state_manager else None
        if current_game_state == "PlayingState":
            ring_icon, ring_empty = self.ui_asset_surfaces.get("ring_icon"), self.ui_asset_surfaces.get("ring_icon_empty")
            if ring_icon and ring_empty:
                for i in range(self.game_controller.level_manager.total_rings_per_level): 
                    show_filled = i < self.game_controller.level_manager.displayed_collected_rings_count
                    icon_x = rings_x + i * (hud_ring_icon_size + hud_ring_icon_spacing)
                    self.screen.blit(ring_icon if show_filled else ring_empty, (icon_x, rings_y))
    
    def _draw_fragments_hud(self, width, panel_y):
        """Draw core fragment collection indicators"""
        hud_ring_icon_area_x_offset = get_setting("display", "HUD_RING_ICON_AREA_X_OFFSET", 150)
        frags_x = width - hud_ring_icon_area_x_offset
        frags_y = panel_y + 65
        
        
        core_fragment_details = settings_manager.get_core_fragment_details()
        collected = self.drone_system.get_collected_fragments_ids()
        required = sorted([d['id'] for d in core_fragment_details.values() if d.get('required_for_vault')])
        animating_ids = [anim['fragment_id'] for anim in self.game_controller.animating_fragments_to_hud]

        for i, frag_id in enumerate(required):
            show_filled_icon = (frag_id in collected) and (frag_id not in animating_ids)
            icon = self.ui_asset_surfaces["core_fragment_icons"].get(frag_id) if show_filled_icon else self.ui_asset_surfaces["core_fragment_empty_icon"]
            if icon: 
                self.screen.blit(icon, (frags_x + i * (self.ui_icon_size_fragments[0] + 5), frags_y))
