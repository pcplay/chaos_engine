import pygame
import random
import math

_screen_shake = 0.0
_shake_decay = 0.85


def add_shake(amount, max_shake=30):
    global _screen_shake
    _screen_shake = min(_screen_shake + amount, max_shake)


def shake_offset():
    global _screen_shake
    if _screen_shake > 0.5:
        ox = random.uniform(-_screen_shake, _screen_shake)
        oy = random.uniform(-_screen_shake, _screen_shake)
        _screen_shake *= _shake_decay
        return pygame.Vector2(ox, oy)
    _screen_shake = 0
    return pygame.Vector2(0, 0)


def set_shake_decay(decay):
    global _shake_decay
    _shake_decay = decay


class Camera:
    """Handles resolution scaling when window resizes."""

    def __init__(self, logical_width, logical_height, resizable=True):
        self.logical_width = logical_width
        self.logical_height = logical_height
        self.window_width = logical_width
        self.window_height = logical_height
        self.resizable = resizable
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.offset = pygame.Vector2(0, 0)

        flags = pygame.RESIZABLE if resizable else 0
        self.window = pygame.display.set_mode(
            (logical_width, logical_height), flags
        )
        self.render_surface = pygame.Surface((logical_width, logical_height))

    def handle_resize(self, event):
        self.window_width = event.w
        self.window_height = event.h
        self.scale_x = self.window_width / self.logical_width
        self.scale_y = self.window_height / self.logical_height
        self.window = pygame.display.set_mode(
            (self.window_width, self.window_height), pygame.RESIZABLE
        )

    def begin_frame(self):
        self.offset = shake_offset()
        self.render_surface.fill((0, 0, 0))
        return self.render_surface

    def end_frame(self):
        scaled = pygame.transform.smoothscale(
            self.render_surface, (self.window_width, self.window_height)
        )
        self.window.blit(scaled, (0, 0))
        pygame.display.flip()

    def screen_to_logical(self, screen_pos):
        """Convert mouse screen coords to logical coords."""
        return pygame.Vector2(
            screen_pos[0] / self.scale_x,
            screen_pos[1] / self.scale_y
        )


class DamageNumber:
    def __init__(self, x, y, value, color=(255, 255, 255), crit=False):
        self.pos = pygame.Vector2(x + random.randint(-10, 10), y - 10)
        self.vel = pygame.Vector2(random.uniform(-0.5, 0.5), -2.5)
        self.value = value
        self.color = color
        self.life = 60
        self.crit = crit

    def update(self, dt):
        self.pos += self.vel * dt
        self.vel.y += 0.04 * dt
        self.life -= dt

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = min(1.0, self.life / 30)
        size = 20 if not self.crit else 30
        font = pygame.font.SysFont("consolas", size, bold=self.crit)
        text = font.render(str(int(self.value)), True, self.color)
        text.set_alpha(int(alpha * 255))
        surface.blit(text, (int(self.pos.x), int(self.pos.y)))


class Trail:
    def __init__(self, max_length=20):
        self.points = []
        self.max_length = max_length

    def add(self, pos):
        self.points.append(pygame.Vector2(pos))
        if len(self.points) > self.max_length:
            self.points.pop(0)

    def draw(self, surface, color, max_width=6):
        if len(self.points) < 2:
            return
        for i in range(1, len(self.points)):
            alpha = i / len(self.points)
            w = max(1, int(max_width * alpha))
            c = tuple(int(v * alpha) for v in color)
            p1 = (int(self.points[i - 1].x), int(self.points[i - 1].y))
            p2 = (int(self.points[i].x), int(self.points[i].y))
            pygame.draw.line(surface, c, p1, p2, w)

    def clear(self):
        self.points.clear()
