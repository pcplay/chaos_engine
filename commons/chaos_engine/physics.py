import pygame
import random
import math


class PhysicsBody:
    def __init__(self, x, y, mass=1.0, radius=10):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.acc = pygame.Vector2(0, 0)
        self.mass = mass
        self.radius = radius
        self.drag = 0.995
        self.restitution = 0.7
        self.static = False

    def apply_force(self, force):
        if not self.static:
            self.acc += force / self.mass

    def apply_impulse(self, impulse):
        if not self.static:
            self.vel += impulse / self.mass

    def update(self, dt):
        if self.static:
            return
        self.vel += self.acc * dt
        self.vel *= self.drag
        self.pos += self.vel * dt
        self.acc = pygame.Vector2(0, 0)

    @property
    def speed(self):
        return self.vel.length()

    @property
    def kinetic_energy(self):
        return 0.5 * self.mass * self.vel.length_squared()


class CollisionSystem:
    def __init__(self, restitution=0.7):
        self.restitution = restitution

    def resolve(self, bodies, dt):
        for i in range(len(bodies)):
            if bodies[i].static:
                continue
            for j in range(i + 1, len(bodies)):
                self._check_pair(bodies[i], bodies[j])

    def _check_pair(self, a, b):
        diff = b.pos - a.pos
        dist = diff.length()
        min_dist = a.radius + b.radius

        if dist < min_dist and dist > 0.001:
            normal = diff / dist
            overlap = min_dist - dist

            if b.static:
                a.pos -= normal * overlap
            elif a.static:
                b.pos += normal * overlap
            else:
                total_mass = a.mass + b.mass
                a.pos -= normal * (overlap * b.mass / total_mass)
                b.pos += normal * (overlap * a.mass / total_mass)

            rel_vel = a.vel - b.vel
            vel_along = rel_vel.dot(normal)

            if vel_along > 0:
                if b.static:
                    a.vel -= normal * vel_along * (1 + self.restitution)
                elif a.static:
                    b.vel += normal * vel_along * (1 + self.restitution)
                else:
                    impulse = (1 + self.restitution) * vel_along / total_mass
                    a.vel -= normal * impulse * b.mass
                    b.vel += normal * impulse * a.mass

            return True
        return False

    def check_bounds(self, body, width, height, bounce=True):
        hit = False
        if body.pos.x - body.radius < 0:
            body.pos.x = body.radius
            if bounce:
                body.vel.x = abs(body.vel.x) * self.restitution
            hit = True
        elif body.pos.x + body.radius > width:
            body.pos.x = width - body.radius
            if bounce:
                body.vel.x = -abs(body.vel.x) * self.restitution
            hit = True
        if body.pos.y - body.radius < 0:
            body.pos.y = body.radius
            if bounce:
                body.vel.y = abs(body.vel.y) * self.restitution
            hit = True
        elif body.pos.y + body.radius > height:
            body.pos.y = height - body.radius
            if bounce:
                body.vel.y = -abs(body.vel.y) * self.restitution
            hit = True
        return hit


class Spring:
    def __init__(self, body_a, body_b, stiffness=0.02, damping=0.98, break_distance=150):
        self.a = body_a
        self.b = body_b
        self.rest_length = (body_a.pos - body_b.pos).length()
        self.stiffness = stiffness
        self.damping = damping
        self.break_distance = break_distance
        self.broken = False
        self.strain = 0

    def update(self, dt):
        if self.broken:
            return
        diff = self.b.pos - self.a.pos
        dist = diff.length()
        if dist < 0.001:
            return

        self.strain = dist / self.break_distance
        if dist > self.break_distance:
            self.broken = True
            return

        direction = diff / dist
        displacement = dist - self.rest_length
        force = direction * displacement * self.stiffness * dt

        self.a.apply_force(force)
        self.b.apply_force(-force)

    def draw(self, surface, color_ok=(100, 200, 100), color_break=(255, 50, 50)):
        if self.broken:
            return
        p1 = (int(self.a.pos.x), int(self.a.pos.y))
        p2 = (int(self.b.pos.x), int(self.b.pos.y))
        t = min(1, self.strain)
        color = tuple(int(a + (b - a) * t) for a, b in zip(color_ok, color_break))
        pygame.draw.line(surface, color, p1, p2, 2)


class Attractor:
    def __init__(self, x, y, strength=500, repulse=False, radius=15):
        self.pos = pygame.Vector2(x, y)
        self.strength = strength
        self.repulse = repulse
        self.radius = radius

    def apply_to(self, body, dt):
        if body.static:
            return
        diff = self.pos - body.pos
        dist_sq = diff.length_squared()
        if dist_sq < 100:
            dist_sq = 100
        dist = math.sqrt(dist_sq)
        direction = diff / dist
        force_mag = self.strength / dist_sq * 60 * dt
        if self.repulse:
            force_mag = -force_mag
        body.apply_force(direction * force_mag)

    def draw(self, surface):
        pos = (int(self.pos.x), int(self.pos.y))
        color = (50, 150, 255) if not self.repulse else (255, 100, 50)
        pygame.draw.circle(surface, color, pos, self.radius, 3)
        pygame.draw.circle(surface, color, pos, self.radius // 2)
        pulse = math.sin(pygame.time.get_ticks() * 0.005) * 4
        pygame.draw.circle(surface, color, pos, int(self.radius + 5 + pulse), 1)
