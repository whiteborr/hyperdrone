# hyperdrone_core/pathfinding.py
import heapq
import math
import random
import logging

logger = logging.getLogger(__name__)

class AStarNode:
    """Node class for A* pathfinding algorithm"""
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g_cost = 0  # Cost from start to current node
        self.h_cost = 0  # Heuristic cost from current node to goal
        self.f_cost = 0  # Total cost (g_cost + h_cost)
    
    def __eq__(self, other):
        return self.position == other.position
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __hash__(self):
        return hash(self.position)


def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    """
    A* pathfinding algorithm to find the shortest path between two points.
    
    Args:
        maze_grid: 2D grid where 1 represents walls and 0 represents walkable areas
        start_pos_grid: Starting position as (row, col)
        end_pos_grid: Goal position as (row, col)
        maze_rows: Number of rows in the maze grid
        maze_cols: Number of columns in the maze grid
        
    Returns:
        List of positions forming the path from start to end, or None if no path exists
    """
    # Validate input
    if not maze_grid or not (0 <= start_pos_grid[0] < maze_rows and 0 <= start_pos_grid[1] < maze_cols) or not (0 <= end_pos_grid[0] < maze_rows and 0 <= end_pos_grid[1] < maze_cols):
        return None
    
    # Initialize start and end nodes
    start_node = AStarNode(start_pos_grid)
    end_node = AStarNode(end_pos_grid)
    
    # Initialize open and closed lists
    open_list = []
    closed_set = set()
    heapq.heappush(open_list, (0, start_node))
    
    # Initialize g_score map
    g_score = {(r, c): float('inf') for r in range(maze_rows) for c in range(maze_cols)}
    g_score[start_pos_grid] = 0
    
    # Keep track of nodes in open list for faster lookup
    open_set_hash = {start_pos_grid}
    
    # Main loop
    while open_list:
        # Get node with lowest f_cost
        _, current_node = heapq.heappop(open_list)
        
        # Skip if node was already processed
        if current_node.position not in open_set_hash:
            continue
        
        open_set_hash.remove(current_node.position)
        
        # Check if we reached the goal
        if current_node.position == end_node.position:
            # Reconstruct path
            path = []
            temp = current_node
            while temp:
                path.append(temp.position)
                temp = temp.parent
            return path[::-1]  # Return reversed path (start to end)
        
        # Add current node to closed set
        closed_set.add(current_node.position)
        
        # Check neighbors (4-directional movement)
        for new_pos_offset in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            node_pos = (current_node.position[0] + new_pos_offset[0], current_node.position[1] + new_pos_offset[1])
            
            # Skip if out of bounds, wall, or already processed
            if not (0 <= node_pos[0] < maze_rows and 0 <= node_pos[1] < maze_cols) or maze_grid[node_pos[0]][node_pos[1]] == 1 or node_pos in closed_set:
                continue
            
            # Create neighbor node
            neighbor = AStarNode(node_pos, current_node)
            
            # Calculate costs
            neighbor.g_cost = current_node.g_cost + 1
            neighbor.h_cost = abs(neighbor.position[0] - end_node.position[0]) + abs(neighbor.position[1] - end_node.position[1])
            neighbor.f_cost = neighbor.g_cost + neighbor.h_cost
            
            # Skip if we already found a better path to this neighbor
            if not any(n[1] == neighbor and neighbor.g_cost >= n[1].g_cost for n in open_list):
                heapq.heappush(open_list, (neighbor.f_cost, neighbor))
                open_set_hash.add(neighbor.position)
    
    # No path found
    return None


def find_wall_follow_target(maze, current_grid_pos, maze_rows, maze_cols):
    """
    Find a target position along a wall to follow using A*
    
    Args:
        maze: Maze object with a grid attribute
        current_grid_pos: Current position as (row, col)
        maze_rows: Number of rows in the maze grid
        maze_cols: Number of columns in the maze grid
        
    Returns:
        Target position as (row, col) or None if no suitable target found
    """
    if not maze or not hasattr(maze, 'grid') or not current_grid_pos:
        return None
        
    # Check if we're near a wall
    directions = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
    wall_directions = []
    
    for dx, dy in directions:
        check_pos = (current_grid_pos[0] + dx, current_grid_pos[1] + dy)
        if 0 <= check_pos[0] < maze_rows and 0 <= check_pos[1] < maze_cols:
            if maze.grid[check_pos[0]][check_pos[1]] == 1:  # Wall
                wall_directions.append((dx, dy))
    
    if not wall_directions:
        return None  # No walls nearby
        
    # Find a path that follows along the wall
    # Look for a walkable cell that's 2-3 cells away along the wall
    for wall_dir in wall_directions:
        # Get perpendicular directions to the wall
        if wall_dir[0] == 0:  # Vertical wall
            perp_dirs = [(1, 0), (-1, 0)]
        elif wall_dir[1] == 0:  # Horizontal wall
            perp_dirs = [(0, 1), (0, -1)]
        else:  # Diagonal wall
            perp_dirs = [(wall_dir[1], -wall_dir[0]), (-wall_dir[1], wall_dir[0])]
            
        # Try both perpendicular directions
        for perp_dir in perp_dirs:
            # Move along the wall
            for dist in range(3, 8):  # Try different distances
                target_pos = (
                    current_grid_pos[0] + perp_dir[0] * dist,
                    current_grid_pos[1] + perp_dir[1] * dist
                )
                
                # Check if this is a valid walkable position
                if 0 <= target_pos[0] < maze_rows and 0 <= target_pos[1] < maze_cols:
                    if maze.grid[target_pos[0]][target_pos[1]] == 0:  # Walkable
                        # Check if there's a valid path to this position
                        path = a_star_search(
                            maze.grid, 
                            current_grid_pos, 
                            target_pos, 
                            maze_rows, 
                            maze_cols
                        )
                        if path and len(path) > 1:
                            return target_pos
    
    # If no good wall-following path found, try a random walkable cell
    for _ in range(10):  # Try up to 10 random positions
        rand_row = random.randint(max(0, current_grid_pos[0] - 5), min(maze_rows - 1, current_grid_pos[0] + 5))
        rand_col = random.randint(max(0, current_grid_pos[1] - 5), min(maze_cols - 1, current_grid_pos[1] + 5))
        
        if maze.grid[rand_row][rand_col] == 0:  # Walkable
            return (rand_row, rand_col)
            
    return None


def find_alternative_target(maze, current_grid_pos, primary_target_grid, maze_rows, maze_cols, max_distance=10):
    """
    Find an alternative target when the primary target is unreachable.
    
    Args:
        maze: Maze object with a grid attribute
        current_grid_pos: Current position as (row, col)
        primary_target_grid: Primary target position as (row, col)
        maze_rows: Number of rows in the maze grid
        maze_cols: Number of columns in the maze grid
        max_distance: Maximum distance to search for alternative targets
        
    Returns:
        Alternative target position as (row, col) or None if no suitable target found
    """
    if not maze or not hasattr(maze, 'grid'):
        return None
    
    # Try to find a position closer to the primary target
    best_distance = float('inf')
    best_target = None
    
    # Calculate direction to primary target
    dir_row = primary_target_grid[0] - current_grid_pos[0]
    dir_col = primary_target_grid[1] - current_grid_pos[1]
    
    # Normalize direction
    magnitude = math.sqrt(dir_row**2 + dir_col**2)
    if magnitude > 0:
        dir_row /= magnitude
        dir_col /= magnitude
    
    # Try positions in the general direction of the primary target
    for distance in range(3, max_distance + 1):
        for angle_offset in [0, 15, -15, 30, -30, 45, -45]:
            # Calculate rotated direction
            angle_rad = math.radians(angle_offset)
            rotated_row = dir_row * math.cos(angle_rad) - dir_col * math.sin(angle_rad)
            rotated_col = dir_row * math.sin(angle_rad) + dir_col * math.cos(angle_rad)
            
            # Calculate target position
            target_row = int(current_grid_pos[0] + rotated_row * distance)
            target_col = int(current_grid_pos[1] + rotated_col * distance)
            
            # Check if position is valid
            if 0 <= target_row < maze_rows and 0 <= target_col < maze_cols:
                if maze.grid[target_row][target_col] == 0:  # Walkable
                    # Check if there's a path to this position
                    path = a_star_search(
                        maze.grid,
                        current_grid_pos,
                        (target_row, target_col),
                        maze_rows,
                        maze_cols
                    )
                    
                    if path and len(path) > 1:
                        # Calculate distance to primary target
                        dist_to_primary = math.sqrt(
                            (target_row - primary_target_grid[0])**2 + 
                            (target_col - primary_target_grid[1])**2
                        )
                        
                        # Update best target if this one is closer
                        if dist_to_primary < best_distance:
                            best_distance = dist_to_primary
                            best_target = (target_row, target_col)
    
    return best_target