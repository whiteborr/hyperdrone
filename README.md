# 🚀 HYPERDRONE

## 📖 Overview

HYPERDRONE is a dynamic top-down 2D shooter where players pilot advanced drones through procedurally generated mazes. The objective is to navigate challenging environments, engage hostile AI drones, collect valuable items, and progress through increasingly difficult levels. The game features a selection of unique playable drones, a sophisticated weapon system with multiple modes, intelligent enemy behaviors (including a multi-phase boss), a clear informative UI, particle effects, and a special end-game "...

## 🎮 Core Features

### Multiple Playable Drones

Unlock and select from a variety of drones (e.g., DRONE, VANTIS, RHINOX, ZEPHYR, STRIX, OMEGA-9, PHANTOM, Architect-X), each with distinct base stats (HP, speed, turn speed, fire rate multiplier, bullet damage multiplier) and some with special abilities (e.g., Omega-9's random stat boosts, Phantom's cloak). Drone configurations are defined in `drone_management/drone_configs.py`.

### Drone Unlocks & Progression

Unlock new drones by reaching certain player levels, collecting in-game currency (cores), defeating specific bosses, or acquiring blueprints (e.g., from the Architect's Vault).

Player progress is managed by the DroneSystem and saved locally in `data/drone_unlocks.json`.

### Dynamic Weapon System

Cycle through multiple weapon modes: Single Shot, Tri-Shot, Rapid Single, Rapid Tri-Shot, Big Shot, Bounce Shot, Pierce Shot, Heatseeker Missiles, Heatseeker + Rapid Bullets, and Chain Lightning.

Weapon logic uses the Strategy pattern with classes in `entities/weapon_strategies.py`, making it easy to add new weapon types.

Projectile logic is handled in `entities/bullet.py`.

Collect weapon upgrade power-ups to advance to the next weapon mode.

### Power-ups

- **Shield**: Temporary invincibility.
- **Speed Boost**: Increases drone speed and activates a co-shield with particle effects.
- **Weapon Upgrade**: Cycles to the next weapon mode.

Logic for power-ups is found in `entities/collectibles.py`.

### Enemy Drones & AI

Enemy AI uses a behavior-based design pattern for modular and extensible behaviors:
- Base behaviors in `ai/behaviors.py`
- Enemies delegate AI logic to behavior objects (`entities/enemy.py`)
- TR3B enemies use patrol, chase, and dash behaviors (`entities/tr3b_enemy.py`)

The Maze Guardian is a multi-phase boss with laser sweeps, minion summoning, shields, and arena changes (`entities/maze_guardian.py`).

Sentinel Drones are summoned minions.

Prototype Drones appear in the Architect's Vault.

For detailed information about the AI behavior system, see [README_AI_BEHAVIORS.md](README_AI_BEHAVIORS.md)

### Collectibles

- **Rings**: Progress and score.
- **Cores**: Currency.
- **Core Fragments**: Unlock the Architect's Vault and provide buffs inside it.

Managed in `entities/collectibles.py`.

### Architect's Vault

A special sequence with:

- Entry puzzle and terminals.
- Multi-wave combat.
- Boss fight.
- Timed extraction.
- Unique rewards (e.g., Architect-X blueprint, lore entries).

### Procedural Maze Generation

Generated with Recursive Backtracker.

Dynamic wall changes managed in `entities/maze.py`.

### Particle System

Visual effects for explosions and thrust in `entities/particle.py`.

### Scoring & Leaderboard

Points for rings and enemies.

Local leaderboard in `hyperdrone_core/leaderboard.py`.

### Settings Management System

The game now uses a robust settings management system:

- `constants.py`: Contains unchanging constants (colors, state names, etc.)
- `data/settings.json`: Contains gameplay parameters organized by category
- `data/asset_manifest.json`: Contains all asset paths organized by type
- `settings_manager.py`: Handles loading and accessing settings
- `game_settings.py`: Compatibility layer for existing code

Settings are organized into categories like display, gameplay, weapons, enemies, etc., making the game highly configurable and moddable without code changes.

### UI Panel

Shows score, level, time, cores, health, weapon status, power-up timers, lives, and collectibles.

Managed in `ui/ui.py`.

### Sound Effects & Music

Stored in `assets/sounds/`.

### Game States

Handled by `hyperdrone_core/state_manager.py` using the State Design Pattern.

### Sliding Ring Puzzle Minigame

Triggered by interacting with a new "Ancient Alien Terminal" entity.

- 3 concentric, rotatable rings with image-based symbols.
- Use keys 1, 2, 3 to rotate rings.
- Solved by aligning rings to their original 0-degree rotation.
- Rewards include cores and lore unlocks (e.g., "Element-115 Casing").
- Terminal is removed after puzzle completion.
- Known issue: ring layering may require asset adjustment.

## 📁 Project Structure

hyperdrone/
├── main.py
├── game_settings.py
├── settings_manager.py
├── constants.py
├── hyperdrone_core/
│   ├── game_loop.py
│   ├── state_manager.py
│   ├── event_manager.py
│   ├── player_actions.py
│   ├── combat_controller.py
│   ├── ui_flow_controller.py
│   ├── level_manager.py
│   ├── pathfinding.py
│   └── leaderboard.py
├── entities/
│   ├── player.py
│   ├── enemy.py
│   ├── maze_guardian.py
│   ├── bullet.py
│   ├── collectibles.py
│   ├── maze.py
│   └── particle.py
├── drone_management/
│   ├── base_drone.py
│   ├── drone_configs.py
│   └── drone_system.py
├── ui/
│   └── ui.py
├── assets/
│   ├── fonts/
│   ├── images/
│   └── sounds/
└── data/
    ├── leaderboard.json
    ├── drone_unlocks.json
    ├── settings.json
    └── asset_manifest.json

## 🎮 Game Controls

| Key         | Action                                | Context                      |
|-------------|----------------------------------------|------------------------------|
| ↑ Arrow     | Thrust Forward (Toggle On)             | Gameplay                     |
| ↓ Arrow     | Stop Thrust (Toggle Off)               | Gameplay                     |
| ←/→ Arrows  | Rotate Drone                           | Gameplay                     |
| Spacebar    | Fire Weapon                            | Gameplay (Combat States)     |
| P           | Pause / Unpause Game                   | Gameplay, Architect's Vault  |
| S           | Cycle Weapon                           | Gameplay (If Alive & Not Paused) |
| C           | Activate Cloak (Phantom Only)          | Gameplay                     |
| 1, 2, 3     | Activate Vault Terminals               | Architect's Vault (Puzzle)   |
| 1–9         | Rotate Rings                           | Sliding Ring Puzzle          |
| Enter       | Confirm / Select Option                | Menus, Puzzle Results        |
| Esc         | Back / Main Menu                       | Menus, Ring Puzzle           |
| R           | Restart Game                           | Game Over Screen             |
| M           | Main Menu                              | Game Over, Pause Menu        |
| L           | View Leaderboard                       | Game Over, Pause Menu        |
| Q           | Quit Game                              | Menus                        |

## 🖥️ Windows Setup Instructions

### Step 1: Install Python

- Download from the official Python site.
- **Check** "Add Python to PATH" during install.

### Step 2: Verify Python

```bash
python --version
```

## ⚙️ Game Installation

### Step 3: Download the Game Files

```bash
cd C:\YourPreferredDirectory
git clone <repository_url>
cd hyperdrone
```

Or extract ZIP and navigate there.

### Step 4: Install Pygame

```bash
pip install pygame
```

### Step 5: Run the Game

```bash
python main.py
```

## 🛠️ Build a Windows Executable (.exe)

### Step 1: Install PyInstaller

```bash
pip install pyinstaller
```

### Step 2: Compile the Game

```bash
pyinstaller --onefile --windowed --add-data "assets;assets" --add-data "data;data" main.py
```

### Step 3: Locate Executable

- `dist/main.exe` (or in folder if not using `--onefile`)

### Step 4: Run or Share

- Share single `.exe` or the folder.

## 💡 Future Enhancements & Modding Ideas

- Expanded Power-Ups & Collectibles: EMP, score multipliers
- Greater Enemy Variety & Smarter AI
- Enhanced Maze & Level Design
- More Drone Abilities
- Visual & Audio Polish
- UI/UX Improvements
- Online Leaderboards

## 🔧 Settings System

### How to Mod the Game

1. Edit `data/settings.json` to change gameplay parameters
2. Edit `data/asset_manifest.json` to change assets

No code changes required!

## 🔫 Weapon System Architecture

The weapon system uses the Strategy design pattern to make it easy to add, modify, and maintain different weapon types.

### Key Components

1. **BaseWeaponStrategy**: Abstract base class that defines the interface for all weapon strategies
2. **Concrete Strategy Classes**: Implementations for each weapon type (e.g., `TriShotWeaponStrategy`, `HeatseekerWeaponStrategy`)
3. **PlayerDrone**: Context class that holds and uses the current weapon strategy

### Adding New Weapons

To add a new weapon type:

1. Add a new weapon mode constant in `constants.py`
2. Create a new weapon strategy class in `entities/weapon_strategies.py` that extends `BaseWeaponStrategy`
3. Add the new strategy class to the `weapon_strategies` dictionary in `PlayerDrone.__init__()`
4. Add the new weapon mode to the `WEAPON_MODES_SEQUENCE` list in settings

### Benefits

- **Decoupling**: The `PlayerDrone` class no longer needs to know the details of how each weapon works
- **Encapsulation**: Each weapon's behavior is now fully contained in its own strategy class
- **Extensibility**: Adding new weapons is now much easier - just create a new strategy class
- **Maintainability**: The code is more modular and easier to understand

For detailed information about the weapon system refactoring, see [README_WEAPON_SYSTEM.md](README_WEAPON_SYSTEM.md)

### Settings Categories

- **display**: Screen resolution, FPS, volume settings
- **gameplay**: Player stats, game world settings
- **weapons**: Bullet properties, weapon cooldowns
- **enemies**: Enemy stats, attack properties
- **bosses**: Boss stats, attack properties
- **powerups**: Powerup properties, effects
- **collectibles**: Collectible properties, goals
- **progression**: Level timers, rewards, leaderboard

## Recent Improvements

### Architecture Refactoring

1. **State Design Pattern**: Replaced the string-based scene manager with a proper State Design Pattern implementation in `state_manager.py`
2. **Strategy Pattern for Weapons**: Implemented the Strategy pattern for weapon systems in `entities/weapon_strategies.py`, making it easier to add and modify weapon types
3. **Behavior Pattern for Enemy AI**: Implemented a behavior-based design pattern for enemy AI in `ai/behaviors.py`, making it easier to create and combine different enemy behaviors
4. **Controller Classes**: Added specialized controller classes for better separation of concerns:
   - `combat_controller.py`: Handles all combat-related logic
   - `ui_flow_controller.py`: Manages UI navigation and state
   - `level_manager.py`: Handles level progression and scoring
5. **Collision Optimization**: Improved collision detection using pygame's `groupcollide` for better performance
6. **Pathfinding Module**: Extracted pathfinding logic into a dedicated module for better maintainability

### Bug Fixes

1. Fixed issues with settings menu navigation
2. Improved error handling in the UI system
3. Fixed weapon selection in the settings menu

## Recommendations for Future Development

1. **Settings Documentation**: Create a comprehensive settings documentation file
2. **Settings UI**: Update the settings UI to reflect the new categorized structure
3. **Settings Validation**: Add validation for settings values to prevent invalid configurations
4. **Settings Presets**: Implement settings presets for different difficulty levels or play styles
5. **Refactor UI States**: Continue refactoring UI states to use the State Design Pattern consistently
