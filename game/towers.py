import pygame
import math
import random
from game import engine
from game.constants import *
from commons.chaos_engine import ExplosionType, add_shake, Trail, SoundType

TOWER_DATA = {
    "arrow": {"name": "Arrow", "cost": 50, "dmg": 18, "range": 160, "rate": 25, "color": CYAN,
              "desc": "Fast single", "upgrades": [80, 130, 220]},
    "cannon": {"name": "Cannon", "cost": 100, "dmg": 50, "range": 130, "rate": 55, "color": ORANGE,
               "desc": "Splash AOE", "upgrades": [150, 260, 420]},
    "frost": {"name": "Frost", "cost": 75, "dmg": 10, "range": 140, "rate": 22, "color": BLUE,
              "desc": "Slows enemies", "upgrades": [110, 190, 320]},
    "lightning": {"name": "Lightning", "cost": 130, "dmg": 28, "range": 150, "rate": 40, "color": YELLOW,
                  "desc": "Chain 3+", "upgrades": [200, 340, 550]},
    "sniper": {"name": "Sniper", "cost": 160, "dmg": 120, "range": 320, "rate": 85, "color": WHITE,
               "desc": "Massive hit", "upgrades": [270, 430, 700]},
    "chaos": {"name": "Chaos", "cost": 200, "dmg": 35, "range": 170, "rate": 35, "color": MAGENTA,
              "desc": "Random FX", "upgrades": [320, 520, 850]},
    "flame": {"name": "Flame", "cost": 110, "dmg": 5, "range": 100, "rate": 5, "color": (255, 120, 20),
              "desc": "Burn DOT", "upgrades": [170, 280, 450]},
    "missile": {"name": "Missile", "cost": 180, "dmg": 80, "range": 250, "rate": 75, "color": PINK,
                "desc": "Homing boom", "upgrades": [280, 460, 750]},
    "laser": {"name": "Laser", "cost": 200, "dmg": 3, "range": 200, "rate": 1, "color": (255, 50, 50),
              "desc": "Beam ramp", "upgrades": [300, 500, 800]},
    "tesla": {"name": "Tesla", "cost": 175, "dmg": 15, "range": 120, "rate": 30, "color": (200, 200, 255),
              "desc": "AOE aura", "upgrades": [260, 420, 680]},
    "necro": {"name": "Necro", "cost": 220, "dmg": 20, "range": 160, "rate": 40, "color": (100, 200, 100),
              "desc": "Raise dead", "upgrades": [340, 560, 900]},
    "vortex": {"name": "Vortex", "cost": 150, "dmg": 0, "range": 130, "rate": 1, "color": (150, 50, 200),
               "desc": "Pull+slow", "upgrades": [230, 380, 620]},
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

        if self.pos.x < -100 or self.pos.x > engine.width + 100 or self.pos.y < -100 or self.pos.y > engine.height + 100:
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
            engine.particles.explode(self.target.pos.x, self.target.pos.y, self.color,
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


class GhostAlly:
    """Friendly ghost spawned by Necro tower. Chases and damages enemies."""

    def __init__(self, x, y, damage, duration=300):
        self.pos = pygame.Vector2(x, y)
        self.damage = damage
        self.speed = 3.0
        self.radius = 8
        self.alive = True
        self.life = duration
        self.attack_timer = 0
        self.attack_rate = 30
        self.target = None
        self.age = 0

    def update(self, enemies, dt):
        if not self.alive:
            return
        self.life -= dt
        self.age += dt
        if self.life <= 0:
            self.alive = False
            engine.particles.emit(self.pos.x, self.pos.y, (100, 200, 100), 6, speed=2)
            return

        # Find target
        best = None
        best_dist = 200
        for e in enemies:
            if e.alive:
                d = (e.pos - self.pos).length()
                if d < best_dist:
                    best = e
                    best_dist = d
        self.target = best

        if self.target:
            diff = self.target.pos - self.pos
            if diff.length() > 5:
                self.pos += diff.normalize() * self.speed * dt

            # Attack
            self.attack_timer -= dt
            if self.attack_timer <= 0 and (self.target.pos - self.pos).length() < 30:
                self.target.take_damage(self.damage)
                self.attack_timer = self.attack_rate
                engine.particles.emit(self.target.pos.x, self.target.pos.y, (100, 200, 100), 3, speed=2)

    def draw(self, surface):
        if not self.alive:
            return
        alpha = min(1.0, self.life / 60)
        color = (int(100 * alpha), int(200 * alpha), int(100 * alpha))
        pos = (int(self.pos.x), int(self.pos.y))
        # Ghostly wobble
        wobble = math.sin(self.age * 0.1) * 2
        pygame.draw.circle(surface, color, (pos[0], pos[1] + int(wobble)), self.radius)
        pygame.draw.circle(surface, (150, 255, 150), (pos[0], pos[1] + int(wobble)), self.radius, 1)


class Tower:
    def __init__(self, x, y, tower_type="arrow"):
        self.pos = pygame.Vector2(x, y)
        self.tower_type = tower_type
        self.level = 1
        self.fire_timer = 0
        self.target = None
        self.angle = 0
        self.kills = 0

        data = TOWER_DATA[tower_type]
        self.damage = data["dmg"]
        self.range = data["range"]
        self.fire_rate = data["rate"]
        self.color = data["color"]

        # Animation
        self.anim_flash = 0
        self.recoil = 0
        self.flame_stream = []
        self.lightning_arcs = []

        # Laser state
        self.beam_target = None
        self.beam_damage_ramp = 0

        # Necro state
        self.ghost_allies = []

    def get_upgrade_cost(self):
        data = TOWER_DATA[self.tower_type]
        if self.level - 1 < len(data["upgrades"]):
            return data["upgrades"][self.level - 1]
        return None

    def upgrade(self):
        self.level += 1
        self.damage = int(self.damage * 1.6)
        self.range = int(self.range * 1.1)
        self.fire_rate = max(1, int(self.fire_rate * 0.82))
        engine.particles.explode(self.pos.x, self.pos.y, GOLD, ExplosionType.CONFETTI, 0.8)
        engine.audio.play(SoundType.UPGRADE)
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

    def update(self, enemies, projectiles_list, dt, fire_rate_mult=1.0, damage_mult=1.0):
        self.find_target(enemies)

        # Smooth rotation
        if self.target:
            diff = self.target.pos - self.pos
            target_angle = math.atan2(diff.y, diff.x)
            angle_diff = target_angle - self.angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            self.angle += angle_diff * 0.15 * dt

        # Type-specific continuous updates
        if self.tower_type == "laser":
            self._update_laser(enemies, dt, damage_mult)
        elif self.tower_type == "tesla":
            self._update_tesla(enemies, dt, fire_rate_mult, damage_mult)
        elif self.tower_type == "vortex":
            self._update_vortex(enemies, dt)
        else:
            # Standard projectile towers
            self.fire_timer -= dt * fire_rate_mult
            if self.target and self.fire_timer <= 0:
                self.fire_timer = self.fire_rate
                self.shoot(projectiles_list, enemies, damage_mult)
                self.anim_flash = 8

        # Decay animations
        if self.anim_flash > 0:
            self.anim_flash -= dt
        if self.recoil > 0:
            self.recoil *= 0.82
        self.lightning_arcs = [(a, b, life - dt) for a, b, life in self.lightning_arcs if life > 0]

        # Flame stream
        if self.tower_type == "flame" and self.target and self.target.alive:
            if (self.target.pos - self.pos).length() <= self.range:
                self._update_flame_stream()
            else:
                self.flame_stream = []
        elif self.tower_type != "flame":
            self.flame_stream = []

        # Necro ghosts
        for ghost in self.ghost_allies:
            ghost.update(enemies, dt)
        self.ghost_allies = [g for g in self.ghost_allies if g.alive]

    def _update_laser(self, enemies, dt, damage_mult):
        if self.target and self.target.alive:
            dist = (self.target.pos - self.pos).length()
            if dist <= self.range:
                if self.beam_target is self.target:
                    self.beam_damage_ramp = min(5.0, self.beam_damage_ramp + 0.02 * dt)
                else:
                    self.beam_target = self.target
                    self.beam_damage_ramp = 1.0
                dmg = self.damage * self.beam_damage_ramp * damage_mult * dt
                self.target.take_damage(dmg)
                if random.random() < 0.05:
                    engine.particles.emit(self.target.pos.x, self.target.pos.y, (255, 50, 50), 2, speed=2)
            else:
                self.beam_damage_ramp = max(1.0, self.beam_damage_ramp - 0.05 * dt)
        else:
            self.beam_target = None
            self.beam_damage_ramp = max(1.0, self.beam_damage_ramp - 0.1 * dt)

    def _update_tesla(self, enemies, dt, fire_rate_mult, damage_mult):
        self.fire_timer -= dt * fire_rate_mult
        if self.fire_timer <= 0:
            self.fire_timer = self.fire_rate
            hit_any = False
            for e in enemies:
                if e.alive and (e.pos - self.pos).length() <= self.range:
                    e.take_damage(self.damage * damage_mult)
                    self.lightning_arcs.append((pygame.Vector2(self.pos), pygame.Vector2(e.pos), 6))
                    hit_any = True
            if hit_any:
                engine.audio.play(SoundType.LIGHTNING, 0.3)
                engine.particles.emit(self.pos.x, self.pos.y, (200, 200, 255), 5, speed=4, glow=True)

    def _update_vortex(self, enemies, dt):
        for e in enemies:
            if not e.alive:
                continue
            diff = self.pos - e.pos
            dist = diff.length()
            if dist <= self.range and dist > 10:
                # Pull toward tower
                pull_force = 0.5 * dt * (1 - dist / self.range)
                e.pos += diff.normalize() * pull_force
                # Slow
                e.slow_timer = max(e.slow_timer, 30)
                e.slow_factor = 0.5
        # Visual
        if random.random() < 0.1:
            a = random.uniform(0, math.pi * 2)
            r = self.range
            engine.particles.emit(
                self.pos.x + math.cos(a) * r, self.pos.y + math.sin(a) * r,
                (150, 50, 200), 1, speed=1, angle=a + math.pi, spread=0.3, decay=0.03
            )

    def _update_flame_stream(self):
        start = self.pos + pygame.Vector2(math.cos(self.angle), math.sin(self.angle)) * 28
        end = self.target.pos
        self.flame_stream = []
        for i in range(10):
            t = i / 9
            px = start.x + (end.x - start.x) * t + random.uniform(-8, 8) * t
            py = start.y + (end.y - start.y) * t + random.uniform(-8, 8) * t
            self.flame_stream.append((px, py))

    def shoot(self, projectiles_list, enemies, damage_mult=1.0):
        if not self.target:
            return
        x, y = self.pos.x, self.pos.y
        dmg = self.damage * damage_mult

        _sounds = {
            "arrow": SoundType.SHOOT, "cannon": SoundType.EXPLOSION,
            "frost": SoundType.FROST, "lightning": SoundType.LIGHTNING,
            "sniper": SoundType.LASER, "chaos": SoundType.CHAOS_EVENT,
            "flame": SoundType.FLAME, "missile": SoundType.MISSILE_LAUNCH,
            "necro": SoundType.SHOOT,
        }
        engine.audio.play(_sounds.get(self.tower_type, SoundType.SHOOT), 0.35)

        if self.tower_type == "arrow":
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=12, color=self.color))
            engine.particles.emit(x + math.cos(self.angle) * 25, y + math.sin(self.angle) * 25,
                                  CYAN, 4, speed=5, spread=0.4, angle=self.angle)

        elif self.tower_type == "cannon":
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=8, color=self.color,
                                               splash=70, explosion_type=ExplosionType.BURST))
            self.recoil = 7
            engine.particles.emit(x + math.cos(self.angle) * 25, y + math.sin(self.angle) * 25,
                                  ORANGE, 10, speed=6, spread=0.6, angle=self.angle, radius=4)
            add_shake(2)

        elif self.tower_type == "frost":
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=10, color=self.color, slow=0.35))
            engine.particles.emit(x + math.cos(self.angle) * 20, y + math.sin(self.angle) * 20,
                                  (150, 200, 255), 6, speed=4, spread=0.8, angle=self.angle, radius=2)

        elif self.tower_type == "lightning":
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=18, color=self.color, chain=3 + self.level))
            self.lightning_arcs.append((pygame.Vector2(self.pos), pygame.Vector2(self.target.pos), 12))
            engine.particles.emit(x, y, YELLOW, 8, speed=5, radius=3, glow=True)

        elif self.tower_type == "sniper":
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=25, color=self.color,
                                               explosion_type=ExplosionType.SPARKS))
            self.recoil = 9
            self.lightning_arcs.append((pygame.Vector2(self.pos), pygame.Vector2(self.target.pos), 5))
            engine.particles.emit(x + math.cos(self.angle) * 28, y + math.sin(self.angle) * 28,
                                  WHITE, 8, speed=8, spread=0.3, angle=self.angle, radius=3, glow=True)
            add_shake(3)

        elif self.tower_type == "chaos":
            effects = [
                {"splash": 90, "explosion_type": ExplosionType.SHOCKWAVE},
                {"chain": 6}, {"pierce": 4},
                {"slow": 0.15, "splash": 60},
                {"burn": 3, "explosion_type": ExplosionType.FIREWORK},
                {"splash": 120, "explosion_type": ExplosionType.NOVA},
            ]
            effect = random.choice(effects)
            proj_dmg = dmg * random.uniform(0.8, 3.0)
            projectiles_list.append(Projectile(x, y, self.target, proj_dmg, speed=10, color=MAGENTA, **effect))
            for _ in range(5):
                c = random.choice([MAGENTA, PURPLE, CYAN, YELLOW, RED, PINK])
                engine.particles.emit(x, y, c, 2, speed=5, radius=3)
            if random.random() < 0.3:
                add_shake(4)

        elif self.tower_type == "flame":
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=8, color=self.color, burn=2 + self.level))
            engine.particles.emit(x + math.cos(self.angle) * 20, y + math.sin(self.angle) * 20,
                                  (255, random.randint(60, 180), 0), 6, speed=4,
                                  spread=0.5, angle=self.angle, radius=4, gravity=0.03)

        elif self.tower_type == "missile":
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=6, color=self.color,
                                               splash=100, explosion_type=ExplosionType.NOVA))
            self.recoil = 5
            engine.particles.emit(x, y, (100, 100, 100), 10, speed=3, radius=5, gravity=0.02, decay=0.02)
            add_shake(2)

        elif self.tower_type == "necro":
            projectiles_list.append(Projectile(x, y, self.target, dmg, speed=10, color=self.color))
            engine.particles.emit(x, y, (100, 200, 100), 4, speed=3)

    def on_enemy_killed(self, enemy):
        """Called when any enemy dies in this tower's range. For necro."""
        if self.tower_type == "necro":
            dist = (enemy.pos - self.pos).length()
            if dist <= self.range and len(self.ghost_allies) < 3 + self.level:
                ghost = GhostAlly(enemy.pos.x, enemy.pos.y, self.damage * 0.5, 300 + self.level * 60)
                self.ghost_allies.append(ghost)
                engine.particles.explode(enemy.pos.x, enemy.pos.y, (100, 200, 100), ExplosionType.RING, 0.5)

    def draw(self, surface, selected=False):
        pos = (int(self.pos.x), int(self.pos.y))
        base_r = 18 + self.level * 2

        if selected:
            pygame.draw.circle(surface, (50, 50, 70), pos, self.range, 1)

        # Dispatch to unique sprite
        draw_fn = getattr(self, f"_draw_{self.tower_type}", None)
        if draw_fn:
            draw_fn(surface, pos, base_r)
        else:
            pygame.draw.circle(surface, DARK_GRAY, pos, base_r)
            pygame.draw.circle(surface, self.color, pos, base_r, 2)

        # Flame stream
        if self.flame_stream and len(self.flame_stream) > 1:
            for i in range(1, len(self.flame_stream)):
                t = i / len(self.flame_stream)
                w = max(1, int(7 * (1 - t * 0.4)))
                fc = (255, int(200 - 160 * t), int(50 * (1 - t)))
                p1 = (int(self.flame_stream[i - 1][0]), int(self.flame_stream[i - 1][1]))
                p2 = (int(self.flame_stream[i][0]), int(self.flame_stream[i][1]))
                pygame.draw.line(surface, fc, p1, p2, w)

        # Lightning arcs
        for start, end, life in self.lightning_arcs:
            alpha = min(1.0, life / 6)
            points = [start]
            for seg_i in range(1, 8):
                t = seg_i / 8
                mid = start + (end - start) * t
                mid = pygame.Vector2(mid.x + random.uniform(-12, 12) * alpha,
                                     mid.y + random.uniform(-12, 12) * alpha)
                points.append(mid)
            points.append(end)
            w = max(1, int(3 * alpha))
            color = (int(255 * alpha), int(220 * alpha), int(50 * alpha))
            for j in range(len(points) - 1):
                p1 = (int(points[j].x), int(points[j].y))
                p2 = (int(points[j + 1].x), int(points[j + 1].y))
                pygame.draw.line(surface, color, p1, p2, w)

        # Muzzle flash
        if self.anim_flash > 0:
            alpha = self.anim_flash / 8
            fr = int(12 * alpha)
            fx = int(self.pos.x + math.cos(self.angle) * 28)
            fy = int(self.pos.y + math.sin(self.angle) * 28)
            pygame.draw.circle(surface, self.color, (fx, fy), fr)

        # Level stars
        if self.level > 1:
            for i in range(min(self.level - 1, 5)):
                sx = int(self.pos.x - 8 + i * 8)
                sy = int(self.pos.y + base_r + 6)
                pygame.draw.circle(surface, GOLD, (sx, sy), 3)

        # Ghost allies
        for ghost in self.ghost_allies:
            ghost.draw(surface)

    # === UNIQUE TOWER SPRITES ===

    def _draw_arrow(self, surface, pos, r):
        for i in range(6):
            a1 = math.pi / 3 * i
            a2 = math.pi / 3 * (i + 1)
            p1 = (int(self.pos.x + math.cos(a1) * r), int(self.pos.y + math.sin(a1) * r))
            p2 = (int(self.pos.x + math.cos(a2) * r), int(self.pos.y + math.sin(a2) * r))
            pygame.draw.line(surface, CYAN, p1, p2, 2)
        pygame.draw.circle(surface, (20, 40, 50), pos, r - 4)
        pygame.draw.circle(surface, CYAN, pos, 5)
        bl = r + 14
        bx = self.pos.x + math.cos(self.angle) * bl
        by = self.pos.y + math.sin(self.angle) * bl
        pygame.draw.line(surface, CYAN, pos, (int(bx), int(by)), 2)
        tip = 7
        tx = bx + math.cos(self.angle) * tip
        ty = by + math.sin(self.angle) * tip
        lx = bx + math.cos(self.angle + 2.5) * tip
        ly = by + math.sin(self.angle + 2.5) * tip
        rx = bx + math.cos(self.angle - 2.5) * tip
        ry = by + math.sin(self.angle - 2.5) * tip
        pygame.draw.polygon(surface, CYAN, [(int(tx), int(ty)), (int(lx), int(ly)), (int(rx), int(ry))])

    def _draw_cannon(self, surface, pos, r):
        half = r
        pts = [(int(self.pos.x - half), int(self.pos.y - half)), (int(self.pos.x + half), int(self.pos.y - half)),
               (int(self.pos.x + half), int(self.pos.y + half)), (int(self.pos.x - half), int(self.pos.y + half))]
        pygame.draw.polygon(surface, (50, 35, 20), pts)
        pygame.draw.polygon(surface, ORANGE, pts, 2)
        bl = r + 16 - self.recoil
        bx = self.pos.x + math.cos(self.angle) * bl
        by = self.pos.y + math.sin(self.angle) * bl
        pygame.draw.line(surface, ORANGE, (int(self.pos.x + math.cos(self.angle) * r * 0.5),
                         int(self.pos.y + math.sin(self.angle) * r * 0.5)), (int(bx), int(by)), 6)
        pygame.draw.line(surface, (200, 120, 30), (int(self.pos.x + math.cos(self.angle) * r * 0.5),
                         int(self.pos.y + math.sin(self.angle) * r * 0.5)), (int(bx), int(by)), 3)
        px = math.cos(self.angle + math.pi / 2) * 5
        py_o = math.sin(self.angle + math.pi / 2) * 5
        pygame.draw.line(surface, ORANGE, (int(bx - px), int(by - py_o)), (int(bx + px), int(by + py_o)), 3)

    def _draw_frost(self, surface, pos, r):
        rot = engine.frame_count * 0.005
        for i in range(8):
            a1 = math.pi / 4 * i + rot
            a2 = math.pi / 4 * (i + 1) + rot
            p1 = (int(self.pos.x + math.cos(a1) * r), int(self.pos.y + math.sin(a1) * r))
            p2 = (int(self.pos.x + math.cos(a2) * r), int(self.pos.y + math.sin(a2) * r))
            pygame.draw.line(surface, (100, 150, 255), p1, p2, 2)
        pygame.draw.circle(surface, (15, 25, 50), pos, r - 4)
        for i in range(4):
            a = math.pi / 2 * i + engine.frame_count * 0.02
            cx = int(self.pos.x + math.cos(a) * 7)
            cy = int(self.pos.y + math.sin(a) * 7)
            pygame.draw.circle(surface, (150, 200, 255), (cx, cy), 3)
        pygame.draw.circle(surface, BLUE, pos, 4)
        bx = self.pos.x + math.cos(self.angle) * (r + 10)
        by = self.pos.y + math.sin(self.angle) * (r + 10)
        pygame.draw.line(surface, (100, 180, 255), pos, (int(bx), int(by)), 3)

    def _draw_lightning(self, surface, pos, r):
        pygame.draw.circle(surface, (30, 30, 20), pos, r)
        pygame.draw.circle(surface, YELLOW, pos, r, 2)
        orb_pulse = 1 + math.sin(engine.frame_count * 0.12) * 0.25
        orb_r = int(8 * orb_pulse)
        pygame.draw.circle(surface, YELLOW, pos, orb_r)
        pygame.draw.circle(surface, WHITE, pos, max(2, orb_r - 3))
        for _ in range(3):
            a = random.uniform(0, math.pi * 2)
            sx = int(self.pos.x + math.cos(a) * (r - 2))
            sy = int(self.pos.y + math.sin(a) * (r - 2))
            pygame.draw.line(surface, YELLOW, pos, (sx, sy), 1)
        dx = int(self.pos.x + math.cos(self.angle) * (r + 6))
        dy = int(self.pos.y + math.sin(self.angle) * (r + 6))
        pygame.draw.circle(surface, YELLOW, (dx, dy), 3)

    def _draw_sniper(self, surface, pos, r):
        diamond = [(int(self.pos.x), int(self.pos.y - r)), (int(self.pos.x + r), int(self.pos.y)),
                   (int(self.pos.x), int(self.pos.y + r)), (int(self.pos.x - r), int(self.pos.y))]
        pygame.draw.polygon(surface, (25, 25, 30), diamond)
        pygame.draw.polygon(surface, WHITE, diamond, 2)
        pygame.draw.line(surface, (80, 80, 80), (int(self.pos.x - 6), int(self.pos.y)), (int(self.pos.x + 6), int(self.pos.y)), 1)
        pygame.draw.line(surface, (80, 80, 80), (int(self.pos.x), int(self.pos.y - 6)), (int(self.pos.x), int(self.pos.y + 6)), 1)
        bl = r + 22 - self.recoil
        bx = self.pos.x + math.cos(self.angle) * bl
        by = self.pos.y + math.sin(self.angle) * bl
        pygame.draw.line(surface, WHITE, pos, (int(bx), int(by)), 2)
        pygame.draw.circle(surface, WHITE, (int(bx), int(by)), 2)

    def _draw_chaos(self, surface, pos, r):
        rot = engine.frame_count * 0.03
        for i in range(3):
            a1 = rot + (math.pi * 2 / 3) * i
            a2 = rot + (math.pi * 2 / 3) * (i + 1)
            p1 = (int(self.pos.x + math.cos(a1) * r), int(self.pos.y + math.sin(a1) * r))
            p2 = (int(self.pos.x + math.cos(a2) * r), int(self.pos.y + math.sin(a2) * r))
            pygame.draw.line(surface, [MAGENTA, PURPLE, CYAN][i], p1, p2, 2)
        phase = engine.frame_count * 0.05
        cr = int(128 + 127 * math.sin(phase))
        cg = int(128 + 127 * math.sin(phase + 2))
        cb = int(128 + 127 * math.sin(phase + 4))
        orb_c = (cr, cg, cb)
        pygame.draw.circle(surface, orb_c, pos, 9)
        pygame.draw.circle(surface, WHITE, pos, 5)
        for i in range(3):
            a = engine.frame_count * 0.04 + (math.pi * 2 / 3) * i
            ox = int(self.pos.x + math.cos(a) * (r - 5))
            oy = int(self.pos.y + math.sin(a) * (r - 5))
            pygame.draw.circle(surface, orb_c, (ox, oy), 2)

    def _draw_flame(self, surface, pos, r):
        pygame.draw.circle(surface, (50, 25, 10), pos, r)
        pygame.draw.circle(surface, (255, 120, 20), pos, r, 2)
        for i in range(4):
            a = math.pi / 2 * i + engine.frame_count * 0.01
            vx = int(self.pos.x + math.cos(a) * (r - 5))
            vy = int(self.pos.y + math.sin(a) * (r - 5))
            vc = (255, random.randint(80, 180), 0) if self.target else (100, 40, 10)
            pygame.draw.circle(surface, vc, (vx, vy), 3)
        fp = 1 + math.sin(engine.frame_count * 0.15) * 0.3
        fr = int(7 * fp)
        pygame.draw.circle(surface, (255, 100, 0), pos, fr)
        pygame.draw.circle(surface, (255, 200, 50), pos, max(2, fr - 3))
        nl = r + 10
        nx = self.pos.x + math.cos(self.angle) * nl
        ny = self.pos.y + math.sin(self.angle) * nl
        pygame.draw.line(surface, (200, 80, 0), pos, (int(nx), int(ny)), 4)
        px = math.cos(self.angle + math.pi / 2) * 5
        py_o = math.sin(self.angle + math.pi / 2) * 5
        pygame.draw.line(surface, (255, 120, 20), (int(nx - px), int(ny - py_o)), (int(nx + px), int(ny + py_o)), 3)

    def _draw_missile(self, surface, pos, r):
        for i in range(5):
            a1 = math.pi * 2 / 5 * i - math.pi / 2
            a2 = math.pi * 2 / 5 * (i + 1) - math.pi / 2
            p1 = (int(self.pos.x + math.cos(a1) * r), int(self.pos.y + math.sin(a1) * r))
            p2 = (int(self.pos.x + math.cos(a2) * r), int(self.pos.y + math.sin(a2) * r))
            pygame.draw.line(surface, PINK, p1, p2, 2)
        pygame.draw.circle(surface, (35, 20, 30), pos, r - 4)
        for offset in [-5, 0, 5]:
            px = math.cos(self.angle + math.pi / 2) * offset
            py_o = math.sin(self.angle + math.pi / 2) * offset
            sx = self.pos.x + px
            sy = self.pos.y + py_o
            ex = sx + math.cos(self.angle) * (r + 12 - self.recoil)
            ey = sy + math.sin(self.angle) * (r + 12 - self.recoil)
            pygame.draw.line(surface, PINK, (int(sx), int(sy)), (int(ex), int(ey)), 2)
        pygame.draw.circle(surface, PINK, pos, 4)

    def _draw_laser(self, surface, pos, r):
        # Sleek red base with focusing lens
        pygame.draw.circle(surface, (40, 15, 15), pos, r)
        pygame.draw.circle(surface, (255, 50, 50), pos, r, 2)
        pygame.draw.circle(surface, (255, 100, 100), pos, 6)
        bl = r + 14 - self.recoil
        bx = self.pos.x + math.cos(self.angle) * bl
        by = self.pos.y + math.sin(self.angle) * bl
        pygame.draw.line(surface, (255, 50, 50), pos, (int(bx), int(by)), 2)
        # Beam if active
        if self.beam_target and self.beam_target.alive:
            ramp = min(1.0, self.beam_damage_ramp / 3.0)
            w = max(2, int(5 * ramp))
            color = (255, int(50 + 100 * (1 - ramp)), int(50 * (1 - ramp)))
            pygame.draw.line(surface, color, pos,
                             (int(self.beam_target.pos.x), int(self.beam_target.pos.y)), w)
            pygame.draw.circle(surface, (255, 200, 200),
                               (int(self.beam_target.pos.x), int(self.beam_target.pos.y)), int(5 * ramp))

    def _draw_tesla(self, surface, pos, r):
        pygame.draw.circle(surface, (20, 20, 35), pos, r)
        pygame.draw.circle(surface, (200, 200, 255), pos, r, 2)
        pulse = 1 + math.sin(engine.frame_count * 0.1) * 0.1
        pygame.draw.circle(surface, (60, 60, 100), pos, int(self.range * pulse), 1)
        orb_r = int(8 * (1 + math.sin(engine.frame_count * 0.12) * 0.2))
        pygame.draw.circle(surface, (200, 200, 255), pos, orb_r)
        pygame.draw.circle(surface, WHITE, pos, max(2, orb_r - 3))
        for _ in range(3):
            a = random.uniform(0, math.pi * 2)
            sx = int(self.pos.x + math.cos(a) * (r - 2))
            sy = int(self.pos.y + math.sin(a) * (r - 2))
            pygame.draw.line(surface, (180, 180, 255), pos, (sx, sy), 1)

    def _draw_necro(self, surface, pos, r):
        pygame.draw.circle(surface, (15, 30, 15), pos, r)
        pygame.draw.circle(surface, (100, 200, 100), pos, r, 2)
        # Skull-like face
        pygame.draw.circle(surface, (180, 255, 180), (pos[0] - 4, pos[1] - 2), 3)
        pygame.draw.circle(surface, (180, 255, 180), (pos[0] + 4, pos[1] - 2), 3)
        pygame.draw.line(surface, (100, 200, 100), (pos[0] - 3, pos[1] + 4), (pos[0] + 3, pos[1] + 4), 2)
        # Barrel
        bl = r + 10
        bx = self.pos.x + math.cos(self.angle) * bl
        by = self.pos.y + math.sin(self.angle) * bl
        pygame.draw.line(surface, (100, 200, 100), pos, (int(bx), int(by)), 2)

    def _draw_vortex(self, surface, pos, r):
        pygame.draw.circle(surface, (20, 10, 30), pos, r)
        pygame.draw.circle(surface, (150, 50, 200), pos, r, 2)
        # Spinning spiral arms
        for i in range(4):
            a = engine.frame_count * 0.05 + math.pi / 2 * i
            for seg in range(6):
                t = seg / 6
                r_dist = 8 + (self.range * 0.7) * t
                seg_a = a + t * 2.0
                sx = int(self.pos.x + math.cos(seg_a) * r_dist)
                sy = int(self.pos.y + math.sin(seg_a) * r_dist)
                alpha = 1 - t
                c = (int(150 * alpha), int(50 * alpha), int(200 * alpha))
                pygame.draw.circle(surface, c, (sx, sy), max(1, int(3 * alpha)))
        pygame.draw.circle(surface, (200, 100, 255), pos, 5)
