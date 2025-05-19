import json
import os
import random

from drone_configs import DRONE_DATA, OMEGA_STAT_RANGES # For drone stats and Omega-9 randomization
# game_settings is not directly imported here, but its values are used by drone_configs
# and potentially by the player class which interacts with drone_system.

DATA_DIR = "data" # Directory to store save files
UNLOCKS_FILE_PATH = os.path.join(DATA_DIR, "drone_unlocks.json") # Path to the drone unlocks save file

class DroneSystem:
    """
    Manages drone configurations, unlock status, player progress related to drones,
    and persistence of this data.
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
                # Depending on the game's needs, this could raise an error or try a fallback.
                return

    def _load_unlocks(self):
        """
        Loads drone unlock status and player progress (level, cores, defeated bosses) from a JSON file.
        If the file doesn't exist or is corrupted, creates/returns default data and attempts to save it.
        """
        # Define the absolute default structure for unlock data.
        default_data = {
            "unlocked_drones": ["ORIGINAL_DRONE"], # ORIGINAL_DRONE is always unlocked by default.
            "selected_drone": "ORIGINAL_DRONE",   # Default selected drone.
            "player_level": 1,                    # For tracking level-based unlocks.
            "bosses_defeated": [],                # For tracking boss-based unlocks.
            "player_cores": 0                     # For tracking core-based unlocks or purchases.
        }

        if not os.path.exists(UNLOCKS_FILE_PATH):
            print(f"'{UNLOCKS_FILE_PATH}' not found. Creating default unlock data.")
            self._save_unlocks(default_data) # Save the default data immediately if file is new.
            return default_data

        try:
            with open(UNLOCKS_FILE_PATH, 'r') as f:
                data = json.load(f)
                # Merge loaded data with defaults to ensure all keys are present,
                # especially if new keys were added to default_data in a game update.
                for key, value in default_data.items():
                    if key not in data:
                        data[key] = value
                
                # Sanity check: Ensure ORIGINAL_DRONE is always in unlocked_drones.
                if "ORIGINAL_DRONE" not in data.get("unlocked_drones", []):
                    data.setdefault("unlocked_drones", []).append("ORIGINAL_DRONE")
                
                # Sanity check: If selected_drone is not valid or not unlocked, reset to ORIGINAL_DRONE.
                if data.get("selected_drone") not in data.get("unlocked_drones", []):
                    print(f"Warning: Previously selected drone '{data.get('selected_drone')}' is not valid/unlocked. Resetting to ORIGINAL_DRONE.")
                    data["selected_drone"] = "ORIGINAL_DRONE"
                return data
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading or parsing '{UNLOCKS_FILE_PATH}': {e}. Returning default and attempting to re-save.")
            # If loading fails, it's critical to save a clean default to prevent ongoing errors.
            self._save_unlocks(default_data) 
            return default_data

    def _save_unlocks(self, data_to_save=None):
        """Saves the current unlock status (or provided data) to the JSON file."""
        self._ensure_data_dir_exists() # Should not be strictly necessary if init calls it, but good for safety.
        current_data_to_save = data_to_save if data_to_save is not None else self.unlock_data
        try:
            with open(UNLOCKS_FILE_PATH, 'w') as f:
                json.dump(current_data_to_save, f, indent=2) # Using indent=2 for readability.
        except IOError as e:
            print(f"Error saving unlock data to '{UNLOCKS_FILE_PATH}': {e}")

    def get_selected_drone_id(self):
        """Returns the ID of the currently selected drone."""
        # _load_unlocks should have corrected any invalid selection, so this should be safe.
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
            return DRONE_DATA["ORIGINAL_DRONE"] 
        return config

    def get_all_drone_ids_ordered(self):
        """Returns a list of all drone IDs in their intended display order (from drone_configs)."""
        from drone_configs import DRONE_DISPLAY_ORDER # Import here to avoid circular dependency issues at module load.
        return DRONE_DISPLAY_ORDER

    def is_drone_unlocked(self, drone_id):
        """Checks if a specific drone ID is present in the list of unlocked drones."""
        return drone_id in self.unlock_data.get("unlocked_drones", [])

    def get_player_level(self):
        """Returns the player's current level."""
        return self.unlock_data.get("player_level", 1)

    def set_player_level(self, level):
        """
        Sets the player's level, checks for new drone unlocks based on this level,
        and saves if any new unlocks occurred.
        Returns a list of newly unlocked drone IDs from this level change.
        """
        self.unlock_data["player_level"] = level
        newly_unlocked = self.check_for_new_unlocks() # This checks all passive conditions.
        if newly_unlocked: # Only save if there were actual changes to unlock status.
            self._save_unlocks()
            print(f"Player level set to {level}. New unlocks: {newly_unlocked}")
        # else:
            # print(f"Player level set to {level}. No new unlocks from this change.")
        return newly_unlocked

    def get_player_cores(self):
        """Returns the player's current number of cores."""
        return self.unlock_data.get("player_cores", 0)

    def add_player_cores(self, amount):
        """
        Adds a specified amount of cores to the player's total.
        Note: This method itself does not trigger saving. Saving usually happens
        after a game event (like level end) or if an unlock occurs due to spending cores.
        """
        self.unlock_data["player_cores"] = self.unlock_data.get("player_cores", 0) + amount
        # Passive unlocks via gaining cores are not typical; usually, cores are spent.
        # If you had passive core unlocks, you'd call check_for_new_unlocks() and potentially save.

    def spend_player_cores(self, amount):
        """
        Spends player cores if available. Saves immediately if successful.
        Returns True if cores were spent, False otherwise.
        """
        current_cores = self.get_player_cores()
        if current_cores >= amount:
            self.unlock_data["player_cores"] = current_cores - amount
            self._save_unlocks() # Save immediately after spending cores.
            return True
        return False

    def add_defeated_boss(self, boss_name):
        """
        Adds a defeated boss to the player's record, checks for new drone unlocks
        based on this, and saves if any new unlocks occurred.
        Returns a list of newly unlocked drone IDs from this boss defeat.
        """
        if boss_name not in self.unlock_data.get("bosses_defeated", []):
            self.unlock_data.setdefault("bosses_defeated", []).append(boss_name)
            newly_unlocked = self.check_for_new_unlocks() # Check all passive conditions.
            if newly_unlocked: 
                 self._save_unlocks() # Save if new drones were unlocked.
                 print(f"Boss '{boss_name}' defeated. New unlocks: {newly_unlocked}")
            # else:
                # print(f"Boss '{boss_name}' defeated. No new unlocks from this.")
            return newly_unlocked
        return [] # Return empty list if boss was already defeated (no new unlocks from this event).

    def check_for_new_unlocks(self):
        """
        Checks all drones if their passive unlock conditions (level, boss defeat) are met.
        Updates the internal 'unlocked_drones' list in self.unlock_data if new drones are unlocked.
        Returns a list of drone IDs that were newly unlocked during this check.
        IMPORTANT: This method DOES NOT save the unlock_data itself. The caller should handle saving.
        """
        newly_unlocked_in_this_check = []
        player_level = self.get_player_level()
        bosses_defeated = self.unlock_data.get("bosses_defeated", [])
        unlocked_drones_list = self.unlock_data.get("unlocked_drones", []) # Get current list.

        for drone_id, config in DRONE_DATA.items():
            if drone_id in unlocked_drones_list: # Already unlocked, skip.
                continue 

            condition = config.get("unlock_condition", {})
            can_be_unlocked_passively = False
            unlock_type = condition.get("type")
            unlock_value = condition.get("value")

            if unlock_type == "default": # Should be in initial list, but good for robustness.
                can_be_unlocked_passively = True
            elif unlock_type == "level" and player_level >= unlock_value:
                can_be_unlocked_passively = True
            elif unlock_type == "boss" and unlock_value in bosses_defeated:
                can_be_unlocked_passively = True
            # "cores" type unlocks are active (player initiated), not passive.

            if can_be_unlocked_passively:
                # This check is slightly redundant if the outer loop skips already unlocked,
                # but ensures no duplicates if logic changes.
                if drone_id not in unlocked_drones_list: 
                    unlocked_drones_list.append(drone_id) # Modify the list directly in self.unlock_data.
                    newly_unlocked_in_this_check.append(drone_id)
        
        if newly_unlocked_in_this_check:
            # The self.unlock_data["unlocked_drones"] is now updated in memory.
            # print(f"Passive new unlocks detected (in memory): {newly_unlocked_in_this_check}")
            pass # Caller (e.g., set_player_level, add_defeated_boss) is responsible for calling _save_unlocks.
        return newly_unlocked_in_this_check

    def attempt_unlock_drone_with_cores(self, drone_id):
        """
        Attempts to unlock a drone by spending cores.
        Returns True if successful (unlocks and saves), False otherwise.
        """
        if self.is_drone_unlocked(drone_id): # Already unlocked.
            return True 

        config = self.get_drone_config(drone_id) # Gets config, or ORIGINAL_DRONE's if ID is bad.
        unlock_condition = config.get("unlock_condition", {})

        if not config or unlock_condition.get("type") != "cores":
            # print(f"Drone '{drone_id}' is not unlockable with cores or is an invalid ID.")
            return False # Not a core-unlockable drone or invalid ID.

        cost = unlock_condition.get("value", float('inf')) # Get cost, default to infinity if not specified.
        if self.get_player_cores() >= cost:
            if self.spend_player_cores(cost): # spend_player_cores now saves if successful.
                # Ensure "unlocked_drones" list exists, then append.
                if "unlocked_drones" not in self.unlock_data: # Should not happen if _load_unlocks is robust.
                    self.unlock_data["unlocked_drones"] = ["ORIGINAL_DRONE"] # Initialize if somehow missing.
                
                if drone_id not in self.unlock_data["unlocked_drones"]:
                    self.unlock_data["unlocked_drones"].append(drone_id)
                
                # _save_unlocks() was called by spend_player_cores, but call again to ensure
                # the addition to unlocked_drones list is also saved.
                self._save_unlocks()
                print(f"Drone '{drone_id}' unlocked by spending {cost} cores.")
                return True
            else: # Should not happen if get_player_cores was accurate and spend_player_cores worked.
                print(f"Error spending cores for '{drone_id}'. This should not occur if checks passed.")
                return False
        else:
            # print(f"Not enough cores to unlock '{drone_id}'. Need {cost}, have {self.get_player_cores()}.")
            return False

    def get_drone_stats(self, drone_id):
        """
        Returns the effective stats for a drone, applying any special modifications
        like Omega-9's randomization.
        """
        config = self.get_drone_config(drone_id) # This now defaults to ORIGINAL_DRONE config if ID is bad.
        
        # Start with a fresh copy of the *base* stats for the specific drone ID from DRONE_DATA.
        # This is crucial for Omega-9 to ensure its randomization applies to its own true base stats.
        # If drone_id is invalid, config will be for ORIGINAL_DRONE, so true_base_stats will be correct.
        true_base_stats_template = DRONE_DATA.get(drone_id, DRONE_DATA["ORIGINAL_DRONE"])
        true_base_stats = true_base_stats_template.get("base_stats", {}).copy() # Ensure "base_stats" key exists
        
        # If the drone is Omega-9 and has the omega_boost special ability, apply randomization.
        if drone_id == "OMEGA-9" and config.get("base_stats", {}).get("special_ability") == "omega_boost":
            print(f"OMEGA-9 ({drone_id}): Applying random stat boosts for this run.")
            # Iterate over the stats defined in OMEGA_STAT_RANGES (from drone_configs.py).
            for stat_name, (min_mult, max_mult) in OMEGA_STAT_RANGES.items():
                if stat_name in true_base_stats: # Check if the stat exists in the drone's base stats.
                    original_value = true_base_stats[stat_name] # The actual base value for this stat.
                    multiplier = random.uniform(min_mult, max_mult)
                    modified_value = original_value * multiplier
                    
                    # Ensure HP is an integer after modification.
                    if stat_name == "hp":
                        true_base_stats[stat_name] = int(modified_value)
                    else: # Other stats like speed, fire_rate_multiplier can be float.
                        true_base_stats[stat_name] = modified_value 
                    
                    # print(f"  OMEGA-9 {stat_name}: {original_value:.2f} -> {true_base_stats[stat_name]:.2f} (x{multiplier:.2f})")
            return true_base_stats # Return the modified stats for Omega-9.
            
        return true_base_stats # Return the (unmodified) base stats for other drones.

