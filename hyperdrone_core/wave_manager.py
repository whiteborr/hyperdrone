import pygame
import random
import math
import logging

from settings_manager import get_setting

# Get build phase duration from settings
BUILD_PHASE_DEFAULT_DURATION_MS = get_setting("defense", "DEFENSE_BUILD_PHASE_DURATION_MS", 30000)

logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

class WaveManager:
    def __init__(self, game_controller_ref):
        self.game_controller = game_controller_ref 
        self.current_wave_number = 0
        self.is_wave_active = False 
        self.is_build_phase_active = False 
        self.current_wave_enemy_groups, self.current_group_index = [], 0 
        self.enemies_spawned_in_current_group, self.time_since_last_spawn_ms = 0, 0
        self.time_until_next_group_ms, self.build_phase_duration_ms = 0, BUILD_PHASE_DEFAULT_DURATION_MS
        self.build_phase_timer_remaining_ms, self.all_waves_cleared = 0, False 
        self._define_waves(); self.total_waves = len(self.wave_definitions)
        logger.info("WaveManager initialized.")

    def _define_waves(self):
        """
        Defines the structure of enemy waves using the new DefenseDrone types.
        """
        self.wave_definitions = [
            # Wave 1: Basic drones
            [ {"enemy_type": "defense_drone_1", "count": 8, "spawn_delay_ms": 1500, "group_delay_ms": 0} ],
            # Wave 2: More basic drones, faster
            [ {"enemy_type": "defense_drone_1", "count": 10, "spawn_delay_ms": 1200, "group_delay_ms": 0} ],
            # Wave 3: Introduce the faster drone
            [ {"enemy_type": "defense_drone_1", "count": 5, "spawn_delay_ms": 1000, "group_delay_ms": 0},
              {"enemy_type": "defense_drone_3", "count": 4, "spawn_delay_ms": 800, "group_delay_ms": 3000} ],
            # Wave 4: Introduce the tougher drone
            [ {"enemy_type": "defense_drone_2", "count": 6, "spawn_delay_ms": 1800, "group_delay_ms": 0},
              {"enemy_type": "defense_drone_1", "count": 5, "spawn_delay_ms": 1000, "group_delay_ms": 2000} ],
            # Wave 5: Mix of tough and fast
            [ {"enemy_type": "defense_drone_2", "count": 4, "spawn_delay_ms": 2000, "group_delay_ms": 0},
              {"enemy_type": "defense_drone_3", "count": 8, "spawn_delay_ms": 700, "group_delay_ms": 4000} ],
            # Wave 6: Introduce the heavily armored drone
            [ {"enemy_type": "defense_drone_4", "count": 3, "spawn_delay_ms": 3000, "group_delay_ms": 0},
              {"enemy_type": "defense_drone_1", "count": 8, "spawn_delay_ms": 1000, "group_delay_ms": 5000} ],
            # Wave 7: Armored and fast
            [ {"enemy_type": "defense_drone_4", "count": 2, "spawn_delay_ms": 2500, "group_delay_ms": 0},
              {"enemy_type": "defense_drone_3", "count": 10, "spawn_delay_ms": 600, "group_delay_ms": 4000} ],
            # Wave 8: Introduce the elite drone
            [ {"enemy_type": "defense_drone_5", "count": 5, "spawn_delay_ms": 1500, "group_delay_ms": 0},
              {"enemy_type": "defense_drone_2", "count": 5, "spawn_delay_ms": 1800, "group_delay_ms": 3000} ],
            # Wave 9: A swarm of fast drones
            [ {"enemy_type": "defense_drone_3", "count": 20, "spawn_delay_ms": 400, "group_delay_ms": 0} ],
            # Wave 10: The final assault
            [ {"enemy_type": "defense_drone_4", "count": 4, "spawn_delay_ms": 2000, "group_delay_ms": 0},
              {"enemy_type": "defense_drone_5", "count": 6, "spawn_delay_ms": 1500, "group_delay_ms": 3000},
              {"enemy_type": "defense_drone_3", "count": 8, "spawn_delay_ms": 500, "group_delay_ms": 2000} ]
        ]
        self.total_waves = len(self.wave_definitions)

    def update(self, current_time_ms, delta_time_ms):
        if self.all_waves_cleared: return

        if self.is_build_phase_active:
            self.build_phase_timer_remaining_ms -= delta_time_ms
            if self.build_phase_timer_remaining_ms <= 0:
                self.build_phase_timer_remaining_ms = 0; self._start_combat_wave_internal() 
        elif self.is_wave_active:
            if self.time_until_next_group_ms > 0:
                self.time_until_next_group_ms -= delta_time_ms
                if self.time_until_next_group_ms <= 0: self.time_until_next_group_ms = 0; self.time_since_last_spawn_ms = 0 
                return 

            if self.current_group_index < len(self.current_wave_enemy_groups):
                group = self.current_wave_enemy_groups[self.current_group_index]
                self.time_since_last_spawn_ms += delta_time_ms
                if self.enemies_spawned_in_current_group < group["count"] and self.time_since_last_spawn_ms >= group["spawn_delay_ms"]:
                    
                    spawn_grid_positions = self.game_controller.maze.ENEMY_SPAWN_GRID_POSITIONS
                    if not spawn_grid_positions: return

                    spawn_grid_pos = random.choice(spawn_grid_positions)
                    path = self.game_controller.maze.get_enemy_path_to_core(spawn_grid_pos)
                    if not path:
                        logger.error(f"WaveManager: Could not get path for spawn {spawn_grid_pos}. Skipping spawn.")
                        return

                    self.game_controller.combat_controller.enemy_manager.spawn_enemy_for_defense(
                        group["enemy_type"], 
                        spawn_grid_pos,
                        path
                    )
                    self.enemies_spawned_in_current_group += 1
                    self.time_since_last_spawn_ms = 0 

                if self.enemies_spawned_in_current_group >= group["count"]:
                    self.current_group_index += 1; self.enemies_spawned_in_current_group = 0; self.time_since_last_spawn_ms = 0
                    if self.current_group_index < len(self.current_wave_enemy_groups):
                        self.time_until_next_group_ms = self.current_wave_enemy_groups[self.current_group_index].get("group_delay_ms", 0)
            
            if self.current_group_index >= len(self.current_wave_enemy_groups) and self.game_controller.combat_controller.enemy_manager.get_active_enemies_count() == 0:
                self.is_wave_active = False; logger.info(f"WaveManager: Wave {self.current_wave_number} Cleared!")
                base_reward = get_setting("defense", "DEFENSE_WAVE_CLEAR_CORE_REWARD_BASE", 100)
                increment = get_setting("defense", "DEFENSE_WAVE_CLEAR_CORE_INCREMENT", 50)
                reward = base_reward + (self.current_wave_number - 1) * increment
                self.game_controller.drone_system.add_player_cores(reward); self.game_controller.play_sound('level_up') 
                if self.current_wave_number >= self.total_waves: self.all_waves_cleared = True 
                self._start_build_phase_internal()
    
    def reset(self):
        self.current_wave_number = 0
        self.is_wave_active = False
        self.is_build_phase_active = False
        self.all_waves_cleared = False
        logger.info("WaveManager: Reset for new Maze Defense session.")

    def start_first_build_phase(self):
        self.reset()
        self.current_wave_number = 1
        self._start_build_phase_internal(is_first_wave=True)

    def manual_start_next_wave(self):
        if not self.is_build_phase_active or self.all_waves_cleared:
            logger.warning("WaveManager: Manual wave start attempted but not in build phase or all waves cleared.")
            return
        logger.info("WaveManager: Player manually starting next wave.")
        self._start_combat_wave_internal()

    def _start_build_phase_internal(self, is_first_wave=False):
        if self.all_waves_cleared: return
        if not is_first_wave:
            self.current_wave_number = min(self.total_waves, self.current_wave_number + 1)
        
        self.is_build_phase_active = True
        self.build_phase_timer_remaining_ms = self.build_phase_duration_ms
        self.game_controller.is_build_phase = True
        if self.game_controller.ui_manager.build_menu:
            self.game_controller.ui_manager.build_menu.activate()
        
        self.game_controller.set_story_message(f"Prepare defenses! Wave {self.current_wave_number}/{self.total_waves} incoming.", self.build_phase_duration_ms)
        logger.info(f"WaveManager: Build phase started for wave {self.current_wave_number}.")
        if is_first_wave: logger.info("WaveManager: First build phase started.")
        
    def _start_combat_wave_internal(self):
        if self.current_wave_number > self.total_waves:
            self.all_waves_cleared = True
            return
            
        self.is_build_phase_active = False
        self.is_wave_active = True
        self.game_controller.is_build_phase = False
        if self.game_controller.ui_manager.build_menu:
            self.game_controller.ui_manager.build_menu.deactivate()
        
        self.current_wave_enemy_groups = self.wave_definitions[self.current_wave_number - 1]
        self.current_group_index = 0
        self.enemies_spawned_in_current_group = 0
        self.time_since_last_spawn_ms = 0
        self.time_until_next_group_ms = 0
        self.game_controller.set_story_message(f"Wave {self.current_wave_number}/{self.total_waves} Incoming!")
        logger.info(f"WaveManager: Starting Combat Wave {self.current_wave_number} of {self.total_waves}")

    def get_current_wave_display(self):
        if self.all_waves_cleared: return "All Waves Cleared!"
        wave_info = f"Wave {self.current_wave_number}/{self.total_waves}"
        if self.is_build_phase_active: return f"Build Phase - {wave_info}"
        elif self.is_wave_active: return wave_info
        else: return f"Prepare for {wave_info}"

    def get_build_phase_time_remaining_display(self):
        if not self.is_build_phase_active: return ""
        seconds_remaining = self.build_phase_timer_remaining_ms / 1000.0
        return f"{max(0, seconds_remaining):.1f}s"