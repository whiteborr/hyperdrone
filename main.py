import sys
import traceback
import pygame

from hyperdrone_core.game_loop import GameController

if __name__ == '__main__':
    """
    Main entry point for the Hyperdrone game.
    Initializes the GameController and starts the game loop.
    """
    print("Starting Hyperdrone...") #
    try:
        # Create an instance of the GameController
        game_controller = GameController() #
        # Start the main game loop
        game_controller.run() #
    except Exception as e: #
        print(f"FATAL ERROR in GameController execution: {e}") #
        traceback.print_exc() # Print the full traceback for the runtime error #
        # Attempt to clean up Pygame if it was initialized
        if pygame.get_init(): #
            pygame.quit() #
        sys.exit() #