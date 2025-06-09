# entities/__init__.py

from .base_drone import BaseDrone
from .player import PlayerDrone # CORRECTED: Import PlayerDrone directly
from .enemy import Enemy, SentinelDrone, DefenseDrone
from .bullet import Bullet, Missile, LightningZap
from .collectibles import (
    Ring, WeaponUpgradeItem, ShieldItem, SpeedBoostItem, 
    CoreFragmentItem, VaultLogItem, GlyphTabletItem, AncientAlienTerminal, ArchitectEchoItem
)
from .particle import Particle
from .maze_guardian import MazeGuardian 
from .escape_zone import EscapeZone
from .core_reactor import CoreReactor
from .turret import Turret
from .maze import Maze # Chapter 1 Maze
from .maze_chapter2 import MazeChapter2 # Chapter 2 Maze

__all__ = [
    "AncientAlienTerminal",
    "ArchitectEchoItem",
    "BaseDrone",
    "Bullet",
    "CoreFragmentItem",
    "CoreReactor",
    "Enemy",
    "EscapeZone",
    "GlyphTabletItem",
    "LightningZap",
    "Maze", 
    "MazeChapter2", 
    "MazeGuardian",
    "Missile",
    "Particle",
    "PlayerDrone", # The class PlayerDrone is now directly available
    "Ring",
    "SentinelDrone",
    "ShieldItem",
    "SpeedBoostItem",
    "Turret",
    "VaultLogItem",
    "WeaponUpgradeItem"
]
