import sys
import traceback

import pygame

import game_settings

# Import the GameController
game_loop_module = None
GameController_class = None
import game_loop 

game_loop_module = game_loop # Assign if import game_loop was successful

from game_loop import GameController
GameController_class = GameController

if __name__ == '__main__':
    """
    Main entry point for the Hyperdrone game.
    Initializes the GameController and starts the game loop.
    """
    print("Starting Hyperdrone...")
    try:
        # Create an instance of the GameController
        game_controller = GameController_class() # Use the successfully imported class
        # Start the main game loop
        game_controller.run()
    except Exception as e:
        print(f"FATAL ERROR in GameController execution: {e}")
        traceback.print_exc() # Print the full traceback for the runtime error
        # Attempt to clean up Pygame if it was initialized
        if pygame.get_init():
            pygame.quit()
        sys.exit()
