# hyperdrone_core/water_core_state.py
import pygame
from .state import State
from entities import PlayerDrone, Enemy, ParticleSystem
from entities.elemental_core import ElementalCore
from constants import GAME_STATE_STORY_MAP

class WaterCoreState(State):
    def __init__(self, game):
        super().__init__(game)
        self.player = None
        self.water_core = None
        self.enemies = pygame.sprite.Group()
        self.particles = ParticleSystem()
        self.core_collected = False
        self.scroll_offset = 0
        self.wave_count = 0
        self.spawn_timer = 0
        self.wreckage_pieces = []
        
    def enter(self, previous_state=None, **kwargs):
        # Initialize player at top
        start_pos = (400, 50)
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        self.player = PlayerDrone(
            start_pos[0], start_pos[1], drone_id, drone_stats,
            self.game.asset_manager, "drone_default", "crash", self.game.drone_system
        )
        
        # Create water core at bottom
        self.water_core = ElementalCore(400, 800, "water", self.game.asset_manager)
        
        # Create wreckage pieces for atmosphere
        self._create_wreckage()
        
    def _create_wreckage(self):
        # Create visual wreckage pieces (non-interactive)
        for i in range(15):
            x = 50 + (i * 50) % 700
            y = 200 + (i * 80)
            self.wreckage_pieces.append({
                'rect': pygame.Rect(x, y, 30, 20),
                'color': (100, 100, 120)
            })
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.paused = not self.game.paused
                elif event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                else:
                    if hasattr(self.game, 'player_actions'):
                        self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                if hasattr(self.game, 'player_actions'):
                    self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        if self.game.paused:
            return
            
        current_time = pygame.time.get_ticks()
        
        # Vertical scrolling effect
        self.scroll_offset += 1
        
        # Spawn enemy waves
        self.spawn_timer += delta_time
        if self.spawn_timer > 2000:  # Every 2 seconds
            self._spawn_enemy_wave()
            self.spawn_timer = 0
        
        # Update player
        if hasattr(self.player, 'update'):
            self.player.update(current_time, None, self.enemies, self.game.player_actions, 0)
        
        # Update player actions
        if hasattr(self.game, 'player_actions'):
            self.game.player_actions.update_player_movement_and_actions(current_time)
        
        # Update enemies
        for enemy in self.enemies:
            if hasattr(enemy, 'update'):
                enemy.update(None, current_time, delta_time, 0)
                # Move enemies down for vertical scrolling effect
                enemy.rect.y += 2
                # Remove enemies that go off screen
                if enemy.rect.y > 900:
                    enemy.kill()
        
        # Update water core
        self.water_core.update(delta_time)
        
        # Check for core collection
        if hasattr(self.player, 'rect') and hasattr(self.water_core, 'rect'):
            if self.player.rect.colliderect(self.water_core.rect):
                self._collect_water_core()
        
        # Update particles
        self.particles.update(delta_time)
        
        # Handle combat
        self._handle_combat()
    
    def _spawn_enemy_wave(self):
        self.wave_count += 1
        enemies_in_wave = min(3 + self.wave_count, 8)
        
        for i in range(enemies_in_wave):
            x = 100 + (i * 100) % 600
            y = -50  # Spawn above screen
            enemy_config = {
                "health": 1,  # One-shot kills for SHMUP style
                "speed": 2 + (self.wave_count * 0.3),
                "damage": 10
            }
            enemy = Enemy(x, y, self.game.asset_manager, enemy_config)
            self.enemies.add(enemy)
    
    def _handle_combat(self):
        # Player bullets vs enemies
        if hasattr(self.player, 'bullets_group'):
            for bullet in self.player.bullets_group:
                for enemy in self.enemies:
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.health = 0
                        bullet.kill()
                        enemy.kill()
                        self.particles.create_explosion(
                            enemy.rect.centerx, enemy.rect.centery,
                            (0, 150, 255), 12
                        )
        
        # Enemy bullets vs player
        for enemy in self.enemies:
            if hasattr(enemy, 'bullets_group'):
                for bullet in enemy.bullets_group:
                    if bullet.rect.colliderect(self.player.rect):
                        self.player.take_damage(bullet.damage)
                        bullet.kill()
    
    def _collect_water_core(self):
        if not self.core_collected:
            self.core_collected = True
            self.game.drone_system.collect_core_fragment("water")
            self.game.set_story_message("Water Core collected! Hidden memories flow through your circuits.", 3000)
            
            # Return to story map
            pygame.time.set_timer(pygame.USEREVENT + 3, 2000)
    
    def draw(self, surface):
        surface.fill((10, 30, 60))  # Deep blue water background
        
        # Draw wreckage pieces
        for piece in self.wreckage_pieces:
            pygame.draw.rect(surface, piece['color'], piece['rect'])
        
        # Draw player
        self.player.draw(surface)
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(surface)
        
        # Draw water core
        self.water_core.draw(surface, (0, 0))
        
        # Draw particles
        self.particles.draw(surface, (0, 0))
        
        # Draw water effect overlay
        water_surface = pygame.Surface((surface.get_width(), surface.get_height()))
        water_surface.set_alpha(20)
        water_surface.fill((0, 100, 200))
        surface.blit(water_surface, (0, 0))
        
        # Draw wave counter
        font = pygame.font.Font(None, 24)
        text = font.render(f"Wave: {self.wave_count}", True, (255, 255, 255))
        surface.blit(text, (10, 10))
    
    def exit(self, next_state=None):
        pass