import pygame
import random

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600)) 
pygame.display.set_caption("Chaos Gravity Demo")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
RED = (255, 80, 80)
BG_COLOR = (30, 30, 30)

# === Entity class ===
class Entity:
    def __init__(self, x, y):
        self.pos = pygame.Vector3(x, y, random.uniform(0.5, 1.5))
        self.vel = pygame.Vector3(random.uniform(-1, 1), random.uniform(-1, 1), 0)
        self.radius = 20
        self.break_force = 20 
        self.broken = False

    def update(self, gravity, chaos):
        if not self.broken:
            self.vel += gravity
            self.pos += self.vel

            if chaos:
                self.vel += pygame.Vector3(
                    random.randint(-2, 2),
                    random.randint(-2, 2),
                    0
                )

            if self.vel.length() > self.break_force:
                self.broken = True

    def draw(self, surface):
        scale = max(0.1, 1 / self.pos.z)
        draw_x = int(self.pos.x)
        draw_y = int(self.pos.y)
        scaled_radius = int(self.radius * scale)
        color = RED if self.broken else WHITE
        pygame.draw.circle(surface, color, (draw_x, draw_y), scaled_radius)

# === Helper functions ===
entities = []

def spawn_entities(n=5):
    for _ in range(n):
        entities.append(Entity(random.randint(100, 700), random.randint(100, 500)))

def reset_game():
    entities.clear()
    spawn_entities(25)

# Create initial entities
spawn_entities(25)

# === Main loop variables ===
running = True
chaos_mode = False
time_paused = False
gravity = pygame.Vector3(0, 0.2, 0.005)

# === Main loop ===
while running:
    screen.fill(BG_COLOR)
    
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                chaos_mode = not chaos_mode
            elif event.key == pygame.K_r:
                reset_game()
            elif event.key == pygame.K_n:
                spawn_entities(5)
            elif event.key == pygame.K_t:
                time_paused = not time_paused

    # Update and draw entities
    if not time_paused:
        for e in entities:
            e.update(gravity, chaos_mode)

    for e in entities:
        e.draw(screen)

    # Info
    font = pygame.font.SysFont(None, 24)
    text = font.render(
        f"Chaos: {'ON' if chaos_mode else 'OFF'} | Time: {'Paused' if time_paused else 'Running'} | R: Reset | N: New | T: Time | SPACE: Chaos",
        True, WHITE
    )
    screen.blit(text, (10, 10))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

