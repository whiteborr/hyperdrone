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
            "collected_glyph_tablet_ids": [] # New: For tracking collected tablets
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
                
                if not isinstance(data.get("collected_glyph_tablet_ids"), list): # Ensure tablet list exists
                    data["collected_glyph_tablet_ids"] = []
                    
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
        if drone_id in self.unlock_data.get("unlocked_blueprints", []) and drone_id in DRONE_DATA:
            return True
        return False

    def get_player_level(self):
        return self.unlock_data.get("player_level", 1)

    def set_player_level(self, level):
        self.unlock_data["player_level"] = level
        newly_unlocked_drones = self._check_for_passive_unlocks()
        newly_unlocked_lore = self.check_and_unlock_lore_entries() 
        if not newly_unlocked_drones and not newly_unlocked_lore:
            self._save_unlocks()
        if newly_unlocked_drones:
             print(f"DroneSystem: Player level set to {level}. New drone unlocks: {newly_unlocked_drones}")
        if newly_unlocked_lore:
             print(f"DroneSystem: Player level set to {level}. New lore unlocks: {newly_unlocked_lore}")
        return newly_unlocked_drones 

    def get_player_cores(self):
        return self.unlock_data.get("player_cores", 0)

    def add_player_cores(self, amount):
        self.unlock_data["player_cores"] = self.unlock_data.get("player_cores", 0) + amount

    def spend_player_cores(self, amount):
        current_cores = self.get_player_cores()
        if current_cores >= amount:
            self.unlock_data["player_cores"] = current_cores - amount
            self._save_unlocks() 
            return True
        return False

    def add_defeated_boss(self, boss_name):
        bosses_defeated_list = self.unlock_data.setdefault("bosses_defeated", [])
        newly_unlocked_drones = []
        newly_unlocked_lore = []
        if boss_name not in bosses_defeated_list:
            bosses_defeated_list.append(boss_name)
            newly_unlocked_drones = self._check_for_passive_unlocks()
            newly_unlocked_lore = self.check_and_unlock_lore_entries(event_trigger="boss_defeated", trigger_value=boss_name)
            if not newly_unlocked_drones and not newly_unlocked_lore:
                 self._save_unlocks()
            if newly_unlocked_drones:
                 print(f"DroneSystem: Boss '{boss_name}' defeated. New drone unlocks: {newly_unlocked_drones}")
            if newly_unlocked_lore:
                 print(f"DroneSystem: Boss '{boss_name}' defeated. New lore unlocks: {newly_unlocked_lore}")
        return newly_unlocked_drones 

    def _check_for_passive_unlocks(self): 
        newly_unlocked_this_check = []
        player_level = self.get_player_level()
        bosses_defeated = self.unlock_data.get("bosses_defeated", [])
        unlocked_drones_list = self.unlock_data.setdefault("unlocked_drones", [])

        for drone_id, config in DRONE_DATA.items():
            if drone_id in unlocked_drones_list:
                continue

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

            if unlocked_by_passive_condition:
                if drone_id not in unlocked_drones_list:
                    unlocked_drones_list.append(drone_id)
                    newly_unlocked_this_check.append(drone_id)

        if newly_unlocked_this_check:
            self._save_unlocks() 
            print(f"DroneSystem: Passive drone check unlocked: {newly_unlocked_this_check}")
        return newly_unlocked_this_check

    def attempt_unlock_drone_with_cores(self, drone_id):
        if self.is_drone_unlocked(drone_id):
            return True, "already_unlocked" 

        config = self.get_drone_config(drone_id)
        if not config: return False, "drone_not_found"

        unlock_condition = config.get("unlock_condition", {})
        if unlock_condition.get("type") != "cores":
            return False, "not_core_unlock"

        cost = unlock_condition.get("value", float('inf'))
        if self.spend_player_cores(cost):
            unlocked_list = self.unlock_data.setdefault("unlocked_drones", [])
            if drone_id not in unlocked_list:
                unlocked_list.append(drone_id)
            lore_unlocked = self.check_and_unlock_lore_entries(event_trigger=f"drone_unlocked_{drone_id}")
            if lore_unlocked:
                print(f"DroneSystem: Unlocked lore related to drone '{drone_id}'.")
            self._save_unlocks() 
            print(f"DroneSystem: Drone '{drone_id}' unlocked by spending {cost} cores.")
            return True, "unlocked"
        return False, "insufficient_cores"


    def get_drone_stats(self, drone_id, is_in_architect_vault=False):
        base_config = self.get_drone_config(drone_id)
        if not base_config or "base_stats" not in base_config:
            print(f"DroneSystem: Error - Base config or base_stats not found for drone '{drone_id}'. Returning minimal stats.")
            return {
                "hp": gs.get_game_setting("PLAYER_MAX_HEALTH"),
                "speed": gs.get_game_setting("PLAYER_SPEED"),
                "turn_speed": gs.get_game_setting("ROTATION_SPEED"),
                "fire_rate_multiplier": 1.0,
                "bullet_damage_multiplier": 1.0,
                "special_ability": None
            }

        effective_stats = base_config["base_stats"].copy()

        if drone_id == "OMEGA-9" and effective_stats.get("special_ability") == "omega_boost":
            for stat_name, (min_mult, max_mult) in OMEGA_STAT_RANGES.items():
                if stat_name in effective_stats:
                    original_value = DRONE_DATA["OMEGA-9"]["base_stats"][stat_name]
                    multiplier = random.uniform(min_mult, max_mult)
                    modified_value = original_value * multiplier
                    effective_stats[stat_name] = int(modified_value) if stat_name == "hp" else modified_value
        
        if is_in_architect_vault and CORE_FRAGMENT_DETAILS:
            collected_fragment_ids = self.get_collected_fragments_ids()
            for frag_id in collected_fragment_ids:
                fragment_config = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                
                if fragment_config:
                    if "buff" in fragment_config:
                        buff = fragment_config["buff"]
                        buff_type = buff.get("type")
                        buff_value = buff.get("value")
                        if buff_type == "speed" and "speed" in effective_stats:
                            effective_stats["speed"] *= buff_value
                        elif buff_type == "bullet_damage_multiplier" and "bullet_damage_multiplier" in effective_stats:
                            effective_stats["bullet_damage_multiplier"] *= buff_value

                    if "buff_alt" in fragment_config:
                        buff_alt = fragment_config["buff_alt"]
                        buff_alt_type = buff_alt.get("type")
                        buff_alt_value = buff_alt.get("value")
                        if buff_alt_type == "damage_reduction":
                            effective_stats["damage_taken_multiplier"] = effective_stats.get("damage_taken_multiplier", 1.0) * (1.0 - buff_alt_value)
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
            newly_unlocked_lore = self.check_and_unlock_lore_entries(event_trigger=f"collect_fragment_{fragment_id_to_collect}")
            if newly_unlocked_lore:
                print(f"DroneSystem: Lore unlocked by collecting fragment {fragment_id_to_collect}: {newly_unlocked_lore}")
            self._save_unlocks()
            print(f"DroneSystem: Core Fragment '{fragment_id_to_collect}' collected. Total: {len(collected_list)}/{TOTAL_CORE_FRAGMENTS_NEEDED}")
            return True
        return False

    def has_collected_fragment(self, fragment_id_to_check):
        return fragment_id_to_check in self.unlock_data.get("collected_core_fragments", [])

    def get_collected_fragments_ids(self):
        return self.unlock_data.get("collected_core_fragments", [])[:]

    def are_all_core_fragments_collected(self):
        num_collected = len(self.unlock_data.get("collected_core_fragments", []))
        relevant_fragments_for_vault_entry = [
            key for key, details in CORE_FRAGMENT_DETAILS.items() 
            if details and details.get("id") != "vault_core" and details.get("spawn_info") 
        ]
        return num_collected >= TOTAL_CORE_FRAGMENTS_NEEDED


    def reset_collected_fragments_in_storage(self):
        if "collected_core_fragments" in self.unlock_data:
            self.unlock_data["collected_core_fragments"] = []
            print("DroneSystem: Persisted collected core fragments have been reset for new game session.")
        else:
            self.unlock_data["collected_core_fragments"] = []
            print("DroneSystem: Persisted collected_core_fragments key initialized and reset for new game session.")

    def reset_architect_vault_status(self):
        if "architect_vault_completed" in self.unlock_data:
            self.unlock_data["architect_vault_completed"] = False
            print("DroneSystem: Architect's Vault completion status reset for new game session.")
        else:
            self.unlock_data["architect_vault_completed"] = False
            print("DroneSystem: Architect's Vault completion status initialized and reset for new game session.")

    def mark_architect_vault_completed(self, completed_successfully=True):
        self.unlock_data["architect_vault_completed"] = completed_successfully
        newly_unlocked_lore = []
        if completed_successfully:
            print("DroneSystem: Architect's Vault completed successfully!")
            if ARCHITECT_REWARD_BLUEPRINT_ID: self.unlock_blueprint(ARCHITECT_REWARD_BLUEPRINT_ID)
            if ARCHITECT_REWARD_LORE_ID:
                newly_unlocked_lore.extend(self.unlock_lore_entry_by_id(ARCHITECT_REWARD_LORE_ID))
            newly_unlocked_lore.extend(self.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB05"))

        else:
            print("DroneSystem: Architect's Vault attempt failed.")
        
        if newly_unlocked_lore:
            print(f"DroneSystem: Lore unlocked from vault completion: {newly_unlocked_lore}")
        self._save_unlocks()


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

        newly_unlocked_drone_via_blueprint = False
        if blueprint_id in DRONE_DATA: 
            unlocked_drones_list = self.unlock_data.setdefault("unlocked_drones", [])
            if blueprint_id not in unlocked_drones_list:
                unlocked_drones_list.append(blueprint_id)
                newly_unlocked_drone_via_blueprint = True
                print(f"DroneSystem: Drone '{blueprint_id}' unlocked via blueprint.")
                self.check_and_unlock_lore_entries(event_trigger=f"drone_unlocked_{blueprint_id}")


        if newly_unlocked_blueprint or newly_unlocked_drone_via_blueprint:
            self._save_unlocks()
        return newly_unlocked_blueprint or newly_unlocked_drone_via_blueprint

    def has_unlocked_blueprint(self, blueprint_id):
        return blueprint_id in self.unlock_data.get("unlocked_blueprints", [])

    def unlock_lore_entry_by_id(self, lore_id_to_unlock):
        """Unlocks a specific lore entry by its ID if not already unlocked."""
        if not lore_id_to_unlock: return []
        unlocked_lore_list = self.unlock_data.setdefault("unlocked_lore_codex_entries", [])
        if lore_id_to_unlock not in unlocked_lore_list:
            unlocked_lore_list.append(lore_id_to_unlock)
            self._save_unlocks() 
            print(f"DroneSystem: Lore Codex Entry '{lore_id_to_unlock}' unlocked!")
            return [lore_id_to_unlock] 
        return []

    def get_unlocked_lore_ids(self):
        """Returns a list of all unlocked lore entry IDs."""
        return self.unlock_data.get("unlocked_lore_codex_entries", [])[:]

    def get_lore_entry_details(self, lore_id):
        """Returns the details of a specific lore entry if it exists."""
        return self.all_lore_entries.get(lore_id)
        
    def get_all_loaded_lore_entries(self):
        """Returns the dictionary of all loaded lore entries."""
        return self.all_lore_entries

    def check_and_unlock_lore_entries(self, event_trigger=None, trigger_value=None):
        if not self.all_lore_entries:
            return []

        newly_unlocked_lore_ids = []
        unlocked_lore_list = self.unlock_data.setdefault("unlocked_lore_codex_entries", [])
        
        player_level = self.get_player_level()
        bosses_defeated = self.unlock_data.get("bosses_defeated", [])
        collected_tablets = self.get_collected_glyph_tablet_ids() # Get current collected tablets

        for lore_id, lore_details in self.all_lore_entries.items():
            if lore_id in unlocked_lore_list:
                continue 

            unlock_condition_str = lore_details.get("unlocked_by", "")
            should_unlock = False

            if event_trigger:
                if unlock_condition_str == event_trigger: 
                    should_unlock = True
                elif trigger_value and unlock_condition_str.startswith(event_trigger) and unlock_condition_str.endswith(str(trigger_value)):
                    should_unlock = True
                elif unlock_condition_str.startswith(event_trigger) and not trigger_value: 
                     drone_id_suffix = unlock_condition_str.split(event_trigger)[-1] 
                     if event_trigger.startswith("drone_unlocked_") and drone_id_suffix in self.unlock_data.get("unlocked_drones", []):
                         should_unlock = True
            else: 
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
                    required_fragment = unlock_condition_str.split("collect_fragment_")[-1]
                    if required_fragment in self.get_collected_fragments_ids(): 
                        should_unlock = True
                elif unlock_condition_str.startswith("collect_log_"): # Handle specific log collection
                    required_log = unlock_condition_str.split("collect_log_")[-1]
                    # This condition is usually met by specific event_trigger, but can be here for completeness
                    # For general check, this log_id wouldn't be in trigger_value.
                    # Better handled by direct trigger from GameController when item is picked up.
                    pass 
                elif unlock_condition_str.startswith("collect_glyph_tablet_"): # Handle specific tablet collection
                    required_tablet = unlock_condition_str.split("collect_glyph_tablet_")[-1]
                    # Also better handled by direct event_trigger.
                    pass
                elif unlock_condition_str == "collect_all_architect_glyph_tablets":
                    # Check if all required tablets ("alpha", "beta", "gamma") are in collected_tablets
                    required_set = {"alpha", "beta", "gamma"}
                    if required_set.issubset(set(collected_tablets)):
                        should_unlock = True
                elif unlock_condition_str.startswith("story_beat_trigger_"):
                    pass


            if should_unlock:
                unlocked_lore_list.append(lore_id)
                newly_unlocked_lore_ids.append(lore_id)
                print(f"DroneSystem: Lore entry '{lore_id}' unlocked by condition '{unlock_condition_str}'.")

        if newly_unlocked_lore_ids:
            self._save_unlocks() 
        return newly_unlocked_lore_ids


    def has_unlocked_lore(self, lore_id): 
        return lore_id in self.unlock_data.get("unlocked_lore_codex_entries", [])

    def reset_all_progress(self):
        print("DroneSystem: Resetting all player progress to default.")
        default_data = {
            "unlocked_drones": ["DRONE"], "selected_drone": "DRONE",
            "player_level": 1, "bosses_defeated": [], "player_cores": 0,
            "collected_core_fragments": [], "architect_vault_completed": False,
            "unlocked_blueprints": [], "unlocked_lore_codex_entries": [],
            "collected_glyph_tablet_ids": [] # Ensure reset
        }
        self.unlock_data = default_data
        self._save_unlocks()
        print("DroneSystem: All progress reset.")

if __name__ == '__main__':
    print("DroneSystem: Running self-test...")
    try:
        pass
    except ImportError:
        print("Self-test: Could not import sibling/parent modules for full context. Limited test.")

    ds = DroneSystem()
    print(f"DroneSystem Test: Initial selected drone: {ds.get_selected_drone_id()}")
    if "VANTIS" in DRONE_DATA:
        print(f"DroneSystem Test: Is VANTIS unlocked? {ds.is_drone_unlocked('VANTIS')}")
    ds.set_player_level(5) 
    print(f"DroneSystem Test: Player level after set: {ds.get_player_level()}")
    ds.add_player_cores(500)
    print(f"DroneSystem Test: Player cores after add: {ds.get_player_cores()}")
    ds.spend_player_cores(100) 
    print(f"DroneSystem Test: Player cores after spend: {ds.get_player_cores()}")
    
    print(f"DroneSystem Test: Loaded {len(ds.all_lore_entries)} lore entries.")
    if "architect_legacy_intro" in ds.all_lore_entries:
        print(f"DroneSystem Test: 'architect_legacy_intro' details: {ds.get_lore_entry_details('architect_legacy_intro')['title']}")
    
    unlocked_on_start = ds.check_and_unlock_lore_entries(event_trigger="game_start")
    print(f"DroneSystem Test: Lore unlocked on 'game_start': {unlocked_on_start}")
    print(f"DroneSystem Test: All unlocked lore IDs: {ds.get_unlocked_lore_ids()}")

    ds.unlock_data["player_level"] = 2 
    ds._check_for_passive_unlocks() 
    ds.check_and_unlock_lore_entries()
    print(f"DroneSystem Test: Is VANTIS drone unlocked at L2? {ds.is_drone_unlocked('VANTIS')}")
    print(f"DroneSystem Test: Is VANTIS lore unlocked at L2? {ds.has_unlocked_lore('drone_VANTIS')}")
    
    ds.set_player_level(3) 
    print(f"DroneSystem Test: Is VANTIS drone unlocked at L3? {ds.is_drone_unlocked('VANTIS')}")
    
    if ds.is_drone_unlocked('VANTIS'):
        lore_for_vantis = ds.check_and_unlock_lore_entries(event_trigger=f"drone_unlocked_VANTIS")
        if lore_for_vantis:
             print(f"DroneSystem Test: Lore for VANTIS unlocked via specific trigger: {lore_for_vantis}")
    print(f"DroneSystem Test: Is VANTIS lore unlocked at L3 (after checks)? {ds.has_unlocked_lore('drone_VANTIS')}")


    ds.reset_all_progress()