import json
import os

from game_settings import LEADERBOARD_FILE_NAME, LEADERBOARD_MAX_ENTRIES

DATA_DIR = "data"
LEADERBOARD_FULL_PATH = os.path.join(DATA_DIR, LEADERBOARD_FILE_NAME)

def _ensure_data_dir_exists():
    """Ensures the data directory exists. Creates it if not."""
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
            print(f"Leaderboard: Created data directory at '{DATA_DIR}'")
        except OSError as e:
            print(f"Leaderboard: Error creating data directory '{DATA_DIR}': {e}")
            # Depending on desired behavior, you might raise an error or try to save in current dir
            return False
    return True

def load_scores():
    """Loads scores from the leaderboard file."""
    if not _ensure_data_dir_exists(): # Ensure directory exists before trying to load
        return [] # Cannot load if directory can't be accessed/created

    if not os.path.exists(LEADERBOARD_FULL_PATH):
        print(f"Leaderboard: File '{LEADERBOARD_FULL_PATH}' not found. Returning empty list.")
        return []
    try:
        with open(LEADERBOARD_FULL_PATH, 'r') as f:
            scores = json.load(f)
            # Ensure scores are properly formatted (list of dicts)
            if not isinstance(scores, list):
                print(f"Leaderboard: Data in '{LEADERBOARD_FULL_PATH}' is not a list. Resetting.")
                return []
            for entry in scores:
                if not isinstance(entry, dict):
                    print(f"Leaderboard: Invalid entry found in '{LEADERBOARD_FULL_PATH}'. Resetting.")
                    return []
            # Sort scores: primarily by score (desc), then by level (desc), then by name (asc)
            scores.sort(key=lambda x: (-int(x.get('score', 0)), -int(x.get('level', 0)), str(x.get('name', 'ZZZ'))))
            return scores
    except (IOError, json.JSONDecodeError) as e:
        print(f"Leaderboard: Error loading or parsing '{LEADERBOARD_FULL_PATH}': {e}. Returning empty list.")
        return []
    except Exception as e: # Catch any other unexpected errors during loading
        print(f"Leaderboard: Unexpected error loading scores from '{LEADERBOARD_FULL_PATH}': {e}. Returning empty list.")
        return []

def save_scores(scores):
    """Saves scores to the leaderboard file."""
    if not _ensure_data_dir_exists(): # Ensure directory exists before trying to save
        print("Leaderboard: Cannot save scores, data directory issue.")
        return

    try:
        # Ensure scores are sorted before saving, using the same criteria as load
        scores.sort(key=lambda x: (-int(x.get('score', 0)), -int(x.get('level', 0)), str(x.get('name', 'ZZZ'))))
        with open(LEADERBOARD_FULL_PATH, 'w') as f:
            json.dump(scores, f, indent=4) # Use indent for readability
    except IOError as e:
        print(f"Leaderboard: Error: Could not save scores to '{LEADERBOARD_FULL_PATH}': {e}")
    except Exception as e: # Catch any other unexpected errors during saving
        print(f"Leaderboard: Unexpected error saving scores to '{LEADERBOARD_FULL_PATH}': {e}")

def add_score(name, score, level):
    """
    Adds a new score (and level) to the leaderboard if it qualifies.
    Args:
        name (str): Player's name.
        score (int): Player's score.
        level (int): Level reached by the player.
    Returns:
        bool: True if the score was added, False otherwise.
    """
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        print("Leaderboard: Invalid name provided for score. Not adding.")
        return False
    
    try:
        current_score = int(score)
        current_level = int(level)
    except ValueError:
        print("Leaderboard: Invalid score or level provided (must be numbers). Not adding.")
        return False

    scores = load_scores()
    new_score_entry = {'name': name.strip().upper()[:6], 'score': current_score, 'level': current_level} # Limit name length

    should_add = False
    if len(scores) < LEADERBOARD_MAX_ENTRIES:
        should_add = True
    else:
        # Qualifies if score is higher, or score is same and level is higher,
        # than the current lowest score on the leaderboard (which is the last element after sorting).
        # Ensure comparison with numeric types.
        lowest_on_board_score = int(scores[-1].get('score', 0))
        lowest_on_board_level = int(scores[-1].get('level', 0))

        if current_score > lowest_on_board_score:
            should_add = True
        elif current_score == lowest_on_board_score and current_level > lowest_on_board_level:
            should_add = True

    if should_add:
        scores.append(new_score_entry)
        # Sort by score (descending), then level (descending), then by name (ascending for tie-breaking)
        scores.sort(key=lambda x: (-int(x.get('score', 0)), -int(x.get('level', 0)), str(x.get('name', 'ZZZ'))))

        # Keep only the top MAX_SCORES
        scores = scores[:LEADERBOARD_MAX_ENTRIES]
        save_scores(scores)
        print(f"Leaderboard: Score added for {new_score_entry['name']}: Score {new_score_entry['score']}, Level {new_score_entry['level']}")
        return True

    print(f"Leaderboard: Score for {new_score_entry['name']} (Score: {new_score_entry['score']}, Level: {new_score_entry['level']}) did not qualify.")
    return False

def get_top_scores():
    """Returns the top scores, sorted."""
    # load_scores already sorts them.
    return load_scores()

def is_high_score(score, level):
    """
    Checks if a score and level are high enough to be on the leaderboard.
    Args:
        score (int): The score to check.
        level (int): The level achieved with that score.
    Returns:
        bool: True if the score qualifies, False otherwise.
    """
    try:
        check_score = int(score)
        check_level = int(level)
    except ValueError:
        print("Leaderboard: Invalid score or level provided for high score check.")
        return False

    scores = load_scores()
    if len(scores) < LEADERBOARD_MAX_ENTRIES:
        return True # Always a high score if the leaderboard isn't full
    if not scores: # Should be caught by len < MAX_ENTRIES if MAX_ENTRIES > 0
        return True

    # Check against the last entry (lowest score on the full leaderboard)
    lowest_on_board_score = int(scores[-1].get('score', 0))
    lowest_on_board_level = int(scores[-1].get('level', 0))

    if check_score > lowest_on_board_score:
        return True
    if check_score == lowest_on_board_score and check_level > lowest_on_board_level:
        return True

    return False

# Example usage / Test functions (can be commented out in the final game)
if __name__ == '__main__':
    print("Leaderboard Module Self-Test:")
    
    # Ensure game_settings.py exists for test or use fallbacks
    if 'LEADERBOARD_FILE_NAME' not in globals():
        LEADERBOARD_FILE_NAME = "test_leaderboard.json" # Use a test-specific file
        LEADERBOARD_MAX_ENTRIES = 5 # Test with a smaller leaderboard
        LEADERBOARD_FULL_PATH = os.path.join(DATA_DIR, LEADERBOARD_FILE_NAME)
        print(f"Self-test using temporary file: {LEADERBOARD_FULL_PATH} and Max Entries: {LEADERBOARD_MAX_ENTRIES}")

    # Clear leaderboard for testing if it's a test file
    if LEADERBOARD_FILE_NAME == "test_leaderboard.json" and os.path.exists(LEADERBOARD_FULL_PATH):
        os.remove(LEADERBOARD_FULL_PATH)
        print(f"Removed test file: {LEADERBOARD_FULL_PATH}")

    print("\nInitial scores (should be empty or from previous test run if not cleared):")
    for s_entry in get_top_scores(): print(s_entry)

    print("\nAdding scores...")
    add_score("ALICE", 1000, 3)
    add_score("BOB", 1500, 5)
    add_score("CHARLIE", 1000, 2) # Lower level than Alice for same score
    add_score("DAVID", 2000, 1)
    add_score("EVE", 1500, 5)    # Same score and level as Bob, should be sorted by name (Bob before Eve)
    add_score("FRANK", 2500, 6)  # Should push someone out if MAX_ENTRIES is 5
    add_score("GRACE", 500, 1)   # Should not make it if MAX_ENTRIES is 5 and others are higher

    print("\nScores after adding entries:")
    for s_entry in get_top_scores():
        print(s_entry)

    print(f"\nMax entries allowed: {LEADERBOARD_MAX_ENTRIES}")
    print(f"Current number of scores: {len(get_top_scores())}")

    print("\nChecking high scores:")
    print(f"Is 1200, level 4 a high score? {is_high_score(1200, 4)}")
    print(f"Is 400, level 1 a high score? {is_high_score(400, 1)}")
    # Test with a score equal to the lowest but higher level
    current_scores = get_top_scores()
    if current_scores and len(current_scores) == LEADERBOARD_MAX_ENTRIES:
        lowest_score_val = current_scores[-1]['score']
        print(f"Is {lowest_score_val}, level 10 a high score (same score as lowest, higher level)? {is_high_score(lowest_score_val, 10)}")
        print(f"Is {lowest_score_val}, level 1 a high score (same score as lowest, lower/same level)? {is_high_score(lowest_score_val, 1)}")
    
    print("\nTest with invalid inputs:")
    add_score("", 5000, 10) # Empty name
    add_score("INVALID", "notascore", 10) # Invalid score type

    # Clean up test file
    if LEADERBOARD_FILE_NAME == "test_leaderboard.json" and os.path.exists(LEADERBOARD_FULL_PATH):
        # os.remove(LEADERBOARD_FULL_PATH)
        # print(f"Removed test file: {LEADERBOARD_FULL_PATH} at end of test.")
        pass # Keep it for inspection if needed