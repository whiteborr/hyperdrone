import json
import os
import random

from drone_configs import DRONE_DATA, OMEGA_STAT_RANGES
# Import new settings from game_settings for validation and use
from game_settings import (
    CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED,
    ARCHITECT_REWARD_BLUEPRINT_ID, ARCHITECT_REWARD_LORE_ID # New reward IDs
)

DATA_DIR = "data" # Directory to store save files
UNLOCKS_FILE_PATH = os.path.join(DATA_DIR, "drone_unlocks.json") # Path to the drone unlocks save file

class DroneSystem:
    """
    Manages drone configurations, unlock status, player progress related to drones,
    and persistence of this data, including collected core fragments and Architect's Vault rewards.
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
            "collected_core_fragments": [],
            "architect_vault_completed": False, # New: Track if Architect's Vault has been cleared
            "unlocked_blueprints": [], # New: Track special blueprints like Architect's reward
            "unlocked_lore_codex_entries": [] # New: Track unlocked lore
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

                # Validate collected_core_fragments
                if "collected_core_fragments" in data and CORE_FRAGMENT_DETAILS:
                    valid_fragment_ids = [details["id"] for cfg_key, details in CORE_FRAGMENT_DETAILS.items() if details] # Check if details is not None
                    data["collected_core_fragments"] = [fid for fid in data["collected_core_fragments"] if fid in valid_fragment_ids]
                else:
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
        from drone_configs import DRONE_DISPLAY_ORDER # Local import to avoid circular dependency issues at module load time
        return DRONE_DISPLAY_ORDER

    def is_drone_unlocked(self, drone_id):
        """Checks if a specific drone ID is present in the list of unlocked drones."""
        # Also consider blueprints as unlocking drones
        if drone_id in self.unlock_data.get("unlocked_drones", []):
            return True
        if drone_id in self.unlock_data.get("unlocked_blueprints", []): # Check if it's an unlocked blueprint
             # If a blueprint ID matches a drone ID in DRONE_DATA, it implies the drone is unlocked
            if drone_id in DRONE_DATA:
                return True
        return False

    def get_player_level(self):
        """Returns the player's current level."""
        return self.unlock_data.get("player_level", 1)

    def set_player_level(self, level):
        """
        Sets the player's level, checks for new drone unlocks, and saves if changes occurred.
        Returns a list of newly unlocked drone IDs.
        """
        self.unlock_data["player_level"] = level
        newly_unlocked = self.check_for_new_unlocks() # This will save if new unlocks occur
        # No need for explicit save here as check_for_new_unlocks handles it if it finds something
        if newly_unlocked:
             print(f"Player level set to {level}. New unlocks: {newly_unlocked}")
        else: # Save if level changed but no new unlocks (e.g., player leveled down or re-set to same level)
            self._save_unlocks()
        return newly_unlocked


    def get_player_cores(self):
        """Returns the player's current number of cores."""
        return self.unlock_data.get("player_cores", 0)

    def add_player_cores(self, amount):
        """Adds cores to the player's total. Does not save on its own; caller should save."""
        self.unlock_data["player_cores"] = self.unlock_data.get("player_cores", 0) + amount
        # Caller (e.g., Game class) should call _save_unlocks() after a series of changes or at game events.

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
            newly_unlocked = self.check_for_new_unlocks() # This will save if new unlocks occur
            if newly_unlocked:
                 print(f"Boss '{boss_name}' defeated. New unlocks: {newly_unlocked}")
            else: # Save if boss was added but no new drone unlocks happened
                self._save_unlocks()
            return newly_unlocked
        return []

    def check_for_new_unlocks(self):
        """
        Checks all drones if passive unlock conditions are met. Updates internal list.
        Saves if any new drone is unlocked. Returns newly unlocked drone IDs.
        """
        newly_unlocked_in_this_check = []
        player_level = self.get_player_level()
        bosses_defeated = self.unlock_data.get("bosses_defeated", [])
        unlocked_drones_list = self.unlock_data.get("unlocked_drones", [])

        for drone_id, config in DRONE_DATA.items():
            if drone_id in unlocked_drones_list:
                continue # Already unlocked

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
            # Blueprints are handled separately by `unlock_blueprint`

            if can_be_unlocked_passively:
                if drone_id not in unlocked_drones_list:
                    unlocked_drones_list.append(drone_id)
                    newly_unlocked_in_this_check.append(drone_id)
        
        if newly_unlocked_in_this_check:
            self.unlock_data["unlocked_drones"] = unlocked_drones_list # Update the main list
            self._save_unlocks() # Save if new drones were unlocked
            print(f"Passive check unlocked: {newly_unlocked_in_this_check}")
        return newly_unlocked_in_this_check

    def attempt_unlock_drone_with_cores(self, drone_id):
        """Attempts to unlock a drone by spending cores. Returns True if successful."""
        if self.is_drone_unlocked(drone_id): # is_drone_unlocked now checks blueprints too
            return True

        config = self.get_drone_config(drone_id)
        unlock_condition = config.get("unlock_condition", {})

        if not config or unlock_condition.get("type") != "cores":
            return False

        cost = unlock_condition.get("value", float('inf'))
        if self.get_player_cores() >= cost:
            if self.spend_player_cores(cost): # This saves player_cores
                unlocked_list = self.unlock_data.setdefault("unlocked_drones", [])
                if drone_id not in unlocked_list:
                    unlocked_list.append(drone_id)
                self._save_unlocks() # Save again to ensure the new drone is in the unlocked_drones list
                print(f"Drone '{drone_id}' unlocked by spending {cost} cores.")
                return True
            else: # Should not happen if checks passed
                print(f"Core spending failed for {drone_id} despite sufficient cores (unexpected).")
                return False
        else:
            # print(f"Not enough cores to unlock {drone_id}. Need: {cost}, Have: {self.get_player_cores()}")
            return False

    def get_drone_stats(self, drone_id, is_in_architect_vault=False):
        """
        Returns the effective stats for a drone, applying special modifications
        like Omega-9's randomization and buffs from collected Core Fragments if in the Vault.
        """
        config = self.get_drone_config(drone_id) # Base config from DRONE_DATA
        # Start with a copy of the base stats defined in DRONE_DATA
        # Ensure "base_stats" key exists and is a dict
        true_base_stats_template = DRONE_DATA.get(drone_id, DRONE_DATA.get("ORIGINAL_DRONE", {}))
        effective_stats = true_base_stats_template.get("base_stats", {}).copy()
        if not effective_stats: # If base_stats was missing or empty
            print(f"Warning: No base_stats found for drone '{drone_id}'. Using empty stats.")
            effective_stats = {"hp": 100, "speed": 3, "turn_speed": 5, "fire_rate_multiplier": 1.0}


        # Apply Omega-9 specific randomization
        if drone_id == "OMEGA-9" and effective_stats.get("special_ability") == "omega_boost":
            # print(f"OMEGA-9 ({drone_id}): Applying random stat boosts for this run.")
            for stat_name, (min_mult, max_mult) in OMEGA_STAT_RANGES.items():
                if stat_name in effective_stats:
                    original_value = effective_stats[stat_name]
                    multiplier = random.uniform(min_mult, max_mult)
                    modified_value = original_value * multiplier
                    
                    if stat_name == "hp": # HP should be integer
                        effective_stats[stat_name] = int(modified_value)
                    else: # Other stats can be float
                        effective_stats[stat_name] = modified_value
        
        # If in Architect's Vault, apply buffs from collected fragments
        if is_in_architect_vault:
            collected_fragment_ids = self.get_collected_fragments_ids()
            for frag_id in collected_fragment_ids:
                # Find the fragment's details in CORE_FRAGMENT_DETAILS
                fragment_config = None
                for key, details_dict in CORE_FRAGMENT_DETAILS.items():
                    if details_dict and details_dict.get("id") == frag_id: # Check details_dict is not None
                        fragment_config = details_dict
                        break
                
                if fragment_config and "buff" in fragment_config:
                    buff = fragment_config["buff"]
                    buff_type = buff.get("type")
                    buff_value = buff.get("value")

                    if buff_type == "speed" and "speed" in effective_stats:
                        effective_stats["speed"] *= buff_value
                        # print(f"Applied {frag_id} speed buff: new speed {effective_stats['speed']:.2f}")
                    elif buff_type == "damage" and "bullet_damage_multiplier" in effective_stats: # Assuming a general damage multiplier stat
                        effective_stats["bullet_damage_multiplier"] = effective_stats.get("bullet_damage_multiplier", 1.0) * buff_value
                    elif buff_type == "damage" and "fire_rate_multiplier" in effective_stats: # If damage buff affects fire rate instead
                         # Example: A "damage" buff might actually be implemented as faster firing for some fragments
                         # This is a placeholder; actual damage stat needs to be consistently used by Bullet class
                         pass # Placeholder for actual damage stat modification
                    # Add more buff types as needed (e.g., shield strength, fire rate directly)
                
                # Check for alternative buff structure (e.g., "buff_alt")
                if fragment_config and "buff_alt" in fragment_config:
                    buff_alt = fragment_config["buff_alt"]
                    buff_alt_type = buff_alt.get("type")
                    buff_alt_value = buff_alt.get("value")
                    if buff_alt_type == "damage_reduction" and "damage_taken_multiplier" in effective_stats:
                        effective_stats["damage_taken_multiplier"] = effective_stats.get("damage_taken_multiplier", 1.0) * (1.0 - buff_alt_value)
                        # print(f"Applied {frag_id} damage reduction: new multiplier {effective_stats['damage_taken_multiplier']:.2f}")


        return effective_stats


    # --- Methods for Core Fragments ---
    def collect_core_fragment(self, fragment_id_to_collect):
        """Adds a fragment_id to the list of collected fragments if not already present and saves."""
        if not CORE_FRAGMENT_DETAILS: # Check if CORE_FRAGMENT_DETAILS is available
            print("Warning: CORE_FRAGMENT_DETAILS not loaded. Cannot validate or collect fragment.")
            return False

        is_valid_fragment = any(details["id"] == fragment_id_to_collect for cfg_key, details in CORE_FRAGMENT_DETAILS.items() if details)
        if not is_valid_fragment:
            print(f"Warning: Attempted to collect invalid fragment_id: {fragment_id_to_collect}")
            return False

        collected_list = self.unlock_data.setdefault("collected_core_fragments", [])
        if fragment_id_to_collect not in collected_list:
            collected_list.append(fragment_id_to_collect)
            self._save_unlocks()
            print(f"Core Fragment '{fragment_id_to_collect}' collected. Total: {len(collected_list)}/{TOTAL_CORE_FRAGMENTS_NEEDED}")
            return True
        return False

    def has_collected_fragment(self, fragment_id_to_check):
        """Checks if a specific core fragment has been collected."""
        return fragment_id_to_check in self.unlock_data.get("collected_core_fragments", [])

    def get_collected_fragments_ids(self):
        """Returns a list of collected core fragment IDs."""
        return self.unlock_data.get("collected_core_fragments", [])[:]

    def are_all_core_fragments_collected(self):
        """Checks if the number of collected fragments meets the required total."""
        num_collected = len(self.unlock_data.get("collected_core_fragments", []))
        return num_collected >= TOTAL_CORE_FRAGMENTS_NEEDED

    def reset_collected_fragments(self):
        """Resets the list of collected fragments and saves."""
        if "collected_core_fragments" in self.unlock_data:
            self.unlock_data["collected_core_fragments"] = []
            self._save_unlocks()
            print("Collected core fragments have been reset.")

    # --- Methods for Architect's Vault Completion & Rewards ---
    def mark_architect_vault_completed(self, completed_successfully=True):
        """Marks the Architect's Vault as completed and saves."""
        self.unlock_data["architect_vault_completed"] = completed_successfully
        if completed_successfully:
            print("Architect's Vault completed successfully!")
            # Potentially unlock blueprint/lore here or let Game class handle it
            self.unlock_blueprint(ARCHITECT_REWARD_BLUEPRINT_ID) # Example
            self.unlock_lore_entry(ARCHITECT_REWARD_LORE_ID)   # Example
        else:
            print("Architect's Vault attempt failed.")
        self._save_unlocks()

    def has_completed_architect_vault(self):
        """Checks if the Architect's Vault has been successfully completed."""
        return self.unlock_data.get("architect_vault_completed", False)

    def unlock_blueprint(self, blueprint_id):
        """Adds a blueprint ID to the player's unlocked list if not already present and saves."""
        if not blueprint_id: return False
        unlocked_blueprints_list = self.unlock_data.setdefault("unlocked_blueprints", [])
        if blueprint_id not in unlocked_blueprints_list:
            unlocked_blueprints_list.append(blueprint_id)
            # If the blueprint ID also corresponds to a drone ID in DRONE_DATA, unlock it directly
            if blueprint_id in DRONE_DATA:
                unlocked_drones_list = self.unlock_data.setdefault("unlocked_drones", [])
                if blueprint_id not in unlocked_drones_list:
                    unlocked_drones_list.append(blueprint_id)
                    print(f"Drone '{blueprint_id}' unlocked via blueprint.")
            self._save_unlocks()
            print(f"Blueprint '{blueprint_id}' unlocked!")
            return True
        return False # Already unlocked

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
            print(f"Lore Codex Entry '{lore_id}' unlocked!")
            return True
        return False

    def has_unlocked_lore(self, lore_id):
        """Checks if a specific lore entry has been unlocked."""
        return lore_id in self.unlock_data.get("unlocked_lore_codex_entries", [])

    def reset_architect_vault_progress(self): # For testing or full game reset
        """Resets Architect's Vault completion status and related rewards."""
        self.unlock_data["architect_vault_completed"] = False
        # Decide if blueprints/lore from vault should also be reset
        # For now, let's assume they are persistent once earned, unless a full reset is intended.
        # If ARCHITECT_REWARD_BLUEPRINT_ID was added to "unlocked_blueprints", it would need removal here for a full reset.
        # e.g., if ARCHITECT_REWARD_BLUEPRINT_ID in self.unlock_data.get("unlocked_blueprints", []):
        #          self.unlock_data["unlocked_blueprints"].remove(ARCHITECT_REWARD_BLUEPRINT_ID)
        self._save_unlocks()
        print("Architect's Vault progress has been reset.")


if __name__ == '__main__':
    # Example Usage / Testing
    print("Testing DroneSystem...")
    ds = DroneSystem()
    print(f"Initial selected drone: {ds.get_selected_drone_id()}")
    print(f"Is VANTIS unlocked? {ds.is_drone_unlocked('VANTIS')}")
    print(f"Player level: {ds.get_player_level()}")
    print(f"Player cores: {ds.get_player_cores()}")
    
    print(f"Initial collected fragments: {ds.get_collected_fragments_ids()}")
    print(f"Architect Vault completed? {ds.has_completed_architect_vault()}")
    print(f"Unlocked blueprints: {ds.unlock_data.get('unlocked_blueprints')}")
    print(f"Unlocked lore: {ds.unlock_data.get('unlocked_lore_codex_entries')}")

    # Test fragment collection
    # ds.reset_collected_fragments()
    # ds.reset_architect_vault_progress()

    if CORE_FRAGMENT_DETAILS:
        frag_ids_to_collect = [details["id"] for _, details in CORE_FRAGMENT_DETAILS.items() if details]
        for fid in frag_ids_to_collect:
            ds.collect_core_fragment(fid)
        
        print(f"Collected fragments after loop: {ds.get_collected_fragments_ids()}")
        print(f"All fragments collected? {ds.are_all_core_fragments_collected()} (Need {TOTAL_CORE_FRAGMENTS_NEEDED})")

        if ds.are_all_core_fragments_collected():
            print("Simulating Architect's Vault completion...")
            ds.mark_architect_vault_completed(True) # This will also try to unlock default blueprint/lore
            print(f"Architect Vault completed status: {ds.has_completed_architect_vault()}")
            print(f"Unlocked blueprints after vault: {ds.unlock_data.get('unlocked_blueprints')}")
            print(f"Has ARCHITECT_X blueprint? {ds.has_unlocked_blueprint(ARCHITECT_REWARD_BLUEPRINT_ID)}")
            print(f"Is DRONE_ARCHITECT_X unlocked (as a drone)? {ds.is_drone_unlocked(ARCHITECT_REWARD_BLUEPRINT_ID)}")

    # Test Omega-9 stats
    # print("\nTesting Omega-9 stats (randomized):")
    # for _ in range(3): # Print a few random sets
    #     omega_stats = ds.get_drone_stats("OMEGA-9")
    #     print(omega_stats)

    # Test fragment buffs in vault (requires drone_id and is_in_architect_vault=True)
    # print("\nTesting stats with fragment buffs (in vault):")
    # original_drone_stats_in_vault = ds.get_drone_stats("ORIGINAL_DRONE", is_in_architect_vault=True)
    # print(f"ORIGINAL_DRONE stats in vault: {original_drone_stats_in_vault}")

    # Example of setting selected drone (assuming VANTIS can be unlocked for testing)
    # ds.set_player_level(5) 
    # ds.set_selected_drone_id("VANTIS")
    # print(f"New selected drone: {ds.get_selected_drone_id()}")