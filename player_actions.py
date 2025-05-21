import pygame

# Pygame key constants can be directly used if EventManager passes the 'keys' state.
# No direct import of game_settings needed here typically, as actions are delegated.

class PlayerActions:
    def __init__(self, game_controller_ref):
        """
        Initializes the PlayerActions handler.
        Args:
            game_controller_ref: A reference to the main game controller,
                                 which holds the player object and other game context.
        """
        self.game_controller = game_controller_ref

    def _get_player(self):
        """
        Safely gets the player object from the game controller.
        Returns the player object (Drone instance) or None if not found or not alive.
        """
        player = getattr(self.game_controller, 'player', None)
        if player and hasattr(player, 'alive') and player.alive:
            return player
        # Optional: print a warning if player is not found/alive when an action is attempted
        # else:
        #     print("PlayerActions: Warning - Player object not found or not alive in game_controller.")
        return None

    def start_moving_forward(self):
        """Initiates forward movement for the player's drone."""
        player = self._get_player()
        if player: # Player's 'alive' check is implicit in _get_player
            player.moving_forward = True # Player object (Drone class) has this attribute
            # If player has a method to attempt speed boost on movement start
            if hasattr(player, 'attempt_speed_boost_activation'):
                player.attempt_speed_boost_activation()

    def stop_moving_forward(self):
        """Stops forward movement for the player's drone (typically on K_DOWN press)."""
        player = self._get_player()
        if player:
            player.moving_forward = False
            # Note: Speed boost deactivation is typically handled by the Player's update method based on its timer.

    def stop_moving_forward_on_key_up(self):
        """
        Stops forward movement if the K_UP key is released.
        Provides a more responsive stop.
        """
        player = self._get_player()
        if player:
            player.moving_forward = False

    def handle_continuous_input(self, keys_pressed, current_time_ms):
        """
        Handles continuous inputs like rotation, typically called every frame
        when relevant keys are held down.
        Args:
            keys_pressed: The state of all keyboard keys from pygame.key.get_pressed().
            current_time_ms: The current game time in milliseconds (unused here but good practice for timed abilities).
        """
        player = self._get_player()
        if not player:
            return

        # Player Rotation
        # The player.rotate() method itself should use player.rotation_speed
        if keys_pressed[pygame.K_LEFT]:
            if hasattr(player, 'rotate'):
                player.rotate("left") # Player's rotate method handles its own rotation_speed
        if keys_pressed[pygame.K_RIGHT]:
            if hasattr(player, 'rotate'):
                player.rotate("right")
        
        # Other continuous actions could be handled here if needed.
        # For example, if cloak was "hold K_c to stay cloaked", but it's a toggle.

    def shoot(self, current_time_ms): # current_time_ms is passed by EventManager
        """
        Commands the player's drone to shoot.
        Retrieves necessary context (maze, enemies, sounds) from the game_controller.
        Args:
            current_time_ms: The current game time in milliseconds (Player's shoot method uses this for cooldowns).
        """
        player = self._get_player()
        if player: # Player is alive if _get_player returns it
            if hasattr(player, 'shoot'):
                # Get necessary context from the game_controller for the player's shoot method
                maze_ref = getattr(self.game_controller, 'maze', None)
                enemies_group_ref = getattr(self.game_controller, 'enemies', None) # Or specific group for missiles
                
                # Get sounds from game_controller (assuming it loads and stores them)
                primary_shoot_sound = None
                missile_launch_sound = None
                # Lightning sound might be handled similarly if player.shoot needs it
                
                if hasattr(self.game_controller, 'sounds') and isinstance(self.game_controller.sounds, dict):
                    primary_shoot_sound = self.game_controller.sounds.get('shoot')
                    missile_launch_sound = self.game_controller.sounds.get('missile_launch')
                    # lightning_sound = self.game_controller.sounds.get('lightning_zap') # Example

                # The player's shoot method is now more comprehensive
                player.shoot(
                    sound=primary_shoot_sound,
                    missile_sound=missile_launch_sound,
                    maze=maze_ref, # For bouncing bullets
                    enemies_group=enemies_group_ref # For missile targeting / lightning
                    # current_time_ms is implicitly used by player.shoot for cooldown checks
                )

    def try_activate_cloak(self, current_time_ms):
        """
        Attempts to activate the player's cloak ability.
        Called by EventManager on K_c KEYDOWN.
        Args:
            current_time_ms: The current game time in milliseconds.
        """
        player = self._get_player()
        if player: # Player is alive
            if hasattr(player, 'try_activate_cloak'):
                # Player's Drone class handles cooldown logic and actual activation
                if player.try_activate_cloak(current_time_ms):
                    # Optionally play a cloak activation sound via game_controller
                    if hasattr(self.game_controller, 'play_sound'):
                        self.game_controller.play_sound('cloak_activate') # Example sound name
                else:
                    # Optionally play a "cannot cloak" (e.g., cooldown) sound
                    if hasattr(self.game_controller, 'play_sound'):
                        self.game_controller.play_sound('ui_denied') # Example sound name
    
    # Example for cycling weapon, though EventManager currently calls player.cycle_weapon_state directly
    # def cycle_weapon_action(self):
    #     """Commands the player to cycle their weapon."""
    #     player = self._get_player()
    #     if player and hasattr(player, 'cycle_weapon_state'):
    #         if player.cycle_weapon_state(force_cycle=True): # True to cycle even at end of sequence
    #             if hasattr(self.game_controller, 'play_sound'):
    #                 self.game_controller.play_sound('ui_select') # Example sound for weapon cycle