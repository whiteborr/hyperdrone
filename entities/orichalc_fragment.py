# entities/orichalc_fragment.py
import pygame.sprite
import pygame.transform
from pygame import Surface, SRCALPHA
from math import sin
from constants import GOLD

class OrichalcFragment(pygame.sprite.Sprite):
    def __init__(self, x, y, *, asset_manager):
        super().__init__()
        self.center_x, self.center_y = float(x), float(y)
        fragment_size = 32
        self.original_icon = asset_manager.get_image("ORICHALC_FRAGMENT_ICON")
        if self.original_icon:
            self.original_icon = pygame.transform.scale(self.original_icon, (fragment_size, fragment_size))
        self.collected = False
        self.rotation_angle = 0
        self.pulse_time = 0
        self.image = Surface((fragment_size + 10, fragment_size + 10), SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self._render_fragment()
        
    def _render_fragment(self):
        self.image.fill((0, 0, 0, 0))
        if self.original_icon:
            # Rotate icon
            rotated_icon = pygame.transform.rotate(self.original_icon, self.rotation_angle)
            # Pulse scale
            pulse_scale = 1.0 + 0.1 * sin(self.pulse_time)
            if pulse_scale != 1.0:
                size = rotated_icon.get_size()
                new_size = (int(size[0] * pulse_scale), int(size[1] * pulse_scale))
                rotated_icon = pygame.transform.scale(rotated_icon, new_size)
            # Center on surface
            icon_rect = rotated_icon.get_rect(center=self.image.get_rect().center)
            self.image.blit(rotated_icon, icon_rect)
        
    def update(self):
        if self.collected:
            return True
        # Update rotation and pulse
        self.rotation_angle = (self.rotation_angle + 0.3) % 360
        self.pulse_time += 0.1
        self._render_fragment()
        return False
        
    def draw(self, surface, camera=None):
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            surface.blit(self.image, screen_rect)
        else:
            surface.blit(self.image, self.rect)
        
    def apply_effect(self, player_drone, game_controller_instance):
        if not self.collected:
            self.collected = True
            # Add 1 core to player
            if hasattr(game_controller_instance, 'drone_system'):
                game_controller_instance.drone_system.add_player_cores(1)
            # Play collection sound
            if hasattr(game_controller_instance, 'play_sound'):
                game_controller_instance.play_sound('collect_fragment')
            return True
        return False
    

    
    def start_pickup_animation(self, hud_container):
        """Create an energy particle that flies to the HUD container"""
        from entities.energy_particle import EnergyParticle
        target_pos = hud_container.get_position()
        return EnergyParticle(self.center_x, self.center_y, target_pos[0], target_pos[1])