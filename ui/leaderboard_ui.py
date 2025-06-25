# ui/leaderboard_ui.py
import pygame
from pygame import Surface, Rect, draw, font
from pygame.time import get_ticks
from math import sin, cos
from json import load, dump, JSONDecodeError
from os.path import join, dirname, exists
from os import makedirs
from logging import getLogger

from constants import CYAN, GOLD, GREEN, RED, WHITE, GREY
from settings_manager import get_setting

logger = getLogger(__name__)
DATA_DIR = "data"

def _ensure_data_dir_exists():
    if not exists(DATA_DIR):
        try:
            makedirs(DATA_DIR)
            logger.info(f"Created data directory at '{DATA_DIR}'")
        except OSError as e:
            logger.error(f"Error creating data directory '{DATA_DIR}': {e}")
            return False
    return True

def load_scores():
    from constants import KEY_LEADERBOARD_NAME, KEY_LEADERBOARD_SCORE, KEY_LEADERBOARD_LEVEL
    if not _ensure_data_dir_exists():
        return []
    current_leaderboard_path = join(DATA_DIR, get_setting("progression", "LEADERBOARD_FILE_NAME", "leaderboard.json"))
    if not exists(current_leaderboard_path):
        return []
    try:
        with open(current_leaderboard_path, 'r') as f:
            scores = load(f)
            if not isinstance(scores, list):
                return []
            scores.sort(key=lambda x: (-int(x.get(KEY_LEADERBOARD_SCORE, 0)), -int(x.get(KEY_LEADERBOARD_LEVEL, 0)), str(x.get(KEY_LEADERBOARD_NAME, 'ZZZ'))))
            return scores
    except (IOError, JSONDecodeError):
        return []

def save_scores(scores):
    if not _ensure_data_dir_exists():
        return
    current_leaderboard_path = join(DATA_DIR, get_setting("progression", "LEADERBOARD_FILE_NAME", "leaderboard.json"))
    try:
        scores.sort(key=lambda x: (-int(x.get('score', 0)), -int(x.get('level', 0)), str(x.get('name', 'ZZZ'))))
        with open(current_leaderboard_path, 'w') as f:
            dump(scores, f, indent=4)
    except IOError:
        pass

def add_score(name, score, level):
    from constants import KEY_LEADERBOARD_NAME, KEY_LEADERBOARD_SCORE, KEY_LEADERBOARD_LEVEL
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        return False
    try:
        current_score = int(score)
        current_level = int(level)
    except ValueError:
        return False
    scores = load_scores()
    new_score_entry = {
        KEY_LEADERBOARD_NAME: name.strip().upper()[:6],
        KEY_LEADERBOARD_SCORE: current_score,
        KEY_LEADERBOARD_LEVEL: current_level
    }
    max_entries = get_setting("progression", "LEADERBOARD_MAX_ENTRIES", 10)
    should_add = len(scores) < max_entries
    if not should_add and scores:
        lowest_score = int(scores[-1].get(KEY_LEADERBOARD_SCORE, 0))
        lowest_level = int(scores[-1].get(KEY_LEADERBOARD_LEVEL, 0))
        should_add = current_score > lowest_score or (current_score == lowest_score and current_level > lowest_level)
    if should_add:
        scores.append(new_score_entry)
        scores.sort(key=lambda x: (-int(x.get(KEY_LEADERBOARD_SCORE, 0)), -int(x.get(KEY_LEADERBOARD_LEVEL, 0)), str(x.get(KEY_LEADERBOARD_NAME, 'ZZZ'))))
        scores = scores[:max_entries]
        save_scores(scores)
        return True
    return False

def get_top_scores():
    return load_scores()

def is_high_score(score, level):
    from constants import KEY_LEADERBOARD_SCORE, KEY_LEADERBOARD_LEVEL
    try:
        check_score = int(score)
        check_level = int(level)
    except ValueError:
        return False
    scores = load_scores()
    max_entries = get_setting("progression", "LEADERBOARD_MAX_ENTRIES", 10)
    if len(scores) < max_entries or not scores:
        return True
    lowest_score = int(scores[-1].get(KEY_LEADERBOARD_SCORE, 0))
    lowest_level = int(scores[-1].get(KEY_LEADERBOARD_LEVEL, 0))
    return check_score > lowest_score or (check_score == lowest_score and check_level > lowest_level)

class LeaderboardUI:
    def __init__(self):
        font_path = join(dirname(dirname(__file__)), "assets", "fonts", "neuropol.otf")
        self.font_title = font.Font(font_path, 40)
        self.font_subtitle = font.Font(font_path, 28)
        self.font_entry = font.Font(font_path, 24)
        self.font_small = font.Font(font_path, 18)
        self.scanline_offset = 0
        self.scanline_alpha = 50
        
        from hyperdrone_core.asset_manager import AssetManager
        self.asset_manager = AssetManager()

    def draw(self, screen):
        width, height = screen.get_size()
        self._draw_background(screen)

        board_width = 1000
        board_height = 650
        board_x = (width - board_width) // 2
        board_y = (height - board_height) // 2

        self._draw_main_frame(screen, board_x, board_y, board_width, board_height)
        self._draw_title(screen, "HIGH SCORES", board_x + board_width // 2 - 120, board_y + 30)
        self._draw_scores(screen, board_x + 80, board_y + 120)
        self._draw_instructions(screen, board_x, board_y, board_width, board_height)
        self._draw_scanlines(screen)

    def _draw_background(self, screen):
        width, height = screen.get_size()
        overlay = Surface((width, height), pygame.SRCALPHA)
        time_factor = get_ticks() * 0.001
        bg_alpha = int(200 + 30 * sin(time_factor))
        overlay.fill((5, 15, 35, bg_alpha))

        grid_offset = int(get_ticks() * 0.02) % 50
        for x in range(-grid_offset, width + 50, 50):
            a = int(60 + 40 * sin(time_factor + x * 0.01))
            draw.line(overlay, (20, 60, 120, a), (x, 0), (x, height))
        for y in range(-grid_offset, height + 50, 50):
            a = int(60 + 40 * cos(time_factor + y * 0.01))
            draw.line(overlay, (20, 60, 120, a), (0, y), (width, y))
        screen.blit(overlay, (0, 0))

    def _draw_main_frame(self, screen, x, y, width, height):
        # Animated main background
        panel_surface = Surface((width, height), pygame.SRCALPHA)
        time_factor = get_ticks() * 0.002
        bg_alpha = int(220 + 20 * sin(time_factor))
        panel_surface.fill((20, 35, 60, bg_alpha))
        screen.blit(panel_surface, (x, y))
        
        # Animated border glow
        border_alpha = int(120 + 80 * sin(time_factor * 2))
        draw.rect(screen, (0, 200, 255, border_alpha), (x-1, y-1, width+2, height+2), 3, border_radius=12)
        draw.rect(screen, (0, 255, 255, 150), (x, y, width, height), 2, border_radius=10)
        
        # Enhanced corner details with glow
        corner_size = 40
        glow_alpha = int(150 + 100 * sin(time_factor * 3))
        
        # Top-left corner
        draw.line(screen, (*GOLD, glow_alpha), (x-2, y + corner_size), (x-2, y-2), 5)
        draw.line(screen, (*GOLD, glow_alpha), (x-2, y-2), (x + corner_size, y-2), 5)
        draw.line(screen, GOLD, (x, y + corner_size), (x, y), 3)
        draw.line(screen, GOLD, (x, y), (x + corner_size, y), 3)
        
        # Top-right corner
        draw.line(screen, (*GOLD, glow_alpha), (x + width - corner_size, y-2), (x + width+2, y-2), 5)
        draw.line(screen, (*GOLD, glow_alpha), (x + width+2, y-2), (x + width+2, y + corner_size), 5)
        draw.line(screen, GOLD, (x + width - corner_size, y), (x + width, y), 3)
        draw.line(screen, GOLD, (x + width, y), (x + width, y + corner_size), 3)

        # Bottom-left corner
        draw.line(screen, (*GOLD, glow_alpha), (x-2, y + height - corner_size), (x-2, y + height+2), 5)
        draw.line(screen, (*GOLD, glow_alpha), (x-2, y + height+2), (x + corner_size, y + height+2), 5)
        draw.line(screen, GOLD, (x, y + height - corner_size), (x, y + height), 3)
        draw.line(screen, GOLD, (x, y + height), (x + corner_size, y + height), 3)
        
        # Bottom-right corner
        draw.line(screen, (*GOLD, glow_alpha), (x + width - corner_size, y + height+2), (x + width+2, y + height+2), 5)
        draw.line(screen, (*GOLD, glow_alpha), (x + width+2, y + height+2), (x + width+2, y + height - corner_size), 5)
        draw.line(screen, GOLD, (x + width - corner_size, y + height), (x + width, y + height), 3)
        draw.line(screen, GOLD, (x + width, y + height), (x + width, y + height - corner_size), 3)

    def _draw_title(self, screen, text, x, y):
        self._draw_text_with_shadow(screen, text, self.font_title, GOLD, (x, y))

    def _draw_scores(self, screen, start_x, start_y):
        scores = get_top_scores()
        if not scores:
            self._draw_text_with_shadow(screen, "No scores yet!", self.font_subtitle, GREY, 
                                        (start_x + 300, start_y + 200))
            return
            
        # Enhanced score display with ranking highlights
        for i, entry in enumerate(scores[:10]):
            name = entry.get("name", "???")
            score = entry.get("score", 0)
            level = entry.get("level", 0)
            
            y_pos = start_y + i * 45
            
            # Rank-based styling
            if i == 0:  # 1st place
                color = GOLD
                rank_bg_color = (*GOLD, 60)
                glow_alpha = int(80 + 40 * sin(get_ticks() * 0.005 + i))
                # Gold glow for 1st place
                glow_surf = Surface((800, 40), pygame.SRCALPHA)
                glow_surf.fill((*GOLD, glow_alpha))
                screen.blit(glow_surf, (start_x - 20, y_pos - 5))
            elif i < 3:  # Top 3
                color = CYAN
                rank_bg_color = (*CYAN, 40)
            else:
                color = WHITE
                rank_bg_color = (*WHITE, 20)
            
            # Background highlight for each entry
            bg_surf = Surface((800, 35), pygame.SRCALPHA)
            bg_surf.fill(rank_bg_color)
            screen.blit(bg_surf, (start_x - 10, y_pos - 2))
            
            # Rank number with special styling
            rank_text = f"{i+1:2}."
            self._draw_text_with_shadow(screen, rank_text, self.font_entry, color, (start_x, y_pos))
            
            # Player name
            self._draw_text_with_shadow(screen, name, self.font_entry, color, (start_x + 60, y_pos))
            
            # Score with formatting
            score_text = f"SCORE: {score:,}"
            self._draw_text_with_shadow(screen, score_text, self.font_entry, color, (start_x + 200, y_pos))
            
            # Level
            level_text = f"LVL: {level}"
            self._draw_text_with_shadow(screen, level_text, self.font_entry, color, (start_x + 450, y_pos))
            
            # Special trophy icon for 1st place
            if i == 0:
                trophy_image = self.asset_manager.get_image("TROPHY_ICON")
                if trophy_image:
                    screen.blit(trophy_image, (start_x + 570, y_pos))

    def _draw_text_with_shadow(self, screen, text, font_obj, color, pos, shadow_color=(0, 0, 0), offset=(2, 2)):
        """Helper to draw text with a drop shadow."""
        text_surf = font_obj.render(text, True, shadow_color)
        screen.blit(text_surf, (pos[0] + offset[0], pos[1] + offset[1]))
        text_surf = font_obj.render(text, True, color)
        screen.blit(text_surf, pos)

    def _draw_scanlines(self, screen):
        width, height = screen.get_size()
        scanline_surface = Surface((width, height), pygame.SRCALPHA)
        
        self.scanline_offset = (self.scanline_offset + 0.5) % 6
        time_factor = get_ticks() * 0.001
        
        # Variable intensity scanlines
        for y in range(int(self.scanline_offset), height, 6):
            alpha = int(self.scanline_alpha + 20 * sin(time_factor + y * 0.1))
            alpha = max(10, min(80, alpha))
            draw.line(scanline_surface, (0, 20, 40, alpha), (0, y), (width, y), 1)
            
        # Occasional bright scanline
        bright_line_y = int((get_ticks() * 0.1) % height)
        draw.line(scanline_surface, (0, 100, 200, 60), (0, bright_line_y), (width, bright_line_y), 2)
            
        screen.blit(scanline_surface, (0, 0))
        
    def _draw_instructions(self, screen, board_x, board_y, board_width, board_height):
        """Draw control instructions at the bottom."""
        instructions = "Press [ESC] to return to Main Menu"
        self._draw_text_with_shadow(screen, instructions, self.font_small, WHITE,
                                    (board_x + board_width // 2 - 150, board_y + board_height - 50))