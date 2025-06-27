# ui/leaderboard_ui.py
from pygame import Surface, SRCALPHA
from pygame.time import get_ticks
from math import sin
from json import load, dump, JSONDecodeError
from os.path import join, exists
from os import makedirs
from logging import getLogger

from constants import CYAN, GOLD, WHITE, GREY
from settings_manager import get_setting
from .ui_common import UICommon

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
        fonts = UICommon.load_fonts()
        self.font_title = fonts['title']
        self.font_subtitle = fonts['subtitle']
        self.font_entry = fonts['ui']
        self.font_small = fonts['small']
        
        from hyperdrone_core.asset_manager import AssetManager
        self.asset_manager = AssetManager()

    def draw(self, screen):
        width, height = screen.get_size()
        UICommon.draw_background(screen)

        board_width = 780
        board_height = 650
        board_x = (width - board_width) // 2
        board_y = (height - board_height) // 2

        UICommon.draw_main_frame(screen, board_x, board_y, board_width, board_height)
        self._draw_title(screen, "HIGH SCORES", board_x + board_width // 2 - 100, board_y + 30)
        self._draw_scores(screen, board_x + 60, board_y + 120)
        self._draw_instructions(screen, board_x, board_y, board_width, board_height)
        UICommon.draw_scanlines(screen)

    def _draw_title(self, screen, text, x, y):
        UICommon.draw_text_with_shadow(screen, text, self.font_title, GOLD, (x, y))

    def _draw_scores(self, screen, start_x, start_y):
        scores = get_top_scores()
        if not scores:
            UICommon.draw_text_with_shadow(screen, "No scores yet!", self.font_subtitle, GREY,
                                           (start_x + 200, start_y + 200))
            return

        row_height = 45
        row_width = 680
        name_col = 60
        score_col = 200
        level_col = 490
        trophy_col = 620

        for i, entry in enumerate(scores[:10]):
            name = entry.get("name", "???")
            score = entry.get("score", 0)
            level = entry.get("level", 0)
            y_pos = start_y + i * row_height

            # Highlight color
            if i == 0:
                color = GOLD
                glow_alpha = int(80 + 40 * sin(get_ticks() * 0.005 + i))
                glow_surf = Surface((row_width, 40), SRCALPHA)
                glow_surf.fill((*GOLD, glow_alpha))
                screen.blit(glow_surf, (start_x - 10, y_pos - 5))
            elif i < 3:
                color = CYAN
            else:
                color = WHITE

            # Background
            bg_color = (*color, 25 if i >= 3 else 50)
            bg_surf = Surface((row_width, 35), SRCALPHA)
            bg_surf.fill(bg_color)
            screen.blit(bg_surf, (start_x - 5, y_pos - 2))

            UICommon.draw_text_with_shadow(screen, f"{i+1:2}.", self.font_entry, color, (start_x, y_pos))
            UICommon.draw_text_with_shadow(screen, name, self.font_entry, color, (start_x + name_col, y_pos))
            UICommon.draw_text_with_shadow(screen, f"SCORE: {score:,}", self.font_entry, color, (start_x + score_col, y_pos))
            UICommon.draw_text_with_shadow(screen, f"LVL: {level}", self.font_entry, color, (start_x + level_col, y_pos))

            trophy = None
            if i == 0:
                trophy = self.asset_manager.get_image("TROPHY_ICON_GOLD")
            elif i == 1:
                trophy = self.asset_manager.get_image("TROPHY_ICON_SILVER")
            elif i == 2:
                trophy = self.asset_manager.get_image("TROPHY_ICON_BRONZE")
            if trophy:
                screen.blit(trophy, (start_x + trophy_col, y_pos))

    def _draw_instructions(self, screen, board_x, board_y, board_width, board_height):
        instructions = "Press [ESC] to return to Main Menu"
        text_width, _ = self.font_small.size(instructions)
        x = board_x + (board_width - text_width) // 2
        y = board_y + board_height + 20 
        UICommon.draw_text_with_shadow(screen, instructions, self.font_small, WHITE, (x, y))

        