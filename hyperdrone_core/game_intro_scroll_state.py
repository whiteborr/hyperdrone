# hyperdrone_core/game_intro_scroll_state.py
import pygame
from .state import State

class GameIntroScrollState(State):
    def enter(self, previous_state=None, **kwargs):
        self.game.ui_flow_controller.initialize_game_intro(self.game._load_intro_data())
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.game.ui_flow_controller.advance_intro_screen()
                elif event.key == pygame.K_ESCAPE:
                    self.game.ui_flow_controller.skip_intro()
    
    def update(self, delta_time):
        if self.game.ui_flow_controller.intro_sequence_finished:
            self.game.state_manager.set_state("PlayingState")
    
    def draw(self, surface):
        surface.fill(self.game.gs.BLACK)
        
        ui_flow = self.game.ui_flow_controller
        if not ui_flow.intro_screens_data or ui_flow.current_intro_screen_index >= len(ui_flow.intro_screens_data):
            return

        current_screen_data = ui_flow.intro_screens_data[ui_flow.current_intro_screen_index]
        image_key = current_screen_data.get("image_path_key")
        text = current_screen_data.get("text", "")
        
        screen_width = self.game.gs.get_game_setting("WIDTH")
        screen_height = self.game.gs.get_game_setting("HEIGHT")

        # Draw background image
        if image_key:
            bg_image = self.game.asset_manager.get_image(image_key)
            if bg_image:
                bg_surf = pygame.transform.scale(bg_image, (screen_width, screen_height))
                surface.blit(bg_surf, (0, 0))

        # Draw text
        lines = text.split('\n')
        font = self.game.asset_manager.get_font("medium_text", 36) or pygame.font.Font(None, 36)
        start_y = screen_height - (len(lines) * 40) - 100

        for i, line in enumerate(lines):
            line_surf = font.render(line, True, self.game.gs.WHITE)
            surface.blit(line_surf, line_surf.get_rect(center=(screen_width / 2, start_y + i * 40)))
            
        # Draw prompt
        prompt_surf = font.render("Press SPACE to continue...", True, self.game.gs.GOLD)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(screen_width / 2, screen_height - 50)))