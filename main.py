from sys import exit
from pygame import get_init, quit as pygame_quit
import logging
from logging_config import setup_logging

# Setup logging for the application
logger = setup_logging(logging.INFO)

from hyperdrone_core.game_loop import GameController

if __name__ == '__main__':
    """
    Main entry point for the Hyperdrone game.
    Initializes the GameController and starts the game loop.
    """
    logger.info("Starting Hyperdrone...")
    try:
        # Create an instance of the GameController
        game_controller = GameController()
        # Start the main game loop
        game_controller.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        # Attempt to clean up Pygame if it was initialized
        if get_init():
            pygame_quit()
        exit()
