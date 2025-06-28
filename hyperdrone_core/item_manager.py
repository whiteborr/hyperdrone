# hyperdrone_core/item_manager.py
from random import random, choice, shuffle
from pygame.time import get_ticks
from math import hypot
from logging import getLogger, warning, info

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

        # Get collectible groups
        self.groups = {
            'rings': game_controller_ref.collectible_rings_group,
            'powerups': game_controller_ref.power_ups_group,
            'fragments': game_controller_ref.core_fragments_group,
            'vault_logs': game_controller_ref.vault_logs_group,
            'glyph_tablets': game_controller_ref.glyph_tablets_group,
            'architect_echoes': game_controller_ref.architect_echoes_group,
            'alien_terminals': game_controller_ref.alien_terminals_group,
            'corrupted_logs': game_controller_ref.corrupted_logs_group,
            'quantum_circuitry': game_controller_ref.quantum_circuitry_group
        }

        # Spawn settings
        self.last_powerup_spawn_time = 0
        self.powerup_spawn_interval = get_setting("powerups", "POWERUP_SPAWN_INTERVAL", 15000)
        self.powerup_spawn_chance = get_setting("powerups", "POWERUP_SPAWN_CHANCE", 0.3)
        self.spawned_rings_count = 0
        self.max_rings_per_level = get_setting("collectibles", "MAX_RINGS_PER_LEVEL", 5)

    def update(self, current_time_ms, maze):
        # Update all items
        for group in [self.groups['rings'], self.groups['powerups'], self.groups['corrupted_logs'], 
                     self.groups['quantum_circuitry'], self.groups['fragments']]:
            for item in list(group):
                item.update()

        # Spawn powerups periodically
        if current_time_ms - self.last_powerup_spawn_time > self.powerup_spawn_interval:
            self.last_powerup_spawn_time = current_time_ms
            if random() < self.powerup_spawn_chance:
                self._spawn_random_powerup(maze)

        # Ensure rings are spawned
        if self.spawned_rings_count < self.max_rings_per_level:
            self._spawn_all_rings(maze)

    def _get_valid_positions(self, maze, min_distance, exclude_groups=None):
        """Get valid spawn positions avoiding other items"""
        if not maze:
            return []
            
        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            return []

        exclude_groups = exclude_groups or ['rings', 'powerups', 'fragments']
        valid_positions = []
        
        for pos in walkable_tiles:
            too_close = False
            for group_name in exclude_groups:
                for item in self.groups[group_name]:
                    if hypot(pos[0] - item.rect.centerx, pos[1] - item.rect.centery) < min_distance:
                        too_close = True
                        break
                if too_close:
                    break
            
            if not too_close:
                valid_positions.append(pos)
                
        return valid_positions

    def _spawn_random_powerup(self, maze):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        valid_positions = self._get_valid_positions(maze, tile_size * 4, ['powerups'])
        
        if not valid_positions:
            return False

        # Check chapter for powerup types
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            powerup_types = ["shield", "speed"]
        else:
            powerup_types = ["weapon", "shield", "speed"]

        spawn_pos = choice(valid_positions)
        powerup_type = choice(powerup_types)

        powerup_classes = {
            "weapon": WeaponUpgradeItem,
            "shield": ShieldItem,
            "speed": SpeedBoostItem
        }

        powerup_class = powerup_classes[powerup_type]
        new_powerup = powerup_class(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        self.groups['powerups'].add(new_powerup)
        return True

    def spawn_corrupted_logs(self, maze, log_ids_to_spawn):
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
                break

            spawn_pos = walkable_tiles.pop()
            new_log = CorruptedLogItem(spawn_pos[0], spawn_pos[1], log_id, asset_manager=self.asset_manager)
            self.groups['corrupted_logs'].add(new_log)
            info(f"Spawned Corrupted Log '{log_id}' at {spawn_pos}")

    def spawn_quantum_circuitry(self, x, y):
        circuitry = QuantumCircuitryItem(x, y, asset_manager=self.asset_manager)
        self.groups['quantum_circuitry'].add(circuitry)
        info(f"Spawned Quantum Circuitry at ({x}, {y})")

    def reset_for_level(self):
        self.spawned_rings_count = 0
        self.last_powerup_spawn_time = get_ticks()
        self.clear_all_items()

        if hasattr(self.game_controller, 'maze') and self.game_controller.maze:
            self._spawn_all_rings(self.game_controller.maze)
            self._spawn_core_fragment(self.game_controller.maze)
            
            # Spawn weapon shop on specific levels
            level = self.game_controller.level_manager.level
            if ((level == 2 and not hasattr(self.game_controller, 'weapon_shop_used_level_2')) or 
                (level == 7 and not hasattr(self.game_controller, 'weapon_shop_used_level_7'))):
                self._spawn_weapons_upgrade_shop(self.game_controller.maze)

    def clear_all_items(self):
        for group in self.groups.values():
            group.empty()

    def _spawn_core_fragment(self, maze):
        if not maze:
            warning("Cannot spawn core fragment: maze is None")
            return False

        # Check chapter restrictions
        current_chapter = self.game_controller.story_manager.get_current_chapter()
        if current_chapter and current_chapter.chapter_id == "chapter_1":
            # Only spawn Earth fragment on final level of Chapter 1
            if self.game_controller.level_manager.chapter1_level < self.game_controller.level_manager.chapter1_max_levels:
                return False
            fragment_id = "earth_core_fragment"
        else:
            fragment_id = None

        # Get fragment details
        all_fragments = settings_manager.get_core_fragment_details()
        collected_ids = self.game_controller.drone_system.get_collected_fragments_ids()

        fragment_details = None
        if fragment_id:
            # Specific fragment
            if fragment_id in all_fragments and fragment_id not in collected_ids:
                fragment_details = all_fragments[fragment_id]
        else:
            # Next required fragment
            required_fragments = sorted(
                [details for _, details in all_fragments.items() if details.get('required_for_vault')],
                key=lambda d: d.get('id')
            )
            for frag_details in required_fragments:
                if frag_details['id'] not in collected_ids:
                    fragment_details = frag_details
                    break
        
        if not fragment_details:
            info("No more required core fragments to spawn")
            return False

        # Find spawn position
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        valid_positions = self._get_valid_positions(maze, tile_size * 3)
        
        if not valid_positions:
            warning("Cannot spawn core fragment: no valid positions found")
            return False
            
        spawn_pos = choice(valid_positions)
        new_fragment = CoreFragmentItem(
            spawn_pos[0], spawn_pos[1],
            fragment_id=fragment_details['id'],
            fragment_config_details=fragment_details,
            asset_manager=self.asset_manager
        )
        self.groups['fragments'].add(new_fragment)
        info(f"Spawned core fragment '{fragment_details['name']}' at {spawn_pos}")
        return True

    def _spawn_all_rings(self, maze):
        if not maze:
            warning("Cannot spawn rings: maze is None")
            return

        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            warning("Cannot spawn rings: no walkable tiles found")
            return

        shuffle(walkable_tiles)
        self.groups['rings'].empty()
        self.spawned_rings_count = 0

        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        min_spacing = tile_size * 3
        positions = []

        # Find well-spaced positions
        for pos in walkable_tiles:
            too_close = any(hypot(pos[0] - existing[0], pos[1] - existing[1]) < min_spacing 
                           for existing in positions)
            
            if not too_close:
                positions.append(pos)
                if len(positions) >= self.max_rings_per_level:
                    break

        # Spawn rings
        for pos in positions:
            new_ring = CollectibleRing(pos[0], pos[1])
            self.groups['rings'].add(new_ring)
            self.spawned_rings_count += 1

        # Spawn initial powerup if no powerups exist
        if len(positions) > 0 and len(self.groups['powerups']) == 0:
            self._spawn_random_powerup(maze)

        info(f"Spawned {len(positions)} rings for level {self.game_controller.level_manager.level}")
    
    def _spawn_weapons_upgrade_shop(self, maze):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        valid_positions = self._get_valid_positions(maze, tile_size * 4)
        
        if not valid_positions:
            warning("Cannot spawn weapons upgrade shop: no valid positions found")
            return False
            
        spawn_pos = choice(valid_positions)
        shop_item = WeaponsUpgradeShopItem(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager)
        self.groups['powerups'].add(shop_item)
        info(f"Spawned weapons upgrade shop at {spawn_pos}")
        return True