# Improvements

## Gameplay Mechanics & Content

### Power-Ups & Collectibles Expansion

Planning to introduce new types of collectibles too:

* **EMP Blast**

– when picked up, this stuns all enemies on-screen briefly.

* **Score Multiplier** – Additinal point for killing all enemies and completing withing 120 seconds

### Enemy Variety & Smarter AI

Right now, enemy behavior is pretty basic: they move toward the player and shoot. Want to add some diversity with new enemy types:

* **Swarmers**

– weak but fast, they rely on numbers.

* **Tanks** – heavy armor, take more hits, and maybe deal more damage or have special attacks.
* **Snipers** – long-range, accurate shots but slow firing rate.
* **Support Drones** – could heal others or deploy shields.

Also want to upgrade enemy pathfinding. Instead of just homing in, something like A* would let them move through the maze better without getting stuck.

### Maze & Level Design Enhancements

`maze.py` already generates random mazes, which is great for replayability. Looking to deepen the system with:

* **Themed Levels**

– different visuals per level (e.g. tech, jungle, industrial).

* **Hazards & Obstacles**
– like laser grids, moving walls, or traps (slime, spikes).

* **Interactive Elements**
– switches, breakable walls, or explosive barrels.

* **New Objectives**
– variety beyond ring collection, like:
* Timed escape missions.
* Kill-target levels (e.g. take out all turrets).
* Escorting friendly drones to safety.

### Boss Battles

Planning to add boss enemies at key stages — they’ll need unique patterns, high health, and multi-phase attacks. These will serve as major difficulty spikes and reward moments.

### Player Progression & Special Abilities

* **Permanent Upgrades**

– between levels, use rings (or another currency) to buy stat boosts (speed, health, damage, shield recharge).

* **Drone Abilities**
– give the player cooldown-based abilities, maybe including:
* Dash/dodge
* Temporary shield
* High-powered laser shot
* EMP blast (could also be an ability, not just a pickup)

## Visuals and Audio

### Visual Feedback Improvements

Working on adding better visual cues and polish:

* **Particle Effects**
– for explosions, collisions, thrusters, power-up pickup.

* **Distinct Enemy Designs**
– would help make new enemy types stand out; could include animated bits like blinking lights or moving parts.

* **Impact Decals**
– small marks where bullets hit walls.

### Audio Enhancements

Basic sound effects are in, but more variety would help:

* Add different sounds for various weapons and enemy attacks.
* New audio cues for new power-ups.
* More dynamic explosion effects.
* Possibly vary the background music intensity depending on what's happening.

## UI & UX Improvements

* **Mini-Map** – helpful in maze layouts; maybe a fog-of-war style map that fills out as the player explores.
* **Game Over Screen** – display more stats like kill count, accuracy, total time, rings collected, etc.
* **Optional Story Elements** – maybe include light story beats or cutscenes between levels to give more context to the maze traversal.

These all build on ideas already touched on in the "Future Enhancements" section of the `README.md`, like having multiple levels and smarter AI. This is the current roadmap to improve overall depth and polish.
