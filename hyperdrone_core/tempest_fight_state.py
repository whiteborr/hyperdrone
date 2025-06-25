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

    def enter(self, **kwargs):
        print("Entering Tempest Fight State")
        self.next_level = kwargs.get("next_level", 1)
        self.boss_defeated = False
        
        # Clear existing enemies and projectiles before the fight
        self.game.enemy_manager.enemies.empty()
        self.game.enemy_projectiles.empty()

        # Spawn the Tempest boss
        spawn_x = get_setting("display", "SCREEN_WIDTH", 1920) / 2
        spawn_y = 150
        self.boss = self.game.enemy_manager.spawn_enemy_by_id("tempest_boss", spawn_x, spawn_y)

        # Register listener for boss defeat
        self.game.event_manager.register_listener(self.game.game_events.BossDefeatedEvent, self.on_boss_defeated)
        
        # Play boss music
        self.game.asset_manager.play_music("music_boss_fight", loops=-1)

    def exit(self):
        print("Exiting Tempest Fight State")
        # Unregister listener to avoid multiple triggers
        self.game.event_manager.unregister_listener(self.game.game_events.BossDefeatedEvent, self.on_boss_defeated)

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
        self.game.player.handle_events(events)
        for event in events:
            if event.type == USEREVENT + 1:
                # Transition after delay
                self.game.level_manager.set_level(self.next_level)
                self.game.state_manager.set_state('StoryMapState')

    def update(self, delta_time):
        self.game.player.update(self.game.maze, self.game.enemy_manager.enemies, game_area_x_offset=0)
        self.game.enemy_manager.update(self.game.maze, self.game.player)
        self.game.player_projectiles.update(self.game.maze, 0)
        self.game.enemy_projectiles.update(self.game.maze, 0)
        self.game.collectibles_group.update(self.game.player)
        self.game.combat_controller.handle_collisions()

    def draw(self, surface):
        surface.fill(get_setting("colors", "BLACK", (0, 0, 0)))
        self.game.player.draw(surface)
        self.game.enemy_manager.draw(surface)
        self.game.player_projectiles.draw(surface)
        self.game.enemy_projectiles.draw(surface)
        self.game.collectibles_group.draw(surface)
        if self.boss:
            self.game.ui.draw_boss_health_bar(surface, self.boss)

