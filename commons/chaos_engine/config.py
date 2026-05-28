import json
import os

DEFAULT_CONFIG = {
    "screen_width": 1200,
    "screen_height": 800,
    "gravity_x": 0,
    "gravity_y": 0.3,
    "gravity_z": 0.005,
    "break_force": 25,
    "chaos_strength": 2,
    "chaos_escalation_rate": 0.01,
    "drag": 0.995,
    "restitution": 0.7,
    "trail_length": 20,
    "particle_count": 12,
    "chain_reaction_radius": 100,
    "chain_reaction_force": 15,
    "attractor_strength": 500,
    "spring_stiffness": 0.02,
    "spring_damping": 0.98,
    "spring_break_distance": 150,
    "time_scale_step": 0.1,
    "screen_shake_intensity": 15,
    "screen_shake_decay": 0.85,
    "max_entities": 1000,
    "max_particles": 3000,
    "fps": 60,
    "explosion_particle_min": 15,
    "explosion_particle_max": 50,
    "resizable": True,
    "min_width": 800,
    "min_height": 600,
}


def load_config(path=None):
    config = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        with open(path, "r") as f:
            user_config = json.load(f)
        config.update(user_config)
    return config
