# hyperdrone_core/harvest_chamber_state.py
from pygame import Surface, Rect
from pygame.sprite import Group, spritecollide
from pygame.draw import circle
from pygame.key import get_pressed
from pygame.time import get_ticks
from pygame.transform import rotate, scale
from pygame import KEYDOWN, K_LEFT, K_RIGHT, K_UP, K_DOWN, K_a, K_d, K_w, K_s, K_SPACE, K_p
from random import randint, choice, random
from logging import getLogger
from math import sin, cos, atan2, pi, hypot
from .state import State
from settings_manager import get_setting
from entities import Enemy 

logger = getLogger(__name__)

class ScrollingBackground:
    def __init__(self, screen_height, image):
        self.image = image or self._create_default_background(screen_height)
        self.rect = self.image.get_rect()
        self.y1 = 0
        self.y2 = -self.rect.height
        self.scroll_speed = 4

    def _create_default_background(self, height):
        width = get_setting("display", "WIDTH", 1920)
        bg = Surface((width, height)).convert()
        bg.fill((10, 0, 20))
        
        # Add stars
        for _ in range(100):
            x, y = randint(0, width), randint(0, height)
            size = randint(1, 3)
            color = (randint(50, 100), 0, randint(100, 150))
            circle(bg, color, (x, y), size)
        
        return bg

    def update(self, delta_time):
        self.y1 += self.scroll_speed
        self.y2 += self.scroll_speed
        
        if self.y1 >= self.rect.height:
            self.y1 = -self.rect.height + (self.y1 - self.rect.height)
        if self.y2 >= self.rect.height:
            self.y2 = -self.rect.height + (self.y2 - self.rect.height)

    def draw(self, surface):
        surface.blit(self.image, (0, self.y1))
        surface.blit(self.image, (0, self.y2))

class ShmupEnemyManager:
    def __init__(self, game_controller):
        self.game_controller = game_controller
        self.enemies = Group()
        self.enemy_teams = []
        self.current_wave = 0
        self.wave_spawn_timer = 0
        self.wave_delay = 3000
        self.wave_complete = True

        # Formation movement
        self.formation_direction = 1
        self.formation_speed_x = 10
        self.formation_step_y = 20
        self.last_move_time = 0
        self.move_interval = 800

        # Combat
        self.last_shot_time = 0
        self.shoot_interval = 2000
        self.return_distance = 300
        self.return_threshold = 100
        self.reengage_cooldown = 3000

    def update(self, current_time, delta_time):
        # Check wave completion
        if len(self.enemies) == 0 and not self.wave_complete:
            self.wave_complete = True
            self.wave_spawn_timer = current_time

        # Spawn new wave
        if self.wave_complete and current_time - self.wave_spawn_timer > self.wave_delay:
            self.spawn_wave()

        # Update formations
        if current_time - self.last_move_time > self.move_interval:
            self._update_formations()
            self.last_move_time = current_time

        # Update individual behaviors
        self._update_fly_down_behavior(current_time)

        # Random shooting
        if current_time - self.last_shot_time > self.shoot_interval:
            self._random_enemy_shoot()
            self.last_shot_time = current_time

    def spawn_wave(self):
        self.current_wave += 1
        self.wave_complete = False
        self.enemy_teams.clear()

        # Wave parameters
        rows = min(2 + (self.current_wave - 1) // 3, 5)
        cols = min(5 + (self.current_wave - 1) // 2, 10)
        width = get_setting("display", "WIDTH", 1920)
        spacing_x, spacing_y = 80, 60
        start_x = (width - (cols - 1) * spacing_x) // 2

        # Enemy type based on wave
        if self.current_wave % 5 == 0:
            enemy_type = "elite"
        elif self.current_wave % 3 == 0:
            enemy_type = "sniper"
        else:
            enemy_type = "sentinel"

        # Get enemy config
        enemy_config = self.game_controller.combat_controller.enemy_manager.enemy_configs.get(enemy_type)
        if not enemy_config:
            return
            
        enemy_config = enemy_config.copy()
        enemy_config['health'] = 1 if enemy_type == "sentinel" else 2

        # Create teams
        team_size = 5
        num_teams = max(1, cols // team_size)

        for team_index in range(num_teams):
            team_members = []
            captain = None
            
            for row in range(rows):
                for col in range(team_size):
                    col_index = team_index * team_size + col
                    if col_index >= cols:
                        break
                        
                    x = start_x + col_index * spacing_x
                    y = 100 + row * spacing_y
                    
                    enemy = self._create_enemy(x, y, enemy_config, enemy_type)
                    
                    if captain is None:
                        enemy.is_captain = True
                        captain = enemy

                    self.enemies.add(enemy)
                    team_members.append(enemy)

            if team_members:
                self.enemy_teams.append({
                    "captain": captain, 
                    "members": team_members, 
                    "active_index": 1
                })

        # Increase difficulty
        self.formation_speed_x += 1
        self.move_interval = max(200, self.move_interval - 50)
        self.shoot_interval = max(800, self.shoot_interval - 100)

    def _create_enemy(self, x, y, config, enemy_type):
        enemy = Enemy(x, y, self.game_controller.asset_manager, config)
        enemy.speed = 0
        enemy.angle = 90
        enemy.enemy_type = enemy_type
        enemy.is_captain = False
        enemy.fly_down = False
        enemy.fly_curve_time = 0
        enemy.original_pos = (x, y)
        enemy.returning = False
        enemy.cooldown_until = 0

        # Scale enemy sprite
        if hasattr(enemy, 'image') and enemy.image:
            original_size = enemy.image.get_size()
            new_size = (int(original_size[0] * 1.25), int(original_size[1] * 1.25))
            enemy.image = scale(enemy.image, new_size)
            enemy.rect = enemy.image.get_rect(center=enemy.rect.center)
            
        return enemy

    def _update_formations(self):
        screen_width = get_setting("display", "WIDTH", 1920)
        
        for team in self.enemy_teams:
            members = [m for m in team["members"] if not getattr(m, "fly_down", False)]
            if not members:
                continue
                
            # Calculate team bounds
            team_bounds = members[0].rect.copy()
            for enemy in members[1:]:
                team_bounds.union_ip(enemy.rect)

            # Check if need to change direction
            move_sideways = True
            if ((self.formation_direction == 1 and team_bounds.right + self.formation_speed_x > screen_width) or 
                (self.formation_direction == -1 and team_bounds.left - self.formation_speed_x < 0)):
                self.formation_direction *= -1
                move_sideways = False

            # Move enemies
            for enemy in members:
                if move_sideways:
                    enemy.rect.x += self.formation_direction * self.formation_speed_x
                else:
                    enemy.rect.y += self.formation_step_y

    def _update_fly_down_behavior(self, current_time):
        for team in self.enemy_teams:
            members = team["members"]
            active_index = team["active_index"]
            
            if active_index >= len(members):
                continue
                
            target = members[active_index]
            if not target.alive:
                team["active_index"] += 1
                continue

            if current_time < getattr(target, "cooldown_until", 0):
                continue

            if not target.fly_down:
                target.fly_down = True
                target.fly_curve_time = 0
            elif not target.returning:
                # Fly down with curve
                target.fly_curve_time += 0.05
                x_offset = 50 * sin(target.fly_curve_time * 2.0)
                y_offset = 3 + 2 * cos(target.fly_curve_time)
                target.rect.x += int(x_offset)
                target.rect.y += int(y_offset)

                # Check if should return
                distance = target.rect.y - target.original_pos[1]
                if distance > self.return_distance:
                    target.returning = True
            else:
                # Return to formation
                ox, oy = target.original_pos
                dx = ox - target.rect.centerx
                dy = oy - target.rect.centery
                dist = hypot(dx, dy)
                
                if dist < self.return_threshold:
                    target.fly_down = False
                    target.returning = False
                    target.cooldown_until = current_time + self.reengage_cooldown
                    target.rect.center = target.original_pos
                else:
                    target.rect.x += int(dx * 0.1)
                    target.rect.y += int(dy * 0.1)

            # Random shooting while flying
            if hasattr(target, "shoot") and random() < 0.01:
                self._shoot_at_player(target)

    def _random_enemy_shoot(self):
        available = [e for e in self.enemies if not getattr(e, "fly_down", False)]
        if available:
            shooter = choice(available)
            if hasattr(shooter, "shoot"):
                self._shoot_at_player(shooter)

    def _shoot_at_player(self, enemy):
        player = self.game_controller.player
        if player:
            dx = player.x - enemy.x
            dy = player.y - enemy.y
            angle = atan2(dy, dx) * 180 / pi
            enemy.shoot(angle, None)

    def draw(self, surface):
        self.enemies.draw(surface)

class ShmupPlayerController:
    def __init__(self, player):
        self.player = player
        self.speed = get_setting("gameplay", "PLAYER_SPEED", 3) * 1.5

    def handle_input(self):
        if not self.player:
            return

        keys = get_pressed()
        dx = dy = 0

        # Movement
        if keys[K_LEFT] or keys[K_a]:
            dx = -1
        if keys[K_RIGHT] or keys[K_d]:
            dx = 1
        if keys[K_UP] or keys[K_w]:
            dy = -1
        if keys[K_DOWN] or keys[K_s]:
            dy = 1

        # Update position
        self.player.x += dx * self.speed
        self.player.y += dy * self.speed

        # Clamp to screen
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        hw, hh = self.player.rect.width / 2, self.player.rect.height / 2
        
        self.player.x = max(hw, min(self.player.x, width - hw))
        self.player.y = max(hh, min(self.player.y, height - hh))
        self.player.rect.center = (self.player.x, self.player.y)

        # Shooting
        if keys[K_SPACE]:
            self.player.shoot()

class HarvestChamberState(State):
    def enter(self, previous_state=None, **kwargs):
        logger.info("Entering HarvestChamberState...")
        
        # Setup player
        if not self.game.player:
            self._create_player()
        
        self._setup_player_for_shmup()
        
        # Initialize systems
        self.player_controller = ShmupPlayerController(self.game.player)
        self.background = ScrollingBackground(get_setting("display", "HEIGHT", 1080), None)
        self.shmup_enemy_manager = ShmupEnemyManager(self.game)

        # Check story state
        current_chapter = self.game.story_manager.get_current_chapter()
        if not (current_chapter and current_chapter.chapter_id == "chapter_4"):
             logger.warning("Not on Chapter 4 in story")
        
        # Spawn quantum circuitry
        width = get_setting("display", "WIDTH", 1920)
        self.game.item_manager.spawn_quantum_circuitry(width/2, 200)

    def _create_player(self):
        from entities import PlayerDrone
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        self.game.player = PlayerDrone(
            width / 2, height - 100, drone_id, drone_stats, 
            self.game.asset_manager, sprite_key, 'crash', self.game.drone_system
        )
        self.game.lives = get_setting("gameplay", "PLAYER_LIVES", 3)

    def _setup_player_for_shmup(self):
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        
        self.game.player.x = width / 2
        self.game.player.y = height - 100
        self.game.player.is_cruising = False 
        self.game.player.angle = -90
        self.game.player.shmup_mode = True

    def update(self, delta_time):
        current_time = get_ticks()

        if not self.game.player:
            self.game.state_manager.set_state("MainMenuState")
            return
        
        # Update systems
        if self.player_controller:
            self.player_controller.handle_input()

        self.game.player.update(current_time, None, self.shmup_enemy_manager.enemies, None, 0)
        self.shmup_enemy_manager.update(current_time, delta_time)
        self.background.update(delta_time)
        self._handle_collisions()
        
        # Check game over
        if not self.game.player.alive:
            self.game.state_manager.set_state("GameOverState")

    def _handle_collisions(self):
        if not self.game.player:
            return

        # Get all projectiles
        projectiles = (list(self.game.player.bullets_group) + 
                      list(self.game.player.missiles_group) + 
                      list(self.game.player.lightning_zaps_group))

        # Projectile-enemy collisions (instant kill)
        for projectile in projectiles:
            if not projectile.alive:
                continue
                
            for enemy in list(self.shmup_enemy_manager.enemies):
                if not enemy.alive:
                    continue
                    
                if projectile.rect.colliderect(enemy.rect):
                    enemy.health = 0
                    enemy.alive = False
                    self.game._create_explosion(enemy.rect.centerx, enemy.rect.centery, 15, None, True)
                    enemy.kill()
                    projectile.alive = False
                    projectile.kill()
                    break

        # Player-enemy collisions
        for enemy in spritecollide(self.game.player, self.shmup_enemy_manager.enemies, True):
            self.game.player.take_damage(50)

    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN and event.key == K_p:
                self.game.toggle_pause()

    def draw(self, surface):
        surface.fill((10, 0, 20)) 
        self.background.draw(surface)
        
        self.game.quantum_circuitry_group.draw(surface)
        self.shmup_enemy_manager.draw(surface)
        
        self.game.explosion_particles_group.update()
        self.game.explosion_particles_group.draw(surface)
        
        if self.game.player:
            # Draw projectiles
            self.game.player.bullets_group.draw(surface)
            self.game.player.missiles_group.draw(surface)
            
            for zap in self.game.player.lightning_zaps_group:
                if hasattr(zap, 'draw'):
                    zap.draw(surface)
            
            # Draw player (scaled and rotated)
            if hasattr(self.game.player, 'image') and self.game.player.image:
                rotated = rotate(self.game.player.image, 90)
                scaled = scale(rotated, (int(rotated.get_width() * 1.5), int(rotated.get_height() * 1.5)))
                pos = (self.game.player.rect.centerx - scaled.get_width()//2, 
                       self.game.player.rect.centery - scaled.get_height()//2)
                surface.blit(scaled, pos)
            else:
                self.game.player.draw(surface)

        self.game.ui_manager.draw_current_scene_ui()