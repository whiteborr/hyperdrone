# hyperdrone_core/game_events.pyAdd commentMore actions
import logging
from .event_batch import BatchedEvent

class GameEvent:
    """A base class for all game events."""
    # By default, events are not batchable
    batchable = False
    pass

class EnemyDefeatedEvent(GameEvent, BatchedEvent):
    """Event triggered when an enemy is defeated."""
    batchable = True
    batch_window_ms = 50  # Batch enemy defeats within 50ms
    max_batch_size = 20   # Or when we reach 20 defeats
    
    def __init__(self, score_value, position, enemy_id):
        self.score_value = score_value
        self.position = position
        self.enemy_id = enemy_id
    
    @classmethod
    def create_batch_event(cls, events):
        """
        Create a batched enemy defeated event.
        
        Args:
            events: List of EnemyDefeatedEvent objects
            
        Returns:
            BatchedEnemyDefeatedEvent: A single event representing multiple enemy defeats
        """
        total_score = sum(event.score_value for event in events)
        positions = [event.position for event in events]
        enemy_ids = [event.enemy_id for event in events]
        
        return BatchedEnemyDefeatedEvent(total_score, positions, enemy_ids)

class BatchedEnemyDefeatedEvent(GameEvent):
    """Event representing multiple enemy defeats batched together."""
    def __init__(self, total_score, positions, enemy_ids):
        self.total_score = total_score
        self.positions = positions
        self.enemy_ids = enemy_ids
        self.count = len(enemy_ids)

class BulletHitEvent(GameEvent, BatchedEvent):
    """Event triggered when a bullet hits something."""
    batchable = True
    batch_window_ms = 30  # Batch bullet hits within 30ms
    max_batch_size = 50   # Or when we reach 50 hits
    
    def __init__(self, bullet_type, position, target_id=None):
        self.bullet_type = bullet_type
        self.position = position
        self.target_id = target_id
    
    @classmethod
    def create_batch_event(cls, events):
        """
        Create a batched bullet hit event.
        
        Args:
            events: List of BulletHitEvent objects
            
        Returns:
            BatchedBulletHitEvent: A single event representing multiple bullet hits
        """
        bullet_types = set(event.bullet_type for event in events)
        positions = [event.position for event in events]
        target_ids = [event.target_id for event in events if event.target_id is not None]
        
        return BatchedBulletHitEvent(bullet_types, positions, target_ids)

class BatchedBulletHitEvent(GameEvent):
    """Event representing multiple bullet hits batched together."""
    def __init__(self, bullet_types, positions, target_ids):
        self.bullet_types = bullet_types
        self.positions = positions
        self.target_ids = target_ids
        self.count = len(positions)

class ParticleEmitEvent(GameEvent, BatchedEvent):
    """Event triggered when particles are emitted."""
    batchable = True
    batch_window_ms = 20  # Batch particle emissions within 20ms
    max_batch_size = 100  # Or when we reach 100 emissions
    
    def __init__(self, particle_type, position, count):
        self.particle_type = particle_type
        self.position = position
        self.count = count
    
    @classmethod
    def create_batch_event(cls, events):
        """
        Create a batched particle emit event.
        
        Args:
            events: List of ParticleEmitEvent objects
            
        Returns:
            BatchedParticleEmitEvent: A single event representing multiple particle emissions
        """
        particle_types = set(event.particle_type for event in events)
        positions_and_counts = [(event.position, event.count) for event in events]
        total_count = sum(event.count for event in events)
        
        return BatchedParticleEmitEvent(particle_types, positions_and_counts, total_count)

class BatchedParticleEmitEvent(GameEvent):
    """Event representing multiple particle emissions batched together."""
    def __init__(self, particle_types, positions_and_counts, total_count):
        self.particle_types = particle_types
        self.positions_and_counts = positions_and_counts
        self.total_count = total_count

class ItemCollectedEvent(GameEvent):
    """Event triggered when a story-relevant item is collected."""
    def __init__(self, item_id, item_type='generic'):
        self.item_id = item_id
        self.item_type = item_type
        logging.info(f"ItemCollectedEvent dispatched: id={item_id}, type={item_type}")

class BossDefeatedEvent(GameEvent):
    """Event triggered when a boss is defeated."""
    def __init__(self, boss_id):
        self.boss_id = boss_id
        logging.info(f"BossDefeatedEvent dispatched: id={boss_id}")
