# hyperdrone/ui/ui.py
import os
import math
import random
import logging

import pygame

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

        height = get_setting("display", "HEIGHT", 1080)
        self.BOTTOM_INSTRUCTION_CENTER_Y = height - 50
        self.SECONDARY_INSTRUCTION_CENTER_Y = height - 80
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
        # Use state_manager instead of scene_manager
        if not hasattr(self, 'state_manager') or self.state_manager is None:
            return
            
        current_state = self.state_manager.get_current_state_id() if self.state_manager else None
        ui_flow_ctrl = self.game_controller.ui_flow_controller 
        
        is_menu_like_state = current_state in [
            "MainMenuState", "DroneSelectState", "SettingsState",
            "LeaderboardState", "CodexState",
            "ArchitectVaultSuccessState", "ArchitectVaultFailureState",
            "GameOverState", "EnterNameState", "StoryMapState"
        ]
        
        if is_menu_like_state: 
            self.screen.fill(BLACK)
            if ui_flow_ctrl and hasattr(ui_flow_ctrl, 'menu_stars') and ui_flow_ctrl.menu_stars:
                 for star_params in ui_flow_ctrl.menu_stars:
                    pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

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
            self.draw_gameplay_hud()
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
        """Draw the story map screen showing player progression through chapters"""
        # 1. Draw background
        bg = self.asset_manager.load_image('images/ui/story_map_background.png', key='story_map_background')
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        if bg:
            scaled_bg = pygame.transform.scale(bg, (width, height))
            self.screen.blit(scaled_bg, (0, 0))
        else:
            self.screen.fill((10, 20, 40))  # Dark blue fallback color
            
        # Title removed from minimap as requested

        # 2. Define chapter positions and path - moved lower on the screen
        chapter_positions = [
            (width * 0.2, height * 0.6),    # Chapter 1
            (width * 0.35, height * 0.45),  # Chapter 2
            (width * 0.5, height * 0.6),    # Chapter 3
            (width * 0.65, height * 0.45),  # Chapter 4
            (width * 0.8, height * 0.6),    # Chapter 5
            (width * 0.9, height * 0.4)     # Bonus Chapter
        ]
        
        # Get current chapter index from story manager
        current_chapter_index = 0  # Default to first chapter
        current_chapter = None
        if hasattr(self.game_controller, 'story_manager'):
            story_manager = self.game_controller.story_manager
            if story_manager:
                current_chapter = story_manager.get_current_chapter()
                if current_chapter:
                    # Map chapter IDs to indices (0-based)
                    chapter_id_map = {
                        "chapter_1": 0,
                        "chapter1": 0,
                        "chapter_2": 1,
                        "chapter2": 1,
                        "chapter_3": 2,
                        "chapter3": 2,
                        "chapter_4": 3,
                        "chapter4": 3,
                        "chapter_5": 4,
                        "chapter5": 4,
                        "bonus": 5
                    }
                    current_chapter_index = chapter_id_map.get(current_chapter.chapter_id, 0)
                else:
                    # If no current chapter, set to first chapter
                    current_chapter_index = 0
        
        # 3. Draw paths between chapters
        path_color = (100, 80, 50)        # Brown for locked paths
        unlocked_path_color = (200, 160, 100)  # Light gold for unlocked paths
        
        for i in range(len(chapter_positions) - 1):
            # Skip the path to bonus chapter if not the last main chapter
            if i == 4:  # Path from Chapter 5 to Bonus
                if current_chapter_index >= 4:  # Only show if Chapter 5 is unlocked
                    color = unlocked_path_color if current_chapter_index >= 5 else path_color
                    pygame.draw.line(self.screen, color, chapter_positions[i], chapter_positions[i+1], 4)
            else:  # Regular chapter paths
                color = unlocked_path_color if i < current_chapter_index else path_color
                pygame.draw.line(self.screen, color, chapter_positions[i], chapter_positions[i+1], 4)

        # 4. Draw chapter icons and player cursor
        # Load images directly from file paths
        locked_icon = self.asset_manager.load_image('images/ui/chapter_icon_locked.png', key='chapter_icon_locked')
        unlocked_icon = self.asset_manager.load_image('images/ui/chapter_icon_unlocked.png', key='chapter_icon_unlocked')
        player_cursor = self.asset_manager.load_image('images/ui/player_map_cursor.png', key='player_map_cursor')
        
        # Create fallback icons if needed
        if not locked_icon:
            locked_icon = self._create_fallback_icon_surface((40, 40), "?", (80, 80, 80))
        if not unlocked_icon:
            unlocked_icon = self._create_fallback_icon_surface((40, 40), "!", (200, 200, 100))
        if not player_cursor:
            player_cursor = self._create_fallback_icon_surface((50, 50), "X", (0, 200, 200))

        # Chapter names
        chapter_names = ["Chapter 1", "Chapter 2", "Chapter 3", "Chapter 4", "Chapter 5", "Bonus"]
        # Use a font size that's already loaded
        font = self.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 24)
        
        for i, pos in enumerate(chapter_positions):
            # Determine if this chapter is unlocked
            is_unlocked = i <= current_chapter_index
            
            # Draw the appropriate icon
            icon_to_draw = unlocked_icon if is_unlocked else locked_icon
            if icon_to_draw:
                rect = icon_to_draw.get_rect(center=pos)
                self.screen.blit(icon_to_draw, rect)
            
            # Draw chapter name
            name_color = WHITE if is_unlocked else GREY
            name_surf = font.render(chapter_names[i], True, name_color)
            name_pos = (pos[0], pos[1] + 40)  # Position below the icon
            self.screen.blit(name_surf, name_surf.get_rect(center=name_pos))
            
            # Draw player cursor on current chapter
            if i == current_chapter_index and player_cursor:
                cursor_rect = player_cursor.get_rect(center=(pos[0], pos[1] - 30))  # Position above the icon
                self.screen.blit(player_cursor, cursor_rect)
        
        # Display chapter title and description in top left
        if current_chapter:
            # Draw chapter title
            chapter_title_surf = self._render_text_safe(current_chapter.title, "medium_text", GOLD, fallback_size=36)
            self.screen.blit(chapter_title_surf, (20, 20))
            
            # Draw chapter description
            desc_font = self.asset_manager.get_font("ui_text", 28) or pygame.font.Font(None, 28)
            wrapped_desc = self._wrap_text_with_font_obj(current_chapter.description, desc_font, width/2 - 40)
            for i, line in enumerate(wrapped_desc):
                desc_surf = desc_font.render(line, True, WHITE)
                self.screen.blit(desc_surf, (20, 60 + i * 30))
            
            # Draw objectives as bullet points
            obj_y = 60 + len(wrapped_desc) * 30 + 10
            obj_font = self.asset_manager.get_font("ui_text", 24) or pygame.font.Font(None, 24)
            
            for obj in current_chapter.objectives:
                obj_color = GREEN if obj.is_complete else WHITE
                obj_text = f"• {obj.description}"
                obj_surf = obj_font.render(obj_text, True, obj_color)
                self.screen.blit(obj_surf, (30, obj_y))
                obj_y += 30
        
        # Draw instruction at bottom
        instruction = "Press SPACE or ENTER to continue"
        # Use a font size that's already loaded (28 instead of 24)
        instruction_surf = self._render_text_safe(instruction, "ui_text", CYAN, fallback_size=28)
        self.screen.blit(instruction_surf, instruction_surf.get_rect(center=(width // 2, height - 30)))

    def draw_architect_vault_hud_elements(self):
        title_surf = self._render_text_safe("Architect's Vault", "large_text", GOLD, fallback_size=48)
        width = get_setting("display", "WIDTH", 1920)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 50)))

    def draw_game_intro_scroll(self):
        ui_flow = self.game_controller.ui_flow_controller
        if not ui_flow.intro_screens_data or ui_flow.current_intro_screen_index >= len(ui_flow.intro_screens_data):
            return

        current_screen_data = ui_flow.intro_screens_data[ui_flow.current_intro_screen_index]
        image_key = current_screen_data.get("image_path_key")
        text = current_screen_data.get("text", "")
        
        screen_width = get_setting("display", "WIDTH", 1920)
        screen_height = get_setting("display", "HEIGHT", 1080)

        if image_key:
            bg_image = self.asset_manager.get_image(image_key)
            if bg_image:
                bg_surf = pygame.transform.scale(bg_image, (screen_width, screen_height))
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
        font = self.asset_manager.get_font("ui_text", 28) or pygame.font.Font(None, 28)
        text_surf = font.render(message, True, CYAN)
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        bg_rect = text_surf.get_rect(center=(width // 2, height - 150))
        bg_rect.inflate_ip(40, 20)
        
        bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        bg_surface.fill((30, 30, 30, 180))
        self.screen.blit(bg_surface, bg_rect.topleft)
        pygame.draw.rect(self.screen, CYAN, bg_rect, 1)
        self.screen.blit(text_surf, text_surf.get_rect(center=bg_rect.center))

    def draw_codex_screen(self):
        ui_flow = self.game_controller.ui_flow_controller
        font_title = self.asset_manager.get_font("large_text", 52)
        font_cat = self.asset_manager.get_font("medium_text", 36)
        font_entry = self.asset_manager.get_font("ui_text", 28)
        font_content = self.asset_manager.get_font("ui_text", 24)
        
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        title_surf = font_title.render("CODEX", True, GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width / 2, 60)))
        
        if ui_flow.codex_current_view == "categories":
            start_y = 150
            for i, cat_name in enumerate(ui_flow.codex_categories_list):
                color = YELLOW if i == ui_flow.codex_selected_category_index else WHITE
                cat_surf = font_cat.render(cat_name, True, color)
                self.screen.blit(cat_surf, cat_surf.get_rect(center=(width/2, start_y + i * 50)))
        
        elif ui_flow.codex_current_view == "entries":
            cat_title_surf = font_cat.render(f"Category: {ui_flow.codex_current_category_name}", True, CYAN)
            self.screen.blit(cat_title_surf, cat_title_surf.get_rect(center=(width/2, 140)))
            start_y = 220
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

    def draw_main_menu(self):
        if self.ui_asset_surfaces["menu_background"]:
            logo_surf = self.ui_asset_surfaces["menu_background"]
            screen_width = get_setting("display", "WIDTH", 1920)
            screen_height = get_setting("display", "HEIGHT", 1080)
            scaled_bg_surf = pygame.transform.scale(logo_surf, (screen_width, screen_height))
            self.screen.blit(scaled_bg_surf, (0, 0))

        ui_flow_ctrl = self.game_controller.ui_flow_controller
        if ui_flow_ctrl and hasattr(ui_flow_ctrl, 'menu_stars') and ui_flow_ctrl.menu_stars:
            for star_params in ui_flow_ctrl.menu_stars:
                pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

        options, selected_index = ui_flow_ctrl.menu_options, ui_flow_ctrl.selected_menu_option
        height = get_setting("display", "HEIGHT", 1080)
        start_y, option_height = height * 0.55, 60
        font_menu = self.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)

        for i, option_text in enumerate(options):
            color = GOLD if i == selected_index else WHITE
            text_surf = font_menu.render(option_text, True, color)
            width = get_setting("display", "WIDTH", 1920)
            text_rect = text_surf.get_rect(center=(width // 2, start_y + i * option_height))
            self.screen.blit(text_surf, text_rect)

    def draw_drone_select_menu(self):
        title_surf = self._render_text_safe("Select Drone", "large_text", GOLD, fallback_size=48)
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 80)))
        
        ui_flow = self.game_controller.ui_flow_controller
        if not ui_flow.drone_select_options: return

        selected_drone_id = ui_flow.drone_select_options[ui_flow.selected_drone_preview_index]
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        is_unlocked = self.drone_system.is_drone_unlocked(selected_drone_id)

        sprite_asset_key = drone_config.get("sprite_path", "").replace("assets/","")
        sprite_surf = self.asset_manager.get_image(sprite_asset_key, scale_to_size=(256, 256))
        if sprite_surf: self.screen.blit(sprite_surf, sprite_surf.get_rect(center=(width/2, height/2 - 100)))

        name_surf = self._render_text_safe(drone_config.get("name"), "medium_text", WHITE if is_unlocked else GREY, fallback_size=48)
        self.screen.blit(name_surf, name_surf.get_rect(center=(width/2, height/2 + 100)))
        
        desc_surf = self._render_text_safe(drone_config.get("description"), "ui_text", CYAN, fallback_size=24)
        self.screen.blit(desc_surf, desc_surf.get_rect(center=(width/2, height/2 + 150)))
        
        if not is_unlocked:
            unlock_cond = drone_config.get("unlock_condition", {})
            unlock_desc = unlock_cond.get("description", "Locked")
            unlock_surf = self._render_text_safe(unlock_desc, "ui_text", RED, fallback_size=28)
            self.screen.blit(unlock_surf, unlock_surf.get_rect(center=(width/2, height/2 + 200)))

    def draw_gameplay_hud(self):
        player = self.game_controller.player
        if not player: return
        panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        height = get_setting("display", "HEIGHT", 1080)
        width = get_setting("display", "WIDTH", 1920)
        panel_y = height - panel_height
        panel_bg_color = (*DARK_GREY[:3], 220)
        panel_surface = pygame.Surface((width, panel_height), pygame.SRCALPHA)
        panel_surface.fill(panel_bg_color)
        self.screen.blit(panel_surface, (0, panel_y))
        pygame.draw.line(self.screen, CYAN, (0, panel_y), (width, panel_y), 2)
        font_ui, font_small = self.asset_manager.get_font("ui_text", 28), self.asset_manager.get_font("ui_text", 24)
        
        # Left side - Weapon and lives
        wpn_x, wpn_y = 30, panel_y + 20
        icon_height = 0
        
        weapon_icon = self.ui_asset_surfaces.get("current_weapon_icon")
        if weapon_icon:
            rotated_icon = pygame.transform.rotate(weapon_icon, 90)
            icon_width, icon_height = rotated_icon.get_size()
            
            # Removed weapon label
            
            self.screen.blit(rotated_icon, (wpn_x, wpn_y))
            
            # Display lives as multiple weapon mode icons to the right of the weapon bar
            if self.game_controller.lives > 0:
                icon_spacing = 10
                lives_start_x = wpn_x + icon_width + 20
                
                actual_lives = self.game_controller.lives - 1

                for i in range(actual_lives):
                    icon_x = lives_start_x + (i * (icon_width + icon_spacing))
                    self.screen.blit(rotated_icon, (icon_x, panel_y + 20))
        
        # Weapon cooldown bar
        wpn_mode = player.current_weapon_mode
        from constants import WEAPON_MODE_NAMES
        wpn_name = WEAPON_MODE_NAMES.get(wpn_mode, "N/A")
        
        self.update_weapon_icon_surface(wpn_mode)
        
        icon_surf = self.ui_asset_surfaces.get("current_weapon_icon")
        if icon_surf:
            rotated_icon = pygame.transform.rotate(icon_surf, 90)
            icon_width, icon_height = rotated_icon.get_size()
            icon_rect = pygame.Rect(wpn_x, wpn_y, icon_width, icon_height)
            text_x = icon_rect.right + 15
            cooldown_bar_y = wpn_y + icon_height + 10
            # Extend weapon bar to the left of the screen
            time_since = pygame.time.get_ticks() - player.last_shot_time
            progress = min(1.0, time_since / player.current_shoot_cooldown) if player.current_shoot_cooldown > 0 else 1.0
            cooldown_width = 200
            pygame.draw.rect(self.screen, DARK_GREY, (wpn_x, cooldown_bar_y, cooldown_width, 10))
            pygame.draw.rect(self.screen, YELLOW, (wpn_x, cooldown_bar_y, cooldown_width * progress, 10))
            pygame.draw.rect(self.screen, WHITE, (wpn_x, cooldown_bar_y, cooldown_width, 10), 1)

        # Right side - Rings and fragments
        hud_ring_icon_area_x_offset = get_setting("display", "HUD_RING_ICON_AREA_X_OFFSET", 150)
        hud_ring_icon_area_y_offset = get_setting("display", "HUD_RING_ICON_AREA_Y_OFFSET", 30)
        hud_ring_icon_size = get_setting("display", "HUD_RING_ICON_SIZE", 24)
        hud_ring_icon_spacing = get_setting("display", "HUD_RING_ICON_SPACING", 5)
        
        rings_x = width - hud_ring_icon_area_x_offset
        rings_y = panel_y + hud_ring_icon_area_y_offset
        frags_x = width - 150
        frags_y = panel_y + 65
        
        current_game_state = self.state_manager.get_current_state_id() if self.state_manager else None
        if current_game_state == "PlayingState":
            ring_icon, ring_empty = self.ui_asset_surfaces.get("ring_icon"), self.ui_asset_surfaces.get("ring_icon_empty")
            if ring_icon and ring_empty:
                for i in range(self.game_controller.level_manager.total_rings_per_level): 
                    show_filled = i < self.game_controller.level_manager.displayed_collected_rings_count
                    icon_x = rings_x + i * (hud_ring_icon_size + hud_ring_icon_spacing)
                    self.screen.blit(ring_icon if show_filled else ring_empty, (icon_x, rings_y))
        
        core_fragment_details = settings_manager.get_core_fragment_details()
        collected = self.drone_system.get_collected_fragments_ids()
        required = sorted([d['id'] for d in core_fragment_details.values() if d.get('required_for_vault')])
        animating_ids = [anim['fragment_id'] for anim in self.game_controller.animating_fragments_to_hud]

        for i, frag_id in enumerate(required):
            show_filled_icon = (frag_id in collected) and (frag_id not in animating_ids)
            icon = self.ui_asset_surfaces["core_fragment_icons"].get(frag_id) if show_filled_icon else self.ui_asset_surfaces["core_fragment_empty_icon"]
            if icon: self.screen.blit(icon, (frags_x + i * (self.ui_icon_size_fragments[0] + 5), frags_y))

    def get_scaled_fragment_icon_surface(self, fragment_id):
        # First check if it's a level fragment (fragment_level_1, etc.)
        if fragment_id.startswith("fragment_level_"):
            level_num = fragment_id.split("_")[-1]
            # Try to find the corresponding alpha, beta, gamma fragment based on level
            if level_num == "1":
                fragment_id = "alpha"
            elif level_num == "2":
                fragment_id = "beta"
            elif level_num == "3":
                fragment_id = "gamma"
        
        icon_surface = self.ui_asset_surfaces["core_fragment_icons"].get(fragment_id)
        if icon_surface: 
            return icon_surface
        
        # Try loading directly from asset manager
        if fragment_id in ["alpha", "beta", "gamma"]:
            direct_key = f"images/collectibles/core_fragment_{fragment_id}.png"
            icon_surface = self.asset_manager.get_image(direct_key, scale_to_size=self.ui_icon_size_fragments)
            if icon_surface:
                # Cache it for future use
                self.ui_asset_surfaces["core_fragment_icons"][fragment_id] = icon_surface
                return icon_surface
        
        logger.warning(f"UIManager: Scaled icon surface for fragment_id '{fragment_id}' not found. Using fallback.")
        return self._create_fallback_icon_surface(self.ui_icon_size_fragments, "?", PURPLE)

    def draw_settings_menu(self):
        title_surf = self._render_text_safe("Settings", "large_text", GOLD, fallback_size=48)
        width = get_setting("display", "WIDTH", 1920)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 80)))
        
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
            self.screen.blit(val_surf, (width - 200 - val_surf.get_width(), y_pos))

    def draw_leaderboard_overlay(self):
        title_surf = self._render_text_safe("Leaderboard", "large_text", GOLD, fallback_size=48)
        width = get_setting("display", "WIDTH", 1920)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 80)))
        
        scores = self.game_controller.ui_flow_controller.leaderboard_scores
        font_header = self.asset_manager.get_font("medium_text", 36)
        font_score = self.asset_manager.get_font("ui_text", 28)
        
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
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        overlay = pygame.Surface((width, height), pygame.SRCALPHA); overlay.fill((50, 0, 0, 180))
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
            font = self.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
            
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
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        title_surf = self._render_text_safe("Vault Conquered", "large_text", GOLD, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, height//2)))

    def draw_architect_vault_failure_overlay(self):
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        title_surf = self._render_text_safe("Mission Failed", "large_text", RED, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, height//2)))

    def draw_maze_defense_hud(self):
        width = get_setting("display", "WIDTH", 1920)
        title_surf = self._render_text_safe("Maze Defense", "large_text", CYAN, fallback_size=48)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 50)))

    def draw_pause_overlay(self):
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        pause_text = self._render_text_safe("PAUSED", "title_text", WHITE, fallback_size=90)
        self.screen.blit(pause_text, pause_text.get_rect(center=(width//2, height//2)))