import json
import os

import game_settings as gs

DATA_DIR = "data" #
LEADERBOARD_FULL_PATH = os.path.join(DATA_DIR, gs.LEADERBOARD_FILE_NAME) #

def _ensure_data_dir_exists(): #
    """Ensures the data directory exists. Creates it if not."""
    if not os.path.exists(DATA_DIR): #
        try: #
            os.makedirs(DATA_DIR) #
            print(f"Leaderboard: Created data directory at '{DATA_DIR}'") #
        except OSError as e: #
            print(f"Leaderboard: Error creating data directory '{DATA_DIR}': {e}") #
            return False #
    return True #

def load_scores(): #
    """Loads scores from the leaderboard file."""
    from hyperdrone_core.constants import KEY_LEADERBOARD_NAME, KEY_LEADERBOARD_SCORE, KEY_LEADERBOARD_LEVEL
    
    if not _ensure_data_dir_exists(): #
        return [] #

    # Update path to use gs.LEADERBOARD_FILE_NAME if it changed due to settings
    current_leaderboard_path = os.path.join(DATA_DIR, gs.get_game_setting("LEADERBOARD_FILE_NAME"))

    if not os.path.exists(current_leaderboard_path): #
        print(f"Leaderboard: File '{current_leaderboard_path}' not found. Returning empty list.") #
        return [] #
    try: #
        with open(current_leaderboard_path, 'r') as f: #
            scores = json.load(f) #
            if not isinstance(scores, list): #
                print(f"Leaderboard: Data in '{current_leaderboard_path}' is not a list. Resetting.") #
                return [] #
            for entry in scores: #
                if not isinstance(entry, dict): #
                    print(f"Leaderboard: Invalid entry found in '{current_leaderboard_path}'. Resetting.") #
                    return [] #
            scores.sort(key=lambda x: (-int(x.get(KEY_LEADERBOARD_SCORE, 0)), -int(x.get(KEY_LEADERBOARD_LEVEL, 0)), str(x.get(KEY_LEADERBOARD_NAME, 'ZZZ')))) #
            return scores #
    except (IOError, json.JSONDecodeError) as e: #
        print(f"Leaderboard: Error loading or parsing '{current_leaderboard_path}': {e}. Returning empty list.") #
        return [] #
    except Exception as e: #
        print(f"Leaderboard: Unexpected error loading scores from '{current_leaderboard_path}': {e}. Returning empty list.") #
        return [] #

def save_scores(scores): #
    """Saves scores to the leaderboard file."""
    if not _ensure_data_dir_exists(): #
        print("Leaderboard: Cannot save scores, data directory issue.") #
        return #

    # Update path to use gs.LEADERBOARD_FILE_NAME if it changed due to settings
    current_leaderboard_path = os.path.join(DATA_DIR, gs.get_game_setting("LEADERBOARD_FILE_NAME"))

    try: #
        scores.sort(key=lambda x: (-int(x.get('score', 0)), -int(x.get('level', 0)), str(x.get('name', 'ZZZ')))) #
        with open(current_leaderboard_path, 'w') as f: #
            json.dump(scores, f, indent=4) #
    except IOError as e: #
        print(f"Leaderboard: Error: Could not save scores to '{current_leaderboard_path}': {e}") #
    except Exception as e: #
        print(f"Leaderboard: Unexpected error saving scores to '{current_leaderboard_path}': {e}") #

def add_score(name, score, level): #
    """
    Adds a new score (and level) to the leaderboard if it qualifies.
    """
    from hyperdrone_core.constants import KEY_LEADERBOARD_NAME, KEY_LEADERBOARD_SCORE, KEY_LEADERBOARD_LEVEL
    
    if not name or not isinstance(name, str) or len(name.strip()) == 0: #
        print("Leaderboard: Invalid name provided for score. Not adding.") #
        return False #
    
    try: #
        current_score = int(score) #
        current_level = int(level) #
    except ValueError: #
        print("Leaderboard: Invalid score or level provided (must be numbers). Not adding.") #
        return False #

    scores = load_scores() #
    new_score_entry = {
        KEY_LEADERBOARD_NAME: name.strip().upper()[:6], 
        KEY_LEADERBOARD_SCORE: current_score, 
        KEY_LEADERBOARD_LEVEL: current_level
    } #

    should_add = False #
    # Use gs.get_game_setting for LEADERBOARD_MAX_ENTRIES
    if len(scores) < gs.get_game_setting("LEADERBOARD_MAX_ENTRIES"): #
        should_add = True #
    else: #
        lowest_on_board_score = int(scores[-1].get(KEY_LEADERBOARD_SCORE, 0)) #
        lowest_on_board_level = int(scores[-1].get(KEY_LEADERBOARD_LEVEL, 0)) #

        if current_score > lowest_on_board_score: #
            should_add = True #
        elif current_score == lowest_on_board_score and current_level > lowest_on_board_level: #
            should_add = True #

    if should_add: #
        scores.append(new_score_entry) #
        scores.sort(key=lambda x: (-int(x.get(KEY_LEADERBOARD_SCORE, 0)), -int(x.get(KEY_LEADERBOARD_LEVEL, 0)), str(x.get(KEY_LEADERBOARD_NAME, 'ZZZ')))) #
        # Use gs.get_game_setting for LEADERBOARD_MAX_ENTRIES
        scores = scores[:gs.get_game_setting("LEADERBOARD_MAX_ENTRIES")] #
        save_scores(scores) #
        print(f"Leaderboard: Score added for {new_score_entry[KEY_LEADERBOARD_NAME]}: Score {new_score_entry[KEY_LEADERBOARD_SCORE]}, Level {new_score_entry[KEY_LEADERBOARD_LEVEL]}") #
        return True #

    print(f"Leaderboard: Score for {new_score_entry[KEY_LEADERBOARD_NAME]} (Score: {new_score_entry[KEY_LEADERBOARD_SCORE]}, Level: {new_score_entry[KEY_LEADERBOARD_LEVEL]}) did not qualify.") #
    return False #

def get_top_scores(): #
    """Returns the top scores, sorted."""
    return load_scores() #

def is_high_score(score, level): #
    """
    Checks if a score and level are high enough to be on the leaderboard.
    """
    from hyperdrone_core.constants import KEY_LEADERBOARD_SCORE, KEY_LEADERBOARD_LEVEL
    
    try: #
        check_score = int(score) #
        check_level = int(level) #
    except ValueError: #
        print("Leaderboard: Invalid score or level provided for high score check.") #
        return False #

    scores = load_scores() #
    # Use gs.get_game_setting for LEADERBOARD_MAX_ENTRIES
    if len(scores) < gs.get_game_setting("LEADERBOARD_MAX_ENTRIES"): #
        return True #
    if not scores: #
        return True #

    lowest_on_board_score = int(scores[-1].get(KEY_LEADERBOARD_SCORE, 0)) #
    lowest_on_board_level = int(scores[-1].get(KEY_LEADERBOARD_LEVEL, 0)) #

    if check_score > lowest_on_board_score: #
        return True #
    if check_score == lowest_on_board_score and check_level > lowest_on_board_level: #
        return True #

    return False #

# Example usage / Test functions (can be commented out in the final game)
if __name__ == '__main__': #
    print("Leaderboard Module Self-Test:") #
    
    # Since game_settings is imported as gs, use gs.get_game_setting for test values
    # Or ensure that the test environment can directly access these names if this
    # __main__ block is run independently of the full game context.
    # For robustness in this self-test, let's define fallbacks if gs isn't fully set up.
    try:
        LEADERBOARD_FILE_NAME_TEST = gs.get_game_setting("LEADERBOARD_FILE_NAME")
        LEADERBOARD_MAX_ENTRIES_TEST = gs.get_game_setting("LEADERBOARD_MAX_ENTRIES")
    except (NameError, AttributeError): # gs might not be defined if run standalone without game_settings fully parsed
        print("Self-test: gs.get_game_setting not available, using fallback test values.")
        LEADERBOARD_FILE_NAME_TEST = "test_leaderboard.json"
        LEADERBOARD_MAX_ENTRIES_TEST = 5
    
    LEADERBOARD_FULL_PATH_TEST = os.path.join(DATA_DIR, LEADERBOARD_FILE_NAME_TEST) #
    print(f"Self-test using temporary file: {LEADERBOARD_FULL_PATH_TEST} and Max Entries: {LEADERBOARD_MAX_ENTRIES_TEST}") #

    if LEADERBOARD_FILE_NAME_TEST == "test_leaderboard.json" and os.path.exists(LEADERBOARD_FULL_PATH_TEST): #
        os.remove(LEADERBOARD_FULL_PATH_TEST) #
        print(f"Removed test file: {LEADERBOARD_FULL_PATH_TEST}") #

    print("\nInitial scores (should be empty or from previous test run if not cleared):") #
    for s_entry in get_top_scores(): print(s_entry) #

    print("\nAdding scores...") #
    add_score("ALICE", 1000, 3) #
    add_score("BOB", 1500, 5) #
    add_score("CHARLIE", 1000, 2) #
    add_score("DAVID", 2000, 1) #
    add_score("EVE", 1500, 5)    #
    add_score("FRANK", 2500, 6)  #
    add_score("GRACE", 500, 1)   #

    print("\nScores after adding entries:") #
    for s_entry in get_top_scores(): #
        print(s_entry) #

    print(f"\nMax entries allowed: {LEADERBOARD_MAX_ENTRIES_TEST}") #
    print(f"Current number of scores: {len(get_top_scores())}") #

    print("\nChecking high scores:") #
    print(f"Is 1200, level 4 a high score? {is_high_score(1200, 4)}") #
    print(f"Is 400, level 1 a high score? {is_high_score(400, 1)}") #
    current_scores = get_top_scores() #
    if current_scores and len(current_scores) == LEADERBOARD_MAX_ENTRIES_TEST: #
        lowest_score_val = current_scores[-1]['score'] #
        print(f"Is {lowest_score_val}, level 10 a high score (same score as lowest, higher level)? {is_high_score(lowest_score_val, 10)}") #
        print(f"Is {lowest_score_val}, level 1 a high score (same score as lowest, lower/same level)? {is_high_score(lowest_score_val, 1)}") #
    
    print("\nTest with invalid inputs:") #
    add_score("", 5000, 10) #
    add_score("INVALID", "notascore", 10) #

    # Keep test file for inspection if needed, otherwise uncomment to remove.
    # if LEADERBOARD_FILE_NAME_TEST == "test_leaderboard.json" and os.path.exists(LEADERBOARD_FULL_PATH_TEST):
    #     os.remove(LEADERBOARD_FULL_PATH_TEST)
    #     print(f"Removed test file: {LEADERBOARD_FULL_PATH_TEST} at end of test.")