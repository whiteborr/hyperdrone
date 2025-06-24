# entities/tempest_boss.py

import pygame
import random
import math
from .enemy import Enemy
from .tornado_minion import TornadoMinion
from .bullet import Bullet
from settings_manager import get_setting

class TempestBoss(Enemy):
    """
    An air-themed boss for Chapter 1. It is agile and uses wind-based attacks.
    It has two phases: a standard phase and an enraged phase below 50% health.
    """
    def __init__(self, game, x, y, config):
        super().__init__(game, x, y, config)
        self.phase = 1
        self.enraged_threshold = self.health / 2

        # Timers for special attacks
        self.last_gust_attack = pygame.time.get_ticks()
        self.gust_attack_cooldown = get_setting("bosses", "tempest", "GUST_COOLDOWN", 5000)

        self.last_tornado_spawn = pygame.time.get_ticks()
        self.tornado_spawn_cooldown = get_setting("bosses", "tempest", "TORNADO_COOLDOWN", 8000)
        
        self.last_cyclone_burst = pygame.time.get_ticks()
        self.cyclone_burst_cooldown = get_setting("bosses", "tempest", "CYCLONE_COOLDOWN", 10000)

        self.speed = get_setting("bosses", "tempest", "SPEED", 3)

    def update(self, maze, player, bullets, game_area_x_offset=0):
        super().update(maze, player, bullets, game_area_x_offset)
        self._check_phase_transition()
        self._update_ai(player)

    def _check_phase_transition(self):
        """Transitions the boss to Phase 2 if health is below the threshold."""
        if self.health <= self.enraged_threshold and self.phase == 1:
            self.phase = 2
            # Increase speed and reduce cooldowns for enraged phase
            self.speed *= 1.5
            self.gust_attack_cooldown *= 0.5
            self.tornado_spawn_cooldown *= 0.7
            print("Tempest has entered ENRAGED phase!")

    def _update_ai(self, player):
        """Handles the boss's attack patterns based on its current phase."""
        current_time = pygame.time.get_ticks()

        # Move towards the player
        dx, dy = player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist != 0:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed
        
        self.rect.topleft = (self.x, self.y)

        # Special attacks
        if current_time - self.last_gust_attack > self.gust_attack_cooldown:
            self.gust_attack(player)
            self.last_gust_attack = current_time

        if self.phase == 2:
            if current_time - self.last_tornado_spawn > self.tornado_spawn_cooldown:
                self.spawn_tornadoes()
                self.last_tornado_spawn = current_time
            
            if current_time - self.last_cyclone_burst > self.cyclone_burst_cooldown:
                self.cyclone_burst()
                self.last_cyclone_burst = current_time


    def gust_attack(self, player):
        """Fires a wide, slow-moving projectile that pushes the player."""
        print("Tempest used Gust Attack!")
        # A gust projectile would be a custom bullet type.
        # For simplicity, we'll use a large, slow standard bullet.
        dx, dy = player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery
        angle = math.atan2(dy, dx)
        
        gust_bullet = Bullet(
            self.game,
            self.rect.centerx,
            self.rect.centery,
            angle,
            damage=5,
            speed=2,
            size=get_setting("bosses", "tempest", "GUST_SIZE", 30),
            color=get_setting("colors", "LIGHT_BLUE", (173, 216, 230)),
            piercing=True
        )
        self.game.enemy_projectiles.add(gust_bullet)


    def spawn_tornadoes(self):
        """Spawns several small, swirling minions."""
        print("Tempest spawned Tornado Minions!")
        num_tornadoes = get_setting("bosses", "tempest", "TORNADO_COUNT", 3)
        for _ in range(num_tornadoes):
            spawn_x = self.rect.centerx + random.randint(-50, 50)
            spawn_y = self.rect.centery + random.randint(-50, 50)
            self.game.enemy_manager.spawn_enemy_by_id("tornado_minion", spawn_x, spawn_y)

    def cyclone_burst(self):
        """Unleashes a radial burst of projectiles."""
        print("Tempest used Cyclone Burst!")
        num_projectiles = get_setting("bosses", "tempest", "CYCLONE_PROJECTILES", 16)
        for i in range(num_projectiles):
            angle = (360 / num_projectiles) * i
            rad_angle = math.radians(angle)
            cyclone_bullet = Bullet(
                self.game,
                self.rect.centerx,
                self.rect.centery,
                rad_angle,
                damage=10,
                speed=4,
                color=get_setting("colors", "WHITE", (255, 255, 255))
            )
            self.game.enemy_projectiles.add(cyclone_bullet)


    def take_damage(self, amount, source=None):
        super().take_damage(amount, source)
        if self.health <= 0:
            self.game.event_manager.dispatch(self.game.game_events.BossDefeatedEvent(boss_id="tempest_boss"))

