"""
CHAOS ENGINE — Idle Tower Defense
All engine features from commons/chaos_engine.
Resizable window. EXPLOSIONS EVERYWHERE.
"""
import pygame
import random
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from commons.chaos_engine import (
    ChaosEngine, ParticleSystem, ExplosionType,
    PhysicsBody, CollisionSystem, Attractor,
    Camera, add_shake, DamageNumber, Trail,
    Entity, EntityManager,
    ChaosField, ChaosEvent, CHAOS_MODES,
    UIRenderer, load_config,
)

# === Colors ===
BG_COLOR = (12, 12, 18)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 200)
YELLOW = (255, 220, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 120)
ORANGE = (255, 150, 30)
BLUE = (50, 100, 255)
PURPLE = (180, 50, 255)
DARK_GRAY = (40, 40, 50)
GOLD = (255, 200, 50)
TEAL = (0, 200, 180)
PINK = (255, 100, 150)

# === Init Engine ===
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
engine = ChaosEngine("CHAOS ENGINE — Idle Tower Defense", CONFIG_PATH)
WIDTH = engine.width
HEIGHT = engine.height


# === Path Generation ===
def generate_path():
    points = []
    segments = random.randint(5, 7)
    margin = 100
    x_step = (WIDTH - margin * 2) / segments
    start_y = random.randint(HEIGHT // 4, HEIGHT * 3 // 4)
    points.append(pygame.Vector2(-20, start_y))
    for i in range(1, segments):
        x = margin + x_step * i
        y = random.randint(margin, HEIGHT - margin - 120)
        points.append(pygame.Vector2(x, y))
    points.append(pygame.Vector2(WIDTH - 60, HEIGHT // 2))
    return points


def interpolate_path(points, steps=80):
    path = []
    for i in range(len(points) - 1):
        for t in range(steps):
            frac = t / steps
            p = points[i] + (points[i + 1] - points[i]) * frac
            path.append(p)
    path.append(points[-1])
    return path


NUM_LANES = 3
lanes = []


def regenerate_lanes():
    global lanes
    lanes = [interpolate_path(generate_path(), 80) for _ in range(NUM_LANES)]


regenerate_lanes()


# === Enemy ===
class Enemy:
    def __init__(self, path, enemy_type="normal", wave=1):
        self.path = path
        self.path_idx = 0
        self.pos = pygame.Vector2(path[0])
        self.alive = True
        self.enemy_type = enemy_type
        self.wave = wave
        self.slow_timer = 0
        self.slow_factor = 0.4
        self.burn_timer = 0
        self.burn_dps = 0
        self.age = 0
        self._counted = False

        stats = {
            "normal": (30, 1.5, 12, RED, 5, 10),
            "fast": (20, 3.2, 9, ORANGE, 8, 15),
            "tank": (120, 0.7, 24, (150, 60, 60), 25, 40),
            "swarm": (10, 2.2, 7, MAGENTA, 2, 5),
            "boss": (600, 0.5, 38, PURPLE, 120, 250),
            "healer": (45, 1.1, 14, GREEN, 18, 25),
            "shielded": (60, 1.0, 16, TEAL, 20, 22),
            "exploder": (25, 2.5, 13, YELLOW, 12, 18),
            "ghost": (35, 1.8, 11, (200, 200, 255), 15, 20),
        }
        hp, spd, rad, col, gold, score = stats.get(enemy_type, stats["normal"])
        self.max_hp = hp + wave * (10 if enemy_type != "boss" else 80)
        self.hp = self.max_hp
        self.speed = spd + wave * 0.04
        self.radius = rad
        self.color = col
        self.gold_value = gold + wave
        self.score_value = score
        self.shield_hp = (30 + wave * 5) if enemy_type == "shielded" else 0
        self.max_shield = self.shield_hp
        self.heal_timer = 0
        self.phase_timer = 0

    def update(self, enemies_list, dt):
        if not self.alive:
            return False
        self.age += dt

        speed_mult = 1.0
        if self.slow_timer > 0:
            self.slow_timer -= dt
            speed_mult = self.slow_factor

        if self.enemy_type == "ghost":
            self.phase_timer += dt
            if math.sin(self.phase_timer * 0.03) > 0.8:
                speed_mult *= 2.0

        if self.burn_timer > 0:
            self.burn_timer -= dt
            self.hp -= self.burn_dps * dt
            if random.random() < 0.1:
                engine.particles.emit(self.pos.x, self.pos.y, ORANGE, 2, speed=2, radius=2)
            if self.hp <= 0:
                self.die()
                return False

        if self.path_idx < len(self.path) - 1:
            target = self.path[self.path_idx + 1]
            diff = target - self.pos
            dist = diff.length()
            move = self.speed * speed_mult * dt
            if dist <= move:
                self.path_idx += 1
                self.pos = pygame.Vector2(target)
            else:
                self.pos += diff.normalize() * move
        else:
            self.alive = False
            return True

        if self.enemy_type == "healer":
            self.heal_timer += dt
            if self.heal_timer >= 90:
                self.heal_timer = 0
                for e in enemies_list:
                    if e.alive and e is not self:
                        if (e.pos - self.pos).length() < 100:
                            e.hp = min(e.max_hp, e.hp + e.max_hp * 0.05)

        return False

    def take_damage(self, dmg, dmg_type="physical"):
        if not self.alive:
            return

        if self.enemy_type == "ghost" and math.sin(self.phase_timer * 0.03) > 0.8:
            engine.particles.emit(self.pos.x, self.pos.y, (200, 200, 255), 5, speed=3)
            return

        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, dmg)
            self.shield_hp -= absorbed
            dmg -= absorbed
            if self.shield_hp <= 0:
                engine.particles.explode(self.pos.x, self.pos.y, TEAL, ExplosionType.RING, 0.5)

        crit = random.random() < 0.12
        if crit:
            dmg *= 2.2
        self.hp -= dmg
        damage_numbers.append(DamageNumber(self.pos.x, self.pos.y, dmg, YELLOW if crit else WHITE, crit))
        if self.hp <= 0:
            self.die()

    def die(self):
        self.alive = False
        if self.enemy_type == "boss":
            engine.particles.chain_explosion(self.pos.x, self.pos.y, self.color, 150, 8, 2.0)
            add_shake(20)
        elif self.enemy_type == "exploder":
            engine.particles.explode(self.pos.x, self.pos.y, YELLOW, ExplosionType.SHOCKWAVE, 1.5)
            add_shake(8)
            for e in enemies:
                if e.alive and e is not self:
                    if (e.pos - self.pos).length() < 80:
                        e.take_damage(30)
        elif self.enemy_type == "tank":
            engine.particles.explode(self.pos.x, self.pos.y, self.color, ExplosionType.NOVA, 1.2)
            add_shake(6)
        else:
            etype = random.choice([ExplosionType.BURST, ExplosionType.SPARKS, ExplosionType.FIREWORK])
            engine.particles.explode(self.pos.x, self.pos.y, self.color, etype, 0.8)
            add_shake(2)

    def draw(self, surface):
        if not self.alive:
            return
        pos = (int(self.pos.x), int(self.pos.y))
        pulse = 1 + math.sin(self.age * 0.08) * 0.08
        r = int(self.radius * pulse)

        if self.enemy_type == "ghost" and math.sin(self.phase_timer * 0.03) > 0.8:
            color = tuple(c // 3 for c in self.color)
            pygame.draw.circle(surface, color, pos, r)
            return

        if self.slow_timer > 0:
            pygame.draw.circle(surface, BLUE, pos, r + 5, 1)

        pygame.draw.circle(surface, self.color, pos, r)

        if self.shield_hp > 0:
            pygame.draw.circle(surface, TEAL, pos, r + 3, 2)

        bar_w = self.radius * 2.5
        bar_h = 4
        bx = self.pos.x - bar_w / 2
        by = self.pos.y - self.radius - 10
        pct = self.hp / self.max_hp
        pygame.draw.rect(surface, DARK_GRAY, (int(bx), int(by), int(bar_w), bar_h))
        col = GREEN if pct > 0.5 else YELLOW if pct > 0.25 else RED
        pygame.draw.rect(surface, col, (int(bx), int(by), int(bar_w * pct), bar_h))

        if self.burn_timer > 0:
            pygame.draw.circle(surface, ORANGE, pos, r + 2, 1)


# === Tower Types ===
TOWER_DATA = {
    "arrow": {"name": "Arrow", "cost": 50, "dmg": 18, "range": 160, "rate": 25, "color": CYAN,
              "desc": "Fast single target", "upgrades": [80, 130, 220]},
    "cannon": {"name": "Cannon", "cost": 100, "dmg": 50, "range": 130, "rate": 55, "color": ORANGE,
               "desc": "Splash AOE", "upgrades": [150, 260, 420]},
    "frost": {"name": "Frost", "cost": 75, "dmg": 10, "range": 140, "rate": 22, "color": BLUE,
              "desc": "Slows enemies", "upgrades": [110, 190, 320]},
    "lightning": {"name": "Lightning", "cost": 130, "dmg": 28, "range": 150, "rate": 40, "color": YELLOW,
                  "desc": "Chain 3 targets", "upgrades": [200, 340, 550]},
    "sniper": {"name": "Sniper", "cost": 160, "dmg": 120, "range": 320, "rate": 85, "color": WHITE,
               "desc": "Massive single hit", "upgrades": [270, 430, 700]},
    "chaos": {"name": "Chaos", "cost": 200, "dmg": 35, "range": 170, "rate": 35, "color": MAGENTA,
              "desc": "Random EXPLOSIONS", "upgrades": [320, 520, 850]},
    "flame": {"name": "Flame", "cost": 110, "dmg": 5, "range": 100, "rate": 5, "color": (255, 120, 20),
              "desc": "Burn DOT, short range", "upgrades": [170, 280, 450]},
    "missile": {"name": "Missile", "cost": 180, "dmg": 80, "range": 250, "rate": 75, "color": PINK,
                "desc": "Homing + BIG explosion", "upgrades": [280, 460, 750]},
}


class Projectile:
    def __init__(self, x, y, target, damage, speed=10, color=CYAN,
                 splash=0, slow=0, chain=0, pierce=0, burn=0, homing=True,
                 explosion_type=None):
        self.pos = pygame.Vector2(x, y)
        self.target = target
        self.damage = damage
        self.speed = speed
        self.color = color
        self.radius = 4
        self.alive = True
        self.splash = splash
        self.slow = slow
        self.chain = chain
        self.pierce = pierce
        self.burn = burn
        self.homing = homing
        self.explosion_type = explosion_type
        self.hit_ids = set()
        self.age = 0
        self.trail = Trail(max_length=8)

    def update(self, enemies, dt):
        if not self.alive:
            return
        self.age += dt
        self.trail.add(self.pos)

        if self.target is None or not self.target.alive:
            if self.homing:
                closest = None
                closest_dist = 9999
                for e in enemies:
                    if e.alive and id(e) not in self.hit_ids:
                        d = (e.pos - self.pos).length()
                        if d < closest_dist:
                            closest = e
                            closest_dist = d
                self.target = closest
            if self.target is None:
                self.alive = False
                return

        diff = self.target.pos - self.pos
        dist = diff.length()
        if dist < self.speed * dt + self.target.radius:
            self.hit(enemies)
        else:
            self.pos += diff.normalize() * self.speed * dt

        if self.pos.x < -100 or self.pos.x > WIDTH + 100 or self.pos.y < -100 or self.pos.y > HEIGHT + 100:
            self.alive = False
        if self.age > 400:
            self.alive = False

    def hit(self, enemies):
        if not self.target or not self.target.alive:
            self.alive = False
            return

        self.target.take_damage(self.damage)
        self.hit_ids.add(id(self.target))

        if self.explosion_type:
            engine.particles.explode(
                self.target.pos.x, self.target.pos.y, self.color,
                self.explosion_type, 1.0 + self.splash * 0.01)
            add_shake(3 + self.splash * 0.05)
        else:
            engine.particles.emit(self.target.pos.x, self.target.pos.y, self.color, 4, speed=3)

        if self.slow > 0 and self.target.alive:
            self.target.slow_timer = max(self.target.slow_timer, 60)
            self.target.slow_factor = self.slow

        if self.burn > 0 and self.target.alive:
            self.target.burn_timer = 120
            self.target.burn_dps = self.burn

        if self.splash > 0:
            for e in enemies:
                if e.alive and e is not self.target and id(e) not in self.hit_ids:
                    if (e.pos - self.target.pos).length() < self.splash:
                        e.take_damage(self.damage * 0.5)
                        self.hit_ids.add(id(e))

        if self.chain > 0:
            closest = None
            closest_dist = 160
            for e in enemies:
                if e.alive and id(e) not in self.hit_ids:
                    d = (e.pos - self.target.pos).length()
                    if d < closest_dist:
                        closest = e
                        closest_dist = d
            if closest:
                self.target = closest
                self.chain -= 1
                self.damage *= 0.7
                engine.particles.emit(closest.pos.x, closest.pos.y, YELLOW, 3, speed=2)
                return

        if self.pierce > 0:
            self.pierce -= 1
            closest = None
            closest_dist = 200
            for e in enemies:
                if e.alive and id(e) not in self.hit_ids:
                    d = (e.pos - self.pos).length()
                    if d < closest_dist:
                        closest = e
                        closest_dist = d
            if closest:
                self.target = closest
                return

        self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        self.trail.draw(surface, self.color, max_width=4)
        pos = (int(self.pos.x), int(self.pos.y))
        pygame.draw.circle(surface, self.color, pos, self.radius)
        pygame.draw.circle(surface, WHITE, pos, max(1, self.radius - 2))


# === Tower with Unique Sprites & Attack Animations ===
class Tower:
    def __init__(self, x, y, tower_type="arrow"):
        self.pos = pygame.Vector2(x, y)
        self.tower_type = tower_type
        self.level = 1
        self.fire_timer = 0
        self.target = None
        self.angle = 0
        self.kills = 0
        self.total_damage = 0

        data = TOWER_DATA[tower_type]
        self.damage = data["dmg"]
        self.range = data["range"]
        self.fire_rate = data["rate"]
        self.color = data["color"]

        # Animation state
        self.anim_flash = 0
        self.recoil = 0
        self.flame_stream = []
        self.lightning_arcs = []

    def get_upgrade_cost(self):
        data = TOWER_DATA[self.tower_type]
        if self.level - 1 < len(data["upgrades"]):
            return data["upgrades"][self.level - 1]
        return None

    def upgrade(self):
        self.level += 1
        self.damage = int(self.damage * 1.6)
        self.range = int(self.range * 1.1)
        self.fire_rate = max(5, int(self.fire_rate * 0.82))
        engine.particles.explode(self.pos.x, self.pos.y, GOLD, ExplosionType.CONFETTI, 0.8)
        add_shake(3)

    def find_target(self, enemies):
        best = None
        best_progress = -1
        for e in enemies:
            if not e.alive:
                continue
            dist = (e.pos - self.pos).length()
            if dist <= self.range and e.path_idx > best_progress:
                best = e
                best_progress = e.path_idx
        self.target = best

    def update(self, enemies, projectiles_list, dt, fire_rate_mult=1.0):
        self.fire_timer -= dt * fire_rate_mult
        self.find_target(enemies)

        # Smooth turret rotation
        if self.target:
            diff = self.target.pos - self.pos
            target_angle = math.atan2(diff.y, diff.x)
            angle_diff = target_angle - self.angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            self.angle += angle_diff * 0.15 * dt

        if self.target and self.fire_timer <= 0:
            self.fire_timer = self.fire_rate
            self.shoot(projectiles_list, enemies)
            self.anim_flash = 8

        # Decay animations
        if self.anim_flash > 0:
            self.anim_flash -= dt
        if self.recoil > 0:
            self.recoil *= 0.82

        # Flame stream
        if self.tower_type == "flame" and self.target and self.target.alive:
            if (self.target.pos - self.pos).length() <= self.range:
                self._update_flame_stream()
            else:
                self.flame_stream = []
        else:
            self.flame_stream = []

        # Lightning arc decay
        self.lightning_arcs = [(a, b, life - dt) for a, b, life in self.lightning_arcs if life > 0]

    def _update_flame_stream(self):
        start = self.pos + pygame.Vector2(math.cos(self.angle), math.sin(self.angle)) * 28
        end = self.target.pos
        self.flame_stream = []
        for i in range(10):
            t = i / 9
            px = start.x + (end.x - start.x) * t + random.uniform(-8, 8) * t
            py = start.y + (end.y - start.y) * t + random.uniform(-8, 8) * t
            self.flame_stream.append((px, py))
        if random.random() < 0.5:
            mid = self.flame_stream[len(self.flame_stream) // 2]
            engine.particles.emit(mid[0], mid[1],
                                  random.choice([(255, 150, 20), (255, 80, 0), (255, 220, 50)]),
                                  2, speed=2, radius=3, gravity=0.04, decay=0.06)

    def shoot(self, projectiles_list, enemies):
        if not self.target:
            return
        x, y = self.pos.x, self.pos.y
        muzzle_x = x + math.cos(self.angle) * 25
        muzzle_y = y + math.sin(self.angle) * 25

        if self.tower_type == "arrow":
            projectiles_list.append(Projectile(x, y, self.target, self.damage, speed=12, color=self.color))
            engine.particles.emit(muzzle_x, muzzle_y, CYAN, 4, speed=5, spread=0.4, angle=self.angle)

        elif self.tower_type == "cannon":
            projectiles_list.append(Projectile(x, y, self.target, self.damage,
                                               speed=8, color=self.color, splash=70,
                                               explosion_type=ExplosionType.BURST))
            self.recoil = 7
            engine.particles.emit(muzzle_x, muzzle_y, ORANGE, 10, speed=6, spread=0.6, angle=self.angle, radius=4)
            engine.particles.emit(x, y, (80, 80, 80), 5, speed=2, radius=5, gravity=0.02)
            add_shake(2)

        elif self.tower_type == "frost":
            projectiles_list.append(Projectile(x, y, self.target, self.damage, speed=10, color=self.color, slow=0.35))
            engine.particles.emit(muzzle_x, muzzle_y, (150, 200, 255), 6, speed=4, spread=0.8, angle=self.angle, radius=2)

        elif self.tower_type == "lightning":
            projectiles_list.append(Projectile(x, y, self.target, self.damage,
                                               speed=18, color=self.color, chain=3 + self.level))
            self.lightning_arcs.append((pygame.Vector2(self.pos), pygame.Vector2(self.target.pos), 12))
            engine.particles.emit(x, y, YELLOW, 8, speed=5, radius=3, glow=True)

        elif self.tower_type == "sniper":
            projectiles_list.append(Projectile(x, y, self.target, self.damage,
                                               speed=25, color=self.color,
                                               explosion_type=ExplosionType.SPARKS))
            self.recoil = 9
            self.lightning_arcs.append((pygame.Vector2(self.pos), pygame.Vector2(self.target.pos), 5))
            engine.particles.emit(muzzle_x, muzzle_y, WHITE, 8, speed=8, spread=0.3, angle=self.angle, radius=3, glow=True)
            add_shake(3)

        elif self.tower_type == "chaos":
            effects = [
                {"splash": 90, "explosion_type": ExplosionType.SHOCKWAVE},
                {"chain": 6},
                {"pierce": 4},
                {"slow": 0.15, "splash": 60},
                {"burn": 3, "explosion_type": ExplosionType.FIREWORK},
                {"splash": 120, "explosion_type": ExplosionType.NOVA},
            ]
            effect = random.choice(effects)
            dmg = self.damage * random.uniform(0.8, 3.0)
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=10, color=MAGENTA, **effect))
            for _ in range(5):
                c = random.choice([MAGENTA, PURPLE, CYAN, YELLOW, RED, PINK])
                engine.particles.emit(x, y, c, 2, speed=5, radius=3)
            if random.random() < 0.3:
                add_shake(4)

        elif self.tower_type == "flame":
            projectiles_list.append(Projectile(x, y, self.target, self.damage,
                                               speed=8, color=self.color, burn=2 + self.level))
            engine.particles.emit(muzzle_x, muzzle_y,
                                  (255, random.randint(60, 180), 0), 6, speed=4,
                                  spread=0.5, angle=self.angle, radius=4, gravity=0.03)

        elif self.tower_type == "missile":
            projectiles_list.append(Projectile(x, y, self.target, self.damage,
                                               speed=6, color=self.color, splash=100,
                                               explosion_type=ExplosionType.NOVA))
            self.recoil = 5
            engine.particles.emit(x, y, (100, 100, 100), 10, speed=3, radius=5, gravity=0.02, decay=0.02)
            engine.particles.emit(muzzle_x, muzzle_y, PINK, 5, speed=4, spread=0.4, angle=self.angle)
            add_shake(2)

    def draw(self, surface, selected=False):
        pos = (int(self.pos.x), int(self.pos.y))
        base_r = 18 + self.level * 2

        if selected:
            pygame.draw.circle(surface, (50, 50, 70), pos, self.range, 1)

        # Dispatch to unique sprite
        if self.tower_type == "arrow":
            self._draw_arrow(surface, pos, base_r)
        elif self.tower_type == "cannon":
            self._draw_cannon(surface, pos, base_r)
        elif self.tower_type == "frost":
            self._draw_frost(surface, pos, base_r)
        elif self.tower_type == "lightning":
            self._draw_lightning(surface, pos, base_r)
        elif self.tower_type == "sniper":
            self._draw_sniper(surface, pos, base_r)
        elif self.tower_type == "chaos":
            self._draw_chaos(surface, pos, base_r)
        elif self.tower_type == "flame":
            self._draw_flame(surface, pos, base_r)
        elif self.tower_type == "missile":
            self._draw_missile(surface, pos, base_r)

        # Level stars
        if self.level > 1:
            for i in range(min(self.level - 1, 5)):
                sx = int(self.pos.x - 8 + i * 8)
                sy = int(self.pos.y + base_r + 6)
                pygame.draw.circle(surface, GOLD, (sx, sy), 3)

        # Attack effects on top
        self._draw_effects(surface)

    # === ARROW: Hexagonal base, thin barrel, arrowhead tip ===
    def _draw_arrow(self, surface, pos, r):
        for i in range(6):
            a1 = math.pi / 3 * i
            a2 = math.pi / 3 * (i + 1)
            p1 = (int(self.pos.x + math.cos(a1) * r), int(self.pos.y + math.sin(a1) * r))
            p2 = (int(self.pos.x + math.cos(a2) * r), int(self.pos.y + math.sin(a2) * r))
            pygame.draw.line(surface, CYAN, p1, p2, 2)
        pygame.draw.circle(surface, (20, 40, 50), pos, r - 4)
        pygame.draw.circle(surface, CYAN, pos, 5)
        # Barrel
        bl = r + 14
        bx = self.pos.x + math.cos(self.angle) * bl
        by = self.pos.y + math.sin(self.angle) * bl
        pygame.draw.line(surface, CYAN, pos, (int(bx), int(by)), 2)
        # Arrowhead
        tip = 7
        tx = bx + math.cos(self.angle) * tip
        ty = by + math.sin(self.angle) * tip
        lx = bx + math.cos(self.angle + 2.5) * tip
        ly = by + math.sin(self.angle + 2.5) * tip
        rx = bx + math.cos(self.angle - 2.5) * tip
        ry = by + math.sin(self.angle - 2.5) * tip
        pygame.draw.polygon(surface, CYAN, [(int(tx), int(ty)), (int(lx), int(ly)), (int(rx), int(ry))])

    # === CANNON: Square armored base, thick barrel with muzzle brake ===
    def _draw_cannon(self, surface, pos, r):
        half = r
        pts = [
            (int(self.pos.x - half), int(self.pos.y - half)),
            (int(self.pos.x + half), int(self.pos.y - half)),
            (int(self.pos.x + half), int(self.pos.y + half)),
            (int(self.pos.x - half), int(self.pos.y + half)),
        ]
        pygame.draw.polygon(surface, (50, 35, 20), pts)
        pygame.draw.polygon(surface, ORANGE, pts, 2)
        pygame.draw.line(surface, (80, 50, 20),
                         (int(self.pos.x - half + 3), int(self.pos.y)),
                         (int(self.pos.x + half - 3), int(self.pos.y)), 2)
        # Thick barrel with recoil
        bl = r + 16 - self.recoil
        bx = self.pos.x + math.cos(self.angle) * bl
        by = self.pos.y + math.sin(self.angle) * bl
        pygame.draw.line(surface, ORANGE,
                         (int(self.pos.x + math.cos(self.angle) * r * 0.5),
                          int(self.pos.y + math.sin(self.angle) * r * 0.5)),
                         (int(bx), int(by)), 6)
        pygame.draw.line(surface, (200, 120, 30),
                         (int(self.pos.x + math.cos(self.angle) * r * 0.5),
                          int(self.pos.y + math.sin(self.angle) * r * 0.5)),
                         (int(bx), int(by)), 3)
        # Muzzle brake
        px = math.cos(self.angle + math.pi / 2) * 5
        py_off = math.sin(self.angle + math.pi / 2) * 5
        pygame.draw.line(surface, ORANGE,
                         (int(bx - px), int(by - py_off)),
                         (int(bx + px), int(by + py_off)), 3)

    # === FROST: Octagonal crystal, ice spikes, slow rotation ===
    def _draw_frost(self, surface, pos, r):
        rot = engine.frame_count * 0.005
        for i in range(8):
            a1 = math.pi / 4 * i + rot
            a2 = math.pi / 4 * (i + 1) + rot
            p1 = (int(self.pos.x + math.cos(a1) * r), int(self.pos.y + math.sin(a1) * r))
            p2 = (int(self.pos.x + math.cos(a2) * r), int(self.pos.y + math.sin(a2) * r))
            pygame.draw.line(surface, (100, 150, 255), p1, p2, 2)
        pygame.draw.circle(surface, (15, 25, 50), pos, r - 4)
        # Rotating crystals
        for i in range(4):
            a = math.pi / 2 * i + engine.frame_count * 0.02
            cx = int(self.pos.x + math.cos(a) * 7)
            cy = int(self.pos.y + math.sin(a) * 7)
            pygame.draw.circle(surface, (150, 200, 255), (cx, cy), 3)
        pygame.draw.circle(surface, BLUE, pos, 4)
        # Ice barrel
        bx = self.pos.x + math.cos(self.angle) * (r + 10)
        by = self.pos.y + math.sin(self.angle) * (r + 10)
        pygame.draw.line(surface, (100, 180, 255), pos, (int(bx), int(by)), 3)
        # Frost aura when targeting
        if self.target:
            pulse = math.sin(engine.frame_count * 0.08) * 3
            pygame.draw.circle(surface, (40, 60, 120), pos, int(r + 5 + pulse), 1)

    # === LIGHTNING: Tesla coil, orb with electrical arcs ===
    def _draw_lightning(self, surface, pos, r):
        pygame.draw.circle(surface, (30, 30, 20), pos, r)
        pygame.draw.circle(surface, YELLOW, pos, r, 2)
        pygame.draw.circle(surface, YELLOW, pos, r - 5, 1)
        # Pulsing tesla orb
        orb_pulse = 1 + math.sin(engine.frame_count * 0.12) * 0.25
        orb_r = int(8 * orb_pulse)
        pygame.draw.circle(surface, YELLOW, pos, orb_r)
        pygame.draw.circle(surface, WHITE, pos, max(2, orb_r - 3))
        # Random sparks
        for _ in range(3):
            a = random.uniform(0, math.pi * 2)
            sx = int(self.pos.x + math.cos(a) * (r - 2))
            sy = int(self.pos.y + math.sin(a) * (r - 2))
            pygame.draw.line(surface, YELLOW, pos, (sx, sy), 1)
        # Direction dot
        dx = int(self.pos.x + math.cos(self.angle) * (r + 6))
        dy = int(self.pos.y + math.sin(self.angle) * (r + 6))
        pygame.draw.circle(surface, YELLOW, (dx, dy), 3)

    # === SNIPER: Diamond base, long thin barrel, scope ===
    def _draw_sniper(self, surface, pos, r):
        diamond = [
            (int(self.pos.x), int(self.pos.y - r)),
            (int(self.pos.x + r), int(self.pos.y)),
            (int(self.pos.x), int(self.pos.y + r)),
            (int(self.pos.x - r), int(self.pos.y)),
        ]
        pygame.draw.polygon(surface, (25, 25, 30), diamond)
        pygame.draw.polygon(surface, WHITE, diamond, 2)
        # Crosshair
        pygame.draw.line(surface, (80, 80, 80),
                         (int(self.pos.x - 6), int(self.pos.y)),
                         (int(self.pos.x + 6), int(self.pos.y)), 1)
        pygame.draw.line(surface, (80, 80, 80),
                         (int(self.pos.x), int(self.pos.y - 6)),
                         (int(self.pos.x), int(self.pos.y + 6)), 1)
        # Long barrel with recoil
        bl = r + 22 - self.recoil
        bx = self.pos.x + math.cos(self.angle) * bl
        by = self.pos.y + math.sin(self.angle) * bl
        pygame.draw.line(surface, WHITE, pos, (int(bx), int(by)), 2)
        # Scope
        sd = r * 0.7
        scope_x = int(self.pos.x + math.cos(self.angle) * sd + math.cos(self.angle + math.pi / 2) * 5)
        scope_y = int(self.pos.y + math.sin(self.angle) * sd + math.sin(self.angle + math.pi / 2) * 5)
        pygame.draw.circle(surface, (150, 150, 150), (scope_x, scope_y), 3)
        pygame.draw.circle(surface, WHITE, (int(bx), int(by)), 2)

    # === CHAOS: Rotating triangle, color-shifting orb, orbiting particles ===
    def _draw_chaos(self, surface, pos, r):
        rot = engine.frame_count * 0.03
        for i in range(3):
            a1 = rot + (math.pi * 2 / 3) * i
            a2 = rot + (math.pi * 2 / 3) * (i + 1)
            p1 = (int(self.pos.x + math.cos(a1) * r), int(self.pos.y + math.sin(a1) * r))
            p2 = (int(self.pos.x + math.cos(a2) * r), int(self.pos.y + math.sin(a2) * r))
            c = [MAGENTA, PURPLE, CYAN][i]
            pygame.draw.line(surface, c, p1, p2, 2)
        # Shifting orb
        phase = engine.frame_count * 0.05
        cr = int(128 + 127 * math.sin(phase))
        cg = int(128 + 127 * math.sin(phase + 2))
        cb = int(128 + 127 * math.sin(phase + 4))
        orb_c = (cr, cg, cb)
        pygame.draw.circle(surface, orb_c, pos, 9)
        pygame.draw.circle(surface, WHITE, pos, 5)
        # Orbiting dots
        for i in range(3):
            a = engine.frame_count * 0.04 + (math.pi * 2 / 3) * i
            ox = int(self.pos.x + math.cos(a) * (r - 5))
            oy = int(self.pos.y + math.sin(a) * (r - 5))
            pygame.draw.circle(surface, orb_c, (ox, oy), 2)
        # Direction
        dx = int(self.pos.x + math.cos(self.angle) * (r + 8))
        dy = int(self.pos.y + math.sin(self.angle) * (r + 8))
        pygame.draw.circle(surface, orb_c, (dx, dy), 4)

    # === FLAME: Industrial furnace, vents, continuous fire stream ===
    def _draw_flame(self, surface, pos, r):
        pygame.draw.circle(surface, (50, 25, 10), pos, r)
        pygame.draw.circle(surface, (255, 120, 20), pos, r, 2)
        # Heat vents
        for i in range(4):
            a = math.pi / 2 * i + engine.frame_count * 0.01
            vx = int(self.pos.x + math.cos(a) * (r - 5))
            vy = int(self.pos.y + math.sin(a) * (r - 5))
            vent_c = (255, random.randint(80, 180), 0) if self.target else (100, 40, 10)
            pygame.draw.circle(surface, vent_c, (vx, vy), 3)
        # Core flame
        fp = 1 + math.sin(engine.frame_count * 0.15) * 0.3
        fr = int(7 * fp)
        pygame.draw.circle(surface, (255, 100, 0), pos, fr)
        pygame.draw.circle(surface, (255, 200, 50), pos, max(2, fr - 3))
        # Nozzle
        nl = r + 10
        nx = self.pos.x + math.cos(self.angle) * nl
        ny = self.pos.y + math.sin(self.angle) * nl
        pygame.draw.line(surface, (200, 80, 0), pos, (int(nx), int(ny)), 4)
        # Wide nozzle tip
        px = math.cos(self.angle + math.pi / 2) * 5
        py_off = math.sin(self.angle + math.pi / 2) * 5
        pygame.draw.line(surface, (255, 120, 20),
                         (int(nx - px), int(ny - py_off)),
                         (int(nx + px), int(ny + py_off)), 3)
        # FLAME STREAM
        if self.flame_stream and len(self.flame_stream) > 1:
            for i in range(1, len(self.flame_stream)):
                t = i / len(self.flame_stream)
                w = max(1, int(7 * (1 - t * 0.4)))
                fr_c = (255, int(200 - 160 * t), int(50 * (1 - t)))
                p1 = (int(self.flame_stream[i - 1][0]), int(self.flame_stream[i - 1][1]))
                p2 = (int(self.flame_stream[i][0]), int(self.flame_stream[i][1]))
                pygame.draw.line(surface, fr_c, p1, p2, w)
            # Glow at tip
            tip = self.flame_stream[-1]
            pygame.draw.circle(surface, (255, 100, 0), (int(tip[0]), int(tip[1])), 6)
            pygame.draw.circle(surface, (255, 200, 50), (int(tip[0]), int(tip[1])), 3)

    # === MISSILE: Pentagon base, triple launch tubes ===
    def _draw_missile(self, surface, pos, r):
        for i in range(5):
            a1 = math.pi * 2 / 5 * i - math.pi / 2
            a2 = math.pi * 2 / 5 * (i + 1) - math.pi / 2
            p1 = (int(self.pos.x + math.cos(a1) * r), int(self.pos.y + math.sin(a1) * r))
            p2 = (int(self.pos.x + math.cos(a2) * r), int(self.pos.y + math.sin(a2) * r))
            pygame.draw.line(surface, PINK, p1, p2, 2)
        pygame.draw.circle(surface, (35, 20, 30), pos, r - 4)
        # 3 missile tubes
        for offset in [-5, 0, 5]:
            px = math.cos(self.angle + math.pi / 2) * offset
            py_off = math.sin(self.angle + math.pi / 2) * offset
            sx = self.pos.x + px
            sy = self.pos.y + py_off
            ex = sx + math.cos(self.angle) * (r + 12 - self.recoil)
            ey = sy + math.sin(self.angle) * (r + 12 - self.recoil)
            pygame.draw.line(surface, PINK, (int(sx), int(sy)), (int(ex), int(ey)), 2)
        pygame.draw.circle(surface, PINK, pos, 4)
        # Warning flash on fire
        if self.anim_flash > 4:
            pygame.draw.circle(surface, RED, pos, r, 1)

    # === ATTACK EFFECTS (muzzle flash, lightning bolts, tracers) ===
    def _draw_effects(self, surface):
        # Muzzle flash
        if self.anim_flash > 0:
            alpha = self.anim_flash / 8
            flash_r = int(14 * alpha)
            fx = int(self.pos.x + math.cos(self.angle) * 28)
            fy = int(self.pos.y + math.sin(self.angle) * 28)
            fc = self.color
            if self.tower_type == "flame":
                fc = (255, random.randint(100, 220), 0)
            pygame.draw.circle(surface, fc, (fx, fy), flash_r)
            if flash_r > 4:
                pygame.draw.circle(surface, WHITE, (fx, fy), flash_r // 2)

        # Lightning arcs / sniper tracers
        for start, end, life in self.lightning_arcs:
            self._draw_bolt(surface, start, end, life)

    def _draw_bolt(self, surface, start, end, life):
        alpha = min(1.0, life / 6)
        points = [start]
        segments = 8
        for i in range(1, segments):
            t = i / segments
            mid = start + (end - start) * t
            mid = pygame.Vector2(mid.x + random.uniform(-12, 12) * alpha,
                                 mid.y + random.uniform(-12, 12) * alpha)
            points.append(mid)
        points.append(end)

        w = max(1, int(3 * alpha))
        color = (int(255 * alpha), int(220 * alpha), int(50 * alpha))
        for i in range(len(points) - 1):
            p1 = (int(points[i].x), int(points[i].y))
            p2 = (int(points[i + 1].x), int(points[i + 1].y))
            pygame.draw.line(surface, color, p1, p2, w)
            if w > 1:
                glow = (color[0] // 3, color[1] // 3, color[2] // 3)
                pygame.draw.line(surface, glow, p1, p2, w + 2)


# === Hero (auto-attacks + right-click + abilities) ===
class Hero:
    def __init__(self):
        self.pos = pygame.Vector2(WIDTH - 100, HEIGHT // 2)
        self.radius = 18
        self.speed = 4.5
        self.alive = True
        self.trail = Trail(max_length=12)

        self.attack_damage = 25
        self.attack_speed = 18
        self.attack_range = 200
        self.attack_timer = 0
        self.target = None
        self.angle = 0
        self.level = 1
        self.xp = 0
        self.xp_to_level = 80
        self.kills = 0

        self.q_cd = 0
        self.q_max = 150
        self.w_cd = 0
        self.w_max = 300
        self.rally_active = 0
        self.e_cd = 0
        self.e_max = 200
        self.r_cd = 0
        self.r_max = 540

        # Visual state
        self.swing_anim = 0  # attack swing timer
        self.swing_angle = 0  # swing arc
        self.q_anim = 0  # whirlwind spin visual
        self.e_anim = 0  # execute slash visual
        self.e_target_pos = None
        self.r_anim = 0  # chaos overload pulse
        self.hit_flash = 0
        self.move_bob = 0  # walking bob

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_level:
            self.xp -= self.xp_to_level
            self.level += 1
            self.xp_to_level = int(self.xp_to_level * 1.35)
            self.attack_damage += 10
            self.attack_range += 8
            self.attack_speed = max(6, self.attack_speed - 1)
            engine.particles.explode(self.pos.x, self.pos.y, GOLD, ExplosionType.CONFETTI, 1.5)
            add_shake(5)
            damage_numbers.append(DamageNumber(self.pos.x, self.pos.y - 30, self.level, GOLD, True))

    def update(self, keys, enemies, projectiles_list, dt):
        if not self.alive:
            return

        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if move.length() > 0:
            self.pos += move.normalize() * self.speed * dt
            self.move_bob += 0.3 * dt
        self.pos.x = max(self.radius, min(WIDTH - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(HEIGHT - self.radius, self.pos.y))
        self.trail.add(self.pos)

        self.attack_timer -= dt
        if self.attack_timer <= 0:
            self.find_target(enemies)
            if self.target:
                self.auto_attack(projectiles_list)
                self.attack_timer = self.attack_speed

        self.q_cd = max(0, self.q_cd - dt)
        self.w_cd = max(0, self.w_cd - dt)
        self.e_cd = max(0, self.e_cd - dt)
        self.r_cd = max(0, self.r_cd - dt)
        if self.rally_active > 0:
            self.rally_active -= dt

        # Decay animations
        if self.swing_anim > 0:
            self.swing_anim -= dt
        if self.q_anim > 0:
            self.q_anim -= dt
        if self.e_anim > 0:
            self.e_anim -= dt
        if self.r_anim > 0:
            self.r_anim -= dt
        if self.hit_flash > 0:
            self.hit_flash -= dt

    def find_target(self, enemies):
        best = None
        best_dist = self.attack_range
        for e in enemies:
            if e.alive:
                d = (e.pos - self.pos).length()
                if d < best_dist:
                    best = e
                    best_dist = d
        self.target = best
        if best:
            diff = best.pos - self.pos
            self.angle = math.atan2(diff.y, diff.x)

    def auto_attack(self, projectiles_list):
        if self.target and self.target.alive:
            projectiles_list.append(Projectile(
                self.pos.x, self.pos.y, self.target,
                self.attack_damage, speed=14, color=CYAN
            ))
            engine.particles.emit(
                self.pos.x + math.cos(self.angle) * 20,
                self.pos.y + math.sin(self.angle) * 20,
                CYAN, 3, speed=4
            )
            self.swing_anim = 10
            self.swing_angle = self.angle

    def right_click(self, mouse_pos, enemies, projectiles_list):
        for e in enemies:
            if not e.alive:
                continue
            if (e.pos - mouse_pos).length() < e.radius + 15:
                if (e.pos - self.pos).length() < self.attack_range * 1.5:
                    dmg = self.attack_damage * 2.5
                    projectiles_list.append(Projectile(
                        self.pos.x, self.pos.y, e, dmg,
                        speed=18, color=WHITE,
                        explosion_type=ExplosionType.SPARKS
                    ))
                    engine.particles.emit(self.pos.x, self.pos.y, WHITE, 8, speed=5)
                    add_shake(3)
                    return True
        return False

    def ability_q(self, enemies):
        if self.q_cd > 0:
            return
        self.q_cd = self.q_max
        self.q_anim = 20
        hits = 0
        for e in enemies:
            if e.alive and (e.pos - self.pos).length() < 130:
                e.take_damage(self.attack_damage * 1.8)
                hits += 1
        engine.particles.explode(self.pos.x, self.pos.y, CYAN, ExplosionType.SHOCKWAVE, 1.5)
        add_shake(6)
        if hits:
            self.gain_xp(hits * 5)

    def ability_w(self, towers):
        if self.w_cd > 0:
            return
        self.w_cd = self.w_max
        self.rally_active = 180
        engine.particles.explode(self.pos.x, self.pos.y, GOLD, ExplosionType.RING, 1.0)

    def ability_e(self, enemies):
        if self.e_cd > 0:
            return
        self.e_cd = self.e_max
        self.e_anim = 15
        target = None
        lowest_pct = 1.0
        for e in enemies:
            if e.alive and (e.pos - self.pos).length() < self.attack_range:
                pct = e.hp / e.max_hp
                if pct < lowest_pct:
                    lowest_pct = pct
                    target = e
        if target:
            self.e_target_pos = pygame.Vector2(target.pos)
            dmg = target.max_hp * 0.35 + self.attack_damage * 2
            target.take_damage(dmg)
            engine.particles.explode(target.pos.x, target.pos.y, RED, ExplosionType.BURST, 1.2)
            add_shake(5)

    def ability_r(self, enemies):
        if self.r_cd > 0:
            return
        self.r_cd = self.r_max
        self.r_anim = 30
        add_shake(25)
        engine.particles.chain_explosion(self.pos.x, self.pos.y, MAGENTA, 200, 10, 2.5)
        for e in enemies:
            if not e.alive:
                continue
            dmg = self.attack_damage * 4
            e.take_damage(dmg)
            if e.path_idx > 10:
                e.path_idx = max(0, e.path_idx - 25)
                e.pos = pygame.Vector2(e.path[e.path_idx])
            engine.particles.explode(e.pos.x, e.pos.y,
                                     random.choice([MAGENTA, RED, ORANGE, YELLOW]),
                                     random.choice(list(ExplosionType)), 0.6)

    def draw(self, surface):
        if not self.alive:
            return

        pos = (int(self.pos.x), int(self.pos.y))
        bob = math.sin(self.move_bob) * 2

        # Trail with gradient
        self.trail.draw(surface, CYAN, max_width=5)

        # Attack range (subtle)
        pygame.draw.circle(surface, (20, 35, 40), pos, self.attack_range, 1)

        # Rally golden aura
        if self.rally_active > 0:
            ar = 220 + math.sin(engine.frame_count * 0.1) * 8
            pygame.draw.circle(surface, GOLD, pos, int(ar), 2)
            # Inner pulse
            pygame.draw.circle(surface, (100, 80, 20), pos, int(ar * 0.8), 1)

        # === R: Chaos Overload — expanding energy rings ===
        if self.r_anim > 0:
            progress = 1 - self.r_anim / 30
            ring_r = int(200 * progress)
            ring_alpha = int(255 * (1 - progress))
            for i in range(3):
                rr = ring_r - i * 20
                if rr > 0:
                    c = (min(255, ring_alpha), 0, min(255, ring_alpha))
                    pygame.draw.circle(surface, c, pos, rr, 2)

        # === Q: Whirlwind — spinning blade arcs ===
        if self.q_anim > 0:
            spin_progress = 1 - self.q_anim / 20
            num_blades = 4
            blade_len = 100 + 30 * spin_progress
            for i in range(num_blades):
                blade_angle = spin_progress * math.pi * 4 + (math.pi * 2 / num_blades) * i
                bx = self.pos.x + math.cos(blade_angle) * blade_len
                by = self.pos.y + math.sin(blade_angle) * blade_len
                # Arc line
                alpha = 1 - spin_progress
                c = (int(0 * alpha + 255 * (1-alpha)),
                     int(255 * alpha),
                     int(255 * alpha))
                pygame.draw.line(surface, c, pos, (int(bx), int(by)), 2)
                # Blade tip
                pygame.draw.circle(surface, CYAN, (int(bx), int(by)), 4)
            # Spinning circle
            pygame.draw.circle(surface, CYAN, pos, int(blade_len), 1)

        # === E: Execute — slash line to target ===
        if self.e_anim > 0 and self.e_target_pos:
            slash_alpha = self.e_anim / 15
            sx = int(self.e_target_pos.x)
            sy = int(self.e_target_pos.y)
            # Red slash line
            pygame.draw.line(surface, (int(255 * slash_alpha), 0, 0),
                             pos, (sx, sy), max(1, int(4 * slash_alpha)))
            # X mark at target
            cross_size = int(15 * slash_alpha)
            pygame.draw.line(surface, RED,
                             (sx - cross_size, sy - cross_size),
                             (sx + cross_size, sy + cross_size), 3)
            pygame.draw.line(surface, RED,
                             (sx + cross_size, sy - cross_size),
                             (sx - cross_size, sy + cross_size), 3)

        # === BODY: Knight/warrior sprite ===
        draw_y = int(self.pos.y + bob)
        body_pos = (int(self.pos.x), draw_y)

        # Outer shield ring (level-based complexity)
        shield_sides = min(3 + self.level, 8)
        shield_r = self.radius + 4
        shield_rot = engine.frame_count * 0.008
        shield_pts = []
        for i in range(shield_sides):
            a = shield_rot + (math.pi * 2 / shield_sides) * i
            px = self.pos.x + math.cos(a) * shield_r
            py = draw_y + math.sin(a) * shield_r
            shield_pts.append((int(px), int(py)))
        pygame.draw.polygon(surface, (30, 80, 100), shield_pts, 2)

        # Inner body (armored core)
        pygame.draw.circle(surface, (20, 50, 60), body_pos, self.radius)
        # Armor plates — chevron pattern
        for i in range(3):
            offset = -4 + i * 4
            a1 = self.angle + 0.3 + offset * 0.05
            a2 = self.angle - 0.3 + offset * 0.05
            p1 = (int(self.pos.x + math.cos(a1) * (self.radius - 4)),
                  int(draw_y + math.sin(a1) * (self.radius - 4)))
            p2 = (int(self.pos.x + math.cos(a2) * (self.radius - 4)),
                  int(draw_y + math.sin(a2) * (self.radius - 4)))
            pygame.draw.line(surface, CYAN, body_pos, p1, 2)
            pygame.draw.line(surface, CYAN, body_pos, p2, 2)

        # Core gem (pulsing with level)
        gem_pulse = 1 + math.sin(engine.frame_count * 0.06) * 0.2
        gem_r = int(5 * gem_pulse)
        gem_color = CYAN if self.level < 5 else GOLD if self.level < 10 else MAGENTA
        pygame.draw.circle(surface, gem_color, body_pos, gem_r)
        pygame.draw.circle(surface, WHITE, body_pos, max(2, gem_r - 2))

        # Outer ring
        pygame.draw.circle(surface, CYAN, body_pos, self.radius, 2)

        # === WEAPON: Sword/blade extending toward target ===
        blade_len = self.radius + 16
        # Swing animation — arc the blade
        swing_offset = 0
        if self.swing_anim > 0:
            swing_progress = self.swing_anim / 10
            swing_offset = math.sin(swing_progress * math.pi) * 0.8
        blade_angle = self.angle + swing_offset

        blade_end_x = self.pos.x + math.cos(blade_angle) * blade_len
        blade_end_y = draw_y + math.sin(blade_angle) * blade_len

        # Blade body (wider at base, thin at tip)
        blade_mid_x = self.pos.x + math.cos(blade_angle) * (blade_len * 0.6)
        blade_mid_y = draw_y + math.sin(blade_angle) * (blade_len * 0.6)
        perp = blade_angle + math.pi / 2
        w1 = 4  # base width
        w2 = 1  # tip width

        # Blade polygon (tapered)
        bp1 = (int(self.pos.x + math.cos(blade_angle) * self.radius + math.cos(perp) * w1),
               int(draw_y + math.sin(blade_angle) * self.radius + math.sin(perp) * w1))
        bp2 = (int(self.pos.x + math.cos(blade_angle) * self.radius - math.cos(perp) * w1),
               int(draw_y + math.sin(blade_angle) * self.radius - math.sin(perp) * w1))
        bp3 = (int(blade_end_x - math.cos(perp) * w2),
               int(blade_end_y - math.sin(perp) * w2))
        bp4 = (int(blade_end_x + math.cos(perp) * w2),
               int(blade_end_y + math.sin(perp) * w2))
        pygame.draw.polygon(surface, (180, 220, 255), [bp1, bp4, bp3, bp2])
        pygame.draw.polygon(surface, WHITE, [bp1, bp4, bp3, bp2], 1)

        # Blade glow on swing
        if self.swing_anim > 0:
            glow_alpha = self.swing_anim / 10
            glow_r = int(8 * glow_alpha)
            pygame.draw.circle(surface, CYAN, (int(blade_end_x), int(blade_end_y)), glow_r)

        # === Shoulder pads (scale with level) ===
        if self.level >= 3:
            for side in [-1, 1]:
                pad_angle = self.angle + math.pi / 2 * side + math.pi
                pad_x = int(self.pos.x + math.cos(pad_angle) * (self.radius - 2))
                pad_y = int(draw_y + math.sin(pad_angle) * (self.radius - 2))
                pad_color = CYAN if self.level < 8 else GOLD
                pygame.draw.circle(surface, pad_color, (pad_x, pad_y), 4)
                if self.level >= 6:
                    pygame.draw.circle(surface, WHITE, (pad_x, pad_y), 4, 1)

        # === Level / XP indicator ===
        # XP arc around body
        if self.xp > 0:
            xp_pct = self.xp / self.xp_to_level
            arc_angle = xp_pct * math.pi * 2
            arc_r = self.radius + 8
            prev = None
            steps = int(arc_angle / 0.2) + 1
            for i in range(steps):
                a = -math.pi / 2 + (arc_angle * i / max(1, steps - 1))
                px = int(self.pos.x + math.cos(a) * arc_r)
                py = int(draw_y + math.sin(a) * arc_r)
                if prev:
                    pygame.draw.line(surface, GOLD, prev, (px, py), 2)
                prev = (px, py)

        # Level text
        engine.ui.text(surface, f"Lv{self.level}", int(self.pos.x - 10),
                       int(self.pos.y + self.radius + 10), gem_color, engine.ui.font_small)


# === Base ===
class Base:
    def __init__(self):
        self.pos = pygame.Vector2(WIDTH - 60, HEIGHT // 2)
        self.hp = 25
        self.max_hp = 25
        self.radius = 32

    def take_damage(self, amount=1):
        self.hp -= amount
        add_shake(10)
        engine.particles.explode(self.pos.x, self.pos.y, RED, ExplosionType.BURST, 1.5)

    def draw(self, surface):
        pos = (int(self.pos.x), int(self.pos.y))
        pulse = 1 + math.sin(engine.frame_count * 0.05) * 0.08
        r = int(self.radius * pulse)
        pct = self.hp / self.max_hp
        color = tuple(int(a + (b - a) * (1 - pct)) for a, b in zip(GREEN, RED))
        pygame.draw.circle(surface, color, pos, r)
        pygame.draw.circle(surface, WHITE, pos, r, 2)
        engine.ui.text_centered(surface, f"{self.hp}", self.pos.x, self.pos.y, WHITE, engine.ui.font_med)


# === Idle Economy ===
class Economy:
    def __init__(self):
        self.gold_per_sec = 2
        self.timer = 0
        self.interest_rate = 0.03
        self.interest_timer = 0

    def update(self, state, dt):
        self.timer += dt
        if self.timer >= 60:
            self.timer = 0
            state["gold"] += self.gold_per_sec
        self.interest_timer += dt
        if self.interest_timer >= 600:
            self.interest_timer = 0
            bonus = int(state["gold"] * self.interest_rate)
            if bonus > 0:
                state["gold"] += bonus
                damage_numbers.append(DamageNumber(WIDTH - 150, 55, bonus, GOLD))


# === Chaos Events (game-level) ===
GAME_CHAOS_EVENTS = [
    "double_speed", "weaken_enemies", "gold_rain", "tower_frenzy",
    "enemy_shields", "path_scramble", "surprise_boss", "freeze_all",
    "MEGA_EXPLOSION", "gravity_flip"
]


class GameChaos:
    def __init__(self):
        self.timer = 0
        self.interval = 900
        self.event_text = ""
        self.event_duration = 0

    def update(self, state, enemies, towers, dt):
        self.timer += dt
        if self.event_duration > 0:
            self.event_duration -= dt
            if self.event_duration <= 0:
                self.event_text = ""

        if self.timer >= self.interval and state["wave"] >= 3:
            self.timer = 0
            self.trigger(state, enemies, towers)

    def trigger(self, state, enemies, towers):
        event = random.choice(GAME_CHAOS_EVENTS)
        self.event_duration = 300
        self.event_text = f"CHAOS: {event.replace('_', ' ').upper()}!"

        if event == "double_speed":
            for e in enemies:
                if e.alive:
                    e.speed *= 2
        elif event == "weaken_enemies":
            for e in enemies:
                if e.alive:
                    e.hp = max(1, e.hp // 2)
            engine.particles.explode(WIDTH // 2, HEIGHT // 2, GREEN, ExplosionType.RING, 1.5)
        elif event == "gold_rain":
            state["gold"] += 150 + state["wave"] * 25
            engine.particles.explode(WIDTH // 2, 80, GOLD, ExplosionType.CONFETTI, 2.0)
        elif event == "tower_frenzy":
            for t in towers:
                t.fire_timer = 0
        elif event == "enemy_shields":
            for e in enemies:
                if e.alive:
                    e.shield_hp += 20
                    e.max_shield = max(e.max_shield, e.shield_hp)
        elif event == "path_scramble":
            regenerate_lanes()
            for e in enemies:
                if e.alive:
                    lane = random.choice(lanes)
                    e.path = lane
                    e.path_idx = min(e.path_idx, len(lane) - 1)
        elif event == "surprise_boss":
            lane = random.choice(lanes)
            enemies.append(Enemy(lane, "boss", state["wave"]))
        elif event == "freeze_all":
            for e in enemies:
                if e.alive:
                    e.slow_timer = 150
                    e.slow_factor = 0.1
            engine.particles.explode(WIDTH // 2, HEIGHT // 2, BLUE, ExplosionType.SHOCKWAVE, 2.0)
        elif event == "MEGA_EXPLOSION":
            for _ in range(15):
                ex = random.randint(100, WIDTH - 100)
                ey = random.randint(100, HEIGHT - 200)
                etype = random.choice(list(ExplosionType))
                color = random.choice([RED, ORANGE, YELLOW, MAGENTA, CYAN])
                engine.particles.explode(ex, ey, color, etype, random.uniform(0.8, 2.0))
            for e in enemies:
                if e.alive:
                    e.take_damage(50)
            add_shake(20)
        elif event == "gravity_flip":
            engine.chaos.active = True
            engine.chaos.mode = random.choice(CHAOS_MODES)

        add_shake(6)

    def draw(self, surface):
        if self.event_text and self.event_duration > 0:
            engine.ui.text_centered(surface, self.event_text,
                                    WIDTH // 2, 90, MAGENTA, engine.ui.font_large)


# === Wave Manager ===
class WaveManager:
    def __init__(self):
        self.wave = 0
        self.spawns = []
        self.spawn_timer = 0
        self.between_waves = True
        self.pause_timer = 180

    def start_wave(self, n):
        self.wave = n
        self.between_waves = False
        self.spawns = self.gen_spawns()
        self.spawn_timer = 0

    def gen_spawns(self):
        w = self.wave
        spawns = []
        spawns += ["normal"] * (5 + w * 3)
        if w >= 2:
            spawns += ["fast"] * min(w * 2, 12)
        if w >= 3:
            spawns += ["swarm"] * min(w * 3, 25)
        if w >= 4:
            spawns += ["tank"] * min(w - 3, 6)
        if w >= 5:
            spawns += ["healer"] * min(w - 4, 3)
            spawns += ["exploder"] * min(w - 4, 4)
        if w >= 6:
            spawns += ["shielded"] * min(w - 5, 5)
        if w >= 7:
            spawns += ["ghost"] * min(w - 6, 4)
        if w % 5 == 0:
            spawns += ["boss"] * (w // 5)
        random.shuffle(spawns)
        return spawns

    def update(self, enemies, dt):
        if self.between_waves:
            self.pause_timer -= dt
            if self.pause_timer <= 0:
                self.start_wave(self.wave + 1)
            return

        if self.spawns:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                etype = self.spawns.pop(0)
                lane = random.choice(lanes)
                enemies.append(Enemy(lane, etype, self.wave))
                self.spawn_timer = max(6, 28 - self.wave * 1.5)

        if not self.spawns and not any(e.alive for e in enemies):
            self.between_waves = True
            self.pause_timer = 180


# === Draw Helpers ===
def draw_paths(surface):
    for lane in lanes:
        for i in range(len(lane) - 1):
            p1 = (int(lane[i].x), int(lane[i].y))
            p2 = (int(lane[i + 1].x), int(lane[i + 1].y))
            pygame.draw.line(surface, (22, 22, 32), p1, p2, 10)
            pygame.draw.line(surface, (35, 35, 50), p1, p2, 2)


def draw_shop(surface, gold, selected_tower_obj):
    panel_y = HEIGHT - 95
    pygame.draw.rect(surface, (20, 20, 28), (0, panel_y, WIDTH, 95))
    pygame.draw.line(surface, (50, 50, 65), (0, panel_y), (WIDTH, panel_y), 2)

    x = 10
    idx = 1
    for key, data in TOWER_DATA.items():
        sel = (key == shop_selected)
        box_c = data["color"] if sel else (50, 50, 60)
        pygame.draw.rect(surface, box_c, (x, panel_y + 8, 75, 78), 2 if not sel else 0)
        if sel:
            pygame.draw.rect(surface, (18, 18, 25), (x + 2, panel_y + 10, 71, 74))

        engine.ui.text(surface, data["name"], x + 4, panel_y + 12, data["color"], engine.ui.font_small)
        cost_col = GOLD if gold >= data["cost"] else RED
        engine.ui.text(surface, f"${data['cost']}", x + 4, panel_y + 28, cost_col, engine.ui.font_small)
        engine.ui.text(surface, data["desc"][:10], x + 4, panel_y + 44, (120, 120, 120), engine.ui.font_small)
        engine.ui.text(surface, f"[{idx}]", x + 55, panel_y + 65, (80, 80, 80), engine.ui.font_small)
        x += 82
        idx += 1

    if selected_tower_obj:
        ix = x + 10
        iy = panel_y + 10
        t = selected_tower_obj
        engine.ui.text(surface, f"{TOWER_DATA[t.tower_type]['name']} Lv{t.level}", ix, iy, WHITE)
        engine.ui.text(surface, f"DMG:{t.damage} SPD:{t.fire_rate} RNG:{t.range}", ix, iy + 18, (180, 180, 180), engine.ui.font_small)
        cost = t.get_upgrade_cost()
        if cost:
            c = GOLD if gold >= cost else RED
            engine.ui.text(surface, f"Upgrade: ${cost} [U]", ix, iy + 36, c, engine.ui.font_small)
        else:
            engine.ui.text(surface, "MAX LEVEL", ix, iy + 36, GOLD, engine.ui.font_small)
        engine.ui.text(surface, f"Sell [X]: ${TOWER_DATA[t.tower_type]['cost'] // 2}", ix, iy + 54, (150, 150, 150), engine.ui.font_small)


def draw_hud(surface, state, hero, wave_mgr, game_chaos):
    engine.ui.text(surface, f"${state['gold']}", 15, 12, GOLD, engine.ui.font_large)
    engine.ui.text(surface, f"+{economy.gold_per_sec}/s", 15, 40, (180, 150, 50), engine.ui.font_small)
    engine.ui.text(surface, f"Score: {int(state['score'])}", 15, 58, WHITE, engine.ui.font_med)

    engine.ui.text_centered(surface, f"WAVE {wave_mgr.wave}", WIDTH // 2, 20, CYAN, engine.ui.font_large)
    if wave_mgr.between_waves:
        secs = max(0, int(wave_mgr.pause_timer / 60))
        engine.ui.text_centered(surface, f"Next: {secs}s [SPACE]", WIDTH // 2, 45,
                                (120, 120, 120), engine.ui.font_small)

    engine.ui.text(surface, f"Hero Lv{hero.level} | ATK:{hero.attack_damage} | Kills:{hero.kills}",
                   WIDTH - 280, 12, CYAN, engine.ui.font_small)
    xp_pct = hero.xp / hero.xp_to_level
    engine.ui.progress_bar(surface, WIDTH - 280, 30, 150, 8, xp_pct, GOLD)

    abilities = [
        ("Q", hero.q_cd, hero.q_max, CYAN),
        ("W", hero.w_cd, hero.w_max, GOLD),
        ("E", hero.e_cd, hero.e_max, RED),
        ("R", hero.r_cd, hero.r_max, MAGENTA),
    ]
    ax = WIDTH - 280
    for name, cd, mx, col in abilities:
        fill = 1.0 - cd / mx if mx > 0 else 1.0
        engine.ui.cooldown_icon(surface, ax, 45, 30, fill, col, name)
        ax += 38

    game_chaos.draw(surface)
    engine.ui.text(surface, f"Particles: {engine.particles.count}", WIDTH - 130, HEIGHT - 110,
                   (60, 60, 60), engine.ui.font_small)


def draw_game_over(surface, state, wave_mgr, hero):
    engine.ui.overlay(surface, 180)
    engine.ui.text_centered(surface, "BASE DESTROYED", WIDTH // 2, HEIGHT // 3 - 30, RED, engine.ui.font_huge)
    lines = [
        f"Score: {int(state['score'])}",
        f"Wave: {wave_mgr.wave}",
        f"Hero Lv{hero.level} — {hero.kills} kills",
        f"Towers: {len(towers)}",
        "",
        "R to restart",
    ]
    y = HEIGHT // 3 + 40
    for line in lines:
        engine.ui.text_centered(surface, line, WIDTH // 2, y, WHITE, engine.ui.font_med)
        y += 32


# === Game State Init ===
def init_game():
    global towers, enemies, projectiles, damage_numbers
    global hero, base, wave_mgr, game_chaos, economy
    global state, selected_tower, shop_selected, placing, game_over

    regenerate_lanes()
    towers = []
    enemies = []
    projectiles = []
    damage_numbers = []
    engine.particles.particles.clear()

    hero = Hero()
    base = Base()
    wave_mgr = WaveManager()
    game_chaos = GameChaos()
    economy = Economy()
    selected_tower = None
    shop_selected = "arrow"
    placing = False
    game_over = False

    state = {
        "gold": 200,
        "score": 0,
        "wave": 0,
    }


init_game()

# === MAIN LOOP ===
while engine.running:
    surface = engine.begin_frame()
    surface.fill(BG_COLOR)
    keys = pygame.key.get_pressed()
    mouse_pos = engine.mouse_logical()

    events = engine.process_events()
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and game_over:
                init_game()
                continue

            if event.key == pygame.K_SPACE and wave_mgr.between_waves:
                wave_mgr.start_wave(wave_mgr.wave + 1)
                state["wave"] = wave_mgr.wave

            tower_keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                          pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8]
            tower_names = list(TOWER_DATA.keys())
            for i, tk in enumerate(tower_keys):
                if event.key == tk and i < len(tower_names):
                    shop_selected = tower_names[i]
                    placing = True

            if event.key == pygame.K_u and selected_tower:
                cost = selected_tower.get_upgrade_cost()
                if cost and state["gold"] >= cost:
                    state["gold"] -= cost
                    selected_tower.upgrade()

            if event.key == pygame.K_x and selected_tower:
                refund = TOWER_DATA[selected_tower.tower_type]["cost"] // 2
                state["gold"] += refund
                towers.remove(selected_tower)
                selected_tower = None

            if event.key == pygame.K_ESCAPE:
                placing = False
                selected_tower = None

            if event.key == pygame.K_q:
                hero.ability_q(enemies)
            if event.key == pygame.K_t:
                hero.ability_w(towers)
            if event.key == pygame.K_e:
                hero.ability_e(enemies)
            if event.key == pygame.K_f:
                hero.ability_r(enemies)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if mouse_pos.y > HEIGHT - 95:
                    x = 10
                    for key in TOWER_DATA:
                        if x <= mouse_pos.x <= x + 75:
                            shop_selected = key
                            placing = True
                            break
                        x += 82
                elif placing:
                    cost = TOWER_DATA[shop_selected]["cost"]
                    if state["gold"] >= cost:
                        can = all((t.pos - mouse_pos).length() > 40 for t in towers)
                        if can and mouse_pos.y < HEIGHT - 95:
                            state["gold"] -= cost
                            towers.append(Tower(mouse_pos.x, mouse_pos.y, shop_selected))
                            engine.particles.explode(mouse_pos.x, mouse_pos.y,
                                                     TOWER_DATA[shop_selected]["color"],
                                                     ExplosionType.CONFETTI, 0.6)
                            placing = False
                else:
                    selected_tower = None
                    for t in towers:
                        if (t.pos - mouse_pos).length() < 25:
                            selected_tower = t
                            break

            elif event.button == 3:
                hero.right_click(mouse_pos, enemies, projectiles)

    if game_over:
        draw_paths(surface)
        for t in towers:
            t.draw(surface)
        base.draw(surface)
        draw_game_over(surface, state, wave_mgr, hero)
        engine.end_frame()
        continue

    # === UPDATE ===
    dt = engine.dt

    hero.update(keys, enemies, projectiles, dt)

    fire_mult = 1.8 if hero.rally_active > 0 else 1.0
    for t in towers:
        t.update(enemies, projectiles, dt, fire_mult)

    wave_mgr.update(enemies, dt)
    state["wave"] = wave_mgr.wave

    for e in enemies:
        reached = e.update(enemies, dt)
        if reached:
            base.take_damage()
            if base.hp <= 0:
                game_over = True
                engine.particles.chain_explosion(base.pos.x, base.pos.y, RED, 200, 12, 3.0)
                add_shake(25)

    for p in projectiles:
        p.update(enemies, dt)
    projectiles[:] = [p for p in projectiles if p.alive]

    for e in enemies:
        if not e.alive and not e._counted:
            e._counted = True
            state["gold"] += e.gold_value
            state["score"] += e.score_value
            hero.gain_xp(e.score_value)
            hero.kills += 1
            economy.gold_per_sec = 2 + hero.kills // 15

    enemies[:] = [e for e in enemies if e.alive]

    economy.update(state, dt)
    game_chaos.update(state, enemies, towers, dt)
    engine.particles.update(dt)

    for d in damage_numbers:
        d.update(dt)
    damage_numbers[:] = [d for d in damage_numbers if d.life > 0]

    # === DRAW ===
    draw_paths(surface)

    if placing:
        data = TOWER_DATA[shop_selected]
        pygame.draw.circle(surface, data["color"], (int(mouse_pos.x), int(mouse_pos.y)), data["range"], 1)
        pygame.draw.circle(surface, data["color"], (int(mouse_pos.x), int(mouse_pos.y)), 18, 2)

    for t in towers:
        t.draw(surface, t is selected_tower)

    for e in enemies:
        e.draw(surface)

    for p in projectiles:
        p.draw(surface)

    hero.draw(surface)
    base.draw(surface)
    engine.particles.draw(surface)

    for d in damage_numbers:
        d.draw(surface)

    draw_hud(surface, state, hero, wave_mgr, game_chaos)
    draw_shop(surface, state["gold"], selected_tower)

    engine.end_frame()

engine.quit()
