import pygame
import random
import math
from enum import Enum


class ExplosionType(Enum):
    BURST = "burst"
    RING = "ring"
    DIRECTIONAL = "directional"
    FIREWORK = "firework"
    SHOCKWAVE = "shockwave"
    NOVA = "nova"
    SPARKS = "sparks"
    CONFETTI = "confetti"


class Particle:
    __slots__ = ['x', 'y', 'vx', 'vy', 'life', 'decay', 'color', 'radius',
                 'gravity', 'drag', 'glow', 'fade_color']

    def __init__(self, x, y, vx, vy, color, radius=3, life=1.0,
                 decay=0.03, gravity=0, drag=0.95, glow=False, fade_color=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.decay = decay
        self.color = color
        self.radius = radius
        self.gravity = gravity
        self.drag = drag
        self.glow = glow
        self.fade_color = fade_color or (0, 0, 0)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= self.drag
        self.vy *= self.drag
        self.vy += self.gravity * dt
        self.life -= self.decay * dt
        self.radius *= 0.98

    def draw(self, surface):
        if self.life <= 0 or self.radius < 0.3:
            return
        alpha = max(0, min(1, self.life))
        r = int(self.color[0] * alpha)
        g = int(self.color[1] * alpha)
        b = int(self.color[2] * alpha)
        pos = (int(self.x), int(self.y))
        rad = max(1, int(self.radius))

        if self.glow and rad > 2:
            # Outer glow
            glow_color = (r // 3, g // 3, b // 3)
            pygame.draw.circle(surface, glow_color, pos, rad + 3)

        pygame.draw.circle(surface, (r, g, b), pos, rad)


class ParticleSystem:
    def __init__(self, max_particles=3000):
        self.particles = []
        self.max_particles = max_particles

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles[:] = [p for p in self.particles if p.life > 0 and p.radius > 0.2]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    @property
    def count(self):
        return len(self.particles)

    def emit(self, x, y, color, count=10, speed=5, spread=math.pi * 2,
             angle=0, radius=3, life=1.0, decay=0.03, gravity=0,
             drag=0.95, glow=False, fade_color=None):
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break
            a = angle + random.uniform(-spread / 2, spread / 2)
            s = speed * random.uniform(0.5, 1.5)
            vx = math.cos(a) * s
            vy = math.sin(a) * s
            r = radius * random.uniform(0.6, 1.4)
            d = decay * random.uniform(0.8, 1.2)
            self.particles.append(Particle(
                x + random.uniform(-3, 3), y + random.uniform(-3, 3),
                vx, vy, color, r, life, d, gravity, drag, glow, fade_color
            ))

    def explode(self, x, y, color, explosion_type=ExplosionType.BURST,
                intensity=1.0, count=None):
        base_count = count or int(20 * intensity)

        if explosion_type == ExplosionType.BURST:
            self.emit(x, y, color, base_count, speed=8 * intensity,
                      radius=4 * intensity, glow=True, gravity=0.05)

        elif explosion_type == ExplosionType.RING:
            for i in range(base_count):
                angle = (2 * math.pi * i) / base_count
                self.emit(x, y, color, 1, speed=6 * intensity,
                          angle=angle, spread=0.1, radius=3, glow=True)

        elif explosion_type == ExplosionType.DIRECTIONAL:
            self.emit(x, y, color, base_count, speed=10 * intensity,
                      spread=math.pi * 0.5, radius=3, gravity=0.1)

        elif explosion_type == ExplosionType.FIREWORK:
            # Initial burst
            self.emit(x, y, color, base_count // 2, speed=5 * intensity,
                      radius=4, glow=True)
            # Secondary sparks
            colors = [
                (255, 200, 50), (255, 100, 50), (255, 50, 200),
                (50, 200, 255), (50, 255, 100)
            ]
            for _ in range(base_count // 2):
                c = random.choice(colors)
                self.emit(x, y, c, 1, speed=8 * intensity,
                          radius=2, decay=0.04, glow=True)

        elif explosion_type == ExplosionType.SHOCKWAVE:
            # Dense ring that expands fast
            for i in range(base_count * 2):
                angle = (2 * math.pi * i) / (base_count * 2)
                self.emit(x, y, color, 1, speed=12 * intensity,
                          angle=angle, spread=0.05, radius=2,
                          decay=0.06, drag=0.92)

        elif explosion_type == ExplosionType.NOVA:
            # Multiple rings at different speeds
            for ring in range(3):
                speed = (4 + ring * 4) * intensity
                for i in range(base_count):
                    angle = (2 * math.pi * i) / base_count + ring * 0.3
                    self.emit(x, y, color, 1, speed=speed,
                              angle=angle, spread=0.1, radius=3 - ring,
                              glow=True, decay=0.03 + ring * 0.01)

        elif explosion_type == ExplosionType.SPARKS:
            self.emit(x, y, color, base_count, speed=10 * intensity,
                      radius=2, decay=0.02, gravity=0.15, drag=0.97)
            # Extra bright core
            self.emit(x, y, (255, 255, 255), base_count // 4,
                      speed=3, radius=4, decay=0.05, glow=True)

        elif explosion_type == ExplosionType.CONFETTI:
            colors = [
                (255, 50, 50), (50, 255, 50), (50, 50, 255),
                (255, 255, 50), (255, 50, 255), (50, 255, 255)
            ]
            for _ in range(base_count):
                c = random.choice(colors)
                self.emit(x, y, c, 1, speed=6 * intensity,
                          radius=random.uniform(2, 5), gravity=0.08,
                          decay=0.015, drag=0.97)

    def chain_explosion(self, x, y, color, radius=100, count=5, intensity=1.0):
        """Multiple explosions in a radius — chain reaction."""
        self.explode(x, y, color, ExplosionType.NOVA, intensity)
        for _ in range(count - 1):
            ox = x + random.uniform(-radius, radius)
            oy = y + random.uniform(-radius, radius)
            etype = random.choice(list(ExplosionType))
            self.explode(ox, oy, color, etype, intensity * 0.7)

    def continuous_emit(self, x, y, color, rate=2, speed=3, radius=2,
                        spread=math.pi * 2, gravity=0):
        """Call every frame for continuous particle emission."""
        for _ in range(rate):
            if len(self.particles) < self.max_particles:
                self.emit(x, y, color, 1, speed=speed, radius=radius,
                          spread=spread, gravity=gravity, decay=0.04)
