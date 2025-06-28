# ui/ui.py
from os.path import exists
from math import ceil
from random import random
from logging import getLogger, warning, error

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

class UIManager:
    def __init__(self, screen, asset_manager, game_controller_ref, scene_manager_ref, drone_system_ref):
        self.screen = screen
        self.asset_manager = asset_manager
        self.game_controller = game_controller_ref 
        self.scene_manager = scene_manager_ref
        self.drone_system = drone_system_ref
        
        # Cache settings
        self._cached_width = get_setting("display", "WIDTH", 1920)
        self._cached_height = get_setting("display", "HEIGHT", 1080)
        
        # UI assets
        self.ui_asset_surfaces = {
            "ring_icon": None, "ring_icon_empty": None, "menu_background": None,
            "current_drone_life_icon": None, "core_fragment_icons": {},
            "core_fragment_empty_icon": None, "reactor_icon_placeholder": None,
            "ability_icon_placeholder": None
        }
        
        # Icon sizes
        self.ui_icon_size_lives = (48, 48)
        self.ui_icon_size_rings = (20, 20)
        self.ui_icon_size_fragments = (28, 28)
        self.ui_icon_size_reactor = (32, 32)
        ability_size = get_setting("display", "HUD_ABILITY_ICON_SIZE", 60)
        self.ui_icon_size_ability = (ability_size, ability_size)

        # Codex settings
        self.codex_list_item_height = 0
        self.codex_max_visible_items_list = 0
        self.codex_max_visible_lines_content = 0

        # Instruction settings
        self.BOTTOM_INSTRUCTION_CENTER_Y = self._cached_height - 50
        self.SECONDARY_INSTRUCTION_CENTER_Y = self._cached_height - 80
        self.INSTRUCTION_TEXT_COLOR = CYAN
        self.INSTRUCTION_BG_COLOR = (30, 30, 30, 150)
        self.INSTRUCTION_PADDING_X = 20
        self.INSTRUCTION_PADDING_Y = 10

        # Initialize UI components
        self.build_menu = BuildMenu(self.game_controller, self, self.asset_manager) if BuildMenu else None
        self.leaderboard_ui = LeaderboardUI() if LeaderboardUI else None
        self.settings_ui = SettingsUI(self.asset_manager) if SettingsUI else None

        # Load assets
        self._load_ui_assets()
        self.update_player_life_icon_surface()

    def _load_ui_assets(self):
        # Ring icons
        self.ui_asset_surfaces["ring_icon"] = (
            self.asset_manager.get_image("ring_ui_icon", scale_to_size=self.ui_icon_size_rings) or
            self._create_fallback_icon(self.ui_icon_size_rings, "O", GOLD)
        )
        
        self.ui_asset_surfaces["ring_icon_empty"] = (
            self.asset_manager.get_image("ring_ui_icon_empty", scale_to_size=self.ui_icon_size_rings) or
            self._create_fallback_icon(self.ui_icon_size_rings, "O", GREY)
        )

        # Menu background
        self.ui_asset_surfaces["menu_background"] = self.asset_manager.get_image("menu_logo_hyperdrone")

        # Core fragment icons
        self.ui_asset_surfaces["core_fragment_empty_icon"] = (
            self.asset_manager.get_image("core_fragment_empty_icon", scale_to_size=self.ui_icon_size_fragments) or
            self._create_fallback_icon(self.ui_icon_size_fragments, "F", DARK_GREY, GREY)
        )

        self._load_fragment_icons()

        # Reactor icon
        self.ui_asset_surfaces["reactor_icon_placeholder"] = (
            self.asset_manager.get_image("reactor_hud_icon_key", scale_to_size=self.ui_icon_size_reactor) or
            self._create_fallback_icon(self.ui_icon_size_reactor, "R", (50, 50, 200))
        )

        # Ability icon
        self.ui_asset_surfaces["ability_icon_placeholder"] = (
            self.asset_manager.get_image("ability_icon_placeholder", scale_to_size=self.ui_icon_size_ability) or
            self._create_fallback_icon(self.ui_icon_size_ability, "A", (100, 200, 255))
        )

    def _load_fragment_icons(self):
        fragment_details = settings_manager.get_core_fragment_details()
        if not fragment_details:
            return
            
        for _, details in fragment_details.items():
            frag_id = details.get("id")
            if not frag_id:
                continue
                
            # Try icon_filename first, then fallback to old pattern
            icon = None
            if "icon_filename" in details:
                icon = self.asset_manager.get_image(details["icon_filename"], scale_to_size=self.ui_icon_size_fragments)
            
            if not icon:
                asset_key = f"{frag_id}_icon"
                icon = self.asset_manager.get_image(asset_key, scale_to_size=self.ui_icon_size_fragments)
            
            if icon:
                self.ui_asset_surfaces["core_fragment_icons"][frag_id] = icon
            else:
                warning(f"Core fragment icon for ID '{frag_id}' not found")
                self.ui_asset_surfaces["core_fragment_icons"][frag_id] = self._create_fallback_icon(
                    self.ui_icon_size_fragments, frag_id[:1] if frag_id else "!", PURPLE
                )

    def update_player_life_icon_surface(self):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        life_icon_key = f"drone_{selected_drone_id}_hud_icon"
        icon = self.asset_manager.get_image(life_icon_key, scale_to_size=self.ui_icon_size_lives)
        
        if icon:
            self.ui_asset_surfaces["current_drone_life_icon"] = rotate(icon, 90)
        else:
            warning(f"Life icon for drone '{selected_drone_id}' not found")
            self.ui_asset_surfaces["current_drone_life_icon"] = self._create_fallback_icon(
                self.ui_icon_size_lives, "L", CYAN
            )
            
    def update_weapon_icon_surface(self, weapon_mode):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        weapon_key = f"{selected_drone_id}_WEAPON_{weapon_mode}"
        icon = self.asset_manager.get_image(weapon_key, scale_to_size=(64, 64))
        
        if not icon:
            icon = self.asset_manager.get_image("weapon_upgrade_powerup_icon", scale_to_size=(64, 64))
            
        if icon:
            self.ui_asset_surfaces["current_weapon_icon"] = icon
        else:
            warning(f"Weapon icon for drone '{selected_drone_id}' mode '{weapon_mode}' not found")
            self.ui_asset_surfaces["current_weapon_icon"] = self._create_fallback_icon((64, 64), "W", CYAN)

    def _create_fallback_icon(self, size=(30, 30), text="?", color=GREY, text_color=WHITE, font_key="ui_text"):
        surface = Surface(size, SRCALPHA)
        surface.fill(color)
        draw_rect(surface, WHITE, surface.get_rect(), 1)
        
        font = self.asset_manager.get_font(font_key, max(10, size[1]-4)) or Font(None, max(10, size[1]-4))
        if text and font:
            try:
                text_surf = font.render(text, True, text_color)
                surface.blit(text_surf, text_surf.get_rect(center=(size[0] // 2, size[1] // 2)))
            except Exception as e:
                error(f"Error rendering fallback icon text '{text}': {e}")
        return surface

    def _render_text_safe(self, text, font_key, color, fallback_size=24):
        font = self.asset_manager.get_font(font_key, fallback_size) or Font(None, fallback_size)
        try:
            return font.render(str(text), True, color)
        except Exception as e:
            error(f"Error rendering text '{text}': {e}")
            return Font(None, fallback_size).render("ERR", True, RED)

    def _wrap_text(self, text, font_key, size, max_width):
        font = self.asset_manager.get_font(font_key, size) or Font(None, size)
        return self._wrap_text_with_font(text, font, max_width)

    def _wrap_text_with_font(self, text, font, max_width):
        if not font:
            return [text]
            
        words = text.split(' ')
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        
        if current_line:
            lines.append(current_line.strip())
        return lines

    def _draw_star_background(self):
        ui_flow = self.game_controller.ui_flow_controller
        if ui_flow and hasattr(ui_flow, 'menu_stars') and ui_flow.menu_stars:
            for star in ui_flow.menu_stars:
                circle(self.screen, WHITE, (int(star[0]), int(star[1])), star[3])

    def draw_current_scene_ui(self, player_active_abilities_data=None):
        if not hasattr(self, 'state_manager') or not self.state_manager:
            return
            
        current_state = self.state_manager.get_current_state_id() if self.state_manager else None
        
        menu_states = [
            "MainMenuState", "DroneSelectState", "SettingsState", "LeaderboardState", 
            "CodexState", "ArchitectVaultSuccessState", "ArchitectVaultFailureState",
            "GameOverState", "EnterNameState", "StoryMapState", "NarrativeState"
        ]
        
        if current_state in menu_states:
            self.screen.fill(BLACK)

        # State drawing map
        state_handlers = {
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

        if current_state in state_handlers:
            state_handlers[current_state]()
        elif current_state and current_state.startswith("ArchitectVault"):
            self.draw_architect_vault_hud_elements()
            if self.game_controller.paused:
                self.draw_pause_overlay()
        elif current_state in ["PlayingState", "BonusLevelPlayingState", "EarthCoreState", "FireCoreState", "AirCoreState", "WaterCoreState", "OrichalcCoreState"]:
            self.draw_gameplay_hud(player_active_abilities_data)
            if self.game_controller.paused:
                self.draw_pause_overlay()
        elif current_state == "MazeDefenseState":
            self.draw_maze_defense_hud()
            if self.game_controller.paused:
                self.draw_pause_overlay()
            if (self.build_menu and self.build_menu.is_active and 
                hasattr(self.game_controller, 'is_build_phase') and self.game_controller.is_build_phase):
                self.build_menu.draw(self.screen)
        elif current_state == "RingPuzzleState":
            if not (self.game_controller.puzzle_controller and 
                    self.game_controller.puzzle_controller.ring_puzzle_active_flag):
                self.screen.fill(DARK_GREY)
                loading_text = self._render_text_safe("Loading Puzzle...", "medium_text", WHITE, 48)
                self.screen.blit(loading_text, loading_text.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))

        # Draw story message overlay
        if (hasattr(self.game_controller, 'story_message_active') and 
            self.game_controller.story_message_active and
            hasattr(self.game_controller, 'story_message') and 
            self.game_controller.story_message and
            current_state != "game_intro_scroll"):
            self.draw_story_message_overlay(self.game_controller.story_message)
    
    def draw_story_map(self):
        self._draw_star_background()
        width, height = self._cached_width, self._cached_height
        
        # Background
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
        
        # Title
        title = self._render_text_safe("Story Map", "large_text", GOLD, 48)
        self.screen.blit(title, title.get_rect(center=(width // 2, 100)))
        
        # Chapter map
        self._draw_chapter_map_line(width, height)
        
        # Chapter details
        current_state = self.state_manager.get_current_state() if self.state_manager else None
        show_details = not (
            (hasattr(current_state, 'showing_completion_summary') and current_state.showing_completion_summary) or
            (hasattr(current_state, 'animating_to_next_chapter') and current_state.animating_to_next_chapter)
        )
            
        if show_details:
            self._draw_current_chapter_details(width)
        
        # Instructions
        animation_complete = (hasattr(current_state, 'animating_to_next_chapter') and 
                            not current_state.animating_to_next_chapter and 
                            hasattr(current_state, 'animation_timer'))
        
        if show_details or animation_complete:
            instruction = self._render_text_safe("Press SPACE or ENTER to continue", "ui_text", CYAN, 24)
            self.screen.blit(instruction, instruction.get_rect(center=(width // 2, height - 50)))

    def _draw_current_chapter_details(self, width):
        current_chapter = None
        if hasattr(self.game_controller, 'story_manager') and self.game_controller.story_manager:
            current_chapter = self.game_controller.story_manager.get_current_chapter()
        
        if not current_chapter:
            return
            
        # Chapter title
        title = self._render_text_safe(current_chapter.title, "ui_text", CYAN, 32)
        self.screen.blit(title, title.get_rect(center=(width // 2, 450)))
        
        # Description
        desc_font = self.asset_manager.get_font("ui_text", 24) or Font(None, 24)
        wrapped_desc = self._wrap_text_with_font(current_chapter.description, desc_font, width - 200)
        for i, line in enumerate(wrapped_desc):
            desc_surf = desc_font.render(line, True, WHITE)
            self.screen.blit(desc_surf, desc_surf.get_rect(center=(width // 2, 490 + i * 30)))
        
        # Objectives
        obj_y = 490 + len(wrapped_desc) * 30 + 50
        obj_font = self.asset_manager.get_font("ui_text", 24) or Font(None, 24)
        
        for obj in current_chapter.objectives:
            color = GREEN if obj.is_complete else WHITE
            obj_text = f"• {obj.description}"
            obj_surf = obj_font.render(obj_text, True, color)
            self.screen.blit(obj_surf, obj_surf.get_rect(center=(width // 2, obj_y)))
            obj_y += 30
    
    def _draw_chapter_map_line(self, width, height):
        # Load icons
        chapter_unlocked = (self.asset_manager.get_image("CHAPTER_ICON_UNLOCKED", scale_to_size=(64, 64)) or
                           self._create_fallback_icon((64, 64), "✓", GREEN))
        chapter_locked = (self.asset_manager.get_image("CHAPTER_ICON_LOCKED", scale_to_size=(64, 64)) or
                         self._create_fallback_icon((64, 64), "✗", GREY))
        player_cursor = (self.asset_manager.get_image("PLAYER_MAP_CURSOR", scale_to_size=(32, 32)) or
                        self._create_fallback_icon((32, 32), "►", GOLD))
        
        # Positions
        map_y = 250
        chapter_spacing = 150
        start_x = (width - (4 * chapter_spacing)) // 2
        
        # Get current chapter
        current_chapter_index = -1
        if hasattr(self.game_controller, 'story_manager') and self.game_controller.story_manager:
            current_chapter_index = self.game_controller.story_manager.current_chapter_index
        
        # Draw connecting line
        line_start_x = start_x + 32
        line_end_x = start_x + (4 * chapter_spacing) + 32
        draw_line(self.screen, WHITE, (line_start_x, map_y + 32), (line_end_x, map_y + 32), 3)
        
        # Draw chapters
        for i in range(5):
            chapter_x = start_x + (i * chapter_spacing)
            is_unlocked = i <= current_chapter_index
            icon = chapter_unlocked if is_unlocked else chapter_locked
            
            self.screen.blit(icon, (chapter_x, map_y))
            
            # Chapter number
            num_surf = self._render_text_safe(f"{i + 1}", "ui_text", WHITE, 24)
            self.screen.blit(num_surf, num_surf.get_rect(center=(chapter_x + 32, map_y + 80)))
        
        # Draw player cursor
        current_state = self.state_manager.get_current_state() if self.state_manager else None
        if (hasattr(current_state, 'animating_to_next_chapter') and 
            current_state.animating_to_next_chapter and 
            hasattr(current_state, 'current_animation_pos')):
            pos = current_state.current_animation_pos
            self.screen.blit(player_cursor, (int(pos.x), int(pos.y)))
        elif 0 <= current_chapter_index < 5:
            display_index = current_chapter_index
            if (hasattr(current_state, 'showing_completion_summary') and 
                current_state.showing_completion_summary):
                display_index = max(0, current_chapter_index - 1)
            
            cursor_x = start_x + (display_index * chapter_spacing) + 16
            cursor_y = map_y - 40
            self.screen.blit(player_cursor, (cursor_x, cursor_y))

    def draw_architect_vault_hud_elements(self):
        title = self._render_text_safe("Architect's Vault", "large_text", GOLD, 48)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, 50)))

    def draw_game_intro_scroll(self):
        self._draw_star_background()
        ui_flow = self.game_controller.ui_flow_controller
        
        if (not ui_flow.intro_screens_data or 
            ui_flow.current_intro_screen_index >= len(ui_flow.intro_screens_data)):
            return

        current_screen = ui_flow.intro_screens_data[ui_flow.current_intro_screen_index]
        image_key = current_screen.get("image_path_key")
        text = current_screen.get("text", "")
        
        # Background image
        if image_key:
            bg_image = self.asset_manager.get_image(image_key)
            if bg_image:
                bg_surf = scale(bg_image, (self._cached_width, self._cached_height))
                self.screen.blit(bg_surf, (0, 0))

        # Text
        lines = text.split('\n')
        font = self.asset_manager.get_font("medium_text", 36)
        start_y = self._cached_height - (len(lines) * 40) - 100

        for i, line in enumerate(lines):
            line_surf = font.render(line, True, WHITE)
            self.screen.blit(line_surf, line_surf.get_rect(center=(self._cached_width / 2, start_y + i * 40)))
            
        # Prompt
        prompt = self._render_text_safe("Press SPACE to continue...", "ui_text", GOLD, 28)
        self.screen.blit(prompt, prompt.get_rect(center=(self._cached_width / 2, self._cached_height - 50)))

    def draw_story_message_overlay(self, message):
        font = self.asset_manager.get_font("ui_text", 28) or Font(None, 28)
        text_surf = font.render(message, True, CYAN)
        
        bg_rect = text_surf.get_rect(center=(self._cached_width // 2, self._cached_height - 150))
        bg_rect.inflate_ip(40, 20)
        
        bg_surface = Surface(bg_rect.size, SRCALPHA)
        bg_surface.fill((30, 30, 30, 180))
        self.screen.blit(bg_surface, bg_rect.topleft)
        draw_rect(self.screen, CYAN, bg_rect, 1)
        self.screen.blit(text_surf, text_surf.get_rect(center=bg_rect.center))

    def draw_main_menu(self):
        # Background logo
        if self.ui_asset_surfaces["menu_background"]:
            logo = self.ui_asset_surfaces["menu_background"]
            scaled_bg = scale(logo, (self._cached_width, self._cached_height))
            self.screen.blit(scaled_bg, (0, 0))

        # Stars on top
        self._draw_star_background()

        # Menu options
        ui_flow = self.game_controller.ui_flow_controller
        options = ui_flow.menu_options
        selected = ui_flow.selected_menu_option
        
        start_y = self._cached_height * 0.55
        option_height = 60
        font = self.asset_manager.get_font("large_text", 48) or Font(None, 48)

        for i, option in enumerate(options):
            color = GOLD if i == selected else WHITE
            text_surf = font.render(option, True, color)
            text_rect = text_surf.get_rect(center=(self._cached_width // 2, start_y + i * option_height))
            self.screen.blit(text_surf, text_rect)

    def draw_drone_select_menu(self):
        self._draw_star_background()
        
        title = self._render_text_safe("Select Drone", "large_text", GOLD, 48)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, 70)))
        
        ui_flow = self.game_controller.ui_flow_controller
        drone_options = getattr(ui_flow, 'drone_select_options', [])
        selected_idx = getattr(ui_flow, 'selected_drone_preview_index', 0)
        
        if not drone_options:
            no_drones = self._render_text_safe("NO DRONES AVAILABLE", "large_text", RED, 48)
            self.screen.blit(no_drones, no_drones.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))
            return
        
        current_drone_id = drone_options[selected_idx]
        drone_config = self.drone_system.get_drone_config(current_drone_id)
        
        # Basic drone info display
        if drone_config:
            name_text = self._render_text_safe(drone_config.get('name', current_drone_id), "ui_text", WHITE, 32)
            self.screen.blit(name_text, name_text.get_rect(center=(self._cached_width // 2, 300)))
        
        # Basic drone info display
        if drone_config:
            name_text = self._render_text_safe(drone_config.get('name', current_drone_id), "ui_text", WHITE, 32)
            self.screen.blit(name_text, name_text.get_rect(center=(self._cached_width // 2, 300)))

    def draw_settings_menu(self):
        if self.settings_ui:
            self.settings_ui.draw(self.screen, self.game_controller.ui_flow_controller)
        else:
            self.screen.fill(BLACK)
            error_text = self._render_text_safe("Settings UI not available", "ui_text", RED, 32)
            self.screen.blit(error_text, error_text.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))

    def draw_leaderboard_ui(self):
        if self.leaderboard_ui:
            self.leaderboard_ui.draw(self.screen)
        else:
            self.screen.fill(BLACK)
            error_text = self._render_text_safe("Leaderboard UI not available", "ui_text", RED, 32)
            self.screen.blit(error_text, error_text.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))

    def draw_codex_screen(self):
        self.screen.fill(BLACK)
        title = self._render_text_safe("Lore Codex", "large_text", GOLD, 48)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, 60)))
        
        # Basic codex display
        info_text = self._render_text_safe("Codex functionality not implemented", "ui_text", WHITE, 24)
        self.screen.blit(info_text, info_text.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))

    def draw_game_over_overlay(self):
        overlay = Surface((self._cached_width, self._cached_height), SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        title = self._render_text_safe("GAME OVER", "large_text", RED, 64)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, self._cached_height // 2 - 100)))
        
        instructions = self._render_text_safe("Press R to restart, M for menu, or Q to quit", "ui_text", WHITE, 24)
        self.screen.blit(instructions, instructions.get_rect(center=(self._cached_width // 2, self._cached_height // 2 + 50)))

    def draw_enter_name_overlay(self):
        overlay = Surface((self._cached_width, self._cached_height), SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        title = self._render_text_safe("HIGH SCORE!", "large_text", GOLD, 48)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, self._cached_height // 2 - 100)))
        
        ui_flow = self.game_controller.ui_flow_controller
        name_input = getattr(ui_flow, 'player_name_input_cache', '')
        name_text = self._render_text_safe(f"Name: {name_input}_", "ui_text", WHITE, 32)
        self.screen.blit(name_text, name_text.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))

    def draw_architect_vault_success_overlay(self):
        overlay = Surface((self._cached_width, self._cached_height), SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        title = self._render_text_safe("VAULT CONQUERED", "large_text", GOLD, 48)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))

    def draw_architect_vault_failure_overlay(self):
        overlay = Surface((self._cached_width, self._cached_height), SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        title = self._render_text_safe("MISSION FAILED", "large_text", RED, 48)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))

    def draw_narrative_state(self):
        self.screen.fill(BLACK)
        title = self._render_text_safe("Narrative", "large_text", CYAN, 48)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, 100)))

    def draw_gameplay_hud(self, player_active_abilities_data=None):
        # Lives display with icon
        if hasattr(self.game_controller, 'lives') and self.ui_asset_surfaces["current_drone_life_icon"]:
            lives_icon = self.ui_asset_surfaces["current_drone_life_icon"]
            for i in range(self.game_controller.lives):
                self.screen.blit(lives_icon, (10 + i * 55, 10))
        
        # Score display
        if hasattr(self.game_controller, 'score'):
            score_text = self._render_text_safe(f"Score: {self.game_controller.score}", "ui_text", WHITE, 24)
            self.screen.blit(score_text, (10, 70))
        
        # Ring collection display
        if hasattr(self.game_controller, 'level_manager'):
            self._draw_ring_collection_hud()
        
        # Fragment display for Chapter 1
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            self._draw_fragment_hud()

    def _draw_ring_collection_hud(self):
        # Ring collection area
        width = self._cached_width
        height = self._cached_height
        bottom_panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        panel_y = height - bottom_panel_height
        
        rings_x = width - HUD_RING_ICON_AREA_X_OFFSET
        rings_y = panel_y + HUD_RING_ICON_AREA_Y_OFFSET
        
        # Draw collected rings
        collected = self.game_controller.level_manager.displayed_collected_rings_count
        total = self.game_controller.level_manager.total_rings_per_level
        
        for i in range(total):
            icon = self.ui_asset_surfaces["ring_icon"] if i < collected else self.ui_asset_surfaces["ring_icon_empty"]
            if icon:
                x = rings_x + i * (HUD_RING_ICON_SIZE + HUD_RING_ICON_SPACING)
                self.screen.blit(icon, (x, rings_y))

    def _draw_fragment_hud(self):
        # Fragment collection display
        width = self._cached_width
        height = self._cached_height
        bottom_panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        panel_y = height - bottom_panel_height
        
        frags_x = width - 150
        frags_y = panel_y + 65
        
        # Get required fragments for vault
        core_fragment_details = settings_manager.get_core_fragment_details()
        if core_fragment_details:
            required_fragments = [d for d in core_fragment_details.values() if d.get('required_for_vault')]
            
            for i, fragment_data in enumerate(required_fragments):
                fragment_id = fragment_data.get('id')
                if fragment_id:
                    # Check if collected
                    collected = hasattr(self.drone_system, 'has_core_fragment') and self.drone_system.has_core_fragment(fragment_id)
                    
                    # Get icon
                    if collected and fragment_id in self.ui_asset_surfaces["core_fragment_icons"]:
                        icon = self.ui_asset_surfaces["core_fragment_icons"][fragment_id]
                    else:
                        icon = self.ui_asset_surfaces["core_fragment_empty_icon"]
                    
                    if icon:
                        x = frags_x + i * (self.ui_icon_size_fragments[0] + 5)
                        self.screen.blit(icon, (x, frags_y))

    def draw_maze_defense_hud(self):
        title = self._render_text_safe("Maze Defense", "ui_text", CYAN, 32)
        self.screen.blit(title, (10, 10))

    def draw_pause_overlay(self):
        overlay = Surface((self._cached_width, self._cached_height), SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        title = self._render_text_safe("PAUSED", "large_text", WHITE, 64)
        self.screen.blit(title, title.get_rect(center=(self._cached_width // 2, self._cached_height // 2)))
        
        # Drone preview display
        if hasattr(self.game_controller, 'player') and self.game_controller.player:
            drone_id = self.game_controller.drone_system.get_selected_drone_id()
            drone_config = self.game_controller.drone_system.get_drone_config(drone_id)
            
            # Display current drone info
            drone_name = drone_config.get('name', drone_id)
            drone_text = self._render_text_safe(f"Current Drone: {drone_name}", "ui_text", CYAN, 24)
            self.screen.blit(drone_text, drone_text.get_rect(center=(self._cached_width // 2, self._cached_height // 2 + 100)))
            
            # Display weapon info
            weapon_mode = self.game_controller.player.current_weapon_mode
            weapon_names = get_setting("weapon_modes", "WEAPON_MODE_NAMES", {})
            weapon_name = weapon_names.get(str(weapon_mode), f"Mode {weapon_mode}")
            weapon_text = self._render_text_safe(f"Weapon: {weapon_name}", "ui_text", WHITE, 20)
            self.screen.blit(weapon_text, weapon_text.get_rect(center=(self._cached_width // 2, self._cached_height // 2 + 130)))
            
            # Display controls
            controls_text = self._render_text_safe("Press P to resume | TAB to cycle weapons", "ui_text", GREY, 18)
            self.screen.blit(controls_text, controls_text.get_rect(center=(self._cached_width // 2, self._cached_height // 2 + 160)))
    
    def get_scaled_fragment_icon_surface(self, fragment_id):
        """Get a scaled fragment icon surface for animations"""
        if fragment_id in self.ui_asset_surfaces["core_fragment_icons"]:
            return self.ui_asset_surfaces["core_fragment_icons"][fragment_id]
        return self.ui_asset_surfaces["core_fragment_empty_icon"]