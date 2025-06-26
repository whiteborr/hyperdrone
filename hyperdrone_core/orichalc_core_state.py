# hyperdrone_core/orichalc_core_state.py
import pygame
from .state import State
from entities import PlayerDrone, Enemy, ParticleSystem, Turret
from entities.elemental_core import ElementalCore
from constants import GAME_STATE_STORY_MAP

class OrichalcCoreState(State):
    def __init__(self, game):
        super().__init__(game)
        self.player = None
        self.orichalc_core = None
        self.enemies = pygame.sprite.Group()
        self.turrets = pygame.sprite.Group()
        self.particles = ParticleSystem()
        self.core_collected = False
        self.defense_phase = True
        self.wave_count = 0
        self.spawn_timer = 0
        self.final_choice_made = False
        self.choice_timer = 0
        
    def enter(self, previous_state=None, **kwargs):
        # Initialize player
        start_pos = (400, 500)
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        self.player = PlayerDrone(
            start_pos[0], start_pos[1], drone_id, drone_stats,
            self.game.asset_manager, "drone_default", "crash", self.game.drone_system
        )
        
        # Create Orichalc core at center
        self.orichalc_core = ElementalCore(400, 300, "orichalc", self.game.asset_manager)
        
        # Create defensive turrets
        self._create_turrets()
        
    def _create_turrets(self):
        turret_positions = [
            (200, 200), (600, 200), (200, 400), (600, 400)
        ]
        for pos in turret_positions:
            turret = Turret(pos[0], pos[1], self.game.asset_manager)
            self.turrets.add(turret)
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.paused = not self.game.paused
                elif event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                elif not self.defense_phase and not self.final_choice_made:
                    # Final choice keys
                    if event.key == pygame.K_1:
                        self._make_choice("preserve")
                    elif event.key == pygame.K_2:
                        self._make_choice("erase")
                    elif event.key == pygame.K_3:
                        self._make_choice("merge")
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
        
        if self.defense_phase:
            self._update_defense_phase(current_time, delta_time)
        elif not self.final_choice_made:
            self._update_choice_phase(delta_time)
        
        # Update player
        if hasattr(self.player, 'update'):
            self.player.update(current_time, None, self.enemies, self.game.player_actions, 0)
        
        # Update player actions
        if hasattr(self.game, 'player_actions'):
            self.game.player_actions.update_player_movement_and_actions(current_time)
        
        # Update particles
        self.particles.update(delta_time)
    
    def _update_defense_phase(self, current_time, delta_time):
        # Spawn enemy waves
        self.spawn_timer += delta_time
        if self.spawn_timer > 3000:  # Every 3 seconds
            self._spawn_defense_wave()
            self.spawn_timer = 0
        
        # Update enemies
        for enemy in self.enemies:
            if hasattr(enemy, 'update'):
                enemy.update(None, current_time, delta_time, 0)
        
        # Update turrets
        for turret in self.turrets:
            if hasattr(turret, 'update'):
                turret.update(current_time, self.enemies)
        
        # Handle combat
        self._handle_combat()
        
        # Check if defense phase complete (5 waves)
        if self.wave_count >= 5 and len(self.enemies) == 0:
            self.defense_phase = False
            self.game.set_story_message("The Architect's voice returns: 'Would you let it die... or evolve?'", 5000)
    
    def _update_choice_phase(self, delta_time):
        self.choice_timer += delta_time
        # Update core with special effects
        self.orichalc_core.update(delta_time)
    
    def _spawn_defense_wave(self):
        self.wave_count += 1
        enemies_in_wave = 4 + self.wave_count
        
        spawn_positions = [
            (50, 100), (750, 100), (50, 500), (750, 500),
            (400, 50), (100, 300), (700, 300)
        ]
        
        for i in range(min(enemies_in_wave, len(spawn_positions))):
            pos = spawn_positions[i]
            enemy_config = {
                "health": 20 + (self.wave_count * 5),
                "speed": 1.5 + (self.wave_count * 0.2),
                "damage": 15
            }
            enemy = Enemy(pos[0], pos[1], self.game.asset_manager, enemy_config)
            self.enemies.add(enemy)
    
    def _handle_combat(self):
        # Player bullets vs enemies
        if hasattr(self.player, 'bullets_group'):
            for bullet in self.player.bullets_group:
                for enemy in self.enemies:
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.health -= bullet.damage
                        bullet.kill()
                        self.particles.create_explosion(
                            bullet.rect.centerx, bullet.rect.centery,
                            (255, 200, 0), 10
                        )
                        if enemy.health <= 0:
                            enemy.kill()
        
        # Turret bullets vs enemies
        for turret in self.turrets:
            if hasattr(turret, 'bullets_group'):
                for bullet in turret.bullets_group:
                    for enemy in self.enemies:
                        if bullet.rect.colliderect(enemy.rect):
                            enemy.health -= bullet.damage
                            bullet.kill()
                            if enemy.health <= 0:
                                enemy.kill()
        
        # Enemy bullets vs player and turrets
        for enemy in self.enemies:
            if hasattr(enemy, 'bullets_group'):
                for bullet in enemy.bullets_group:
                    if bullet.rect.colliderect(self.player.rect):
                        self.player.take_damage(bullet.damage)
                        bullet.kill()
                    
                    for turret in self.turrets:
                        if bullet.rect.colliderect(turret.rect):
                            turret.take_damage(bullet.damage)
                            bullet.kill()
    
    def _make_choice(self, choice):
        self.final_choice_made = True
        
        if choice == "preserve":
            self.game.set_story_message("You stabilize the Orichalc Core. The Vault enters dormancy, but its hunger remains...", 5000)
        elif choice == "erase":
            self.game.set_story_message("The Vault is destroyed. Earth is free, but now exposed to the Guardians...", 5000)
        elif choice == "merge":
            self.game.set_story_message("You merge with the Vault. Earth becomes your domain to protect and shape...", 5000)
        
        # Mark vault as completed
        self.game.drone_system.architect_vault_completed = True
        
        # Return to story map after delay
        pygame.time.set_timer(pygame.USEREVENT + 4, 6000)
    
    def draw(self, surface):
        surface.fill((60, 40, 80))  # Deep purple background
        
        # Draw player
        self.player.draw(surface)
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(surface)
        
        # Draw turrets
        for turret in self.turrets:
            turret.draw(surface)
        
        # Draw Orichalc core with special effects
        self.orichalc_core.draw(surface, (0, 0))
        
        # Draw particles
        self.particles.draw(surface, (0, 0))
        
        # Draw UI
        font = pygame.font.Font(None, 24)
        if self.defense_phase:
            text = font.render(f"Defend the Core - Wave: {self.wave_count}/5", True, (255, 255, 255))
            surface.blit(text, (10, 10))
        elif not self.final_choice_made:
            # Draw choice options
            font_large = pygame.font.Font(None, 36)
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