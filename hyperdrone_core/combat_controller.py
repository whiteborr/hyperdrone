# hyperdrone_core/combat_controller.py
import pygame
import math
import random
import logging

from settings_manager import get_setting
from constants import (
    GAME_STATE_PLAYING, GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
    GAME_STATE_ARCHITECT_VAULT_EXTRACTION, GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT,
    GAME_STATE_MAZE_DEFENSE, GAME_STATE_GAME_OVER
)

from entities import (
    PlayerDrone, Enemy, SentinelDrone, MazeGuardian,
    Bullet, Missile, LightningZap, Particle,
    WeaponUpgradeItem, ShieldItem, SpeedBoostItem,
    Turret, CoreReactor
)

from .enemy_manager import EnemyManager
from .wave_manager import WaveManager

logger = logging.getLogger(__name__)

class CombatController:
    """
    Manages all combat-related logic, including projectile collisions,
    enemy interactions, and boss battles. It has been refactored to use the
    new settings manager and optimized collision functions.
    """
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        self.asset_manager.game_controller = game_controller_ref
        
        self.player = None 
        self.maze = None   
        
        self.enemy_manager = EnemyManager(game_controller_ref, self.asset_manager)
        self.wave_manager = WaveManager(game_controller_ref) 

        self.turrets_group = pygame.sprite.Group() 
        self.power_ups_group = pygame.sprite.Group()
        self.explosion_particles_group = pygame.sprite.Group()

        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False

        self.core_reactor = None 
        self.architect_vault_gauntlet_current_wave = 0

    def set_active_entities(self, player, maze, core_reactor=None, turrets_group=None, power_ups_group=None, explosion_particles_group=None):
        self.player = player
        self.maze = maze
        self.core_reactor = core_reactor 
        self.turrets_group = turrets_group if turrets_group is not None else pygame.sprite.Group()
        self.power_ups_group = power_ups_group if power_ups_group is not None else pygame.sprite.Group()
        self.explosion_particles_group = explosion_particles_group if explosion_particles_group is not None else pygame.sprite.Group()
        
        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False

    def update(self, current_time_ms, delta_time_ms):
        current_game_state = self.game_controller.state_manager.get_current_state_id()
        if current_game_state != GAME_STATE_MAZE_DEFENSE and (not self.player or not self.maze):
            return 
        if current_game_state == GAME_STATE_MAZE_DEFENSE and (not self.maze or not self.core_reactor):
            return

        player_pos_pixels = self.player.get_position() if self.player and self.player.alive else None
        game_area_x_offset = self.maze.game_area_x_offset if self.maze else 0
        
        is_defense_mode_active = (current_game_state == GAME_STATE_MAZE_DEFENSE)
        target_for_enemies = self.core_reactor.rect.center if is_defense_mode_active and self.core_reactor and self.core_reactor.alive else player_pos_pixels

        self.enemy_manager.update_enemies(
            target_for_enemies, self.maze, current_time_ms, delta_time_ms,
            game_area_x_offset, is_defense_mode=is_defense_mode_active
        )

        if self.boss_active and self.maze_guardian:
            if self.maze_guardian.alive:
                self.maze_guardian.update(player_pos_pixels, self.maze, current_time_ms, game_area_x_offset)
            elif not self.maze_guardian_defeat_processed:
                self._handle_maze_guardian_defeated() 

        if is_defense_mode_active:
            self.turrets_group.update(self.enemy_manager.get_sprites(), self.maze, game_area_x_offset) 
            if self.core_reactor and not self.core_reactor.alive:
                self.game_controller.state_manager.set_state(GAME_STATE_GAME_OVER) 
                return
            if self.wave_manager:
                self.wave_manager.update(current_time_ms, delta_time_ms)

        self._update_power_ups(current_time_ms)
        self._handle_collisions(current_game_state)
        self.explosion_particles_group.update()

    def _handle_collisions(self, current_game_state):
        if not self.player and current_game_state != GAME_STATE_MAZE_DEFENSE:
            return

        player_is_alive = self.player and self.player.alive
        if player_is_alive:
            self._handle_player_projectile_collisions()
            self._handle_player_power_up_collisions()
        
        self._handle_enemy_projectile_collisions(current_game_state)

        if current_game_state == GAME_STATE_MAZE_DEFENSE:
            self._handle_turret_projectile_collisions()

        self._handle_physical_collisions(current_game_state)

    def _handle_turret_projectile_collisions(self):
        if not self.turrets_group or not self.enemy_manager: return
        enemies_to_check = self.enemy_manager.get_sprites()
        if not enemies_to_check: return

        for turret in self.turrets_group:
            turret_projectiles = pygame.sprite.Group()
            if hasattr(turret, 'bullets'): turret_projectiles.add(turret.bullets)
            if hasattr(turret, 'missiles'): turret_projectiles.add(turret.missiles)
            if hasattr(turret, 'lightning_zaps'): turret_projectiles.add(turret.lightning_zaps)

            collision_func = lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
            hits = pygame.sprite.groupcollide(turret_projectiles, enemies_to_check, False, False, collision_func)
            
            for projectile, enemies_hit in hits.items():
                if not projectile.alive: continue
                for enemy in enemies_hit:
                    if enemy.alive:
                        enemy.take_damage(projectile.damage)
                        if not enemy.alive:
                            self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery)
                        
                        if not isinstance(projectile, LightningZap) and not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                            projectile.pierces_done += 1
                        
                        if not projectile.alive: break

    def _handle_player_projectile_collisions(self):
        player_projectiles = pygame.sprite.Group()
        if hasattr(self.player, 'bullets_group'): player_projectiles.add(self.player.bullets_group)
        if hasattr(self.player, 'missiles_group'): player_projectiles.add(self.player.missiles_group)
        if hasattr(self.player, 'lightning_zaps_group'): player_projectiles.add(self.player.lightning_zaps_group)

        # Handle boss corners first
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            for projectile in list(player_projectiles):
                if not projectile.alive: continue
                for corner in self.maze_guardian.corners:
                    if corner['status'] != 'destroyed' and projectile.rect.colliderect(corner['rect']):
                        damage = projectile.damage if not isinstance(projectile, LightningZap) else get_setting("weapons", "LIGHTNING_DAMAGE", 15)
                        if self.maze_guardian.damage_corner(corner['id'], damage):
                            self.game_controller.level_manager.add_score(250)
                            self.game_controller.drone_system.add_player_cores(25)
                        if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        break 
                if not projectile.alive: continue

        # Handle regular enemies
        collision_func = lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
        hits = pygame.sprite.groupcollide(player_projectiles, self.enemy_manager.get_sprites(), False, False, collision_func)
        
        for projectile, enemies_hit in hits.items():
            if not projectile.alive: continue
            for enemy in enemies_hit:
                if enemy.alive:
                    enemy.take_damage(projectile.damage)
                    if not enemy.alive:
                        self.game_controller.level_manager.add_score(50)
                        self.game_controller.drone_system.add_player_cores(10) 
                        self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery) 
                        self.game_controller.check_for_all_enemies_killed()
                    
                    if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                        projectile.kill()
                    elif hasattr(projectile, 'pierces_done'):
                        projectile.pierces_done += 1
                    
                    if not projectile.alive: break

    def _handle_enemy_projectile_collisions(self, current_game_state):
        all_hostile_projectiles = pygame.sprite.Group()
        for enemy in self.enemy_manager.get_sprites():
            if hasattr(enemy, 'bullets'): all_hostile_projectiles.add(enemy.bullets)
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            if hasattr(self.maze_guardian, 'bullets'): all_hostile_projectiles.add(self.maze_guardian.bullets)
            if hasattr(self.maze_guardian, 'laser_beams'): all_hostile_projectiles.add(self.maze_guardian.laser_beams)

        # Player collision
        if self.player and self.player.alive:
            player_hits = pygame.sprite.spritecollide(self.player, all_hostile_projectiles, True, pygame.sprite.collide_rect_ratio(0.7))
            for projectile in player_hits:
                self.player.take_damage(projectile.damage, sound_key_on_hit='crash')
                if not self.player.alive: self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")

        # Turret and Reactor collision in Defense Mode
        if current_game_state == GAME_STATE_MAZE_DEFENSE:
            if self.turrets_group:
                pygame.sprite.groupcollide(all_hostile_projectiles, self.turrets_group, True, False)
            if self.core_reactor and self.core_reactor.alive:
                reactor_hits = pygame.sprite.spritecollide(self.core_reactor, all_hostile_projectiles, True)
                for projectile in reactor_hits:
                    self.core_reactor.take_damage(projectile.damage, self.game_controller)
                    if not self.core_reactor.alive: self.game_controller.state_manager.set_state(GAME_STATE_GAME_OVER)

    def _handle_physical_collisions(self, current_game_state):
        # Player-enemy collisions
        if self.player and self.player.alive:
            enemy_hits = pygame.sprite.spritecollide(self.player, self.enemy_manager.get_sprites(), False, pygame.sprite.collide_rect_ratio(0.7))
            for enemy in enemy_hits:
                if enemy.alive: 
                    self.player.take_damage(34, sound_key_on_hit='crash') 
                    enemy.take_damage(50) 
                    if not enemy.alive: 
                        self.game_controller.level_manager.add_score(10)
                        self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery)
                        self.game_controller.check_for_all_enemies_killed()
                    if not self.player.alive: 
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                        return

            if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
                if self.player.collision_rect.colliderect(self.maze_guardian.collision_rect):
                    self.player.take_damage(50, sound_key_on_hit='crash') 
                    if not self.player.alive: self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")

        # Enemy-reactor collisions
        if current_game_state == GAME_STATE_MAZE_DEFENSE and self.core_reactor and self.core_reactor.alive:
            reactor_hits = pygame.sprite.spritecollide(self.core_reactor, self.enemy_manager.get_sprites(), True, pygame.sprite.collide_rect_ratio(0.7))
            for enemy in reactor_hits:
                self.core_reactor.take_damage(getattr(enemy, 'contact_damage', 25), self.game_controller) 
                self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery)
                if not self.core_reactor.alive: self.game_controller.state_manager.set_state(GAME_STATE_GAME_OVER)

    def _handle_player_power_up_collisions(self):
        powerup_hits = pygame.sprite.spritecollide(self.player, self.power_ups_group, True, pygame.sprite.collide_rect_ratio(0.7))
        for item in powerup_hits:
            if hasattr(item, 'apply_effect'):
                item.apply_effect(self.player)
                self.game_controller.play_sound('weapon_upgrade_collect') 
                self.game_controller.level_manager.add_score(25)

    def _update_power_ups(self, current_time_ms):
        for p_up in list(self.power_ups_group): 
            if p_up.update(): p_up.kill()
        
        current_game_state = self.game_controller.state_manager.get_current_state_id()
        if current_game_state == GAME_STATE_PLAYING: 
            spawn_chance = get_setting("powerups", "POWERUP_SPAWN_CHANCE", 0.05)
            fps = get_setting("display", "FPS", 60)
            if random.random() < (spawn_chance / fps if fps > 0 else 0.01):
                if len(self.power_ups_group) < get_setting("powerups", "MAX_POWERUPS_ON_SCREEN", 2):
                    self._try_spawn_powerup_item_internal()

    def _try_spawn_powerup_item_internal(self):
        if not self.maze or not self.player: return
        spawn_pos = self.game_controller._get_safe_spawn_point(get_setting("powerups", "POWERUP_SIZE", 26), get_setting("powerups", "POWERUP_SIZE", 26))
        if not spawn_pos: return
        
        powerup_types = ["weapon_upgrade", "shield", "speed_boost"]
        chosen_type = random.choice(powerup_types)
        
        if chosen_type == "weapon_upgrade": new_powerup = WeaponUpgradeItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        elif chosen_type == "shield": new_powerup = ShieldItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        else: new_powerup = SpeedBoostItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        
        if new_powerup: self.power_ups_group.add(new_powerup)
    
    def reset_combat_state(self):
        self.enemy_manager.reset_all()
        self.wave_manager.reset() 
        self.turrets_group.empty()
        self.power_ups_group.empty()
        self.explosion_particles_group.empty()
        if self.player:
            if hasattr(self.player, 'bullets_group'): self.player.bullets_group.empty()
            if hasattr(self.player, 'missiles_group'): self.player.missiles_group.empty()
            if hasattr(self.player, 'lightning_zaps_group'): self.player.lightning_zaps_group.empty()
        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False
        self.core_reactor = None
        self.architect_vault_gauntlet_current_wave = 0