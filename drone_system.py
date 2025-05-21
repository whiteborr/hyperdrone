import json
import os
import random

# Import from drone_configs.py
try:
    from drone_configs import DRONE_DATA, DRONE_DISPLAY_ORDER, OMEGA_STAT_RANGES
    # Note: Special ability constants like PHANTOM_CLOAK_DURATION_MS_CONFIG
    # are in drone_configs.py. Player will get effective values via game_settings.
except ImportError:
    print("Critical Error (drone_system.py): Could not import from drone_configs.py. System may not function.")
    DRONE_DATA = {}
    DRONE_DISPLAY_ORDER = []
    OMEGA_STAT_RANGES = {}

# Import from game_settings.py
try:
    from game_settings import (
        CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED,
        ARCHITECT_REWARD_BLUEPRINT_ID, ARCHITECT_REWARD_LORE_ID,
        # get_game_setting is used by player.py to get effective ability values
        # DroneSystem might not need get_game_setting directly for these if player handles it.
    )
except ImportError:
    print("Warning (drone_system.py): Could not import all constants from game_settings. Using fallbacks.")
    CORE_FRAGMENT_DETAILS = {}
    TOTAL_CORE_FRAGMENTS_NEEDED = 3
    ARCHITECT_REWARD_BLUEPRINT_ID = "DRONE_ARCHITECT_X"
    ARCHITECT_REWARD_LORE_ID = "lore_architect_origin"

DATA_DIR = "data" # Directory to store save files
UNLOCKS_FILE_PATH = os.path.join(DATA_DIR, "drone_unlocks.json")

class DroneSystem:
    """
    Manages drone configurations, unlock status, player progress related to drones,
    and persistence of this data, including collected core fragments and Architect's Vault rewards.
    """
    def __init__(self):
        """Initializes the DroneSystem by ensuring data directory exists and loading unlock data."""
        self._ensure_data_dir_exists()
        self.unlock_data = self._load_unlocks()

    def _ensure_data_dir_exists(self):
        """Ensures the data directory (e.g., 'data/') exists. Creates it if not."""
        if not os.path.exists(DATA_DIR):
            try:
                os.makedirs(DATA_DIR)
                print(f"DroneSystem: Created directory: {DATA_DIR}")
            except OSError as e:
                print(f"DroneSystem: Error creating directory {DATA_DIR}: {e}")

    def _load_unlocks(self):
        """
        Loads drone unlock status and player progress from a JSON file.
        If the file doesn't exist or is corrupted, creates/returns default data.
        """
        default_data = {
            "unlocked_drones": ["ORIGINAL_DRONE"], # ORIGINAL_DRONE is always unlocked
            "selected_drone": "ORIGINAL_DRONE",
            "player_level": 1,
            "bosses_defeated": [], # For future boss unlock conditions
            "player_cores": 0,
            "collected_core_fragments": [], # List of fragment_ids
            "architect_vault_completed": False,
            "unlocked_blueprints": [], # List of blueprint_ids (e.g., for Architect-X)
            "unlocked_lore_codex_entries": []
        }

        if not os.path.exists(UNLOCKS_FILE_PATH):
            print(f"DroneSystem: '{UNLOCKS_FILE_PATH}' not found. Creating default unlock data.")
            self._save_unlocks(default_data) # Save the default data immediately
            return default_data

        try:
            with open(UNLOCKS_FILE_PATH, 'r') as f:
                data = json.load(f)
                # Merge loaded data with defaults to ensure all keys are present for robustness
                for key, value in default_data.items():
                    data.setdefault(key, value) # Adds key with default value if key is missing

                # Sanity check: Ensure ORIGINAL_DRONE is always in unlocked_drones.
                if "ORIGINAL_DRONE" not in data.get("unlocked_drones", []):
                    data.setdefault("unlocked_drones", []).append("ORIGINAL_DRONE")

                # Sanity check: If selected_drone is not valid or not unlocked, reset.
                if data.get("selected_drone") not in data.get("unlocked_drones", []) or \
                   data.get("selected_drone") not in DRONE_DATA:
                    print(f"DroneSystem: Warning - Previously selected drone '{data.get('selected_drone')}' is not valid/unlocked. Resetting to ORIGINAL_DRONE.")
                    data["selected_drone"] = "ORIGINAL_DRONE"

                # Validate collected_core_fragments against current game definitions
                if "collected_core_fragments" in data and CORE_FRAGMENT_DETAILS:
                    valid_fragment_ids = [details["id"] for cfg_key, details in CORE_FRAGMENT_DETAILS.items() if details and "id" in details]
                    data["collected_core_fragments"] = [fid for fid in data["collected_core_fragments"] if fid in valid_fragment_ids]
                else:
                    data["collected_core_fragments"] = []
                return data
        except (IOError, json.JSONDecodeError) as e:
            print(f"DroneSystem: Error loading or parsing '{UNLOCKS_FILE_PATH}': {e}. Returning default and attempting to re-save.")
            self._save_unlocks(default_data)
            return default_data

    def _save_unlocks(self, data_to_save=None):
        """Saves the current unlock status (or provided data) to the JSON file."""
        self._ensure_data_dir_exists() # Make sure dir exists before trying to save
        current_data_to_save = data_to_save if data_to_save is not None else self.unlock_data
        try:
            with open(UNLOCKS_FILE_PATH, 'w') as f:
                json.dump(current_data_to_save, f, indent=2) # Use indent for readability
        except IOError as e:
            print(f"DroneSystem: Error saving unlock data to '{UNLOCKS_FILE_PATH}': {e}")

    def get_selected_drone_id(self):
        """Returns the ID of the currently selected drone."""
        return self.unlock_data.get("selected_drone", "ORIGINAL_DRONE")

    def set_selected_drone_id(self, drone_id):
        """Sets the selected drone if it's valid and unlocked, then saves."""
        if drone_id in DRONE_DATA and self.is_drone_unlocked(drone_id):
            self.unlock_data["selected_drone"] = drone_id
            self._save_unlocks()
            print(f"DroneSystem: Drone '{drone_id}' selected.")
            return True
        print(f"DroneSystem: Failed to select drone '{drone_id}'. Not found in DRONE_DATA or not unlocked.")
        return False

    def get_drone_config(self, drone_id):
        """
        Returns the base configuration for a specific drone ID from DRONE_DATA.
        Returns ORIGINAL_DRONE's config as a fallback if the ID is not found.
        """
        config = DRONE_DATA.get(drone_id)
        if not config:
            print(f"DroneSystem: Warning - Drone ID '{drone_id}' not found in DRONE_DATA. Returning ORIGINAL_DRONE config.")
            return DRONE_DATA.get("ORIGINAL_DRONE", {}) # Ensure ORIGINAL_DRONE itself exists as a fallback
        return config

    def get_all_drone_ids_ordered(self):
        """Returns a list of all drone IDs in their intended display order from drone_configs."""
        return DRONE_DISPLAY_ORDER # Imported from drone_configs

    def is_drone_unlocked(self, drone_id):
        """Checks if a specific drone ID is present in the list of unlocked drones or blueprints."""
        if drone_id in self.unlock_data.get("unlocked_drones", []):
            return True
        # Check if it's an unlocked blueprint that corresponds to a drone ID
        if drone_id in self.unlock_data.get("unlocked_blueprints", []) and drone_id in DRONE_DATA:
            return True
        return False

    def get_player_level(self):
        """Returns the player's current level."""
        return self.unlock_data.get("player_level", 1)

    def set_player_level(self, level):
        """
        Sets the player's level, checks for new passive drone unlocks, and saves if changes occurred.
        Returns a list of newly unlocked drone IDs.
        """
        self.unlock_data["player_level"] = level
        newly_unlocked = self._check_for_passive_unlocks() # This will save if new unlocks occur
        if not newly_unlocked: # Save if level changed but no new unlocks
            self._save_unlocks()
        if newly_unlocked:
             print(f"DroneSystem: Player level set to {level}. New unlocks: {newly_unlocked}")
        return newly_unlocked

    def get_player_cores(self):
        """Returns the player's current number of cores."""
        return self.unlock_data.get("player_cores", 0)

    def add_player_cores(self, amount):
        """Adds cores to the player's total. Does not save on its own; caller should save."""
        self.unlock_data["player_cores"] = self.unlock_data.get("player_cores", 0) + amount
        # GameController should call _save_unlocks() at appropriate times (e.g., end of level).

    def spend_player_cores(self, amount):
        """Spends player cores if available. Saves immediately if successful."""
        current_cores = self.get_player_cores()
        if current_cores >= amount:
            self.unlock_data["player_cores"] = current_cores - amount
            self._save_unlocks() # Save after spending
            return True
        return False

    def add_defeated_boss(self, boss_name):
        """Adds a defeated boss, checks for unlocks, and saves if new unlocks occurred."""
        if boss_name not in self.unlock_data.get("bosses_defeated", []):
            self.unlock_data.setdefault("bosses_defeated", []).append(boss_name)
            newly_unlocked = self._check_for_passive_unlocks()
            if not newly_unlocked: self._save_unlocks() # Save if boss added but no new unlocks
            if newly_unlocked:
                 print(f"DroneSystem: Boss '{boss_name}' defeated. New unlocks: {newly_unlocked}")
            return newly_unlocked
        return []

    def _check_for_passive_unlocks(self):
        """
        Checks all drones if passive unlock conditions (level, boss defeat) are met.
        Updates internal list and saves if any new drone is unlocked.
        Returns a list of newly unlocked drone IDs from this check.
        """
        newly_unlocked_this_check = []
        player_level = self.get_player_level()
        bosses_defeated = self.unlock_data.get("bosses_defeated", [])
        unlocked_drones_list = self.unlock_data.setdefault("unlocked_drones", [])

        for drone_id, config in DRONE_DATA.items():
            if drone_id in unlocked_drones_list:
                continue # Already unlocked

            condition = config.get("unlock_condition", {})
            unlock_type = condition.get("type")
            unlock_value = condition.get("value")
            unlocked_by_passive_condition = False

            if unlock_type == "default":
                unlocked_by_passive_condition = True
            elif unlock_type == "level" and player_level >= unlock_value:
                unlocked_by_passive_condition = True
            elif unlock_type == "boss" and unlock_value in bosses_defeated:
                unlocked_by_passive_condition = True
            # "cores" and "blueprint" types are not passive, handled by other methods.

            if unlocked_by_passive_condition:
                if drone_id not in unlocked_drones_list: # Should be true if we passed the first check
                    unlocked_drones_list.append(drone_id)
                    newly_unlocked_this_check.append(drone_id)

        if newly_unlocked_this_check:
            # self.unlock_data["unlocked_drones"] is already updated by reference
            self._save_unlocks() # Save if new drones were passively unlocked
            print(f"DroneSystem: Passive check unlocked: {newly_unlocked_this_check}")
        return newly_unlocked_this_check

    def attempt_unlock_drone_with_cores(self, drone_id):
        """Attempts to unlock a drone by spending cores. Returns True if successful."""
        if self.is_drone_unlocked(drone_id):
            return True # Already unlocked

        config = self.get_drone_config(drone_id)
        if not config: return False # Should not happen if drone_id is valid

        unlock_condition = config.get("unlock_condition", {})
        if unlock_condition.get("type") != "cores":
            return False # Not unlockable by cores

        cost = unlock_condition.get("value", float('inf'))
        if self.spend_player_cores(cost): # spend_player_cores already saves
            unlocked_list = self.unlock_data.setdefault("unlocked_drones", [])
            if drone_id not in unlocked_list:
                unlocked_list.append(drone_id)
            # Save again to ensure the drone_id is added to the unlocked_drones list in the file
            self._save_unlocks()
            print(f"DroneSystem: Drone '{drone_id}' unlocked by spending {cost} cores.")
            return True
        return False

    def get_drone_stats(self, drone_id, is_in_architect_vault=False):
        """
        Returns the effective stats for a drone, applying special modifications
        like Omega-9's randomization and buffs from collected Core Fragments if in the Vault.
        """
        base_config = self.get_drone_config(drone_id)
        if not base_config or "base_stats" not in base_config:
            print(f"DroneSystem: Error - Base config or base_stats not found for drone '{drone_id}'. Returning minimal stats.")
            return {"hp": 100, "speed": 3, "turn_speed": 5, "fire_rate_multiplier": 1.0, "bullet_damage_multiplier": 1.0, "special_ability": None}

        effective_stats = base_config["base_stats"].copy() # Start with a copy of defined base stats

        # Apply Omega-9 specific randomization if applicable
        if drone_id == "OMEGA-9" and effective_stats.get("special_ability") == "omega_boost":
            # print(f"DroneSystem: OMEGA-9 ({drone_id}): Applying random stat boosts.")
            for stat_name, (min_mult, max_mult) in OMEGA_STAT_RANGES.items():
                if stat_name in effective_stats:
                    original_value = effective_stats[stat_name]
                    multiplier = random.uniform(min_mult, max_mult)
                    modified_value = original_value * multiplier
                    
                    # Ensure HP is an integer, other stats can be float
                    effective_stats[stat_name] = int(modified_value) if stat_name == "hp" else modified_value

        # If in Architect's Vault, apply buffs from collected Core Fragments
        if is_in_architect_vault and CORE_FRAGMENT_DETAILS:
            collected_fragment_ids = self.get_collected_fragments_ids()
            for frag_id in collected_fragment_ids:
                fragment_config = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                
                if fragment_config:
                    # Apply primary buff if defined
                    if "buff" in fragment_config:
                        buff = fragment_config["buff"]
                        buff_type = buff.get("type")
                        buff_value = buff.get("value")
                        if buff_type == "speed" and "speed" in effective_stats:
                            effective_stats["speed"] *= buff_value
                        elif buff_type == "damage" and "bullet_damage_multiplier" in effective_stats:
                            effective_stats["bullet_damage_multiplier"] *= buff_value
                        # Add more primary buff types here

                    # Apply alternative buff if defined
                    if "buff_alt" in fragment_config:
                        buff_alt = fragment_config["buff_alt"]
                        buff_alt_type = buff_alt.get("type")
                        buff_alt_value = buff_alt.get("value")
                        if buff_alt_type == "damage_reduction": # Example: damage_taken_multiplier
                            # Assuming a stat like 'damage_taken_multiplier' exists or is added
                            effective_stats["damage_taken_multiplier"] = effective_stats.get("damage_taken_multiplier", 1.0) * (1.0 - buff_alt_value)
                        # Add more alternative buff types here
        return effective_stats

    # --- Methods for Core Fragments ---
    def collect_core_fragment(self, fragment_id_to_collect):
        """Adds a fragment_id to the list of collected fragments if not already present and saves."""
        if not CORE_FRAGMENT_DETAILS:
            print("DroneSystem: Warning - CORE_FRAGMENT_DETAILS not loaded. Cannot validate/collect fragment.")
            return False

        is_valid_fragment = any(details["id"] == fragment_id_to_collect for _, details in CORE_FRAGMENT_DETAILS.items() if details and "id" in details)
        if not is_valid_fragment:
            print(f"DroneSystem: Warning - Attempted to collect invalid fragment_id: {fragment_id_to_collect}")
            return False

        collected_list = self.unlock_data.setdefault("collected_core_fragments", [])
        if fragment_id_to_collect not in collected_list:
            collected_list.append(fragment_id_to_collect)
            self._save_unlocks()
            print(f"DroneSystem: Core Fragment '{fragment_id_to_collect}' collected. Total: {len(collected_list)}/{TOTAL_CORE_FRAGMENTS_NEEDED}")
            return True
        return False # Already collected

    def has_collected_fragment(self, fragment_id_to_check):
        """Checks if a specific core fragment has been collected."""
        return fragment_id_to_check in self.unlock_data.get("collected_core_fragments", [])

    def get_collected_fragments_ids(self):
        """Returns a copy of the list of collected core fragment IDs."""
        return self.unlock_data.get("collected_core_fragments", [])[:] # Return a copy

    def are_all_core_fragments_collected(self):
        """Checks if the number of collected fragments meets the required total."""
        num_collected = len(self.unlock_data.get("collected_core_fragments", []))
        return num_collected >= TOTAL_CORE_FRAGMENTS_NEEDED

    def reset_collected_fragments(self): # For testing or specific game events
        """Resets the list of collected fragments and saves."""
        self.unlock_data["collected_core_fragments"] = []
        self._save_unlocks()
        print("DroneSystem: Collected core fragments have been reset.")

    # --- Methods for Architect's Vault Completion & Rewards ---
    def mark_architect_vault_completed(self, completed_successfully=True):
        """Marks the Architect's Vault as completed and handles related rewards."""
        self.unlock_data["architect_vault_completed"] = completed_successfully
        if completed_successfully:
            print("DroneSystem: Architect's Vault completed successfully!")
            # Unlock associated blueprint and lore entry
            if ARCHITECT_REWARD_BLUEPRINT_ID: self.unlock_blueprint(ARCHITECT_REWARD_BLUEPRINT_ID)
            if ARCHITECT_REWARD_LORE_ID: self.unlock_lore_entry(ARCHITECT_REWARD_LORE_ID)
        else:
            print("DroneSystem: Architect's Vault attempt failed.")
        self._save_unlocks()

    def has_completed_architect_vault(self):
        """Checks if the Architect's Vault has been successfully completed."""
        return self.unlock_data.get("architect_vault_completed", False)

    def unlock_blueprint(self, blueprint_id):
        """Adds a blueprint ID to the player's unlocked list and saves. Also unlocks the drone if applicable."""
        if not blueprint_id: return False
        unlocked_blueprints_list = self.unlock_data.setdefault("unlocked_blueprints", [])
        newly_unlocked_blueprint = False
        if blueprint_id not in unlocked_blueprints_list:
            unlocked_blueprints_list.append(blueprint_id)
            newly_unlocked_blueprint = True
            print(f"DroneSystem: Blueprint '{blueprint_id}' unlocked!")

        # If the blueprint ID also corresponds to a drone ID in DRONE_DATA, unlock it directly
        newly_unlocked_drone_via_blueprint = False
        if blueprint_id in DRONE_DATA:
            unlocked_drones_list = self.unlock_data.setdefault("unlocked_drones", [])
            if blueprint_id not in unlocked_drones_list:
                unlocked_drones_list.append(blueprint_id)
                newly_unlocked_drone_via_blueprint = True
                print(f"DroneSystem: Drone '{blueprint_id}' unlocked via blueprint.")

        if newly_unlocked_blueprint or newly_unlocked_drone_via_blueprint:
            self._save_unlocks()
        return newly_unlocked_blueprint or newly_unlocked_drone_via_blueprint


    def has_unlocked_blueprint(self, blueprint_id):
        """Checks if a specific blueprint has been unlocked."""
        return blueprint_id in self.unlock_data.get("unlocked_blueprints", [])

    def unlock_lore_entry(self, lore_id):
        """Adds a lore ID to the player's unlocked list if not already present and saves."""
        if not lore_id: return False
        unlocked_lore_list = self.unlock_data.setdefault("unlocked_lore_codex_entries", [])
        if lore_id not in unlocked_lore_list:
            unlocked_lore_list.append(lore_id)
            self._save_unlocks()
            print(f"DroneSystem: Lore Codex Entry '{lore_id}' unlocked!")
            return True
        return False # Already unlocked

    def has_unlocked_lore(self, lore_id):
        """Checks if a specific lore entry has been unlocked."""
        return lore_id in self.unlock_data.get("unlocked_lore_codex_entries", [])

    def reset_all_progress(self): # For full game reset option
        """Resets all unlock data to defaults."""
        print("DroneSystem: Resetting all player progress to default.")
        # Create a fresh default_data dictionary
        default_data = {
            "unlocked_drones": ["ORIGINAL_DRONE"], "selected_drone": "ORIGINAL_DRONE",
            "player_level": 1, "bosses_defeated": [], "player_cores": 0,
            "collected_core_fragments": [], "architect_vault_completed": False,
            "unlocked_blueprints": [], "unlocked_lore_codex_entries": []
        }
        self.unlock_data = default_data
        self._save_unlocks()
        print("DroneSystem: All progress reset.")

# Example Usage / Testing (can be commented out for production)
if __name__ == '__main__':
    print("DroneSystem: Running self-test...")
    # Create a dummy game_settings.py if it doesn't exist for testing
    if not os.path.exists("game_settings.py"):
        with open("game_settings.py", "w") as gs_file:
            gs_file.write("PLAYER_MAX_HEALTH = 100\n")
            gs_file.write("PLAYER_SPEED = 3\n")
            gs_file.write("ROTATION_SPEED = 5\n")
            gs_file.write("CORE_FRAGMENT_DETAILS = {}\n") # Empty for test
            gs_file.write("TOTAL_CORE_FRAGMENTS_NEEDED = 0\n")
            gs_file.write("ARCHITECT_REWARD_BLUEPRINT_ID = 'TEST_BLUEPRINT_ARCH'\n")
            gs_file.write("ARCHITECT_REWARD_LORE_ID = 'TEST_LORE_ARCH'\n")
    if not os.path.exists("drone_configs.py"):
         with open("drone_configs.py", "w") as dc_file:
            dc_file.write("DRONE_DATA = {'ORIGINAL_DRONE': {'name': 'Test Drone', 'base_stats': {'hp':100, 'speed':3, 'turn_speed':5, 'fire_rate_multiplier':1, 'bullet_damage_multiplier':1, 'special_ability':None}, 'unlock_condition':{'type':'default'}} }\n")
            dc_file.write("DRONE_DISPLAY_ORDER = ['ORIGINAL_DRONE']\n")
            dc_file.write("OMEGA_STAT_RANGES = {}\n")


    ds = DroneSystem()
    print(f"DroneSystem Test: Initial selected drone: {ds.get_selected_drone_id()}")
    print(f"DroneSystem Test: Is VANTIS unlocked? {ds.is_drone_unlocked('VANTIS')}") # Assuming VANTIS is in DRONE_DATA
    ds.set_player_level(5)
    print(f"DroneSystem Test: Player level after set: {ds.get_player_level()}")
    ds.add_player_cores(500)
    # ds._save_unlocks() # Explicit save after add_player_cores if it doesn't save itself
    print(f"DroneSystem Test: Player cores after add: {ds.get_player_cores()}")
    ds.spend_player_cores(100)
    print(f"DroneSystem Test: Player cores after spend: {ds.get_player_cores()}")

    # Test reset
    # ds.reset_all_progress()
    # print(f"DroneSystem Test: Player cores after reset: {ds.get_player_cores()}")
    # print(f"DroneSystem Test: Selected drone after reset: {ds.get_selected_drone_id()}")