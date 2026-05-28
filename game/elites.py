"""
Elite modifier system — enemies can roll random affixes from wave 5+.
Boss phases from wave 5+. Scaling that outpaces passive play.
"""
import random
import math
import pygame
from game import engine
from game.constants import *
from commons.chaos_engine import ExplosionType, add_shake

# Elite affixes — applied randomly to enemies
ELITE_AFFIXES = {
    "regen": {
        "name": "Regenerating",
        "color": GREEN,
        "desc": "Heals 2% HP/sec",
    },
    "thorns": {
        "name": "Thorny",
        "color": ORANGE,
        "desc": "Reflects 20% damage to nearest tower",
    },
    "immune_phase": {
        "name": "Phasing",
        "color": (200, 200, 255),
        "desc": "Immune for 2s every 8s",
    },
    "speed_burst": {
        "name": "Sprinter",
        "color": YELLOW,
        "desc": "Bursts to 3x speed for 1s every 5s",
    },
    "vampiric": {
        "name": "Vampiric",
        "color": (180, 0, 60),
        "desc": "Heals on hitting base",
    },
    "armored": {
        "name": "Armored",
        "color": SILVER,
        "desc": "Takes 40% less damage",
    },
    "enrage": {
        "name": "Enraged",
        "color": RED,
        "desc": "Gets stronger when allies die nearby",
    },
    "dodgy": {
        "name": "Evasive",
        "color": CYAN,
        "desc": "20% chance to dodge attacks",
    },
}

# Boss phases — bosses cycle through these
BOSS_PHASES = [
    {"name": "Assault", "speed_mult": 1.5, "dmg_reduction": 0, "summon": False, "duration": 300},
    {"name": "Shield", "speed_mult": 0.5, "dmg_reduction": 0.8, "summon": False, "duration": 180},
    {"name": "Summon", "speed_mult": 0.3, "dmg_reduction": 0.3, "summon": True, "duration": 200},
    {"name": "Berserk", "speed_mult": 2.0, "dmg_reduction": -0.3, "summon": False, "duration": 150},
]


def roll_elite_affixes(wave, enemy_type):
    """Roll 0-2 elite affixes based on wave. Higher waves = more elites."""
    if wave < 5:
        return []
    if enemy_type == "boss":
        # Bosses always get 2 affixes from wave 5+
        return random.sample(list(ELITE_AFFIXES.keys()), min(2, len(ELITE_AFFIXES)))
    if enemy_type in ("swarm", "fast"):
        # Small enemies rarely elite
        chance = (wave - 5) * 0.02
    else:
        chance = (wave - 4) * 0.05

    affixes = []
    if random.random() < chance:
        affixes.append(random.choice(list(ELITE_AFFIXES.keys())))
    if wave >= 10 and random.random() < chance * 0.5:
        second = random.choice([a for a in ELITE_AFFIXES if a not in affixes])
        affixes.append(second)
    return affixes


class EliteModifier:
    """Manages elite affix state on an enemy."""

    def __init__(self, affixes):
        self.affixes = affixes
        self.is_elite = len(affixes) > 0
        # Timers
        self.immune_timer = 0
        self.immune_cooldown = 0
        self.speed_burst_timer = 0
        self.speed_burst_cooldown = 0
        self.enrage_stacks = 0
        self.regen_timer = 0

    def update(self, enemy, enemies_list, dt):
        if not self.is_elite:
            return

        # Regen
        if "regen" in self.affixes:
            self.regen_timer += dt
            if self.regen_timer >= 60:
                self.regen_timer = 0
                heal = enemy.max_hp * 0.02
                enemy.hp = min(enemy.max_hp, enemy.hp + heal)

        # Immune phase
        if "immune_phase" in self.affixes:
            if self.immune_timer > 0:
                self.immune_timer -= dt
            else:
                self.immune_cooldown -= dt
                if self.immune_cooldown <= 0:
                    self.immune_timer = 120  # 2 sec immune
                    self.immune_cooldown = 480  # 8 sec cd
                    engine.particles.emit(enemy.pos.x, enemy.pos.y, (200, 200, 255), 8, speed=3)

        # Speed burst
        if "speed_burst" in self.affixes:
            if self.speed_burst_timer > 0:
                self.speed_burst_timer -= dt
            else:
                self.speed_burst_cooldown -= dt
                if self.speed_burst_cooldown <= 0:
                    self.speed_burst_timer = 60  # 1 sec burst
                    self.speed_burst_cooldown = 300  # 5 sec cd

    def modify_damage_taken(self, dmg, enemy):
        """Modify incoming damage. Return modified amount."""
        if not self.is_elite:
            return dmg

        # Immune phase
        if "immune_phase" in self.affixes and self.immune_timer > 0:
            engine.particles.emit(enemy.pos.x, enemy.pos.y, (200, 200, 255), 3, speed=2)
            return 0

        # Armor
        if "armored" in self.affixes:
            dmg *= 0.6

        # Dodge
        if "dodgy" in self.affixes:
            if random.random() < 0.2:
                engine.particles.emit(enemy.pos.x, enemy.pos.y, CYAN, 4, speed=4)
                return 0

        # Enrage reduction (gets tankier with stacks)
        if "enrage" in self.affixes:
            dmg *= max(0.5, 1 - self.enrage_stacks * 0.05)

        return dmg

    def modify_speed(self, base_speed):
        """Modify movement speed."""
        if not self.is_elite:
            return base_speed

        speed = base_speed
        if "speed_burst" in self.affixes and self.speed_burst_timer > 0:
            speed *= 3.0
        if "enrage" in self.affixes:
            speed *= (1 + self.enrage_stacks * 0.1)
        return speed

    def on_nearby_death(self):
        """Called when an ally dies nearby — for enrage."""
        if "enrage" in self.affixes:
            self.enrage_stacks = min(10, self.enrage_stacks + 1)

    def on_hit_base(self, enemy):
        """Called when enemy reaches base — for vampiric."""
        if "vampiric" in self.affixes:
            enemy.hp = min(enemy.max_hp, enemy.hp + enemy.max_hp * 0.3)

    def draw_indicators(self, surface, pos, radius):
        """Draw elite visual indicators."""
        if not self.is_elite:
            return
        # Elite border glow
        for i, affix in enumerate(self.affixes):
            color = ELITE_AFFIXES[affix]["color"]
            r = radius + 4 + i * 3
            pygame.draw.circle(surface, color, pos, r, 1)

        # Immune shield visual
        if "immune_phase" in self.affixes and self.immune_timer > 0:
            pygame.draw.circle(surface, (200, 200, 255), pos, radius + 8, 2)

        # Enrage stacks
        if "enrage" in self.affixes and self.enrage_stacks > 0:
            for i in range(min(self.enrage_stacks, 5)):
                sx = pos[0] - 10 + i * 5
                sy = pos[1] - radius - 14
                pygame.draw.circle(surface, RED, (sx, sy), 2)


class BossPhaseManager:
    """Manages boss phase cycling."""

    def __init__(self):
        self.phase_idx = 0
        self.phase_timer = 0
        self.active = False
        self.summon_timer = 0

    @property
    def current_phase(self):
        return BOSS_PHASES[self.phase_idx]

    def update(self, enemy, enemies_list, path, wave, dt):
        if not self.active:
            return []

        self.phase_timer += dt
        phase = self.current_phase
        spawned = []

        if self.phase_timer >= phase["duration"]:
            self.phase_timer = 0
            self.phase_idx = (self.phase_idx + 1) % len(BOSS_PHASES)
            # Phase transition explosion
            engine.particles.explode(enemy.pos.x, enemy.pos.y, PURPLE, ExplosionType.RING, 1.0)
            add_shake(4)

        # Summon phase — spawn minions
        if phase["summon"]:
            self.summon_timer += dt
            if self.summon_timer >= 90:
                self.summon_timer = 0
                from game.enemies import Enemy
                mini = Enemy(path, "swarm", wave)
                mini.path_idx = enemy.path_idx
                mini.pos = pygame.Vector2(enemy.pos)
                spawned.append(mini)
                engine.particles.emit(enemy.pos.x, enemy.pos.y, PURPLE, 6, speed=3)

        return spawned

    def modify_speed(self, base_speed):
        if not self.active:
            return base_speed
        return base_speed * self.current_phase["speed_mult"]

    def modify_damage(self, dmg):
        if not self.active:
            return dmg
        reduction = self.current_phase["dmg_reduction"]
        return dmg * (1 - reduction)

    def draw(self, surface, pos, radius):
        if not self.active:
            return
        phase = self.current_phase
        # Phase indicator ring
        progress = self.phase_timer / phase["duration"]
        arc_end = math.pi * 2 * progress
        phase_colors = [(255, 100, 100), (100, 100, 255), (200, 100, 255), (255, 50, 50)]
        color = phase_colors[self.phase_idx]
        pygame.draw.arc(surface, color,
                        (pos[0] - radius - 8, pos[1] - radius - 8,
                         (radius + 8) * 2, (radius + 8) * 2),
                        -math.pi / 2, -math.pi / 2 + arc_end, 3)
        # Phase name
        engine.ui.text_centered(surface, phase["name"], pos[0], pos[1] - radius - 16,
                                color, engine.ui.font_small)


# === Difficulty Scaling ===
def get_wave_scaling(wave):
    """Returns multipliers that scale enemy stats per wave. Exponential past wave 10."""
    if wave <= 5:
        hp_mult = 1.0 + wave * 0.15
        speed_mult = 1.0 + wave * 0.02
        elite_chance = 0
    elif wave <= 10:
        hp_mult = 1.75 + (wave - 5) * 0.3
        speed_mult = 1.1 + (wave - 5) * 0.03
        elite_chance = (wave - 5) * 0.1
    elif wave <= 20:
        hp_mult = 3.25 + (wave - 10) * 0.5
        speed_mult = 1.25 + (wave - 10) * 0.04
        elite_chance = 0.5 + (wave - 10) * 0.03
    else:
        # Exponential scaling past wave 20
        hp_mult = 8.25 * (1.12 ** (wave - 20))
        speed_mult = 1.65 + (wave - 20) * 0.02
        elite_chance = min(0.9, 0.8 + (wave - 20) * 0.01)

    return {
        "hp_mult": hp_mult,
        "speed_mult": speed_mult,
        "elite_chance": elite_chance,
        "gold_mult": 1.0 + wave * 0.05,
    }


# === Smart Enemy AI Behaviors ===
class EnemyAI:
    """Smarter enemy behaviors — dodging, lane targeting, priority."""

    @staticmethod
    def should_dodge(enemy, projectiles):
        """Fast enemies try to dodge incoming projectiles."""
        if enemy.enemy_type not in ("fast", "teleporter", "ghost"):
            return None
        for p in projectiles:
            if not p.alive:
                continue
            # Check if projectile is heading toward this enemy
            if p.target is enemy:
                dist = (p.pos - enemy.pos).length()
                if dist < 50 and random.random() < 0.15:
                    # Dodge perpendicular to projectile direction
                    diff = enemy.pos - p.pos
                    if diff.length() > 0:
                        perp = pygame.Vector2(-diff.y, diff.x).normalize()
                        return perp * 15 * random.choice([-1, 1])
        return None

    @staticmethod
    def healer_priority(healer, enemies_list):
        """Healer prioritizes lowest HP ally in range."""
        best = None
        lowest_pct = 1.0
        for e in enemies_list:
            if e is healer or not e.alive:
                continue
            dist = (e.pos - healer.pos).length()
            if dist < 120:
                pct = e.hp / e.max_hp
                if pct < lowest_pct:
                    lowest_pct = pct
                    best = e
        return best

    @staticmethod
    def assassin_behavior(enemy, base_pos, towers):
        """Some enemies pathfind to avoid tower coverage (future: path deviation)."""
        # For now: if enemy is fast-type near towers, speed boost
        for t in towers:
            dist = (t.pos - enemy.pos).length()
            if dist < t.range * 0.8:
                return 1.3  # Speed boost through kill zones
        return 1.0
