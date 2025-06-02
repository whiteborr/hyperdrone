# drone_management/drone_system.py

import json
import os
import random

from .drone_configs import DRONE_DATA, DRONE_DISPLAY_ORDER, OMEGA_STAT_RANGES
import game_settings as gs
from game_settings import (
    CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED,
    ARCHITECT_REWARD_BLUEPRINT_ID, ARCHITECT_REWARD_LORE_ID
)

DATA_DIR = "data"
UNLOCKS_FILE_PATH = os.path.join(DATA_DIR, "drone_unlocks.json")
LORE_FILE_PATH = os.path.join(DATA_DIR, "lore_entries.json")

class DroneSystem:
    def __init__(self):
        self._ensure_data_dir_exists()
        self.unlock_data = self._load_unlocks()
        self.all_lore_entries = self._load_all_lore_entries()

    def _ensure_data_dir_exists(self):
        if not os.path.exists(DATA_DIR):
            try:
                os.makedirs(DATA_DIR)
                print(f"DroneSystem: Created directory: {DATA_DIR}")
            except OSError as e:
                print(f"DroneSystem: Error creating directory {DATA_DIR}: {e}")

    def _load_unlocks(self):
        default_data = {
            "unlocked_drones": ["DRONE"],
            "selected_drone": "DRONE",
            "player_level": 1,
            "bosses_defeated": [],
            "player_cores": 0,
            "collected_core_fragments": [],
            "architect_vault_completed": False,
            "unlocked_blueprints": [],
            "unlocked_lore_codex_entries": [],
            "collected_glyph_tablet_ids": [],
            "solved_puzzle_terminals": [] # New: For tracking solved puzzle terminals
        }

        if not os.path.exists(UNLOCKS_FILE_PATH):
            print(f"DroneSystem: '{UNLOCKS_FILE_PATH}' not found. Creating default unlock data.")
            self._save_unlocks(default_data)
            return default_data

        try:
            with open(UNLOCKS_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, value in default_data.items():
                    data.setdefault(key, value) # Ensure all default keys are present

                if "DRONE" not in data.get("unlocked_drones", []):
                    data.setdefault("unlocked_drones", []).append("DRONE")

                if data.get("selected_drone") not in data.get("unlocked_drones", []) or \
                   data.get("selected_drone") not in DRONE_DATA:
                    print(f"DroneSystem: Warning - Previously selected drone '{data.get('selected_drone')}' is not valid/unlocked. Resetting to DRONE.")
                    data["selected_drone"] = "DRONE"

                if "collected_core_fragments" in data and CORE_FRAGMENT_DETAILS:
                    valid_fragment_ids = [details["id"] for _, details in CORE_FRAGMENT_DETAILS.items() if details and "id" in details]
                    data["collected_core_fragments"] = [fid for fid in data["collected_core_fragments"] if fid in valid_fragment_ids]
                else:
                    data["collected_core_fragments"] = []
                
                if not isinstance(data.get("unlocked_lore_codex_entries"), list):
                    data["unlocked_lore_codex_entries"] = []
                
                if not isinstance(data.get("collected_glyph_tablet_ids"), list):
                    data["collected_glyph_tablet_ids"] = []
                
                if not isinstance(data.get("solved_puzzle_terminals"), list): # Ensure new key is a list
                    data["solved_puzzle_terminals"] = []
                    
                return data
        except (IOError, json.JSONDecodeError) as e:
            print(f"DroneSystem: Error loading or parsing '{UNLOCKS_FILE_PATH}': {e}. Returning default and attempting to re-save.")
            self._save_unlocks(default_data)
            return default_data

    def _load_all_lore_entries(self):
        if not os.path.exists(LORE_FILE_PATH):
            print(f"DroneSystem: Lore file '{LORE_FILE_PATH}' not found. No lore entries loaded.")
            return {}
        try:
            with open(LORE_FILE_PATH, 'r', encoding='utf-8') as f:
                lore_data_raw = json.load(f)
                if "entries" in lore_data_raw and isinstance(lore_data_raw["entries"], list):
                    lore_dict = {entry["id"]: entry for entry in lore_data_raw["entries"] if "id" in entry}
                    print(f"DroneSystem: Successfully loaded {len(lore_dict)} lore entries.")
                    return lore_dict
                else:
                    print(f"DroneSystem: Lore file '{LORE_FILE_PATH}' has incorrect format. Expected a root key 'entries' with a list.")
                    return {}
        except (IOError, json.JSONDecodeError) as e:
            print(f"DroneSystem: Error loading or parsing lore file '{LORE_FILE_PATH}': {e}")
            return {}
        except Exception as e:
            print(f"DroneSystem: An unexpected error occurred while loading lore file '{LORE_FILE_PATH}': {e}")
            return {}


    def _save_unlocks(self, data_to_save=None):
        self._ensure_data_dir_exists()
        current_data_to_save = data_to_save if data_to_save is not None else self.unlock_data
        try:
            with open(UNLOCKS_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(current_data_to_save, f, indent=2)
        except IOError as e:
            print(f"DroneSystem: Error saving unlock data to '{UNLOCKS_FILE_PATH}': {e}")

    def add_collected_glyph_tablet(self, tablet_id):
        """Adds a unique tablet ID to the list of collected tablets."""
        if not tablet_id:
            return False
        collected_tablets = self.unlock_data.setdefault("collected_glyph_tablet_ids", [])
        if tablet_id not in collected_tablets:
            collected_tablets.append(tablet_id)
            self._save_unlocks()
            print(f"DroneSystem: Added collected glyph tablet: {tablet_id}. Current: {collected_tablets}")
            return True
        return False

    def get_collected_glyph_tablet_ids(self):
        """Returns a list of collected glyph tablet IDs."""
        return self.unlock_data.get("collected_glyph_tablet_ids", [])[:]

    def get_selected_drone_id(self):
        return self.unlock_data.get("selected_drone", "DRONE")

    def set_selected_drone_id(self, drone_id):
        if drone_id in DRONE_DATA and self.is_drone_unlocked(drone_id):
            self.unlock_data["selected_drone"] = drone_id
            self._save_unlocks()
            print(f"DroneSystem: Drone '{drone_id}' selected.")
            return True
        print(f"DroneSystem: Failed to select drone '{drone_id}'. Not found in DRONE_DATA or not unlocked.")
        return False

    def get_drone_config(self, drone_id):
        config = DRONE_DATA.get(drone_id)
        if not config:
            print(f"DroneSystem: Warning - Drone ID '{drone_id}' not found in DRONE_DATA. Returning DRONE config.")
            return DRONE_DATA.get("DRONE", {})
        return config

    def get_all_drone_ids_ordered(self):
        return DRONE_DISPLAY_ORDER

    def is_drone_unlocked(self, drone_id):
        if drone_id in self.unlock_data.get("unlocked_drones", []):
            return True
        # Check if unlocked via blueprint (Architect-X example)
        if drone_id in self.unlock_data.get("unlocked_blueprints", []) and drone_id in DRONE_DATA:
            return True
        return False

    def get_player_level(self):
        return self.unlock_data.get("player_level", 1)

    def set_player_level(self, level):
        self.unlock_data["player_level"] = level
        newly_unlocked_drones = self._check_for_passive_unlocks()
        newly_unlocked_lore = self.check_and_unlock_lore_entries() # General check based on new level
        if not newly_unlocked_drones and not newly_unlocked_lore: # Save only if nothing else triggered a save
            self._save_unlocks()
        if newly_unlocked_drones:
             print(f"DroneSystem: Player level set to {level}. New drone unlocks: {newly_unlocked_drones}")
        if newly_unlocked_lore:
             print(f"DroneSystem: Player level set to {level}. New lore unlocks: {newly_unlocked_lore}")
        return newly_unlocked_drones # Return drones for potential UI notification

    def get_player_cores(self):
        return self.unlock_data.get("player_cores", 0)

    def add_player_cores(self, amount):
        self.unlock_data["player_cores"] = self.unlock_data.get("player_cores", 0) + amount
        # No save here, typically saved at end of level or when spending

    def spend_player_cores(self, amount):
        current_cores = self.get_player_cores()
        if current_cores >= amount:
            self.unlock_data["player_cores"] = current_cores - amount
            self._save_unlocks() # Save after spending
            return True
        return False

    def add_defeated_boss(self, boss_name):
        bosses_defeated_list = self.unlock_data.setdefault("bosses_defeated", [])
        newly_unlocked_drones = []
        newly_unlocked_lore = []
        if boss_name not in bosses_defeated_list:
            bosses_defeated_list.append(boss_name)
            newly_unlocked_drones = self._check_for_passive_unlocks()
            # Specifically trigger lore unlock related to this boss defeat
            newly_unlocked_lore = self.check_and_unlock_lore_entries(event_trigger="boss_defeated", trigger_value=boss_name)
            if not newly_unlocked_drones and not newly_unlocked_lore: # Save only if nothing else triggered save
                 self._save_unlocks()
            if newly_unlocked_drones:
                 print(f"DroneSystem: Boss '{boss_name}' defeated. New drone unlocks: {newly_unlocked_drones}")
            if newly_unlocked_lore:
                 print(f"DroneSystem: Boss '{boss_name}' defeated. New lore unlocks: {newly_unlocked_lore}")
        return newly_unlocked_drones # Return drones for potential UI notification

    def _check_for_passive_unlocks(self): # Checks level, boss defeats for drone unlocks
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
            # "cores" and "blueprint" are active unlocks, not passive

            if unlocked_by_passive_condition:
                if drone_id not in unlocked_drones_list:
                    unlocked_drones_list.append(drone_id)
                    newly_unlocked_this_check.append(drone_id)
                    # Also check for lore tied to this drone unlock
                    self.check_and_unlock_lore_entries(event_trigger=f"drone_unlocked_{drone_id}")


        if newly_unlocked_this_check:
            self._save_unlocks() # Save if any passive unlocks occurred
            print(f"DroneSystem: Passive drone check unlocked: {newly_unlocked_this_check}")
        return newly_unlocked_this_check

    def attempt_unlock_drone_with_cores(self, drone_id):
        if self.is_drone_unlocked(drone_id):
            return True, "already_unlocked" # Already unlocked

        config = self.get_drone_config(drone_id)
        if not config: return False, "drone_not_found"

        unlock_condition = config.get("unlock_condition", {})
        if unlock_condition.get("type") != "cores":
            return False, "not_core_unlock"

        cost = unlock_condition.get("value", float('inf'))
        if self.spend_player_cores(cost): # spend_player_cores already saves
            unlocked_list = self.unlock_data.setdefault("unlocked_drones", [])
            if drone_id not in unlocked_list: # Ensure it's added if not already
                unlocked_list.append(drone_id)
            # Check for lore related to this drone unlock
            lore_unlocked = self.check_and_unlock_lore_entries(event_trigger=f"drone_unlocked_{drone_id}")
            if lore_unlocked:
                print(f"DroneSystem: Unlocked lore related to drone '{drone_id}'.")
            self._save_unlocks() # Ensure save after adding to list explicitly
            print(f"DroneSystem: Drone '{drone_id}' unlocked by spending {cost} cores.")
            return True, "unlocked"
        return False, "insufficient_cores"


    def get_drone_stats(self, drone_id, is_in_architect_vault=False):
        base_config = self.get_drone_config(drone_id)
        if not base_config or "base_stats" not in base_config:
            print(f"DroneSystem: Error - Base config or base_stats not found for drone '{drone_id}'. Returning minimal stats.")
            # Return a default minimal structure to prevent crashes
            return {
                "hp": gs.get_game_setting("PLAYER_MAX_HEALTH"),
                "speed": gs.get_game_setting("PLAYER_SPEED"),
                "turn_speed": gs.get_game_setting("ROTATION_SPEED"),
                "fire_rate_multiplier": 1.0,
                "bullet_damage_multiplier": 1.0,
                "special_ability": None
            }

        effective_stats = base_config["base_stats"].copy()

        # Apply Omega-9 randomization if applicable
        if drone_id == "OMEGA-9" and effective_stats.get("special_ability") == "omega_boost":
            for stat_name, (min_mult, max_mult) in OMEGA_STAT_RANGES.items():
                if stat_name in effective_stats: # Make sure the stat exists to be modified
                    # Get the defined base value from DRONE_DATA for Omega-9 for consistency
                    original_value = DRONE_DATA["OMEGA-9"]["base_stats"][stat_name]
                    multiplier = random.uniform(min_mult, max_mult)
                    modified_value = original_value * multiplier
                    # Apply type casting for HP
                    effective_stats[stat_name] = int(modified_value) if stat_name == "hp" else modified_value
        
        # Apply buffs from collected Core Fragments if in Architect's Vault
        if is_in_architect_vault and CORE_FRAGMENT_DETAILS:
            collected_fragment_ids = self.get_collected_fragments_ids()
            for frag_id in collected_fragment_ids:
                # Find the fragment's config details
                fragment_config = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                
                if fragment_config:
                    if "buff" in fragment_config: # Primary buff
                        buff = fragment_config["buff"]
                        buff_type = buff.get("type")
                        buff_value = buff.get("value")
                        if buff_type == "speed" and "speed" in effective_stats:
                            effective_stats["speed"] *= buff_value
                        elif buff_type == "bullet_damage_multiplier" and "bullet_damage_multiplier" in effective_stats:
                            effective_stats["bullet_damage_multiplier"] *= buff_value
                        # Add other primary buff types here if needed

                    if "buff_alt" in fragment_config: # Alternate buff (e.g., damage reduction)
                        buff_alt = fragment_config["buff_alt"]
                        buff_alt_type = buff_alt.get("type")
                        buff_alt_value = buff_alt.get("value")
                        if buff_alt_type == "damage_reduction":
                            # Apply damage reduction by multiplying a damage taken multiplier
                            effective_stats["damage_taken_multiplier"] = effective_stats.get("damage_taken_multiplier", 1.0) * (1.0 - buff_alt_value)
                        # Add other alternate buff types here if needed
        return effective_stats

    def collect_core_fragment(self, fragment_id_to_collect):
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
            # Check for lore related to this fragment collection
            newly_unlocked_lore = self.check_and_unlock_lore_entries(event_trigger=f"collect_fragment_{fragment_id_to_collect}")
            if newly_unlocked_lore:
                print(f"DroneSystem: Lore unlocked by collecting fragment {fragment_id_to_collect}: {newly_unlocked_lore}")
            self._save_unlocks()
            print(f"DroneSystem: Core Fragment '{fragment_id_to_collect}' collected. Total: {len(collected_list)}/{TOTAL_CORE_FRAGMENTS_NEEDED}")
            return True
        return False # Already collected

    def has_collected_fragment(self, fragment_id_to_check):
        return fragment_id_to_check in self.unlock_data.get("collected_core_fragments", [])

    def get_collected_fragments_ids(self):
        """Returns a copy of the list of collected fragment IDs."""
        return self.unlock_data.get("collected_core_fragments", [])[:]

    def are_all_core_fragments_collected(self):
        """Checks if all *required for vault entry* core fragments are collected."""
        num_collected = len(self.unlock_data.get("collected_core_fragments", []))
        # This definition of "required" might need to be more specific if some fragments are optional
        # For now, assuming TOTAL_CORE_FRAGMENTS_NEEDED is the count for alpha, beta, gamma.
        relevant_fragments_for_vault_entry = [
            key for key, details in CORE_FRAGMENT_DETAILS.items() 
            if details and details.get("id") != "vault_core" # Exclude the one that's a reward FROM the vault
               # and details.get("spawn_info") # If only spawned fragments count (not rewarded ones)
        ]
        # This check is simply based on count vs the defined total needed for vault entry.
        return num_collected >= TOTAL_CORE_FRAGMENTS_NEEDED


    def reset_collected_fragments_in_storage(self):
        """ Resets only the 'collected_core_fragments' list in the persistent storage. """
        if "collected_core_fragments" in self.unlock_data:
            self.unlock_data["collected_core_fragments"] = []
            print("DroneSystem: Persisted collected core fragments have been reset for new game session.")
            # No save here; should be part of broader session reset or game save logic
        else: # Should not happen if _load_unlocks initializes correctly
            self.unlock_data["collected_core_fragments"] = []
            print("DroneSystem: Persisted collected_core_fragments key initialized and reset for new game session.")


    def reset_architect_vault_status(self):
        if "architect_vault_completed" in self.unlock_data:
            self.unlock_data["architect_vault_completed"] = False
            print("DroneSystem: Architect's Vault completion status reset for new game session.")
        else:
            self.unlock_data["architect_vault_completed"] = False # Ensure it's initialized
            print("DroneSystem: Architect's Vault completion status initialized and reset for new game session.")
        # No save here; should be part of broader session reset or game save logic

    def mark_architect_vault_completed(self, completed_successfully=True):
        self.unlock_data["architect_vault_completed"] = completed_successfully
        newly_unlocked_lore = []
        if completed_successfully:
            print("DroneSystem: Architect's Vault completed successfully!")
            if ARCHITECT_REWARD_BLUEPRINT_ID: self.unlock_blueprint(ARCHITECT_REWARD_BLUEPRINT_ID) # This will save
            if ARCHITECT_REWARD_LORE_ID:
                newly_unlocked_lore.extend(self.unlock_lore_entry_by_id(ARCHITECT_REWARD_LORE_ID)) # This saves
            # Also, trigger general story beat for vault completion
            newly_unlocked_lore.extend(self.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB05"))

        else:
            print("DroneSystem: Architect's Vault attempt failed.")
        
        if newly_unlocked_lore: # Check_and_unlock_lore already saves if it finds something
            print(f"DroneSystem: Lore unlocked from vault completion: {newly_unlocked_lore}")
        self._save_unlocks() # Explicit save after all potential changes


    def has_completed_architect_vault(self):
        return self.unlock_data.get("architect_vault_completed", False)

    def unlock_blueprint(self, blueprint_id):
        if not blueprint_id: return False
        unlocked_blueprints_list = self.unlock_data.setdefault("unlocked_blueprints", [])
        newly_unlocked_blueprint = False
        if blueprint_id not in unlocked_blueprints_list:
            unlocked_blueprints_list.append(blueprint_id)
            newly_unlocked_blueprint = True
            print(f"DroneSystem: Blueprint '{blueprint_id}' unlocked!")

        # If this blueprint also unlocks a drone directly
        newly_unlocked_drone_via_blueprint = False
        if blueprint_id in DRONE_DATA: # Check if the blueprint ID matches a drone ID
            unlocked_drones_list = self.unlock_data.setdefault("unlocked_drones", [])
            if blueprint_id not in unlocked_drones_list:
                unlocked_drones_list.append(blueprint_id)
                newly_unlocked_drone_via_blueprint = True
                print(f"DroneSystem: Drone '{blueprint_id}' unlocked via blueprint.")
                # Check for lore related to this drone unlock
                self.check_and_unlock_lore_entries(event_trigger=f"drone_unlocked_{blueprint_id}")


        if newly_unlocked_blueprint or newly_unlocked_drone_via_blueprint:
            self._save_unlocks()
        return newly_unlocked_blueprint or newly_unlocked_drone_via_blueprint

    def has_unlocked_blueprint(self, blueprint_id):
        return blueprint_id in self.unlock_data.get("unlocked_blueprints", [])

    # --- Puzzle Terminal Solved Tracking ---
    def mark_puzzle_terminal_as_solved(self, terminal_id):
        """Marks a puzzle terminal as solved and saves the progress."""
        if not terminal_id:
            return False
        solved_terminals = self.unlock_data.setdefault("solved_puzzle_terminals", [])
        if terminal_id not in solved_terminals:
            solved_terminals.append(terminal_id)
            self._save_unlocks()
            print(f"DroneSystem: Puzzle terminal '{terminal_id}' marked as solved.")
            return True
        return False

    def has_puzzle_terminal_been_solved(self, terminal_id):
        """Checks if a specific puzzle terminal has been solved."""
        return terminal_id in self.unlock_data.get("solved_puzzle_terminals", [])


    def unlock_lore_entry_by_id(self, lore_id_to_unlock):
        """Unlocks a specific lore entry by its ID if not already unlocked."""
        if not lore_id_to_unlock: return [] # Return empty list if no ID
        unlocked_lore_list = self.unlock_data.setdefault("unlocked_lore_codex_entries", [])
        if lore_id_to_unlock not in unlocked_lore_list:
            unlocked_lore_list.append(lore_id_to_unlock)
            self._save_unlocks() # Save after unlocking
            print(f"DroneSystem: Lore Codex Entry '{lore_id_to_unlock}' unlocked!")
            return [lore_id_to_unlock] # Return list of newly unlocked
        return [] # Return empty list if already unlocked

    def get_unlocked_lore_ids(self):
        """Returns a list of all unlocked lore entry IDs."""
        return self.unlock_data.get("unlocked_lore_codex_entries", [])[:] # Return a copy

    def get_lore_entry_details(self, lore_id):
        """Returns the details of a specific lore entry if it exists."""
        return self.all_lore_entries.get(lore_id)
        
    def get_all_loaded_lore_entries(self):
        """Returns the dictionary of all loaded lore entries."""
        return self.all_lore_entries

    def check_and_unlock_lore_entries(self, event_trigger=None, trigger_value=None):
        # ... (rest of the method remains the same)
        if not self.all_lore_entries:
            return []

        newly_unlocked_lore_ids = []
        unlocked_lore_list = self.unlock_data.setdefault("unlocked_lore_codex_entries", [])
        
        player_level = self.get_player_level()
        bosses_defeated = self.unlock_data.get("bosses_defeated", [])
        collected_tablets = self.get_collected_glyph_tablet_ids() # Get current collected tablets

        for lore_id, lore_details in self.all_lore_entries.items():
            if lore_id in unlocked_lore_list:
                continue # Already unlocked

            unlock_condition_str = lore_details.get("unlocked_by", "")
            should_unlock = False

            # --- Start of condition checking ---
            if event_trigger: # If a specific event triggered this check
                if unlock_condition_str == event_trigger: # Exact match (e.g., "game_start")
                    should_unlock = True
                # Match for specific value triggers (e.g., "boss_defeated_MAZE_GUARDIAN")
                elif trigger_value and unlock_condition_str.startswith(event_trigger) and unlock_condition_str.endswith(str(trigger_value)):
                    should_unlock = True
                # Match for general type triggers where the specific drone/item is part of the unlock string
                # e.g., event_trigger="drone_unlocked_", unlock_condition_str="drone_unlocked_VANTIS"
                elif unlock_condition_str.startswith(event_trigger) and not trigger_value: # Ensure trigger_value is None or empty for this case
                     # This part is a bit broad. Example: if event_trigger is "drone_unlocked_"
                     # and unlock_condition_str is "drone_unlocked_VANTIS", this will check if VANTIS is unlocked.
                     # This might be redundant if passive checks already handle "drone_unlocked_X"
                     # Let's refine: this case is mostly for when the `event_trigger` itself contains the specific ID.
                     # e.g. `event_trigger = "drone_unlocked_PHANTOM"`
                     pass # This type of check is better handled by specific event_triggers like `drone_unlocked_DRONE_ID`

            else: # General check (e.g., on level up, or periodic check)
                if unlock_condition_str == "default" or unlock_condition_str == "game_start":
                    should_unlock = True
                elif unlock_condition_str.startswith("level_reached_"):
                    try:
                        required_level = int(unlock_condition_str.split("_")[-1])
                        if player_level >= required_level:
                            should_unlock = True
                    except ValueError:
                        print(f"DroneSystem: Invalid level format in lore unlock condition: {unlock_condition_str}")
                elif unlock_condition_str.startswith("boss_defeated_"):
                    required_boss = unlock_condition_str.split("boss_defeated_")[-1]
                    if required_boss in bosses_defeated:
                        should_unlock = True
                elif unlock_condition_str.startswith("drone_unlocked_"):
                    required_drone = unlock_condition_str.split("drone_unlocked_")[-1]
                    if required_drone in self.unlock_data.get("unlocked_drones", []):
                        should_unlock = True
                elif unlock_condition_str.startswith("collect_fragment_"):
                    required_fragment_id_from_lore_string = unlock_condition_str.split("collect_fragment_")[-1]
                    if required_fragment_id_from_lore_string in self.get_collected_fragments_ids(): # Check against currently collected
                        should_unlock = True
                elif unlock_condition_str.startswith("collect_log_"):
                    # This typically requires an event_trigger with the specific log ID.
                    # For a general check, it's hard to determine if the specific log was just collected.
                    pass
                elif unlock_condition_str.startswith("collect_glyph_tablet_"):
                    required_tablet_id_from_lore_string = unlock_condition_str.split("collect_glyph_tablet_")[-1]
                    if required_tablet_id_from_lore_string in collected_tablets:
                        should_unlock = True
                elif unlock_condition_str == "collect_all_architect_glyph_tablets":
                    required_set = {"alpha", "beta", "gamma"} # Define which tablets are "all"
                    if required_set.issubset(set(collected_tablets)):
                        should_unlock = True
                elif unlock_condition_str.startswith("story_beat_trigger_"):
                    # Story beats are usually triggered by specific game events passed via event_trigger.
                    # For a general check, it's hard to know if the condition for SB01, SB02 etc. just occurred.
                    # However, if a story beat ID is directly the unlock_condition, it implies it's an event.
                    # Example: unlock_by: "story_beat_SB01" (would be caught by event_trigger == unlock_condition_str)
                    pass
                elif unlock_condition_str == "element115_puzzle_solved":
                     if self.has_puzzle_terminal_been_solved("level_5_element115_terminal"): # Example ID
                         should_unlock = True


            if should_unlock:
                unlocked_lore_list.append(lore_id)
                newly_unlocked_lore_ids.append(lore_id)
                print(f"DroneSystem: Lore entry '{lore_id}' unlocked by condition '{unlock_condition_str}'.")
        # --- End of condition checking ---

        if newly_unlocked_lore_ids:
            self._save_unlocks() # Save if any new lore was unlocked
        return newly_unlocked_lore_ids


    def has_unlocked_lore(self, lore_id): # Simple check if ID is in the list
        return lore_id in self.unlock_data.get("unlocked_lore_codex_entries", [])

    def reset_all_progress(self):
        print("DroneSystem: Resetting all player progress to default.")
        default_data = {
            "unlocked_drones": ["DRONE"], "selected_drone": "DRONE",
            "player_level": 1, "bosses_defeated": [], "player_cores": 0,
            "collected_core_fragments": [], "architect_vault_completed": False,
            "unlocked_blueprints": [], "unlocked_lore_codex_entries": [],
            "collected_glyph_tablet_ids": [],
            "solved_puzzle_terminals": [] # Ensure reset
        }
        self.unlock_data = default_data
        self._save_unlocks()
        print("DroneSystem: All progress reset.")

# Example usage / Test functions (can be commented out in the final game)
if __name__ == '__main__':
    print("DroneSystem: Running self-test...")
    try:
        # Attempt to import game_settings to make gs. available for testing if needed
        # This is just to simulate a bit more of the game environment for the self-test
        pass
    except ImportError:
        print("Self-test: Could not import sibling/parent modules for full context. Limited test.")

    ds = DroneSystem()
    print(f"DroneSystem Test: Initial selected drone: {ds.get_selected_drone_id()}")
    if "VANTIS" in DRONE_DATA: # Check if VANTIS config exists
        print(f"DroneSystem Test: Is VANTIS unlocked? {ds.is_drone_unlocked('VANTIS')}")
    ds.set_player_level(5) # This will also trigger passive unlocks and lore checks
    print(f"DroneSystem Test: Player level after set: {ds.get_player_level()}")
    ds.add_player_cores(500)
    print(f"DroneSystem Test: Player cores after add: {ds.get_player_cores()}")
    ds.spend_player_cores(100) # This saves
    print(f"DroneSystem Test: Player cores after spend: {ds.get_player_cores()}")
    
    print(f"DroneSystem Test: Loaded {len(ds.all_lore_entries)} lore entries.")
    if "architect_legacy_intro" in ds.all_lore_entries: # Check if a specific lore entry is loaded
        print(f"DroneSystem Test: 'architect_legacy_intro' details: {ds.get_lore_entry_details('architect_legacy_intro')['title']}")
    
    # Test lore unlock by specific event
    unlocked_on_start = ds.check_and_unlock_lore_entries(event_trigger="game_start")
    print(f"DroneSystem Test: Lore unlocked on 'game_start': {unlocked_on_start}")
    print(f"DroneSystem Test: All unlocked lore IDs: {ds.get_unlocked_lore_ids()}")

    # Test passive drone and lore unlock via level up
    ds.unlock_data["player_level"] = 2 # Simulate level change
    ds._check_for_passive_unlocks() # Manually trigger passive check
    ds.check_and_unlock_lore_entries() # General check after level up
    print(f"DroneSystem Test: Is VANTIS drone unlocked at L2? {ds.is_drone_unlocked('VANTIS')}")
    # Lore for VANTIS should unlock if VANTIS is unlocked and "drone_unlocked_VANTIS" is a condition
    print(f"DroneSystem Test: Is VANTIS lore unlocked at L2? {ds.has_unlocked_lore('drone_VANTIS')}") # Assuming 'drone_VANTIS' is an ID in lore_entries.json
    
    ds.set_player_level(3) # This should re-trigger checks
    print(f"DroneSystem Test: Is VANTIS drone unlocked at L3? {ds.is_drone_unlocked('VANTIS')}")
    
    # Test specific lore unlock if VANTIS is unlocked
    if ds.is_drone_unlocked('VANTIS'):
        lore_for_vantis = ds.check_and_unlock_lore_entries(event_trigger=f"drone_unlocked_VANTIS")
        if lore_for_vantis:
             print(f"DroneSystem Test: Lore for VANTIS unlocked via specific trigger: {lore_for_vantis}")
    print(f"DroneSystem Test: Is VANTIS lore unlocked at L3 (after checks)? {ds.has_unlocked_lore('drone_VANTIS')}")


    # Test puzzle terminal tracking
    test_terminal_id = "test_puzzle_01"
    print(f"DroneSystem Test: Has '{test_terminal_id}' been solved initially? {ds.has_puzzle_terminal_been_solved(test_terminal_id)}")
    ds.mark_puzzle_terminal_as_solved(test_terminal_id)
    print(f"DroneSystem Test: Has '{test_terminal_id}' been solved after marking? {ds.has_puzzle_terminal_been_solved(test_terminal_id)}")


    ds.reset_all_progress()