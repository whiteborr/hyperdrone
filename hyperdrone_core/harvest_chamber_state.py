# hyperdrone_core/harvest_chamber_state.py
import pygame
import random
from .state import State
from settings_manager import get_setting
from entities import Enemy 

class ScrollingBackground:
    """Manages the scrolling background for the Harvest Chamber."""
    def __init__(self, screen_height, image):
        self.image = image
        if self.image is None:
            self.image = pygame.Surface((get_setting("display", "WIDTH", 1920), screen_height)).convert()
            self.image.fill((10, 0, 20))
            for _ in range(100):
                x = random.randint(0, self.image.get_width())
                y = random.randint(0, self.image.get_height())
                size = random.randint(1, 3)
                pygame.draw.circle(self.image, (random.randint(50, 100), 0, random.randint(100, 150)), (x, y), size)

        self.rect = self.image.get_rect()
        self.y1 = 0
        self.y2 = -self.rect.height
        self.scroll_speed = 4

    def update(self, delta_time):
        self.y1 += self.scroll_speed
        self.y2 += self.scroll_speed
        if self.y1 >= self.rect.height:
            self.y1 = -self.rect.height + (self.y1 - self.rect.height)
        if self.y2 >= self.rect.height:
            self.y2 = -self.rect.height + (self.y2 - self.rect.height)

    def draw(self, surface):
        surface.blit(self.image, (0, self.y1))
        surface.blit(self.image, (0, self.y2))

class ShmupEnemyManager:
    """Manages spawning and updating of enemies in the SHMUP level."""
    def __init__(self, game_controller):
        self.game_controller = game_controller
        self.enemies = pygame.sprite.Group()
        self.spawn_timer = pygame.time.get_ticks()
        self.spawn_interval = 1000 

    def update(self, current_time, delta_time):
        if current_time - self.spawn_timer > self.spawn_interval:
            self.spawn_timer = current_time
            self.spawn_enemy()
        
        for enemy in self.enemies:
            enemy.y += enemy.speed
            enemy.rect.y = enemy.y
            if enemy.rect.top > get_setting("display", "HEIGHT", 1080):
                enemy.kill()

    def spawn_enemy(self):
        spawn_x = random.randint(50, get_setting("display", "WIDTH", 1920) - 50)
        enemy_config = self.game_controller.combat_controller.enemy_manager.enemy_configs.get("sentinel")
        if enemy_config:
            new_enemy = Enemy(spawn_x, -50, self.game_controller.asset_manager, enemy_config)
            new_enemy.speed = 4 
            new_enemy.angle = 90
            self.enemies.add(new_enemy)

    def draw(self, surface):
        self.enemies.draw(surface)

class ShmupPlayerController:
    """Handles player movement and actions in the SHMUP state."""
    def __init__(self, player):
        self.player = player
        self.player_speed = get_setting("gameplay", "PLAYER_SPEED", 3) * 1.5

    def handle_input(self):
        if not self.player:
            return

        keys = pygame.key.get_pressed()
        dx, dy = 0, 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1

        self.player.x += dx * self.player_speed
        self.player.y += dy * self.player_speed

        # Clamp player position to screen bounds
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        self.player.x = max(self.player.rect.width / 2, min(self.player.x, width - self.player.rect.width / 2))
        self.player.y = max(self.player.rect.height / 2, min(self.player.y, height - self.player.rect.height / 2))
        self.player.rect.center = (self.player.x, self.player.y)

        # Continuous shooting
        if keys[pygame.K_SPACE]:
            self.player.shoot()

class HarvestChamberState(State):
    """
    Manages the gameplay for Chapter 4: The Harvest Chamber.
    """
    def enter(self, previous_state=None, **kwargs):
        """Initializes the vertical scrolling level."""
        print("Entering HarvestChamberState...")
        
        self.player_controller = None
        if self.game.player:
            self.game.player.x = get_setting("display", "WIDTH", 1920) / 2
            self.game.player.y = get_setting("display", "HEIGHT", 1080) - 100
            self.game.player.is_cruising = False 
            self.game.player.angle = -90
            self.player_controller = ShmupPlayerController(self.game.player)

        bg_image = self.game.asset_manager.get_image("harvest_chamber_bg")
        self.background = ScrollingBackground(get_setting("display", "HEIGHT", 1080), bg_image)
        self.shmup_enemy_manager = ShmupEnemyManager(self.game)

        current_chapter = self.game.story_manager.get_current_chapter()
        if not (current_chapter and current_chapter.chapter_id == "chapter_4"):
             print("Warning: Entered HarvestChamberState but not on Chapter 4 in story.")
        
        self.game.item_manager.spawn_quantum_circuitry(get_setting("display", "WIDTH", 1920)/2, 200)

    def update(self, delta_time):
        """Update SHMUP gameplay logic."""
        current_time = pygame.time.get_ticks()

        if not self.game.player:
            self.game.state_manager.set_state("MainMenuState")
            return
        
        if self.player_controller:
            self.player_controller.handle_input()

        if self.game.player:
            self.game.player.bullets_group.update()
            
        self.shmup_enemy_manager.update(current_time, delta_time)
        self.background.update(delta_time)
        self._handle_shmup_collisions()
        
        if not self.game.player.alive:
            self.game.state_manager.set_state("GameOverState")


    def _handle_shmup_collisions(self):
        """Handles collisions for the SHMUP state."""
        if not self.game.player:
            return

        hit_enemies = pygame.sprite.groupcollide(self.game.player.bullets_group, self.shmup_enemy_manager.enemies, True, False)
        for bullet, enemies in hit_enemies.items():
            for enemy in enemies:
                enemy.take_damage(bullet.damage)

        if pygame.sprite.spritecollide(self.game.player, self.shmup_enemy_manager.enemies, True):
            self.game.player.take_damage(50)


    def handle_events(self, events):
        """Handle player input for SHMUP controls."""
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                self.game.toggle_pause()

    def draw(self, surface):
        """Render the vertical scrolling scene."""
        surface.fill((10, 0, 20)) 
        self.background.draw(surface)
        
        self.game.quantum_circuitry_group.draw(surface)
        self.shmup_enemy_manager.draw(surface)
        
        if self.game.player:
            self.game.player.bullets_group.draw(surface)
            self.game.player.draw(surface)

        self.game.ui_manager.draw_current_scene_ui()
