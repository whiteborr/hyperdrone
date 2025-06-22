# ui/ui.py
from os.path import exists
from math import ceil
from random import random
import logging

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

try:
    from .build_menu import BuildMenu
except ImportError:
    logging.warning("UIManager: Could not import BuildMenu. Build UI will not be available.")
    BuildMenu = None 

logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')


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
                        logger.warning(f"UIManager: Core fragment icon for ID '{frag_id}' not found. Using fallback.")
                        self.ui_asset_surfaces["core_fragment_icons"][frag_id] = self._create_fallback_icon_surface(self.ui_icon_size_fragments, frag_id[:1] if frag_id else "!", PURPLE)
        
        reactor_icon_asset = self.asset_manager.get_image("reactor_hud_icon_key", scale_to_size=self.ui_icon_size_reactor)
        if reactor_icon_asset: self.ui_asset_surfaces["reactor_icon_placeholder"] = reactor_icon_asset
        else: self.ui_asset_surfaces["reactor_icon_placeholder"] = self._create_fallback_icon_surface(self.ui_icon_size_reactor, "R", (50,50,200))

        # NEW: Load ability icon
        self.ui_asset_surfaces["ability_icon_placeholder"] = self.asset_manager.get_image("ability_icon_placeholder", scale_to_size=self.ui_icon_size_ability)
        if not self.ui_asset_surfaces["ability_icon_placeholder"]:
            logger.warning("UIManager: Ability icon placeholder not found. Using fallback.")
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
            logger.warning(f"UIManager: Life icon for drone '{selected_drone_id}' (key: '{life_icon_asset_key}') not found. Using fallback.")
            self.ui_asset_surfaces["current_drone_life_icon"] = self._create_fallback_icon_surface(size=self.ui_icon_size_lives, text="L", color=CYAN)
            
    def update_weapon_icon_surface(self, weapon_mode):
        """Update the weapon icon in the HUD based on the current weapon mode"""
        # Map weapon modes to their sprite names
        from constants import (
            WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
            WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
            WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
            WEAPON_MODE_LIGHTNING
        )
        
        weapon_sprite_names = {
            WEAPON_MODE_DEFAULT: "default",
            WEAPON_MODE_TRI_SHOT: "tri_shot",
            WEAPON_MODE_RAPID_SINGLE: "rapid_single",
            WEAPON_MODE_RAPID_TRI: "rapid_tri_shot",
            WEAPON_MODE_BIG_SHOT: "big_shot",
            WEAPON_MODE_BOUNCE: "bounce",
            WEAPON_MODE_PIERCE: "pierce",
            WEAPON_MODE_HEATSEEKER: "heatseeker",
            WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "heatseeker_plus_bullets",
            WEAPON_MODE_LIGHTNING: "lightning"
        }
        
        # Get the weapon sprite name
        weapon_sprite_name = weapon_sprite_names.get(weapon_mode, "default")
        
        # Try to load the weapon-specific drone sprite for the HUD
        weapon_sprite_key = f"drone_{weapon_sprite_name}"
        loaded_icon = self.asset_manager.get_image(weapon_sprite_key, scale_to_size=(64, 64))
        
        # If not found, use the generic weapon icon
        if not loaded_icon:
            loaded_icon = self.asset_manager.get_image("weapon_upgrade_powerup_icon", scale_to_size=(64, 64))
            
        # Store the icon for use in the HUD
        if loaded_icon:
            self.ui_asset_surfaces["current_weapon_icon"] = loaded_icon
        else:
            logger.warning(f"UIManager: Weapon icon for mode '{weapon_mode}' not found. Using fallback.")
            # Use CYAN which is already imported at the top of the file
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
            except Exception as e: logger.error(f"UIManager: Error rendering fallback icon text '{text}' with font key '{font_key}': {e}")
        return surface

    def _render_text_safe(self, text, font_key, color, fallback_size=24):
        font = self.asset_manager.get_font(font_key, fallback_size)
        if not font: font = Font(None, fallback_size)
        try: return font.render(str(text), True, color)
        except Exception as e:
            logger.error(f"UIManager: Error rendering text '{text}' with font key '{font_key}': {e}")
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
            "GameOverState", "EnterNameState", "StoryMapState"
        ]
        
        if is_menu_like_state: 
            self.screen.fill(BLACK)

        state_draw_map = {
            "MainMenuState": self.draw_main_menu,
            "DroneSelectState": self.draw_drone_select_menu,
            "SettingsState": self.draw_settings_menu,
            "LeaderboardState": self.draw_leaderboard_overlay,
            "CodexState": self.draw_codex_screen,
            "GameOverState": self.draw_game_over_overlay,
            "EnterNameState": self.draw_enter_name_overlay,
            "GameIntroScrollState": self.draw_game_intro_scroll,
            "StoryMapState": self.draw_story_map,
            "ArchitectVaultSuccessState": self.draw_architect_vault_success_overlay,
            "ArchitectVaultFailureState": self.draw_architect_vault_failure_overlay
        }

        if current_state in state_draw_map:
            state_draw_map[current_state]()
        
        elif current_state and current_state.startswith("ArchitectVault"):
            self.draw_architect_vault_hud_elements()
            if self.game_controller.paused: self.draw_pause_overlay()
        
        elif current_state in ["PlayingState", "BonusLevelPlayingState"]:
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
        
        # Draw current chapter details below the map
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
            
            # Draw player cursor on current chapter
            if i == current_chapter_index:
                cursor_x = chapter_x + 16  # Center cursor over chapter icon
                cursor_y = map_y - 40  # Position above the chapter icon
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
        self._draw_star_background()
        ui_flow = self.game_controller.ui_flow_controller
        font_title = self.asset_manager.get_font("large_text", 52) or Font(None, 52)
        font_cat = self.asset_manager.get_font("medium_text", 36) or Font(None, 36)
        font_entry = self.asset_manager.get_font("ui_text", 28) or Font(None, 28)
        font_content = self.asset_manager.get_font("ui_text", 24) or Font(None, 24)
        
        width, height = self._cached_width, self._cached_height
        
        title_surf = font_title.render("CODEX", True, GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width / 2, 60)))
        
        if ui_flow.codex_current_view == "categories":
            if not ui_flow.codex_categories_list:
                no_entries_surf = font_cat.render("No lore entries unlocked yet!", True, WHITE)
                self.screen.blit(no_entries_surf, no_entries_surf.get_rect(center=(width/2, 300)))
                instruction_surf = font_entry.render("Explore the game to unlock lore entries", True, CYAN)
                self.screen.blit(instruction_surf, instruction_surf.get_rect(center=(width/2, 350)))
            else:
                start_y = 150
                for i, cat_name in enumerate(ui_flow.codex_categories_list):
                    color = YELLOW if i == ui_flow.codex_selected_category_index else WHITE
                    cat_surf = font_cat.render(cat_name, True, color)
                    self.screen.blit(cat_surf, cat_surf.get_rect(center=(width/2, start_y + i * 50)))
        
        elif ui_flow.codex_current_view == "entries":
            cat_title_surf = font_cat.render(f"Category: {ui_flow.codex_current_category_name}", True, CYAN)
            self.screen.blit(cat_title_surf, cat_title_surf.get_rect(center=(width/2, 140)))
            start_y = 220
            if not ui_flow.codex_entries_in_category_list:
                no_entries_surf = font_entry.render("No entries in this category yet!", True, WHITE)
                self.screen.blit(no_entries_surf, no_entries_surf.get_rect(center=(width/2, 300)))
            else:
                for i, entry_data in enumerate(ui_flow.codex_entries_in_category_list):
                    color = YELLOW if i == ui_flow.codex_selected_entry_index_in_category else WHITE
                    entry_surf = font_entry.render(entry_data.get("title", "Unknown"), True, color)
                    self.screen.blit(entry_surf, (100, start_y + i * 40))
                
        elif ui_flow.codex_current_view == "content":
            entry_details = self.drone_system.get_lore_entry_details(ui_flow.codex_selected_entry_id)
            if entry_details:
                content_title_surf = font_cat.render(entry_details.get("title", ""), True, GOLD)
                self.screen.blit(content_title_surf, content_title_surf.get_rect(center=(width/2, 140)))
                
                content_text = entry_details.get("content", "No content available.")
                wrapped_lines = self._wrap_text_with_font_obj(content_text, font_content, width - 200)
                ui_flow.codex_current_entry_total_lines = len(wrapped_lines)

                start_y, line_height = 220, font_content.get_linesize()
                for i, line in enumerate(wrapped_lines[ui_flow.codex_content_scroll_offset:]):
                    line_surf = font_content.render(line, True, WHITE)
                    line_y = start_y + i * line_height
                    if line_y > height - 100: break
                    self.screen.blit(line_surf, (100, line_y))
        
        # Add navigation instructions
        if ui_flow.codex_current_view == "categories":
            instruction = "Use UP/DOWN to navigate, ENTER to select, ESC to return to menu"
        elif ui_flow.codex_current_view == "entries":
            instruction = "Use UP/DOWN to navigate, ENTER to view, ESC to go back"
        else:
            instruction = "Use UP/DOWN to scroll, ESC to go back"
        
        instruction_surf = font_content.render(instruction, True, CYAN)
        self.screen.blit(instruction_surf, instruction_surf.get_rect(center=(width/2, height - 50)))

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
        self._draw_star_background()
        title_surf = self._render_text_safe("Select Drone", "large_text", GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(self._cached_width // 2, 80)))
        
        ui_flow = self.game_controller.ui_flow_controller
        if not ui_flow.drone_select_options: return

        selected_drone_id = ui_flow.drone_select_options[ui_flow.selected_drone_preview_index]
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        is_unlocked = self.drone_system.is_drone_unlocked(selected_drone_id)

        sprite_asset_key = drone_config.get("sprite_path", "").replace("assets/","")
        sprite_surf = self.asset_manager.get_image(sprite_asset_key, scale_to_size=(256, 256))
        if sprite_surf: self.screen.blit(sprite_surf, sprite_surf.get_rect(center=(self._cached_width/2, self._cached_height/2 - 100)))

        name_surf = self._render_text_safe(drone_config.get("name"), "medium_text", WHITE if is_unlocked else GREY, fallback_size=48)
        self.screen.blit(name_surf, name_surf.get_rect(center=(self._cached_width/2, self._cached_height/2 + 100)))
        
        desc_surf = self._render_text_safe(drone_config.get("description"), "ui_text", CYAN, fallback_size=24)
        self.screen.blit(desc_surf, desc_surf.get_rect(center=(self._cached_width/2, self._cached_height/2 + 150)))
        
        if not is_unlocked:
            unlock_cond = drone_config.get("unlock_condition", {})
            unlock_desc = unlock_cond.get("description", "Locked")
            unlock_surf = self._render_text_safe(unlock_desc, "ui_text", RED, fallback_size=28)
            self.screen.blit(unlock_surf, unlock_surf.get_rect(center=(self._cached_width/2, self._cached_height/2 + 200)))

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
        
        logger.warning(f"UIManager: Scaled icon surface for fragment_id '{fragment_id}' not found. Using fallback.")
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
            return self.asset_manager.get_image("ORICHALC_FRAGMENT_CONTAINER", scale_to_size=self.ui_icon_size_fragments)
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
        self._draw_star_background()
        title_surf = self._render_text_safe("Settings", "large_text", GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(self._cached_width // 2, 80)))
        
        ui_flow = self.game_controller.ui_flow_controller
        settings_items, selected_index = ui_flow.settings_items_data, ui_flow.selected_setting_index
        font_setting = self.asset_manager.get_font("ui_text", 28)
        
        start_y = 200
        for i, item in enumerate(settings_items):
            y_pos = start_y + i * 50
            color = YELLOW if i == selected_index else WHITE
            label_surf = font_setting.render(item['label'], True, color)
            self.screen.blit(label_surf, (200, y_pos))
            
            val_text = ""
            if item['type'] != 'action':
                category = item.get('category', 'gameplay')  # Default to gameplay if not specified
                current_val = get_setting(category, item['key'], None)
                val_to_format = current_val
                if item.get("is_ms_to_sec") and val_to_format is not None: val_to_format /= 1000
                
                if 'display_format' in item and val_to_format is not None:
                    val_text = item['display_format'].format(val_to_format)
                elif 'get_display' in item and current_val is not None:
                    val_text = item['get_display'](current_val)
                else:
                    val_text = str(current_val) if current_val is not None else "N/A"
                    
                if item['type'] in ["numeric", "choice"]: val_text = f"< {val_text} >"
            else: val_text = "[PRESS ENTER]"
            
            val_surf = font_setting.render(val_text, True, color)
            self.screen.blit(val_surf, (self._cached_width - 200 - val_surf.get_width(), y_pos))

    def draw_leaderboard_overlay(self):
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

    def draw_maze_defense_hud(self):
        width = get_setting("display", "WIDTH", 1920)
        title_surf = self._render_text_safe("Maze Defense", "large_text", CYAN, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 50)))
        
        # Display player cores
        if self.drone_system:
            cores = self.drone_system.get_player_cores()
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
        frags_x = width - 200
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
