# hyperdrone_core/event_manager.py
import pygame
import sys
import logging
import time
from collections import defaultdict

from settings_manager import get_setting
from constants import (
    GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS,
    GAME_STATE_LEADERBOARD, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, GAME_STATE_CODEX,
    GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_RING_PUZZLE, GAME_STATE_MAZE_DEFENSE
)
from .event_batch import EventBatch

logger = logging.getLogger(__name__)

class EventManager:
    def __init__(self, game_controller_ref, scene_manager_ref, combat_controller_ref, puzzle_controller_ref, ui_flow_controller_ref):
        self.game_controller = game_controller_ref
        self.scene_manager = scene_manager_ref
        self.combat_controller = combat_controller_ref
        self.puzzle_controller = puzzle_controller_ref
        self.ui_flow_controller = ui_flow_controller_ref
        
        # Event bus system
        self.listeners = defaultdict(list)
        
        # Event batching system
        self.event_batches = {}
        self.batch_enabled = get_setting("gameplay", "EVENT_BATCHING_ENABLED", True)
        
        logger.info("EventManager initialized.")

    def process_events(self):
        """
        Process all game events for the current frame.
        This includes pygame events, camera controls, and player input.
        """
        current_time_ms = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()
        
        # Handle camera panning in maze defense mode
        if current_game_state == GAME_STATE_MAZE_DEFENSE and not self.game_controller.paused and self.game_controller.camera:
            self._handle_camera_panning()

        # Process pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game_controller.quit_game()
            
            # Mouse wheel for zoom in maze defense
            if event.type == pygame.MOUSEWHEEL and current_game_state == GAME_STATE_MAZE_DEFENSE and self.game_controller.camera:
                self._handle_mouse_wheel(event)

            # Keyboard events
            if event.type == pygame.KEYDOWN:
                self._handle_key_down(event, current_game_state)

            # Key up events
            if event.type == pygame.KEYUP and not self.game_controller.paused:
                self.game_controller.player_actions.handle_key_up(event)
            
            # Mouse button events
            if event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event, current_game_state)

        # Handle continuous player movement in gameplay states
        is_gameplay_state = current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or (isinstance(current_game_state, str) and current_game_state.startswith("architect_vault"))
        if is_gameplay_state and not self.game_controller.paused:
            self.game_controller.player_actions.update_player_movement_and_actions(current_time_ms)
            
        # Process any pending event batches that have timed out
        self._process_timed_out_batches()
    
    def _handle_camera_panning(self):
        """Handle continuous camera panning from keyboard input."""
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = 1
        if dx != 0 or dy != 0:
            self.game_controller.camera.pan(dx, dy)
    
    def _handle_mouse_wheel(self, event):
        if event.y > 0:
            self.game_controller.camera.zoom(1.1)
        elif event.y < 0:
            self.game_controller.camera.zoom(0.9)
    
    def _handle_key_down(self, event, current_game_state):
        # Handle escape key
        if event.key == pygame.K_ESCAPE:
            self.handle_escape_key(current_game_state)
            return
            
        # Let UI handle input first
        if self.ui_flow_controller.handle_key_input(event.key, current_game_state):
            return
            
        # Handle gameplay input
        is_gameplay_state = current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or (isinstance(current_game_state, str) and current_game_state.startswith("architect_vault"))
        if is_gameplay_state and not self.game_controller.paused:
            self.game_controller.player_actions.handle_key_down(event)
            
        # Handle maze defense specific input
        if current_game_state == GAME_STATE_MAZE_DEFENSE and not self.game_controller.paused:
            if event.key == pygame.K_SPACE and self.combat_controller.wave_manager:
                self.combat_controller.wave_manager.manual_start_next_wave()
                
        # Handle pause toggle
        if event.key == pygame.K_p and (is_gameplay_state or current_game_state == GAME_STATE_MAZE_DEFENSE):
            self.game_controller.toggle_pause()
            
        # Let puzzle controller handle input
        self.puzzle_controller.handle_input(event, current_game_state)
    
    def _handle_mouse_down(self, event, current_game_state):
        # Handle maze defense mode mouse input
        if current_game_state == GAME_STATE_MAZE_DEFENSE and not self.game_controller.paused and self.game_controller.camera:
            screen_pos = event.pos
            
            # Check if clicking on build menu
            if self.game_controller.ui_manager.build_menu and self.game_controller.ui_manager.build_menu.is_mouse_over_build_menu(screen_pos):
                self.game_controller.ui_manager.build_menu.handle_input(event, screen_pos)
                return
                
            # Handle turret placement/upgrade
            world_pos = self.game_controller.camera.screen_to_world(screen_pos)
            if event.button == 1:
                self.combat_controller.try_place_turret(world_pos)
            elif event.button == 3:
                self.combat_controller.try_upgrade_clicked_turret(world_pos)
        # Handle other mouse input
        elif self.game_controller.ui_manager.build_menu:
            self.game_controller.ui_manager.build_menu.handle_input(event, event.pos)

    def register_listener(self, event_type, listener_callback):
        """Register a listener function for a specific event type."""
        self.listeners[event_type].append(listener_callback)
        logger.debug(f"Registered listener {listener_callback.__name__} for event {event_type.__name__}")

    def dispatch(self, event):
        """
        Dispatch an event to all registered listeners and the story manager.
        If the event is batchable, it may be batched with similar events.
        """
        event_type = type(event)

        # Pass the event to the Story Manager for objective tracking.
        if hasattr(self.game_controller, 'story_manager'):
            self.game_controller.story_manager.handle_game_event(event)
        
        # Check if this event type should be batched
        if self.batch_enabled and hasattr(event, 'batchable') and event.batchable:
            should_dispatch = self._add_to_batch(event)
            if not should_dispatch:
                return  # Event was batched, don't dispatch yet
        
        # Dispatch the event to all registered listeners
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event listener {callback.__name__} for event {event_type.__name__}: {e}")
    
    def _add_to_batch(self, event):
        """Add an event to its appropriate batch."""
        event_type = type(event)
        
        # Create a batch for this event type if it doesn't exist
        if event_type not in self.event_batches:
            batch_window = getattr(event, 'batch_window_ms', 50)
            max_batch_size = getattr(event, 'max_batch_size', 100)
            self.event_batches[event_type] = EventBatch(event_type, batch_window, max_batch_size)
        
        # Add the event to its batch
        should_dispatch = self.event_batches[event_type].add(event)
        
        # If the batch is ready to dispatch, do so
        if should_dispatch:
            self._dispatch_batch(event_type)
            return True
        
        return False
    
    def _dispatch_batch(self, event_type):
        """Dispatch a batch of events as a single batched event."""
        batch = self.event_batches[event_type]
        if batch.is_empty():
            return
            
        events = batch.get_events()
        
        # Create a batched event
        try:
            batched_event = event_type.create_batch_event(events)
            
            # Dispatch the batched event
            batched_event_type = type(batched_event)
            if batched_event_type in self.listeners:
                for callback in self.listeners[batched_event_type]:
                    try:
                        callback(batched_event)
                    except Exception as e:
                        logger.error(f"Error in event listener {callback.__name__} for batched event {batched_event_type.__name__}: {e}")
            
            # Also dispatch to listeners of the original event type
            if event_type in self.listeners:
                for callback in self.listeners[event_type]:
                    try:
                        callback(batched_event)
                    except Exception as e:
                        logger.error(f"Error in event listener {callback.__name__} for batched event {event_type.__name__}: {e}")
                        
        except Exception as e:
            logger.error(f"Error creating batched event for {event_type.__name__}: {e}")
            # Fall back to dispatching individual events
            for event in events:
                if event_type in self.listeners:
                    for callback in self.listeners[event_type]:
                        try:
                            callback(event)
                        except Exception as e:
                            logger.error(f"Error in event listener {callback.__name__} for event {event_type.__name__}: {e}")
        
        # Clear the batch
        batch.clear()
    
    def _process_timed_out_batches(self):
        """Process any event batches that have timed out."""
        current_time = time.time() * 1000  # Convert to milliseconds
        
        for event_type, batch in list(self.event_batches.items()):
            if not batch.is_empty() and current_time - batch.last_dispatch_time >= batch.batch_window_ms:
                self._dispatch_batch(event_type)

    def handle_escape_key(self, current_game_state):
        """Handles the logic for when the ESCAPE key is pressed."""
        if current_game_state in [GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, GAME_STATE_CODEX, GAME_STATE_ENTER_NAME]:
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
        
        elif isinstance(current_game_state, str) and current_game_state.startswith("architect_vault"):
            self.game_controller.toggle_pause()
        
        elif current_game_state in [GAME_STATE_RING_PUZZLE]:
            self.puzzle_controller.exit_ring_puzzle(puzzle_was_solved=False)

        elif current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, GAME_STATE_MAZE_DEFENSE]:
            self.game_controller.toggle_pause()
            
    def flush_all_batches(self):
        """Force dispatch of all pending event batches."""
        for event_type in list(self.event_batches.keys()):
            self._dispatch_batch(event_type)
            
    def set_batch_enabled(self, enabled):
        """Enable or disable event batching."""
        if self.batch_enabled != enabled:
            self.batch_enabled = enabled
            
            # If disabling, flush all pending batches
            if not enabled:
                self.flush_all_batches()
