import sys
import traceback
import pygame
import logging

logging.basicConfig(level=logging.INFO)

from hyperdrone_core.game_loop import GameController

if __name__ == '__main__':
    """
    Main entry point for the Hyperdrone game.
    Initializes the GameController and starts the game loop.
    """
    logging.info("Starting Hyperdrone...")
    try:
        # Create an instance of the GameController
        game_controller = GameController() #
        # Start the main game loop
        game_controller.run() #
    except Exception as e: #
        traceback.print_exc() # Print the full traceback for the runtime error #
        # Attempt to clean up Pygame if it was initialized
        if pygame.get_init(): #
            pygame.quit() #
        sys.exit() #