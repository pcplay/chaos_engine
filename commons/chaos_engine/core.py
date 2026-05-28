import pygame
from commons.chaos_engine.config import load_config
from commons.chaos_engine.rendering import Camera, add_shake
from commons.chaos_engine.particles import ParticleSystem
from commons.chaos_engine.physics import CollisionSystem
from commons.chaos_engine.entities import EntityManager
from commons.chaos_engine.chaos import ChaosField
from commons.chaos_engine.ui import UIRenderer


class ChaosEngine:
    """Core engine — ties all systems together."""

    def __init__(self, title="Chaos Engine", config_path=None):
        pygame.init()
        self.config = load_config(config_path)
        self.width = self.config["screen_width"]
        self.height = self.config["screen_height"]

        pygame.display.set_caption(title)
        self.camera = Camera(self.width, self.height, self.config.get("resizable", True))
        self.clock = pygame.time.Clock()
        self.fps = self.config["fps"]

        # Systems
        self.particles = ParticleSystem(self.config.get("max_particles", 3000))
        self.collision = CollisionSystem(self.config.get("restitution", 0.7))
        self.entities = EntityManager(self.config.get("max_entities", 1000))
        self.chaos = ChaosField(self.width, self.height)
        self.ui = UIRenderer()

        # State
        self.running = True
        self.dt = 1.0
        self.time_scale = 1.0
        self.paused = False
        self.frame_count = 0

    @property
    def surface(self):
        return self.camera.render_surface

    def process_events(self):
        """Process events, return list for game to handle."""
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.camera.handle_resize(event)
        return events

    def begin_frame(self):
        self.frame_count += 1
        self.dt = self.time_scale if not self.paused else 0
        return self.camera.begin_frame()

    def end_frame(self):
        self.camera.end_frame()
        self.clock.tick(self.fps)

    def update_systems(self):
        """Update all engine systems."""
        if self.paused:
            return
        self.entities.update(self.dt)
        self.chaos.update(self.dt)

        # Apply chaos to all entities
        if self.chaos.active:
            for e in self.entities.entities:
                self.chaos.apply_to(e.body, self.dt)

        self.particles.update(self.dt)

    def mouse_logical(self):
        """Get mouse position in logical coordinates."""
        return self.camera.screen_to_logical(pygame.mouse.get_pos())

    def quit(self):
        pygame.quit()
