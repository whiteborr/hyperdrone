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
        self.font_entry = font.Font(font_path, 24)
        self.font_small = font.Font(font_path, 18)
        self.scanline_offset = 0

    def draw(self, screen):
        width, height = screen.get_size()
        self._draw_background(screen)

        board_width = 800
        board_height = 600
        board_x = (width - board_width) // 2
        board_y = (height - board_height) // 2

        self._draw_main_frame(screen, board_x, board_y, board_width, board_height)
        self._draw_title(screen, "HIGH SCORES", board_x + 240, board_y + 20)
        self._draw_scores(screen, board_x + 60, board_y + 100)
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
        surf = Surface((width, height), pygame.SRCALPHA)
        alpha = int(220 + 20 * sin(get_ticks() * 0.002))
        surf.fill((20, 35, 60, alpha))
        screen.blit(surf, (x, y))

        draw.rect(screen, (0, 255, 255, 150), (x, y, width, height), 2, border_radius=12)

    def _draw_title(self, screen, text, x, y):
        self._draw_text_with_shadow(screen, text, self.font_title, GOLD, (x, y))

    def _draw_scores(self, screen, start_x, start_y):
        scores = get_top_scores()
        for i, entry in enumerate(scores[:10]):
            name = entry.get("name", "???")
            score = entry.get("score", 0)
            level = entry.get("level", 0)

            color = GREEN if i == 0 else CYAN if i < 3 else WHITE
            text = f"{i+1:2}. {name:6}  SCORE: {score:<6}  LVL: {level}"
            self._draw_text_with_shadow(screen, text, self.font_entry, color, (start_x, start_y + i * 40))

    def _draw_text_with_shadow(self, screen, text, font_obj, color, pos, shadow=(0, 0, 0), offset=(2, 2)):
        shadow_surf = font_obj.render(text, True, shadow)
        screen.blit(shadow_surf, (pos[0] + offset[0], pos[1] + offset[1]))
        text_surf = font_obj.render(text, True, color)
        screen.blit(text_surf, pos)

    def _draw_scanlines(self, screen):
        width, height = screen.get_size()
        overlay = Surface((width, height), pygame.SRCALPHA)
        self.scanline_offset = (self.scanline_offset + 0.5) % 6
        time_factor = get_ticks() * 0.001

        for y in range(int(self.scanline_offset), height, 6):
            alpha = int(40 + 20 * sin(time_factor + y * 0.1))
            draw.line(overlay, (0, 20, 40, alpha), (0, y), (width, y), 1)
        screen.blit(overlay, (0, 0))