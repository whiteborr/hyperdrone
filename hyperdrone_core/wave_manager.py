# hyperdrone_core/wave_manager.py
import pygame
import random
import math
import logging # Import the logging module

import game_settings as gs

# Attempt to get build phase duration from game settings, with a fallback
try:
    BUILD_PHASE_DEFAULT_DURATION_MS = gs.get_game_setting("DEFENSE_BUILD_PHASE_DURATION_MS", 30000)
except (AttributeError, NameError): # Fallback if gs or get_game_setting isn't fully available at import time
    BUILD_PHASE_DEFAULT_DURATION_MS = 30000

# Configure basic logging for this module
logger = logging.getLogger(__name__)
# BasicConfig should ideally be called once at the application entry point (e.g., main.py)
# Adding a check to avoid reconfiguring if already done.
if not logging.getLogger().hasHandlers(): # Check if the root logger already has handlers
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


class WaveManager:
    """
    Manages the sequence of enemy waves for the Maze Defense mode.
    Handles build phases, enemy spawning schedules, and wave progression.
    """
    def __init__(self, game_controller_ref):
        """
        Initializes the WaveManager.
        Args:
            game_controller_ref: Reference to the main GameController instance.
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
        logger.info("WaveManager initialized.")

    def _define_waves(self):
        """
        Defines the structure of enemy waves. Each wave is a list of enemy groups.
        Each group specifies:
            - "enemy_type": Key from EnemyManager's defense_enemy_configs.
            - "count": Number of enemies in this group.
            - "spawn_delay_ms": Delay between spawning individual enemies in this group.
            - "group_delay_ms": Delay *before* this group starts spawning (after previous group finishes).
        """
        self.wave_definitions = [
            # Wave 1
            [
                {"enemy_type": "standard_drone", "count": 3, "spawn_delay_ms": 1500, "group_delay_ms": 0},
            ],
            # Wave 2
            [
                {"enemy_type": "standard_drone", "count": 5, "spawn_delay_ms": 1200, "group_delay_ms": 0},
            ],
            # Wave 3
            [
                {"enemy_type": "standard_drone", "count": 4, "spawn_delay_ms": 1000, "group_delay_ms": 0},
                {"enemy_type": "fast_drone", "count": 2, "spawn_delay_ms": 800, "group_delay_ms": 3000},
            ],
            # Wave 4
            [
                {"enemy_type": "standard_drone", "count": 3, "spawn_delay_ms": 900, "group_delay_ms": 0},
                {"enemy_type": "fast_drone", "count": 3, "spawn_delay_ms": 700, "group_delay_ms": 2000},
                {"enemy_type": "standard_drone", "count": 3, "spawn_delay_ms": 900, "group_delay_ms": 2000},
            ],
            # Wave 5
            [
                {"enemy_type": "armored_drone", "count": 2, "spawn_delay_ms": 2500, "group_delay_ms": 0},
                {"enemy_type": "standard_drone", "count": 5, "spawn_delay_ms": 800, "group_delay_ms": 3000},
                {"enemy_type": "fast_drone", "count": 4, "spawn_delay_ms": 600, "group_delay_ms": 2000},
            ],
            # Wave 6 - Introducing Sentinels
            [
                {"enemy_type": "sentinel_drone", "count": 1, "spawn_delay_ms": 1000, "group_delay_ms": 0},
                {"enemy_type": "standard_drone", "count": 4, "spawn_delay_ms": 1000, "group_delay_ms": 4000},
            ],
            # Wave 7
            [
                {"enemy_type": "sentinel_drone", "count": 2, "spawn_delay_ms": 1500, "group_delay_ms": 0},
                {"enemy_type": "fast_drone", "count": 5, "spawn_delay_ms": 700, "group_delay_ms": 3000},
            ],
            # Wave 8
            [
                {"enemy_type": "armored_drone", "count": 3, "spawn_delay_ms": 1800, "group_delay_ms": 0},
                {"enemy_type": "sentinel_drone", "count": 2, "spawn_delay_ms": 1200, "group_delay_ms": 4000},
                {"enemy_type": "standard_drone", "count": 6, "spawn_delay_ms": 700, "group_delay_ms": 3000},
            ],
            # Wave 9
            [
                {"enemy_type": "fast_drone", "count": 8, "spawn_delay_ms": 500, "group_delay_ms": 0},
                {"enemy_type": "sentinel_drone", "count": 2, "spawn_delay_ms": 1500, "group_delay_ms": 2000},
                {"enemy_type": "armored_drone", "count": 2, "spawn_delay_ms": 2000, "group_delay_ms": 2000},
            ],
            # Wave 10 - Final Wave Example
            [
                {"enemy_type": "armored_drone", "count": 4, "spawn_delay_ms": 1500, "group_delay_ms": 0},
                {"enemy_type": "sentinel_drone", "count": 3, "spawn_delay_ms": 1200, "group_delay_ms": 3000},
                {"enemy_type": "fast_drone", "count": 6, "spawn_delay_ms": 400, "group_delay_ms": 2000},
                {"enemy_type": "standard_drone", "count": 10, "spawn_delay_ms": 600, "group_delay_ms": 1000},
            ]
        ]
        self.total_waves = len(self.wave_definitions)

    def start_first_build_phase(self):
        """Initiates the very first build phase when Maze Defense mode starts."""
        self.current_wave_number = 0 
        self.all_waves_cleared = False
        self._start_build_phase_internal()
        logger.info("WaveManager: First build phase started.")

    def _start_build_phase_internal(self):
        """
        Internal logic to start a build phase.
        If all waves are already cleared, it triggers the victory condition.
        """
        if self.all_waves_cleared: 
            if hasattr(self.game_controller, 'handle_maze_defense_victory'):
                self.game_controller.handle_maze_defense_victory()
            self.is_build_phase_active = False 
            if hasattr(self.game_controller, 'is_build_phase'): 
                self.game_controller.is_build_phase = False
            self.is_wave_active = False
            logger.info("WaveManager: All waves cleared, victory handled.")
            return

        self.is_build_phase_active = True
        self.is_wave_active = False 
        self.build_phase_timer_remaining_ms = self.build_phase_duration_ms
        if hasattr(self.game_controller, 'is_build_phase'):
            self.game_controller.is_build_phase = True

        wave_display_next = self.current_wave_number + 1
        if self.current_wave_number == 0: 
            self.game_controller.set_story_message(f"Prepare defenses! Wave {wave_display_next}/{self.total_waves} incoming.", 5000)
        else: 
            self.game_controller.set_story_message(f"Wave {self.current_wave_number} Cleared! Prepare for Wave {wave_display_next}/{self.total_waves}!", 5000)

        if hasattr(self.game_controller, 'play_sound'):
            self.game_controller.play_sound('ui_confirm', 0.5)
        logger.info(f"WaveManager: Build phase started for wave {wave_display_next}.")

    def manual_start_next_wave(self):
        """
        Allows the player to manually start the next combat wave.
        """
        if self.is_build_phase_active and not self.all_waves_cleared:
            self.build_phase_timer_remaining_ms = 0 
            if hasattr(self.game_controller, 'play_sound'):
                self.game_controller.play_sound('ui_confirm', 0.7)
            logger.info("WaveManager: Player manually starting next wave.")
        else: 
            if hasattr(self.game_controller, 'play_sound'):
                self.game_controller.play_sound('ui_denied', 0.5)
            logger.warning("WaveManager: Manual wave start attempted but not in build phase or all waves cleared.")


    def _start_combat_wave_internal(self):
        """
        Internal logic to start the next combat wave.
        """
        if self.all_waves_cleared: 
            logger.info("WaveManager: All waves already cleared. Cannot start new combat wave.")
            if hasattr(self.game_controller, 'handle_maze_defense_victory'): 
                self.game_controller.handle_maze_defense_victory()
            return

        self.is_build_phase_active = False
        if hasattr(self.game_controller, 'is_build_phase'):
            self.game_controller.is_build_phase = False

        self.current_wave_number += 1 
        
        if self.current_wave_number > self.total_waves: 
            self.all_waves_cleared = True
            self.is_wave_active = False
            logger.info("WaveManager: All defined waves successfully cleared!")
            self._start_build_phase_internal() 
            return

        logger.info(f"WaveManager: Starting Combat Wave {self.current_wave_number} of {self.total_waves}")
        self.game_controller.set_story_message(f"Wave {self.current_wave_number}/{self.total_waves} Incoming!", 3000)
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
                    
                    enemy_type = current_group["enemy_type"] 
                    spawn_points = self.game_controller.get_enemy_spawn_points_for_defense() 
                    if not spawn_points:
                        logger.critical("WaveManager: No spawn points defined for defense mode! Using fallback (50,50).")
                        spawn_point = (50, 50) 
                    else:
                        spawn_point = random.choice(spawn_points) 

                    reactor_target = None
                    if self.game_controller.combat_controller and hasattr(self.game_controller.combat_controller, 'core_reactor'):
                        reactor_target = self.game_controller.combat_controller.core_reactor
                    else:
                        logger.error("WaveManager: CombatController or core_reactor not found on GameController. Cannot set enemy target for defense.")
                    
                    if self.game_controller.combat_controller and \
                       hasattr(self.game_controller.combat_controller, 'enemy_manager') and \
                       hasattr(self.game_controller.combat_controller.enemy_manager, 'spawn_enemy_for_defense'):
                        self.game_controller.combat_controller.enemy_manager.spawn_enemy_for_defense(
                            enemy_type, 
                            spawn_point, 
                            reactor_target 
                        )
                    else:
                        logger.error(f"WaveManager: Could not spawn enemy. CombatController, EnemyManager, or spawn_enemy_for_defense method is missing.")

                    self.enemies_spawned_in_current_group += 1
                    self.time_since_last_spawn_ms = 0 

                if self.enemies_spawned_in_current_group >= current_group["count"]:
                    self.current_group_index += 1 
                    self.enemies_spawned_in_current_group = 0 
                    self.time_since_last_spawn_ms = 0
                    if self.current_group_index < len(self.current_wave_enemy_groups):
                        self.time_until_next_group_ms = self.current_wave_enemy_groups[self.current_group_index].get("group_delay_ms", 0)
            
            active_enemies = 0
            if self.game_controller.combat_controller and self.game_controller.combat_controller.enemy_manager:
                active_enemies = self.game_controller.combat_controller.enemy_manager.get_active_enemies_count()

            if self.current_group_index >= len(self.current_wave_enemy_groups) and active_enemies == 0:
                self.is_wave_active = False 
                logger.info(f"WaveManager: Wave {self.current_wave_number} Cleared of enemies!")
                
                cores_reward = gs.get_game_setting("DEFENSE_WAVE_CLEAR_CORE_REWARD_BASE", 100) + \
                               (self.current_wave_number -1) * gs.get_game_setting("DEFENSE_WAVE_CLEAR_CORE_INCREMENT", 50)
                self.game_controller.drone_system.add_player_cores(cores_reward)
                self.game_controller.play_sound('level_up') 

                if self.current_wave_number >= self.total_waves:
                    self.all_waves_cleared = True 
                
                self._start_build_phase_internal() 

    def get_current_wave_display(self):
        """Returns a string for displaying the current wave status."""
        if self.all_waves_cleared:
            return "All Waves Cleared!"
        if self.current_wave_number == 0 and self.is_build_phase_active: 
            return f"Prepare for Wave 1/{self.total_waves}"
        if self.is_build_phase_active: 
            return f"Prepare for Wave {self.current_wave_number + 1}/{self.total_waves}"
        return f"Wave: {self.current_wave_number}/{self.total_waves}"

    def get_build_phase_time_remaining_display(self):
        """Returns a string for the build phase timer."""
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
        logger.info("WaveManager: Reset for new Maze Defense session.")
