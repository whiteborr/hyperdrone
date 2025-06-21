# hyperdrone_core/__init__.pyAdd commentMore actions

# Import the main GameController class to be accessible when importing hyperdrone_core
from .game_loop import GameController

# Import other core manager classes
from .state_manager import StateManager
from .event_manager import EventManager
from .player_actions import PlayerActions
from .enemy_manager import EnemyManager
from .ring_puzzle_module import RingPuzzle
from .wave_manager import WaveManager
from .boss_fight_state import BossFightState
from .corrupted_sector_state import CorruptedSectorState
from .harvest_chamber_state import HarvestChamberState # Import the new state

# Import NEW sub-controller classes
from .combat_controller import CombatController
from .puzzle_controller import PuzzleController
from .ui_flow_controller import UIFlowController

# Import the AssetManager and Camera classes
from .asset_manager import AssetManager
from .camera import Camera

# Import the leaderboard module directly if it contains functions to be used
from . import leaderboard

# Define what is available for import when using 'from hyperdrone_core import *'
__all__ = [
    "GameController",
    "StateManager",
    "EventManager",
    "PlayerActions",
    "EnemyManager",
    "RingPuzzle",
    "WaveManager",
    "BossFightState",
    "CorruptedSectorState",
    "HarvestChamberState",
    "CombatController",
    "PuzzleController",
    "UIFlowController",
    "AssetManager",
    "Camera",
    "leaderboard"
]