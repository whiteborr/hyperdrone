# entities/path_manager.py
from heapq import heappush, heappop
from logging import getLogger, error, warning

logger = getLogger(__name__)

class PathManager:
    def __init__(self, grid_width, grid_height, tile_size):
        self.width = grid_width
        self.height = grid_height
        self.tile_size = tile_size
        self.grid = [[0] * grid_width for _ in range(grid_height)]
        self.spawns = []
        self.goal = None
        
    def set_grid(self, grid):
        if not grid or not grid[0]:
            error("Invalid grid provided")
            return
        self.height = len(grid)
        self.width = len(grid[0])
        self.grid = grid
        
    def set_spawn_points(self, points):
        self.spawns = points
        
    def set_goal_point(self, point):
        self.goal = point
        
    def is_valid(self, r, c):
        return 0 <= r < self.height and 0 <= c < self.width
        
    def is_walkable(self, r, c):
        return self.is_valid(r, c) and self.grid[r][c] not in [1, 'U']
        
    def get_neighbors(self, r, c):
        neighbors = []
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if self.is_walkable(nr, nc):
                neighbors.append((nr, nc))
        return neighbors
        
    def manhattan_distance(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
    def find_path(self, start, goal):
        if not self.is_walkable(*start) or not self.is_walkable(*goal):
            return []
            
        open_set = [(0, start)]
        open_hash = {start}
        came_from = {}
        g_score = {start: 0}
        
        while open_set:
            _, current = heappop(open_set)
            if current not in open_hash:
                continue
            open_hash.remove(current)
            
            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return path[::-1]
            
            for neighbor in self.get_neighbors(*current):
                tentative_g = g_score.get(current, float('inf')) + 1
                
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self.manhattan_distance(neighbor, goal)
                    
                    if neighbor not in open_hash:
                        heappush(open_set, (f_score, neighbor))
                        open_hash.add(neighbor)
                    
        return []
        
    def can_place_tower(self, r, c):
        if not self.is_valid(r, c):
            return False
            
        if self.grid[r][c] == 'T':
            return True
            
        if not self.is_walkable(r, c) or not self.goal or not self.spawns:
            return False
            
        # Test placement
        original = self.grid[r][c]
        self.grid[r][c] = 'U'
        
        # Check if any spawn can still reach goal
        can_place = any(self.find_path(spawn, self.goal) for spawn in self.spawns)
        
        self.grid[r][c] = original
        return can_place
        
    def grid_to_pixel(self, r, c):
        x = c * self.tile_size + self.tile_size // 2
        y = r * self.tile_size + self.tile_size // 2
        return (x, y)
        
    def pixel_to_grid(self, x, y):
        return (y // self.tile_size, x // self.tile_size)
