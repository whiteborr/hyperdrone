# hyperdrone_core/camera.pyAdd commentMore actions
import pygame
from settings_manager import get_setting

class Camera:
    """
    Manages the game view, handling scrolling (panning) and zooming.
    """
    def __init__(self, map_width_pixels, map_height_pixels):
        self.offset = pygame.math.Vector2(0, 0)
        self.map_width = map_width_pixels
        self.map_height = map_height_pixels
        self.zoom_level = 1.0
        self.pan_speed = get_setting("display", "CAMERA_PAN_SPEED", 15)

    def apply_to_rect(self, rect):
        """Applies zoom and offset to a pygame.Rect for drawing."""
        zoomed_x = rect.x * self.zoom_level
        zoomed_y = rect.y * self.zoom_level
        zoomed_width = rect.width * self.zoom_level
        zoomed_height = rect.height * self.zoom_level
        
        screen_x = zoomed_x - self.offset.x
        screen_y = zoomed_y - self.offset.y
        
        return pygame.Rect(screen_x, screen_y, zoomed_width, zoomed_height)

    def apply_to_pos(self, pos):
        """Applies zoom and offset to a single (x, y) world position tuple."""
        zoomed_x = pos[0] * self.zoom_level
        zoomed_y = pos[1] * self.zoom_level
        
        screen_x = zoomed_x - self.offset.x
        screen_y = zoomed_y - self.offset.y
        
        return (screen_x, screen_y)

    def screen_to_world(self, screen_pos):
        """Converts screen coordinates (e.g., mouse position) to world coordinates."""
        world_x = (screen_pos[0] + self.offset.x) / self.zoom_level
        world_y = (screen_pos[1] + self.offset.y) / self.zoom_level
        return (world_x, world_y)

    def pan(self, dx, dy):
        """Moves the camera view by a given delta."""
        self.offset.x += dx * self.pan_speed
        self.offset.y += dy * self.pan_speed
        self.clamp_offset()

    def zoom(self, factor):
        """Adjusts the zoom level, keeping the view centered on the mouse."""
        mouse_pos_screen = pygame.mouse.get_pos()
        mouse_pos_world_before = self.screen_to_world(mouse_pos_screen)

        self.zoom_level *= factor
        min_zoom = get_setting("display", "MIN_ZOOM_LEVEL", 0.4)
        max_zoom = get_setting("display", "MAX_ZOOM_LEVEL", 1.5)
        self.zoom_level = max(min_zoom, min(self.zoom_level, max_zoom)) # Clamp zoom

        mouse_pos_world_after = self.screen_to_world(mouse_pos_screen)
        
        self.offset.x += (mouse_pos_world_before[0] - mouse_pos_world_after[0]) * self.zoom_level
        self.offset.y += (mouse_pos_world_before[1] - mouse_pos_world_after[1]) * self.zoom_level
        self.clamp_offset()

    def clamp_offset(self):
        """Ensures the camera doesn't scroll too far beyond the map edges."""
        screen_w, screen_h = pygame.display.get_surface().get_size()
        
        zoomed_map_width = self.map_width * self.zoom_level
        zoomed_map_height = self.map_height * self.zoom_level

        max_offset_x = max(0, zoomed_map_width - screen_w)
        max_offset_y = max(0, zoomed_map_height - screen_h)
        
        self.offset.x = max(0, min(self.offset.x, max_offset_x))
        self.offset.y = max(0, min(self.offset.y, max_offset_y))
