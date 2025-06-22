# hyperdrone_core/weapons_upgrade_shop_state.py
import pygame
from .state import State
from ui.weapon_shop_ui import WeaponShopUI

class WeaponsUpgradeShopState(State):
    def enter(self, previous_state=None, **kwargs):
        self.previous_state = previous_state
        self.weapon_shop_ui = WeaponShopUI(self.game.asset_manager)
        
        # Get current orichalc fragments count
        fragments_count = getattr(self.game, 'orichalc_fragments', 0)
        
        # Create a mock weapon shop for the UI
        from entities.weapon_shop import WeaponShop
        self.weapon_shop = WeaponShop(0, 0, self.game.asset_manager)
        
        # Show the weapon shop UI
        self.weapon_shop_ui.show(self.weapon_shop, fragments_count, self.game)
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.scene_manager.set_state("MainMenuState")
                    return
                
                # Handle weapon shop input
                cost = self.weapon_shop_ui.handle_input(event.key)
                if cost and cost > 0:
                    # Deduct fragments
                    if hasattr(self.game, 'orichalc_fragments'):
                        self.game.orichalc_fragments -= cost
                    self.weapon_shop_ui.fragments_count -= cost
            
            elif event.type == pygame.MOUSEMOTION or event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                mouse_pressed = pygame.mouse.get_pressed()
                self.weapon_shop_ui.handle_mouse(mouse_pos, mouse_pressed)
    
    def update(self, delta_time):
        pass
    
    def draw(self, surface):
        # Fill background
        surface.fill((20, 20, 40))
        
        # Draw weapon shop UI
        self.weapon_shop_ui.draw(surface)