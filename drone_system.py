import json
import os
import random

from drone_configs import DRONE_DATA, OMEGA_STAT_RANGES
# Import new settings from game_settings for validation and use
from game_settings import CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED

DATA_DIR = "data" # Directory to store save files
UNLOCKS_FILE_PATH = os.path.join(DATA_DIR, "drone_unlocks.json") # Path to the drone unlocks save file

class DroneSystem:
    """
    Manages drone configurations, unlock status, player progress related to drones,
    and persistence of this data, including collected core fragments.
    """
    def __init__(self):
        """Initializes the DroneSystem by ensuring data directory exists and loading unlock data."""
        self._ensure_data_dir_exists() # Ensure 'data' directory exists before any file operations.
        self.unlock_data = self._load_unlocks() # Load existing unlock data or create default.

    def _ensure_data_dir_exists(self):
        """Ensures the data directory (e.g., 'data/') exists. Creates it if not."""
        if not os.path.exists(DATA_DIR):
            try:
                os.makedirs(DATA_DIR)
                print(f"Created directory: {DATA_DIR}")
            except OSError as e:
                print(f"Error creating directory {DATA_DIR}: {e}")
                return

    def _load_unlocks(self):
        """
        Loads drone unlock status and player progress from a JSON file.
        If the file doesn't exist or is corrupted, creates/returns default data.
        """
        default_data = {
            "unlocked_drones": ["ORIGINAL_DRONE"],
            "selected_drone": "ORIGINAL_DRONE",
            "player_level": 1,
            "bosses_defeated": [],
            "player_cores": 0,
            "collected_core_fragments": [] # Added for tracking secret blueprints
        }

        if not os.path.exists(UNLOCKS_FILE_PATH):
            print(f"'{UNLOCKS_FILE_PATH}' not found. Creating default unlock data.")
            self._save_unlocks(default_data) # Save the default data immediately
            return default_data

        try:
            with open(UNLOCKS_FILE_PATH, 'r') as f:
                data = json.load(f)
                # Merge loaded data with defaults to ensure all keys are present
                for key, value in default_data.items():
                    if key not in data:
                        data[key] = value
                
                # Sanity check: Ensure ORIGINAL_DRONE is always in unlocked_drones.
                if "ORIGINAL_DRONE" not in data.get("unlocked_drones", []):
                    data.setdefault("unlocked_drones", []).append("ORIGINAL_DRONE")
                
                # Sanity check: If selected_drone is not valid or not unlocked, reset.
                if data.get("selected_drone") not in data.get("unlocked_drones", []):
                    print(f"Warning: Previously selected drone '{data.get('selected_drone')}' is not valid/unlocked. Resetting to ORIGINAL_DRONE.")
                    data["selected_drone"] = "ORIGINAL_DRONE"

                # Validate collected_core_fragments (remove any invalid IDs if CORE_FRAGMENT_DETAILS changes)
                if "collected_core_fragments" in data:
                    valid_fragment_ids = [details["id"] for details in CORE_FRAGMENT_DETAILS.values()]
                    data["collected_core_fragments"] = [fid for fid in data["collected_core_fragments"] if fid in valid_fragment_ids]
                else: # Should be handled by the loop above, but as an explicit fallback
                    data["collected_core_fragments"] = []
                
                return data
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading or parsing '{UNLOCKS_FILE_PATH}': {e}. Returning default and attempting to re-save.")
            self._save_unlocks(default_data) 
            return default_data

    def _save_unlocks(self, data_to_save=None):
        """Saves the current unlock status (or provided data) to the JSON file."""
        self._ensure_data_dir_exists()
        current_data_to_save = data_to_save if data_to_save is not None else self.unlock_data
        try:
            with open(UNLOCKS_FILE_PATH, 'w') as f:
                json.dump(current_data_to_save, f, indent=2)
        except IOError as e:
            print(f"Error saving unlock data to '{UNLOCKS_FILE_PATH}': {e}")

    def get_selected_drone_id(self):
        """Returns the ID of the currently selected drone."""
        return self.unlock_data.get("selected_drone", "ORIGINAL_DRONE")

    def set_selected_drone_id(self, drone_id):
        """Sets the selected drone if it's valid and unlocked, then saves."""
        if drone_id in DRONE_DATA and drone_id in self.unlock_data.get("unlocked_drones", []):
            self.unlock_data["selected_drone"] = drone_id
            self._save_unlocks()
            print(f"Drone '{drone_id}' selected.")
            return True
        print(f"Failed to select drone '{drone_id}'. Not found in DRONE_DATA or not unlocked.")
        return False

    def get_drone_config(self, drone_id):
        """
        Returns the base configuration for a specific drone ID from DRONE_DATA.
        Returns ORIGINAL_DRONE's config as a fallback if the ID is not found.
        """
        config = DRONE_DATA.get(drone_id)
        if not config:
            print(f"Warning: Drone ID '{drone_id}' not found in DRONE_DATA. Returning ORIGINAL_DRONE config.")
            return DRONE_DATA.get("ORIGINAL_DRONE", {}) # Ensure ORIGINAL_DRONE exists
        return config

    def get_all_drone_ids_ordered(self):
        """Returns a list of all drone IDs in their intended display order."""
        from drone_configs import DRONE_DISPLAY_ORDER
        return DRONE_DISPLAY_ORDER

    def is_drone_unlocked(self, drone_id):
        """Checks if a specific drone ID is present in the list of unlocked drones."""
        return drone_id in self.unlock_data.get("unlocked_drones", [])

    def get_player_level(self):
        """Returns the player's current level."""
        return self.unlock_data.get("player_level", 1)

    def set_player_level(self, level):
        """
        Sets the player's level, checks for new drone unlocks, and saves if changes occurred.
        Returns a list of newly unlocked drone IDs.
        """
        self.unlock_data["player_level"] = level
        newly_unlocked = self.check_for_new_unlocks()
        if newly_unlocked:
            self._save_unlocks()
            print(f"Player level set to {level}. New unlocks: {newly_unlocked}")
        return newly_unlocked

    def get_player_cores(self):
        """Returns the player's current number of cores."""
        return self.unlock_data.get("player_cores", 0)

    def add_player_cores(self, amount):
        """Adds cores to the player's total. Does not save on its own."""
        self.unlock_data["player_cores"] = self.unlock_data.get("player_cores", 0) + amount

    def spend_player_cores(self, amount):
        """Spends player cores if available. Saves immediately if successful."""
        current_cores = self.get_player_cores()
        if current_cores >= amount:
            self.unlock_data["player_cores"] = current_cores - amount
            self._save_unlocks()
            return True
        return False

    def add_defeated_boss(self, boss_name):
        """Adds a defeated boss, checks for unlocks, and saves if new unlocks occurred."""
        if boss_name not in self.unlock_data.get("bosses_defeated", []):
            self.unlock_data.setdefault("bosses_defeated", []).append(boss_name)
            newly_unlocked = self.check_for_new_unlocks()
            if newly_unlocked:
                 self._save_unlocks()
                 print(f"Boss '{boss_name}' defeated. New unlocks: {newly_unlocked}")
            return newly_unlocked
        return []

    def check_for_new_unlocks(self):
        """
        Checks all drones if passive unlock conditions are met. Updates internal list.
        Does NOT save; caller should handle saving. Returns newly unlocked IDs.
        """
        newly_unlocked_in_this_check = []
        player_level = self.get_player_level()
        bosses_defeated = self.unlock_data.get("bosses_defeated", [])
        unlocked_drones_list = self.unlock_data.get("unlocked_drones", [])

        for drone_id, config in DRONE_DATA.items():
            if drone_id in unlocked_drones_list:
                continue

            condition = config.get("unlock_condition", {})
            can_be_unlocked_passively = False
            unlock_type = condition.get("type")
            unlock_value = condition.get("value")

            if unlock_type == "default":
                can_be_unlocked_passively = True
            elif unlock_type == "level" and player_level >= unlock_value:
                can_be_unlocked_passively = True
            elif unlock_type == "boss" and unlock_value in bosses_defeated:
                can_be_unlocked_passively = True

            if can_be_unlocked_passively:
                if drone_id not in unlocked_drones_list:
                    unlocked_drones_list.append(drone_id)
                    newly_unlocked_in_this_check.append(drone_id)
        
        # self.unlock_data["unlocked_drones"] is updated in memory here if new unlocks happened
        return newly_unlocked_in_this_check

    def attempt_unlock_drone_with_cores(self, drone_id):
        """Attempts to unlock a drone by spending cores. Returns True if successful."""
        if self.is_drone_unlocked(drone_id):
            return True

        config = self.get_drone_config(drone_id)
        unlock_condition = config.get("unlock_condition", {})

        if not config or unlock_condition.get("type") != "cores":
            return False

        cost = unlock_condition.get("value", float('inf'))
        if self.get_player_cores() >= cost:
            if self.spend_player_cores(cost): # This saves
                unlocked_list = self.unlock_data.setdefault("unlocked_drones", [])
                if drone_id not in unlocked_list:
                    unlocked_list.append(drone_id)
                self._save_unlocks() # Save again to ensure the new drone is in the list
                print(f"Drone '{drone_id}' unlocked by spending {cost} cores.")
                return True
            else:
                return False # Should not happen if checks passed
        else:
            return False

    def get_drone_stats(self, drone_id):
        """
        Returns the effective stats for a drone, applying special modifications.
        """
        config = self.get_drone_config(drone_id)
        true_base_stats_template = DRONE_DATA.get(drone_id, DRONE_DATA.get("ORIGINAL_DRONE", {}))
        true_base_stats = true_base_stats_template.get("base_stats", {}).copy()

        if drone_id == "OMEGA-9" and true_base_stats.get("special_ability") == "omega_boost":
            print(f"OMEGA-9 ({drone_id}): Applying random stat boosts for this run.")
            for stat_name, (min_mult, max_mult) in OMEGA_STAT_RANGES.items():
                if stat_name in true_base_stats:
                    original_value = true_base_stats[stat_name]
                    multiplier = random.uniform(min_mult, max_mult)
                    modified_value = original_value * multiplier
                    
                    if stat_name == "hp":
                        true_base_stats[stat_name] = int(modified_value)
                    else:
                        true_base_stats[stat_name] = modified_value
            return true_base_stats
            
        return true_base_stats

    # --- Methods for Core Fragments (Secret Blueprints) ---
    def collect_core_fragment(self, fragment_id_to_collect):
        """Adds a fragment_id to the list of collected fragments if not already present and saves."""
        # Validate fragment_id against CORE_FRAGMENT_DETAILS
        is_valid_fragment = any(details["id"] == fragment_id_to_collect for cfg_key, details in CORE_FRAGMENT_DETAILS.items())
        if not is_valid_fragment:
            print(f"Warning: Attempted to collect invalid fragment_id: {fragment_id_to_collect}")
            return False

        collected_list = self.unlock_data.setdefault("collected_core_fragments", [])
        if fragment_id_to_collect not in collected_list:
            collected_list.append(fragment_id_to_collect)
            self._save_unlocks()
            print(f"Core Fragment '{fragment_id_to_collect}' collected. Total: {len(collected_list)}/{TOTAL_CORE_FRAGMENTS_NEEDED}")
            return True
        # print(f"Core Fragment '{fragment_id_to_collect}' was already collected.")
        return False # Already collected or invalid

    def has_collected_fragment(self, fragment_id_to_check):
        """Checks if a specific core fragment has been collected."""
        return fragment_id_to_check in self.unlock_data.get("collected_core_fragments", [])

    def get_collected_fragments_ids(self):
        """Returns a list of collected core fragment IDs."""
        return self.unlock_data.get("collected_core_fragments", [])[:] # Return a copy

    def are_all_core_fragments_collected(self):
        """Checks if the number of collected fragments meets the required total."""
        # TOTAL_CORE_FRAGMENTS_NEEDED should be available from game_settings import
        num_collected = len(self.unlock_data.get("collected_core_fragments", []))
        # print(f"DEBUG: Checking all fragments collected. Have: {num_collected}, Need: {TOTAL_CORE_FRAGMENTS_NEEDED}")
        return num_collected >= TOTAL_CORE_FRAGMENTS_NEEDED

    def reset_collected_fragments(self): # Optional: for testing or game reset logic
        """Resets the list of collected fragments and saves."""
        if "collected_core_fragments" in self.unlock_data:
            self.unlock_data["collected_core_fragments"] = []
            self._save_unlocks()
            print("Collected core fragments have been reset.")
        else: # Should not happen if _load_unlocks is correct
             self.unlock_data["collected_core_fragments"] = [] # Ensure key exists
             self._save_unlocks()
             print("Collected core fragments initialized and reset (was missing).")


if __name__ == '__main__':
    # Example Usage / Testing
    print("Testing DroneSystem...")
    ds = DroneSystem()
    print(f"Initial selected drone: {ds.get_selected_drone_id()}")
    print(f"Is VANTIS unlocked? {ds.is_drone_unlocked('VANTIS')}")
    print(f"Player level: {ds.get_player_level()}")
    print(f"Player cores: {ds.get_player_cores()}")
    
    # Test fragment collection
    print(f"Initial collected fragments: {ds.get_collected_fragments_ids()}")
    ds.reset_collected_fragments() # Start fresh for test
    print(f"Fragments after reset: {ds.get_collected_fragments_ids()}")

    if CORE_FRAGMENT_DETAILS:
        first_frag_key = list(CORE_FRAGMENT_DETAILS.keys())[0]
        first_frag_id = CORE_FRAGMENT_DETAILS[first_frag_key]["id"]
        
        print(f"Attempting to collect '{first_frag_id}'...")
        ds.collect_core_fragment(first_frag_id)
        print(f"Has collected '{first_frag_id}'? {ds.has_collected_fragment(first_frag_id)}")
        print(f"All collected? {ds.are_all_core_fragments_collected()} (Need {TOTAL_CORE_FRAGMENTS_NEEDED})")

        if len(CORE_FRAGMENT_DETAILS) > 1 and TOTAL_CORE_FRAGMENTS_NEEDED > 1:
            second_frag_key = list(CORE_FRAGMENT_DETAILS.keys())[1]
            second_frag_id = CORE_FRAGMENT_DETAILS[second_frag_key]["id"]
            ds.collect_core_fragment(second_frag_id)
            print(f"Collected fragments: {ds.get_collected_fragments_ids()}")
            print(f"All collected? {ds.are_all_core_fragments_collected()} (Need {TOTAL_CORE_FRAGMENTS_NEEDED})")

        if len(CORE_FRAGMENT_DETAILS) > 2 and TOTAL_CORE_FRAGMENTS_NEEDED > 2:
            third_frag_key = list(CORE_FRAGMENT_DETAILS.keys())[2]
            third_frag_id = CORE_FRAGMENT_DETAILS[third_frag_key]["id"]
            ds.collect_core_fragment(third_frag_id)
            print(f"Collected fragments: {ds.get_collected_fragments_ids()}")
            print(f"All collected? {ds.are_all_core_fragments_collected()} (Need {TOTAL_CORE_FRAGMENTS_NEEDED})")

    # Example of setting selected drone (assuming VANTIS can be unlocked for testing)
    # ds.set_player_level(5) # Assuming VANTIS unlocks at level <= 5 based on drone_configs
    # ds.set_selected_drone_id("VANTIS")
    # print(f"New selected drone: {ds.get_selected_drone_id()}")