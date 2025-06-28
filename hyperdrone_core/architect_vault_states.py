# hyperdrone_core/architect_vault_states.py
from pygame.time import get_ticks
from pygame.font import Font
from pygame import KEYDOWN, KEYUP, K_ESCAPE, K_p
from .state import State
from settings_manager import get_setting

class BaseArchitectVaultState(State):
    def _draw_title(self, surface, title="Architect's Vault"):
        font = self.game.asset_manager.get_font("large_text", 48) or Font(None, 48)
        gold = get_setting("colors", "GOLD", (255, 215, 0))
        width = get_setting("display", "WIDTH", 1920)
        
        title_surf = font.render(title, True, gold)
        surface.blit(title_surf, title_surf.get_rect(center=(width // 2, 50)))
    
    def _handle_pause(self, events):
        for event in events:
            if event.type == KEYDOWN and event.key in (K_p, K_ESCAPE):
                self.game.toggle_pause()
                return True
        return False

class ArchitectVaultIntroState(BaseArchitectVaultState):
    def enter(self, previous_state=None, **kwargs):
        self.game.architect_vault_current_phase = "intro"
        self.message = "Entering the Architect's Vault..."
        self.timer = get_ticks() + 3000
    
    def update(self, delta_time):
        if get_ticks() > self.timer:
            self.game.state_manager.set_state("ArchitectVaultEntryPuzzleState")
    
    def draw(self, surface):
        bg = get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30))
        white = get_setting("colors", "WHITE", (255, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        surface.fill(bg)
        self._draw_title(surface)
        
        font = self.game.asset_manager.get_font("medium_text", 36) or Font(None, 36)
        msg_surf = font.render(self.message, True, white)
        surface.blit(msg_surf, msg_surf.get_rect(center=(width // 2, height // 2)))

class ArchitectVaultEntryPuzzleState(BaseArchitectVaultState):
    def enter(self, previous_state=None, **kwargs):
        self.game.architect_vault_current_phase = "entry_puzzle"
        if hasattr(self.game.puzzle_controller, 'initialize_vault_entry_puzzle'):
            self.game.puzzle_controller.initialize_vault_entry_puzzle()
    
    def handle_events(self, events):
        if self._handle_pause(events):
            return
        
        for event in events:
            if event.type == KEYDOWN and event.key != K_ESCAPE:
                self.game.puzzle_controller.handle_input(event, "architect_vault_entry_puzzle")
    
    def update(self, delta_time):
        if hasattr(self.game.puzzle_controller, 'update_vault_entry_puzzle'):
            if self.game.puzzle_controller.update_vault_entry_puzzle(delta_time):
                self.game.state_manager.set_state("ArchitectVaultGauntletState")
    
    def draw(self, surface):
        bg = get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30))
        surface.fill(bg)
        self._draw_title(surface)
        
        if hasattr(self.game.puzzle_controller, 'draw_vault_entry_puzzle'):
            self.game.puzzle_controller.draw_vault_entry_puzzle(surface)

class ArchitectVaultGauntletState(BaseArchitectVaultState):
    def enter(self, previous_state=None, **kwargs):
        self.game.architect_vault_current_phase = "gauntlet"
        
        # Initialize maze and player
        self.game.maze = self.game.Maze(is_architect_vault=True)
        
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        spawn_x, spawn_y = self.game._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        
        self.game.player = self.game.PlayerDrone(
            spawn_x, spawn_y, drone_id, drone_stats,
            self.game.asset_manager, f"drone_{drone_id}_ingame_sprite", 'crash',
            self.game.drone_system
        )
        
        # Setup combat
        self.game.combat_controller.reset_combat_state()
        self.game.combat_controller.set_active_entities(
            player=self.game.player, maze=self.game.maze, power_ups_group=self.game.power_ups_group
        )
        
        # Setup waves
        drones_per_wave = get_setting("architect_vault", "ARCHITECT_VAULT_DRONES_PER_WAVE", [3, 4, 5])
        self.game.combat_controller.enemy_manager.spawn_architect_vault_enemies(wave=0, num_enemies=drones_per_wave[0])
        
        self.game.architect_vault_current_wave = 0
        self.game.architect_vault_total_waves = get_setting("architect_vault", "ARCHITECT_VAULT_GAUNTLET_WAVES", 3)
    
    def handle_events(self, events):
        if self._handle_pause(events):
            return
        
        for event in events:
            if event.type == KEYDOWN and event.key not in (K_p, K_ESCAPE):
                self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        current_time = get_ticks()
        
        # Update player
        if self.game.player:
            self.game.player.update(
                current_time, self.game.maze,
                self.game.combat_controller.enemy_manager.get_sprites(),
                self.game.player_actions,
                self.game.maze.game_area_x_offset if self.game.maze else 0
            )
        
        # Update combat
        self.game.combat_controller.update(current_time, delta_time)
        
        # Check wave progression
        if len(self.game.combat_controller.enemy_manager.get_sprites()) == 0:
            self.game.architect_vault_current_wave += 1
            
            if self.game.architect_vault_current_wave >= self.game.architect_vault_total_waves:
                self.game.state_manager.set_state("ArchitectVaultExtractionState")
            else:
                drones_per_wave = get_setting("architect_vault", "ARCHITECT_VAULT_DRONES_PER_WAVE", [3, 4, 5])
                self.game.combat_controller.enemy_manager.spawn_architect_vault_enemies(
                    wave=self.game.architect_vault_current_wave,
                    num_enemies=drones_per_wave[self.game.architect_vault_current_wave]
                )
        
        # Handle game updates
        self.game._handle_collectible_collisions()
        self.game.player_actions.update_player_movement_and_actions(current_time)
    
    def draw(self, surface):
        bg = get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30))
        white = get_setting("colors", "WHITE", (255, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        
        surface.fill(bg)
        
        # Draw game elements
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        # Draw collectibles
        for group in [self.game.collectible_rings_group, self.game.power_ups_group, self.game.core_fragments_group]:
            for item in group:
                item.draw(surface, self.game.camera)
        
        if self.game.player:
            self.game.player.draw(surface)
        
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        
        # Draw wave counter
        font = self.game.asset_manager.get_font("medium_text", 36) or Font(None, 36)
        wave_text = f"Wave {self.game.architect_vault_current_wave + 1}/{self.game.architect_vault_total_waves}"
        wave_surf = font.render(wave_text, True, white)
        surface.blit(wave_surf, wave_surf.get_rect(center=(width // 2, 100)))

class ArchitectVaultExtractionState(BaseArchitectVaultState):
    def enter(self, previous_state=None, **kwargs):
        self.game.architect_vault_current_phase = "extraction"
        self.timer_start = get_ticks()
        
        # Create escape zone
        if hasattr(self.game.maze, 'create_escape_zone'):
            escape_pos = self.game.maze.create_escape_zone()
            if escape_pos:
                self.game.escape_zone_group.empty()
                tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                color = get_setting("colors", "ESCAPE_ZONE_COLOR", (0, 255, 120))
                self.game.escape_zone_group.add(self.game.EscapeZone(
                    escape_pos[0], escape_pos[1], tile_size * 2, tile_size * 2, color
                ))
        
        # Spawn vault core
        if hasattr(self.game, 'item_manager'):
            self.game.item_manager.spawn_vault_core(self.game.maze)
    
    def handle_events(self, events):
        if self._handle_pause(events):
            return
        
        for event in events:
            if event.type == KEYDOWN and event.key not in (K_p, K_ESCAPE):
                self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
                self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        current_time = get_ticks()
        
        # Update player and combat
        if self.game.player:
            self.game.player.update(
                current_time, self.game.maze,
                self.game.combat_controller.enemy_manager.get_sprites(),
                self.game.player_actions,
                self.game.maze.game_area_x_offset if self.game.maze else 0
            )
        
        self.game.combat_controller.update(current_time, delta_time)
        self.game._handle_collectible_collisions()
        
        # Check win condition
        has_core = self.game.drone_system.has_collected_fragment("vault_core")
        if has_core and self.game.player and self.game.escape_zone_group:
            escape_zone = self.game.escape_zone_group.sprite
            if escape_zone and escape_zone.rect.colliderect(self.game.player.rect):
                self.game.state_manager.set_state("ArchitectVaultSuccessState")
        
        # Check time limit
        time_limit = get_setting("architect_vault", "ARCHITECT_VAULT_EXTRACTION_TIMER_MS", 90000)
        if current_time - self.timer_start >= time_limit:
            self.game.architect_vault_failure_reason = "Time ran out"
            self.game.state_manager.set_state("ArchitectVaultFailureState")
        
        self.game.player_actions.update_player_movement_and_actions(current_time)
    
    def draw(self, surface):
        bg = get_setting("colors", "ARCHITECT_VAULT_BG_COLOR", (20, 0, 30))
        red = get_setting("colors", "RED", (255, 0, 0))
        white = get_setting("colors", "WHITE", (255, 255, 255))
        gold = get_setting("colors", "GOLD", (255, 215, 0))
        width = get_setting("display", "WIDTH", 1920)
        
        surface.fill(bg)
        
        # Draw game elements
        if self.game.maze:
            self.game.maze.draw(surface, self.game.camera)
        
        for zone in self.game.escape_zone_group:
            zone.draw(surface, self.game.camera)
        
        for group in [self.game.collectible_rings_group, self.game.power_ups_group, self.game.core_fragments_group]:
            for item in group:
                item.draw(surface, self.game.camera)
        
        if self.game.player:
            self.game.player.draw(surface)
        
        if self.game.combat_controller:
            self.game.combat_controller.enemy_manager.draw_all(surface, self.game.camera)
        
        # Draw timer and objective
        current_time = get_ticks()
        time_limit = get_setting("architect_vault", "ARCHITECT_VAULT_EXTRACTION_TIMER_MS", 90000)
        time_remaining = max(0, time_limit - (current_time - self.timer_start))
        seconds = int(time_remaining / 1000)
        
        font = self.game.asset_manager.get_font("medium_text", 36) or Font(None, 36)
        timer_color = red if seconds <= 30 else white
        timer_surf = font.render(f"Extraction Time: {seconds}s", True, timer_color)
        surface.blit(timer_surf, timer_surf.get_rect(center=(width // 2, 100)))
        
        has_core = self.game.drone_system.has_collected_fragment("vault_core")
        objective = "Find the Vault Core" if not has_core else "Reach the Escape Zone"
        obj_surf = font.render(objective, True, gold)
        surface.blit(obj_surf, obj_surf.get_rect(center=(width // 2, 150)))

class ArchitectVaultSuccessState(BaseArchitectVaultState):
    def enter(self, previous_state=None, **kwargs):
        blueprint_id = get_setting("architect_vault", "ARCHITECT_REWARD_BLUEPRINT_ID", "DRONE_ARCHITECT_X")
        lore_id = get_setting("architect_vault", "ARCHITECT_REWARD_LORE_ID", "lore_architect_origin")
        self.game.drone_system.unlock_drone_by_id(blueprint_id)
        self.game.drone_system.unlock_lore_entry_by_id(lore_id)
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                self.game.state_manager.set_state("MainMenuState")
    
    def draw(self, surface):
        black = get_setting("colors", "BLACK", (0, 0, 0))
        gold = get_setting("colors", "GOLD", (255, 215, 0))
        cyan = get_setting("colors", "CYAN", (0, 255, 255))
        white = get_setting("colors", "WHITE", (255, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        surface.fill(black)
        
        # Success message
        font = self.game.asset_manager.get_font("large_text", 64) or Font(None, 64)
        title = font.render("Vault Conquered", True, gold)
        surface.blit(title, title.get_rect(center=(width // 2, height // 2 - 100)))
        
        # Rewards
        font = self.game.asset_manager.get_font("medium_text", 36) or Font(None, 36)
        reward = font.render("Architect's Blueprint Unlocked!", True, cyan)
        surface.blit(reward, reward.get_rect(center=(width // 2, height // 2)))
        
        lore = font.render("New Codex Entry Available", True, white)
        surface.blit(lore, lore.get_rect(center=(width // 2, height // 2 + 50)))
        
        # Continue prompt
        font = self.game.asset_manager.get_font("ui_text", 24) or Font(None, 24)
        prompt = font.render("Press any key to continue", True, white)
        surface.blit(prompt, prompt.get_rect(center=(width // 2, height // 2 + 150)))

class ArchitectVaultFailureState(BaseArchitectVaultState):
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                self.game.state_manager.set_state("MainMenuState")
    
    def draw(self, surface):
        black = get_setting("colors", "BLACK", (0, 0, 0))
        red = get_setting("colors", "RED", (255, 0, 0))
        white = get_setting("colors", "WHITE", (255, 255, 255))
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        surface.fill(black)
        
        # Failure message
        font = self.game.asset_manager.get_font("large_text", 64) or Font(None, 64)
        title = font.render("Mission Failed", True, red)
        surface.blit(title, title.get_rect(center=(width // 2, height // 2 - 100)))
        
        # Failure reason
        if hasattr(self.game, 'architect_vault_failure_reason') and self.game.architect_vault_failure_reason:
            font = self.game.asset_manager.get_font("medium_text", 36) or Font(None, 36)
            reason = font.render(self.game.architect_vault_failure_reason, True, white)
            surface.blit(reason, reason.get_rect(center=(width // 2, height // 2)))
        
        # Continue prompt
        font = self.game.asset_manager.get_font("ui_text", 24) or Font(None, 24)
        prompt = font.render("Press any key to continue", True, white)
        surface.blit(prompt, prompt.get_rect(center=(width // 2, height // 2 + 150)))