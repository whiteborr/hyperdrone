# hyperdrone_core/fire_core_state.py
from pygame import KEYDOWN, KEYUP, K_p, K_ESCAPE, USEREVENT
from pygame.sprite import Group
from pygame.time import get_ticks, set_timer
from pygame.font import Font
from .state import State
from entities import PlayerDrone, MazeGuardian, ParticleSystem
from entities.elemental_core import ElementalCore
from constants import GAME_STATE_STORY_MAP

class FireCoreState(State):
    def __init__(self, game):
        super().__init__(game)
        self.player = None
        self.maze_guardian = None
        self.fire_core = None
        self.particles = ParticleSystem()
        self.core_collected = False
        self.boss_defeated = False
        
    def enter(self, previous_state=None, **kwargs):
        # Initialize player
        start_pos = (400, 500)
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        self.player = PlayerDrone(
            start_pos[0], start_pos[1], drone_id, drone_stats,
            self.game.asset_manager, "drone_default", "crash", self.game.drone_system
        )
        
        # Create boss
        boss_pos = (400, 200)
        self.maze_guardian = MazeGuardian(
            boss_pos[0], boss_pos[1], self.player, None, None, self.game.asset_manager
        )
        
        # Create fire core (hidden until boss defeated)
        self.fire_core = ElementalCore(400, 150, "fire", self.game.asset_manager)
        self.fire_core.visible = False
        
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    self.game.paused = not self.game.paused
                elif event.key == K_ESCAPE:
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                else:
                    if hasattr(self.game, 'player_actions'):
                        self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
                if hasattr(self.game, 'player_actions'):
                    self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        if self.game.paused:
            return
            
        current_time = get_ticks()
        
        # Update player
        if hasattr(self.player, 'update'):
            self.player.update(current_time, None, Group(), self.game.player_actions, 0)
        
        # Update player actions
        if hasattr(self.game, 'player_actions'):
            self.game.player_actions.update_player_movement_and_actions(current_time)
        
        # Update boss if not defeated
        if not self.boss_defeated and self.maze_guardian:
            self.maze_guardian.update(None, None, current_time, delta_time, 0)
            
            # Check if boss is defeated
            if not self.maze_guardian.alive:
                self.boss_defeated = True
                self.fire_core.visible = True
                self.particles.create_explosion(
                    self.maze_guardian.rect.centerx, 
                    self.maze_guardian.rect.centery,
                    (255, 100, 0), 30
                )
        
        # Update fire core
        if self.fire_core.visible:
            self.fire_core.update(delta_time)
            
            # Check for core collection
            if hasattr(self.player, 'rect') and hasattr(self.fire_core, 'rect'):
                if self.player.rect.colliderect(self.fire_core.rect):
                    self._collect_fire_core()
        
        # Update particles
        self.particles.update(delta_time)
        
        # Handle combat
        if not self.boss_defeated:
            self._handle_combat()
    
    def _handle_combat(self):
        # Player bullets vs boss
        if hasattr(self.player, 'bullets_group'):
            for bullet in self.player.bullets_group:
                if bullet.rect.colliderect(self.maze_guardian.rect):
                    self.maze_guardian.take_damage(bullet.damage)
                    bullet.kill()
                    self.particles.create_explosion(
                        bullet.rect.centerx, bullet.rect.centery,
                        (255, 255, 0), 10
                    )
        
        # Boss bullets vs player
        if hasattr(self.maze_guardian, 'bullets_group'):
            for bullet in self.maze_guardian.bullets_group:
                if bullet.rect.colliderect(self.player.rect):
                    self.player.take_damage(bullet.damage)
                    bullet.kill()
    
    def _collect_fire_core(self):
        if not self.core_collected:
            self.core_collected = True
            self.game.drone_system.collect_core_fragment("fire")
            self.game.set_story_message("Fire Core collected! Raw power courses through your systems.", 3000)
            
            # Return to story map
            set_timer(USEREVENT + 1, 2000)
    
    def draw(self, surface):
        surface.fill((20, 20, 40))  # Dark blue background
        
        # Draw player
        self.player.draw(surface)
        
        # Draw boss if not defeated
        if not self.boss_defeated and self.maze_guardian:
            self.maze_guardian.draw(surface)
        
        # Draw fire core if visible
        if self.fire_core.visible:
            self.fire_core.draw(surface, (0, 0))
        
        # Draw particles
        self.particles.draw(surface, (0, 0))
        
        # Draw UI
        if self.boss_defeated and not self.core_collected:
            font = Font(None, 36)
            text = font.render("Collect the Fire Core!", True, (255, 255, 255))
            surface.blit(text, (300, 50))
    
    def exit(self, next_state=None):
        pass