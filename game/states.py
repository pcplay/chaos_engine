from enum import Enum


class GameState(Enum):
    MENU_TITLE = "menu_title"
    MENU_SETTINGS = "menu_settings"
    MENU_CONTROLS = "menu_controls"
    PLAYING = "playing"
    SKILL_TREE = "skill_tree"
    PAUSED = "paused"
    GAME_OVER = "game_over"


class StateManager:
    """Stack-based state manager. Top state gets events, all get drawn."""

    def __init__(self):
        self.stack = []

    def push(self, state):
        self.stack.append(state)

    def pop(self):
        if self.stack:
            return self.stack.pop()

    def replace(self, state):
        if self.stack:
            self.stack.pop()
        self.stack.append(state)

    @property
    def current(self):
        return self.stack[-1] if self.stack else None

    def handle_events(self, events):
        if self.current:
            return self.current.handle_events(events)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def draw(self, surface):
        for state in self.stack:
            state.draw(surface)


class BaseState:
    """Base class for game states."""

    def handle_events(self, events):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass
