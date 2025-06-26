# hyperdrone_core/item_manager.py
from random import random, choice, shuffle
from pygame.time import get_ticks
from math import hypot
from logging import getLogger, debug, warning, error, info

from entities.collectibles import (
    Ring as CollectibleRing, WeaponUpgradeItem, ShieldItem, SpeedBoostItem,
    CoreFragmentItem, GlyphTabletItem, AncientAlienTerminal,
    ArchitectEchoItem, CorruptedLogItem, QuantumCircuitryItem, WeaponsUpgradeShopItem
)
from settings_manager import get_setting, settings_manager

logger = getLogger(__name__)

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
        self.corrupted_logs_group = self.game_controller.corrupted_logs_group
        self.quantum_circuitry_group = self.game_controller.quantum_circuitry_group

        # Item spawn settings
        self.last_powerup_spawn_time = 0
        self.powerup_spawn_interval = get_setting("powerups", "POWERUP_SPAWN_INTERVAL", 15000)
        self.powerup_spawn_chance = get_setting("powerups", "POWERUP_SPAWN_CHANCE", 0.3)

        # Track spawned items
        self.spawned_rings_count = 0
        self.max_rings_per_level = get_setting("collectibles", "MAX_RINGS_PER_LEVEL", 5)

    def update(self, current_time_ms, maze):
        """Update item manager state and spawn items as needed"""
        # Update all collectible items
        for group in [self.collectible_rings_group, self.power_ups_group, self.corrupted_logs_group, self.quantum_circuitry_group, self.core_fragments_group]:
            for item in list(group):
                item.update()

        # Check if it's time to try spawning a powerup
        if current_time_ms - self.last_powerup_spawn_time > self.powerup_spawn_interval:
            self.last_powerup_spawn_time = current_time_ms

            if random() < self.powerup_spawn_chance:
                self._spawn_random_powerup(maze)

        # Ensure all rings are spawned at the beginning
        if self.spawned_rings_count < self.max_rings_per_level:
            self._spawn_all_rings(maze)

    def _spawn_ring(self, maze):
        """Spawn a collectible ring at a random walkable position"""
        if not maze:
            return False

        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            return False

        valid_positions = []
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        for pos in walkable_tiles:
            too_close = False
            for ring in self.collectible_rings_group:
                if hypot(pos[0] - ring.rect.centerx, pos[1] - ring.rect.centery) < tile_size * 3:
                    too_close = True
                    break

            if not too_close:
                valid_positions.append(pos)

        if not valid_positions:
            return False

        spawn_pos = choice(valid_positions)

        new_ring = CollectibleRing(spawn_pos[0], spawn_pos[1])
        self.collectible_rings_group.add(new_ring)
        self.spawned_rings_count += 1
        debug(f"Spawned ring at {spawn_pos}, total: {self.spawned_rings_count}")
        return True

    def _spawn_random_powerup(self, maze):
        """Spawn a random powerup at a walkable position"""
        if not maze: return False
        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles: return False

        # Check if we're in Chapter 1 - only spawn shield and speed powerups
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            powerup_types = ["shield", "speed"]
        else:
            powerup_types = ["weapon", "shield", "speed"]

        valid_positions = []
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        for pos in walkable_tiles:
            too_close = False
            for powerup in self.power_ups_group:
                if hypot(pos[0] - powerup.rect.centerx, pos[1] - powerup.rect.centery) < tile_size * 4:
                    too_close = True
                    break
            if not too_close: valid_positions.append(pos)

        if not valid_positions: return False

        spawn_pos = choice(valid_positions)
        powerup_type = choice(powerup_types)

        if powerup_type == "weapon": new_powerup = WeaponUpgradeItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        elif powerup_type == "shield": new_powerup = ShieldItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        else: new_powerup = SpeedBoostItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)

        self.power_ups_group.add(new_powerup)
        debug(f"Spawned {powerup_type} powerup at {spawn_pos}")
        return True

    def spawn_corrupted_logs(self, maze, log_ids_to_spawn):
        """Spawns specified corrupted logs in the maze."""
        if not maze:
            warning("Cannot spawn corrupted logs: maze is None")
            return

        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            warning("Cannot spawn corrupted logs: no walkable tiles found")
            return

        shuffle(walkable_tiles)

        for log_id in log_ids_to_spawn:
            if not walkable_tiles:
                error(f"Ran out of walkable tiles to spawn log: {log_id}")
                break

            spawn_pos = walkable_tiles.pop()
            new_log = CorruptedLogItem(spawn_pos[0], spawn_pos[1], log_id, asset_manager=self.asset_manager)
            self.corrupted_logs_group.add(new_log)
            info(f"Spawned Corrupted Log '{log_id}' at {spawn_pos}")

    def spawn_quantum_circuitry(self, x, y):
        """Spawns the Quantum Circuitry at a specific location."""
        from entities.collectibles import QuantumCircuitryItem
        circuitry = QuantumCircuitryItem(x, y, asset_manager=self.asset_manager)
        self.quantum_circuitry_group.add(circuitry)
        info(f"Spawned Quantum Circuitry at ({x}, {y})")

    def reset_for_level(self):
        """Reset item manager state for a new level"""
        self.spawned_rings_count = 0
        self.last_powerup_spawn_time = get_ticks()

        # Clear all collectible groups
        self.clear_all_items()

        # Spawn all rings immediately for the new level
        if hasattr(self.game_controller, 'maze') and self.game_controller.maze:
            self._spawn_all_rings(self.game_controller.maze)

        # Spawn a core fragment for this level
        self._spawn_core_fragment(self.game_controller.maze)
        
        # Spawn weapons upgrade shop on level 2 and 7 (only if not used before)
        if (self.game_controller.level_manager.level == 2 and not hasattr(self.game_controller, 'weapon_shop_used_level_2')) or \
           (self.game_controller.level_manager.level == 7 and not hasattr(self.game_controller, 'weapon_shop_used_level_7')):
            self._spawn_weapons_upgrade_shop(self.game_controller.maze)

    def clear_all_items(self):
        """Clear all collectible items"""
        self.collectible_rings_group.empty()
        self.power_ups_group.empty()
        self.core_fragments_group.empty()
        self.vault_logs_group.empty()
        self.glyph_tablets_group.empty()
        self.architect_echoes_group.empty()
        self.alien_terminals_group.empty()
        self.corrupted_logs_group.empty()
        self.quantum_circuitry_group.empty()

    def _spawn_core_fragment(self, maze):
        """Spawn the next uncollected, required core fragment."""
        if not maze:
            warning("Cannot spawn core fragment: maze is None")
            return False

        # Check if we're in Chapter 1 and not on the 4th level yet
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            if self.game_controller.level_manager.chapter1_level < self.game_controller.level_manager.chapter1_max_levels:
                info(f"Skipping core fragment spawn - Chapter 1 Level {self.game_controller.level_manager.chapter1_level} (fragment only appears on level 4)")
                return False

        # 1. Get all fragment configs and the IDs of already collected fragments
        all_fragments = settings_manager.get_core_fragment_details()
        collected_ids = self.game_controller.drone_system.get_collected_fragments_ids()

        # 2. Find the next required fragment that hasn't been collected yet
        # Sort them to ensure a consistent spawn order (alpha, then beta, etc.)
        required_fragments = sorted(
            [details for _, details in all_fragments.items() if details.get('required_for_vault')],
            key=lambda d: d.get('id')
        )

        fragment_to_spawn_details = None
        for frag_details in required_fragments:
            if frag_details['id'] not in collected_ids:
                # We found the next one to spawn
                fragment_to_spawn_details = frag_details
                break
        
        # If all required fragments are collected or none are defined, do nothing
        if not fragment_to_spawn_details:
            info("No more required core fragments to spawn for this level.")
            return False

        # 3. Find a safe, non-overlapping position to spawn the item
        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            warning("Cannot spawn core fragment: no walkable tiles found")
            return False
            
        valid_positions = []
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        for pos in walkable_tiles:
            too_close = False
            # Check against other important items to avoid overlap
            for item_group in [self.collectible_rings_group, self.power_ups_group, self.core_fragments_group]:
                for item in item_group:
                    if hypot(pos[0] - item.rect.centerx, pos[1] - item.rect.centery) < tile_size * 3:
                        too_close = True
                        break
                if too_close:
                    break
            if not too_close:
                valid_positions.append(pos)
                
        if not valid_positions:
            warning("Cannot spawn core fragment: no valid positions found")
            return False
            
        spawn_pos = choice(valid_positions)

        # 4. Spawn the CoreFragmentItem using the correct ID and config details
        new_fragment = CoreFragmentItem(
            spawn_pos[0],
            spawn_pos[1],
            fragment_id=fragment_to_spawn_details['id'],
            fragment_config_details=fragment_to_spawn_details,
            asset_manager=self.asset_manager
        )
        self.core_fragments_group.add(new_fragment)
        info(f"Spawned core fragment '{fragment_to_spawn_details['name']}' at {spawn_pos}")
        return True

    def _spawn_all_rings(self, maze):
        """Spawn all rings at once at the beginning of the level"""
        if not maze:
            warning("Cannot spawn rings: maze is None")
            return

        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            warning("Cannot spawn rings: no walkable tiles found")
            return

        shuffle(walkable_tiles)

        rings_to_spawn = self.max_rings_per_level - self.spawned_rings_count
        info(f"Attempting to spawn {rings_to_spawn} rings for level {self.game_controller.level_manager.level}")

        self.collectible_rings_group.empty()
        self.spawned_rings_count = 0

        spawned = 0
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        min_spacing = tile_size * 3

        positions = []
        for pos in walkable_tiles:
            too_close = False
            for existing_pos in positions:
                if hypot(pos[0] - existing_pos[0], pos[1] - existing_pos[1]) < min_spacing:
                    too_close = True
                    break

            if not too_close:
                positions.append(pos)
                if len(positions) >= self.max_rings_per_level:
                    break

        for pos in positions:
            new_ring = CollectibleRing(pos[0], pos[1])
            self.collectible_rings_group.add(new_ring)
            self.spawned_rings_count += 1
            spawned += 1

        if spawned > 0 and len(self.power_ups_group) == 0:
            self._spawn_random_powerup(maze)

        info(f"Successfully spawned {spawned} rings for level {self.game_controller.level_manager.level}")
    
    def _spawn_weapons_upgrade_shop(self, maze):
        """Spawn weapons upgrade shop at a walkable position"""
        if not maze:
            warning("Cannot spawn weapons upgrade shop: maze is None")
            return False
            
        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            warning("Cannot spawn weapons upgrade shop: no walkable tiles found")
            return False
            
        valid_positions = []
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        for pos in walkable_tiles:
            too_close = False
            # Check against other items to avoid overlap
            for item_group in [self.collectible_rings_group, self.power_ups_group, self.core_fragments_group]:
                for item in item_group:
                    if hypot(pos[0] - item.rect.centerx, pos[1] - item.rect.centery) < tile_size * 4:
                        too_close = True
                        break
                if too_close:
                    break
            if not too_close:
                valid_positions.append(pos)
                
        if not valid_positions:
            warning("Cannot spawn weapons upgrade shop: no valid positions found")
            return False
            
        spawn_pos = choice(valid_positions)
        shop_item = WeaponsUpgradeShopItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        self.power_ups_group.add(shop_item)
        info(f"Spawned weapons upgrade shop at {spawn_pos}")
        return True
