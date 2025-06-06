# hyperdrone_core/__init__.py

# Import the main GameController class to be accessible when importing hyperdrone_core
from .game_loop import GameController

# Import other core manager classes
from .scene_manager import SceneManager
from .event_manager import EventManager
from .player_actions import PlayerActions
from .enemy_manager import EnemyManager
from .ring_puzzle_module import RingPuzzle # Assuming this is the correct name and location
from .wave_manager import WaveManager

# Import NEW sub-controller classes
from .combat_controller import CombatController
from .puzzle_controller import PuzzleController
from .ui_flow_controller import UIFlowController

# Import the NEW AssetManager class
from .asset_manager import AssetManager # <<< ADDED THIS LINE

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
    "WaveManager",
    "CombatController",
    "PuzzleController",
    "UIFlowController",
    "AssetManager",         # <<< ADDED AssetManager HERE
    "leaderboard"
]

# You can also add any package-level initialization code here if needed,
# though for this structure, it's often not necessary.
# Consider moving the "Hyperdrone Core Systems Initialized" print to a logging statement
# within the GameController or AssetManager if it's for debugging.
# print("Hyperdrone Core Systems (including AssetManager) Initialized.")