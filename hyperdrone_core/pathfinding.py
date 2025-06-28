# hyperdrone_core/pathfinding.py
from heapq import heappush, heappop
from math import sqrt, cos, sin, radians
from random import randint
from logging import getLogger

logger = getLogger(__name__)

class AStarNode:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g_cost = 0
        self.h_cost = 0
        self.f_cost = 0
    
    def __eq__(self, other):
        return self.position == other.position
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __hash__(self):
        return hash(self.position)

def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    # Validate input
    if (not maze_grid or 
        not (0 <= start_pos_grid[0] < maze_rows and 0 <= start_pos_grid[1] < maze_cols) or
        not (0 <= end_pos_grid[0] < maze_rows and 0 <= end_pos_grid[1] < maze_cols)):
        return None
    
    # Initialize
    start_node = AStarNode(start_pos_grid)
    end_node = AStarNode(end_pos_grid)
    
    open_list = []
    closed_set = set()
    heappush(open_list, (0, start_node))
    open_set_hash = {start_pos_grid}
    
    # Main loop
    while open_list:
        _, current_node = heappop(open_list)
        
        if current_node.position not in open_set_hash:
            continue
        
        open_set_hash.remove(current_node.position)
        
        # Goal check
        if current_node.position == end_node.position:
            path = []
            temp = current_node
            while temp:
                path.append(temp.position)
                temp = temp.parent
            return path[::-1]
        
        closed_set.add(current_node.position)
        
        # Check neighbors
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            node_pos = (current_node.position[0] + dx, current_node.position[1] + dy)
            
            # Skip invalid positions
            if (not (0 <= node_pos[0] < maze_rows and 0 <= node_pos[1] < maze_cols) or
                maze_grid[node_pos[0]][node_pos[1]] == 1 or
                node_pos in closed_set):
                continue
            
            # Create neighbor
            neighbor = AStarNode(node_pos, current_node)
            neighbor.g_cost = current_node.g_cost + 1
            neighbor.h_cost = abs(neighbor.position[0] - end_node.position[0]) + abs(neighbor.position[1] - end_node.position[1])
            neighbor.f_cost = neighbor.g_cost + neighbor.h_cost
            
            # Add to open list if not already there with better cost
            if not any(n[1] == neighbor and neighbor.g_cost >= n[1].g_cost for n in open_list):
                heappush(open_list, (neighbor.f_cost, neighbor))
                open_set_hash.add(neighbor.position)
    
    return None

def find_wall_follow_target(maze, current_grid_pos, maze_rows, maze_cols):
    if not maze or not hasattr(maze, 'grid') or not current_grid_pos:
        return None
        
    # Find nearby walls
    directions = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
    wall_directions = []
    
    for dx, dy in directions:
        check_pos = (current_grid_pos[0] + dx, current_grid_pos[1] + dy)
        if (0 <= check_pos[0] < maze_rows and 0 <= check_pos[1] < maze_cols and
            maze.grid[check_pos[0]][check_pos[1]] == 1):
            wall_directions.append((dx, dy))
    
    if not wall_directions:
        return None
        
    # Find wall-following path
    for wall_dir in wall_directions:
        # Get perpendicular directions
        if wall_dir[0] == 0:  # Vertical wall
            perp_dirs = [(1, 0), (-1, 0)]
        elif wall_dir[1] == 0:  # Horizontal wall
            perp_dirs = [(0, 1), (0, -1)]
        else:  # Diagonal wall
            perp_dirs = [(wall_dir[1], -wall_dir[0]), (-wall_dir[1], wall_dir[0])]
            
        # Try perpendicular directions
        for perp_dir in perp_dirs:
            for dist in range(3, 8):
                target_pos = (
                    current_grid_pos[0] + perp_dir[0] * dist,
                    current_grid_pos[1] + perp_dir[1] * dist
                )
                
                # Check validity
                if (0 <= target_pos[0] < maze_rows and 0 <= target_pos[1] < maze_cols and
                    maze.grid[target_pos[0]][target_pos[1]] == 0):
                    
                    path = a_star_search(maze.grid, current_grid_pos, target_pos, maze_rows, maze_cols)
                    if path and len(path) > 1:
                        return target_pos
    
    # Fallback to random nearby position
    for _ in range(10):
        rand_row = randint(max(0, current_grid_pos[0] - 5), min(maze_rows - 1, current_grid_pos[0] + 5))
        rand_col = randint(max(0, current_grid_pos[1] - 5), min(maze_cols - 1, current_grid_pos[1] + 5))
        
        if maze.grid[rand_row][rand_col] == 0:
            return (rand_row, rand_col)
            
    return None

def find_alternative_target(maze, current_grid_pos, primary_target_grid, maze_rows, maze_cols, max_distance=10):
    if not maze or not hasattr(maze, 'grid'):
        return None
    
    best_distance = float('inf')
    best_target = None
    
    # Calculate direction to primary target
    dir_row = primary_target_grid[0] - current_grid_pos[0]
    dir_col = primary_target_grid[1] - current_grid_pos[1]
    
    # Normalize direction
    magnitude = sqrt(dir_row**2 + dir_col**2)
    if magnitude > 0:
        dir_row /= magnitude
        dir_col /= magnitude
    
    # Search for alternative targets
    for distance in range(3, max_distance + 1):
        for angle_offset in [0, 15, -15, 30, -30, 45, -45]:
            # Calculate rotated direction
            angle_rad = radians(angle_offset)
            rotated_row = dir_row * cos(angle_rad) - dir_col * sin(angle_rad)
            rotated_col = dir_row * sin(angle_rad) + dir_col * cos(angle_rad)
            
            # Calculate target position
            target_row = int(current_grid_pos[0] + rotated_row * distance)
            target_col = int(current_grid_pos[1] + rotated_col * distance)
            
            # Check validity
            if (0 <= target_row < maze_rows and 0 <= target_col < maze_cols and
                maze.grid[target_row][target_col] == 0):
                
                path = a_star_search(maze.grid, current_grid_pos, (target_row, target_col), maze_rows, maze_cols)
                
                if path and len(path) > 1:
                    # Calculate distance to primary target
                    dist_to_primary = sqrt(
                        (target_row - primary_target_grid[0])**2 + 
                        (target_col - primary_target_grid[1])**2
                    )
                    
                    # Update best target
                    if dist_to_primary < best_distance:
                        best_distance = dist_to_primary
                        best_target = (target_row, target_col)
    
    return best_target