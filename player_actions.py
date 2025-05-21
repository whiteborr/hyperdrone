# player_actions.py
import pygame

# Pygame key constants, can be defined here or imported if globally managed.
# For consistency, if these are defined in game_settings.py and imported elsewhere,
# it might be better to import them. However, for a focused module, direct use is also common.
K_LEFT = pygame.K_LEFT
K_RIGHT = pygame.K_RIGHT
K_c = pygame.K_c # Key for cloak ability

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
        Returns the player object or None if not found or not alive.
        """
        if hasattr(self.game_controller, 'player') and self.game_controller.player:
            # Optionally, could also check player.alive here if actions should only apply to alive player
            return self.game_controller.player
        print("PlayerActions: Warning - Player object not found in game_controller.")
        return None

    def start_moving_forward(self):
        """Initiates forward movement for the player's drone."""
        player = self._get_player()
        if player and player.alive: # Check if player is alive before action
            player.moving_forward = True
            if hasattr(player, 'attempt_speed_boost_activation'):
                player.attempt_speed_boost_activation()

    def stop_moving_forward(self):
        """Stops forward movement for the player's drone (typically on K_DOWN press)."""
        player = self._get_player()
        if player and player.alive:
            player.moving_forward = False
            # Speed boost deactivation is handled by player.update based on its timer

    def stop_moving_forward_on_key_up(self):
        """
        Stops forward movement if the K_UP key is released.
        This provides a more responsive stop than relying solely on K_DOWN.
        """
        player = self._get_player()
        if player and player.alive:
            # This method is called on K_UP keyup. If K_DOWN is simultaneously pressed,
            # K_DOWN's effect (setting moving_forward = False) would likely take precedence
            # or be handled immediately after by EventManager.
            # So, simply setting moving_forward to False here is usually correct.
            player.moving_forward = False

    def handle_continuous_input(self, keys, current_time):
        """
        Handles continuous inputs like rotation, typically called every frame
        when relevant keys are held down.
        Args:
            keys: The state of all keyboard keys from pygame.key.get_pressed().
            current_time: The current game time in milliseconds (for time-based abilities).
        """
        player = self._get_player()
        if not player or not player.alive:
            return

        # Rotation
        if keys[K_LEFT]:
            if hasattr(player, 'rotate') and hasattr(player, 'rotation_speed'):
                player.rotate("left", player.rotation_speed)
        if keys[K_RIGHT]:
            if hasattr(player, 'rotate') and hasattr(player, 'rotation_speed'):
                player.rotate("right", player.rotation_speed)
        
        # Cloak activation (if it were a held key, but it's a toggle on KEYDOWN)
        # The toggle for cloak is better handled in EventManager's KEYDOWN section
        # by calling self.try_activate_cloak(current_time).
        # This method is more for actions that happen *while* a key is held.
        # For example, if cloak was "hold K_c to stay cloaked".
        # if keys[K_c]:
        #     self.try_activate_cloak(current_time) # This would repeatedly try, better as a toggle.
        pass


    def shoot(self, current_time):
        """
        Commands the player's drone to shoot.
        Retrieves necessary context (maze, enemies) from the game_controller.
        Args:
            current_time: The current game time in milliseconds.
        """
        player = self._get_player()
        if player and player.alive:
            if hasattr(player, 'shoot'):
                # Get necessary context from the game_controller
                maze_ref = getattr(self.game_controller, 'maze', None)
                enemies_group_ref = getattr(self.game_controller, 'enemies', None)
                
                # Get sounds from game_controller (assuming it loads and stores them)
                shoot_sound = None
                missile_sound = None
                if hasattr(self.game_controller, 'sounds') and isinstance(self.game_controller.sounds, dict):
                    shoot_sound = self.game_controller.sounds.get('shoot')
                    missile_sound = self.game_controller.sounds.get('missile_launch')

                player.shoot(
                    sound=shoot_sound,
                    missile_sound=missile_sound,
                    maze=maze_ref,
                    enemies_group=enemies_group_ref
                    # current_time is implicitly used by player.shoot for cooldowns
                )
    
    def try_activate_cloak(self, current_time):
        """
        Attempts to activate the player's cloak ability.
        Called by EventManager on K_c KEYDOWN.
        """
        player = self._get_player()
        if player and player.alive and hasattr(player, 'try_activate_cloak'):
            player.try_activate_cloak(current_time) # Drone class handles cooldown logic

    # Example of how other actions could be added:
    # def cycle_weapon_action(self):
    #     """Commands the player to cycle their weapon."""
    #     player = self._get_player()
    #     if player and player.alive and hasattr(player, 'cycle_weapon_state'):
    #         player.cycle_weapon_state(force_cycle=True) # Or False depending on context
    #         # Play UI sound via game_controller if needed
    #         if hasattr(self.game_controller, 'play_sound'):
    #             self.game_controller.play_sound('ui_select') # Example sound
