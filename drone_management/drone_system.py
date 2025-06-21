# drone_management/drone_system.py
from json import load, dump
from os.path import exists, dirname
from os import makedirs
import logging
from .drone_configs import DRONE_DATA
from settings_manager import settings_manager

logger = logging.getLogger(__name__)

class DroneSystem:
    """
    Manages drone selection, unlocks, player progression (cores), and lore entries.
    """
    SAVE_FILE = "data/drone_unlocks.json"
    LORE_FILE = "data/lore_entries.json"

    def __init__(self):
        self.drones = DRONE_DATA
        self.unlocked_drones = {"DRONE"}  # Start with the base drone unlocked
        self.selected_drone_id = "DRONE"
        self.player_cores = 0
        
        # Lore and story progression
        self.all_lore_entries = self._load_all_lore_entries()
        self.unlocked_lore_ids = set()
        
        # Collectibles state
        self.collected_core_fragments = set()
        self.collected_glyph_tablets = set()
        self.solved_puzzle_terminals = set()
        
        # Track defeated bosses for unlocks
        self.defeated_bosses = set()

        # NEW: Track unlocked active abilities
        self.unlocked_abilities = set()

        # Vault status
        self.architect_vault_completed = False

        self._load_unlocks()
        
        # Unlock some basic lore entries by default for testing
        self._unlock_default_lore_entries()
        
        logger.info(f"DroneSystem initialized. Unlocked: {self.unlocked_drones}. Selected: {self.selected_drone_id}")


    def _load_all_lore_entries(self):
        """Loads all possible lore entries from the JSON file and converts the list to a dictionary."""
        from constants import KEY_LORE_ENTRIES, KEY_LORE_ID
        
        if not exists(self.LORE_FILE):
            logger.error(f"Lore file not found at '{self.LORE_FILE}'. No lore will be available.")
            return {}
        try:
            with open(self.LORE_FILE, 'r', encoding='utf-8') as f:
                lore_data_list = load(f).get(KEY_LORE_ENTRIES, [])
                
                # Convert the loaded list into a dictionary, keyed by the 'id' field.
                lore_data_dict = {entry[KEY_LORE_ID]: entry for entry in lore_data_list if KEY_LORE_ID in entry}
                
                logger.info(f"Successfully loaded and processed {len(lore_data_dict)} lore entries.")
                return lore_data_dict
        except (IOError, TypeError, KeyError) as e:
            logger.error(f"Error loading or parsing lore file '{self.LORE_FILE}': {e}")
            return {}
        
    def _load_unlocks(self):
        """Loads player progress from the save file."""
        from constants import (
            KEY_UNLOCKED_DRONES, KEY_SELECTED_DRONE_ID, KEY_PLAYER_CORES,
            KEY_UNLOCKED_LORE_IDS, KEY_COLLECTED_CORE_FRAGMENTS,
            KEY_ARCHITECT_VAULT_COMPLETED, KEY_COLLECTED_GLYPH_TABLETS,
            KEY_SOLVED_PUZZLE_TERMINALS, KEY_DEFEATED_BOSSES
        )
        
        if exists(self.SAVE_FILE):
            try:
                with open(self.SAVE_FILE, 'r') as f:
                    data = load(f)
                    self.unlocked_drones.update(data.get(KEY_UNLOCKED_DRONES, ["DRONE"]))
                    self.selected_drone_id = data.get(KEY_SELECTED_DRONE_ID, "DRONE")
                    self.player_cores = data.get(KEY_PLAYER_CORES, 0)
                    self.unlocked_lore_ids.update(data.get(KEY_UNLOCKED_LORE_IDS, []))
                    self.collected_core_fragments.update(data.get(KEY_COLLECTED_CORE_FRAGMENTS, []))
                    self.architect_vault_completed = data.get(KEY_ARCHITECT_VAULT_COMPLETED, False)
                    self.collected_glyph_tablets.update(data.get(KEY_COLLECTED_GLYPH_TABLETS, []))
                    self.solved_puzzle_terminals.update(data.get(KEY_SOLVED_PUZZLE_TERMINALS, []))
                    self.defeated_bosses.update(data.get(KEY_DEFEATED_BOSSES, []))
                    self.unlocked_abilities.update(data.get('unlocked_abilities', [])) # NEW
            except IOError as e:
                logger.error(f"Error loading save file '{self.SAVE_FILE}': {e}")
        else:
            logger.info(f"No save file found at '{self.SAVE_FILE}'. Starting with defaults.")
            self._save_unlocks() # Create a new save file with defaults

    def _save_unlocks(self):
        """Saves current player progress to the save file."""
        if not getattr(self, '_save_dirty', True):
            return
            
        from constants import (
            KEY_UNLOCKED_DRONES, KEY_SELECTED_DRONE_ID, KEY_PLAYER_CORES,
            KEY_UNLOCKED_LORE_IDS, KEY_COLLECTED_CORE_FRAGMENTS,
            KEY_ARCHITECT_VAULT_COMPLETED, KEY_COLLECTED_GLYPH_TABLETS,
            KEY_SOLVED_PUZZLE_TERMINALS, KEY_DEFEATED_BOSSES
        )
        
        data = {
            KEY_UNLOCKED_DRONES: list(self.unlocked_drones),
            KEY_SELECTED_DRONE_ID: self.selected_drone_id,
            KEY_PLAYER_CORES: self.player_cores,
            KEY_UNLOCKED_LORE_IDS: list(self.unlocked_lore_ids),
            KEY_COLLECTED_CORE_FRAGMENTS: list(self.collected_core_fragments),
            KEY_ARCHITECT_VAULT_COMPLETED: self.architect_vault_completed,
            KEY_COLLECTED_GLYPH_TABLETS: list(self.collected_glyph_tablets),
            KEY_SOLVED_PUZZLE_TERMINALS: list(self.solved_puzzle_terminals),
            KEY_DEFEATED_BOSSES: list(self.defeated_bosses),
            'unlocked_abilities': list(self.unlocked_abilities) # NEW
        }
        try:
            makedirs(dirname(self.SAVE_FILE), exist_ok=True)
            with open(self.SAVE_FILE, 'w') as f:
                dump(data, f, indent=4)
            self._save_dirty = False
        except IOError as e:
            logger.error(f"Error saving progress to file '{self.SAVE_FILE}': {e}")
            self._save_dirty = True

    def add_defeated_boss(self, boss_id):
        """Adds a boss ID to the set of defeated bosses and saves progress."""
        if boss_id not in self.defeated_bosses:
            self.defeated_bosses.add(boss_id)
            self._save_dirty = True
            self._save_unlocks()
            logger.info(f"Boss '{boss_id}' marked as defeated.")
            return True
        return False

    def get_all_drone_ids_in_order(self):
        return list(self.drones.keys())

    def is_drone_unlocked(self, drone_id):
        return drone_id in self.unlocked_drones

    def get_selected_drone_id(self):
        return self.selected_drone_id

    def get_drone_config(self, drone_id):
        return self.drones.get(drone_id, self.drones["DRONE"])

    def get_drone_stats(self, drone_id, is_in_architect_vault=False):
        from constants import KEY_BASE_STATS, KEY_VAULT_STATS
        
        config = self.get_drone_config(drone_id)
        # Use a more robust check for 'base_stats'
        stats_source = config.get(KEY_BASE_STATS, {})
        if is_in_architect_vault and KEY_VAULT_STATS in config:
            stats_source = config.get(KEY_VAULT_STATS)
        return stats_source

    def set_selected_drone(self, drone_id):
        if self.is_drone_unlocked(drone_id) and self.selected_drone_id != drone_id:
            self.selected_drone_id = drone_id
            self._save_dirty = True
            self._save_unlocks()
            return True
        return False

    def unlock_drone(self, drone_id):
        from constants import KEY_UNLOCK_CONDITION, KEY_UNLOCK_TYPE, KEY_UNLOCK_VALUE
        
        if drone_id in self.unlocked_drones:
            return True
        
        config = self.get_drone_config(drone_id)
        unlock_condition = config.get(KEY_UNLOCK_CONDITION, {})
        unlock_type = unlock_condition.get(KEY_UNLOCK_TYPE)
        unlock_value = unlock_condition.get(KEY_UNLOCK_VALUE)

        if unlock_type == "cores":
            if self.player_cores >= unlock_value:
                self.player_cores -= unlock_value
                self.unlocked_drones.add(drone_id)
                self._save_dirty = True
                self._save_unlocks()
                logger.info(f"Drone '{drone_id}' unlocked by spending {unlock_value} cores.")
                return True
        elif unlock_type == "boss":
             if unlock_value in self.defeated_bosses:
                self.unlocked_drones.add(drone_id)
                self._save_dirty = True
                self._save_unlocks()
                logger.info(f"Drone '{drone_id}' unlocked by defeating boss '{unlock_value}'.")
                return True
        elif unlock_type == "level_reach":
            # This logic would need to be called by the game controller when a level is completed.
            # For now, it remains as a potential unlock method.
            pass
        return False
    
    def add_player_cores(self, amount):
        if amount != 0:
            self.player_cores += amount
            self._save_dirty = True
            self._save_unlocks()
        
    def get_player_cores(self):
        return self.player_cores
        
    def set_player_cores(self, amount):
        """Set the player's core count to a specific amount"""
        new_amount = max(0, amount)
        if self.player_cores != new_amount:
            self.player_cores = new_amount
            self._save_dirty = True
            self._save_unlocks()
        return self.player_cores
        
    def spend_player_cores(self, amount):
        if self.player_cores >= amount:
            self.player_cores -= amount
            self._save_dirty = True
            self._save_unlocks()
            return True
        return False

    def unlock_lore_entry_by_id(self, lore_id):
        """Unlocks a specific lore entry if it's not already unlocked."""
        if lore_id in self.all_lore_entries and lore_id not in self.unlocked_lore_ids:
            self.unlocked_lore_ids.add(lore_id)
            logger.info(f"Lore Codex Entry '{lore_id}' unlocked!")
            self._save_dirty = True
            self._save_unlocks()
            return [lore_id]
        return []
        
    def check_and_unlock_lore_entries(self, event_trigger, **kwargs):
        """Checks conditions for all lore entries and unlocks them if criteria are met."""
        from constants import KEY_LORE_UNLOCKED_BY
        
        unlocked_ids_this_check = []
        for lore_id, entry in self.all_lore_entries.items():
            if lore_id not in self.unlocked_lore_ids and entry.get(KEY_LORE_UNLOCKED_BY) == event_trigger:
                self.unlocked_lore_ids.add(lore_id)
                logger.info(f"Lore Codex Entry '{lore_id}' unlocked!")
                unlocked_ids_this_check.append(lore_id)
        
        if unlocked_ids_this_check:
            self._save_dirty = True
            self._save_unlocks()
        return unlocked_ids_this_check

    def get_lore_entry_details(self, lore_id):
        return self.all_lore_entries.get(lore_id)
        
    def has_unlocked_lore(self, lore_id):
        return lore_id in self.unlocked_lore_ids

    def get_unlocked_lore_categories(self):
        """Gets a sorted list of unique categories from all unlocked lore entries."""
        from constants import KEY_LORE_CATEGORY
        
        if not self.unlocked_lore_ids:
            return []
        
        # Cache preferred order as class attribute to avoid recreating
        if not hasattr(self, '_preferred_order'):
            self._preferred_order = ["Story", "Architect's Echoes", "Drones", "Alien Tech", "Alien Races", "Locations", "Story Beats"]
        
        categories = {entry[KEY_LORE_CATEGORY] 
                     for lore_id in self.unlocked_lore_ids 
                     if (entry := self.all_lore_entries.get(lore_id)) and KEY_LORE_CATEGORY in entry}
        
        return sorted(categories, key=lambda x: self._preferred_order.index(x) if x in self._preferred_order else len(self._preferred_order))

    def get_unlocked_lore_entries_by_category(self, category_name):
        """Gets a list of all unlocked lore entries within a specific category."""
        from constants import KEY_LORE_CATEGORY, KEY_LORE_SEQUENCE
        
        entries = []
        for lore_id in self.unlocked_lore_ids:
            entry = self.all_lore_entries.get(lore_id)
            if entry and entry.get(KEY_LORE_CATEGORY) == category_name:
                entries.append(entry)
        
        # Ensure a 'sequence' key exists for sorting, default to 0 if not present
        entries.sort(key=lambda x: x.get(KEY_LORE_SEQUENCE, 0))
        return entries
        
    def collect_core_fragment(self, fragment_id):
        if fragment_id not in self.collected_core_fragments:
            self.collected_core_fragments.add(fragment_id)
            self._save_dirty = True
            self._save_unlocks()
            return True
        return True  # Return True even if already collected to support chapter selection

    def has_collected_fragment(self, fragment_id):
        return fragment_id in self.collected_core_fragments
        
    def get_collected_fragments_ids(self):
        return self.collected_core_fragments

    def unlock_ability(self, ability_id):
        if ability_id not in self.unlocked_abilities:
            self.unlocked_abilities.add(ability_id)
            self._save_dirty = True
            self._save_unlocks()
            logger.info(f"Ability '{ability_id}' unlocked!")
            return True
        return False
    
    def has_ability_unlocked(self, ability_id):
        return ability_id in self.unlocked_abilities
    
    def are_all_core_fragments_collected(self):
        """Checks if all fragments *required for the vault* are collected."""
        from constants import KEY_FRAGMENT_ID, KEY_FRAGMENT_REQUIRED_FOR_VAULT
        
        # Cache required fragments to avoid repeated computation
        if not hasattr(self, '_required_fragments'):
            core_fragments = settings_manager.get_core_fragment_details()
            self._required_fragments = frozenset(details[KEY_FRAGMENT_ID] for _, details in core_fragments.items() 
                                                if details and details.get(KEY_FRAGMENT_REQUIRED_FOR_VAULT))
            if not self._required_fragments:
                logger.warning(f"No fragments marked as '{KEY_FRAGMENT_REQUIRED_FOR_VAULT}'. Vault may be permanently locked.")
        
        return bool(self._required_fragments) and self._required_fragments.issubset(self.collected_core_fragments)   
        
    def reset_collected_fragments_in_storage(self):
        self.collected_core_fragments.clear()
        logger.info("Persisted collected core fragments have been reset for new game session.")
        self._save_dirty = True
        self._save_unlocks()

    def mark_architect_vault_completed(self, success_status):
        self.architect_vault_completed = success_status
        self._save_dirty = True
        self._save_unlocks()
        
    def has_completed_architect_vault(self):
        return self.architect_vault_completed
        
    def reset_architect_vault_status(self):
        self.architect_vault_completed = False
        logger.info("Architect's Vault completion status reset for new game session.")
        self._save_dirty = True
        self._save_unlocks()

    def add_collected_glyph_tablet(self, tablet_id):
        if tablet_id not in self.collected_glyph_tablets:
            self.collected_glyph_tablets.add(tablet_id)
            self._save_dirty = True
            self._save_unlocks()
            return True
        return False
        
    def mark_puzzle_terminal_as_solved(self, terminal_id):
        if terminal_id not in self.solved_puzzle_terminals:
            self.solved_puzzle_terminals.add(terminal_id)
            self._save_dirty = True
            self._save_unlocks()
            return True
        return False
        
    def has_puzzle_terminal_been_solved(self, terminal_id):
        return terminal_id in self.solved_puzzle_terminals

    def set_player_level(self, level):
        """Placeholder for potential future logic related to player level."""
        pass
    
    def _unlock_default_lore_entries(self):
        """Unlock some basic lore entries that should be available from the start"""
        default_entries = [
            "architect_legacy_intro",
            "drone_DRONE"
        ]
        
        for entry_id in default_entries:
            if entry_id in self.all_lore_entries and entry_id not in self.unlocked_lore_ids:
                self.unlocked_lore_ids.add(entry_id)
                logger.info(f"Default lore entry '{entry_id}' unlocked")
        
        if default_entries:
            self._save_dirty = True
            self._save_unlocks()
