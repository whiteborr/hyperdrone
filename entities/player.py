# entities/player.py
from pygame.sprite import Group
from pygame.time import get_ticks
from pygame.transform import smoothscale, rotate
from pygame.draw import rect as draw_rect
from math import radians, cos, sin
import logging 

from settings_manager import get_setting
from constants import (
    WHITE, RED, GREEN, YELLOW, BLACK, BLUE, CYAN, GOLD,
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
    WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
    WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
)

from .bullet import Bullet, Missile, LightningZap
from .particle import Particle
from .base_drone import BaseDrone
from .powerup_manager import PowerUpManager
from .weapon_strategies import (
    DefaultWeaponStrategy, TriShotWeaponStrategy, RapidSingleWeaponStrategy, RapidTriShotWeaponStrategy,
    BigShotWeaponStrategy, BounceWeaponStrategy, PierceWeaponStrategy, HeatseekerWeaponStrategy,
    HeatseekerPlusBulletsWeaponStrategy, LightningWeaponStrategy
)


logger = logging.getLogger(__name__)


class PlayerDrone(BaseDrone):
    """
    Player-controlled drone with weapons, abilities, and power-up management.
    
    Extends BaseDrone with player-specific functionality including:
    - Multiple weapon strategies with upgradeable modes
    - Active abilities system with cooldowns
    - Power-up effects (shield, speed boost, weapon upgrades)
    - Health management and damage handling
    - Sprite management based on current weapon mode
    
    Attributes:
        drone_id (str): Unique identifier for this drone type
        current_weapon_mode (int): Currently active weapon mode
        current_weapon_strategy (BaseWeaponStrategy): Active weapon implementation
        powerup_manager (PowerUpManager): Manages temporary power-up effects
        active_abilities (dict): Currently available active abilities with cooldowns
        bullets_group (pygame.sprite.Group): Player's bullet projectiles
        missiles_group (pygame.sprite.Group): Player's missile projectiles
    """
    def __init__(self, x, y, drone_id, drone_stats, asset_manager, sprite_asset_key, crash_sound_key, drone_system):
        base_speed_from_stats = drone_stats.get("speed", get_setting("gameplay", "PLAYER_SPEED", 3))
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.drone_visual_size = (int(tile_size * 0.7), int(tile_size * 0.7))
        super().__init__(x, y, size=self.drone_visual_size[0], speed=base_speed_from_stats)
        
        self.drone_id = drone_id
        self.drone_system = drone_system  
        self.asset_manager = asset_manager
        self.sprite_asset_key = sprite_asset_key
        self.crash_sound_key = crash_sound_key
        
        # Initialize last_shot_time and current_shoot_cooldown for UI
        self.last_shot_time = get_ticks()
        self.current_shoot_cooldown = 0
        
        self.base_hp = drone_stats.get("hp", get_setting("gameplay", "PLAYER_MAX_HEALTH", 100))
        self.base_turn_speed = drone_stats.get("turn_speed", get_setting("gameplay", "ROTATION_SPEED", 5))
        self.rotation_speed = self.base_turn_speed
        self.base_speed = base_speed_from_stats  # Store base speed for powerups
        
        self.is_cruising = False 
        self.max_health = self.base_hp
        self.health = self.max_health
        
        # Initialize PowerUpManager
        self.powerup_manager = PowerUpManager(self)
        
        self.original_image = None
        self.image = None
        
        initial_weapon_mode = get_setting("gameplay", "INITIAL_WEAPON_MODE", 0)
        weapon_modes_sequence = get_setting("weapon_modes", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        try:
            self.weapon_mode_index = weapon_modes_sequence.index(initial_weapon_mode)
        except ValueError:
            self.weapon_mode_index = 0 
        self.current_weapon_mode = weapon_modes_sequence[self.weapon_mode_index]
        
        self.bullets_group = Group()
        self.missiles_group = Group()
        self.lightning_zaps_group = Group()
        self.enemies_group = Group()  # Initialize enemies_group
        
        # Current weapon strategy will be set by set_weapon_mode
        
        # Set initial weapon strategy
        from .weapon_strategies import create_weapon_strategy
        self.current_weapon_strategy = create_weapon_strategy(self.current_weapon_mode, self)
        self.current_shoot_cooldown = self.current_weapon_strategy.get_cooldown()
        self._load_sprite()

        # NEW: Active Abilities System
        self.active_abilities = {} # {ability_id: {'cooldown_end_time': int, 'is_active': bool}}
        self.ability_cooldowns = {
            "temporary_barricade": get_setting("abilities", "TEMPORARY_BARRICADE_COOLDOWN_MS", 10000)
        }
        self.ability_durations = {
            "temporary_barricade": get_setting("abilities", "TEMPORARY_BARRICADE_DURATION_MS", 3000)
        }
        self.spawned_barricades_group = Group() # NEW: Group for spawned barricades

    def _load_sprite(self):
        # Always use the base drone sprite first
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)
        
        # If we have a valid image, use it
        if loaded_image:
            # We now assume the source image faces RIGHT and do not apply any correction here.
            self.original_image = smoothscale(loaded_image, self.drone_visual_size)
        else:
            self.original_image = self.asset_manager._create_fallback_surface(size=self.drone_visual_size, text=self.drone_id[:1], color=(0,200,0,150))
        
        self.image = self.original_image.copy()
        current_center = self.rect.center if hasattr(self, 'rect') and self.rect else (int(self.x), int(self.y))
        self.rect = self.image.get_rect(center=current_center)
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.3, -self.rect.height * 0.3)
                
    def _update_drone_sprite(self):
        """Update the drone sprite based on the current weapon mode"""
        # Cache weapon sprite mappings as class attribute
        if not hasattr(self.__class__, '_weapon_sprite_names'):
            self.__class__._weapon_sprite_names = {
                WEAPON_MODE_DEFAULT: "default",
                WEAPON_MODE_TRI_SHOT: "tri_shot",
                WEAPON_MODE_RAPID_SINGLE: "rapid_single",
                WEAPON_MODE_RAPID_TRI: "rapid_tri_shot",
                WEAPON_MODE_BIG_SHOT: "big_shot",
                WEAPON_MODE_BOUNCE: "bounce",
                WEAPON_MODE_PIERCE: "pierce",
                WEAPON_MODE_HEATSEEKER: "heatseeker",
                WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "heatseeker_plus_bullets",
                WEAPON_MODE_LIGHTNING: "lightning"
            }
        
        weapon_sprite_name = self._weapon_sprite_names.get(self.current_weapon_mode, "default")
        weapon_sprite_key = f"drone_{weapon_sprite_name}"
        
        # Try weapon-specific sprite first, then fallback
        loaded_image = (self.asset_manager.get_image(weapon_sprite_key) or 
                       self.asset_manager.get_image(self.sprite_asset_key))
        
        if loaded_image:
            self.original_image = smoothscale(loaded_image, self.drone_visual_size)
            current_center = self.rect.center if hasattr(self, 'rect') and self.rect else (int(self.x), int(self.y))
            self.image = self.original_image.copy()
            self.rect = self.image.get_rect(center=current_center)
            self.collision_rect = self.rect.inflate(-self.rect.width * 0.3, -self.rect.height * 0.3)

    def update(self, current_time_ms, maze, enemies_group, player_actions, game_area_x_offset=0):
        if not self.alive: return
        
        # Store enemies_group for weapon strategies that need it
        self.enemies_group = enemies_group
        
        # Update power-up states
        self.powerup_manager.update(current_time_ms)
        
        # Update weapon strategy with current maze and enemies
        if self.current_weapon_strategy:
            self.current_weapon_strategy.update_maze(maze)
            self.current_weapon_strategy.update_enemies_group(enemies_group)
        
        self.moving_forward = self.is_cruising
        
        super().update(maze, game_area_x_offset)
        
        shmup_mode = getattr(self, 'shmup_mode', False)
        self.bullets_group.update(maze, game_area_x_offset, shmup_mode)
        self.missiles_group.update(enemies_group, maze, game_area_x_offset, shmup_mode)
        if hasattr(self, 'lightning_zaps_group'):
            self.lightning_zaps_group.update(current_time_ms)
        
        # NEW: Update active abilities
        self.update_active_abilities(current_time_ms)
        self.spawned_barricades_group.update()

    def update_active_abilities(self, current_time_ms):
        """Updates the state and cooldowns of active abilities."""
        for ability_id, status in list(self.active_abilities.items()):
            if status.get('is_active') and 'active_end_time' in status and current_time_ms > status['active_end_time']:
                status['is_active'] = False
                logger.info(f"Ability '{ability_id}' deactivated.")
            if 'cooldown_end_time' in status and current_time_ms > status['cooldown_end_time']:
                # Ability is off cooldown, remove 'cooldown_end_time' to indicate ready
                del status['cooldown_end_time']

    def unlock_ability(self, ability_id):
        """Unlocks an active ability for the player."""
        if ability_id not in self.active_abilities:
            self.active_abilities[ability_id] = {} # Initialize status
            logger.info(f"Player unlocked active ability: {ability_id}")

    def activate_ability(self, ability_id, game_controller_ref):
        """
        Activates an unlocked active ability if not on cooldown.
        
        Checks unlock status and cooldown before activation. Handles ability-specific
        logic and manages cooldown timers. Provides user feedback through messages.
        
        Args:
            ability_id (str): Identifier of the ability to activate
            game_controller_ref (GameController): Reference to main game controller
            
        Returns:
            bool: True if ability was successfully activated, False otherwise
        """
        if not self.drone_system.has_ability_unlocked(ability_id):
            game_controller_ref.set_story_message(f"Ability '{ability_id}' is not unlocked!", 2000)
            game_controller_ref.play_sound('ui_denied')
            return False

        current_time_ms = get_ticks()
        ability_status = self.active_abilities.get(ability_id, {})
        
        # Check if on cooldown
        if 'cooldown_end_time' in ability_status and current_time_ms < ability_status['cooldown_end_time']:
            remaining_cooldown = (ability_status['cooldown_end_time'] - current_time_ms) / 1000.0
            game_controller_ref.set_story_message(f"{ability_id.replace('_', ' ').title()} on cooldown: {remaining_cooldown:.1f}s", 2000)
            game_controller_ref.play_sound('ui_denied')
            return False

        # Activate the ability
        if ability_id == "temporary_barricade":
            self._activate_temporary_barricade(game_controller_ref)
        # Add more ability activations here
        
        ability_status['is_active'] = True
        ability_status['active_end_time'] = current_time_ms + self.ability_durations.get(ability_id, 0)
        ability_status['cooldown_end_time'] = current_time_ms + self.ability_cooldowns.get(ability_id, 0)
        self.active_abilities[ability_id] = ability_status # Update the dictionary
        
        game_controller_ref.set_story_message(f"{ability_id.replace('_', ' ').title()} Activated!", 2000)
        game_controller_ref.play_sound('ui_confirm') # Play a generic ability activation sound
        return True

    def _activate_temporary_barricade(self, game_controller_ref):
        """Logic for spawning temporary barricades."""
        from entities.temporary_barricade import TemporaryBarricade # NEW import
        
        barricade_count = get_setting("abilities", "TEMPORARY_BARRICADE_COUNT", 3)
        barricade_health = get_setting("abilities", "TEMPORARY_BARRICADE_HEALTH", 50)
        barricade_lifetime = get_setting("abilities", "TEMPORARY_BARRICADE_DURATION_MS", 3000)
        barricade_size = get_setting("abilities", "TEMPORARY_BARRICADE_SIZE", 40)

        # Calculate spawn points in an arc in front of the player
        player_angle_rad = radians(self.angle)
        spawn_distance = self.rect.width * 1.2 # Distance from player center
        
        # Clear existing player-spawned barricades to prevent clutter
        self.spawned_barricades_group.empty()

        for i in range(barricade_count):
            # Distribute barricades in a slight arc
            angle_offset = (i - (barricade_count - 1) / 2) * 20 # -20, 0, 20 for 3 barricades
            barricade_angle_rad = radians(self.angle + angle_offset)

            spawn_x = self.x + cos(barricade_angle_rad) * spawn_distance
            spawn_y = self.y + sin(barricade_angle_rad) * spawn_distance
            
            # Ensure barricade is not spawned inside a wall
            maze = game_controller_ref.maze # Access maze from game_controller
            if maze and maze.is_wall(spawn_x, spawn_y, barricade_size, barricade_size):
                # If intended spawn point is inside a wall, try to adjust slightly or skip
                logger.warning(f"Attempted to spawn barricade in wall at ({spawn_x:.1f}, {spawn_y:.1f})")
                continue 

            new_barricade = TemporaryBarricade(
                spawn_x, spawn_y,
                size=barricade_size,
                health=barricade_health,
                lifetime_ms=barricade_lifetime,
                asset_manager=self.asset_manager # Pass asset_manager
            )
            self.spawned_barricades_group.add(new_barricade)
            game_controller_ref.combat_controller.spawned_barricades_group.add(new_barricade) # Add to combat controller's group as well
                
    def rotate(self, direction):
        super().rotate(direction, self.rotation_speed)
            
    def shoot(self, sound_asset_key=None, missile_sound_asset_key=None, maze=None, enemies_group=None):
        """Fires the current weapon using the active weapon strategy."""
        if not self.current_weapon_strategy:
            return
            
        # Update references if provided
        if enemies_group is not None:
            self.enemies_group = enemies_group
            self.current_weapon_strategy.update_enemies_group(enemies_group)
        
        if maze is not None:
            self.current_weapon_strategy.update_maze(maze)
        
        # Fire weapon
        if self.current_weapon_strategy.fire(sound_asset_key, missile_sound_asset_key):
            self.last_shot_time = get_ticks()

    def cycle_weapon_state(self):
        # Get owned weapons from drone system
        if hasattr(self, 'drone_system') and self.drone_system:
            owned_weapons = self.drone_system.get_owned_weapons()
            if owned_weapons:
                # Find current weapon index in owned weapons
                try:
                    current_index = owned_weapons.index(self.current_weapon_mode)
                    next_index = (current_index + 1) % len(owned_weapons)
                    self.current_weapon_mode = owned_weapons[next_index]
                except ValueError:
                    # Current weapon not in owned list, use first owned weapon
                    self.current_weapon_mode = owned_weapons[0]
                self.set_weapon_mode(self.current_weapon_mode)
                self._update_drone_sprite()
                return
        
        # Fallback to original behavior
        weapon_modes_sequence = get_setting("weapon_modes", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(weapon_modes_sequence)
        self.current_weapon_mode = weapon_modes_sequence[self.weapon_mode_index]
        self.set_weapon_mode(self.current_weapon_mode)
        self._update_drone_sprite()

    def set_weapon_mode(self, mode):
        """Set the current weapon strategy based on the weapon mode"""
        # Always update weapon strategy
            
        from .weapon_strategies import create_weapon_strategy
        
        self.current_weapon_mode = mode
        self.current_weapon_strategy = create_weapon_strategy(mode, self)
        self.current_shoot_cooldown = self.current_weapon_strategy.get_cooldown()
        self._update_drone_sprite()
        self.last_shot_time = get_ticks()

    def take_damage(self, amount, sound_key_on_hit=None):
        if not self.alive: return
        
        # Check if invincibility is enabled in settings
        if get_setting("gameplay", "PLAYER_INVINCIBILITY", False):
            # Play sound but don't reduce health
            if sound_key_on_hit and self.asset_manager:
                sound = self.asset_manager.get_sound(sound_key_on_hit)
                if sound: sound.play()
            return
        
        # Check if shield is active
        if self.powerup_manager.handle_damage(amount):
            # Shield absorbs all damage
            if sound_key_on_hit and self.asset_manager:
                sound = self.asset_manager.get_sound(sound_key_on_hit)
                if sound: sound.play()
            return
            
        self.health -= amount
        if sound_key_on_hit and self.asset_manager:
            sound = self.asset_manager.get_sound(sound_key_on_hit)
            if sound: sound.play()
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def draw(self, surface, camera=None):
        if not self.alive:
            return
            
        # Draw power-up effects first (behind the drone)
        self.powerup_manager.draw(surface, camera)
        
        # Draw spawned barricades
        self.spawned_barricades_group.draw(surface, camera)

        # Draw charging effect for lightning weapon
        if hasattr(self.current_weapon_strategy, 'draw_charging_effect'):
            self.current_weapon_strategy.draw_charging_effect(surface, camera)

        if self.original_image:
            rotated_image = rotate(self.original_image, -self.angle)
            surface.blit(rotated_image, rotated_image.get_rect(center=self.rect.center))
            self.draw_health_bar(surface, camera)
            
        self.bullets_group.draw(surface)
        self.missiles_group.draw(surface)
        
        # Draw lightning zaps
        for zap in self.lightning_zaps_group:
            if hasattr(zap, 'draw'):
                zap.draw(surface, camera)

    def draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect: return
        bar_width = self.rect.width * 0.8
        bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 3
        health_percentage = self.health / self.max_health if self.max_health > 0 else 0
        filled_width = int(bar_width * health_percentage)
        fill_color = GREEN if health_percentage > 0.6 else YELLOW if health_percentage > 0.3 else RED
        draw_rect(surface, (50,50,50), (bar_x, bar_y, bar_width, bar_height))
        if filled_width > 0: draw_rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
        draw_rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)
        
    def activate_shield(self, duration_ms):
        """Activate shield effect for the specified duration"""
        self.powerup_manager.activate_shield(duration_ms)
        
    def arm_speed_boost(self, duration_ms, multiplier=1.5):
        """Store speed boost for later activation with UP key"""
        self.powerup_manager.arm_speed_boost(duration_ms, multiplier)
        
    def activate_speed_boost(self):
        """Activate armed speed boost when UP key is pressed"""
        self.powerup_manager.activate_speed_boost()
        
    def unlock_weapon_mode(self, weapon_mode):
        """Unlock a specific weapon mode for the player"""
        weapon_modes_sequence = get_setting("weapon_modes", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        
        # Add the weapon mode to the sequence if not already present
        if weapon_mode not in weapon_modes_sequence:
            weapon_modes_sequence.append(weapon_mode)
            # Update the setting
            from settings_manager import set_setting
            set_setting("gameplay", "WEAPON_MODES_SEQUENCE", weapon_modes_sequence)
            
        logger.info(f"Player unlocked weapon mode: {weapon_mode}")
        return True