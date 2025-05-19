# HYPERDRONE

## Overview

HYPERDRONE is a dynamic top-down 2D game where players pilot an advanced drone through procedurally generated mazes. The objective is to navigate challenging environments, engage hostile AI drones, collect valuable items, and progress through increasingly difficult levels. The game features precise player controls, a sophisticated weapon system with multiple modes, intelligent enemy behaviors, and a clear, informative UI. Developed using Python and Pygame, the project boasts a modular architecture for easy enhancement and maintenance.

### Core Features

* **Multiple Playable Drones:** Unlock and select from a variety of drones, each with distinct base stats (HP, speed, turn speed, fire rate) and some with special abilities (e.g., Omega-9's random stat boosts, Phantom's cloak).
* **Drone Unlocks & Progression:**
  * Unlock new drones by reaching certain player levels, collecting in-game currency (cores), or defeating specific bosses (future feature).
  * Player progress (level, cores, unlocked drones, selected drone) is saved locally.
* **Dynamic Weapon System:**
    * Cycle through multiple weapon modes (Single Shot, Tri-Shot, Rapid Fire, Big Shot, Bounce Shot, Pierce Shot, Heatseeker Missiles).
    * Collect weapon upgrade power-ups to advance to the next weapon mode.
* **Power-ups:**
    * **Shield:** Provides temporary invincibility.
    * **Speed Boost:** Temporarily increases drone speed and activates a co-shield.
* **Enemy Drones:** Encounter AI-controlled enemy drones that navigate the maze and shoot at the player.
* **Collectibles:**
    * **Rings:** Collect rings in each level to progress and earn score/cores.
    * **Cores:** In-game currency used for unlocking drones.
* **Scoring & Leaderboard:**
    * Earn points for collecting rings and defeating enemies.
    * Local leaderboard saves top scores with player names and levels achieved.
    * Option to disable leaderboard if game settings are modified from defaults.
* **Customizable Game Settings:** Adjust various game parameters like player health, lives, speed, weapon stats, enemy stats, and level timer via an in-game settings menu.
* **UI Panel:** Displays score, level, time remaining, player cores, health, weapon charge, active power-up duration, lives, and collected rings.
* **Sound Effects & Music:** Includes sound effects for game events and background music for menus/gameplay.
* **Game States:** Well-defined states for Main Menu, Drone Selection, Settings, Gameplay, Paused, Game Over, Name Entry, and Leaderboard.

## 🖥️ Windows Setup Instructions (No Python Installed)

### Step 1: Install Python

1. Go to the official [Python Downloads for Windows](https://www.python.org/downloads/windows/) page.
2. Download the latest version of Python 3 (e.g., Python 3.12.x).
3. **Important**: During installation, **check the box that says "Add Python to PATH"**.
4. Complete the installation.

### Step 2: Verify Python is Installed

1. Press `Win + R`, type `cmd`, and press **Enter**.
2. In the command prompt, type:
    `cmd`
    `python --version`
    You should see something like:
   `Python 3.12.0`

    If not, restart your computer and try again.

## 🚀 Game Installation (After Python is Installed)

### Step 3: Download the Game Files

```cmd
cd C:\YourPreferredDirectory
git clone [https://github.com/alliedgwailou/alliedgwailou.git](https://github.com/alliedgwailou/alliedgwailou.git)
cd alliedgwailou

Or download ZIP manually from the GitHub repo and extract it.

Step 4: Install Pygame
pip install pygame

Step 5: Run the Game
python main.py

🎮 The game should launch in a new window.

File Structure
project_root/
├── main.py                # Entry point
├── game.py                # Core game loop and state handling
├── base_drone.py          # Base class for all drones
├── player.py              # Player-specific drone logic
├── enemy.py               # Enemy drone AI
├── bullet.py              # Bullet & missile logic
├── maze.py                # Procedural maze generation
├── game_settings.py       # Configuration and tunable parameters
├── leaderboard.py         # Leaderboard management
└── assets/                # Images, sounds, fonts

Game Controls
Key

Action

↑ Arrow

Thrust forward

↓ Arrow

Cancel thrust (coast)

←/→ Arrows

Rotate drone

Spacebar

Fire weapon

P

Pause / Unpause

R

Restart (Game Over screen)

M

Main Menu

L

View Leaderboard

Q

Quit (from Pause or Game Over)

Modding Ideas
Add new weapons or bullet types.

Introduce new enemy classes or behaviors.

Customize maze generation.

Add new power-ups.

Create new game modes (boss battles, time attack, etc).

Future Enhancements
Boss fights with unique mechanics.

Story/campaign mode.

Level-specific hazards.

Smarter enemy AI and formations.

More immersive sound design and visuals.

🛠️ Compile to Windows Executable (.exe)
You can convert the Python game into a standalone executable using PyInstaller.

Step 1: Install PyInstaller
pip install pyinstaller

Step 2: Compile the Game
Open a command prompt in the project directory and run:

pyinstaller --onefile --windowed main.py

--onefile: Creates a single .exe file

--windowed: Prevents a terminal from opening alongside the game window

Step 3: Locate the Executable
After the build completes, you’ll find your .exe in the dist/ folder:

project_root/
└── dist/
    └── main.exe

Step 4: Run or Share
You can now double-click the .exe to run the game or share it with others. Python is not required to run the .exe.

Note: If your game uses assets like fonts, images, or sounds, you may need to bundle them using the --add-data option:
bash pyinstaller --onefile --windowed --add-data "assets;assets" main.py 
(Use a semicolon ; to separate source and destination on Windows