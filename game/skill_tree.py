import pygame
import math
from game import engine
from game.constants import *
from game.states import BaseState, GameState
from commons.chaos_engine import SoundType, ExplosionType

# Skill node definitions — web/grid layout
# pos is grid (col, row), adjacent links by name
SKILL_NODES = {
    # === ROOT (free) ===
    "root": {
        "name": "Awakening",
        "branch": "ROOT",
        "pos": (4, 3),
        "adjacent": ["atk_1", "def_1", "chaos_1"],
        "effect": None,
        "desc": "Starting node",
    },
    # === ATK BRANCH ===
    "atk_1": {
        "name": "+20% Damage",
        "branch": "ATK",
        "pos": (3, 2),
        "adjacent": ["root", "atk_2", "atk_3"],
        "effect": ("attack_damage_mult", 0.2),
        "desc": "Hero attacks hit harder",
    },
    "atk_2": {
        "name": "+25% Attack Speed",
        "branch": "ATK",
        "pos": (2, 1),
        "adjacent": ["atk_1", "atk_4", "atk_crit"],
        "effect": ("attack_speed_mult", 0.25),
        "desc": "Hero attacks faster",
    },
    "atk_3": {
        "name": "+15% Range",
        "branch": "ATK",
        "pos": (4, 1),
        "adjacent": ["atk_1", "atk_crit", "tower_dmg"],
        "effect": ("attack_range_mult", 0.15),
        "desc": "Hero range extends",
    },
    "atk_4": {
        "name": "+30% Damage",
        "branch": "ATK",
        "pos": (1, 0),
        "adjacent": ["atk_2", "atk_5"],
        "effect": ("attack_damage_mult", 0.3),
        "desc": "Even more damage",
    },
    "atk_5": {
        "name": "Double Strike",
        "branch": "ATK",
        "pos": (0, 0),
        "adjacent": ["atk_4"],
        "effect": ("double_strike", 0.25),
        "desc": "25% chance to hit twice",
    },
    "atk_crit": {
        "name": "+15% Crit Chance",
        "branch": "ATK",
        "pos": (3, 0),
        "adjacent": ["atk_2", "atk_3"],
        "effect": ("crit_chance", 0.15),
        "desc": "More critical hits",
    },
    "tower_dmg": {
        "name": "Tower +20% DMG",
        "branch": "ATK",
        "pos": (5, 0),
        "adjacent": ["atk_3"],
        "effect": ("tower_damage_mult", 0.2),
        "desc": "All towers deal more damage",
    },
    # === DEF BRANCH ===
    "def_1": {
        "name": "+1 Base HP",
        "branch": "DEF",
        "pos": (5, 4),
        "adjacent": ["root", "def_2", "def_3"],
        "effect": ("base_hp", 1),
        "desc": "Base can take one more hit",
    },
    "def_2": {
        "name": "+20% Move Speed",
        "branch": "DEF",
        "pos": (6, 5),
        "adjacent": ["def_1", "def_4"],
        "effect": ("move_speed_mult", 0.2),
        "desc": "Hero moves faster",
    },
    "def_3": {
        "name": "+2 Base HP",
        "branch": "DEF",
        "pos": (5, 5),
        "adjacent": ["def_1", "def_5", "gold_int"],
        "effect": ("base_hp", 2),
        "desc": "Base even tankier",
    },
    "def_4": {
        "name": "+30% Move Speed",
        "branch": "DEF",
        "pos": (7, 6),
        "adjacent": ["def_2"],
        "effect": ("move_speed_mult", 0.3),
        "desc": "Zoom around",
    },
    "def_5": {
        "name": "+5 Base HP",
        "branch": "DEF",
        "pos": (5, 6),
        "adjacent": ["def_3"],
        "effect": ("base_hp", 5),
        "desc": "Fortress mode",
    },
    "gold_int": {
        "name": "+3% Interest",
        "branch": "DEF",
        "pos": (4, 5),
        "adjacent": ["def_3", "chaos_2"],
        "effect": ("gold_interest", 0.03),
        "desc": "More passive gold",
    },
    # === CHAOS BRANCH ===
    "chaos_1": {
        "name": "-15% Ability CD",
        "branch": "CHAOS",
        "pos": (3, 4),
        "adjacent": ["root", "chaos_2", "chaos_3"],
        "effect": ("ability_cd_mult", -0.15),
        "desc": "Abilities come back faster",
    },
    "chaos_2": {
        "name": "-20% Ability CD",
        "branch": "CHAOS",
        "pos": (2, 5),
        "adjacent": ["chaos_1", "chaos_4", "gold_int"],
        "effect": ("ability_cd_mult", -0.2),
        "desc": "Even faster cooldowns",
    },
    "chaos_3": {
        "name": "+30% Ability DMG",
        "branch": "CHAOS",
        "pos": (3, 5),
        "adjacent": ["chaos_1", "chaos_5"],
        "effect": ("ability_damage_mult", 0.3),
        "desc": "Abilities hit harder",
    },
    "chaos_4": {
        "name": "Chaos Aura",
        "branch": "CHAOS",
        "pos": (1, 6),
        "adjacent": ["chaos_2"],
        "effect": ("chaos_aura", 1),
        "desc": "Enemies near hero take DOT",
    },
    "chaos_5": {
        "name": "+50% Ability DMG",
        "branch": "CHAOS",
        "pos": (3, 6),
        "adjacent": ["chaos_3"],
        "effect": ("ability_damage_mult", 0.5),
        "desc": "Devastating abilities",
    },
}

BRANCH_COLORS = {
    "ROOT": WHITE,
    "ATK": RED,
    "DEF": GREEN,
    "CHAOS": MAGENTA,
}


class SkillTree:
    """Skill tree data + logic."""

    def __init__(self):
        self.owned = {"root"}
        self.points = 0

    def can_unlock(self, node_id):
        if node_id in self.owned:
            return False
        if self.points <= 0:
            return False
        node = SKILL_NODES.get(node_id)
        if not node:
            return False
        # Must have at least one adjacent node owned
        return any(adj in self.owned for adj in node["adjacent"])

    def unlock(self, node_id):
        if not self.can_unlock(node_id):
            return False
        self.owned.add(node_id)
        self.points -= 1
        return True

    def get_modifiers(self):
        """Collect all active skill effects into a dict."""
        mods = {}
        for node_id in self.owned:
            node = SKILL_NODES[node_id]
            if node["effect"]:
                key, value = node["effect"]
                if key in mods:
                    mods[key] += value
                else:
                    mods[key] = value
        return mods

    def add_point(self):
        self.points += 1


class SkillTreeState(BaseState):
    """Overlay state for skill tree UI. TAB to open/close."""

    def __init__(self, state_manager, skill_tree):
        self.sm = state_manager
        self.skill_tree = skill_tree
        self.W = engine.width
        self.H = engine.height
        self.hovered_node = None
        # Grid layout params
        self.grid_size = 80
        self.offset_x = self.W // 2 - 4 * self.grid_size
        self.offset_y = self.H // 2 - 3 * self.grid_size

    def _node_screen_pos(self, node_id):
        node = SKILL_NODES[node_id]
        col, row = node["pos"]
        x = self.offset_x + col * self.grid_size
        y = self.offset_y + row * self.grid_size
        return (x, y)

    def handle_events(self, events):
        mouse_pos = engine.mouse_logical()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB or event.key == pygame.K_ESCAPE:
                    return "close_skill_tree"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check click on nodes
                for node_id in SKILL_NODES:
                    sx, sy = self._node_screen_pos(node_id)
                    if (mouse_pos - pygame.Vector2(sx, sy)).length() < 22:
                        if self.skill_tree.unlock(node_id):
                            engine.audio.play(SoundType.UPGRADE)
                            engine.particles.explode(sx, sy,
                                                     BRANCH_COLORS[SKILL_NODES[node_id]["branch"]],
                                                     ExplosionType.CONFETTI, 0.8)
                        break
        return None

    def update(self, dt):
        mouse_pos = engine.mouse_logical()
        self.hovered_node = None
        for node_id in SKILL_NODES:
            sx, sy = self._node_screen_pos(node_id)
            if (mouse_pos - pygame.Vector2(sx, sy)).length() < 22:
                self.hovered_node = node_id
                break

    def draw(self, surface):
        # Semi-transparent overlay
        overlay = pygame.Surface((self.W, self.H))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        surface.blit(overlay, (0, 0))

        # Title
        engine.ui.text_centered(surface, "SKILL TREE", self.W // 2, 30, WHITE, engine.ui.font_title)
        engine.ui.text_centered(surface, f"Points: {self.skill_tree.points}",
                                self.W // 2, 65, GOLD, engine.ui.font_med)

        # Draw connections
        for node_id, node in SKILL_NODES.items():
            sx, sy = self._node_screen_pos(node_id)
            for adj_id in node["adjacent"]:
                if adj_id in SKILL_NODES:
                    ax, ay = self._node_screen_pos(adj_id)
                    # Line color
                    both_owned = node_id in self.skill_tree.owned and adj_id in self.skill_tree.owned
                    color = (80, 120, 80) if both_owned else (40, 40, 50)
                    pygame.draw.line(surface, color, (sx, sy), (ax, ay), 2)

        # Draw nodes
        for node_id, node in SKILL_NODES.items():
            sx, sy = self._node_screen_pos(node_id)
            branch_color = BRANCH_COLORS[node["branch"]]

            if node_id in self.skill_tree.owned:
                # Owned — bright, filled
                pygame.draw.circle(surface, branch_color, (sx, sy), 20)
                pygame.draw.circle(surface, WHITE, (sx, sy), 20, 2)
            elif self.skill_tree.can_unlock(node_id):
                # Available — pulsing outline
                pulse = 1 + math.sin(pygame.time.get_ticks() * 0.005) * 0.2
                r = int(20 * pulse)
                pygame.draw.circle(surface, (30, 30, 40), (sx, sy), 20)
                pygame.draw.circle(surface, branch_color, (sx, sy), r, 2)
            else:
                # Locked — dim
                pygame.draw.circle(surface, (25, 25, 30), (sx, sy), 18)
                pygame.draw.circle(surface, (50, 50, 60), (sx, sy), 18, 1)

            # Node name (short)
            short_name = node["name"][:8]
            engine.ui.text_centered(surface, short_name, sx, sy,
                                    WHITE if node_id in self.skill_tree.owned else (100, 100, 100),
                                    engine.ui.font_small)

        # Tooltip for hovered node
        if self.hovered_node:
            node = SKILL_NODES[self.hovered_node]
            tip_y = self.H - 80
            engine.ui.text_centered(surface, node["name"], self.W // 2, tip_y, WHITE, engine.ui.font_large)
            engine.ui.text_centered(surface, node["desc"], self.W // 2, tip_y + 28,
                                    (180, 180, 180), engine.ui.font_med)
            if self.skill_tree.can_unlock(self.hovered_node):
                engine.ui.text_centered(surface, "Click to unlock", self.W // 2, tip_y + 52,
                                        GOLD, engine.ui.font_small)

        # Instructions
        engine.ui.text_centered(surface, "TAB / ESC to close", self.W // 2, self.H - 20,
                                (60, 60, 60), engine.ui.font_small)
