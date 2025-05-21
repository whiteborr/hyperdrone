# main.py
import sys
import pygame # Pygame might be needed for sys.exit or error handling before GameController init
import traceback # For more detailed error reporting

# Attempt to import game_settings first to catch critical load errors early
try:
    import game_settings
    # Perform a basic check that game_settings can be accessed
    if game_settings.get_game_setting("WIDTH") is None: # A key that should exist
        print("CRITICAL (main.py): Default game settings failed to load via get_game_setting. Exiting.")
        if pygame.get_init(): pygame.quit()
        sys.exit()
except ImportError:
    print("CRITICAL (main.py): game_settings.py could not be imported. Ensure it's in the same directory or Python path. Exiting.")
    traceback.print_exc()
    sys.exit()
except Exception as e:
    print(f"CRITICAL (main.py): Error during game_settings import or initial access: {e}. Exiting.")
    traceback.print_exc()
    if pygame.get_init(): pygame.quit()
    sys.exit()

# Now import the GameController
game_loop_module = None
GameController_class = None
try:
    # Attempt to import the module first to see if the module itself has an issue
    import game_loop 
    game_loop_module = game_loop # Assign if import game_loop was successful

    # Now, specifically try to import GameController from the loaded module
    from game_loop import GameController
    GameController_class = GameController

except ImportError as e_import:
    print(f"CRITICAL (main.py): Failed to import 'game_loop' module or 'GameController' from it.")
    print(f"Specific ImportError: {e_import}")
    print("This usually means 'game_loop.py' (or one of the files it imports) has an error that prevents it from loading correctly.")
    print("Please check the full console output for any errors originating from 'game_loop.py' or its dependencies.")
    traceback.print_exc() # Print the full traceback for the ImportError
    if pygame.get_init(): pygame.quit()
    sys.exit()
except Exception as e_general: # Catch other potential errors during GameController import
    print(f"CRITICAL (main.py): An unexpected error occurred while trying to import GameController: {e_general}")
    print("Check 'game_loop.py' and its dependencies for issues.")
    traceback.print_exc() # Print the full traceback for the general error
    if pygame.get_init(): pygame.quit()
    sys.exit()

if GameController_class is None: 
    # This case should ideally be caught by the exceptions above,
    # but it's a final safeguard.
    print("CRITICAL (main.py): GameController class could not be loaded from game_loop.py for an unknown reason. Exiting.")
    if pygame.get_init(): pygame.quit()
    sys.exit()


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
