# hyperdrone_core/codex_state.py
import pygame
from .state import State

class CodexState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_codex()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("MainMenuState")
                else:
                    self.game.ui_flow_controller.handle_key_input(event.key, "codex_screen")
    
    def draw(self, surface):
        surface.fill(self.game.gs.BLACK)
        
        # Draw stars background
        if hasattr(self.game.ui_flow_controller, 'menu_stars') and self.game.ui_flow_controller.menu_stars:
            for star_params in self.game.ui_flow_controller.menu_stars:
                pygame.draw.circle(surface, self.game.gs.WHITE, 
                                  (int(star_params[0]), int(star_params[1])), star_params[3])
        
        ui_flow = self.game.ui_flow_controller
        font_title = self.game.asset_manager.get_font("large_text", 52) or pygame.font.Font(None, 52)
        font_cat = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
        font_entry = self.game.asset_manager.get_font("ui_text", 28) or pygame.font.Font(None, 28)
        font_content = self.game.asset_manager.get_font("ui_text", 24) or pygame.font.Font(None, 24)
        
        # Draw title
        title_surf = font_title.render("CODEX", True, self.game.gs.GOLD)
        surface.blit(title_surf, title_surf.get_rect(center=(self.game.gs.WIDTH / 2, 60)))
        
        # Draw content based on current view
        if ui_flow.codex_current_view == "categories":
            start_y = 150
            for i, cat_name in enumerate(ui_flow.codex_categories_list):
                color = self.game.gs.YELLOW if i == ui_flow.codex_selected_category_index else self.game.gs.WHITE
                cat_surf = font_cat.render(cat_name, True, color)
                surface.blit(cat_surf, cat_surf.get_rect(center=(self.game.gs.WIDTH/2, start_y + i * 50)))
        
        elif ui_flow.codex_current_view == "entries":
            cat_title_surf = font_cat.render(f"Category: {ui_flow.codex_current_category_name}", True, self.game.gs.CYAN)
            surface.blit(cat_title_surf, cat_title_surf.get_rect(center=(self.game.gs.WIDTH/2, 140)))
            start_y = 220
            for i, entry_data in enumerate(ui_flow.codex_entries_in_category_list):
                color = self.game.gs.YELLOW if i == ui_flow.codex_selected_entry_index_in_category else self.game.gs.WHITE
                entry_surf = font_entry.render(entry_data.get("title", "Unknown"), True, color)
                surface.blit(entry_surf, (100, start_y + i * 40))
                
        elif ui_flow.codex_current_view == "content":
            entry_details = self.game.drone_system.get_lore_entry_details(ui_flow.codex_selected_entry_id)
            if entry_details:
                content_title_surf = font_cat.render(entry_details.get("title", ""), True, self.game.gs.GOLD)
                surface.blit(content_title_surf, content_title_surf.get_rect(center=(self.game.gs.WIDTH/2, 140)))
                
                content_text = entry_details.get("content", "No content available.")
                wrapped_lines = self.game.ui_manager._wrap_text_with_font_obj(content_text, font_content, self.game.gs.WIDTH - 200)
                ui_flow.codex_current_entry_total_lines = len(wrapped_lines)

                start_y, line_height = 220, font_content.get_linesize()
                for i, line in enumerate(wrapped_lines[ui_flow.codex_content_scroll_offset:]):
                    line_surf = font_content.render(line, True, self.game.gs.WHITE)
                    line_y = start_y + i * line_height
                    if line_y > self.game.gs.HEIGHT - 100: break
                    surface.blit(line_surf, (100, line_y))