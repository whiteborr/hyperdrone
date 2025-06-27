# hyperdrone_core/tempest_fight_state.py
from pygame.time import set_timer
from pygame import USEREVENT
from .state import State
from settings_manager import get_setting
from entities.collectibles import CoreFragmentItem

class TempestFightState(State):
    """
    A dedicated game state for the boss fight against the Tempest.
    """
    def __init__(self, game):
        super().__init__(game)
        self.boss = None
        self.boss_defeated = False
        self.next_level = 0

    def enter(self, previous_state=None, **kwargs):
        print("Entering Tempest Fight State")
        self.next_level = kwargs.get("next_level", 1)
        self.boss_defeated = False
        
        # Clear existing enemies and projectiles before the fight
        self.game.combat_controller.enemy_manager.enemies.empty()
        
        # Spawn the Tempest boss
        spawn_x = get_setting("display", "WIDTH", 1920) / 2
        spawn_y = 150
        # For now, just set boss_defeated to True to test transition
        self.boss_defeated = True

        # Immediately transition back to story map for testing
        set_timer(USEREVENT + 1, 2000, 1)  # 2-second delay

    def exit(self, next_state=None):
        print("Exiting Tempest Fight State")

    def on_boss_defeated(self, event):
        if event.boss_id == "tempest_boss" and not self.boss_defeated:
            self.boss_defeated = True
            print("Tempest has been defeated!")
            
            # Spawn the Air Core Fragment as a reward
            fragment = CoreFragment(
                self.game,
                self.boss.rect.centerx,
                self.boss.rect.centery,
                'air'
            )
            self.game.collectibles_group.add(fragment)
            
            # Transition to the story map after a short delay
            set_timer(USEREVENT + 1, 3000, 1) # 3-second delay

    def handle_events(self, events):
        for event in events:
            if event.type == USEREVENT + 1:
                # Transition after delay
                self.game.state_manager.set_state('StoryMapState')

    def update(self, delta_time):
        pass  # Simplified for testing

    def draw(self, surface):
        surface.fill((50, 0, 0))  # Dark red background for boss fight
        # Draw "TEMPEST BOSS FIGHT" text
        from pygame.font import Font
        font = Font(None, 72)
        text = font.render("TEMPEST BOSS FIGHT", True, (255, 255, 255))
        text_rect = text.get_rect(center=(surface.get_width()//2, surface.get_height()//2))
        surface.blit(text, text_rect)

