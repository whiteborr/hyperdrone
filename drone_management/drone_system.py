# drone_management/drone_system.py
import json
import os
import logging
from .drone_configs import DRONE_DATA
import game_settings as gs

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

        # Vault status
        self.architect_vault_completed = False

        self._load_unlocks()
        logger.info(f"DroneSystem initialized. Unlocked drones: {self.unlocked_drones}. Selected: {self.selected_drone_id}")

    def _load_all_lore_entries(self):
        """Loads all possible lore entries from the JSON file and converts the list to a dictionary."""
        if not os.path.exists(self.LORE_FILE):
            logger.error(f"DroneSystem: Lore file not found at '{self.LORE_FILE}'. No lore will be available.")
            return {}
        try:
            with open(self.LORE_FILE, 'r') as f:
                lore_data_list = json.load(f)
                
                # <<< FIX: Convert the loaded list into a dictionary, keyed by the 'id' field. >>>
                lore_data_dict = {entry['id']: entry for entry in lore_data_list if 'id' in entry}
                
                logger.info(f"DroneSystem: Successfully loaded and processed {len(lore_data_dict)} lore entries.")
                return lore_data_dict
        except (IOError, json.JSONDecodeError, TypeError) as e:
            logger.error(f"DroneSystem: Error loading or parsing lore file '{self.LORE_FILE}': {e}")
            return {}

    def _load_unlocks(self):
        """Loads player progress from the save file."""
        if os.path.exists(self.SAVE_FILE):
            try:
                with open(self.SAVE_FILE, 'r') as f:
                    data = json.load(f)
                    self.unlocked_drones.update(data.get("unlocked_drones", ["DRONE"]))
                    self.selected_drone_id = data.get("selected_drone_id", "DRONE")
                    self.player_cores = data.get("player_cores", 0)
                    self.unlocked_lore_ids.update(data.get("unlocked_lore_ids", []))
                    self.collected_core_fragments.update(data.get("collected_core_fragments", []))
                    self.architect_vault_completed = data.get("architect_vault_completed", False)
                    self.collected_glyph_tablets.update(data.get("collected_glyph_tablets", []))
                    self.solved_puzzle_terminals.update(data.get("solved_puzzle_terminals", []))
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"DroneSystem: Error loading save file '{self.SAVE_FILE}': {e}")
        else:
            logger.info(f"DroneSystem: No save file found at '{self.SAVE_FILE}'. Starting with defaults.")
            self._save_unlocks() # Create a new save file with defaults

    def _save_unlocks(self):
        """Saves current player progress to the save file."""
        data = {
            "unlocked_drones": list(self.unlocked_drones),
            "selected_drone_id": self.selected_drone_id,
            "player_cores": self.player_cores,
            "unlocked_lore_ids": list(self.unlocked_lore_ids),
            "collected_core_fragments": list(self.collected_core_fragments),
            "architect_vault_completed": self.architect_vault_completed,
            "collected_glyph_tablets": list(self.collected_glyph_tablets),
            "solved_puzzle_terminals": list(self.solved_puzzle_terminals)
        }
        try:
            os.makedirs(os.path.dirname(self.SAVE_FILE), exist_ok=True)
            with open(self.SAVE_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            logger.error(f"DroneSystem: Error saving progress to file '{self.SAVE_FILE}': {e}")

    def get_all_drone_ids_in_order(self):
        return list(self.drones.keys())

    def is_drone_unlocked(self, drone_id):
        return drone_id in self.unlocked_drones

    def get_selected_drone_id(self):
        return self.selected_drone_id

    def get_drone_config(self, drone_id):
        return self.drones.get(drone_id, self.drones["DRONE"])

    def get_drone_stats(self, drone_id, is_in_architect_vault=False):
        config = self.get_drone_config(drone_id)
        return config.get("vault_stats") if is_in_architect_vault and "vault_stats" in config else config.get("stats", {})

    def set_selected_drone(self, drone_id):
        if self.is_drone_unlocked(drone_id):
            self.selected_drone_id = drone_id
            self._save_unlocks()
            return True
        return False

    def unlock_drone(self, drone_id):
        if drone_id in self.unlocked_drones:
            return True
        
        config = self.get_drone_config(drone_id)
        unlock_condition = config.get("unlock_condition", {})
        unlock_type = unlock_condition.get("type")
        unlock_value = unlock_condition.get("value")

        if unlock_type == "cores":
            if self.player_cores >= unlock_value:
                self.player_cores -= unlock_value
                self.unlocked_drones.add(drone_id)
                self._save_unlocks()
                return True
        elif unlock_type == "level_reach":
            pass
        return False

    def add_player_cores(self, amount):
        self.player_cores += amount
        self._save_unlocks()
        
    def get_player_cores(self):
        return self.player_cores
        
    def spend_player_cores(self, amount):
        if self.player_cores >= amount:
            self.player_cores -= amount
            self._save_unlocks()
            return True
        return False

    # --- Lore and Progression Methods ---
    def unlock_lore_entry_by_id(self, lore_id):
        """Unlocks a specific lore entry if it's not already unlocked."""
        if lore_id in self.all_lore_entries and lore_id not in self.unlocked_lore_ids:
            self.unlocked_lore_ids.add(lore_id)
            logger.info(f"DroneSystem: Lore Codex Entry '{lore_id}' unlocked!")
            self._save_unlocks()
            return [lore_id]
        return []
        
    def check_and_unlock_lore_entries(self, event_trigger, **kwargs):
        """Checks conditions for all lore entries and unlocks them if criteria are met."""
        unlocked_ids_this_check = []
        # This loop now works correctly because self.all_lore_entries is a dictionary
        for lore_id, entry in self.all_lore_entries.items():
            if lore_id not in self.unlocked_lore_ids:
                if entry.get("unlock_trigger") == event_trigger:
                    self.unlock_lore_entry_by_id(lore_id)
                    unlocked_ids_this_check.append(lore_id)
        return unlocked_ids_this_check

    def get_lore_entry_details(self, lore_id):
        # This method now works correctly because self.all_lore_entries is a dictionary
        return self.all_lore_entries.get(lore_id)
        
    def has_unlocked_lore(self, lore_id):
        return lore_id in self.unlocked_lore_ids

    def get_unlocked_lore_categories(self):
        """Gets a sorted list of unique categories from all unlocked lore entries."""
        if not self.unlocked_lore_ids:
            return []
        
        categories = set()
        for lore_id in self.unlocked_lore_ids:
            entry = self.all_lore_entries.get(lore_id)
            if entry and "category" in entry:
                categories.add(entry["category"])
        
        preferred_order = ["Main Story", "Drones", "Factions", "Alien Races", "Technology", "Locations"]
        
        sorted_categories = sorted(list(categories), key=lambda x: preferred_order.index(x) if x in preferred_order else len(preferred_order))
        
        return sorted_categories

    def get_unlocked_lore_entries_by_category(self, category_name):
        """Gets a list of all unlocked lore entries within a specific category."""
        entries = []
        for lore_id in self.unlocked_lore_ids:
            entry = self.all_lore_entries.get(lore_id)
            if entry and entry.get("category") == category_name:
                entries.append(entry)
        
        entries.sort(key=lambda x: x.get('sequence', 0))
        return entries
        
    def collect_core_fragment(self, fragment_id):
        if fragment_id not in self.collected_core_fragments:
            self.collected_core_fragments.add(fragment_id)
            self._save_unlocks()
            return True
        return False

    def has_collected_fragment(self, fragment_id):
        return fragment_id in self.collected_core_fragments
        
    def get_collected_fragments_ids(self):
        return self.collected_core_fragments

    def are_all_core_fragments_collected(self):
        """Checks if all fragments *required for the vault* are collected."""
        required_fragments = {details['id'] for _, details in gs.CORE_FRAGMENT_DETAILS.items() if details and details.get('required_for_vault')}
        return required_fragments.issubset(self.collected_core_fragments)
        
    def reset_collected_fragments_in_storage(self):
        self.collected_core_fragments.clear()
        logger.info("DroneSystem: Persisted collected core fragments have been reset for new game session.")
        self._save_unlocks()

    def mark_architect_vault_completed(self, success_status):
        self.architect_vault_completed = success_status
        self._save_unlocks()
        
    def has_completed_architect_vault(self):
        return self.architect_vault_completed
        
    def reset_architect_vault_status(self):
        self.architect_vault_completed = False
        logger.info("DroneSystem: Architect's Vault completion status reset for new game session.")
        self._save_unlocks()

    def add_collected_glyph_tablet(self, tablet_id):
        if tablet_id not in self.collected_glyph_tablets:
            self.collected_glyph_tablets.add(tablet_id)
            self._save_unlocks()
            return True
        return False
        
    def mark_puzzle_terminal_as_solved(self, terminal_id):
        if terminal_id not in self.solved_puzzle_terminals:
            self.solved_puzzle_terminals.add(terminal_id)
            self._save_unlocks()
            return True
        return False
        
    def has_puzzle_terminal_been_solved(self, terminal_id):
        return terminal_id in self.solved_puzzle_terminals

    def set_player_level(self, level):
        pass
