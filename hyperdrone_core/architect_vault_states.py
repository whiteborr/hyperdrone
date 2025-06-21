# hyperdrone_core/architect_vault_states.pyAdd commentMore actions
import pygame
from .state import State
from settings_manager import get_setting

class ArchitectVaultIntroState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.architect_vault_current_phase = "intro"
        self.game.architect_vault_message = "Entering the Architect's Vault..."
        self.game.architect_vault_message_timer = pygame.time.get_ticks() + 3000  # 3 seconds display
    
    def update(self, delta_time):
        current_time = pygame.time.get_ticks()
        if current_time > self.game.architect_vault_message_timer:
            self.game.state_manager.set_state("ArchitectVaultEntryPuzzleState")
    
    def draw(self, surface):
        bg_color = get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30))
        gold_color = get_setting("colors", "GOLD", (255, 215, 0))
        white_color = get_setting("colors", "WHITE", (255, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        surface.fill(bg_color)
        
        # Draw intro message
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        title_surf = font.render("Architect's Vault", True, gold_color)
        surface.blit(title_surf, title_surf.get_rect(center=(width // 2, 50)))
        
        font = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
        msg_surf = font.render(self.game.architect_vault_message, True, white_color)
        surface.blit(msg_surf, msg_surf.get_rect(center=(width // 2, height // 2)))


class ArchitectVaultEntryPuzzleState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.architect_vault_current_phase = "entry_puzzle"
        if hasattr(self.game.puzzle_controller, 'initialize_vault_entry_puzzle'):
            self.game.puzzle_controller.initialize_vault_entry_puzzle()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.toggle_pause()
                else:
                    self.game.puzzle_controller.handle_input(event, "architect_vault_entry_puzzle")
    
    def update(self, delta_time):
        if hasattr(self.game.puzzle_controller, 'update_vault_entry_puzzle'):
            puzzle_completed = self.game.puzzle_controller.update_vault_entry_puzzle(delta_time)
            if puzzle_completed:
                self.game.state_manager.set_state("ArchitectVaultGauntletState")
    
    def draw(self, surface):
        bg_color = get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30))
        gold_color = get_setting("colors", "GOLD", (255, 215, 0))
        width = get_setting("display", "WIDTH", 1920)
        
        surface.fill(bg_color)
        
        # Draw title
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        title_surf = font.render("Architect's Vault", True, gold_color)
        surface.blit(title_surf, title_surf.get_rect(center=(width // 2, 50)))
        
        # Let puzzle controller draw the puzzle
        if hasattr(self.game.puzzle_controller, 'draw_vault_entry_puzzle'):
            self.game.puzzle_controller.draw_vault_entry_puzzle(surface)


class ArchitectVaultGauntletState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.architect_vault_current_phase = "gauntlet"
        
        # Initialize maze for gauntlet
        self.game.maze = self.game.Maze(is_architect_vault=True)
        
        # Initialize player
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        spawn_x, spawn_y = self.game._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        
        self.game.player = self.game.PlayerDrone(
            spawn_x, spawn_y, drone_id, drone_stats, 
            self.game.asset_manager, sprite_key, 'crash', 
            self.game.drone_system
        )
        
        # Set up combat controller
        self.game.combat_controller.reset_combat_state()
        self.game.combat_controller.set_active_entities(
            player=self.game.player, 
            maze=self.game.maze, 
            power_ups_group=self.game.power_ups_group
        )
        
        # Spawn enemies for gauntlet
        drones_per_wave = get_setting("architect_vault", "ARCHITECT_VAULT_DRONES_PER_WAVE", [3, 4, 5])
        self.game.combat_controller.enemy_manager.spawn_architect_vault_enemies(
            wave=0, 
            num_enemies=drones_per_wave[0]
        )
        
        # Set up wave counter
        self.game.architect_vault_current_wave = 0
        self.game.architect_vault_total_waves = get_setting("architect_vault", "ARCHITECT_VAULT_GAUNTLET_WAVES", 3)
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                    self.game.toggle_pause()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        current_time_ms = pygame.time.get_ticks()
        
        # Update player
        if self.game.player:
            self.game.player.update(
                current_time_ms, 
                self.game.maze, 
                self.game.combat_controller.enemy_manager.get_sprites(), 
                self.game.player_actions, 
                self.game.maze.game_area_x_offset if self.game.maze else 0
            )
        
        # Update combat
        self.game.combat_controller.update(current_time_ms, delta_time)
        
        # Check if all enemies are defeated
        if len(self.game.combat_controller.enemy_manager.get_sprites()) == 0:
            self.game.architect_vault_current_wave += 1
            
            # Check if all waves are completed
            if self.game.architect_vault_current_wave >= self.game.architect_vault_total_waves:
                self.game.state_manager.set_state("ArchitectVaultExtractionState")
            else:
                # Spawn next wave
                drones_per_wave = get_setting("architect_vault", "ARCHITECT_VAULT_DRONES_PER_WAVE", [3, 4, 5])
                self.game.combat_controller.enemy_manager.spawn_architect_vault_enemies(
                    wave=self.game.architect_vault_current_wave,
                    num_enemies=drones_per_wave[self.game.architect_vault_current_wave]
                )
        
        # Handle collectible collisions
        self.game._handle_collectible_collisions()
        
        # Update continuous player movement and actions
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
    
    def draw(self, surface):
        bg_color = get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30))
        white_color = get_setting("colors", "WHITE", (255, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        
        surface.fill(bg_color)
        
        # Draw maze
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        # Draw collectibles and powerups
        for item_group in [
            self.game.collectible_rings_group, 
            self.game.power_ups_group, 
            self.game.core_fragments_group
        ]:
            for item in item_group:
                item.draw(surface, self.game.camera)
        
        # Draw player
        if self.game.player:
            self.game.player.draw(surface)
        
        # Draw enemies
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        
        # Draw wave counter
        font = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
        wave_surf = font.render(f"Wave {self.game.architect_vault_current_wave + 1}/{self.game.architect_vault_total_waves}", 
                              True, white_color)
        surface.blit(wave_surf, wave_surf.get_rect(center=(width // 2, 100)))


class ArchitectVaultExtractionState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.architect_vault_current_phase = "extraction"
        
        # Initialize extraction timer
        self.game.architect_vault_phase_timer_start = pygame.time.get_ticks()
        
        # Create escape zone
        if hasattr(self.game.maze, 'create_escape_zone'):
            escape_pos = self.game.maze.create_escape_zone()
            if escape_pos:
                self.game.escape_zone_group.empty()
                tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                escape_zone_color = get_setting("colors", "ESCAPE_ZONE_COLOR", (0, 255, 120))
                self.game.escape_zone_group.add(self.game.EscapeZone(
                    escape_pos[0], escape_pos[1], 
                    tile_size * 2, tile_size * 2, 
                    escape_zone_color
                ))
        
        # Spawn vault core collectible
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.spawn_vault_core(self.game.maze)
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                    self.game.toggle_pause()
                else:
                    self.game.player_actions.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        current_time_ms = pygame.time.get_ticks()
        
        # Update player
        if self.game.player:
            self.game.player.update(
                current_time_ms, 
                self.game.maze, 
                self.game.combat_controller.enemy_manager.get_sprites(), 
                self.game.player_actions, 
                self.game.maze.game_area_x_offset if self.game.maze else 0
            )
        
        # Update combat
        self.game.combat_controller.update(current_time_ms, delta_time)
        
        # Handle collectible collisions
        self.game._handle_collectible_collisions()
        
        # Check if player has collected vault core and reached escape zone
        has_vault_core = self.game.drone_system.has_collected_fragment("vault_core")
        if has_vault_core and self.game.player and self.game.escape_zone_group:
            escape_zone = self.game.escape_zone_group.sprite
            if escape_zone and escape_zone.rect.colliderect(self.game.player.rect):
                self.game.state_manager.set_state("ArchitectVaultSuccessState")
        
        # Check if time is up
        time_elapsed = current_time_ms - self.game.architect_vault_phase_timer_start
        extraction_timer = get_setting("architect_vault", "ARCHITECT_VAULT_EXTRACTION_TIMER_MS", 90000)
        if time_elapsed >= extraction_timer:
            self.game.architect_vault_failure_reason = "Time ran out"
            self.game.state_manager.set_state("ArchitectVaultFailureState")
        
        # Update continuous player movement and actions
        self.game.player_actions.update_player_movement_and_actions(current_time_ms)
    
    def draw(self, surface):
        bg_color = get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30))
        red_color = get_setting("colors", "RED", (255, 0, 0))
        white_color = get_setting("colors", "WHITE", (255, 255, 255))
        gold_color = get_setting("colors", "GOLD", (255, 215, 0))
        width = get_setting("display", "WIDTH", 1920)
        
        surface.fill(bg_color)
        
        # Draw maze
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        # Draw escape zone
        if self.game.escape_zone_group:
            for zone in self.game.escape_zone_group:
                zone.draw(surface, self.game.camera)
        
        # Draw collectibles and powerups
        for item_group in [
            self.game.collectible_rings_group, 
            self.game.power_ups_group, 
            self.game.core_fragments_group
        ]:
            for item in item_group:
                item.draw(surface, self.game.camera)
        
        # Draw player
        if self.game.player:
            self.game.player.draw(surface)
        
        # Draw enemies
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        
        # Draw timer
        current_time_ms = pygame.time.get_ticks()
        time_elapsed = current_time_ms - self.game.architect_vault_phase_timer_start
        extraction_timer = get_setting("architect_vault", "ARCHITECT_VAULT_EXTRACTION_TIMER_MS", 90000)
        time_remaining = max(0, extraction_timer - time_elapsed)
        seconds_remaining = int(time_remaining / 1000)
        
        font = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
        timer_surf = font.render(f"Extraction Time: {seconds_remaining}s", True, 
                               red_color if seconds_remaining <= 30 else white_color)
        surface.blit(timer_surf, timer_surf.get_rect(center=(width // 2, 100)))
        
        # Draw objective
        has_vault_core = self.game.drone_system.has_collected_fragment("vault_core")
        objective_text = "Find the Vault Core" if not has_vault_core else "Reach the Escape Zone"
        objective_surf = font.render(objective_text, True, gold_color)
        surface.blit(objective_surf, objective_surf.get_rect(center=(width // 2, 150)))


class ArchitectVaultSuccessState(State):
    def enter(self, previous_state=None, **kwargs):
        # Unlock rewards
        blueprint_id = get_setting("architect_vault", "ARCHITECT_REWARD_BLUEPRINT_ID", "DRONE_ARCHITECT_X")
        lore_id = get_setting("architect_vault", "ARCHITECT_REWARD_LORE_ID", "lore_architect_origin")
        self.game.drone_system.unlock_drone_by_id(blueprint_id)
        self.game.drone_system.unlock_lore_entry_by_id(lore_id)
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.game.state_manager.set_state("MainMenuState")
    
    def draw(self, surface):
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        gold_color = get_setting("colors", "GOLD", (255, 215, 0))
        cyan_color = get_setting("colors", "CYAN", (0, 255, 255))
        white_color = get_setting("colors", "WHITE", (255, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        surface.fill(black_color)
        
        # Draw success message
        font = self.game.asset_manager.get_font("large_text", 64) or pygame.font.Font(None, 64)
        title_surf = font.render("Vault Conquered", True, gold_color)
        surface.blit(title_surf, title_surf.get_rect(center=(width // 2, height // 2 - 100)))
        
        # Draw rewards
        font = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
        reward_surf = font.render("Architect's Blueprint Unlocked!", True, cyan_color)
        surface.blit(reward_surf, reward_surf.get_rect(center=(width // 2, height // 2)))
        
        lore_surf = font.render("New Codex Entry Available", True, white_color)
        surface.blit(lore_surf, lore_surf.get_rect(center=(width // 2, height // 2 + 50)))
        
        # Draw continue prompt
        font = self.game.asset_manager.get_font("ui_text", 24) or pygame.font.Font(None, 24)
        prompt_surf = font.render("Press any key to continue", True, white_color)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(width // 2, height // 2 + 150)))


class ArchitectVaultFailureState(State):
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.game.state_manager.set_state("MainMenuState")
    
    def draw(self, surface):
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        red_color = get_setting("colors", "RED", (255, 0, 0))
        white_color = get_setting("colors", "WHITE", (255, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        surface.fill(black_color)
        
        # Draw failure message
        font = self.game.asset_manager.get_font("large_text", 64) or pygame.font.Font(None, 64)
        title_surf = font.render("Mission Failed", True, red_color)
        surface.blit(title_surf, title_surf.get_rect(center=(width // 2, height // 2 - 100)))
        
        # Draw reason if available
        if hasattr(self.game, 'architect_vault_failure_reason') and self.game.architect_vault_failure_reason:
            font = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
            reason_surf = font.render(self.game.architect_vault_failure_reason, True, white_color)
            surface.blit(reason_surf, reason_surf.get_rect(center=(width // 2, height // 2)))
        
        # Draw continue prompt
        font = self.game.asset_manager.get_font("ui_text", 24) or pygame.font.Font(None, 24)
        prompt_surf = font.render("Press any key to continue", True, white_color)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(width // 2, height // 2 + 150)))