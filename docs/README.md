# 🚀 HYPERDRONE

## 📖 Overview

HYPERDRONE is a dynamic top-down 2D shooter where players pilot advanced drones through procedurally generated mazes and story-driven chapters. The objective is to navigate challenging environments, engage hostile AI drones, collect valuable items, and uncover the mystery of the Architect's Vault. The game features multiple playable drones, a sophisticated weapon system, intelligent enemy behaviors, particle effects, and a compelling storyline involving ancient alien technology and mysterious disappearances.

## 🎮 Core Features

### Multiple Playable Drones

Unlock and select from a variety of drones (DRONE, VANTIS, RHINOX, ZEPHYR, STRIX, OMEGA-9, PHANTOM, Architect-X), each with distinct base stats (HP, speed, turn speed, fire rate multiplier, bullet damage multiplier) and some with special abilities (e.g., Omega-9's random stat boosts, Phantom's cloak). Drone configurations are defined in `drone_management/drone_configs.py`.

**Currently Implemented**: Basic drone selection and unlocking system with progression tracking.

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

The game uses a data-driven enemy configuration system:

- All enemy types are defined in `data/enemy_configs.json`
- Enemy properties (health, speed, weapons) are configured in JSON
- New enemies can be added without code changes

The Maze Guardian is a multi-phase boss with laser sweeps, minion summoning, shields, and arena changes (`entities/maze_guardian.py`).

Sentinel Drones are summoned minions.

Prototype Drones appear in the Architect's Vault.

For detailed information about:

- AI behavior system: see [README_AI_BEHAVIORS.md](README_AI_BEHAVIORS.md)
- Enemy configuration system: see [README_ENEMY_CONFIG.md](README_ENEMY_CONFIG.md)

### Collectibles

- **Rings**: Progress and score.
- **Cores**: Currency.
- **Core Fragments**: Unlock the Architect's Vault and provide buffs inside it.

Managed in `entities/collectibles.py`.

### Story-Driven Chapters

The game features a complete narrative campaign with five distinct chapters:

**Chapter 1: The Entrance (Earth Core)** - Navigate collapsing mazes, collect rings and cores, face basic defenses while uncovering the Vault's instability.

**Chapter 2: The Guardian (Fire Core)** - Boss fight against the Maze Guardian to earn the Fire elemental core representing raw power.

**Chapter 3: Corruption Sector (Air Core)** - Navigate shifting mazes with corrupted logic, solve spatial puzzles to gain the Air core representing intellect.

**Chapter 4: The Harvest Chamber (Water Core)** - Vertical scrolling SHMUP through harvested wreckage, discover the truth behind MH370.

**Chapter 5: The Orichalc Core** - Tower defense finale with waves of enemies, make the ultimate choice about the Vault's fate.

**Architect's Vault** - A special end-game sequence with:
- Entry puzzle and terminals
- Multi-wave combat
- Boss fight
- Timed extraction
- Unique rewards (Architect-X blueprint, lore entries)

**Implementation Status**:
- ✅ Chapter 1 (Earth Core): Fully functional maze exploration
- ✅ Chapter 2 (Fire Core): Boss fight with Maze Guardian
- ✅ Chapter 3 (Air Core): Shifting maze with corrupted visuals
- ✅ Chapter 4 (Water Core): Vertical SHMUP with wave spawning
- ✅ Chapter 5 (Orichalc Core): Tower defense with final choice mechanics

### Procedural Maze Generation

Generated with Recursive Backtracker algorithm. Features:
- Dynamic maze dimensions based on screen resolution
- Border collision detection
- Wall line rendering and collision systems
- Support for different maze types (standard, architect_vault, corrupted)

Managed in `entities/maze.py`.

### Particle System

Comprehensive particle effects system featuring:
- Explosion effects with customizable colors and particle counts
- Thrust particles for player movement
- Particle lifetime management and alpha blending
- Camera-aware rendering for performance

Implemented in `entities/particle.py` with `ParticleSystem` class for managing particle collections.

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
│   ├── state.py
│   ├── earth_core_state.py          # Chapter 1 implementation
│   ├── event_manager.py
│   ├── game_events.py
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
│   ├── collectibles.py              # Includes Ring, Core, ParticleSystem
│   ├── elemental_core.py            # Earth/Fire/Air/Water cores
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
├── data/
│   ├── leaderboard.json
│   ├── drone_unlocks.json           # Player progression data
│   ├── settings.json
│   ├── asset_manifest.json
│   └── enemy_configs.json
└── docs/                            # Comprehensive documentation
    ├── GAME_CONFIGURATION.md
    ├── IMPROVEMENTS.md
    ├── LOGGING.md
    ├── README_AI_SYSTEM.md
    ├── README_WEAPON_SYSTEM.md
    └── STORYLINE.md

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
| F           | Activate Special Abilities             | Gameplay (Core Fragment Abilities) |
| G           | Gravity Control (Earth Core)           | Chapter 1 (After Core Collection) |
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

## Documentation

### Comprehensive Documentation Suite

The codebase now includes extensive documentation:

- **[API Documentation](API_DOCUMENTATION.md)**: Complete API reference with methods, parameters, and examples
- **[AI System Guide](README_AI_SYSTEM.md)**: Detailed guide to the behavior-based AI architecture
- **[Weapon System Guide](README_WEAPON_SYSTEM.md)**: Strategy pattern implementation and weapon creation
- **[Game Configuration](GAME_CONFIGURATION.md)**: Technical systems and architecture overview

### Code Documentation

All major classes and methods now include comprehensive docstrings with:
- Purpose and functionality descriptions
- Parameter specifications with types
- Return value documentation
- Usage examples and best practices
- Algorithm complexity analysis where applicable

## Recent Improvements

### Architecture Refactoring

1. **Event Bus System**: Implemented an event-driven architecture to decouple game components, allowing them to communicate without direct dependencies.
2. **State Design Pattern**: Replaced the string-based scene manager with a proper State Design Pattern implementation in `state_manager.py`
3. **Strategy Pattern for Weapons**: Implemented the Strategy pattern for weapon systems in `entities/weapon_strategies.py`, making it easier to add and modify weapon types
4. **Behavior Pattern for Enemy AI**: Implemented a behavior-based design pattern for enemy AI in `ai/behaviors.py`, making it easier to create and combine different enemy behaviors
5. **Data-Driven Enemy Configuration**: Implemented a JSON-based enemy configuration system in `data/enemy_configs.json`, making it easier to add and balance enemies
6. **Controller Classes**: Added specialized controller classes for better separation of concerns:
   - `combat_controller.py`: Handles all combat-related logic
   - `ui_flow_controller.py`: Manages UI navigation and state
   - `level_manager.py`: Handles level progression and scoring
7. **Collision Optimization**: Improved collision detection using pygame's `groupcollide` for better performance
8. **Pathfinding Module**: Extracted pathfinding logic into a dedicated module for better maintainability

### Recent Bug Fixes & Stability Improvements

1. **Import Resolution**: Fixed missing import errors for `ParticleSystem` and `Core` classes
2. **Maze System**: Resolved constructor parameter mismatches in maze generation
3. **Player Movement**: Fixed player input handling in Chapter 1 to enable proper movement
4. **Enemy AI**: Corrected enemy update method signatures and behavior initialization
5. **Asset Management**: Implemented fallback sprite generation for missing assets
6. **Collision Detection**: Fixed attribute errors in collision systems and camera handling
7. **Coordinate Systems**: Resolved world-to-grid and grid-to-world coordinate conversion issues

### Current Game Status

**Playable Features**:
- Chapter 1 (Earth Core) is fully functional with maze navigation, enemy combat, and collectibles
- Player movement and weapon systems work correctly
- Particle effects for explosions and movement
- Enemy AI with pathfinding and combat behaviors
- Collectible system (rings, cores) with progression tracking
- Settings system with JSON configuration

**Recently Completed**:
- All five story chapters with unique gameplay mechanics
- Complete narrative arc from Earth Core to final Vault choice
- Diverse gameplay styles: maze exploration, boss fights, puzzle solving, SHMUP, tower defense

**In Development**:
- Advanced enemy types and behaviors
- Enhanced particle effects and visual polish
- Audio integration and music system

## Current Development Status

### Completed Systems
- ✅ Core gameplay loop with maze navigation
- ✅ Player drone movement and weapon systems
- ✅ Enemy AI with behavior patterns and pathfinding
- ✅ Particle system for visual effects
- ✅ Collectible system with progression tracking
- ✅ Settings management with JSON configuration
- ✅ State management system
- ✅ Asset management with fallback generation

### Known Issues
- ⚠️ Some asset warnings for missing sprites (fallbacks implemented)
- ⚠️ Some UI states need State Pattern refactoring
- ⚠️ Chapter transitions need testing and polish

### Recommendations for Future Development

1. **Asset Creation**: Create proper sprite assets to replace fallback generation
2. **Chapter Polish**: Test and refine the newly implemented story chapters
3. **Settings UI**: Update the settings UI to reflect the new categorized structure
4. **Settings Validation**: Add validation for settings values to prevent invalid configurations
5. **Visual Polish**: Enhance particle effects and add more visual feedback
6. **Audio Integration**: Expand sound effects and music system
7. **Performance Optimization**: Optimize collision detection and rendering for larger levels
