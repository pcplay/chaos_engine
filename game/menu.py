import pygame
import math
import random
from game import engine
from game.constants import *
from game.states import BaseState, GameState
from commons.chaos_engine import ExplosionType, CHAOS_MODES, SoundType


class Button:
    def __init__(self, x, y, width, height, text, color=CYAN, action=None):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = text
        self.color = color
        self.action = action
        self.hovered = False
        self.press_anim = 0

    def update(self, mouse_pos, dt):
        self.hovered = self.rect.collidepoint(mouse_pos.x, mouse_pos.y)
        if self.press_anim > 0:
            self.press_anim -= dt

    def draw(self, surface):
        # Background
        bg = (30, 50, 60) if self.hovered else (20, 30, 35)
        pygame.draw.rect(surface, bg, self.rect)
        # Border
        border_color = WHITE if self.hovered else self.color
        width = 3 if self.hovered else 2
        pygame.draw.rect(surface, border_color, self.rect, width)
        # Text
        engine.ui.text_centered(surface, self.text,
                                self.rect.centerx, self.rect.centery,
                                WHITE if self.hovered else self.color,
                                engine.ui.font_large)

    def click(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos.x, mouse_pos.y):
            self.press_anim = 10
            engine.audio.play(SoundType.UI_CLICK)
            return self.action
        return None


class Slider:
    def __init__(self, x, y, width, label, value=0.7, color=CYAN):
        self.rect = pygame.Rect(x, y, width, 20)
        self.label = label
        self.value = value
        self.color = color
        self.dragging = False

    def handle_event(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(mouse_pos.x, mouse_pos.y):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.value = max(0, min(1, (mouse_pos.x - self.rect.x) / self.rect.width))

    def draw(self, surface):
        # Label
        engine.ui.text(surface, self.label, self.rect.x, self.rect.y - 18, WHITE, engine.ui.font_small)
        # Track
        pygame.draw.rect(surface, DARK_GRAY, self.rect)
        # Fill
        fill_w = int(self.rect.width * self.value)
        pygame.draw.rect(surface, self.color, (self.rect.x, self.rect.y, fill_w, self.rect.height))
        pygame.draw.rect(surface, WHITE, self.rect, 1)
        # Value text
        engine.ui.text(surface, f"{int(self.value * 100)}%",
                       self.rect.right + 10, self.rect.y + 2, WHITE, engine.ui.font_small)


class MenuTitleState(BaseState):
    def __init__(self, state_manager):
        self.sm = state_manager
        self.W = engine.width
        self.H = engine.height
        self.time = 0

        # Buttons
        cx = self.W // 2
        self.buttons = [
            Button(cx, self.H // 2 + 20, 250, 50, "PLAY", CYAN, "play"),
            Button(cx, self.H // 2 + 85, 250, 50, "SETTINGS", GOLD, "settings"),
            Button(cx, self.H // 2 + 150, 250, 50, "CONTROLS", BLUE, "controls"),
            Button(cx, self.H // 2 + 215, 250, 50, "QUIT", RED, "quit"),
        ]

        # Background chaos particles
        self.chaos_field = engine.chaos
        self.chaos_field.active = True
        self.chaos_field.mode = "vortex"
        self.chaos_field.strength = 1.5

    def handle_events(self, events):
        mouse_pos = engine.mouse_logical()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in self.buttons:
                    action = btn.click(mouse_pos)
                    if action == "play":
                        self.chaos_field.active = False
                        return GameState.PLAYING
                    elif action == "settings":
                        return GameState.MENU_SETTINGS
                    elif action == "controls":
                        return GameState.MENU_CONTROLS
                    elif action == "quit":
                        engine.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.chaos_field.active = False
                    return GameState.PLAYING
        return None

    def update(self, dt):
        self.time += dt
        mouse_pos = engine.mouse_logical()
        for btn in self.buttons:
            btn.update(mouse_pos, dt)

        # VFX update
        engine.vfx.update(dt)
        # Periodic pulse rings for atmosphere
        if random.random() < 0.02:
            rx = random.randint(100, self.W - 100)
            ry = random.randint(100, self.H - 100)
            color = random.choice([CYAN, MAGENTA, PURPLE])
            engine.vfx.ring(rx, ry, color, random.randint(50, 150))

        # Emit background particles
        if random.random() < 0.3:
            x = random.randint(0, self.W)
            y = random.randint(0, self.H)
            color = random.choice([CYAN, MAGENTA, PURPLE, BLUE, TEAL])
            engine.particles.emit(x, y, color, 1, speed=1, radius=random.uniform(2, 4),
                                  decay=0.008, drag=0.99)

        engine.particles.update(dt)

    def draw(self, surface):
        surface.fill(BG_COLOR)

        # VFX background (grid + ambient)
        engine.vfx.draw_background(surface)
        engine.particles.draw(surface)
        engine.vfx.draw_foreground(surface)

        # Title
        title_y = self.H // 4
        bob = math.sin(self.time * 0.03) * 5
        engine.ui.text_centered(surface, "CHAOS ENGINE", self.W // 2, title_y + bob,
                                CYAN, engine.ui.font_huge)
        # Subtitle
        engine.ui.text_centered(surface, "IDLE TOWER DEFENSE", self.W // 2, title_y + 45 + bob,
                                (100, 150, 150), engine.ui.font_med)

        # Version
        engine.ui.text(surface, "v2.0", 10, self.H - 20, (60, 60, 60), engine.ui.font_small)

        # Buttons
        for btn in self.buttons:
            btn.draw(surface)


class MenuSettingsState(BaseState):
    def __init__(self, state_manager):
        self.sm = state_manager
        self.W = engine.width
        self.H = engine.height

        cx = self.W // 2
        sx = cx - 100
        self.sliders = [
            Slider(sx, self.H // 3, 200, "Master Volume", engine.audio.master_volume, CYAN),
            Slider(sx, self.H // 3 + 60, 200, "SFX Volume", engine.audio.sfx_volume, GREEN),
            Slider(sx, self.H // 3 + 120, 200, "Music Volume", engine.audio.music_volume, GOLD),
        ]
        self.difficulty = 1  # 0=easy, 1=normal, 2=hard
        self.diff_names = ["EASY", "NORMAL", "HARD"]
        self.diff_colors = [GREEN, YELLOW, RED]

    def handle_events(self, events):
        mouse_pos = engine.mouse_logical()
        for event in events:
            for slider in self.sliders:
                slider.handle_event(event, mouse_pos)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._apply()
                    return GameState.MENU_TITLE
                if event.key == pygame.K_LEFT:
                    self.difficulty = max(0, self.difficulty - 1)
                if event.key == pygame.K_RIGHT:
                    self.difficulty = min(2, self.difficulty + 1)
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Difficulty buttons
                diff_y = self.H // 3 + 200
                for i in range(3):
                    bx = self.W // 2 - 120 + i * 100
                    if pygame.Rect(bx, diff_y, 80, 30).collidepoint(mouse_pos.x, mouse_pos.y):
                        self.difficulty = i
                        engine.audio.play(SoundType.UI_CLICK)
        return None

    def _apply(self):
        engine.audio.set_master_volume(self.sliders[0].value)
        engine.audio.set_sfx_volume(self.sliders[1].value)
        engine.audio.set_music_volume(self.sliders[2].value)

    def update(self, dt):
        self._apply()

    def draw(self, surface):
        surface.fill(BG_COLOR)
        engine.ui.text_centered(surface, "SETTINGS", self.W // 2, 50, WHITE, engine.ui.font_title)

        for slider in self.sliders:
            slider.draw(surface)

        # Difficulty
        diff_y = self.H // 3 + 200
        engine.ui.text(surface, "Difficulty:", self.W // 2 - 120, diff_y - 20, WHITE, engine.ui.font_med)
        for i in range(3):
            bx = self.W // 2 - 120 + i * 100
            selected = i == self.difficulty
            color = self.diff_colors[i]
            pygame.draw.rect(surface, color if selected else DARK_GRAY, (bx, diff_y, 80, 30), 0 if selected else 2)
            engine.ui.text_centered(surface, self.diff_names[i], bx + 40, diff_y + 15,
                                    WHITE if selected else color, engine.ui.font_small)

        engine.ui.text_centered(surface, "ESC to go back", self.W // 2, self.H - 40,
                                (80, 80, 80), engine.ui.font_small)


class MenuControlsState(BaseState):
    def __init__(self, state_manager):
        self.sm = state_manager
        self.W = engine.width
        self.H = engine.height

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return GameState.MENU_TITLE
        return None

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(BG_COLOR)
        engine.ui.text_centered(surface, "CONTROLS", self.W // 2, 40, WHITE, engine.ui.font_title)

        controls = [
            ("WASD / Arrows", "Move hero"),
            ("Right Click", "Manual attack (2.5x damage)"),
            ("Q", "Whirlwind (AOE slash)"),
            ("T", "Rally (buff tower fire rate)"),
            ("E", "Execute (% HP finisher)"),
            ("F", "Chaos Overload (massive AOE)"),
            ("1-9, 0", "Select tower to place"),
            ("Left Click", "Place / Select tower"),
            ("U", "Upgrade tower"),
            ("X", "Sell tower"),
            ("SPACE", "Start next wave"),
            ("TAB", "Skill tree"),
            ("M", "Mute/Unmute"),
            ("R", "Restart (game over)"),
            ("ESC", "Cancel / Back"),
        ]

        y = 90
        for key, action in controls:
            engine.ui.text(surface, key, self.W // 2 - 180, y, CYAN, engine.ui.font_med)
            engine.ui.text(surface, action, self.W // 2 + 20, y, WHITE, engine.ui.font_med)
            y += 28

        engine.ui.text_centered(surface, "ESC to go back", self.W // 2, self.H - 40,
                                (80, 80, 80), engine.ui.font_small)
