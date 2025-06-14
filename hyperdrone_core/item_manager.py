# hyperdrone_core/item_manager.py
import random
import pygame
import math
import logging

from entities.collectibles import (
    Ring as CollectibleRing, WeaponUpgradeItem, ShieldItem, SpeedBoostItem,
    CoreFragmentItem, VaultLogItem, GlyphTabletItem, AncientAlienTerminal,
    ArchitectEchoItem
)
from settings_manager import get_setting

logger = logging.getLogger(__name__)

class ItemManager:
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        
        # Get references to the collectible groups from the game controller
        self.collectible_rings_group = self.game_controller.collectible_rings_group
        self.power_ups_group = self.game_controller.power_ups_group
        self.core_fragments_group = self.game_controller.core_fragments_group
        self.vault_logs_group = self.game_controller.vault_logs_group
        self.glyph_tablets_group = self.game_controller.glyph_tablets_group
        self.architect_echoes_group = self.game_controller.architect_echoes_group
        self.alien_terminals_group = self.game_controller.alien_terminals_group
        
        # Item spawn settings
        self.last_powerup_spawn_time = 0
        self.powerup_spawn_interval = get_setting("powerups", "POWERUP_SPAWN_INTERVAL", 15000)  # 15 seconds
        self.powerup_spawn_chance = get_setting("powerups", "POWERUP_SPAWN_CHANCE", 0.3)  # 30% chance each interval
        
        # Track spawned items
        self.spawned_rings_count = 0
        self.max_rings_per_level = get_setting("collectibles", "MAX_RINGS_PER_LEVEL", 5)
        
    def update(self, current_time_ms, maze):
        """Update item manager state and spawn items as needed"""
        # Update all collectible items
        for item in list(self.collectible_rings_group):
            item.update()
        for item in list(self.power_ups_group):
            item.update()
            
        # Check if it's time to try spawning a powerup
        if current_time_ms - self.last_powerup_spawn_time > self.powerup_spawn_interval:
            self.last_powerup_spawn_time = current_time_ms
            
            # Try to spawn a powerup with the configured chance
            if random.random() < self.powerup_spawn_chance:
                self._spawn_random_powerup(maze)
                
        # Ensure all rings are spawned at the beginning
        if self.spawned_rings_count < self.max_rings_per_level:
            self._spawn_all_rings(maze)
                
    def _spawn_ring(self, maze):
        """Spawn a collectible ring at a random walkable position"""
        if not maze:
            return False
            
        # Get a random walkable position
        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            return False
            
        # Choose a position that's not too close to existing items
        valid_positions = []
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        for pos in walkable_tiles:
            # Check distance from existing collectibles
            too_close = False
            for ring in self.collectible_rings_group:
                if math.hypot(pos[0] - ring.rect.centerx, pos[1] - ring.rect.centery) < tile_size * 3:
                    too_close = True
                    break
                    
            if not too_close:
                valid_positions.append(pos)
                
        if not valid_positions:
            return False
            
        # Choose a random valid position
        spawn_pos = random.choice(valid_positions)
        
        # Create and add the ring
        new_ring = CollectibleRing(spawn_pos[0], spawn_pos[1])
        self.collectible_rings_group.add(new_ring)
        self.spawned_rings_count += 1
        logger.debug(f"Spawned ring at {spawn_pos}, total: {self.spawned_rings_count}")
        return True
        
    def _spawn_random_powerup(self, maze):
        """Spawn a random powerup at a walkable position"""
        if not maze:
            return False
            
        # Get a random walkable position
        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            return False
            
        # Choose a position that's not too close to existing items
        valid_positions = []
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        for pos in walkable_tiles:
            # Check distance from existing powerups
            too_close = False
            for powerup in self.power_ups_group:
                if math.hypot(pos[0] - powerup.rect.centerx, pos[1] - powerup.rect.centery) < tile_size * 4:
                    too_close = True
                    break
                    
            if not too_close:
                valid_positions.append(pos)
                
        if not valid_positions:
            return False
            
        # Choose a random valid position
        spawn_pos = random.choice(valid_positions)
        
        # Determine which powerup to spawn
        powerup_type = random.choice(["weapon", "shield", "speed"])
        
        # Create and add the powerup
        if powerup_type == "weapon":
            new_powerup = WeaponUpgradeItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        elif powerup_type == "shield":
            new_powerup = ShieldItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        else:  # speed
            new_powerup = SpeedBoostItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
            
        self.power_ups_group.add(new_powerup)
        logger.debug(f"Spawned {powerup_type} powerup at {spawn_pos}")
        return True
        
    def reset_for_level(self):
        """Reset item manager state for a new level"""
        self.spawned_rings_count = 0
        self.last_powerup_spawn_time = pygame.time.get_ticks()
        
        # Clear all collectible groups
        self.collectible_rings_group.empty()
        self.power_ups_group.empty()
        
        # Spawn all rings immediately for the new level
        if hasattr(self.game_controller, 'maze') and self.game_controller.maze:
            self._spawn_all_rings(self.game_controller.maze)
            
        # Spawn a core fragment for this level
        self._spawn_core_fragment(self.game_controller.maze)
        
    def clear_all_items(self):
        """Clear all collectible items"""
        self.collectible_rings_group.empty()
        self.power_ups_group.empty()
        self.core_fragments_group.empty()
        self.vault_logs_group.empty()
        self.glyph_tablets_group.empty()
        self.architect_echoes_group.empty()
        self.alien_terminals_group.empty()

    def _spawn_core_fragment(self, maze):
        """Spawn a core fragment at a random walkable position"""
        if not maze:
            logger.warning("Cannot spawn core fragment: maze is None")
            return False
            
        # Get a random walkable position
        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            logger.warning("Cannot spawn core fragment: no walkable tiles found")
            return False
            
        # Choose a position that's not too close to existing items
        valid_positions = []
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        for pos in walkable_tiles:
            # Check distance from existing collectibles
            too_close = False
            for ring in self.collectible_rings_group:
                if math.hypot(pos[0] - ring.rect.centerx, pos[1] - ring.rect.centery) < tile_size * 3:
                    too_close = True
                    break
                    
            if not too_close:
                valid_positions.append(pos)
                
        if not valid_positions:
            logger.warning("Cannot spawn core fragment: no valid positions found")
            return False
            
        # Choose a random valid position
        spawn_pos = random.choice(valid_positions)
        
        # Create fragment config details
        fragment_id = f"fragment_level_{self.game_controller.level_manager.level}"
        fragment_config = {
            "name": f"Level {self.game_controller.level_manager.level} Fragment",
            "display_color": (128, 0, 255),  # Purple color
            "icon_filename": "images/collectibles/core_fragment_alpha.png"  # Use existing fragment image
        }
        
        # Create and add the core fragment
        new_fragment = CoreFragmentItem(
            spawn_pos[0], 
            spawn_pos[1], 
            fragment_id, 
            fragment_config, 
            asset_manager=self.asset_manager
        )
        self.core_fragments_group.add(new_fragment)
        logger.info(f"Spawned core fragment at {spawn_pos}")
        return True
        
    def _spawn_all_rings(self, maze):
        """Spawn all rings at once at the beginning of the level"""
        if not maze:
            logger.warning("Cannot spawn rings: maze is None")
            return
            
        # Get all walkable positions
        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            logger.warning("Cannot spawn rings: no walkable tiles found")
            return
            
        # Shuffle the walkable tiles to get random positions
        random.shuffle(walkable_tiles)
        
        # Calculate how many rings we still need to spawn
        rings_to_spawn = self.max_rings_per_level - self.spawned_rings_count
        logger.info(f"Attempting to spawn {rings_to_spawn} rings for level {self.game_controller.level_manager.level}")
        
        # Clear existing rings first to avoid issues
        self.collectible_rings_group.empty()
        self.spawned_rings_count = 0
        
        # Try to spawn all rings
        spawned = 0
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        min_spacing = tile_size * 3  # Minimum spacing between rings
        
        # Use a different approach to ensure we get enough rings
        positions = []
        for pos in walkable_tiles:
            # Check if this position is too close to already selected positions
            too_close = False
            for existing_pos in positions:
                if math.hypot(pos[0] - existing_pos[0], pos[1] - existing_pos[1]) < min_spacing:
                    too_close = True
                    break
                    
            if not too_close:
                positions.append(pos)
                if len(positions) >= self.max_rings_per_level:
                    break
        
        # Create rings at the selected positions
        for pos in positions:
            new_ring = CollectibleRing(pos[0], pos[1])
            self.collectible_rings_group.add(new_ring)
            self.spawned_rings_count += 1
            spawned += 1
            
        # Also spawn an initial powerup
        if spawned > 0 and len(self.power_ups_group) == 0:
            self._spawn_random_powerup(maze)
                
        logger.info(f"Successfully spawned {spawned} rings for level {self.game_controller.level_manager.level}")