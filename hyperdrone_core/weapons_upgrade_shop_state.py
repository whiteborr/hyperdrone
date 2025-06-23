# hyperdrone_core/weapons_upgrade_shop_state.py
from pygame.mouse import get_pos as mouse_get_pos, get_pressed as mouse_get_pressed
from pygame import KEYDOWN, MOUSEMOTION, MOUSEBUTTONDOWN, K_ESCAPE
from .state import State
from ui.weapon_shop_ui import WeaponShopUI

class WeaponsUpgradeShopState(State):
    def enter(self, previous_state=None, **kwargs):
        self.previous_state = previous_state or "PlayingState"
        self.weapon_shop_ui = WeaponShopUI(self.game.asset_manager)
        
        # Pause timer for levels 2 and 7
        if hasattr(self.game, 'level_manager') and self.game.level_manager.level in [2, 7]:
            self.game.level_manager.pause_timer()
        
        # Get current cores count
        fragments_count = self.game.drone_system.get_cores() if hasattr(self.game, 'drone_system') else 0
        
        # Create a mock weapon shop for the UI
        from entities.weapon_shop import WeaponShop
        self.weapon_shop = WeaponShop(0, 0, self.game.asset_manager)
        
        # Show the weapon shop UI
        self.weapon_shop_ui.show(self.weapon_shop, fragments_count, self.game)
    
    def handle_events(self, events):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    # Resume timer for levels 2 and 7 when exiting
                    if hasattr(self.game, 'level_manager') and self.game.level_manager.level in [2, 7]:
                        self.game.level_manager.resume_timer()
                    self.game.state_manager.set_state(self.previous_state)
                    return
                
                # Handle weapon shop input
                result = self.weapon_shop_ui.handle_input(event.key)
                if result and result > 0:
                    # Deduct cores
                    if hasattr(self.game, 'drone_system'):
                        self.game.drone_system.spend_cores(result)
                    self.weapon_shop_ui.fragments_count -= result
            
            elif event.type == MOUSEMOTION or event.type == MOUSEBUTTONDOWN:
                mouse_pos = mouse_get_pos()
                mouse_pressed = mouse_get_pressed()
                self.weapon_shop_ui.handle_mouse(mouse_pos, mouse_pressed)
    
    def update(self, delta_time):
        pass
    
    def exit(self, next_state=None):
        # Resume timer for levels 2 and 7 when exiting state
        if hasattr(self.game, 'level_manager') and self.game.level_manager.level in [2, 7]:
            self.game.level_manager.resume_timer()
    
    def draw(self, surface):
        # Fill background
        surface.fill((20, 20, 40))
        
        # Draw weapon shop UI
        self.weapon_shop_ui.draw(surface)
