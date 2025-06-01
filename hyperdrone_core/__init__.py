# hyperdrone_core/__init__.py

# Import the main GameController class to be accessible when importing hyperdrone_core
from .game_loop import GameController

# Import other core manager classes
from .scene_manager import SceneManager
from .event_manager import EventManager
from .player_actions import PlayerActions
from .enemy_manager import EnemyManager
from .ring_puzzle_module import RingPuzzle
from .wave_manager import WaveManager # Added WaveManager

# Import the leaderboard module directly if it contains functions to be used
from . import leaderboard

# Define what is available for import when using 'from hyperdrone_core import *'
# It's generally good practice to explicitly list what you want to export.
__all__ = [
    "GameController",
    "SceneManager",
    "EventManager",
    "PlayerActions",
    "EnemyManager",
    "RingPuzzle",
    "WaveManager", # Added WaveManager
    "leaderboard"
]

# You can also add any package-level initialization code here if needed,
# though for this structure, it's often not necessary.
print("Hyperdrone Core Systems Initialized.")
