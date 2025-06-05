# hyperdrone_core/combat_controller.py
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
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref
        self.player = None 
        self.maze = None   
        
        self.enemy_manager = EnemyManager(game_controller_ref)
        self.wave_manager = WaveManager(game_controller_ref) 

        self.turrets_group = pygame.sprite.Group() 
        self.power_ups_group = pygame.sprite.Group()
        self.explosion_particles_group = pygame.sprite.Group()

        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False

        self.core_reactor = None 

        self.architect_vault_gauntlet_current_wave = 0
        # print("CombatController initialized.") # Reduced startup logging

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
        current_game_state = self.game_controller.scene_manager.get_current_state()
        if current_game_state != GAME_STATE_MAZE_DEFENSE and (not self.player or not self.maze):
            return 
        if current_game_state == GAME_STATE_MAZE_DEFENSE and (not self.maze or not self.core_reactor):
            return

        if self.player and self.player.alive:
            pass 

        player_pos_pixels = self.player.get_position() if self.player and self.player.alive else None
        game_area_x_offset = self.maze.game_area_x_offset if self.maze else 0
        
        is_defense_mode_active = (current_game_state == GAME_STATE_MAZE_DEFENSE)
        target_for_enemies = self.core_reactor.rect.center if is_defense_mode_active and self.core_reactor and self.core_reactor.alive else player_pos_pixels

        self.enemy_manager.update_enemies(
            target_for_enemies, 
            self.maze, 
            current_time_ms, 
            game_area_x_offset,
            is_defense_mode=is_defense_mode_active
        )

        if self.boss_active and self.maze_guardian:
            if self.maze_guardian.alive:
                self.maze_guardian.update(player_pos_pixels, self.maze, current_time_ms, game_area_x_offset)
            elif not self.maze_guardian_defeat_processed:
                self._handle_maze_guardian_defeated() 

        if is_defense_mode_active:
            self.turrets_group.update(self.enemy_manager.get_sprites(), self.maze, game_area_x_offset) 
            if self.core_reactor and not self.core_reactor.alive:
                self.game_controller.scene_manager.set_game_state(gs.GAME_STATE_GAME_OVER) 
                return

        if is_defense_mode_active and self.wave_manager:
            self.wave_manager.update(current_time_ms, delta_time_ms)
            if self.wave_manager.all_waves_cleared and self.enemy_manager.get_active_enemies_count() == 0:
                 if hasattr(self.game_controller, 'handle_maze_defense_victory'):
                    self.game_controller.handle_maze_defense_victory()

        self._update_power_ups(current_time_ms)
        self._handle_collisions(current_game_state)
        self.explosion_particles_group.update()


    def _handle_collisions(self, current_game_state):
        if not self.player and current_game_state != GAME_STATE_MAZE_DEFENSE : 
            return
        if self.player and not self.player.alive and current_game_state != GAME_STATE_MAZE_DEFENSE: 
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
        if not enemies_to_check: return

        for turret in self.turrets_group:
            turret_projectiles = pygame.sprite.Group()
            if hasattr(turret, 'bullets'): turret_projectiles.add(turret.bullets)
            if hasattr(turret, 'missiles'): turret_projectiles.add(turret.missiles)
            if hasattr(turret, 'lightning_zaps'): turret_projectiles.add(turret.lightning_zaps)

            for projectile in list(turret_projectiles): 
                if not projectile.alive: continue
                
                hit_enemies = pygame.sprite.spritecollide(
                    projectile, enemies_to_check, False, 
                    lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
                )
                for enemy in hit_enemies:
                    if enemy.alive:
                        damage_to_enemy = projectile.damage
                        if isinstance(projectile, LightningZap):
                            damage_to_enemy = projectile.damage 
                        enemy.take_damage(damage_to_enemy)
                        if not enemy.alive:
                            self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, specific_sound='enemy_shoot')
                        
                        # MODIFICATION for LightningZap: Do not kill lightning zaps via piercing logic
                        if isinstance(projectile, LightningZap):
                            # Lightning zaps have their own lifetime, don't kill on first hit unless designed to
                            # If you want turret lightning to pierce or chain, that logic would be here.
                            # For now, assume it hits one enemy and continues its lifetime.
                            pass 
                        elif not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                            projectile.pierces_done +=1
                        
                        if not projectile.alive: break 
    
    def _handle_player_projectile_collisions(self):
        if not self.player or not self.player.alive:
            return

        player_projectiles = pygame.sprite.Group()
        if hasattr(self.player, 'bullets_group'): player_projectiles.add(self.player.bullets_group)
        if hasattr(self.player, 'missiles_group'): player_projectiles.add(self.player.missiles_group)
        if hasattr(self.player, 'lightning_zaps_group'): player_projectiles.add(self.player.lightning_zaps_group)

        enemies_to_check = self.enemy_manager.get_sprites()

        for projectile in list(player_projectiles): 
            if not projectile.alive:
                continue

            if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
                hit_a_corner = False
                for corner in self.maze_guardian.corners:
                    if corner['status'] != 'destroyed' and projectile.rect.colliderect(corner['rect']):
                        damage_to_corner = projectile.damage
                        if isinstance(projectile, LightningZap): 
                            damage_to_corner = gs.get_game_setting("LIGHTNING_DAMAGE", 15) 
                        
                        if self.maze_guardian.damage_corner(corner['id'], damage_to_corner):
                            self.game_controller.score += 250
                            self.game_controller.drone_system.add_player_cores(25)
                        
                        hit_a_corner = True
                        # MODIFICATION for LightningZap: Do not kill lightning zaps via piercing logic
                        if isinstance(projectile, LightningZap):
                           pass # Let lightning manage its own lifetime
                        elif not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                             projectile.pierces_done +=1
                        break 
                if hit_a_corner and not projectile.alive:
                    continue 

            hit_enemies = pygame.sprite.spritecollide(
                projectile, enemies_to_check, False, 
                lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
            )
            for enemy in hit_enemies:
                if enemy.alive:
                    damage_to_enemy = projectile.damage
                    # MODIFICATION for LightningZap: Apply damage but don't use piercing logic to kill it
                    if isinstance(projectile, LightningZap): 
                        # Lightning damage logic is often special (e.g., instant, or over time if it was a beam)
                        # For a single zap, ensure it does its damage. It will expire on its own.
                        # Player's LightningZap already applies its own damage during its lifetime/collision checks.
                        # Here, we just confirm it "hit" for scoring/effects.
                        # The projectile.kill() will be skipped for LightningZap based on the check below.
                         if not projectile.damage_applied : # Only apply damage once per zap per enemy if needed
                            enemy.take_damage(damage_to_enemy) # Or specific lightning damage calculation
                            # projectile.damage_applied = True # If one zap should only damage one enemy once
                    else: # Regular bullets/missiles
                        enemy.take_damage(damage_to_enemy)

                    if not enemy.alive:
                        self.game_controller.score += 50 
                        self.game_controller.drone_system.add_player_cores(10) 
                        self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, specific_sound='enemy_shoot') 
                        if self.game_controller.scene_manager.get_current_state() == GAME_STATE_PLAYING:
                            self.game_controller.all_enemies_killed_this_level = all(not e.alive for e in enemies_to_check)
                            if self.game_controller.all_enemies_killed_this_level:
                                self.game_controller._check_level_clear_condition()
                    
                    # MODIFICATION for LightningZap: Prevent immediate kill
                    if isinstance(projectile, LightningZap):
                        # Do not kill LightningZap here; let its lifetime handle it.
                        # If it should be single-target, that logic is within LightningZap itself
                        # or needs to be added (e.g., a flag on the zap after hitting an enemy).
                        pass 
                    elif not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                        projectile.kill() 
                    elif hasattr(projectile, 'pierces_done'):
                        projectile.pierces_done +=1 
                    
                    if not projectile.alive:
                        break 

    def _handle_enemy_projectile_collisions(self, current_game_state):
        # ... (content as before) ...
        all_hostile_projectiles = pygame.sprite.Group()
        for enemy in self.enemy_manager.get_sprites():
            if hasattr(enemy, 'bullets'): all_hostile_projectiles.add(enemy.bullets)
        
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            if hasattr(self.maze_guardian, 'bullets'): all_hostile_projectiles.add(self.maze_guardian.bullets)
            if hasattr(self.maze_guardian, 'laser_beams'): all_hostile_projectiles.add(self.maze_guardian.laser_beams)

        for projectile in list(all_hostile_projectiles): 
            if not projectile.alive: continue

            if self.player and self.player.alive and projectile.rect.colliderect(self.player.collision_rect):
                self.player.take_damage(projectile.damage, self.game_controller.sounds.get('crash'))
                if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent): 
                    projectile.kill()
                if not self.player.alive: 
                    self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                if not projectile.alive: continue 

            if current_game_state == GAME_STATE_MAZE_DEFENSE and self.turrets_group:
                hit_turrets = pygame.sprite.spritecollide(projectile, self.turrets_group, False) 
                for turret in hit_turrets:
                    if hasattr(turret, 'take_damage'): 
                        turret.take_damage(projectile.damage) 
                    if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent):
                        projectile.kill()
                    if not projectile.alive: break 
                if not projectile.alive: continue

            if current_game_state == GAME_STATE_MAZE_DEFENSE and self.core_reactor and self.core_reactor.alive:
                if projectile.rect.colliderect(self.core_reactor.rect):
                    self.core_reactor.take_damage(projectile.damage, self.game_controller) 
                    if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent):
                        projectile.kill()
                    if not self.core_reactor.alive:
                        self.game_controller.scene_manager.set_game_state(gs.GAME_STATE_GAME_OVER) 
                    if not projectile.alive: continue
            
            if self.maze and not getattr(projectile, 'can_pierce_walls', False):
                 if self.maze.is_wall(projectile.rect.centerx, projectile.rect.centery, projectile.rect.width, projectile.rect.height):
                    projectile.kill()
                    continue


    def _handle_physical_collisions(self, current_game_state):
        # ... (content as before) ...
        if self.player and self.player.alive:
            enemies_collided_player = pygame.sprite.spritecollide(
                self.player, self.enemy_manager.get_sprites(), False, 
                lambda p, e: p.collision_rect.colliderect(getattr(e, 'collision_rect', e.rect))
            )
            for enemy in enemies_collided_player:
                if enemy.alive: 
                    self.player.take_damage(34, self.game_controller.sounds.get('crash')) 
                    enemy.take_damage(50) 
                    if not enemy.alive: 
                         self.game_controller.score += 10 
                         self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, specific_sound='crash')

                    if not self.player.alive: 
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                        return 

            if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
                if self.player.collision_rect.colliderect(self.maze_guardian.collision_rect):
                    self.player.take_damage(50, self.game_controller.sounds.get('crash')) 
                    if not self.player.alive:
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                        return

        if current_game_state == GAME_STATE_MAZE_DEFENSE and self.core_reactor and self.core_reactor.alive:
            enemies_hitting_reactor = pygame.sprite.spritecollide(
                self.core_reactor, self.enemy_manager.get_sprites(), True, 
                pygame.sprite.collide_rect_ratio(0.7) 
            )
            for enemy in enemies_hitting_reactor:
                contact_dmg = getattr(enemy, 'contact_damage', 25) 
                self.core_reactor.take_damage(contact_dmg, self.game_controller) 
                self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, specific_sound='crash')
                if not self.core_reactor.alive:
                    self.game_controller.scene_manager.set_game_state(gs.GAME_STATE_GAME_OVER) 
                    return

    def _handle_player_power_up_collisions(self):
        # ... (content as before) ...
        if not self.player or not self.player.alive or not self.power_ups_group:
            return

        collided_powerups = pygame.sprite.spritecollide(
            self.player, self.power_ups_group, False, pygame.sprite.collide_rect_ratio(0.7) 
        )
        for item in collided_powerups:
            if not item.collected and not item.expired and hasattr(item, 'apply_effect'):
                item.apply_effect(self.player) 
                item.collected = True 
                item.kill() 
                self.game_controller.play_sound('weapon_upgrade_collect') 
                self.game_controller.score += 25

    def _update_power_ups(self, current_time_ms):
        # ... (content as before) ...
        for p_up in list(self.power_ups_group): 
            if p_up.update(): 
                p_up.kill()
        current_game_state = self.game_controller.scene_manager.get_current_state()
        if current_game_state == GAME_STATE_PLAYING: 
            if random.random() < (gs.get_game_setting("POWERUP_SPAWN_CHANCE") / gs.FPS if gs.FPS > 0 else 0.01):
                if len(self.power_ups_group) < gs.get_game_setting("MAX_POWERUPS_ON_SCREEN"):
                    self._try_spawn_powerup_item_internal()

    def _try_spawn_powerup_item_internal(self):
        # ... (content as before) ...
        if not self.maze or not self.player: return
        spawn_pos = self.game_controller._get_safe_spawn_point(gs.POWERUP_SIZE, gs.POWERUP_SIZE)
        if not spawn_pos: return
        abs_x, abs_y = spawn_pos
        powerup_type_keys = list(POWERUP_TYPES.keys())
        if not powerup_type_keys: return
        chosen_type_key = random.choice(powerup_type_keys)
        new_powerup = None
        if chosen_type_key == "weapon_upgrade": new_powerup = WeaponUpgradeItem(abs_x, abs_y)
        elif chosen_type_key == "shield": new_powerup = ShieldItem(abs_x, abs_y)
        elif chosen_type_key == "speed_boost": new_powerup = SpeedBoostItem(abs_x, abs_y)
        if new_powerup: self.power_ups_group.add(new_powerup)

    def spawn_maze_guardian(self):
        # ... (content as before) ...
        if not self.player or not self.maze: return
        self.enemy_manager.reset_all() 
        boss_spawn_x = self.maze.game_area_x_offset + (gs.WIDTH - self.maze.game_area_x_offset) / 2
        boss_spawn_y = gs.GAME_PLAY_AREA_HEIGHT / 2
        self.maze_guardian = MazeGuardian(x=boss_spawn_x, y=boss_spawn_y, player_ref=self.player, maze_ref=self.maze, game_controller_ref=self.game_controller)
        self.boss_active = True; self.maze_guardian_defeat_processed = False
        self.game_controller.play_sound('boss_intro', 0.8)

    def _handle_maze_guardian_defeated(self):
        # ... (content as before) ...
        if self.maze_guardian_defeat_processed: return
        self.game_controller.score += 5000; self.game_controller.drone_system.add_player_cores(1500)
        self.game_controller.drone_system.add_defeated_boss("MAZE_GUARDIAN")
        self.game_controller.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB01")
        self.game_controller.trigger_story_beat("story_beat_SB01")
        vault_core_id = "vault_core"; vault_core_details = CORE_FRAGMENT_DETAILS.get("fragment_vault_core")
        if vault_core_details and not self.game_controller.drone_system.has_collected_fragment(vault_core_id):
            if self.game_controller.drone_system.collect_core_fragment(vault_core_id):
                self.game_controller.set_story_message(f"Lore Unlocked: {vault_core_details.get('name', 'Vault Core Data')}")
        self.boss_active = False
        if self.maze_guardian: self.maze_guardian.kill(); self.maze_guardian = None 
        self.maze_guardian_defeat_processed = True
        if self.game_controller.scene_manager.get_current_state() == GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT:
            self.game_controller.architect_vault_message = "MAZE GUARDIAN DEFEATED! ACCESS GRANTED!"
            self.game_controller.architect_vault_message_timer = pygame.time.get_ticks() + 4000

    def reset_combat_state(self):
        # ... (content as before) ...
        self.enemy_manager.reset_all(); self.wave_manager.reset() 
        self.turrets_group.empty(); self.power_ups_group.empty(); self.explosion_particles_group.empty()
        if self.player:
            if hasattr(self.player, 'bullets_group'): self.player.bullets_group.empty()
            if hasattr(self.player, 'missiles_group'): self.player.missiles_group.empty()
            if hasattr(self.player, 'lightning_zaps_group'): self.player.lightning_zaps_group.empty()
        self.maze_guardian = None; self.boss_active = False; self.maze_guardian_defeat_processed = False
        self.core_reactor = None; self.architect_vault_gauntlet_current_wave = 0

    def try_place_turret(self, screen_pos):
        # ... (content as before, with Turret.MAX_TURRETS fix) ...
        if not self.maze or not self.core_reactor or not isinstance(self.maze, MazeChapter2):
            self.game_controller.play_sound('ui_denied', 0.6); return False
        grid_c = int((screen_pos[0] - self.maze.game_area_x_offset) / TILE_SIZE); grid_r = int(screen_pos[1] / TILE_SIZE)
        if not (0 <= grid_r < self.maze.actual_maze_rows and 0 <= grid_c < self.maze.actual_maze_cols):
            self.game_controller.play_sound('ui_denied', 0.6); return False
        
        max_turrets_allowed = Turret.MAX_TURRETS 
        if len(self.turrets_group) >= max_turrets_allowed:
            self.game_controller.play_sound('ui_denied', 0.6); return False
        if not self.maze.can_place_turret(grid_r, grid_c):
            self.game_controller.play_sound('ui_denied', 0.6); return False
        turret_cost = Turret.TURRET_COST 
        if self.game_controller.drone_system.get_player_cores() >= turret_cost:
            if self.game_controller.drone_system.spend_player_cores(turret_cost):
                tile_center_x_abs = grid_c * TILE_SIZE + TILE_SIZE//2 + self.maze.game_area_x_offset
                tile_center_y_abs = grid_r * TILE_SIZE + TILE_SIZE//2
                new_turret = Turret(tile_center_x_abs, tile_center_y_abs, self.game_controller)
                self.turrets_group.add(new_turret); self.maze.mark_turret_spot_as_occupied(grid_r, grid_c) 
                self.game_controller.play_sound('turret_place_placeholder', 0.7); return True
        self.game_controller.play_sound('ui_denied', 0.6); return False

    def try_upgrade_turret(self, turret_to_upgrade):
        # ... (content as before) ...
        if turret_to_upgrade and turret_to_upgrade in self.turrets_group:
            upgrade_cost = Turret.UPGRADE_COST 
            if self.game_controller.drone_system.get_player_cores() >= upgrade_cost:
                if turret_to_upgrade.upgrade(): 
                    self.game_controller.drone_system.spend_player_cores(upgrade_cost)
                    self.game_controller.play_sound('weapon_upgrade_collect', 0.8)
                    if self.game_controller.ui_manager and self.game_controller.ui_manager.build_menu:
                        self.game_controller.ui_manager.build_menu.set_selected_turret(turret_to_upgrade)
                    return True
        self.game_controller.play_sound('ui_denied', 0.6); return False
