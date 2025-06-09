# hyperdrone_core/enemy_manager.py
import pygame
import random
from entities import Enemy, SentinelDrone
import game_settings as gs
from game_settings import TILE_SIZE 

class EnemyManager:
    def __init__(self, game_controller_ref, asset_manager):
        self.game_controller = game_controller_ref
        self.asset_manager = asset_manager
        self.enemies = pygame.sprite.Group()

        self.defense_enemy_configs = {
            "standard_drone": {
                "class": Enemy, "sprite_asset_key": "regular_enemy_sprite_key",
                "health": gs.get_game_setting("ENEMY_HEALTH", 100), "speed": gs.get_game_setting("ENEMY_SPEED", 1.5),
                "shoot_cooldown": gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500), "contact_damage": 25
            },
            "fast_drone": { 
                "class": Enemy, "sprite_asset_key": "regular_enemy_sprite_key",
                "health": int(gs.get_game_setting("ENEMY_HEALTH", 100) * 0.7), "speed": gs.get_game_setting("ENEMY_SPEED", 1.5) * 1.5,
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.8), "contact_damage": 20
            },
            "armored_drone": { 
                "class": Enemy, "sprite_asset_key": "regular_enemy_sprite_key",
                "health": int(gs.get_game_setting("ENEMY_HEALTH", 100) * 1.8), "speed": gs.get_game_setting("ENEMY_SPEED", 1.5) * 0.7,
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 1.2), "contact_damage": 35
            },
            "sentinel_drone": {
                "class": SentinelDrone, "sprite_asset_key": "sentinel_drone_sprite_key",
                "health": gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75), "speed": gs.get_game_setting("SENTINEL_DRONE_SPEED", 3.0),
                "shoot_cooldown": int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.7), "contact_damage": 30
            }
        }

    def spawn_enemies_for_level(self, level):
        self.enemies.empty()
        num_enemies = min(level + 1, 7) 
        enemy_shoot_sound_key = 'enemy_shoot'
        player_bullet_size_setting = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        
        # --- START OF FIX ---
        # Changed condition to spawn the more reliable SentinelDrones from level 4 onwards.
        if level >= 4:
        # --- END OF FIX ---
            sentinel_sprite_key = "sentinel_drone_sprite_key"
            for _ in range(num_enemies):
                if abs_x_y := self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.6, TILE_SIZE * 0.6):
                    self.enemies.add(SentinelDrone(x=abs_x_y[0], y=abs_x_y[1], player_bullet_size_base=player_bullet_size_setting, shoot_sound_key=enemy_shoot_sound_key, asset_manager=self.asset_manager, sprite_asset_key=sentinel_sprite_key, target_player_ref=self.game_controller.player))
        else: 
            regular_enemy_sprite_key = "regular_enemy_sprite_key"
            for _ in range(num_enemies):
                if abs_x_y := self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7):
                    self.enemies.add(Enemy(abs_x_y[0], abs_x_y[1], player_bullet_size_setting, shoot_sound_key=enemy_shoot_sound_key, asset_manager=self.asset_manager, sprite_asset_key=regular_enemy_sprite_key, target_player_ref=self.game_controller.player))

    def spawn_prototype_drones(self, count, far_from_player=False):
        if not self.game_controller.maze: return
        for _ in range(count):
            if abs_x_y := self.game_controller._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7):
                proto_drone = Enemy(abs_x_y[0], abs_x_y[1], gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE"), shoot_sound_key='enemy_shoot', asset_manager=self.asset_manager, sprite_asset_key="prototype_drone_sprite_key", target_player_ref=self.game_controller.player)
                proto_drone.health = gs.get_game_setting("PROTOTYPE_DRONE_HEALTH"); proto_drone.max_health = gs.get_game_setting("PROTOTYPE_DRONE_HEALTH"); proto_drone.speed = gs.get_game_setting("PROTOTYPE_DRONE_SPEED"); proto_drone.shoot_cooldown = gs.get_game_setting("PROTOTYPE_DRONE_SHOOT_COOLDOWN")
                self.enemies.add(proto_drone)
    
    def spawn_sentinel_drone_at_location(self, x, y):
        self.enemies.add(SentinelDrone(x=x, y=y, player_bullet_size_base=gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE"), shoot_sound_key='enemy_shoot', asset_manager=self.asset_manager, sprite_asset_key="sentinel_drone_sprite_key", target_player_ref=self.game_controller.player))

    def spawn_enemy_for_defense(self, enemy_type_key, spawn_position, reactor_target):
        config = self.defense_enemy_configs.get(enemy_type_key, self.defense_enemy_configs["standard_drone"])
        enemy = config["class"](x=spawn_position[0], y=spawn_position[1], player_bullet_size_base=gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE"), shoot_sound_key='enemy_shoot', asset_manager=self.asset_manager, sprite_asset_key=config["sprite_asset_key"], target_player_ref=self.game_controller.player)
        enemy.health = config.get("health", enemy.health); enemy.max_health = config.get("health", enemy.max_health); enemy.speed = config.get("speed", enemy.speed); enemy.shoot_cooldown = config.get("shoot_cooldown", enemy.shoot_cooldown)
        enemy.defense_target = reactor_target; enemy.is_in_defense_mode = True; enemy.contact_damage = config.get("contact_damage", 25)
        self.enemies.add(enemy)

    def update_enemies(self, primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset=0, is_defense_mode=False):
        for enemy_obj in list(self.enemies):
            if enemy_obj.alive:
                enemy_obj.update(primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset, is_defense_mode)
            elif not hasattr(enemy_obj, '_exploded'):
                self.game_controller._create_explosion(enemy_obj.rect.centerx, enemy_obj.rect.centery, specific_sound_key='prototype_drone_explode' if isinstance(enemy_obj, SentinelDrone) else 'enemy_shoot')
                enemy_obj._exploded = True; enemy_obj.kill()
            elif not enemy_obj.bullets and hasattr(enemy_obj, '_exploded'):
                 enemy_obj.kill()

    def draw_all(self, surface, camera=None):
        for enemy in self.enemies:
            enemy.draw(surface, camera)
            if enemy.alive and hasattr(enemy, '_draw_health_bar'):
                enemy._draw_health_bar(surface, camera)

    def reset_all(self):
        self.enemies.empty() 

    def get_sprites(self):
        return self.enemies

    def get_active_enemies_count(self):
        return sum(1 for e in self.enemies if e.alive)