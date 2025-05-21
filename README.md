# HYPERDRONE

## Overview

HYPERDRONE is a dynamic top-down 2D game where players pilot an advanced drone through procedurally generated mazes. The objective is to navigate challenging environments, engage hostile AI drones, collect valuable items, and progress through increasingly difficult levels. The game features precise player controls, a sophisticated weapon system with multiple modes, intelligent enemy behaviors, a clear informative UI, and a special end-game "Architect's Vault" sequence. Developed using Python and Pygame, the project boasts a modular architecture for easy enhancement and maintenance.

## Core Features

* **Multiple Playable Drones:** Unlock and select from a variety of drones (e.g., DRONE, VANTIS, RHINOX, ZEPHYR, STRIX, OMEGA-9, PHANTOM, Architect-X), each with distinct base stats (HP, speed, turn speed, fire rate) and some with special abilities (e.g., Omega-9's random stat boosts, Phantom's cloak).

* **Drone Unlocks & Progression:**

  * Unlock new drones by reaching certain player levels, collecting in-game currency (cores), or acquiring blueprints (e.g., from the Architect's Vault).

  * Player progress (level, cores, unlocked drones, selected drone, collected core fragments, Architect's Vault completion status) is saved locally.

* **Dynamic Weapon System:**

  * Cycle through multiple weapon modes: Single Shot, Tri-Shot, Rapid Single, Rapid Tri-Shot, Big Shot, Bounce Shot, Pierce Shot, Heatseeker Missiles, Heatseeker + Rapid Bullets, and Chain Lightning.

  * Collect weapon upgrade power-ups to advance to the next weapon mode.

* **Power-ups:**

  * **Shield:** Provides temporary invincibility.

  * **Speed Boost:** Temporarily increases drone speed and activates a co-shield.

  * **Weapon Upgrade:** Cycles to the next available weapon mode.

* **Enemy Drones:** Encounter AI-controlled enemy drones (standard and tougher "Prototype Drones" in the Vault) that navigate the maze and shoot at the player.

* **Collectibles:**

  * **Rings:** Collect rings in each level to progress and earn score/cores.

  * **Cores:** In-game currency used for unlocking drones.

  * **Core Fragments:** Collect unique fragments to gain access to the Architect's Vault and receive minor buffs while inside.

* **Architect's Vault:** A special multi-phase end-game sequence triggered by collecting all Core Fragments, featuring:

  * Introductory phase.

  * Entry puzzle requiring activation of terminals.

  * Multi-wave gauntlet against Prototype Drones.

  * Timed extraction sequence.

  * Unique rewards upon successful completion (e.g., Architect-X drone blueprint).

* **Procedural Maze Generation:** Mazes are generated using a Growing Tree algorithm, providing a different layout each time.

* **Scoring & Leaderboard:**

  * Earn points for collecting rings and defeating enemies.

  * Local leaderboard saves top scores with player names and levels achieved.

  * Leaderboard is disabled if game settings are modified from defaults.

* **Customizable Game Settings:** Adjust various game parameters like player health, lives, speed, weapon stats, enemy stats, level timer, and fullscreen mode via an in-game settings menu.

* **UI Panel:** Displays score, level, time remaining, player cores, health, weapon charge/type, active power-up duration, lives, and collected rings/fragments.

* **Sound** Effects & **Music:** Includes sound effects for game events and background music for menus, gameplay, and the Architect's Vault.

* **Game States:** Well-defined states for Main Menu, Drone Selection, Settings, Gameplay (Playing, Bonus Level), Paused, Game Over, Name Entry, Leaderboard, and multiple Architect's Vault phases.

## 🖥️ Windows Setup Instructions (No Python Installed)

### Step 1: Install Python

1. Go to the official [Python Downloads for Windows](https://www.python.org/downloads/windows/) page.

2. Download the latest stable version of Python 3 (e.g., Python 3.10.x or newer).

3. **Important**: During installation, **check the box that says "Add Python to PATH"**.

4. Complete the installation.

### Step 2: Verify Python is Installed

1. Press `Win + R`, type `cmd`, and press **Enter**.

2. In the command prompt, type:


python --version


You should see something like: `Python 3.10.7`. If not, restart your computer and try again.

## 🚀 Game Installation (After Python is Installed)

### Step 3: Download the Game Files

1. Navigate to your preferred directory in the command prompt.


cd C:\YourPreferredDirectory


2. Clone the repository (if you have Git installed):


git clone https://github.com/your-username/hyperdrone.git
cd hyperdrone


(Replace `your-username/hyperdrone.git` with the actual repository URL if applicable)
Alternatively, download the ZIP file of the game from its source (e.g., GitHub) and extract it to a folder named `hyperdrone`. Then navigate into this folder in your command prompt.

### Step 4: Install Pygame

In the command prompt, inside the `hyperdrone` project directory, type:


pip install pygame


### Step 5: Run the Game

In the command prompt, inside the `hyperdrone` project directory, type:


python main.py


🎮 The game should launch in a new window.

## File Structure (Key Files)


hyperdrone/
├── main.py                     # Main entry point for the game.
├── game_loop.py                # Core game logic, GameController class.
├── scene_manager.py            # Manages game states and transitions.
├── event_manager.py            # Handles user input and game events.
├── ui.py                       # Manages all UI elements (HUD, menus).
├── player.py                   # Player drone logic, movement, abilities.
├── player_actions.py           # Handles player-initiated actions.
├── enemy.py                    # Enemy drone AI and behavior.
├── bullet.py                   # Logic for bullets, missiles, lightning.
├── maze.py                     # Procedural maze generation.
├── game_settings.py            # Game configuration, constants, dynamic settings.
├── drone_configs.py            # Definitions for all playable drones.
├── drone_system.py             # Manages drone unlocks, player progress.
├── collectibles.py             # Logic for rings, power-ups, core fragments.
├── leaderboard.py              # Manages loading and saving high scores.
├── base_drone.py               # Base class for drone entities.
├── assets/
│   ├── fonts/                  # Game fonts.
│   ├── images/                 # Sprites, icons, UI elements.
│   └── sounds/                 # Sound effects and music.
└── data/
├── leaderboard.json        # Saved high scores.
└── drone_unlocks.json      # Saved player progression and unlocks.


## Game Controls

| Key | Action | Context | 
 | ----- | ----- | ----- | 
| ↑ Arrow | Thrust Forward (Toggle On) | Gameplay | 
| ↓ Arrow | Stop Thrust (Toggle Off) | Gameplay | 
| ←/→ Arrows | Rotate Drone | Gameplay | 
| Spacebar | Fire Weapon | Gameplay (Combat States) | 
| P | Pause / Unpause Game | Gameplay, Architect's Vault | 
| S | Cycle Weapon | Gameplay (If Player Alive & Not Paused) | 
| C | Activate Cloak (If Phantom Drone Equipped) | Gameplay (If Player Alive & Not Paused) | 
| 1, 2, 3 | Activate Vault Terminals | Architect's Vault (Entry Puzzle) | 
| Enter | Select Option / Confirm | Menus, Name Entry, Vault Success/Failure | 
| Esc | Back / Main Menu | Drone Select, Settings, Leaderboard, Pause (Vault) | 
| R | Restart Game | Game Over Screen | 
| M | Main Menu | Game Over, Pause Menu, Vault Success/Failure | 
| L | View Leaderboard | Game Over, Pause Menu (Playing State) | 
| Q | Quit Game | Main Menu, Game Over, Leaderboard, Pause Menu | 

## Future Enhancements & Modding Ideas

(Refer to `IMPROVEMENTS.md` for a more detailed list)

* **Expanded** Power-Ups **& Collectibles:** New items like EMP blasts, score multipliers.

* **Greater Enemy Variety & Smarter AI:** Introduce new enemy types (Swarmers, Tanks, Snipers, Support Drones) with advanced pathfinding.

* **Enhanced Maze & Level Design:** Themed levels, dynamic hazards (laser grids, moving walls), interactive elements (switches, breakable walls), and diverse objectives.

* **Boss Battles:** Implement challenging boss encounters at key stages.

* **Deeper Player Progression:** Permanent upgrades using collected rings/cores.

* **More Drone Abilities:** Cooldown-based special abilities for various drones.

* **Visual & Audio Polish:** Particle effects, distinct enemy designs, varied soundscapes.

* **UI/UX Improvements:** Mini-map, detailed game over statistics, optional story elements.

## 🛠️ Compile to Windows Executable (.exe)

You can convert the Python game into a standalone executable using PyInstaller.

### Step 1: Install PyInstaller


pip install pyinstaller


### Step 2: Compile the Game

Open a command prompt in the project directory (where `main.py` is located) and run:


pyinstaller --onefile --windowed --add-data "assets;assets" --add-data "data;data" main.py


* `--onefile`: Creates a single `.exe` file (may take longer to start).

* `--windowed`: Prevents a console window from opening with the game.

* `--add-data "assets;assets"`: Bundles the entire `assets` folder into the executable, making it available at runtime in a relative `assets` path.

* `--add-data "data;data"`: Bundles the `data` folder. This is important if you want to ship default `leaderboard.json` or `drone_unlocks.json`, though these files are also created if missing.

If you prefer a faster startup and don't mind multiple files, omit `--onefile`. The executable and its dependencies will be in a folder within `dist`.

### Step 3: Locate the Executable

After the build completes, you’ll find your game in the `dist/main` folder (if not using `--onefile`) or as `dist/main.exe` (if using `--onefile`).

### Step 4: Run or Share

You can now run the `.exe` to play the game. If you created a folder, you'll need to distribute the entire folder. If you used `--onefile`, you can distribute the single `main.exe` file.
