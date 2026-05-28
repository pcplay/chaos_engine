import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commons.chaos_engine import (
    ChaosEngine, ParticleSystem, ExplosionType,
    PhysicsBody, CollisionSystem, Attractor,
    Camera, add_shake, DamageNumber, Trail,
    Entity, EntityManager,
    ChaosField, ChaosEvent, CHAOS_MODES,
    UIRenderer, AudioEngine, SoundType, load_config,
)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
engine = ChaosEngine("CHAOS ENGINE — Idle Tower Defense", CONFIG_PATH)
