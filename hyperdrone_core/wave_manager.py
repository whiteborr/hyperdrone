# hyperdrone_core/wave_manager.py
import pygame
import random
import math 

import game_settings as gs 

try:
    BUILD_PHASE_DEFAULT_DURATION_MS = gs.get_game_setting("DEFENSE_BUILD_PHASE_DURATION_MS", 30000)
except AttributeError: 
    BUILD_PHASE_DEFAULT_DURATION_MS = 30000 

class WaveManager:
    def __init__(self, game_controller_ref):
        """
        Initializes the WaveManager.
        Args:
            game_controller_ref: Reference to the main GameController.
        """
        self.game_controller = game_controller_ref
        self.current_wave_number = 0
        self.wave_definitions = []  
        self.is_wave_active = False 
        self.is_build_phase_active = False

        self.current_wave_enemy_groups = [] 
        self.current_group_index = 0
        self.enemies_spawned_in_current_group = 0
        self.time_since_last_spawn_ms = 0
        self.time_until_next_group_ms = 0 

        self._define_waves() 

        self.build_phase_duration_ms = BUILD_PHASE_DEFAULT_DURATION_MS
        self.build_phase_timer_remaining_ms = 0

        self.total_waves = len(self.wave_definitions)
        self.all_waves_cleared = False
        print(f"WaveManager initialized with {self.total_waves} wave definitions.")

    def _define_waves(self):
        """
        Defines the properties of each enemy wave.
        Each wave is a list of groups.
        Each group: {'enemy_type': str, 'count': int, 'spawn_delay_ms': int, 'group_delay_ms': int (delay before this group starts)}
        """
        self.wave_definitions = [
            # Wave 1: Simple start
            [ 
                {"enemy_type": "standard_drone", "count": 3, "spawn_delay_ms": 1500, "group_delay_ms": 0},
            ],
            # Wave 2: More standard drones
            [
                {"enemy_type": "standard_drone", "count": 5, "spawn_delay_ms": 1200, "group_delay_ms": 0},
            ],
            # Wave 3: Introduce fast drones
            [
                {"enemy_type": "standard_drone", "count": 4, "spawn_delay_ms": 1000, "group_delay_ms": 0},
                {"enemy_type": "fast_drone", "count": 2, "spawn_delay_ms": 800, "group_delay_ms": 3000}, 
            ],
            # Wave 4: Mix them up
            [
                {"enemy_type": "standard_drone", "count": 3, "spawn_delay_ms": 900, "group_delay_ms": 0},
                {"enemy_type": "fast_drone", "count": 3, "spawn_delay_ms": 700, "group_delay_ms": 2000},
                {"enemy_type": "standard_drone", "count": 3, "spawn_delay_ms": 900, "group_delay_ms": 2000},
            ],
            # Wave 5: Introduce armored drones
            [
                {"enemy_type": "armored_drone", "count": 2, "spawn_delay_ms": 2500, "group_delay_ms": 0},
                {"enemy_type": "standard_drone", "count": 5, "spawn_delay_ms": 800, "group_delay_ms": 3000},
                {"enemy_type": "fast_drone", "count": 4, "spawn_delay_ms": 600, "group_delay_ms": 2000},
            ],
            # Wave 6: Sentinels appear
            [
                {"enemy_type": "sentinel_drone", "count": 1, "spawn_delay_ms": 1000, "group_delay_ms": 0},
                {"enemy_type": "standard_drone", "count": 4, "spawn_delay_ms": 1000, "group_delay_ms": 4000},
            ],
            # Wave 7: More Sentinels and fast drones
            [
                {"enemy_type": "sentinel_drone", "count": 2, "spawn_delay_ms": 1500, "group_delay_ms": 0},
                {"enemy_type": "fast_drone", "count": 5, "spawn_delay_ms": 700, "group_delay_ms": 3000},
            ],
            # Wave 8: Tougher mix
            [
                {"enemy_type": "armored_drone", "count": 3, "spawn_delay_ms": 1800, "group_delay_ms": 0},
                {"enemy_type": "sentinel_drone", "count": 2, "spawn_delay_ms": 1200, "group_delay_ms": 4000},
                {"enemy_type": "standard_drone", "count": 6, "spawn_delay_ms": 700, "group_delay_ms": 3000},
            ],
             # Wave 9: Chaos
            [
                {"enemy_type": "fast_drone", "count": 8, "spawn_delay_ms": 500, "group_delay_ms": 0},
                {"enemy_type": "sentinel_drone", "count": 2, "spawn_delay_ms": 1500, "group_delay_ms": 2000},
                {"enemy_type": "armored_drone", "count": 2, "spawn_delay_ms": 2000, "group_delay_ms": 2000},
            ],
            # Wave 10: Final wave example (can be much larger)
            [
                {"enemy_type": "armored_drone", "count": 4, "spawn_delay_ms": 1500, "group_delay_ms": 0},
                {"enemy_type": "sentinel_drone", "count": 3, "spawn_delay_ms": 1200, "group_delay_ms": 3000},
                {"enemy_type": "fast_drone", "count": 6, "spawn_delay_ms": 400, "group_delay_ms": 2000},
                {"enemy_type": "standard_drone", "count": 10, "spawn_delay_ms": 600, "group_delay_ms": 1000},
            ]
        ]
        self.total_waves = len(self.wave_definitions)

    def start_first_build_phase(self):
        """Initiates the very first build phase of the defense mode."""
        print("WaveManager: Starting initial build phase.")
        self.current_wave_number = 0 
        self.all_waves_cleared = False
        self._start_build_phase_internal()

    def _start_build_phase_internal(self):
        """Internal logic to start any build phase."""
        self.is_build_phase_active = True
        self.is_wave_active = False
        self.build_phase_timer_remaining_ms = self.build_phase_duration_ms
        self.game_controller.is_build_phase = True 

        wave_display_next = self.current_wave_number + 1
        if self.all_waves_cleared:
            self.game_controller.set_story_message("All Waves Cleared! Reactor Secured!", 5000)
        elif self.current_wave_number == 0: 
            self.game_controller.set_story_message(f"Prepare defenses! Wave {wave_display_next} incoming.", 5000)
        else:
            self.game_controller.set_story_message(f"Wave {self.current_wave_number} Cleared! Prepare for Wave {wave_display_next}!", 5000)
        
        if hasattr(self.game_controller, 'play_sound'):
            self.game_controller.play_sound('ui_confirm', 0.5) 

    def manual_start_next_wave(self):
        """Called by player input (e.g., pressing SPACE during build phase)."""
        if self.is_build_phase_active and not self.all_waves_cleared:
            print("WaveManager: Player manually starting next wave.")
            self.build_phase_timer_remaining_ms = 0 
            if hasattr(self.game_controller, 'play_sound'):
                self.game_controller.play_sound('ui_confirm', 0.7)
            # The update loop will detect timer at 0 and call _start_combat_wave_internal
        else:
            if hasattr(self.game_controller, 'play_sound'):
                self.game_controller.play_sound('ui_denied', 0.5)


    def _start_combat_wave_internal(self):
        """Starts the next combat wave's logic."""
        if self.all_waves_cleared:
            print("WaveManager: All waves already cleared. Cannot start new combat wave.")
            return

        self.is_build_phase_active = False
        self.game_controller.is_build_phase = False 
        
        self.current_wave_number += 1
        if self.current_wave_number > self.total_waves:
            self.all_waves_cleared = True
            self.is_wave_active = False
            print("WaveManager: All waves successfully cleared!")
            self._start_build_phase_internal() 
            if hasattr(self.game_controller, 'handle_maze_defense_victory'): 
                self.game_controller.handle_maze_defense_victory()
            return

        print(f"WaveManager: Starting Combat Wave {self.current_wave_number}")
        self.game_controller.set_story_message(f"Wave {self.current_wave_number} Incoming!", 3000)
        if hasattr(self.game_controller, 'play_sound'):
            self.game_controller.play_sound('vault_alarm', 0.6) 

        self.current_wave_enemy_groups = list(self.wave_definitions[self.current_wave_number - 1]) 
        self.current_group_index = 0
        self.enemies_spawned_in_current_group = 0
        self.time_since_last_spawn_ms = 0 
        self.time_until_next_group_ms = 0 
        
        if self.current_wave_enemy_groups: 
            self.time_until_next_group_ms = self.current_wave_enemy_groups[0].get("group_delay_ms", 0)
        
        self.is_wave_active = True

    def update(self, current_time_ms, delta_time_ms):
        """
        Updates the wave manager state, handles build phase timer, and enemy spawning.
        """
        if self.all_waves_cleared:
            return

        if self.is_build_phase_active:
            self.build_phase_timer_remaining_ms -= delta_time_ms
            if self.build_phase_timer_remaining_ms <= 0:
                self.build_phase_timer_remaining_ms = 0
                self._start_combat_wave_internal() 
        
        elif self.is_wave_active:
            if self.time_until_next_group_ms > 0:
                self.time_until_next_group_ms -= delta_time_ms
                if self.time_until_next_group_ms <= 0:
                    self.time_until_next_group_ms = 0
                    self.time_since_last_spawn_ms = 0 
                return 

            if self.current_group_index < len(self.current_wave_enemy_groups):
                current_group = self.current_wave_enemy_groups[self.current_group_index]
                
                self.time_since_last_spawn_ms += delta_time_ms
                if self.enemies_spawned_in_current_group < current_group["count"] and \
                   self.time_since_last_spawn_ms >= current_group["spawn_delay_ms"]:
                    
                    # Corrected key from "type" to "enemy_type"
                    enemy_type = current_group["enemy_type"] 
                    
                    spawn_points = self.game_controller.get_enemy_spawn_points_for_defense() 
                    if not spawn_points:
                        print("WaveManager: CRITICAL - No spawn points defined for defense mode!")
                        spawn_point = (50, 50) 
                    else:
                        spawn_point = random.choice(spawn_points)

                    if hasattr(self.game_controller.enemy_manager, 'spawn_enemy_for_defense'):
                        self.game_controller.enemy_manager.spawn_enemy_for_defense(
                            enemy_type, 
                            spawn_point, 
                            self.game_controller.core_reactor 
                        )
                    else:
                        print(f"WaveManager: EnemyManager missing 'spawn_enemy_for_defense'. Cannot spawn {enemy_type}.")

                    self.enemies_spawned_in_current_group += 1
                    self.time_since_last_spawn_ms = 0 

                if self.enemies_spawned_in_current_group >= current_group["count"]:
                    self.current_group_index += 1 
                    self.enemies_spawned_in_current_group = 0
                    self.time_since_last_spawn_ms = 0
                    if self.current_group_index < len(self.current_wave_enemy_groups):
                        self.time_until_next_group_ms = self.current_wave_enemy_groups[self.current_group_index].get("group_delay_ms", 0)

            if self.current_group_index >= len(self.current_wave_enemy_groups) and \
               self.game_controller.enemy_manager.get_active_enemies_count() == 0:
                self.is_wave_active = False
                print(f"WaveManager: Wave {self.current_wave_number} Cleared of enemies!")
                cores_reward = gs.get_game_setting("DEFENSE_WAVE_CLEAR_CORE_REWARD_BASE", 100) + \
                               self.current_wave_number * gs.get_game_setting("DEFENSE_WAVE_CLEAR_CORE_INCREMENT", 50)
                self.game_controller.drone_system.add_player_cores(cores_reward)
                self.game_controller.play_sound('level_up') 

                if self.current_wave_number >= self.total_waves:
                    self.all_waves_cleared = True
                
                self._start_build_phase_internal() 

    def get_current_wave_display(self):
        if self.all_waves_cleared:
            return "All Waves Cleared!"
        if self.current_wave_number == 0 and self.is_build_phase_active: 
            return f"Prepare for Wave 1"
        if self.is_build_phase_active:
            return f"Prepare for Wave {self.current_wave_number + 1}/{self.total_waves}"
        return f"Wave: {self.current_wave_number}/{self.total_waves}"

    def get_build_phase_time_remaining_display(self):
        if self.is_build_phase_active and not self.all_waves_cleared:
            seconds = math.ceil(max(0, self.build_phase_timer_remaining_ms / 1000))
            return f"Build Time: {int(seconds)}s"
        return ""

    def reset(self):
        """Resets the wave manager for a new game of Maze Defense."""
        self.current_wave_number = 0
        self.is_wave_active = False
        self.is_build_phase_active = False
        self.current_wave_enemy_groups = []
        self.current_group_index = 0
        self.enemies_spawned_in_current_group = 0
        self.time_since_last_spawn_ms = 0
        self.time_until_next_group_ms = 0
        self.build_phase_timer_remaining_ms = 0
        self.all_waves_cleared = False
        print("WaveManager: Reset.")

