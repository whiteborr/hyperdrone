# hyperdrone_core/enemy_manager.py
import pygame
import random
from entities import Enemy, SentinelDrone # Ensure SentinelDrone is imported
import game_settings as gs
from game_settings import TILE_SIZE 

class EnemyManager:
    def __init__(self, game_controller_ref):
        """
        Initializes the EnemyManager.
        Args:
            game_controller_ref: A reference to the main GameController instance.
                                 This is used to access game state, maze, player, sounds, etc.
        """
        self.game_controller = game_controller_ref
        self.enemies = pygame.sprite.Group() # Group to hold all active enemy sprites

        # Define base stats and configurations for different enemy types,
        # primarily used when spawning enemies for the Maze Defense mode.
        # These could be further expanded or loaded from external config files.
        self.defense_enemy_configs = {
            "standard_drone": {
                "class": Enemy, # The class to instantiate for this enemy type
                "sprite_path": gs.get_game_setting("REGULAR_ENEMY_SPRITE_PATH"),
                "health": gs.get_game_setting("ENEMY_HEALTH", 100),
                "speed": gs.get_game_setting("ENEMY_SPEED", 1.5),
                "shoot_cooldown": gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500),
                "contact_damage": 25 # Damage dealt by ramming the reactor in defense mode
            },
            "fast_drone": { 
                "class": Enemy,
                "sprite_path": gs.get_game_setting("REGULAR_ENEMY_SPRITE_PATH"), # Consider a distinct sprite
                "health": int(gs.get_game_setting("ENEMY_HEALTH", 100) * 0.7), # Less health
                "speed": gs.get_game_setting("ENEMY_SPEED", 1.5) * 1.5, # Faster
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.8), # Shoots faster
                "contact_damage": 20
            },
            "armored_drone": { 
                "class": Enemy,
                "sprite_path": gs.get_game_setting("REGULAR_ENEMY_SPRITE_PATH"), # Consider a distinct sprite
                "health": int(gs.get_game_setting("ENEMY_HEALTH", 100) * 1.8), # More health
                "speed": gs.get_game_setting("ENEMY_SPEED", 1.5) * 0.7, # Slower
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 1.2), # Shoots slower
                "contact_damage": 35
            },
            "sentinel_drone": {
                "class": SentinelDrone, # Uses the SentinelDrone class
                "sprite_path": gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH"),
                "health": gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75),
                "speed": gs.get_game_setting("SENTINEL_DRONE_SPEED", 3.0),
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.7), 
                "contact_damage": 30
            }
            # More enemy types can be added here for defense mode variety.
        }


    def spawn_enemies_for_level(self, level):
        """
        Spawns enemies for a given level in the standard game mode (procedural maze).
        This method uses the GameController's _get_safe_spawn_point, which is
        aware of the current maze type (procedural or tile-based).
        """
        self.enemies.empty() # Clear any existing enemies
        
        # Determine number of enemies based on level, with a cap
        num_enemies = min(level + 1, 7) 
        enemy_shoot_sound = self.game_controller.sounds.get('enemy_shoot')
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        
        # Example logic for spawning different enemy types based on level
        if 4 <= level <= 6: 
            print(f"EnemyManager: Spawning SentinelDrones for level {level}")
            enemy_sprite_path = gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH")
            for _ in range(num_enemies):
                # _get_safe_spawn_point will work with either Maze or MazeChapter2
                abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.6, TILE_SIZE * 0.6) 
                if abs_x is not None:
                    enemy = SentinelDrone(x=abs_x, y=abs_y,
                                          player_bullet_size_base=player_bullet_size_setting, 
                                          shoot_sound=enemy_shoot_sound,
                                          sprite_path=enemy_sprite_path, 
                                          target_player_ref=self.game_controller.player)
                    self.enemies.add(enemy)
                else:
                    print(f"EnemyManager: Could not find safe spawn for SentinelDrone on level {level}.")
        else: 
            print(f"EnemyManager: Spawning standard TR-3B enemies for level {level}")
            regular_enemy_sprite = gs.get_game_setting("REGULAR_ENEMY_SPRITE_PATH")
            for _ in range(num_enemies):
                abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7) 
                if abs_x is not None:
                    enemy = Enemy(abs_x, abs_y, player_bullet_size_setting,
                                  shoot_sound=enemy_shoot_sound,
                                  sprite_path=regular_enemy_sprite,
                                  target_player_ref=self.game_controller.player)
                    self.enemies.add(enemy)
                else:
                    print(f"EnemyManager: Could not find safe spawn for standard enemy on level {level}.")

    def spawn_prototype_drones(self, count, far_from_player=False):
        """
        Spawns prototype drones, typically for the Architect's Vault.
        Uses _get_safe_spawn_point which is maze-type aware.
        """
        if not self.game_controller.maze: 
            print("EnemyManager: Cannot spawn prototype drones, maze not initialized.")
            return

        enemy_shoot_sound = self.game_controller.sounds.get('enemy_shoot')
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        prototype_sprite = gs.get_game_setting("PROTOTYPE_DRONE_SPRITE_PATH")

        for _ in range(count):
            abs_x, abs_y = self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7) 
            if abs_x is not None:
                proto_drone = Enemy(abs_x, abs_y, player_bullet_size_setting,
                                    shoot_sound=enemy_shoot_sound,
                                    sprite_path=prototype_sprite,
                                    target_player_ref=self.game_controller.player)
                # Apply specific stats for prototype drones
                proto_drone.health = gs.get_game_setting("PROTOTYPE_DRONE_HEALTH")
                proto_drone.max_health = gs.get_game_setting("PROTOTYPE_DRONE_HEALTH")
                proto_drone.speed = gs.get_game_setting("PROTOTYPE_DRONE_SPEED")
                proto_drone.shoot_cooldown = gs.get_game_setting("PROTOTYPE_DRONE_SHOOT_COOLDOWN")
                self.enemies.add(proto_drone)
            else:
                print("EnemyManager: Could not find safe spawn for prototype drone.")
    
    def spawn_sentinel_drone_at_location(self, x, y):
        """
        Spawns a single SentinelDrone at a specific location.
        Used by MazeGuardian boss or potentially other scripted events.
        """
        shoot_sound = self.game_controller.sounds.get('enemy_shoot')
        player_bullet_size_base = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        sprite_path = gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH")
        
        sentinel = SentinelDrone(
            x=x, y=y,
            player_bullet_size_base=player_bullet_size_base,
            shoot_sound=shoot_sound,
            sprite_path=sprite_path,
            target_player_ref=self.game_controller.player 
        )
        self.enemies.add(sentinel)
        print(f"EnemyManager: Spawned Sentinel Drone at ({x}, {y})")

    def spawn_enemy_for_defense(self, enemy_type_key, spawn_position, reactor_target):
        """
        Spawns a specific type of enemy for the Maze Defense mode.
        The `spawn_position` is provided by the WaveManager, which gets it from
        GameController.get_enemy_spawn_points_for_defense(). For MazeChapter2, these
        will be the fixed spawn points defined in MazeChapter2.MAZE_TILEMAP.

        Args:
            enemy_type_key (str): Key to look up in self.defense_enemy_configs.
            spawn_position (tuple): (x, y) coordinates for spawning (absolute pixel center).
            reactor_target (CoreReactor): The reactor object enemies should target.
        """
        config = self.defense_enemy_configs.get(enemy_type_key)
        if not config:
            print(f"EnemyManager: Unknown enemy_type_key '{enemy_type_key}' for defense mode. Spawning standard drone.")
            config = self.defense_enemy_configs.get("standard_drone")
            if not config: 
                print("EnemyManager: CRITICAL - 'standard_drone' config missing in defense_enemy_configs.")
                return

        EnemyClass = config["class"] # Get the correct enemy class (Enemy or SentinelDrone)
        abs_x, abs_y = spawn_position # Already absolute pixel center
        enemy_shoot_sound = self.game_controller.sounds.get('enemy_shoot')
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")

        # Instantiate the enemy
        # Target_player_ref is None for primary movement in defense; enemies path to reactor.
        # Player is still used for shooting decisions if in range.
        enemy = EnemyClass(x=abs_x, y=abs_y,
                           player_bullet_size_base=player_bullet_size_setting,
                           shoot_sound=enemy_shoot_sound,
                           sprite_path=config["sprite_path"],
                           target_player_ref=self.game_controller.player) # Pass player for shooting logic

        # Apply specific stats from defense config
        enemy.health = config.get("health", enemy.health)
        enemy.max_health = config.get("health", enemy.max_health) 
        enemy.speed = config.get("speed", enemy.speed)
        enemy.shoot_cooldown = config.get("shoot_cooldown", enemy.shoot_cooldown)
        
        # Set attributes for defense mode behavior
        enemy.defense_target = reactor_target # The CoreReactor instance
        enemy.is_in_defense_mode = True 
        enemy.contact_damage = config.get("contact_damage", 25) # Damage on contact with reactor

        self.enemies.add(enemy)
        # print(f"EnemyManager (Defense): Spawned {enemy_type_key} at {spawn_position} targeting reactor.")


    def update_enemies(self, primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset=0, is_defense_mode=False):
        """
        Unified update method for all enemies.
        The `maze` object passed will be the current maze instance (Maze or MazeChapter2).
        The `primary_target_pos_pixels` will be the player in standard mode, or the reactor in defense mode.
        The Enemy.update method itself handles pathfinding and behavior based on these and `is_defense_mode`.
        Args:
            primary_target_pos_pixels (tuple): (x,y) of the main target.
            maze (Maze or MazeChapter2): The current maze object.
            current_time_ms (int): Current game time in milliseconds.
            game_area_x_offset (int): X-offset of the game area.
            is_defense_mode (bool): True if in defense mode, False otherwise.
        """
        for enemy_obj in list(self.enemies): # Iterate over a copy for safe removal if enemy dies
            if enemy_obj.alive:
                enemy_obj.update(primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset, is_defense_mode)
            elif not hasattr(enemy_obj, '_exploded'): # If dead and not yet exploded
                # Determine explosion sound based on enemy type or mode
                explosion_sound = 'enemy_shoot' # Default small explosion sound
                if isinstance(enemy_obj, SentinelDrone):
                    explosion_sound = 'prototype_drone_explode' 
                elif hasattr(enemy_obj, 'is_in_defense_mode') and enemy_obj.is_in_defense_mode:
                    # Could add more specific explosion sounds for defense mode enemy types
                    pass # For now, uses default or Sentinel sound

                self.game_controller._create_explosion(enemy_obj.rect.centerx, enemy_obj.rect.centery, specific_sound=explosion_sound)
                enemy_obj._exploded = True # Mark as exploded to prevent multiple explosions
                enemy_obj.kill() # Remove from all sprite groups
            elif not enemy_obj.bullets and hasattr(enemy_obj, '_exploded'): # If exploded and no bullets left
                 enemy_obj.kill() # Final cleanup


    def draw_all(self, surface):
        """Draws all managed enemies and their health bars."""
        for enemy in self.enemies: 
            enemy.draw(surface) # Enemy's draw method should handle its own sprite
            if enemy.alive and hasattr(enemy, '_draw_health_bar'): # Check if enemy has health bar logic
                enemy._draw_health_bar(surface) # Call enemy's health bar drawing method

    def reset_all(self):
        """Removes all enemies from the manager. Called at game over or new level/mode start."""
        self.enemies.empty() 
        print("EnemyManager: All enemies reset.")

    def get_sprites(self):
        """Returns the sprite group of managed enemies for collision detection or other logic."""
        return self.enemies

    def get_active_enemies_count(self):
        """Returns the number of currently active (alive) enemies."""
        return sum(1 for e in self.enemies if e.alive)
