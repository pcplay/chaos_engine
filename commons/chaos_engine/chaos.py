import pygame
import random
import math

CHAOS_MODES = ["random", "vortex", "explosion", "reverse", "orbital", "spiral", "pulse", "earthquake"]


class ChaosEvent:
    def __init__(self, name, duration=300, intensity=1.0):
        self.name = name
        self.duration = duration
        self.remaining = duration
        self.intensity = intensity
        self.active = True

    def update(self, dt):
        self.remaining -= dt
        if self.remaining <= 0:
            self.active = False

    @property
    def progress(self):
        return 1.0 - (self.remaining / self.duration)


class ChaosField:
    """Applies chaos forces to entities based on active mode."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.center = pygame.Vector2(width // 2, height // 2)
        self.mode = "random"
        self.strength = 2.0
        self.escalation = 0.0
        self.escalation_rate = 0.01
        self.active = False
        self.time = 0

    def set_mode(self, mode):
        if mode in CHAOS_MODES:
            self.mode = mode

    def cycle_mode(self):
        idx = CHAOS_MODES.index(self.mode)
        self.mode = CHAOS_MODES[(idx + 1) % len(CHAOS_MODES)]

    def toggle(self):
        self.active = not self.active
        if not self.active:
            self.escalation = 0

    def update(self, dt):
        if self.active:
            self.time += dt
            self.escalation += self.escalation_rate * dt

    def apply_to(self, body, dt):
        if not self.active or body.static:
            return

        s = (self.strength + self.escalation) * dt
        pos = body.pos

        if self.mode == "random":
            force = pygame.Vector2(random.uniform(-s, s), random.uniform(-s, s))
            body.apply_force(force)

        elif self.mode == "vortex":
            diff = self.center - pos
            dist = diff.length()
            if dist > 1:
                tangent = pygame.Vector2(-diff.y, diff.x).normalize()
                body.apply_force(tangent * s * 0.8)
                body.apply_force(diff.normalize() * s * 0.2)

        elif self.mode == "explosion":
            diff = pos - self.center
            dist = diff.length()
            if dist > 1:
                force = diff.normalize() * s * 3 / max(dist * 0.01, 0.5)
                body.apply_force(force)

        elif self.mode == "reverse":
            body.apply_force(pygame.Vector2(0, -s * 2))
            body.apply_force(pygame.Vector2(random.uniform(-s, s), 0))

        elif self.mode == "orbital":
            diff = self.center - pos
            dist = diff.length()
            if dist > 1:
                tangent = pygame.Vector2(-diff.y, diff.x).normalize()
                body.apply_force(tangent * s * 1.2)

        elif self.mode == "spiral":
            angle = math.atan2(pos.y - self.center.y, pos.x - self.center.x)
            angle += 0.05 * dt
            dist = (pos - self.center).length()
            target = self.center + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist * 0.99
            diff = target - pos
            body.apply_force(diff * s * 0.1)

        elif self.mode == "pulse":
            phase = math.sin(self.time * 0.05)
            diff = pos - self.center
            if diff.length() > 1:
                body.apply_force(diff.normalize() * s * phase * 3)

        elif self.mode == "earthquake":
            body.apply_force(pygame.Vector2(
                random.uniform(-s * 3, s * 3),
                random.uniform(-s, s * 0.5)
            ))
