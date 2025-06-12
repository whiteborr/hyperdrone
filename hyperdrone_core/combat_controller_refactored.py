# hyperdrone_core/combat_controller_refactored.py
import pygame
import math
import random

import game_settings as gs
from game_settings import (
    TILE_SIZE, WEAPON_MODES_SEQUENCE, POWERUP_TYPES,
    GAME_STATE_PLAYING, GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
    GAME_STATE_ARCHITECT_VAULT_EXTRACTION, GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT,
    GAME_STATE_MAZE_DEFENSE, ARCHITECT_VAULT_DRONES_PER_WAVE, ARCHITECT_VAULT_GAUNTLET_WAVES,
    MAZE_GUARDIAN_HEALTH, LIGHTNING_DAMAGE, CORE_FRAGMENT_DETAILS
)

from entities import (
    PlayerDrone, Enemy, SentinelDrone, MazeGuardian,
    Bullet, Missile, LightningZap, Particle,
    WeaponUpgradeItem, ShieldItem, SpeedBoostItem,
    Turret, CoreReactor, MazeChapter2 
)

from .enemy_manager import EnemyManager
from .wave_manager import WaveManager


class CombatController:
    # [All existing methods remain the same except for the ones below]
    
    def _handle_collisions(self, current_game_state):
        if not self.player and current_game_state != GAME_STATE_MAZE_DEFENSE : 
            return
        if self.player and not self.player.alive and current_game_state != GAME_STATE_MAZE_DEFENSE: 
            # Call player death handler when player is not alive
            self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
            if current_game_state == GAME_STATE_MAZE_DEFENSE:
                self._handle_enemy_projectile_collisions(current_game_state)
            return

        if self.player and self.player.alive: 
            self._handle_player_projectile_collisions()

        self._handle_enemy_projectile_collisions(current_game_state)

        if current_game_state == GAME_STATE_MAZE_DEFENSE:
            self._handle_turret_projectile_collisions()

        self._handle_physical_collisions(current_game_state)
        
        if self.player and self.player.alive: 
            self._handle_player_power_up_collisions()

    def _handle_turret_projectile_collisions(self):
        if not self.turrets_group or not self.enemy_manager:
            return
        enemies_to_check = self.enemy_manager.get_sprites()
        if not enemies_to_check: 
            return

        for turret in self.turrets_group:
            turret_projectiles = pygame.sprite.Group()
            if hasattr(turret, 'bullets'): turret_projectiles.add(turret.bullets)
            if hasattr(turret, 'missiles'): turret_projectiles.add(turret.missiles)
            if hasattr(turret, 'lightning_zaps'): turret_projectiles.add(turret.lightning_zaps)

            # Use groupcollide for turret projectiles
            collision_func = lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
            hits = pygame.sprite.groupcollide(turret_projectiles, enemies_to_check, False, False, collision_func)
            
            for projectile, enemies_hit in hits.items():
                if not projectile.alive:
                    continue
                    
                for enemy in enemies_hit:
                    if enemy.alive:
                        damage_to_enemy = projectile.damage
                        if isinstance(projectile, LightningZap):
                            damage_to_enemy = projectile.damage 
                        enemy.take_damage(damage_to_enemy)
                        if not enemy.alive:
                            self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery)
                        
                        if isinstance(projectile, LightningZap):
                           pass
                        elif not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                            projectile.pierces_done += 1
                        
                        if not projectile.alive: 
                            break
    
    def _handle_player_projectile_collisions(self):
        if not self.player or not self.player.alive:
            return

        player_projectiles = pygame.sprite.Group()
        if hasattr(self.player, 'bullets_group'): player_projectiles.add(self.player.bullets_group)
        if hasattr(self.player, 'missiles_group'): player_projectiles.add(self.player.missiles_group)
        if hasattr(self.player, 'lightning_zaps_group'): player_projectiles.add(self.player.lightning_zaps_group)

        enemies_to_check = self.enemy_manager.get_sprites()
        
        # Handle boss corners first if boss is active
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            for projectile in list(player_projectiles):
                if not projectile.alive:
                    continue
                    
                hit_a_corner = False
                for corner in self.maze_guardian.corners:
                    if corner['status'] != 'destroyed' and projectile.rect.colliderect(corner['rect']):
                        damage_to_corner = projectile.damage
                        if isinstance(projectile, LightningZap):
                            damage_to_corner = gs.get_game_setting("LIGHTNING_DAMAGE", 15)
                        
                        if self.maze_guardian.damage_corner(corner['id'], damage_to_corner):
                            self.game_controller.level_manager.add_score(250)
                            self.game_controller.drone_system.add_player_cores(25)
                        
                        hit_a_corner = True
                        if isinstance(projectile, LightningZap):
                           pass
                        elif not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                             projectile.pierces_done += 1
                        break
                if hit_a_corner and not projectile.alive:
                    continue
        
        # Use groupcollide for enemy collisions
        collision_func = lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
        hits = pygame.sprite.groupcollide(player_projectiles, enemies_to_check, False, False, collision_func)
        
        for projectile, enemies_hit in hits.items():
            if not projectile.alive:
                continue
                
            for enemy in enemies_hit:
                if enemy.alive:
                    damage_to_enemy = projectile.damage
                    if isinstance(projectile, LightningZap): 
                         if not projectile.damage_applied:
                            enemy.take_damage(damage_to_enemy)
                    else:
                        enemy.take_damage(damage_to_enemy)

                    if not enemy.alive:
                        self.game_controller.level_manager.add_score(50)
                        self.game_controller.drone_system.add_player_cores(10) 
                        self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery) 
                        self.game_controller.check_for_all_enemies_killed()
                    
                    if isinstance(projectile, LightningZap):
                        pass 
                    elif not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                        projectile.kill() 
                    elif hasattr(projectile, 'pierces_done'):
                        projectile.pierces_done += 1 
                    
                    if not projectile.alive:
                        break

    def _handle_enemy_projectile_collisions(self, current_game_state):
        all_hostile_projectiles = pygame.sprite.Group()
        for enemy in self.enemy_manager.get_sprites():
            if hasattr(enemy, 'bullets'): all_hostile_projectiles.add(enemy.bullets)
        
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            if hasattr(self.maze_guardian, 'bullets'): all_hostile_projectiles.add(self.maze_guardian.bullets)
            if hasattr(self.maze_guardian, 'laser_beams'): all_hostile_projectiles.add(self.maze_guardian.laser_beams)

        # Player collision
        if self.player and self.player.alive:
            player_group = pygame.sprite.GroupSingle(self.player)
            collision_func = lambda proj, player: proj.rect.colliderect(player.collision_rect)
            player_hits = pygame.sprite.groupcollide(all_hostile_projectiles, player_group, False, False, collision_func)
            
            for projectile, players_hit in player_hits.items():
                if not projectile.alive:
                    continue
                    
                for player in players_hit:
                    player.take_damage(projectile.damage, sound_key_on_hit='crash')
                    if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent): 
                        projectile.kill()
                    if not player.alive: 
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                    if not projectile.alive:
                        break

        # Turret collision
        if current_game_state == GAME_STATE_MAZE_DEFENSE and self.turrets_group:
            turret_hits = pygame.sprite.groupcollide(all_hostile_projectiles, self.turrets_group, False, False)
            for projectile, turrets_hit in turret_hits.items():
                if not projectile.alive:
                    continue
                    
                for turret in turrets_hit:
                    if hasattr(turret, 'take_damage'): 
                        turret.take_damage(projectile.damage) 
                    if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent):
                        projectile.kill()
                    if not projectile.alive:
                        break

        # Core reactor collision
        if current_game_state == GAME_STATE_MAZE_DEFENSE and self.core_reactor and self.core_reactor.alive:
            reactor_group = pygame.sprite.GroupSingle(self.core_reactor)
            reactor_hits = pygame.sprite.groupcollide(all_hostile_projectiles, reactor_group, False, False)
            
            for projectile, reactors_hit in reactor_hits.items():
                if not projectile.alive:
                    continue
                    
                for reactor in reactors_hit:
                    reactor.take_damage(projectile.damage, self.game_controller)
                    if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent):
                        projectile.kill()
                    if not reactor.alive:
                        self.game_controller.state_manager.set_state(gs.GAME_STATE_GAME_OVER)
                    if not projectile.alive:
                        break

        # Wall collision
        if self.maze:
            for projectile in list(all_hostile_projectiles):
                if not projectile.alive or getattr(projectile, 'can_pierce_walls', False):
                    continue
                    
                if self.maze.is_wall(projectile.rect.centerx, projectile.rect.centery, projectile.rect.width, projectile.rect.height):
                    projectile.kill()

    def _handle_physical_collisions(self, current_game_state):
        # Player-enemy collisions
        if self.player and self.player.alive:
            player_group = pygame.sprite.GroupSingle(self.player)
            collision_func = lambda p, e: p.collision_rect.colliderect(getattr(e, 'collision_rect', e.rect))
            enemy_hits = pygame.sprite.groupcollide(player_group, self.enemy_manager.get_sprites(), False, False, collision_func)
            
            for player, enemies_hit in enemy_hits.items():
                for enemy in enemies_hit:
                    if enemy.alive: 
                        player.take_damage(34, sound_key_on_hit='crash') 
                        enemy.take_damage(50) 
                        if not enemy.alive: 
                             self.game_controller.level_manager.add_score(10)
                             self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery)
                             self.game_controller.check_for_all_enemies_killed()

                        if not player.alive: 
                            self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                            return

            # Player-boss collision
            if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
                if self.player.collision_rect.colliderect(self.maze_guardian.collision_rect):
                    self.player.take_damage(50, sound_key_on_hit='crash') 
                    if not self.player.alive:
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                        return

        # Enemy-reactor collisions
        if current_game_state == GAME_STATE_MAZE_DEFENSE and self.core_reactor and self.core_reactor.alive:
            reactor_group = pygame.sprite.GroupSingle(self.core_reactor)
            collision_func = pygame.sprite.collide_rect_ratio(0.7)
            reactor_hits = pygame.sprite.groupcollide(reactor_group, self.enemy_manager.get_sprites(), False, True, collision_func)
            
            for reactor, enemies_hit in reactor_hits.items():
                for enemy in enemies_hit:
                    contact_dmg = getattr(enemy, 'contact_damage', 25) 
                    reactor.take_damage(contact_dmg, self.game_controller) 
                    self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery)
                    if not reactor.alive:
                        self.game_controller.state_manager.set_state(gs.GAME_STATE_GAME_OVER) 
                        return

    def _handle_player_power_up_collisions(self):
        if not self.player or not self.player.alive or not self.power_ups_group:
            return

        player_group = pygame.sprite.GroupSingle(self.player)
        collision_func = pygame.sprite.collide_rect_ratio(0.7)
        powerup_hits = pygame.sprite.groupcollide(player_group, self.power_ups_group, False, False, collision_func)
        
        for player, powerups_hit in powerup_hits.items():
            for item in powerups_hit:
                if not item.collected and not item.expired and hasattr(item, 'apply_effect'):
                    item.apply_effect(player) 
                    item.collected = True 
                    item.kill() 
                    self.game_controller.play_sound('weapon_upgrade_collect') 
                    self.game_controller.level_manager.add_score(25)