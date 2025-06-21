# hyperdrone_core/leaderboard_state.py
import pygame
from .state import State

class LeaderboardState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_leaderboard()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("MainMenuState")
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        from constants import BLACK, WHITE, GOLD, CYAN
        
        surface.fill(BLACK)
        
        # Draw stars background if available
        if hasattr(self.game.ui_flow_controller, 'menu_stars') and self.game.ui_flow_controller.menu_stars:
            for star_params in self.game.ui_flow_controller.menu_stars:
                pygame.draw.circle(surface, WHITE, 
                                  (int(star_params[0]), int(star_params[1])), star_params[3])
        
        # Draw title
        font = self.game.asset_manager.get_font("large_text", 48) or pygame.font.Font(None, 48)
        title_surf = font.render("Leaderboard", True, GOLD)
        width = self.game.screen.get_width()
        surface.blit(title_surf, title_surf.get_rect(center=(width // 2, 80)))
        
        # Draw leaderboard entries
        scores = self.game.ui_flow_controller.leaderboard_scores
        font_header = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
        font_score = self.game.asset_manager.get_font("ui_text", 28) or pygame.font.Font(None, 28)
        
        headers = ["RANK", "NAME", "SCORE", "LEVEL"]
        header_positions = [width*0.2, width*0.35, width*0.6, width*0.8]
        
        for i, header in enumerate(headers):
            header_surf = font_header.render(header, True, CYAN)
            surface.blit(header_surf, header_surf.get_rect(center=(header_positions[i], 180)))
            
        for i, score_entry in enumerate(scores):
            y_pos = 250 + i * 50
            color = GOLD if i == 0 else WHITE
            rank_surf = font_score.render(f"{i+1}", True, color)
            name_surf = font_score.render(score_entry.get('name', 'N/A'), True, color)
            score_surf = font_score.render(str(score_entry.get('score', 0)), True, color)
            level_surf = font_score.render(str(score_entry.get('level', 0)), True, color)
            
            surface.blit(rank_surf, rank_surf.get_rect(center=(header_positions[0], y_pos)))
            surface.blit(name_surf, name_surf.get_rect(center=(header_positions[1], y_pos)))
            surface.blit(score_surf, score_surf.get_rect(center=(header_positions[2], y_pos)))
            surface.blit(level_surf, level_surf.get_rect(center=(header_positions[3], y_pos)))