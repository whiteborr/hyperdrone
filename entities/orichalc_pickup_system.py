# entities/orichalc_pickup_system.py
from pygame.sprite import Sprite, Group
from pygame.time import get_ticks, set_timer
from pygame.display import get_surface
from pygame import Surface, SRCALPHA, USEREVENT
from pygame.draw import circle, rect as draw_rect
from pygame.transform import scale
from math import sin, pi
from constants import GOLD, WHITE

class EnergyParticle(Sprite):
    """Particle that flies from fragment to container"""
    def __init__(self, start_pos, target_pos):
        super().__init__()
        self.start_pos = start_pos
        self.target_pos = target_pos
        self.start_time = get_ticks()
        self.duration = 800  # 0.8 seconds
        self.image = Surface((8, 8), SRCALPHA)
        circle(self.image, GOLD, (4, 4), 4)
        self.rect = self.image.get_rect(center=start_pos)
        
    def update(self):
        current_time = get_ticks()
        elapsed = current_time - self.start_time
        progress = min(1.0, elapsed / self.duration)
        
        if progress >= 1.0:
            self.kill()
            return True
            
        # Lerp position
        x = self.start_pos[0] + (self.target_pos[0] - self.start_pos[0]) * progress
        y = self.start_pos[1] + (self.target_pos[1] - self.start_pos[1]) * progress
        self.rect.center = (int(x), int(y))
        return False

class HUDContainer:
    """Manages the orichalc container display in HUD"""
    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self.container_icon = asset_manager.get_image("orichalc_fragment_container", scale_to_size=(100, 100))
        if not self.container_icon:
            # Fallback container
            self.container_icon = Surface((100, 100), SRCALPHA)
            draw_rect(self.container_icon, GOLD, (0, 0, 100, 100), 2)
            
        self.pulse_start_time = 0
        self.is_pulsing = False
        self._cached_position = None
        self._last_screen_size = None
        
    def get_position(self):
        """Get container position in bottom-right HUD with caching"""
        screen = get_surface()
        current_size = (screen.get_width(), screen.get_height())
        
        if self._cached_position is None or self._last_screen_size != current_size:
            self._last_screen_size = current_size
            self._cached_position = (current_size[0] - 200, current_size[1] - 60)
            
        return self._cached_position
        
    def trigger_pulse(self):
        """Start pulse animation"""
        self.pulse_start_time = get_ticks()
        self.is_pulsing = True
        
    def draw(self, surface, orichalc_count):
        pos = self.get_position()
        
        # Draw container with pulse effect
        if self.is_pulsing:
            elapsed = get_ticks() - self.pulse_start_time
            if elapsed < 300:  # 0.3 second pulse
                pulse_scale = 1.0 + 0.3 * sin(elapsed / 300 * pi * 4)
                size = (int(100 * pulse_scale), int(100 * pulse_scale))
                icon_to_draw = scale(self.container_icon, size)
                surface.blit(icon_to_draw, icon_to_draw.get_rect(center=pos))
            else:
                self.is_pulsing = False
                surface.blit(self.container_icon, self.container_icon.get_rect(center=pos))
        else:
            surface.blit(self.container_icon, self.container_icon.get_rect(center=pos))

class OrichalcPickupSystem:
    """Manages the complete orichalc fragment pickup animation"""
    def __init__(self, game_controller):
        self.game_controller = game_controller
        self.hud_container = HUDContainer(game_controller.asset_manager)
        self.energy_particles = Group()
        self.glowing_fragments = []
        
    def trigger_pickup(self, fragment_pos):
        """Start pickup animation sequence"""
        # Start glow effect
        glow_data = {
            'pos': fragment_pos,
            'start_time': get_ticks(),
            'glow_duration': 300  # 0.3 seconds
        }
        self.glowing_fragments.append(glow_data)
        
        # Create energy particle after glow
        set_timer(USEREVENT + 1, 300)  # Delay particle creation
        self._pending_particle_pos = fragment_pos
        
    def handle_event(self, event):
        """Handle delayed particle creation"""
        if event.type == USEREVENT + 1:
            set_timer(USEREVENT + 1, 0)  # Cancel timer
            target_pos = self.hud_container.get_position()
            particle = EnergyParticle(self._pending_particle_pos, target_pos)
            self.energy_particles.add(particle)
            
    def update(self):
        """Update all animations"""
        current_time = get_ticks()
        
        # Update glow effects - filter in place
        self.glowing_fragments = [glow for glow in self.glowing_fragments 
                                 if current_time - glow['start_time'] <= glow['glow_duration']]
                
        # Update particles and check for completion
        for particle in self.energy_particles:
            if particle.update():  # Particle reached target
                self.hud_container.trigger_pulse()
                self.game_controller.play_sound('collect_fragment')
                
    def draw(self, surface):
        """Draw all effects"""
        if not self.glowing_fragments and not self.energy_particles:
            return  # Early exit if nothing to draw
            
        current_time = get_ticks()
        
        # Draw glowing fragments
        for glow in self.glowing_fragments:
            elapsed = current_time - glow['start_time']
            progress = elapsed / glow['glow_duration']
            # Pulsing glow effect
            alpha = int(128 + 127 * sin(progress * pi * 6))
            glow_surface = Surface((40, 40), SRCALPHA)
            circle(glow_surface, (*GOLD, alpha), (20, 20), 20)
            surface.blit(glow_surface, (glow['pos'][0] - 20, glow['pos'][1] - 20))
                
        # Draw energy particles
        self.energy_particles.draw(surface)
        
    def draw_hud(self, surface):
        """Draw HUD container separately for better control"""
        current_state = self.game_controller.state_manager.get_current_state_id()
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if (current_state in ["PlayingState", "BonusLevelPlayingState"] and 
            current_chapter and current_chapter.chapter_id == "chapter_1"):
            orichalc_count = self.game_controller.drone_system.get_player_cores()
            self.hud_container.draw(surface, orichalc_count)
            
    def get_fragment_count(self):
        """Get current orichalc fragment count"""
        return self.game_controller.drone_system.get_player_cores()
        
    def spend_fragments(self, amount):
        """Spend orichalc fragments"""
        current_count = self.get_fragment_count()
        if current_count >= amount:
            new_count = current_count - amount
            self.game_controller.drone_system.set_player_cores(new_count)
            return True
        return False