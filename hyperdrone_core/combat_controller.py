# hyperdrone_core/combat_controller.py
from pygame.sprite import Group, groupcollide, spritecollide, collide_rect_ratio
from math import hypot
from random import random, choice
from logging import getLogger, info, error

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
    Turret, CoreReactor, GlitchingWall
)
from entities.temporary_barricade import TemporaryBarricade

from .enemy_manager import EnemyManager
from .wave_manager import WaveManager

logger = getLogger(__name__)

class CombatController:
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        self.asset_manager.game_controller = game_controller_ref
        
        self.player = None 
        self.maze = None   
        
        self.enemy_manager = EnemyManager(game_controller_ref, self.asset_manager)
        self.wave_manager = WaveManager(game_controller_ref) 

        self.turrets_group = Group() 
        self.power_ups_group = Group()
        self.explosion_particles_group = Group()
        self.spawned_barricades_group = Group() 

        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False

        self.core_reactor = None 
        self.architect_vault_gauntlet_current_wave = 0

    def set_active_entities(self, player, maze, core_reactor=None, turrets_group=None, power_ups_group=None, explosion_particles_group=None):
        self.player = player
        self.maze = maze
        self.core_reactor = core_reactor 
        self.turrets_group = turrets_group or Group()
        self.power_ups_group = power_ups_group or Group()
        self.explosion_particles_group = explosion_particles_group or Group()
        
        if self.player and hasattr(self.player, 'spawned_barricades_group'):
            self.spawned_barricades_group = self.player.spawned_barricades_group
        else:
            self.spawned_barricades_group = Group()

        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False

    def update(self, current_time_ms, delta_time_ms):
        current_state = self.game_controller.state_manager.get_current_state_id()
        
        # Early exit checks
        if current_state not in [GAME_STATE_MAZE_DEFENSE, "MazeDefenseState"] and (not self.player or not self.maze):
            return 
        if current_state == GAME_STATE_MAZE_DEFENSE and (not self.maze or not self.core_reactor):
            return

        # Get positions and settings
        player_pos = self.player.get_position() if self.player and self.player.alive else None
        x_offset = self.maze.game_area_x_offset if self.maze else 0
        is_defense = (current_state == GAME_STATE_MAZE_DEFENSE)
        target = self.core_reactor.rect.center if is_defense and self.core_reactor and self.core_reactor.alive else player_pos

        # Update entities
        self.enemy_manager.update_enemies(target, self.maze, current_time_ms, delta_time_ms, x_offset, is_defense_mode=is_defense)

        # Update boss
        if self.boss_active and self.maze_guardian:
            if self.maze_guardian.alive:
                self.maze_guardian.update(player_pos, self.maze, current_time_ms, x_offset)
            elif not self.maze_guardian_defeat_processed:
                self._handle_maze_guardian_defeated() 

        # Defense mode updates
        if is_defense:
            self.turrets_group.update(self.enemy_manager.get_sprites(), self.maze, x_offset) 
            if self.core_reactor and not self.core_reactor.alive:
                self.game_controller.state_manager.set_state(GAME_STATE_GAME_OVER) 
                return
            if self.wave_manager:
                self.wave_manager.update(current_time_ms, delta_time_ms)
            if hasattr(self.game_controller, 'tower_defense_manager'):
                self.game_controller.tower_defense_manager.update(delta_time_ms)

        # Update other systems
        self._update_power_ups(current_time_ms)
        self._handle_collisions(current_state)
        self.explosion_particles_group.update()
        self.spawned_barricades_group.update()
        self.game_controller.glitching_walls_group.update()

    def _handle_collisions(self, current_state):
        if not self.player and current_state not in [GAME_STATE_MAZE_DEFENSE, "MazeDefenseState"]:
            return

        player_alive = self.player and self.player.alive
        if player_alive:
            self._handle_player_projectile_collisions()
            self._handle_player_power_up_collisions()
        
        self._handle_enemy_projectile_collisions(current_state)

        if current_state in [GAME_STATE_MAZE_DEFENSE, "MazeDefenseState"]:
            self._handle_turret_projectile_collisions()

        self._handle_physical_collisions(current_state)

    def _handle_turret_projectile_collisions(self):
        if not self.turrets_group: 
            return
            
        # Get enemies to check
        if hasattr(self.game_controller, 'tower_defense_manager'):
            enemies = self.game_controller.tower_defense_manager.enemies_group
        else:
            enemies = self.enemy_manager.get_sprites()
            
        if not enemies: 
            return

        for turret in self.turrets_group:
            # Get turret projectiles
            projectiles = Group()
            for attr in ['bullets', 'missiles', 'lightning_zaps']:
                if hasattr(turret, attr):
                    projectiles.add(getattr(turret, attr))

            # Handle enemy hits
            hits = groupcollide(projectiles, enemies, False, False, lambda p, e: p.rect.colliderect(e.rect))
            
            for projectile, enemies_hit in hits.items():
                if not projectile.alive: 
                    continue
                    
                for enemy in enemies_hit:
                    if enemy.alive:
                        enemy.take_damage(projectile.damage)
                        if not enemy.alive:
                            self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, 15, None, True)
                        
                        # Handle piercing
                        if not isinstance(projectile, LightningZap) and not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                            projectile.pierces_done += 1
                        
                        if not projectile.alive: 
                            break
            
            # Handle barricade hits
            barricade_hits = groupcollide(projectiles, self.spawned_barricades_group, False, False, lambda p, b: p.rect.colliderect(b.rect))
            for projectile, barricades_hit in barricade_hits.items():
                if not projectile.alive: 
                    continue
                    
                for barricade in barricades_hit:
                    if barricade.alive:
                        barricade.take_damage(projectile.damage)
                        if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                            projectile.pierces_done += 1
                        if not projectile.alive: 
                            break

    def _handle_player_projectile_collisions(self):
        # Get player projectiles
        projectiles = Group()
        for attr in ['bullets_group', 'missiles_group', 'lightning_zaps_group']:
            if hasattr(self.player, attr):
                projectiles.add(getattr(self.player, attr))

        # Handle boss corners first
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            for projectile in list(projectiles):
                if not projectile.alive: 
                    continue
                    
                for corner in self.maze_guardian.corners:
                    if corner['status'] != 'destroyed' and projectile.rect.colliderect(corner['rect']):
                        damage = projectile.damage if not isinstance(projectile, LightningZap) else get_setting("weapons", "LIGHTNING_DAMAGE", 15)
                        if self.maze_guardian.damage_corner(corner['id'], damage):
                            self.game_controller.level_manager.add_score(250)
                            self.game_controller.drone_system.add_cores(25)
                        if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        break 
                        
                if not projectile.alive: 
                    continue

        # Handle regular enemies
        collision_func = lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
        hits = groupcollide(projectiles, self.enemy_manager.get_sprites(), False, False, collision_func)
        
        for projectile, enemies_hit in hits.items():
            if not projectile.alive: 
                continue
                
            for enemy in enemies_hit:
                if enemy.alive:
                    enemy.take_damage(projectile.damage)
                    if not enemy.alive:
                        self.game_controller.level_manager.add_score(50)
                        self.game_controller.drone_system.add_cores(10) 
                        self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, 15, None, True)
                        self.game_controller.check_for_all_enemies_killed()
                    
                    # Handle piercing
                    if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                        projectile.kill()
                    elif hasattr(projectile, 'pierces_done'):
                        projectile.pierces_done += 1
                    
                    if not projectile.alive: 
                        break
        
        # Handle barricade hits
        barricade_hits = groupcollide(projectiles, self.spawned_barricades_group, False, False, collision_func)
        for projectile, barricades_hit in barricade_hits.items():
            if not projectile.alive: 
                continue
                
            for barricade in barricades_hit:
                if barricade.alive:
                    barricade.take_damage(projectile.damage)
                    if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                        projectile.kill()
                    elif hasattr(projectile, 'pierces_done'):
                        projectile.pierces_done += 1
                    if not projectile.alive: 
                        break

    def _handle_enemy_projectile_collisions(self, current_state):
        # Get all hostile projectiles
        hostile_projectiles = Group()
        for enemy in self.enemy_manager.get_sprites():
            if hasattr(enemy, 'bullets'): 
                hostile_projectiles.add(enemy.bullets)
                
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            for attr in ['bullets', 'laser_beams']:
                if hasattr(self.maze_guardian, attr):
                    hostile_projectiles.add(getattr(self.maze_guardian, attr))

        # Player collision
        if self.player and self.player.alive:
            player_hits = spritecollide(self.player, hostile_projectiles, True, collide_rect_ratio(0.7))
            for projectile in player_hits:
                self.player.take_damage(projectile.damage, sound_key_on_hit='crash')
                if not self.player.alive: 
                    self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
        
        # Barricade collisions
        barricade_hits = groupcollide(hostile_projectiles, self.spawned_barricades_group, True, False, collide_rect_ratio(0.7))
        for projectile, barricades_hit in barricade_hits.items():
            for barricade in barricades_hit:
                if barricade.alive:
                    barricade.take_damage(projectile.damage)
                    if not barricade.alive:
                        self.game_controller._create_explosion(barricade.rect.centerx, barricade.rect.centery, 5, None, False)

        # Defense mode collisions
        if current_state == GAME_STATE_MAZE_DEFENSE:
            if self.turrets_group:
                groupcollide(hostile_projectiles, self.turrets_group, True, False)
                
            if self.core_reactor and self.core_reactor.alive:
                reactor_hits = spritecollide(self.core_reactor, hostile_projectiles, True)
                for projectile in reactor_hits:
                    self.core_reactor.take_damage(projectile.damage, self.game_controller)
                    if not self.core_reactor.alive: 
                        self.game_controller.state_manager.set_state(GAME_STATE_GAME_OVER)

    def _handle_physical_collisions(self, current_state):
        # Player collisions
        if self.player and self.player.alive:
            # Enemy collisions
            enemy_hits = spritecollide(self.player, self.enemy_manager.get_sprites(), False, collide_rect_ratio(0.7))
            for enemy in enemy_hits:
                if enemy.alive: 
                    self.player.take_damage(34, sound_key_on_hit='crash') 
                    enemy.take_damage(50) 
                    if not enemy.alive: 
                        self.game_controller.level_manager.add_score(10)
                        self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, 15, None, True)
                        self.game_controller.check_for_all_enemies_killed()
                    if not self.player.alive: 
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                        return

            # Boss collision
            if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
                if self.player.collision_rect.colliderect(self.maze_guardian.collision_rect):
                    self.player.take_damage(50, sound_key_on_hit='crash') 
                    if not self.player.alive: 
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
            
            # Glitching wall collisions
            if self.game_controller.glitching_walls_group:
                glitch_hits = spritecollide(self.player, self.game_controller.glitching_walls_group, False, 
                                          collided=lambda p, w: w.is_solid)
                
                for wall in glitch_hits:
                    self.player.take_damage(wall.damage, sound_key_on_hit='crash')
                    if not self.player.alive:
                        self.game_controller._handle_player_death_or_life_loss("Destroyed by a system glitch!")
                        return

            # Barricade collisions (push player away)
            barricade_hits = spritecollide(self.player, self.spawned_barricades_group, False, collide_rect_ratio(0.9))
            for barricade in barricade_hits:
                if barricade.alive:
                    self._push_away(self.player, barricade)
                    self.player.take_damage(5, 'crash')

        # Enemy-reactor collisions
        if current_state == GAME_STATE_MAZE_DEFENSE and self.core_reactor and self.core_reactor.alive:
            enemies = self.game_controller.tower_defense_manager.enemies_group if hasattr(self.game_controller, 'tower_defense_manager') else self.enemy_manager.get_sprites()
            reactor_hits = spritecollide(self.core_reactor, enemies, True, collide_rect_ratio(0.7))
            for enemy in reactor_hits:
                damage = getattr(enemy, 'contact_damage', 25)
                info(f"Enemy hit core reactor for {damage} damage")
                self.core_reactor.take_damage(damage, self.game_controller) 
                self.game_controller._create_enemy_explosion(enemy.rect.centerx, enemy.rect.centery)
                if not self.core_reactor.alive: 
                    info("Core reactor destroyed!")
                    self.game_controller.state_manager.set_state(GAME_STATE_GAME_OVER)
        
        # Enemy-barricade collisions
        for enemy in list(self.enemy_manager.get_sprites()):
            if enemy.alive:
                barricade_hits = spritecollide(enemy, self.spawned_barricades_group, False, collide_rect_ratio(0.7))
                for barricade in barricade_hits:
                    if barricade.alive:
                        enemy.take_damage(10)
                        barricade.take_damage(enemy.contact_damage)
                        self._push_away(enemy, barricade)

    def _push_away(self, obj1, obj2):
        """Push obj1 away from obj2"""
        dx = obj1.x - obj2.x
        dy = obj1.y - obj2.y
        dist = hypot(dx, dy)
        if dist > 0:
            overlap = (obj1.rect.width / 2 + obj2.rect.width / 2) - dist
            if overlap > 0:
                obj1.x += (dx / dist) * overlap
                obj1.y += (dy / dist) * overlap
                obj1.rect.center = (int(obj1.x), int(obj1.y))
                obj1.collision_rect.center = obj1.rect.center

    def _handle_player_power_up_collisions(self):
        powerup_hits = spritecollide(self.player, self.power_ups_group, True, collide_rect_ratio(0.7))
        for item in powerup_hits:
            if hasattr(item, 'apply_effect'):
                item.apply_effect(self.player, self.game_controller)
                self.game_controller.play_sound('weapon_upgrade_collect') 
                self.game_controller.level_manager.add_score(25)

    def _update_power_ups(self, current_time_ms):
        # Update existing power-ups
        for p_up in list(self.power_ups_group): 
            if p_up.update(): 
                p_up.kill()
        
        # Spawn new power-ups in playing state
        current_state = self.game_controller.state_manager.get_current_state_id()
        if current_state == GAME_STATE_PLAYING: 
            spawn_chance = get_setting("powerups", "POWERUP_SPAWN_CHANCE", 0.05)
            fps = get_setting("display", "FPS", 60)
            if random() < (spawn_chance / fps if fps > 0 else 0.01):
                if len(self.power_ups_group) < get_setting("powerups", "MAX_POWERUPS_ON_SCREEN", 2):
                    self._spawn_powerup()

    def _spawn_powerup(self):
        if not self.maze or not self.player: 
            return
            
        spawn_pos = self.game_controller._get_safe_spawn_point(
            get_setting("powerups", "POWERUP_SIZE", 26), 
            get_setting("powerups", "POWERUP_SIZE", 26)
        )
        if not spawn_pos: 
            return
        
        powerup_types = {
            "weapon_upgrade": WeaponUpgradeItem,
            "shield": ShieldItem,
            "speed_boost": SpeedBoostItem
        }
        
        chosen_type = choice(list(powerup_types.keys()))
        powerup_class = powerup_types[chosen_type]
        new_powerup = powerup_class(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        
        if new_powerup: 
            self.power_ups_group.add(new_powerup)
    
    def reset_combat_state(self):
        self.enemy_manager.reset_all()
        self.wave_manager.reset() 
        
        # Clear all groups
        for group in [self.turrets_group, self.power_ups_group, self.explosion_particles_group, 
                     self.spawned_barricades_group]:
            group.empty()
            
        self.game_controller.glitching_walls_group.empty()
        
        # Clear player projectiles
        if self.player:
            for attr in ['bullets_group', 'missiles_group', 'lightning_zaps_group', 'spawned_barricades_group']:
                if hasattr(self.player, attr):
                    getattr(self.player, attr).empty()
                    
        # Reset boss state
        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False
        self.core_reactor = None
        self.architect_vault_gauntlet_current_wave = 0
        
    def try_place_turret(self, world_pos):
        if not hasattr(self.game_controller, 'tower_defense_manager') or not self.game_controller.is_build_phase:
            return False
            
        # Check for existing turret
        for turret in self.turrets_group:
            if turret.rect.collidepoint(world_pos):
                info("Cannot place turret - position occupied")
                return False
            
        return self.game_controller.tower_defense_manager.try_place_tower(world_pos, self.asset_manager)
        
    def try_upgrade_clicked_turret(self, world_pos):
        if not hasattr(self.game_controller, 'tower_defense_manager') or not self.game_controller.is_build_phase:
            return False
            
        # Find turret at position
        clicked_turret = None
        for turret in self.turrets_group:
            if turret.rect.collidepoint(world_pos):
                clicked_turret = turret
                break
                
        if not clicked_turret:
            info("No turret found at position")
            return False
            
        # Check upgrade eligibility
        if clicked_turret.upgrade_level >= clicked_turret.MAX_UPGRADE_LEVEL:
            info("Turret already at max level")
            return False
            
        # Check resources
        upgrade_cost = clicked_turret.UPGRADE_COST
        cores = self.game_controller.drone_system.get_cores()
        if cores < upgrade_cost:
            info(f"Not enough cores (need {upgrade_cost})")
            return False
            
        # Upgrade
        if clicked_turret.upgrade():
            self.game_controller.drone_system.spend_cores(upgrade_cost)
            info(f"Turret upgraded to level {clicked_turret.upgrade_level}")
            return True
            
        return False
        
    def _handle_maze_guardian_defeated(self):
        if self.maze_guardian_defeat_processed:
            return
            
        self.maze_guardian_defeat_processed = True
        
        # Rewards
        if hasattr(self.game_controller, 'level_manager'):
            self.game_controller.level_manager.add_score(1000)
            
        if hasattr(self.game_controller, 'drone_system'):
            self.game_controller.drone_system.add_cores(100)
            
        if hasattr(self.game_controller, 'set_story_message'):
            self.game_controller.set_story_message("Maze Guardian defeated!", 3000)
            
        info("Maze Guardian defeated!")
        
    def _spawn_orichalc_fragment(self, x, y):
        info(f"Spawning orichalc fragment at ({x}, {y})")
        from entities.orichalc_fragment import OrichalcFragment
        fragment = OrichalcFragment(x, y, asset_manager=self.asset_manager)
        if hasattr(self.game_controller, 'core_fragments_group'):
            self.game_controller.core_fragments_group.add(fragment)
            info(f"Added fragment to group, size: {len(self.game_controller.core_fragments_group)}")
        else:
            error("game_controller missing core_fragments_group")