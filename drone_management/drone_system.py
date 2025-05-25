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

class DroneSystem: 
    def __init__(self): 
        self._ensure_data_dir_exists() 
        self.unlock_data = self._load_unlocks() 

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
            "unlocked_lore_codex_entries": [] 
        } 

        if not os.path.exists(UNLOCKS_FILE_PATH): 
            print(f"DroneSystem: '{UNLOCKS_FILE_PATH}' not found. Creating default unlock data.") 
            self._save_unlocks(default_data) 
            return default_data 

        try: 
            with open(UNLOCKS_FILE_PATH, 'r') as f: 
                data = json.load(f) 
                for key, value in default_data.items(): 
                    data.setdefault(key, value) 

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
                return data 
        except (IOError, json.JSONDecodeError) as e: 
            print(f"DroneSystem: Error loading or parsing '{UNLOCKS_FILE_PATH}': {e}. Returning default and attempting to re-save.") 
            self._save_unlocks(default_data) 
            return default_data 

    def _save_unlocks(self, data_to_save=None): 
        self._ensure_data_dir_exists() 
        current_data_to_save = data_to_save if data_to_save is not None else self.unlock_data 
        try: 
            with open(UNLOCKS_FILE_PATH, 'w') as f: 
                json.dump(current_data_to_save, f, indent=2) 
        except IOError as e: 
            print(f"DroneSystem: Error saving unlock data to '{UNLOCKS_FILE_PATH}': {e}") 

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
        newly_unlocked = self._check_for_passive_unlocks() 
        if not newly_unlocked: 
            self._save_unlocks() 
        if newly_unlocked: 
             print(f"DroneSystem: Player level set to {level}. New unlocks: {newly_unlocked}") 
        return newly_unlocked 

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
        if boss_name not in self.unlock_data.get("bosses_defeated", []): 
            self.unlock_data.setdefault("bosses_defeated", []).append(boss_name) 
            newly_unlocked = self._check_for_passive_unlocks() 
            if not newly_unlocked: self._save_unlocks() 
            if newly_unlocked: 
                 print(f"DroneSystem: Boss '{boss_name}' defeated. New unlocks: {newly_unlocked}") 
            return newly_unlocked 
        return [] 

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
            print(f"DroneSystem: Passive check unlocked: {newly_unlocked_this_check}") 
        return newly_unlocked_this_check 

    def attempt_unlock_drone_with_cores(self, drone_id): 
        if self.is_drone_unlocked(drone_id): 
            return True 

        config = self.get_drone_config(drone_id) 
        if not config: return False 

        unlock_condition = config.get("unlock_condition", {}) 
        if unlock_condition.get("type") != "cores": 
            return False 

        cost = unlock_condition.get("value", float('inf')) 
        if self.spend_player_cores(cost): 
            unlocked_list = self.unlock_data.setdefault("unlocked_drones", []) 
            if drone_id not in unlocked_list: 
                unlocked_list.append(drone_id) 
            self._save_unlocks() 
            print(f"DroneSystem: Drone '{drone_id}' unlocked by spending {cost} cores.") 
            return True 
        return False 

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
        return num_collected >= TOTAL_CORE_FRAGMENTS_NEEDED 
    
    def reset_collected_fragments_in_storage(self):
        if "collected_core_fragments" in self.unlock_data:
            self.unlock_data["collected_core_fragments"] = []
            # self._save_unlocks() # Save will be handled by initialize_game_session
            print("DroneSystem: Persisted collected core fragments have been reset for new game session.")
        else:
            self.unlock_data["collected_core_fragments"] = []
            # self._save_unlocks() 
            print("DroneSystem: Persisted collected_core_fragments key initialized and reset for new game session.")

    def reset_architect_vault_status(self):
        """Resets the Architect's Vault completion status for a new game session."""
        if "architect_vault_completed" in self.unlock_data:
            self.unlock_data["architect_vault_completed"] = False
            print("DroneSystem: Architect's Vault completion status reset for new game session.")
        else: # Ensure the key exists even if it wasn't there before
            self.unlock_data["architect_vault_completed"] = False
            print("DroneSystem: Architect's Vault completion status initialized and reset for new game session.")
        # Note: _save_unlocks() will be called by initialize_game_session after all resets.


    def mark_architect_vault_completed(self, completed_successfully=True): 
        self.unlock_data["architect_vault_completed"] = completed_successfully 
        if completed_successfully: 
            print("DroneSystem: Architect's Vault completed successfully!") 
            if ARCHITECT_REWARD_BLUEPRINT_ID: self.unlock_blueprint(ARCHITECT_REWARD_BLUEPRINT_ID) 
            if ARCHITECT_REWARD_LORE_ID: self.unlock_lore_entry(ARCHITECT_REWARD_LORE_ID) 
        else: 
            print("DroneSystem: Architect's Vault attempt failed.") 
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

        if newly_unlocked_blueprint or newly_unlocked_drone_via_blueprint: 
            self._save_unlocks() 
        return newly_unlocked_blueprint or newly_unlocked_drone_via_blueprint 

    def has_unlocked_blueprint(self, blueprint_id): 
        return blueprint_id in self.unlock_data.get("unlocked_blueprints", []) 

    def unlock_lore_entry(self, lore_id): 
        if not lore_id: return False 
        unlocked_lore_list = self.unlock_data.setdefault("unlocked_lore_codex_entries", []) 
        if lore_id not in unlocked_lore_list: 
            unlocked_lore_list.append(lore_id) 
            self._save_unlocks() 
            print(f"DroneSystem: Lore Codex Entry '{lore_id}' unlocked!") 
            return True 
        return False 

    def has_unlocked_lore(self, lore_id): 
        return lore_id in self.unlock_data.get("unlocked_lore_codex_entries", []) 

    def reset_all_progress(self): 
        print("DroneSystem: Resetting all player progress to default.") 
        default_data = {
            "unlocked_drones": ["DRONE"], "selected_drone": "DRONE",
            "player_level": 1, "bosses_defeated": [], "player_cores": 0,
            "collected_core_fragments": [], "architect_vault_completed": False,
            "unlocked_blueprints": [], "unlocked_lore_codex_entries": []
        } 
        self.unlock_data = default_data 
        self._save_unlocks() 
        print("DroneSystem: All progress reset.")

if __name__ == '__main__': #
    print("DroneSystem: Running self-test...") #
    # This self-test block might need adjustment for standalone execution if game_settings
    # isn't fully available or if drone_configs isn't in the path.
    # For package structure, this test would typically be run via a test runner
    # that sets up the correct Python path.
    try: #
        # from ..game_settings import PLAYER_MAX_HEALTH, PLAYER_SPEED, ROTATION_SPEED # Example of relative import if testing from package
        # from .drone_configs import DRONE_DATA # Example
        pass #
    except ImportError: #
        print("Self-test: Could not import sibling/parent modules for full context. Limited test.") #

    ds = DroneSystem() #
    print(f"DroneSystem Test: Initial selected drone: {ds.get_selected_drone_id()}") #
    # Example: check a drone ID from your DRONE_DATA
    if "VANTIS" in DRONE_DATA: #
        print(f"DroneSystem Test: Is VANTIS unlocked? {ds.is_drone_unlocked('VANTIS')}") #
    ds.set_player_level(5) #
    print(f"DroneSystem Test: Player level after set: {ds.get_player_level()}") #
    ds.add_player_cores(500) #
    ds._save_unlocks() # Explicit save after add_player_cores for testing this behavior
    print(f"DroneSystem Test: Player cores after add: {ds.get_player_cores()}") #
    ds.spend_player_cores(100) #
    print(f"DroneSystem Test: Player cores after spend: {ds.get_player_cores()}") #
