"""
Tower synergies and hero transformation system.
Synergies activate when specific tower combos are placed near each other.
Transformations are hero ultimate forms unlocked via skill tree.
"""
import pygame
import math
import random
from game import engine
from game.constants import *
from commons.chaos_engine import ExplosionType, add_shake, SoundType


# === Tower Synergies ===
# When two towers are within 100px of each other, bonus activates

SYNERGY_COMBOS = {
    ("frost", "lightning"): {
        "name": "Shatter",
        "desc": "Frozen enemies take 3x lightning damage",
        "color": (100, 200, 255),
    },
    ("flame", "cannon"): {
        "name": "Napalm",
        "desc": "Splash ignites enemies, burn damage +100%",
        "color": (255, 100, 0),
    },
    ("frost", "sniper"): {
        "name": "Ice Spike",
        "desc": "Slowed enemies take +50% sniper damage",
        "color": (180, 220, 255),
    },
    ("lightning", "tesla"): {
        "name": "Overcharge",
        "desc": "Tesla range +30%, lightning chains +2",
        "color": (255, 255, 100),
    },
    ("necro", "chaos"): {
        "name": "Dark Ritual",
        "desc": "Ghosts deal 2x damage, chaos shots spawn ghosts",
        "color": (100, 0, 150),
    },
    ("vortex", "cannon"): {
        "name": "Implosion",
        "desc": "Pulled enemies take +80% splash damage",
        "color": (180, 80, 200),
    },
    ("missile", "sniper"): {
        "name": "Precision Strike",
        "desc": "Missiles gain +100% damage to targets below 50% HP",
        "color": (255, 150, 200),
    },
    ("laser", "frost"): {
        "name": "Cryo Beam",
        "desc": "Laser slows target, ramp speed +50%",
        "color": (100, 150, 255),
    },
}

SYNERGY_RANGE = 120


def find_active_synergies(towers):
    """Find all active synergies between placed towers."""
    active = []
    checked = set()

    for i, t1 in enumerate(towers):
        for j, t2 in enumerate(towers):
            if i >= j:
                continue
            pair_key = tuple(sorted([t1.tower_type, t2.tower_type]))
            if pair_key in checked:
                continue

            dist = (t1.pos - t2.pos).length()
            if dist <= SYNERGY_RANGE and pair_key in SYNERGY_COMBOS:
                active.append({
                    "combo": pair_key,
                    "towers": (t1, t2),
                    "data": SYNERGY_COMBOS[pair_key],
                })
                checked.add(pair_key)

    return active


def apply_synergy_damage(tower, target, base_damage, active_synergies):
    """Modify tower damage based on active synergies."""
    dmg = base_damage
    for syn in active_synergies:
        t1, t2 = syn["towers"]
        if tower not in (t1, t2):
            continue
        combo = syn["combo"]

        if combo == ("frost", "lightning"):
            # Shatter: frozen enemies take 3x from lightning
            if tower.tower_type == "lightning" and target.slow_timer > 0:
                dmg *= 3.0

        elif combo == ("flame", "cannon"):
            # Napalm: splash ignites
            if tower.tower_type == "cannon":
                target.burn_timer = max(target.burn_timer, 180)
                target.burn_dps = max(target.burn_dps, 4)

        elif combo == ("frost", "sniper"):
            # Ice Spike: slowed = +50% sniper
            if tower.tower_type == "sniper" and target.slow_timer > 0:
                dmg *= 1.5

        elif combo == ("lightning", "tesla"):
            # Overcharge handled in tower range/chain modification
            pass

        elif combo == ("necro", "chaos"):
            # Dark Ritual: ghosts deal 2x (handled elsewhere)
            pass

        elif combo == ("cannon", "vortex"):
            # Implosion: pulled enemies +80% splash
            if tower.tower_type == "cannon" and target.slow_timer > 0:
                dmg *= 1.8

        elif combo == ("missile", "sniper"):
            # Precision: missiles +100% to below 50% HP
            if tower.tower_type == "missile" and target.hp < target.max_hp * 0.5:
                dmg *= 2.0

        elif combo == ("frost", "laser"):
            # Cryo Beam: laser also slows
            if tower.tower_type == "laser":
                target.slow_timer = max(target.slow_timer, 30)
                target.slow_factor = 0.4

    return dmg


def draw_synergy_links(surface, active_synergies):
    """Draw visual connections between synergized towers."""
    for syn in active_synergies:
        t1, t2 = syn["towers"]
        color = syn["data"]["color"]
        p1 = (int(t1.pos.x), int(t1.pos.y))
        p2 = (int(t2.pos.x), int(t2.pos.y))
        # Pulsing line
        pulse = 0.5 + 0.5 * math.sin(engine.frame_count * 0.05)
        alpha_color = tuple(int(c * pulse) for c in color)
        pygame.draw.line(surface, alpha_color, p1, p2, 2)
        # Midpoint icon
        mx = (p1[0] + p2[0]) // 2
        my = (p1[1] + p2[1]) // 2
        pygame.draw.circle(surface, color, (mx, my), 5)


# === Hero Transformations ===
class Transformation:
    """Hero ultimate form — temporary massive power spike."""

    def __init__(self, name, duration, color):
        self.name = name
        self.duration = duration
        self.remaining = 0
        self.active = False
        self.color = color

    def activate(self):
        self.active = True
        self.remaining = self.duration
        add_shake(10)

    def update(self, dt):
        if self.active:
            self.remaining -= dt
            if self.remaining <= 0:
                self.active = False

    @property
    def progress(self):
        if not self.active:
            return 0
        return self.remaining / self.duration


class BerserkerForm(Transformation):
    """ATK form: 2.5x damage, 2x attack speed, attacks cause explosions. -50% HP."""

    def __init__(self):
        super().__init__("BERSERKER", 600, RED)

    def modify_stats(self):
        if not self.active:
            return {}
        return {
            "attack_damage_mult": 1.5,  # stacks with existing
            "attack_speed_mult": 1.0,
            "explosion_on_hit": True,
        }


class ShadowForm(Transformation):
    """DEF form: Invisible to enemies, move 2x speed, every 3rd attack backstabs for 5x."""

    def __init__(self):
        super().__init__("SHADOW", 480, (80, 0, 120))
        self.attack_count = 0

    def modify_stats(self):
        if not self.active:
            return {}
        return {
            "move_speed_mult": 1.0,
            "invisible": True,
            "backstab_mult": 5.0,
            "backstab_every": 3,
        }

    def on_attack(self):
        if not self.active:
            return 1.0
        self.attack_count += 1
        if self.attack_count >= 3:
            self.attack_count = 0
            return 5.0
        return 1.0


class ChaosIncarnateForm(Transformation):
    """CHAOS form: All abilities have no cooldown, chaos field damages all enemies."""

    def __init__(self):
        super().__init__("CHAOS INCARNATE", 360, MAGENTA)

    def modify_stats(self):
        if not self.active:
            return {}
        return {
            "no_cooldowns": True,
            "chaos_field_damage": 2.0,
        }


class TransformationManager:
    """Manages hero transformations. Unlocked via skill tree."""

    def __init__(self):
        self.berserker = BerserkerForm()
        self.shadow = ShadowForm()
        self.chaos = ChaosIncarnateForm()
        self.forms = [self.berserker, self.shadow, self.chaos]
        self.transform_cooldown = 0
        self.transform_max_cd = 1800  # 30 sec

    @property
    def active_form(self):
        for f in self.forms:
            if f.active:
                return f
        return None

    def can_transform(self):
        return self.transform_cooldown <= 0 and self.active_form is None

    def activate(self, form_idx, unlocked_forms):
        """Activate a transformation by index."""
        if not self.can_transform():
            return False
        if form_idx >= len(unlocked_forms) or form_idx < 0:
            return False
        form_name = unlocked_forms[form_idx]
        form_map = {"berserker": self.berserker, "shadow": self.shadow, "chaos": self.chaos}
        form = form_map.get(form_name)
        if form:
            form.activate()
            self.transform_cooldown = self.transform_max_cd
            engine.audio.play(SoundType.POWERUP)
            return True
        return False

    def update(self, dt):
        if self.transform_cooldown > 0:
            self.transform_cooldown -= dt
        for f in self.forms:
            f.update(dt)

    def get_modifiers(self):
        form = self.active_form
        if form:
            return form.modify_stats()
        return {}

    def draw(self, surface, hero_pos):
        form = self.active_form
        if not form:
            return
        pos = (int(hero_pos.x), int(hero_pos.y))
        # Aura
        pulse = 0.8 + 0.2 * math.sin(engine.frame_count * 0.1)
        aura_r = int(40 * pulse)
        pygame.draw.circle(surface, form.color, pos, aura_r, 2)
        pygame.draw.circle(surface, form.color, pos, int(aura_r * 0.6), 1)
        # Form name above hero
        engine.ui.text_centered(surface, form.name, pos[0], pos[1] - 40,
                                form.color, engine.ui.font_small)
        # Duration bar
        bar_w = 40
        bar_x = pos[0] - bar_w // 2
        bar_y = pos[1] - 50
        pygame.draw.rect(surface, DARK_GRAY, (bar_x, bar_y, bar_w, 4))
        pygame.draw.rect(surface, form.color, (bar_x, bar_y, int(bar_w * form.progress), 4))
