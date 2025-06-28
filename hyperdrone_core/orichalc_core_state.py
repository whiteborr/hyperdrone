# hyperdrone_core/orichalc_core_state.py
from pygame import KEYDOWN, KEYUP, K_p, K_ESCAPE, K_1, K_2, K_3, USEREVENT
from pygame.sprite import Group
from pygame.time import get_ticks, set_timer
from pygame.font import Font
from .state import State
from entities import PlayerDrone, Enemy, ParticleSystem, Turret
from entities.elemental_core import ElementalCore
from constants import GAME_STATE_STORY_MAP

class OrichalcCoreState(State):
    def __init__(self, game):
        super().__init__(game)
        self.player = None
        self.orichalc_core = None
        self.enemies = Group()
        self.turrets = Group()
        self.particles = ParticleSystem()
        
        # State flags
        self.core_collected = False
        self.defense_phase = True
        self.final_choice_made = False
        
        # Wave management
        self.wave_count = 0
        self.spawn_timer = 0
        self.choice_timer = 0
        
    def enter(self, previous_state=None, **kwargs):
        # Initialize player
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        self.player = PlayerDrone(
            400, 500, drone_id, drone_stats,
            self.game.asset_manager, "drone_default", "crash", self.game.drone_system
        )
        
        # Create Orichalc core
        self.orichalc_core = ElementalCore(400, 300, "orichalc", self.game.asset_manager)
        
        # Create defensive turrets
        self._create_turrets()
        
    def _create_turrets(self):
        positions = [(200, 200), (600, 200), (200, 400), (600, 400)]
        for x, y in positions:
            turret = Turret(x, y, self.game.asset_manager)
            self.turrets.add(turret)
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    self.game.paused = not self.game.paused
                elif event.key == K_ESCAPE:
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                elif not self.defense_phase and not self.final_choice_made:
                    # Handle final choice
                    choices = {K_1: "preserve", K_2: "erase", K_3: "merge"}
                    if event.key in choices:
                        self._make_choice(choices[event.key])
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
        
        # Update based on phase
        if self.defense_phase:
            self._update_defense_phase(current_time, delta_time)
        elif not self.final_choice_made:
            self._update_choice_phase(delta_time)
        
        # Update entities
        if hasattr(self.player, 'update'):
            self.player.update(current_time, None, self.enemies, self.game.player_actions, 0)
        
        if hasattr(self.game, 'player_actions'):
            self.game.player_actions.update_player_movement_and_actions(current_time)
        
        self.particles.update(delta_time)
    
    def _update_defense_phase(self, current_time, delta_time):
        # Spawn waves
        self.spawn_timer += delta_time
        if self.spawn_timer > 3000:
            self._spawn_defense_wave()
            self.spawn_timer = 0
        
        # Update entities
        for enemy in self.enemies:
            if hasattr(enemy, 'update'):
                enemy.update(None, current_time, delta_time, 0)
        
        for turret in self.turrets:
            if hasattr(turret, 'update'):
                turret.update(current_time, self.enemies)
        
        # Handle combat
        self._handle_combat()
        
        # Check phase completion
        if self.wave_count >= 5 and len(self.enemies) == 0:
            self.defense_phase = False
            self.game.set_story_message("The Architect's voice returns: 'Would you let it die... or evolve?'", 5000)
    
    def _update_choice_phase(self, delta_time):
        self.choice_timer += delta_time
        self.orichalc_core.update(delta_time)
    
    def _spawn_defense_wave(self):
        self.wave_count += 1
        enemies_count = 4 + self.wave_count
        
        positions = [
            (50, 100), (750, 100), (50, 500), (750, 500),
            (400, 50), (100, 300), (700, 300)
        ]
        
        for i in range(min(enemies_count, len(positions))):
            x, y = positions[i]
            config = {
                "health": 20 + (self.wave_count * 5),
                "speed": 1.5 + (self.wave_count * 0.2),
                "damage": 15
            }
            enemy = Enemy(x, y, self.game.asset_manager, config)
            self.enemies.add(enemy)
    
    def _handle_combat(self):
        # Player vs enemies
        if hasattr(self.player, 'bullets_group'):
            for bullet in list(self.player.bullets_group):
                for enemy in list(self.enemies):
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.health -= bullet.damage
                        bullet.kill()
                        self.particles.create_explosion(
                            bullet.rect.centerx, bullet.rect.centery,
                            (255, 200, 0), 10
                        )
                        if enemy.health <= 0:
                            enemy.kill()
                        break
        
        # Turrets vs enemies
        for turret in self.turrets:
            if hasattr(turret, 'bullets_group'):
                for bullet in list(turret.bullets_group):
                    for enemy in list(self.enemies):
                        if bullet.rect.colliderect(enemy.rect):
                            enemy.health -= bullet.damage
                            bullet.kill()
                            if enemy.health <= 0:
                                enemy.kill()
                            break
        
        # Enemies vs player and turrets
        for enemy in self.enemies:
            if hasattr(enemy, 'bullets_group'):
                for bullet in list(enemy.bullets_group):
                    # Check player collision
                    if bullet.rect.colliderect(self.player.rect):
                        self.player.take_damage(bullet.damage)
                        bullet.kill()
                        continue
                    
                    # Check turret collisions
                    for turret in self.turrets:
                        if bullet.rect.colliderect(turret.rect):
                            turret.take_damage(bullet.damage)
                            bullet.kill()
                            break
    
    def _make_choice(self, choice):
        self.final_choice_made = True
        
        messages = {
            "preserve": "You stabilize the Orichalc Core. The Vault enters dormancy, but its hunger remains...",
            "erase": "The Vault is destroyed. Earth is free, but now exposed to the Guardians...",
            "merge": "You merge with the Vault. Earth becomes your domain to protect and shape..."
        }
        
        self.game.set_story_message(messages[choice], 5000)
        self.game.drone_system.architect_vault_completed = True
        
        # Return to story map after delay
        set_timer(USEREVENT + 4, 6000)
    
    def draw(self, surface):
        surface.fill((60, 40, 80))
        
        # Draw entities
        self.player.draw(surface)
        
        for enemy in self.enemies:
            enemy.draw(surface)
        
        for turret in self.turrets:
            turret.draw(surface)
        
        self.orichalc_core.draw(surface, (0, 0))
        self.particles.draw(surface, (0, 0))
        
        # Draw UI
        self._draw_ui(surface)
    
    def _draw_ui(self, surface):
        font = Font(None, 24)
        
        if self.defense_phase:
            text = font.render(f"Defend the Core - Wave: {self.wave_count}/5", True, (255, 255, 255))
            surface.blit(text, (10, 10))
        elif not self.final_choice_made:
            # Draw choice options
            font_large = Font(None, 36)
            title = font_large.render("Choose the Vault's Fate:", True, (255, 255, 255))
            surface.blit(title, (250, 100))
            
            choices = [
                "1 - Preserve: Stabilize the Vault",
                "2 - Erase: Destroy the Vault", 
                "3 - Merge: Become the new Architect"
            ]
            
            for i, choice in enumerate(choices):
                text = font.render(choice, True, (200, 200, 200))
                surface.blit(text, (200, 150 + i * 30))
    
    def exit(self, next_state=None):
        pass