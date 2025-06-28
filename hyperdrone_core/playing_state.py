# hyperdrone_core/playing_state.py
from pygame.sprite import spritecollide
from pygame.time import get_ticks
from pygame import KEYDOWN, KEYUP, K_p, K_TAB
from .state import State
from settings_manager import get_setting

class PlayingState(State):
    def enter(self, previous_state=None, **kwargs):
        # Reset controllers
        self.game.combat_controller.reset_combat_state()
        self.game.puzzle_controller.reset_puzzles_state()
        
        # Clear collectible groups
        groups_to_clear = [
            self.game.collectible_rings_group, self.game.power_ups_group,
            self.game.core_fragments_group, self.game.vault_logs_group,
            self.game.glyph_tablets_group, self.game.architect_echoes_group
        ]
        for group in groups_to_clear:
            group.empty()
        
        # Initialize maze and player
        self._setup_maze_and_player()
        
        # Setup controllers
        self.game.combat_controller.set_active_entities(
            player=self.game.player, maze=self.game.maze, power_ups_group=self.game.power_ups_group
        )
        self.game.combat_controller.enemy_manager.spawn_enemies_for_level(self.game.level_manager.level)
        
        self.game.puzzle_controller.set_active_entities(
            player=self.game.player, drone_system=self.game.drone_system, scene_manager=self.game.state_manager
        )
        
        # Reset camera and timer
        self.game.camera = None
        self._setup_timer()
        
        # Setup items
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.reset_for_level()
            self.game.item_manager._spawn_all_rings(self.game.maze)
            
        # Show level message
        self._show_level_message()

    def _setup_maze_and_player(self):
        self.game.maze = self.game.level_manager.create_maze()
        tile_size = get_setting("display", "TILE_SIZE", 64)
        spawn_x, spawn_y = self.game._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
        
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        
        from entities import PlayerDrone
        self.game.player = PlayerDrone(
            spawn_x, spawn_y, drone_id, drone_stats, 
            self.game.asset_manager, sprite_key, 'crash', self.game.drone_system
        )

    def _setup_timer(self):
        self.game.level_timer_start_ticks = get_ticks()
        self.game.level_time_remaining_ms = get_setting("progression", "LEVEL_TIMER_DURATION", 120000)
        
        if hasattr(self.game, 'level_manager'):
            self.game.level_manager.level_start_time = self.game.level_timer_start_ticks
            self.game.level_manager.timer_paused = False
            self.game.level_manager.total_paused_time = 0

    def _show_level_message(self):
        current_chapter = self.game.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            level_msg = f"Chapter 1 - Level {self.game.level_manager.chapter1_level} of {self.game.level_manager.chapter1_max_levels}"
            self.game.set_story_message(level_msg, 3000)
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    self.game.toggle_pause()
                elif event.key == K_TAB and self.game.player:
                    self.game.player.cycle_weapon_state()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        current_time_ms = get_ticks()
        
        if not self.game.player:
            return
            
        # Update player
        self.game.player.update(
            current_time_ms, self.game.maze, 
            self.game.combat_controller.enemy_manager.get_sprites(), 
            self.game.player_actions, 
            self.game.maze.game_area_x_offset if self.game.maze else 0
        )
        
        # Check player death
        if not self.game.player.alive:
            self.game._handle_player_death_or_life_loss()
            return
        
        # Update systems
        self.game.combat_controller.update(current_time_ms, delta_time)
        
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.update(current_time_ms, self.game.maze)
            
        self.game._handle_collectible_collisions()
        self._handle_bullet_enemy_collisions()
        
        # Check level completion
        if self.game._check_level_clear_condition():
            return
        
        # Check Chapter 1 objectives
        self._check_chapter1_objectives()
        
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)

    def _check_chapter1_objectives(self):
        current_chapter = self.game.story_manager.get_current_chapter()
        if not (current_chapter and current_chapter.chapter_id == "chapter_1"):
            return
            
        # Only check objectives on final level
        if self.game.level_manager.chapter1_level < self.game.level_manager.chapter1_max_levels:
            return
            
        # Check ring collection
        if self.game.level_manager.collected_rings_count >= self.game.level_manager.total_rings_per_level:
            self.game.story_manager.complete_objective_by_id("c1_collect_rings")

        # Check enemy elimination
        if self.game.combat_controller.enemy_manager.get_active_enemies_count() == 0:
            self.game.story_manager.complete_objective_by_id("c1_clear_hostiles")

        # Check chapter completion
        if current_chapter.is_complete():
            self.game.story_manager.advance_chapter()
            self.game.state_manager.set_state("StoryMapState")

    def _handle_bullet_enemy_collisions(self):
        if not self.game.player or not hasattr(self.game.player, 'bullets_group'):
            return
            
        enemy_sprites = self.game.combat_controller.enemy_manager.get_sprites()
        if not enemy_sprites:
            return
            
        # Handle bullets
        for bullet in list(self.game.player.bullets_group):
            for enemy in spritecollide(bullet, enemy_sprites, False):
                if enemy.alive and bullet.alive:
                    enemy.take_damage(bullet.damage)
                    
                    # Handle piercing
                    if bullet.max_pierces > 0:
                        bullet.pierces_done += 1
                        if bullet.pierces_done > bullet.max_pierces:
                            bullet.alive = False
                            bullet.kill()
                    else:
                        bullet.alive = False
                        bullet.kill()
                    break
                        
        # Handle missiles
        if hasattr(self.game.player, 'missiles_group'):
            for missile in list(self.game.player.missiles_group):
                for enemy in spritecollide(missile, enemy_sprites, False):
                    if enemy.alive and missile.alive:
                        enemy.take_damage(missile.damage)
                        if hasattr(enemy, 'rect') and enemy.rect:
                            self.game._create_explosion(enemy.rect.centerx, enemy.rect.centery, 10, 'missile_launch')
                        missile.alive = False
                        missile.kill()
                        break
                        
        # Handle lightning zaps
        if hasattr(self.game.player, 'lightning_zaps_group'):
            for zap in self.game.player.lightning_zaps_group:
                if (not hasattr(zap, 'damage_applied') or not zap.damage_applied) and zap.initial_target_ref:
                    target = zap.initial_target_ref
                    if hasattr(target, 'alive') and target.alive:
                        target.take_damage(zap.damage)
                        if hasattr(target, 'rect') and target.rect:
                            self.game._create_explosion(target.rect.centerx, target.rect.centery, 5, None)
                        zap.damage_applied = True
    
    def draw(self, surface):
        surface.fill(get_setting("colors", "BLACK", (0, 0, 0)))
        
        # Draw maze
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        # Draw collectibles
        item_groups = [
            self.game.collectible_rings_group, self.game.power_ups_group,
            self.game.core_fragments_group, self.game.vault_logs_group,
            self.game.glyph_tablets_group, self.game.architect_echoes_group,
            self.game.spawned_barricades_group
        ]
        
        for group in item_groups:
            for item in group:
                item.draw(surface, self.game.camera)
                # Update orichalc fragments
                from entities.orichalc_fragment import OrichalcFragment
                if isinstance(item, OrichalcFragment):
                    item.update()
        
        # Draw particles
        self.game.explosion_particles_group.update()
        self.game.explosion_particles_group.draw(surface)
        
        self.game.energy_particles_group.update()
        self.game.energy_particles_group.draw(surface)
        
        # Draw HUD
        if hasattr(self.game, 'hud_container'):
            orichalc_count = self.game.drone_system.get_cores()
            self.game.hud_container.draw(surface, orichalc_count)
        
        # Draw entities
        if self.game.player:
            self.game.player.draw(surface)
            
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
            
        # Draw animations
        ring_icon = self.game.asset_manager.get_image("ring_ui_icon")
        self.game.level_manager.draw_ring_animations(surface, ring_icon)
        self.game._draw_fragment_animations()