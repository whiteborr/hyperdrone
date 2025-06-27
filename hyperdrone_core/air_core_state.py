# hyperdrone_core/air_core_state.py
from pygame import KEYDOWN, KEYUP, K_p, K_ESCAPE, USEREVENT
from pygame.sprite import Group
from pygame.time import get_ticks, set_timer
from pygame import Surface
from .state import State
from entities import PlayerDrone, Enemy, ParticleSystem, Maze
from entities.elemental_core import ElementalCore
from constants import GAME_STATE_STORY_MAP

class AirCoreState(State):
    def __init__(self, game):
        super().__init__(game)
        self.player = None
        self.maze = None
        self.air_core = None
        self.enemies = Group()
        self.particles = ParticleSystem()
        self.core_collected = False
        self.shifting_walls = []
        self.shift_timer = 0
        
    def enter(self, previous_state=None, **kwargs):
        # Initialize corrupted maze
        self.maze = Maze(maze_type="corrupted")
        
        # Initialize player
        start_pos = (100, 100)
        drone_id = self.game.drone_system.get_selected_drone_id()
        drone_stats = self.game.drone_system.get_drone_stats(drone_id)
        self.player = PlayerDrone(
            start_pos[0], start_pos[1], drone_id, drone_stats,
            self.game.asset_manager, "drone_default", "crash", self.game.drone_system
        )
        
        # Create air core in center
        center_x = self.maze.available_width // 2
        center_y = self.maze.available_height // 2
        self.air_core = ElementalCore(center_x, center_y, "air", self.game.asset_manager)
        
        # Spawn corrupted enemies
        self._spawn_corrupted_enemies()
        
    def _spawn_corrupted_enemies(self):
        walkable_tiles = self.maze.get_walkable_tiles_abs()
        for i in range(8):
            if i < len(walkable_tiles):
                x, y = walkable_tiles[i * len(walkable_tiles) // 8]
                enemy_config = {"health": 15, "speed": 1.5, "damage": 8}
                enemy = Enemy(x, y, self.game.asset_manager, enemy_config)
                self.enemies.add(enemy)
        
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_p:
                    self.game.paused = not self.game.paused
                elif event.key == K_ESCAPE:
                    self.game.state_manager.set_state(GAME_STATE_STORY_MAP)
                else:
                    if hasattr(self.game, 'player_actions'):
                        self.game.player_actions.handle_key_down(event)
            elif event.type == KEYUP:
                if hasattr(self.game, 'player_actions'):
                    self.game.player_actions.handle_key_up(event)
    
    def update(self, delta_time):
        if self.game.paused:
            return
            
        current_time = get_ticks()
        
        # Update shifting walls
        self.shift_timer += delta_time
        if self.shift_timer > 3000:  # Shift every 3 seconds
            self._shift_maze_walls()
            self.shift_timer = 0
        
        # Update player
        if hasattr(self.player, 'update'):
            self.player.update(current_time, self.maze, self.enemies, self.game.player_actions, 0)
        
        # Update player actions
        if hasattr(self.game, 'player_actions'):
            self.game.player_actions.update_player_movement_and_actions(current_time)
        
        # Update enemies
        for enemy in self.enemies:
            if hasattr(enemy, 'update'):
                enemy.update(self.maze, current_time, delta_time, 0)
        
        # Update air core
        self.air_core.update(delta_time)
        
        # Check for core collection
        if hasattr(self.player, 'rect') and hasattr(self.air_core, 'rect'):
            if self.player.rect.colliderect(self.air_core.rect):
                self._collect_air_core()
        
        # Update particles
        self.particles.update(delta_time)
        
        # Handle combat
        self._handle_combat()
    
    def _shift_maze_walls(self):
        # Randomly modify some maze walls to create shifting effect
        for row in range(min(5, self.maze.actual_maze_rows)):
            for col in range(min(5, self.maze.actual_maze_cols)):
                if row > 0 and col > 0:  # Don't modify edges
                    if get_ticks() % 2 == 0:  # Random chance
                        self.maze.grid[row][col] = 1 - self.maze.grid[row][col]
        
        # Recreate wall lines
        self.maze.walls = self.maze._create_wall_lines()
    
    def _handle_combat(self):
        # Player bullets vs enemies
        if hasattr(self.player, 'bullets_group'):
            for bullet in self.player.bullets_group:
                for enemy in self.enemies:
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.health -= bullet.damage
                        bullet.kill()
                        self.particles.create_explosion(
                            bullet.rect.centerx, bullet.rect.centery,
                            (0, 255, 255), 8
                        )
                        if enemy.health <= 0:
                            enemy.kill()
        
        # Enemy bullets vs player
        for enemy in self.enemies:
            if hasattr(enemy, 'bullets_group'):
                for bullet in enemy.bullets_group:
                    if bullet.rect.colliderect(self.player.rect):
                        self.player.take_damage(bullet.damage)
                        bullet.kill()
    
    def _collect_air_core(self):
        if not self.core_collected:
            self.core_collected = True
            self.game.drone_system.collect_core_fragment("air")
            self.game.set_story_message("Air Core collected! Your mind expands with new possibilities.", 3000)
            
            # Return to story map
            set_timer(USEREVENT + 2, 2000)
    
    def draw(self, surface):
        surface.fill((40, 20, 60))  # Purple corrupted background
        
        # Draw maze
        self.maze.draw(surface)
        
        # Draw player
        self.player.draw(surface)
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(surface)
        
        # Draw air core
        self.air_core.draw(surface, (0, 0))
        
        # Draw particles
        self.particles.draw(surface, (0, 0))
        
        # Draw corruption effect overlay
        corruption_surface = Surface((surface.get_width(), surface.get_height()))
        corruption_surface.set_alpha(30)
        corruption_surface.fill((100, 0, 100))
        surface.blit(corruption_surface, (0, 0))
    
    def exit(self, next_state=None):
        pass