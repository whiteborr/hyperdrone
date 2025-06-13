# hyperdrone_core/combat_controller.py
import pygame
import math
import random

from settings_manager import get_setting, set_setting, get_asset_path
from hyperdrone_core.constants import (
    WEAPON_MODES_SEQUENCE, POWERUP_TYPES,
    GAME_STATE_PLAYING, GAME_STATE_ARCHITECT_VAULT_GAUNTLET,
    GAME_STATE_ARCHITECT_VAULT_EXTRACTION, GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT,
    GAME_STATE_MAZE_DEFENSE
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
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        # Set reference to game_controller in asset_manager for enemy explosions
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
        
        # Get tile size from settings
        self.tile_size = get_setting("gameplay", "TILE_SIZE", 80)

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

        if self.player and self.player.alive:
            pass 

        player_pos_pixels = self.player.get_position() if self.player and self.player.alive else None
        game_area_x_offset = self.maze.game_area_x_offset if self.maze else 0
        
        is_defense_mode_active = (current_game_state == GAME_STATE_MAZE_DEFENSE)
        target_for_enemies = self.core_reactor.rect.center if is_defense_mode_active and self.core_reactor and self.core_reactor.alive else player_pos_pixels

        # Update tower defense manager if available
        if is_defense_mode_active and hasattr(self.game_controller, 'tower_defense_manager'):
            self.game_controller.tower_defense_manager.update(delta_time_ms)
            
            # Use pathfinding enemies if available
            if hasattr(self.game_controller.tower_defense_manager, 'enemies_group') and self.game_controller.tower_defense_manager.enemies_group:
                # We could integrate these with the regular enemy manager, but for now we'll keep them separate
                pass
            else:
                # Use regular enemy manager
                self.enemy_manager.update_enemies(
                    target_for_enemies, 
                    self.maze, 
                    current_time_ms, 
                    delta_time_ms,
                    game_area_x_offset,
                    is_defense_mode=is_defense_mode_active
                )
        else:
            # Regular enemy update
            self.enemy_manager.update_enemies(
                target_for_enemies, 
                self.maze, 
                current_time_ms, 
                delta_time_ms,
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
                self.game_controller.state_manager.set_state(gs.GAME_STATE_GAME_OVER) 
                return

        if is_defense_mode_active and self.wave_manager:
            self.wave_manager.update(current_time_ms, delta_time_ms)
            
            # Start a wave of pathfinding enemies if needed
            if hasattr(self.game_controller, 'tower_defense_manager') and self.wave_manager.is_wave_active and not self.wave_manager.is_build_phase_active:
                if not self.game_controller.tower_defense_manager.wave_active and self.wave_manager.current_wave_number > 0:
                    # Start a new wave of pathfinding enemies
                    enemies_count = 5 + (self.wave_manager.current_wave_number * 2)  # Scale with wave number
                    
                    # Get the current wave definition to use the same enemy types
                    current_wave_def = self.wave_manager.wave_definitions[self.wave_manager.current_wave_number - 1]
                    enemy_types = []
                    for group in current_wave_def:
                        enemy_type = group.get("enemy_type", "defense_drone_1")
                        count = group.get("count", 1)
                        enemy_types.extend([enemy_type] * count)
                    
                    self.game_controller.tower_defense_manager.start_wave(
                        self.wave_manager.current_wave_number, 
                        enemies_count,
                        enemy_types=enemy_types
                    )
            
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
                            damage_to_corner = get_setting("weapons", "LIGHTNING_DAMAGE", 15)
                        
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
                        # Create and dispatch the enemy defeated event
                        from hyperdrone_core.game_events import EnemyDefeatedEvent
                        event = EnemyDefeatedEvent(
                            score_value=50,
                            position=enemy.rect.center,
                            enemy_id=id(enemy)
                        )
                        self.game_controller.event_manager.dispatch(event)
                        
                        # Keep this check as it's not related to scoring or explosions
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
                        self.game_controller.state_manager.set_state(GAME_STATE_GAME_OVER) 
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

    def _update_power_ups(self, current_time_ms):
        for p_up in list(self.power_ups_group): 
            if p_up.update(): 
                p_up.kill()
        current_game_state = self.game_controller.state_manager.get_current_state_id()
        if current_game_state == GAME_STATE_PLAYING: 
            fps = get_setting("display", "FPS", 60)
            powerup_spawn_chance = get_setting("powerups", "POWERUP_SPAWN_CHANCE", 0.05)
            max_powerups = get_setting("powerups", "MAX_POWERUPS_ON_SCREEN", 2)
            
            if random.random() < (powerup_spawn_chance / fps if fps > 0 else 0.01):
                if len(self.power_ups_group) < max_powerups:
                    self._try_spawn_powerup_item_internal()

    def _try_spawn_powerup_item_internal(self):
        if not self.maze or not self.player: return
        powerup_size = get_setting("powerups", "POWERUP_SIZE", 26)
        spawn_pos = self.game_controller._get_safe_spawn_point(powerup_size, powerup_size)
        if not spawn_pos: return
        abs_x, abs_y = spawn_pos
        powerup_type_keys = list(POWERUP_TYPES.keys())
        if not powerup_type_keys: return
        chosen_type_key = random.choice(powerup_type_keys)
        new_powerup = None
        
        if chosen_type_key == "weapon_upgrade": new_powerup = WeaponUpgradeItem(abs_x, abs_y, asset_manager=self.asset_manager)
        elif chosen_type_key == "shield": new_powerup = ShieldItem(abs_x, abs_y, asset_manager=self.asset_manager)
        elif chosen_type_key == "speed_boost": new_powerup = SpeedBoostItem(abs_x, abs_y, asset_manager=self.asset_manager)
        
        if new_powerup: self.power_ups_group.add(new_powerup)

    def spawn_maze_guardian(self):
        if not self.player or not self.maze: return
        self.enemy_manager.reset_all() 
        width = get_setting("display", "WIDTH", 1920)
        game_play_area_height = get_setting("display", "HEIGHT", 1080) - get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        
        boss_spawn_x = self.maze.game_area_x_offset + (width - self.maze.game_area_x_offset) / 2
        boss_spawn_y = game_play_area_height / 2
        self.maze_guardian = MazeGuardian(x=boss_spawn_x, y=boss_spawn_y, 
                                          player_ref=self.player, maze_ref=self.maze, 
                                          game_controller_ref=self.game_controller,
                                          asset_manager=self.asset_manager)
        self.boss_active = True; self.maze_guardian_defeat_processed = False
        self.game_controller.play_sound('boss_intro', 0.8)

    def _handle_maze_guardian_defeated(self):
        if self.maze_guardian_defeat_processed: return
        self.game_controller.level_manager.add_score(5000); self.game_controller.drone_system.add_player_cores(1500)
        self.game_controller.drone_system.add_defeated_boss("MAZE_GUARDIAN")
        self.game_controller.trigger_story_beat("story_beat_SB01")
        
        vault_core_id = "vault_core"
        # Get core fragment details from settings manager
        vault_core_details = self.asset_manager.settings_manager.get_core_fragment_details().get("fragment_vault_core")
        if vault_core_details and not self.game_controller.drone_system.has_collected_fragment(vault_core_id):
            if self.game_controller.drone_system.collect_core_fragment(vault_core_id):
                self.game_controller.set_story_message(f"Lore Unlocked: {vault_core_details.get('name', 'Vault Core Data')}")
        
        self.boss_active = False
        if self.maze_guardian: self.maze_guardian.kill(); self.maze_guardian = None 
        self.maze_guardian_defeat_processed = True
        if self.game_controller.state_manager.get_current_state_id() == GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT:
            self.game_controller.set_story_message("MAZE GUARDIAN DEFEATED! ACCESS GRANTED!", 4000)

    def reset_combat_state(self):
        self.enemy_manager.reset_all(); self.wave_manager.reset() 
        self.turrets_group.empty(); self.power_ups_group.empty(); self.explosion_particles_group.empty()
        if self.player:
            if hasattr(self.player, 'bullets_group'): self.player.bullets_group.empty()
            if hasattr(self.player, 'missiles_group'): self.player.missiles_group.empty()
            if hasattr(self.player, 'lightning_zaps_group'): self.player.lightning_zaps_group.empty()
        self.maze_guardian = None; self.boss_active = False; self.maze_guardian_defeat_processed = False
        self.core_reactor = None; self.architect_vault_gauntlet_current_wave = 0

    def try_place_turret(self, screen_pos):
        if not self.maze or not self.core_reactor or not isinstance(self.maze, MazeChapter2):
            self.game_controller.play_sound('ui_denied', 0.6); return False
            
        # Use tower defense manager if available
        if hasattr(self.game_controller, 'tower_defense_manager'):
            # Check if we can place a tower at this position
            grid_c = int((screen_pos[0] - self.maze.game_area_x_offset) / self.tile_size)
            grid_r = int(screen_pos[1] / self.tile_size)
            
            # First check basic conditions
            if not (0 <= grid_r < self.maze.actual_maze_rows and 0 <= grid_c < self.maze.actual_maze_cols):
                self.game_controller.play_sound('ui_denied', 0.6); return False
                
            max_turrets_allowed = get_setting("defense_mode", "MAX_TURRETS_DEFENSE_MODE", 10)
            if len(self.turrets_group) >= max_turrets_allowed:
                self.game_controller.play_sound('ui_denied', 0.6); return False
                
            if not self.maze.can_place_turret(grid_r, grid_c):
                self.game_controller.play_sound('ui_denied', 0.6); return False
                
            # Check if player has enough resources
            turret_cost = get_setting("defense_mode", "TURRET_BASE_COST", 50)
            if self.game_controller.drone_system.get_player_cores() < turret_cost:
                self.game_controller.play_sound('ui_denied', 0.6); return False
                
            # For MazeChapter2, we should prioritize the maze's can_place_turret check
            # since it knows about designated turret spots
            if not self.maze.can_place_turret(grid_r, grid_c):
                self.game_controller.play_sound('ui_denied', 0.6)
                return False
                
            # Only check path blocking for non-designated spots
            if self.maze.grid[grid_r][grid_c] != 'T' and not self.game_controller.tower_defense_manager.path_manager.can_place_tower(grid_r, grid_c):
                self.game_controller.play_sound('ui_denied', 0.6)
                self.game_controller.set_story_message("Cannot place turret - would block all paths to core!", 2000)
                return False
                
            # Place the turret
            if self.game_controller.drone_system.spend_player_cores(turret_cost):
                tile_center_x_abs = grid_c * self.tile_size + self.tile_size//2 + self.maze.game_area_x_offset
                tile_center_y_abs = grid_r * self.tile_size + self.tile_size//2
                new_turret = Turret(tile_center_x_abs, tile_center_y_abs, self.game_controller, self.asset_manager)
                self.turrets_group.add(new_turret)
                self.maze.mark_turret_spot_as_occupied(grid_r, grid_c)
                
                # Update path manager grid
                self.game_controller.tower_defense_manager.path_manager.grid[grid_r][grid_c] = 'T'
                
                # Trigger path recalculation for all enemies
                self.game_controller.tower_defense_manager.recalculate_all_enemy_paths()
                
                self.game_controller.play_sound('turret_placement', 0.7)
                return True
        else:
            # Original implementation without path validation
            grid_c = int((screen_pos[0] - self.maze.game_area_x_offset) / self.tile_size)
            grid_r = int(screen_pos[1] / self.tile_size)
            
            if not (0 <= grid_r < self.maze.actual_maze_rows and 0 <= grid_c < self.maze.actual_maze_cols):
                self.game_controller.play_sound('ui_denied', 0.6); return False
            
            max_turrets_allowed = get_setting("defense_mode", "MAX_TURRETS_DEFENSE_MODE", 10)
            if len(self.turrets_group) >= max_turrets_allowed:
                self.game_controller.play_sound('ui_denied', 0.6); return False
                
            if not self.maze.can_place_turret(grid_r, grid_c):
                self.game_controller.play_sound('ui_denied', 0.6); return False
                
            turret_cost = get_setting("defense_mode", "TURRET_BASE_COST", 50)
            if self.game_controller.drone_system.get_player_cores() >= turret_cost:
                if self.game_controller.drone_system.spend_player_cores(turret_cost):
                    tile_center_x_abs = grid_c * self.tile_size + self.tile_size//2 + self.maze.game_area_x_offset
                    tile_center_y_abs = grid_r * self.tile_size + self.tile_size//2
                    new_turret = Turret(tile_center_x_abs, tile_center_y_abs, self.game_controller, self.asset_manager)
                    self.turrets_group.add(new_turret)
                    self.maze.mark_turret_spot_as_occupied(grid_r, grid_c) 
                    self.game_controller.play_sound('turret_placement', 0.7)
                    return True
                    
        self.game_controller.play_sound('ui_denied', 0.6)
        return False

    def try_upgrade_turret(self, turret_to_upgrade):
        if turret_to_upgrade and turret_to_upgrade in self.turrets_group:
            upgrade_cost = get_setting("defense_mode", "TURRET_UPGRADE_COST", 100)
            if self.game_controller.drone_system.get_player_cores() >= upgrade_cost:
                if turret_to_upgrade.upgrade(): 
                    self.game_controller.drone_system.spend_player_cores(upgrade_cost)
                    self.game_controller.play_sound('weapon_upgrade_collect', 0.8)
                    if self.game_controller.ui_manager and self.game_controller.ui_manager.build_menu:
                        self.game_controller.ui_manager.build_menu.set_selected_turret(turret_to_upgrade)
                    return True
        self.game_controller.play_sound('ui_denied', 0.6); return False

    def try_upgrade_clicked_turret(self, world_pos):
        """Finds a turret at the given world position and attempts to upgrade it."""
        clicked_turret = None
        for turret in self.turrets_group:
            if turret.rect.collidepoint(world_pos):
                clicked_turret = turret
                break 

        if clicked_turret:
            return self.try_upgrade_turret(clicked_turret)
        
        return False