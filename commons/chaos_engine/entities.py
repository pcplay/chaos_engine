import pygame
import random
from commons.chaos_engine.physics import PhysicsBody
from commons.chaos_engine.rendering import Trail


class Entity:
    _next_id = 0

    def __init__(self, x, y, radius=12, mass=1.0):
        self.id = Entity._next_id
        Entity._next_id += 1
        self.body = PhysicsBody(x, y, mass, radius)
        self.trail = Trail(max_length=20)
        self.alive = True
        self.age = 0
        self.tags = set()
        self.data = {}

    @property
    def pos(self):
        return self.body.pos

    @pos.setter
    def pos(self, value):
        self.body.pos = pygame.Vector2(value)

    @property
    def vel(self):
        return self.body.vel

    @vel.setter
    def vel(self, value):
        self.body.vel = pygame.Vector2(value)

    @property
    def radius(self):
        return self.body.radius

    def update(self, dt):
        if not self.alive:
            return
        self.body.update(dt)
        self.trail.add(self.body.pos)
        self.age += dt

    def kill(self):
        self.alive = False


class EntityManager:
    def __init__(self, max_entities=1000):
        self.entities = []
        self.max_entities = max_entities

    def add(self, entity):
        if len(self.entities) < self.max_entities:
            self.entities.append(entity)
            return entity
        return None

    def remove(self, entity):
        if entity in self.entities:
            self.entities.remove(entity)

    def update(self, dt):
        for e in self.entities:
            e.update(dt)
        self.entities[:] = [e for e in self.entities if e.alive]

    def get_by_tag(self, tag):
        return [e for e in self.entities if tag in e.tags]

    def get_in_radius(self, pos, radius):
        results = []
        r_sq = radius * radius
        for e in self.entities:
            if e.alive and (e.pos - pos).length_squared() < r_sq:
                results.append(e)
        return results

    @property
    def count(self):
        return len(self.entities)

    def clear(self):
        self.entities.clear()
