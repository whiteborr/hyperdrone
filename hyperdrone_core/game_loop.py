# hyperdrone_core/game_loop.py
from sys import exit
from os.path import join, exists
from random import uniform, choice, randint
from math import cos, sin, radians
from json import load
from logging import getLogger

from pygame import init as pygame_init, quit as pygame_quit
from pygame.mixer import init as mixer_init
from pygame.mouse import set_visible
from pygame.display import Info, set_mode, set_caption, flip
from pygame.time import Clock, get_ticks
from pygame.event import get as event_get
from pygame.sprite import Group, GroupSingle, collide_rect, spritecollide
from pygame.transform import scale
from pygame.font import Font
from pygame import FULLSCREEN, QUIT, error as pygame_error

from .state_manager import StateManager
from .event_manager import EventManager
from .player_actions import PlayerActions
from ui.leaderboard_ui import add_score, is_high_score, load_scores
from .combat_controller import CombatController
from .puzzle_controller import PuzzleController
from .ui_flow_controller import UIFlowController
from ui import UIManager 
from .level_manager import LevelManager 
from .asset_manager import AssetManager
from story import StoryManager, Chapter, Objective 

from entities import (
    PlayerDrone, CoreReactor, Turret, LightningZap, Missile, Particle, GlitchingWall,
    MazeGuardian, SentinelDrone, EscapeZone, Maze, MazeChapter3, Bullet
)
from entities.collectibles import (
    Ring as CollectibleRing, WeaponUpgradeItem, ShieldItem, SpeedBoostItem,
    CoreFragmentItem, GlyphTabletItem, AncientAlienTerminal, 
    ArchitectEchoItem, CorruptedLogItem, QuantumCircuitryItem, WeaponsUpgradeShopItem
)
from entities.temporary_barricade import TemporaryBarricade
from drone_management import DroneSystem, DRONE_DATA
from settings_manager import get_setting, set_setting, save_settings, settings_manager
from entities.orichalc_fragment import OrichalcFragment
from entities.orichalc_pickup_system import HUDContainer

logger_gc = getLogger(__name__)

class GameController:
    def __init__(self):
        pygame_init()
        mixer_init()
        set_visible(False)

        # Setup display
        self._setup_display()
        
        # Initialize core systems
        self.asset_manager = AssetManager(base_asset_folder_name="assets")
        self.drone_system = DroneSystem()
        self.asset_manager.preload_game_assets()

        self.clock = Clock()
        
        # Game state
        self.player = None
        self.maze = None
        self.camera = None
        self.score = 0
        self.level = 1
        self.lives = get_setting("gameplay", "PLAYER_LIVES", 3)
        self.paused = False
        self.is_build_phase = False
        
        # Initialize sprite groups
        self._init_sprite_groups()
        
        # Initialize controllers
        self._init_controllers()
        
        # Initialize story system
        self._init_story_system()
        
        # Initialize UI and state management
        self._init_ui_and_states()
        
        # Game timers and messages
        self._init_timers_and_messages()
        
        # Initialize missing attributes
        self.weapon_shop_used_level_2 = False
        self.weapon_shop_used_level_7 = False
        self._death_handled = False
        
        logger_gc.info("GameController initialized successfully.")

    def _setup_display(self):
        try:
            info = Info()
            width, height = max(1920, info.current_w), max(1080, info.current_h)
            set_setting("display", "WIDTH", width)
            set_setting("display", "HEIGHT", height)
            logger_gc.info(f"Screen resolution: {width}x{height}")
        except pygame_error as e:
            logger_gc.error(f"Could not detect screen size: {e}. Using default.")

        self.screen_flags = FULLSCREEN if get_setting("display", "FULLSCREEN_MODE", False) else 0
        self.screen = set_mode((get_setting("display", "WIDTH", 1920), 
                              get_setting("display", "HEIGHT", 1080)), self.screen_flags)
        set_caption("HYPERDRONE")

    def _init_sprite_groups(self):
        self.collectible_rings_group = Group()
        self.power_ups_group = Group()
        self.core_fragments_group = Group()
        self.vault_logs_group = Group()
        self.glyph_tablets_group = Group()
        self.architect_echoes_group = Group()
        self.alien_terminals_group = Group()
        self.architect_vault_puzzle_terminals_group = Group()
        self.explosion_particles_group = Group()
        self.escape_zone_group = GroupSingle()
        self.reactor_group = GroupSingle()
        self.turrets_group = Group()
        self.corrupted_logs_group = Group()
        self.quantum_circuitry_group = GroupSingle()
        self.spawned_barricades_group = Group()
        self.glitching_walls_group = Group()
        self.energy_particles_group = Group()
        self.animating_fragments_to_hud = []

    def _init_controllers(self):
        self.player_actions = PlayerActions(self)
        self.combat_controller = CombatController(self, self.asset_manager)
        self.puzzle_controller = PuzzleController(self, self.asset_manager)
        self.ui_flow_controller = UIFlowController(self)
        self.ui_manager = UIManager(self.screen, self.asset_manager, self, None, self.drone_system)
        
        from .item_manager import ItemManager
        self.item_manager = ItemManager(self, self.asset_manager)
        
        self.hud_container = HUDContainer(self.asset_manager)
        self.level_manager = LevelManager(self)

    def _init_story_system(self):
        self.story_manager = StoryManager(state_manager_ref=None, drone_system_ref=self.drone_system)
        
        # Create chapters
        chapters = [
            Chapter("chapter_1", "Chapter 1: The Anomaly", 
                   "A strange energy signature requires investigation.", 
                   [Objective("c1_collect_rings", "Gather energy signatures", "collect_all", "rings"),
                    Objective("c1_clear_hostiles", "Neutralize defense drones", "kill_all", "standard_enemies")], 
                   "PlayingState"),
            Chapter("chapter_2", "Chapter 2: The Guardian", 
                   "The Vault's defenses are active and hostile.", 
                   [Objective("c2_defeat_guardian", "Decommission the Guardian", "kill", "MAZE_GUARDIAN")], 
                   "BossFightState"),
            Chapter("chapter_3", "Chapter 3: The Corrupted Sector", 
                   "This sector is unstable. Find out why.", 
                   [Objective("c3_find_log_alpha", "Find Corrupted Log Alpha", "collect", "log_alpha"),
                    Objective("c3_find_log_beta", "Access secure data", "collect", "log_beta")], 
                   "CorruptedSectorState"),
            Chapter("chapter_4", "Chapter 4: The Harvest Chamber",
                   "Descend into the Vault's intake chamber.", 
                   [Objective("c4_retrieve_payload", "Retrieve Quantum Circuitry", "collect", "quantum_circuitry")],
                   "HarvestChamberState"),
            Chapter("chapter_5", "Chapter 5: The Final Confrontation",
                   "Face the ultimate challenge.", 
                   [Objective("c5_final_objective", "Complete final mission", "complete", "final_mission")],
                   "MazeDefenseState")
        ]
        
        for chapter in chapters:
            self.story_manager.add_chapter(chapter)
        
        self.story_manager.start_story()

    def _init_ui_and_states(self):
        self.ui_flow_controller.set_dependencies(None, self.ui_manager, self.drone_system)
        self.event_manager = EventManager(self, None, self.combat_controller, self.puzzle_controller, self.ui_flow_controller)
        
        from hyperdrone_core.game_events import EnemyDefeatedEvent
        self.event_manager.register_listener(EnemyDefeatedEvent, self.on_enemy_defeated_effects)
        
        self.state_manager = StateManager(self)
        self.ui_manager.state_manager = self.state_manager
        self.ui_flow_controller.scene_manager = self.state_manager
        self.event_manager.scene_manager = self.state_manager
        self.story_manager.state_manager = self.state_manager

    def _init_timers_and_messages(self):
        self.hud_displayed_fragments = set()
        self.fragment_ui_target_positions = {}
        
        self.level_timer_start_ticks = 0
        self.level_time_remaining_ms = get_setting("progression", "LEVEL_TIMER_DURATION", 120000)
        self.bonus_level_timer_start = 0
        self.bonus_level_duration_ms = get_setting("progression", "BONUS_LEVEL_DURATION_MS", 60000)
        self.bonus_level_start_display_end_time = 0
        
        self.architect_vault_current_phase = None
        self.architect_vault_phase_timer_start = 0
        self.architect_vault_message = ""
        self.architect_vault_message_timer = 0
        self.architect_vault_failure_reason = ""
        
        self.story_message = ""
        self.story_message_active = False
        self.story_message_end_time = 0
        self.STORY_MESSAGE_DURATION = 5000
        self.triggered_story_beats = set()
        
        self.current_intro_image_asset_key = None
        self.intro_screen_text_surfaces_current = []
        self.intro_font_key = "codex_category_font"
        
        self.STORY_FONT_TITLE = Font(None, 48)
        self.STORY_FONT_BODY = Font(None, 28)
        self.STORY_TEXT_COLOR = (220, 220, 220)
        self.STORY_TITLE_COLOR = (255, 255, 255)
    
    def run(self):
        while True:
            delta_time_ms = self.clock.tick(get_setting("display", "FPS", 60))
            
            # Handle events
            events = event_get()
            for event in events:
                if event.type == QUIT:
                    self.quit_game()
            
            current_state = self.state_manager.get_current_state()
            if current_state:
                current_state.handle_events(events)
            
            # Update game state
            if current_state and not self.paused:
                current_state.update(delta_time_ms)
                self.energy_particles_group.update()
                self.hud_container.update()

            # Check particle arrivals
            for particle in list(self.energy_particles_group):
                if particle.has_arrived():
                    self.hud_container.trigger_pulse()
                    particle.kill()
            
            # Update systems
            current_time_ms = get_ticks()
            if current_state:
                self.ui_flow_controller.update(current_time_ms, delta_time_ms, current_state.get_state_id())
            
            if self.story_message_active and current_time_ms > self.story_message_end_time:
                self.story_message_active = False
                self.story_message = ""
            
            self.state_manager.update()
            
            # Draw everything
            if current_state:
                current_state.draw(self.screen)
            
            # Draw HUD and particles
            current_state_id = self.state_manager.get_current_state_id()
            current_chapter = self.story_manager.get_current_chapter()
            if (current_state_id in ["PlayingState", "BonusLevelPlayingState"] and 
                current_chapter and current_chapter.chapter_id == "chapter_1"):
                orichalc_count = self.drone_system.get_cores()
                self.hud_container.draw(self.screen, orichalc_count)
            self.energy_particles_group.draw(self.screen)

            # Draw UI
            active_abilities_data = {}
            if self.player and hasattr(self.player, 'active_abilities') and self.player.active_abilities:
                active_abilities_data = self.player.active_abilities
            
            self.ui_manager.draw_current_scene_ui(player_active_abilities_data=active_abilities_data)
            self._draw_story_overlay(self.screen)
            self.state_manager.draw_fade_transition(self.screen)

            flip()

    def handle_state_transition(self, new_state, old_state, **kwargs):
        self.paused = False
        
        state_handlers = {
            "MainMenuState": lambda: self.ui_flow_controller.initialize_main_menu(kwargs.get('selected_option', 0)),
            "DroneSelectState": lambda: self.ui_flow_controller.initialize_drone_select(),
            "SettingsState": lambda: self.ui_flow_controller.initialize_settings(self._get_settings_menu_items_data_structure()),
            "LeaderboardState": lambda: self.ui_flow_controller.initialize_leaderboard(),
            "CodexState": lambda: self.ui_flow_controller.initialize_codex(),
            "EnterNameState": lambda: self.ui_flow_controller.initialize_enter_name(),
            "GameIntroScrollState": lambda: self.ui_flow_controller.initialize_game_intro(self._load_intro_data())
        }
        
        handler = state_handlers.get(new_state)
        if handler:
            handler()

    def toggle_pause(self):
        self.paused = not self.paused
        logger_gc.info(f"Game {'paused' if self.paused else 'resumed'}")
        self.state_manager._update_music()

    def quit_game(self):
        if self.drone_system: 
            self.drone_system._save_unlocks()
        pygame_quit()
        exit()
        
    def play_sound(self, key, vol=0.7, volume_override=None):
        if not hasattr(self, 'asset_manager'):
            return
            
        sound = self.asset_manager.get_sound(key)
        if sound:
            try:
                if volume_override is not None:
                    final_volume = vol * volume_override
                else:
                    fx_volume = get_setting("audio", "VOLUME_FX", 7) / 10.0
                    final_volume = vol * fx_volume
                sound.set_volume(final_volume)
                sound.play()
            except Exception as e:
                logger_gc.error(f"Error playing sound '{key}': {e}")
        else:
            logger_gc.warning(f"Sound '{key}' not found")
            
    def _load_intro_data(self):
        fallback = [{"text": "The Architect has vanished.", "image_path_key": "images/lore/scene1.png"}]
        intro_path = join("data", "intro.json") 
        
        if not exists(intro_path):
            return fallback
            
        try:
            with open(intro_path, 'r', encoding='utf-8') as f:
                data = load(f)
                if isinstance(data, list) and all("text" in item and "image_path" in item for item in data):
                    return [{"text": item["text"], 
                            "image_path_key": item["image_path"].replace("assets/", "").replace("\\", "/")} 
                           for item in data]
        except Exception as e:
            logger_gc.error(f"Error loading intro.json: {e}")
            
        return fallback
    
    def _get_settings_menu_items_data_structure(self):
        weapon_modes = get_setting("weapon_modes", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3])
        weapon_names = get_setting("weapon_modes", "WEAPON_MODE_NAMES", {})
        weapon_names = {int(k): v for k, v in weapon_names.items()} if weapon_names else {
            0: "Standard", 1: "Spread", 2: "Rapid", 3: "Missile"
        }
        
        chapters = []
        chapter_names = {}
        for i, chapter in enumerate(self.story_manager.chapters):
            chapter_id = f"chapter_{i+1}"
            chapters.append(chapter_id)
            chapter_names[chapter_id] = chapter.title
        
        return [
            {"label":"Volume [FX]","key":"VOLUME_FX","category":"audio","type":"numeric","min":0,"max":10,"step":1},
            {"label":"Volume [Game]","key":"VOLUME_GAME","category":"audio","type":"numeric","min":0,"max":10,"step":1},
            {"label":"Base Max Health","key":"PLAYER_MAX_HEALTH","category":"gameplay","type":"numeric","min":50,"max":200,"step":10},
            {"label":"Starting Lives","key":"PLAYER_LIVES","category":"gameplay","type":"numeric","min":1,"max":9,"step":1},
            {"label":"Base Speed","key":"PLAYER_SPEED","category":"gameplay","type":"numeric","min":1,"max":10,"step":1},
            {"label":"Initial Weapon","key":"INITIAL_WEAPON_MODE","category":"gameplay","type":"choice",
             "choices":weapon_modes, "get_display":lambda val:weapon_names.get(val,"Unknown")},
            {"label":"Invincibility","key":"PLAYER_INVINCIBILITY","category":"gameplay","type":"choice",
             "choices":[False, True], "get_display":lambda val:"ON" if val else "OFF"},
            {"label":"Enemy Speed","key":"ENEMY_SPEED","category":"enemies","type":"numeric","min":0.5,"max":5.0,"step":0.1},
            {"label":"Enemy Health","key":"ENEMY_HEALTH","category":"enemies","type":"numeric","min":10,"max":100,"step":5},
            {"label":"Shield Duration (sec)","key":"SHIELD_POWERUP_DURATION","category":"powerups","type":"numeric","min":5000,"max":30000,"step":1000,"is_ms_to_sec":True,"display_format":"{:.0f}s"},
            {"label":"Speed Boost Duration (sec)","key":"SPEED_BOOST_POWERUP_DURATION","category":"powerups","type":"numeric","min":3000,"max":20000,"step":1000,"is_ms_to_sec":True,"display_format":"{:.0f}s"},
            {"label":"Level Timer (sec)","key":"LEVEL_TIMER_DURATION","category":"progression","type":"numeric","min":30000,"max":300000,"step":10000,"is_ms_to_sec":True,"display_format":"{:.0f}s"},
            {"label":"Start Chapter","key":"START_CHAPTER","category":"testing","type":"choice",
             "choices":chapters, "get_display":lambda val:chapter_names.get(val,"Unknown"),
             "action":"start_chapter"},
            {"label":"Reset to Defaults","key":"RESET_SETTINGS_ACTION","type":"action"},
        ] 
        
    def _get_safe_spawn_point(self, width, height):
        if self.maze and hasattr(self.maze, 'get_walkable_tiles_abs'):
            walkable = self.maze.get_walkable_tiles_abs()
            if walkable:
                screen_width = get_setting("display", "WIDTH", 1920)
                screen_height = get_setting("display", "GAME_PLAY_AREA_HEIGHT", 960)
                
                visible = [pos for pos in walkable if 0 < pos[0] < screen_width and 0 < pos[1] < screen_height]
                return choice(visible if visible else walkable)
        return (200, 200)
        
    def _respawn_player(self):
        if not self.maze:
            return
            
        tile_size = get_setting("display", "TILE_SIZE", 64)
        spawn_x, spawn_y = self._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
        
        drone_id = self.drone_system.get_selected_drone_id()
        drone_stats = self.drone_system.get_drone_stats(drone_id)
        sprite_key = f"drone_{drone_id}_ingame_sprite"
        
        self.player = PlayerDrone(spawn_x, spawn_y, drone_id, drone_stats, 
                                 self.asset_manager, sprite_key, 'crash', self.drone_system)
        
        self.combat_controller.set_active_entities(player=self.player, maze=self.maze, power_ups_group=self.power_ups_group)
        self.puzzle_controller.set_active_entities(player=self.player, drone_system=self.drone_system, scene_manager=self.state_manager)

    def _handle_player_death_or_life_loss(self, reason=""):
        if hasattr(self, '_death_handled') and self._death_handled:
            return
            
        self._death_handled = True
        self.player.alive = False 
        self._create_explosion(self.player.x, self.player.y, 6, 'crash')
        self.lives -= 1
        
        logger_gc.info(f"Player died. Lives remaining: {self.lives}")
        
        if self.lives > 0:
            self.set_story_message(f"Lives remaining: {self.lives}", 2000)
            self._respawn_player()
            self._death_handled = False
        else:
            logger_gc.info("Game over")
            current_state_id = self.state_manager.get_current_state_id()
            self.state_manager.set_state("GameOverState", prev_state=current_state_id)
    
    def _create_explosion(self, x, y, num_particles=20, specific_sound_key=None, is_enemy=False):
        colors = {
            'orange': get_setting("colors", "ORANGE", (255, 165, 0)),
            'yellow': get_setting("colors", "YELLOW", (255, 255, 0)),
            'red': get_setting("colors", "RED", (255, 0, 0)),
            'white': get_setting("colors", "WHITE", (255, 255, 255))
        }
        
        # Flash particle
        flash_size = uniform(3.0, 5.0) if is_enemy else 8.0
        self.explosion_particles_group.add(
            Particle(x, y, [colors['white'], colors['yellow']], 
                    min_speed=0.5, max_speed=1.0, 
                    min_size=flash_size*0.8, max_size=flash_size, 
                    gravity=0, shrink_rate=0.2, 
                    lifetime_frames=10 if is_enemy else 12)
        )
        
        # Main explosion particles
        if is_enemy:
            particle_colors = [colors['red'], colors['orange'], colors['yellow']]
            particle_count = 15
            gravity = 0.01
        else:
            particle_colors = [colors['orange'], colors['yellow'], colors['red']]
            particle_count = num_particles
            gravity = 0.02
            
        for _ in range(particle_count):
            angle = uniform(0, 360)
            if is_enemy:
                distance = uniform(2.0, 4.0)
                px = x + cos(radians(angle)) * distance
                py = y + sin(radians(angle)) * distance
                speed = uniform(1.5, 3.0)
                size = uniform(1.5, 3.0)
                lifetime = randint(15, 25)
            else:
                px, py = x, y
                speed = uniform(2.0, 4.0)
                size = uniform(2.0, 4.0)
                lifetime = randint(20, 30)
            
            self.explosion_particles_group.add(
                Particle(px, py, particle_colors, 
                        min_speed=speed*0.8, max_speed=speed, 
                        min_size=size*0.8, max_size=size, 
                        gravity=gravity, shrink_rate=0.08, 
                        lifetime_frames=lifetime,
                        base_angle_deg=angle, spread_angle_deg=15 if is_enemy else 20)
            )
                
        if specific_sound_key:
            self.play_sound(specific_sound_key)
            
    def on_enemy_defeated_effects(self, event):
        self._create_explosion(event.position[0], event.position[1], 15, None, True)
    
    def check_for_all_enemies_killed(self):
        if self.combat_controller.enemy_manager.get_active_enemies_count() == 0:
            self.level_manager.all_enemies_killed_this_level = True
    
    def _draw_game_world(self):
        self.screen.fill(get_setting("colors", "BLACK", (0, 0, 0)))
        
        if self.maze:
            self.maze.draw(self.screen, self.camera)
        
        # Draw all item groups
        item_groups = [
            self.collectible_rings_group, self.power_ups_group, self.core_fragments_group,
            self.vault_logs_group, self.glyph_tablets_group, self.architect_echoes_group,
            self.corrupted_logs_group, self.quantum_circuitry_group, self.spawned_barricades_group
        ]
        
        for group in item_groups:
            for item in group:
                item.draw(self.screen, self.camera)
        
        self.explosion_particles_group.update()
        self.explosion_particles_group.draw(self.screen) 

        if self.player:
            self.player.draw(self.screen, self.camera)
            
        # Draw game-specific elements
        current_state = self.state_manager.get_current_state_id()
        if current_state == get_setting("game_states", "GAME_STATE_MAZE_DEFENSE", "maze_defense_mode"):
            if hasattr(self, 'tower_defense_manager'):
                self.tower_defense_manager.draw(self.screen, self.camera)
            
        if self.combat_controller:
            self.combat_controller.enemy_manager.draw_all(self.screen, self.camera)
            
        for group in [self.turrets_group, self.reactor_group]:
            for item in group:
                item.draw(self.screen, self.camera)
                
        # Draw animations
        ring_icon = self.asset_manager.get_image("ring_ui_icon")
        self.level_manager.draw_ring_animations(self.screen, ring_icon)
        self._draw_fragment_animations()
    
    def _handle_collectible_collisions(self):
        if not self.player or not hasattr(self.player, 'rect'):
            return None
            
        # Ring collisions
        for ring in spritecollide(self.player, self.collectible_rings_group, True):
            self.level_manager.collect_ring(ring.rect.center)
            self.play_sound('collect_ring')
            
        # Power-up collisions
        for powerup in spritecollide(self.player, self.power_ups_group, True):
            if isinstance(powerup, WeaponUpgradeItem):
                powerup.apply_effect(self.player)
                self.play_sound('weapon_upgrade_collect')
                if hasattr(self.ui_manager, 'update_weapon_icon_surface'):
                    self.ui_manager.update_weapon_icon_surface(self.player.current_weapon_mode)
            elif isinstance(powerup, WeaponsUpgradeShopItem):
                powerup.apply_effect(self.player, self)
            elif isinstance(powerup, (ShieldItem, SpeedBoostItem)):
                powerup.apply_effect(self.player)
                self.play_sound('collect_ring')
                
        # Fragment collisions
        collected_log_id = None
        for fragment in list(self.core_fragments_group):
            if not isinstance(fragment, OrichalcFragment) and collide_rect(self.player, fragment):
                fragment.kill()
                fragment_id = fragment.fragment_id
                self.drone_system.collect_core_fragment(fragment_id)
                
                if hasattr(fragment, 'associated_ability') and fragment.associated_ability:
                    if hasattr(self.player, 'unlock_ability'):
                        self.player.unlock_ability(fragment.associated_ability)

                self.play_sound('collect_fragment')
                self._animate_fragment_to_hud(fragment, fragment_id)
                
                from .game_events import ItemCollectedEvent
                event = ItemCollectedEvent(item_id=fragment_id, item_type='core_fragment')
                self.event_manager.dispatch(event)

        # Log collisions
        for log in spritecollide(self.player, self.corrupted_logs_group, True):
            if hasattr(log, 'apply_effect'):
                log.apply_effect(self.player, self)
                collected_log_id = log.log_id

        # Quantum circuitry collisions
        for qc in spritecollide(self.player, self.quantum_circuitry_group, True):
            if hasattr(qc, 'apply_effect'):
                qc.apply_effect(self.player, self)
        
        # Orichalc fragment collisions
        for fragment in list(self.core_fragments_group):
            if isinstance(fragment, OrichalcFragment) and not fragment.collected:
                if collide_rect(self.player, fragment):
                    particle = fragment.start_pickup_animation(self.hud_container)
                    self.energy_particles_group.add(particle)
                    fragment.apply_effect(self.player, self)
                    fragment.kill()
        
        return collected_log_id

    def _animate_fragment_to_hud(self, fragment, fragment_id):
        fragment_pos = (fragment.center_x, fragment.center_y)
        
        # Calculate target position
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        bottom_panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)
        frags_x = width - 150
        frags_y = height - bottom_panel_height + 65
        
        target_pos = self.fragment_ui_target_positions.get(fragment_id)
        if not target_pos:
            core_fragment_details = settings_manager.get_core_fragment_details()
            required = sorted([d['id'] for d in core_fragment_details.values() if d.get('required_for_vault')])
            try:
                index = required.index(fragment_id)
                target_x = frags_x + index * (self.ui_manager.ui_icon_size_fragments[0] + 5) + self.ui_manager.ui_icon_size_fragments[0] // 2
                target_y = frags_y + self.ui_manager.ui_icon_size_fragments[1] // 2
                target_pos = (target_x, target_y)
            except ValueError:
                target_x = frags_x + len(required) * (self.ui_manager.ui_icon_size_fragments[0] + 5) + self.ui_manager.ui_icon_size_fragments[0] // 2
                target_y = frags_y + self.ui_manager.ui_icon_size_fragments[1] // 2
                target_pos = (target_x, target_y)
        
        self.animating_fragments_to_hud.append({
            'pos': list(fragment_pos),
            'start_time': get_ticks(),
            'duration': 1500,
            'start_pos': fragment_pos,
            'target_pos': target_pos,
            'fragment_id': fragment_id
        })
    
    def _check_level_clear_condition(self):
        return self.level_manager.check_level_clear_condition()
        
    def set_story_message(self, message, duration=5000):
        self.story_message = message
        self.story_message_active = True
        self.story_message_end_time = get_ticks() + duration
    
    def _draw_fragment_animations(self):
        current_time = get_ticks()
        
        for i in range(len(self.animating_fragments_to_hud) - 1, -1, -1):
            fragment_data = self.animating_fragments_to_hud[i]
            elapsed = current_time - fragment_data['start_time']
            progress = min(1.0, elapsed / fragment_data['duration'])
            
            if progress >= 1.0:
                self.animating_fragments_to_hud.pop(i)
                continue
                
            # Ease animation
            ease_progress = 1 - (1 - progress) ** 3
            x = fragment_data['start_pos'][0] + (fragment_data['target_pos'][0] - fragment_data['start_pos'][0]) * ease_progress
            y = fragment_data['start_pos'][1] + (fragment_data['target_pos'][1] - fragment_data['start_pos'][1]) * ease_progress
            
            # Draw fragment
            fragment_id = fragment_data['fragment_id']
            fragment_icon = self.ui_manager.get_scaled_fragment_icon_surface(fragment_id)
            
            if fragment_icon:
                icon_size = self.ui_manager.ui_icon_size_fragments
                scaled_icon = scale(fragment_icon, icon_size)
                icon_rect = scaled_icon.get_rect(center=(int(x), int(y)))
                self.screen.blit(scaled_icon, icon_rect)
    
    def _draw_story_overlay(self, surface):
        current_state = self.state_manager.get_current_state_id()
        if current_state != "StoryMapState":
            return