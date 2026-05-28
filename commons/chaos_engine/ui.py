import pygame


class UIRenderer:
    """Basic UI helpers for HUD rendering."""

    def __init__(self):
        pygame.font.init()
        self.font_small = pygame.font.SysFont("consolas", 12)
        self.font_med = pygame.font.SysFont("consolas", 16)
        self.font_large = pygame.font.SysFont("consolas", 24)
        self.font_title = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_huge = pygame.font.SysFont("consolas", 48, bold=True)

    def text(self, surface, text, x, y, color=(255, 255, 255), font=None):
        f = font or self.font_med
        rendered = f.render(text, True, color)
        surface.blit(rendered, (x, y))
        return rendered.get_width(), rendered.get_height()

    def text_centered(self, surface, text, cx, cy, color=(255, 255, 255), font=None):
        f = font or self.font_large
        rendered = f.render(text, True, color)
        x = cx - rendered.get_width() // 2
        y = cy - rendered.get_height() // 2
        surface.blit(rendered, (x, y))

    def progress_bar(self, surface, x, y, width, height, fill, color,
                     bg_color=(40, 40, 50), border_color=(100, 100, 100)):
        pygame.draw.rect(surface, bg_color, (x, y, width, height))
        fill_w = int(width * max(0, min(1, fill)))
        if fill_w > 0:
            pygame.draw.rect(surface, color, (x, y, fill_w, height))
        pygame.draw.rect(surface, border_color, (x, y, width, height), 1)

    def cooldown_icon(self, surface, x, y, size, fill, color, label="",
                      bg_color=(30, 30, 40)):
        pygame.draw.rect(surface, bg_color, (x, y, size, size))
        if fill < 1.0:
            # Cooldown sweep
            h = int(size * (1 - fill))
            pygame.draw.rect(surface, (20, 20, 25), (x, y, size, h))
        pygame.draw.rect(surface, color if fill >= 1.0 else (60, 60, 70), (x, y, size, size), 2)
        if label:
            self.text(surface, label, x + 3, y + size - 14,
                      color if fill >= 1.0 else (80, 80, 80), self.font_small)

    def overlay(self, surface, alpha=180):
        overlay = pygame.Surface(surface.get_size())
        overlay.fill((0, 0, 0))
        overlay.set_alpha(alpha)
        surface.blit(overlay, (0, 0))
