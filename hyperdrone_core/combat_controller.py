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

# Entities will be passed as references, but good to note what's expected
from entities import (
    PlayerDrone, Enemy, SentinelDrone, MazeGuardian,
    Bullet, Missile, LightningZap, Particle,
    WeaponUpgradeItem, ShieldItem, SpeedBoostItem,
    Turret, CoreReactor, MazeChapter2 # Added MazeChapter2 for type checking
)

# Managers that CombatController will likely interact with or manage
from .enemy_manager import EnemyManager
from .wave_manager import WaveManager


class CombatController:
    """
    Manages all combat-related logic, including player and enemy actions,
    weapon systems, projectile handling, boss fights, and defense mode combat.
    """
    def __init__(self, game_controller_ref):
        """
        Initializes the CombatController.

        Args:
            game_controller_ref: A reference to the main GameController instance,
                                 providing access to shared game objects and methods.
        """
        self.game_controller = game_controller_ref
        self.player = None # Will be set by GameController
        self.maze = None   # Will be set by GameController
        
        # Initialize managers that this controller will oversee
        self.enemy_manager = EnemyManager(game_controller_ref)
        self.wave_manager = WaveManager(game_controller_ref) # For defense mode

        # Sprite groups for combat-related entities (these might be shared or owned)
        # GameController will likely still own the main groups, and CombatController gets references
        self.turrets_group = pygame.sprite.Group() # For defense mode
        self.power_ups_group = pygame.sprite.Group()
        self.explosion_particles_group = pygame.sprite.Group()

        # Boss specific
        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False

        # Defense mode specific
        self.core_reactor = None # Will be set by GameController for defense mode

        # Timers or state flags specific to combat sequences
        self.architect_vault_gauntlet_current_wave = 0
        # Other combat-specific states can be added here

        print("CombatController initialized.")

    def set_active_entities(self, player, maze, core_reactor=None, turrets_group=None, power_ups_group=None, explosion_particles_group=None):
        """
        Sets references to currently active game entities and groups.
        Called by GameController when a game session starts or changes.
        """
        self.player = player
        self.maze = maze
        self.core_reactor = core_reactor # For defense mode
        self.turrets_group = turrets_group if turrets_group is not None else pygame.sprite.Group()
        self.power_ups_group = power_ups_group if power_ups_group is not None else pygame.sprite.Group()
        self.explosion_particles_group = explosion_particles_group if explosion_particles_group is not None else pygame.sprite.Group()
        
        # Reset boss state if player is being set (e.g., new game)
        self.maze_guardian = None
        self.boss_active = False
        self.maze_guardian_defeat_processed = False


    def update(self, current_time_ms, delta_time_ms):
        """
        Main update loop for the CombatController.
        Called every frame by the GameController.

        Args:
            current_time_ms (int): The current game time in milliseconds.
            delta_time_ms (int): The time elapsed since the last frame in milliseconds.
        """
        # Guard clause: if crucial references are missing, don't update.
        # Player and maze are essential for most combat logic.
        # For Maze Defense, player might be None, but maze and core_reactor should exist.
        current_game_state = self.game_controller.scene_manager.get_current_state()
        if current_game_state != GAME_STATE_MAZE_DEFENSE and (not self.player or not self.maze):
            return 
        if current_game_state == GAME_STATE_MAZE_DEFENSE and (not self.maze or not self.core_reactor):
            return


        # Player update (movement is handled by PlayerActions, combat aspects here)
        # Player object might not exist in Maze Defense mode if it's purely AI vs AI.
        if self.player and self.player.alive:
            # Player's projectiles are updated within player.update()
            # Player power-ups are updated within player.update()
            pass # Player shooting is typically event-driven via PlayerActions

        # Enemy updates (delegated to EnemyManager)
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

        # Boss updates (if active)
        if self.boss_active and self.maze_guardian:
            if self.maze_guardian.alive:
                self.maze_guardian.update(player_pos_pixels, self.maze, current_time_ms, game_area_x_offset)
            elif not self.maze_guardian_defeat_processed:
                self._handle_maze_guardian_defeated() # Handle defeat logic once

        # Turret updates (for defense mode)
        if is_defense_mode_active:
            self.turrets_group.update(self.enemy_manager.get_sprites(), self.maze, game_area_x_offset) # Pass necessary args
            if self.core_reactor and not self.core_reactor.alive:
                self.game_controller.scene_manager.set_game_state(gs.GAME_STATE_GAME_OVER) # Or a specific defense_lost state
                return

        # Wave manager updates (for defense mode)
        if is_defense_mode_active and self.wave_manager:
            self.wave_manager.update(current_time_ms, delta_time_ms)
            if self.wave_manager.all_waves_cleared and self.enemy_manager.get_active_enemies_count() == 0:
                 if hasattr(self.game_controller, 'handle_maze_defense_victory'):
                    self.game_controller.handle_maze_defense_victory()


        # Power-up updates (spawning and individual updates)
        self._update_power_ups(current_time_ms)

        # Collision detection
        self._handle_collisions(current_game_state)

        # Particle updates
        self.explosion_particles_group.update()


    def _handle_collisions(self, current_game_state):
        """Handles all combat-related collisions."""
        # Player might not exist in some modes (e.g., pure AI vs AI defense)
        if not self.player and current_game_state != GAME_STATE_MAZE_DEFENSE : # If player is expected but missing
            return
        if self.player and not self.player.alive and current_game_state != GAME_STATE_MAZE_DEFENSE: # If player exists but is dead
             # Still process enemy projectiles if player is dead but turrets/reactor might be hit
            if current_game_state == GAME_STATE_MAZE_DEFENSE:
                self._handle_enemy_projectile_collisions(current_game_state)
            return


        # 1. Player Projectiles vs. Enemies / Boss
        if self.player and self.player.alive: # Only if player is alive and can shoot
            self._handle_player_projectile_collisions()

        # 2. Enemy/Boss Projectiles vs. Player / Turrets / Reactor
        self._handle_enemy_projectile_collisions(current_game_state)

        # 3. Turret Projectiles vs. Enemies (NEW)
        if current_game_state == GAME_STATE_MAZE_DEFENSE:
            self._handle_turret_projectile_collisions()

        # 4. Physical Collisions (Player vs. Enemy/Boss, Enemy vs. Reactor)
        self._handle_physical_collisions(current_game_state)
        
        # 5. Player vs. Power-ups
        if self.player and self.player.alive: # Only if player is alive and can collect
            self._handle_player_power_up_collisions()

    def _handle_turret_projectile_collisions(self):
        """Handles collisions of turret projectiles with enemies."""
        if not self.turrets_group or not self.enemy_manager:
            return

        enemies_to_check = self.enemy_manager.get_sprites()
        if not enemies_to_check: # No enemies to hit
            return

        for turret in self.turrets_group:
            turret_projectiles = pygame.sprite.Group()
            if hasattr(turret, 'bullets'): turret_projectiles.add(turret.bullets)
            if hasattr(turret, 'missiles'): turret_projectiles.add(turret.missiles)
            if hasattr(turret, 'lightning_zaps'): turret_projectiles.add(turret.lightning_zaps)

            for projectile in list(turret_projectiles): # Iterate over a copy
                if not projectile.alive:
                    continue
                
                # Turret projectile vs. Regular Enemies
                hit_enemies = pygame.sprite.spritecollide(
                    projectile, enemies_to_check, False, # False: don't kill enemy on collision yet
                    lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
                )
                for enemy in hit_enemies:
                    if enemy.alive:
                        damage_to_enemy = projectile.damage
                        if isinstance(projectile, LightningZap): # Specific handling for lightning
                            # Lightning from turrets might have different properties or just use its base damage
                            damage_to_enemy = projectile.damage # Use the zap's defined damage

                        enemy.take_damage(damage_to_enemy)
                        if not enemy.alive:
                            # Score/Cores for turret kills might be different or not awarded
                            # self.game_controller.score += 20 # Example: Turret kill score
                            # self.game_controller.drone_system.add_player_cores(5) # Example: Turret kill cores
                            self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, specific_sound='enemy_shoot')
                            
                            # In defense mode, check if wave clear conditions are met
                            if self.game_controller.scene_manager.get_current_state() == GAME_STATE_MAZE_DEFENSE:
                                if self.wave_manager and not self.wave_manager.is_build_phase_active and \
                                   self.enemy_manager.get_active_enemies_count() == 0 and \
                                   self.wave_manager.current_group_index >= len(self.wave_manager.current_wave_enemy_groups):
                                    # This check might be better placed in WaveManager's update or CombatController's main update
                                    pass # Wave clear is handled in WaveManager update

                        # Handle piercing for turret bullets
                        if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                            projectile.pierces_done +=1
                        
                        if not projectile.alive:
                            break # Projectile destroyed
    
    def _handle_player_projectile_collisions(self):
        """Handles collisions of player's projectiles with enemies and boss."""
        if not self.player or not self.player.alive:
            return

        player_projectiles = pygame.sprite.Group()
        if hasattr(self.player, 'bullets_group'): player_projectiles.add(self.player.bullets_group)
        if hasattr(self.player, 'missiles_group'): player_projectiles.add(self.player.missiles_group)
        if hasattr(self.player, 'lightning_zaps_group'): player_projectiles.add(self.player.lightning_zaps_group)

        enemies_to_check = self.enemy_manager.get_sprites()

        for projectile in list(player_projectiles): # Iterate over a copy
            if not projectile.alive:
                continue

            # Player projectile vs. Maze Guardian Corners
            if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
                hit_a_corner = False
                for corner in self.maze_guardian.corners:
                    if corner['status'] != 'destroyed' and projectile.rect.colliderect(corner['rect']):
                        damage_to_corner = projectile.damage
                        if isinstance(projectile, LightningZap): # Specific damage for lightning
                            damage_to_corner = gs.get_game_setting("LIGHTNING_DAMAGE", 15) 
                        
                        if self.maze_guardian.damage_corner(corner['id'], damage_to_corner):
                            self.game_controller.score += 250
                            self.game_controller.drone_system.add_player_cores(25)
                        
                        hit_a_corner = True
                        if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                            projectile.kill()
                        elif hasattr(projectile, 'pierces_done'):
                             projectile.pierces_done +=1
                        break # Projectile hits one corner, then is done or pierces
                if hit_a_corner and not projectile.alive:
                    continue # Move to next projectile if this one was destroyed

            # Player projectile vs. Regular Enemies
            # Use collision_rect for enemies if available
            hit_enemies = pygame.sprite.spritecollide(
                projectile, enemies_to_check, False, # False: don't kill enemy on collision yet
                lambda proj, enemy: proj.rect.colliderect(getattr(enemy, 'collision_rect', enemy.rect))
            )
            for enemy in hit_enemies:
                if enemy.alive:
                    damage_to_enemy = projectile.damage
                    if isinstance(projectile, LightningZap): # Lightning one-shots regular enemies
                        damage_to_enemy = float('inf') 
                    
                    enemy.take_damage(damage_to_enemy)
                    if not enemy.alive:
                        self.game_controller.score += 50 # Standard enemy score
                        self.game_controller.drone_system.add_player_cores(10) # Standard enemy core reward
                        self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, specific_sound='enemy_shoot') # Use a generic enemy explosion sound
                        # Check for level clear condition if in standard playing mode
                        if self.game_controller.scene_manager.get_current_state() == GAME_STATE_PLAYING:
                            self.game_controller.all_enemies_killed_this_level = all(not e.alive for e in enemies_to_check)
                            if self.game_controller.all_enemies_killed_this_level:
                                self.game_controller._check_level_clear_condition()
                    
                    # Handle piercing
                    if not (hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces):
                        projectile.kill() # Kill projectile if it cannot pierce or has pierced max times
                    elif hasattr(projectile, 'pierces_done'):
                        projectile.pierces_done +=1 # Increment pierce count
                    
                    if not projectile.alive:
                        break # Projectile destroyed, move to next projectile

    def _handle_enemy_projectile_collisions(self, current_game_state):
        """Handles collisions of enemy/boss projectiles with player, turrets, reactor."""
        all_hostile_projectiles = pygame.sprite.Group()
        for enemy in self.enemy_manager.get_sprites():
            if hasattr(enemy, 'bullets'): all_hostile_projectiles.add(enemy.bullets)
        
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            if hasattr(self.maze_guardian, 'bullets'): all_hostile_projectiles.add(self.maze_guardian.bullets)
            if hasattr(self.maze_guardian, 'laser_beams'): all_hostile_projectiles.add(self.maze_guardian.laser_beams)

        for projectile in list(all_hostile_projectiles): # Iterate over a copy
            if not projectile.alive: continue

            # Hostile projectile vs. Player
            if self.player and self.player.alive and projectile.rect.colliderect(self.player.collision_rect):
                self.player.take_damage(projectile.damage, self.game_controller.sounds.get('crash'))
                if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent): 
                    projectile.kill()
                if not self.player.alive: 
                    self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                if not projectile.alive: continue 

            # Hostile projectile vs. Turrets (Defense Mode)
            if current_game_state == GAME_STATE_MAZE_DEFENSE and self.turrets_group:
                hit_turrets = pygame.sprite.spritecollide(projectile, self.turrets_group, False) # False: don't kill turret yet
                for turret in hit_turrets:
                    if hasattr(turret, 'take_damage'): 
                        turret.take_damage(projectile.damage) 
                    if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent):
                        projectile.kill()
                    if not projectile.alive: break 
                if not projectile.alive: continue

            # Hostile projectile vs. Core Reactor (Defense Mode)
            if current_game_state == GAME_STATE_MAZE_DEFENSE and self.core_reactor and self.core_reactor.alive:
                if projectile.rect.colliderect(self.core_reactor.rect):
                    self.core_reactor.take_damage(projectile.damage, self.game_controller) 
                    if not (hasattr(projectile, 'is_persistent') and projectile.is_persistent):
                        projectile.kill()
                    if not self.core_reactor.alive:
                        self.game_controller.scene_manager.set_game_state(gs.GAME_STATE_GAME_OVER) 
                    if not projectile.alive: continue
            
            # Hostile projectile vs. Walls (if not piercing)
            if self.maze and not getattr(projectile, 'can_pierce_walls', False):
                 if self.maze.is_wall(projectile.rect.centerx, projectile.rect.centery, projectile.rect.width, projectile.rect.height):
                    projectile.kill()
                    continue


    def _handle_physical_collisions(self, current_game_state):
        """Handles physical collisions: Player vs Enemy/Boss, Enemy vs Reactor."""
        # Player vs. Enemy/Boss (only if player exists and is alive)
        if self.player and self.player.alive:
            enemies_collided_player = pygame.sprite.spritecollide(
                self.player, self.enemy_manager.get_sprites(), False, # False: don't kill enemy on collision
                lambda p, e: p.collision_rect.colliderect(getattr(e, 'collision_rect', e.rect))
            )
            for enemy in enemies_collided_player:
                if enemy.alive: # Ensure enemy is also alive for mutual damage
                    self.player.take_damage(34, self.game_controller.sounds.get('crash')) # Player takes damage
                    enemy.take_damage(50) # Enemy also takes some damage from collision
                    if not enemy.alive: # If enemy died from collision
                         self.game_controller.score += 10 # Small score for collision kill
                         self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, specific_sound='crash')

                    if not self.player.alive: # If player died
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                        return # Player died, no more checks needed for player

            if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
                if self.player.collision_rect.colliderect(self.maze_guardian.collision_rect):
                    self.player.take_damage(50, self.game_controller.sounds.get('crash')) # Higher boss collision damage
                    # Boss might also take some damage or have a special reaction
                    if not self.player.alive:
                        self.game_controller._handle_player_death_or_life_loss("Drone Destroyed!")
                        return

        # Enemy vs. Core Reactor (Defense Mode)
        if current_game_state == GAME_STATE_MAZE_DEFENSE and self.core_reactor and self.core_reactor.alive:
            enemies_hitting_reactor = pygame.sprite.spritecollide(
                self.core_reactor, self.enemy_manager.get_sprites(), True, # True to kill enemy on impact with reactor
                pygame.sprite.collide_rect_ratio(0.7) # Use a reasonable collision ratio
            )
            for enemy in enemies_hitting_reactor:
                contact_dmg = getattr(enemy, 'contact_damage', 25) # Use enemy's specific contact damage
                self.core_reactor.take_damage(contact_dmg, self.game_controller) # Pass GC for sound
                self.game_controller._create_explosion(enemy.rect.centerx, enemy.rect.centery, specific_sound='crash')
                if not self.core_reactor.alive:
                    self.game_controller.scene_manager.set_game_state(gs.GAME_STATE_GAME_OVER) # Or defense_lost
                    return

    def _handle_player_power_up_collisions(self):
        """Handles player collision with power-up items."""
        if not self.player or not self.player.alive or not self.power_ups_group:
            return

        collided_powerups = pygame.sprite.spritecollide(
            self.player, self.power_ups_group, False, pygame.sprite.collide_rect_ratio(0.7) # False: don't kill yet
        )
        for item in collided_powerups:
            if not item.collected and not item.expired and hasattr(item, 'apply_effect'):
                item.apply_effect(self.player) 
                item.collected = True # Mark as collected
                item.kill() # Remove from power_ups_group after applying effect
                self.game_controller.play_sound('weapon_upgrade_collect') 
                self.game_controller.score += 25


    def _update_power_ups(self, current_time_ms):
        """Updates existing power-ups and potentially spawns new ones."""
        for p_up in list(self.power_ups_group): # Iterate over a copy for safe removal
            if p_up.update(): # update_collectible_state returns True if expired/collected
                p_up.kill()

        current_game_state = self.game_controller.scene_manager.get_current_state()
        if current_game_state == GAME_STATE_PLAYING: 
            if random.random() < (gs.get_game_setting("POWERUP_SPAWN_CHANCE") / gs.FPS if gs.FPS > 0 else 0.01):
                if len(self.power_ups_group) < gs.get_game_setting("MAX_POWERUPS_ON_SCREEN"):
                    self._try_spawn_powerup_item_internal()


    def _try_spawn_powerup_item_internal(self):
        """Internal logic to spawn a random power-up item."""
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
        
        if new_powerup:
            self.power_ups_group.add(new_powerup)


    def spawn_maze_guardian(self):
        """Spawns the Maze Guardian boss."""
        if not self.player or not self.maze: return

        self.enemy_manager.reset_all() 
        
        boss_spawn_x = self.maze.game_area_x_offset + (gs.WIDTH - self.maze.game_area_x_offset) / 2
        boss_spawn_y = gs.GAME_PLAY_AREA_HEIGHT / 2
        
        self.maze_guardian = MazeGuardian(
            x=boss_spawn_x, y=boss_spawn_y,
            player_ref=self.player,
            maze_ref=self.maze,
            game_controller_ref=self.game_controller 
        )
        self.boss_active = True
        self.maze_guardian_defeat_processed = False
        self.game_controller.play_sound('boss_intro', 0.8)
        print("CombatController: Maze Guardian spawned.")

    def _handle_maze_guardian_defeated(self):
        """Handles logic when the Maze Guardian is defeated."""
        if self.maze_guardian_defeat_processed: return

        self.game_controller.score += 5000
        self.game_controller.drone_system.add_player_cores(1500)
        self.game_controller.drone_system.add_defeated_boss("MAZE_GUARDIAN")
        
        self.game_controller.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB01")
        self.game_controller.trigger_story_beat("story_beat_SB01")

        vault_core_id = "vault_core"
        vault_core_details = CORE_FRAGMENT_DETAILS.get("fragment_vault_core")
        if vault_core_details and not self.game_controller.drone_system.has_collected_fragment(vault_core_id):
            if self.game_controller.drone_system.collect_core_fragment(vault_core_id):
                print(f"CombatController: Vault Core Fragment '{vault_core_id}' collected after boss defeat.")
                self.game_controller.set_story_message(f"Lore Unlocked: {vault_core_details.get('name', 'Vault Core Data')}")


        self.boss_active = False
        if self.maze_guardian: self.maze_guardian.kill(); self.maze_guardian = None 
        self.maze_guardian_defeat_processed = True
        
        if self.game_controller.scene_manager.get_current_state() == GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT:
            self.game_controller.architect_vault_message = "MAZE GUARDIAN DEFEATED! ACCESS GRANTED!"
            self.game_controller.architect_vault_message_timer = pygame.time.get_ticks() + 4000
        
        print("CombatController: Maze Guardian defeated processing complete.")

    def reset_combat_state(self):
        """Resets combat-specific states for a new game or level."""
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
        print("CombatController: Combat state reset.")

    # --- Turret specific methods for Defense Mode ---
    def try_place_turret(self, screen_pos):
        """Attempts to place a turret at the given screen position."""
        if not self.maze or not self.core_reactor or \
           not isinstance(self.maze, MazeChapter2): # Ensure it's the correct maze type
            self.game_controller.play_sound('ui_denied', 0.6)
            print("CombatController: Cannot place turret - not in MazeChapter2 defense mode or maze/reactor missing.")
            return False

        # Convert screen position to grid position
        grid_c = int((screen_pos[0] - self.maze.game_area_x_offset) / TILE_SIZE)
        grid_r = int(screen_pos[1] / TILE_SIZE)

        # Validate grid position boundaries
        if not (0 <= grid_r < self.maze.actual_maze_rows and \
                0 <= grid_c < self.maze.actual_maze_cols):
            self.game_controller.play_sound('ui_denied', 0.6)
            print(f"CombatController: Turret placement out of bounds: ({grid_r},{grid_c})")
            return False
        
        # Check if the player has enough turrets left to place
        max_turrets_allowed = Turret.MAX_TURRETS # Use constant from Turret class
        if len(self.turrets_group) >= max_turrets_allowed:
            self.game_controller.play_sound('ui_denied', 0.6)
            print(f"CombatController: Max turrets ({max_turrets_allowed}) already placed.")
            return False

        # Use MazeChapter2's specific validation method
        if not self.maze.can_place_turret(grid_r, grid_c): # This now checks 'T' and path blocking
            self.game_controller.play_sound('ui_denied', 0.6)
            print(f"CombatController: MazeChapter2.can_place_turret returned false for ({grid_r},{grid_c}).")
            return False
        
        # Check cost
        turret_cost = Turret.TURRET_COST 
        if self.game_controller.drone_system.get_player_cores() >= turret_cost:
            if self.game_controller.drone_system.spend_player_cores(turret_cost):
                # Create turret at the center of the grid cell
                tile_center_x_abs = grid_c * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                tile_center_y_abs = grid_r * TILE_SIZE + TILE_SIZE // 2
                
                # Use the Turret class from entities
                new_turret = Turret(tile_center_x_abs, tile_center_y_abs, self.game_controller)
                self.turrets_group.add(new_turret)
                
                # Mark the spot as occupied in MazeChapter2's grid
                self.maze.mark_turret_spot_as_occupied(grid_r, grid_c) # New method in MazeChapter2
                
                self.game_controller.play_sound('turret_place_placeholder', 0.7)
                print(f"CombatController: Turret placed at grid ({grid_r},{grid_c}).")
                return True
        
        self.game_controller.play_sound('ui_denied', 0.6) 
        print(f"CombatController: Failed to place turret at ({grid_r},{grid_c}) - insufficient cores or other.")
        return False

    def try_upgrade_turret(self, turret_to_upgrade):
        """Attempts to upgrade the specified turret."""
        if turret_to_upgrade and turret_to_upgrade in self.turrets_group:
            upgrade_cost = Turret.UPGRADE_COST 
            if self.game_controller.drone_system.get_player_cores() >= upgrade_cost:
                if turret_to_upgrade.upgrade(): 
                    self.game_controller.drone_system.spend_player_cores(upgrade_cost)
                    self.game_controller.play_sound('weapon_upgrade_collect', 0.8)
                    print(f"CombatController: Turret at ({turret_to_upgrade.x},{turret_to_upgrade.y}) upgraded to level {turret_to_upgrade.upgrade_level}.")
                    if self.game_controller.ui_manager and self.game_controller.ui_manager.build_menu:
                        self.game_controller.ui_manager.build_menu.set_selected_turret(turret_to_upgrade)
                    return True
                else: 
                    self.game_controller.play_sound('ui_denied', 0.6)
            else: 
                self.game_controller.play_sound('ui_denied', 0.6)
        else: 
            self.game_controller.play_sound('ui_denied', 0.6)
        return False