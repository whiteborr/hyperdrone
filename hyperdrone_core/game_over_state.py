# hyperdrone_core/game_over_state.py
from pygame import KEYDOWN, K_UP, K_DOWN, K_RETURN, K_SPACE
from .state import State

class GameOverState(State):
    def enter(self, previous_state=None, **kwargs):
        # Initialize the selected option
        self.selected_option = 0
        self.options = ["Continue", "Main Menu"]
        
        # Store the previous state for potential continuation
        self.previous_state = kwargs.get('prev_state', previous_state)
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    self.selected_option = (self.selected_option - 1) % len(self.options)
                    self.game.play_sound('menu_move')
                elif event.key == K_DOWN:
                    self.selected_option = (self.selected_option + 1) % len(self.options)
                    self.game.play_sound('menu_move')
                elif event.key == K_RETURN or event.key == K_SPACE:
                    self.game.play_sound('menu_select')
                    if self.selected_option == 0:  # Continue
                        # Always reset lives to 3 when continuing
                        self.game.lives = 3
                        self._respawn_player()
                        
                        # Determine which state to return to based on previous state
                        if self.previous_state in ["PlayingState", "MazeDefenseState", "BossFightState", 
                                                  "CorruptedSectorState", "HarvestChamberState"]:
                            self.game.state_manager.set_state(self.previous_state)
                        else:
                            # Default to story map if previous state is not a gameplay state
                            self.game.state_manager.set_state("StoryMapState")
                    elif self.selected_option == 1:  # Main Menu
                        # Return to main menu
                        self.game.state_manager.set_state("MainMenuState")
    
    def _respawn_player(self):
        """Respawn the player without recreating the maze or level"""
        if hasattr(self.game, '_respawn_player'):
            self.game._respawn_player()
            
            # Reset player movement and shooting state
            if hasattr(self.game, 'player_actions'):
                self.game.player_actions.is_shooting = False
                self.game.player_actions.turn_left = False
                self.game.player_actions.turn_right = False
                
                # Make sure the player isn't cruising
                if self.game.player and hasattr(self.game.player, 'is_cruising'):
                    self.game.player.is_cruising = False
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Let the UI manager handle drawing the game over screen
        # The UI manager will use self.selected_option to highlight the current selection
        pass
