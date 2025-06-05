
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

Projectile logic is handled in `entities/bullet.py`.

Collect weapon upgrade power-ups to advance to the next weapon mode.

### Power-ups

- **Shield**: Temporary invincibility.
- **Speed Boost**: Increases drone speed and activates a co-shield with particle effects.
- **Weapon Upgrade**: Cycles to the next weapon mode.

Logic for power-ups is found in `entities/collectibles.py`.

### Enemy Drones & AI

AI drones navigate using A* pathfinding and shoot at the player (`entities/enemy.py`).

The Maze Guardian is a multi-phase boss with laser sweeps, minion summoning, shields, and arena changes (`entities/maze_guardian.py`).

Sentinel Drones are summoned minions.

Prototype Drones appear in the Architect's Vault.

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

### Customizable Game Settings

Adjust game parameters in `game_settings.py`.

### UI Panel

Shows score, level, time, cores, health, weapon status, power-up timers, lives, and collectibles.

Managed in `ui/ui.py`.

### Sound Effects & Music

Stored in `assets/sounds/`.

### Game States

Handled by `hyperdrone_core/scene_manager.py`.

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
├── hyperdrone_core/
│   ├── game_loop.py
│   ├── scene_manager.py
│   ├── event_manager.py
│   ├── player_actions.py
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
    └── drone_unlocks.json

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
