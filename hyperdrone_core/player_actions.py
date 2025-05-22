import pygame

# game_settings might be needed if any player actions directly reference specific settings keys
# For now, assuming most setting-dependent logic is within the Player/Drone class itself
# or accessed via the game_controller reference.
# import game_settings as gs

class PlayerActions:
    def __init__(self, game_controller_ref):
        """
        Initializes the PlayerActions handler.
        Args:
            game_controller_ref: A reference to the main game controller,
                                 which holds the player object and other game context.
        """
        self.game_controller = game_controller_ref #

    def _get_player(self): #
        """
        Safely gets the player object from the game controller.
        Returns the player object (Drone instance) or None if not found or not alive.
        """
        player = getattr(self.game_controller, 'player', None) #
        if player and hasattr(player, 'alive') and player.alive: #
            return player #
        return None #

    def start_moving_forward(self): #
        """Initiates forward movement for the player's drone."""
        player = self._get_player() #
        if player: # Player's 'alive' check is implicit in _get_player
            player.moving_forward = True # Player object (Drone class) has this attribute
            if hasattr(player, 'attempt_speed_boost_activation'): #
                player.attempt_speed_boost_activation() #

    def stop_moving_forward(self): #
        """Stops forward movement for the player's drone (typically on K_DOWN press)."""
        player = self._get_player() #
        if player: #
            player.moving_forward = False #

    def stop_moving_forward_on_key_up(self): #
        """
        Stops forward movement if the K_UP key is released.
        Provides a more responsive stop.
        """
        # This method might be deprecated if K_DOWN is the sole way to stop.
        # However, if K_UP release should also stop, it remains relevant.
        player = self._get_player() #
        if player: #
            player.moving_forward = False #

    def handle_continuous_input(self, keys_pressed, current_time_ms): #
        """
        Handles continuous inputs like rotation, typically called every frame
        when relevant keys are held down.
        """
        player = self._get_player() #
        if not player: #
            return #

        if keys_pressed[pygame.K_LEFT]: #
            if hasattr(player, 'rotate'): #
                player.rotate("left") #
        if keys_pressed[pygame.K_RIGHT]: #
            if hasattr(player, 'rotate'): #
                player.rotate("right") #
        
    def shoot(self, current_time_ms): # current_time_ms is passed by EventManager
        """
        Commands the player's drone to shoot.
        """
        player = self._get_player() #
        if player: #
            if hasattr(player, 'shoot'): #
                maze_ref = getattr(self.game_controller, 'maze', None) # Already gets maze
                enemies_group_ref = getattr(self.game_controller, 'enemies', None) # Already gets enemies
                                
                primary_shoot_sound = None #
                missile_launch_sound = None #
                
                if hasattr(self.game_controller, 'sounds') and isinstance(self.game_controller.sounds, dict): #
                    primary_shoot_sound = self.game_controller.sounds.get('shoot') #
                    missile_launch_sound = self.game_controller.sounds.get('missile_launch') #

                player.shoot(
                    sound=primary_shoot_sound, 
                    missile_sound=missile_launch_sound, 
                    maze=maze_ref, # Pass the maze reference
                    enemies_group=enemies_group_ref 
                )

    def try_activate_cloak(self, current_time_ms): #
        """
        Attempts to activate the player's cloak ability.
        """
        player = self._get_player() #
        if player: #
            if hasattr(player, 'try_activate_cloak'): #
                if player.try_activate_cloak(current_time_ms): #
                    if hasattr(self.game_controller, 'play_sound'): #
                        self.game_controller.play_sound('cloak_activate') #
                else: #
                    if hasattr(self.game_controller, 'play_sound'): #
                        self.game_controller.play_sound('ui_denied') #