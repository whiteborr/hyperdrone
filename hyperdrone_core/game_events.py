# hyperdrone_core/game_events.py

class GameEvent:
    """A base class for all game events."""
    pass

class EnemyDefeatedEvent(GameEvent):
    """Event triggered when an enemy is defeated."""
    def __init__(self, score_value, position, enemy_id):
        self.score_value = score_value
        self.position = position
        self.enemy_id = enemy_id