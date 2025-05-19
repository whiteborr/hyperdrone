import json
import os

LEADERBOARD_FILE = "leaderboard.json"
MAX_SCORES = 10

def load_scores():
    """Loads scores from the leaderboard file."""
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, 'r') as f:
            scores = json.load(f)
            # Ensure scores are sorted, primarily by score (desc), then by level (desc), then by name (asc) for tie-breaking
            scores.sort(key=lambda x: (-x.get('score', 0), -x.get('level', 0), x.get('name', '')))
            return scores
    except (IOError, json.JSONDecodeError):
        print(f"Error loading or parsing {LEADERBOARD_FILE}. Returning empty list.")
        return []

def save_scores(scores):
    """Saves scores to the leaderboard file."""
    try:
        # Ensure scores are sorted before saving
        scores.sort(key=lambda x: (-x.get('score', 0), -x.get('level', 0), x.get('name', '')))
        with open(LEADERBOARD_FILE, 'w') as f:
            json.dump(scores, f, indent=4)
    except IOError:
        print(f"Error: Could not save scores to {LEADERBOARD_FILE}")

def add_score(name, score, level):
    """Adds a new score (and level) to the leaderboard if it qualifies."""
    scores = load_scores()
    new_score_entry = {'name': name, 'score': score, 'level': level}

    # Check if the score is high enough or if there's space
    # Qualification can be more complex, e.g., higher score, or same score but higher level
    should_add = False
    if len(scores) < MAX_SCORES:
        should_add = True
    else:
        # Qualifies if score is higher, or score is same and level is higher
        # than the current lowest score on the leaderboard
        if score > scores[-1].get('score', 0):
            should_add = True
        elif score == scores[-1].get('score', 0) and level > scores[-1].get('level', 0):
            should_add = True
            
    if should_add:
        scores.append(new_score_entry)
        # Sort by score (descending), then level (descending), then by name (ascending)
        scores.sort(key=lambda x: (-x.get('score', 0), -x.get('level', 0), x.get('name', '')))
        
        # Keep only the top MAX_SCORES
        scores = scores[:MAX_SCORES]
        save_scores(scores)
        print(f"Score added for {name}: Score {score}, Level {level}")
        return True
    
    print(f"Score for {name} (Score: {score}, Level: {level}) did not qualify for leaderboard.")
    return False

def get_top_scores():
    """Returns the top scores."""
    return load_scores()

def is_high_score(score, level):
    """Checks if a score and level are high enough to be on the leaderboard."""
    scores = load_scores()
    if len(scores) < MAX_SCORES:
        return True
    if not scores: 
        return True
    
    # Check against the last entry (lowest score on the full leaderboard)
    # A new score is "high" if it's better than the worst score currently on the board
    last_entry = scores[-1]
    if score > last_entry.get('score', 0):
        return True
    if score == last_entry.get('score', 0) and level > last_entry.get('level', 0):
        return True
        
    return False

if __name__ == '__main__':
    # Test functions
    print("Initial scores:", get_top_scores())
    
    # Clear leaderboard for testing
    # save_scores([]) 
    # print("Cleared scores:", get_top_scores())

    add_score("Alice", 100, 3)
    add_score("Bob", 150, 5)
    add_score("Charlie", 100, 2) # Lower level than Alice for same score
    add_score("David", 200, 1)
    add_score("Eve", 150, 5)    # Same score and level as Bob, should be sorted by name
    
    print("\nScores after adding some entries:")
    for s in get_top_scores():
        print(s)

    print("\nIs 120, level 4 a high score?", is_high_score(120, 4))
    print("Is 90, level 1 a high score?", is_high_score(90, 1))
    print("Is 100, level 3 a high score (same as Alice)?", is_high_score(100,3)) # Should be true if list not full, or better than last
    print("Is 100, level 4 a high score (same score, higher level than Alice)?", is_high_score(100,4))