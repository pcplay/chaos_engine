import pygame
import math
import random
from game import engine
from game.constants import *
from commons.chaos_engine import ExplosionType, add_shake, DamageNumber, SoundType
from game.elites import EliteModifier, BossPhaseManager, roll_elite_affixes, get_wave_scaling, EnemyAI

damage_numbers = []  # shared reference, set from main

ENEMY_STATS = {
    # (base_hp, speed, radius, color, gold, score)
    "normal": (30, 1.5, 12, RED, 5, 10),
    "fast": (20, 3.2, 9, ORANGE, 8, 15),
    "tank": (120, 0.7, 24, DARK_RED, 25, 40),
    "swarm": (10, 2.2, 7, MAGENTA, 2, 5),
    "boss": (600, 0.5, 38, PURPLE, 120, 250),
    "healer": (45, 1.1, 14, GREEN, 18, 25),
    "shielded": (60, 1.0, 16, TEAL, 20, 22),
    "exploder": (25, 2.5, 13, YELLOW, 12, 18),
    "ghost": (35, 1.8, 11, (200, 200, 255), 15, 20),
    "splitter": (50, 1.3, 16, LIME, 15, 20),
    "teleporter": (30, 1.0, 10, VIOLET, 20, 30),
    "berserker": (80, 1.0, 15, (200, 50, 30), 18, 28),
    "summoner": (70, 0.8, 18, (180, 100, 220), 25, 35),
}


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

        hp, spd, rad, col, gold, score = ENEMY_STATS.get(enemy_type, ENEMY_STATS["normal"])

        # Wave scaling
        scaling = get_wave_scaling(wave)
        self.max_hp = int((hp + wave * (10 if enemy_type != "boss" else 80)) * scaling["hp_mult"])
        self.hp = self.max_hp
        self.base_speed = (spd + wave * 0.04) * scaling["speed_mult"]
        self.speed = self.base_speed
        self.radius = rad
        self.color = col
        self.gold_value = int((gold + wave) * scaling["gold_mult"])
        self.score_value = score
        self.shield_hp = (30 + wave * 5) if enemy_type == "shielded" else 0
        self.max_shield = self.shield_hp
        self.heal_timer = 0
        self.phase_timer = 0
        self.teleport_timer = 0
        self.summon_timer = 0
        self.rot = random.uniform(0, math.pi * 2)

        # Elite system
        affixes = roll_elite_affixes(wave, enemy_type)
        self.elite = EliteModifier(affixes)
        if self.elite.is_elite:
            self.max_hp = int(self.max_hp * 1.5)
            self.hp = self.max_hp
            self.gold_value = int(self.gold_value * 2)
            self.score_value = int(self.score_value * 2)

        # Boss phase system
        self.boss_phases = BossPhaseManager()
        if enemy_type == "boss" and wave >= 5:
            self.boss_phases.active = True

    def update(self, enemies_list, dt):
        if not self.alive:
            return False, []
        self.age += dt
        self.rot += 0.02 * dt
        spawned = []

        # Elite modifiers update
        self.elite.update(self, enemies_list, dt)

        # Boss phases
        boss_spawns = self.boss_phases.update(self, enemies_list, self.path, self.wave, dt)
        spawned.extend(boss_spawns)

        speed_mult = 1.0
        if self.slow_timer > 0:
            self.slow_timer -= dt
            speed_mult = self.slow_factor

        # Elite speed modifiers
        speed_mult *= self.elite.modify_speed(1.0)
        # Boss phase speed
        if self.boss_phases.active:
            speed_mult *= self.boss_phases.current_phase["speed_mult"]

        # Ghost phasing
        if self.enemy_type == "ghost":
            self.phase_timer += dt
            if math.sin(self.phase_timer * 0.03) > 0.8:
                speed_mult *= 2.0

        # Berserker — speeds up as HP drops
        if self.enemy_type == "berserker":
            hp_pct = self.hp / self.max_hp
            self.speed = self.base_speed * (1 + (1 - hp_pct) * 2.5)
        else:
            self.speed = self.base_speed

        # Burn damage
        if self.burn_timer > 0:
            self.burn_timer -= dt
            self.hp -= self.burn_dps * dt
            if random.random() < 0.1:
                engine.particles.emit(self.pos.x, self.pos.y, ORANGE, 2, speed=2, radius=2)
            if self.hp <= 0:
                self.die()
                return False, []

        # Movement
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
            return True, []

        # Teleporter — blinks forward
        if self.enemy_type == "teleporter":
            self.teleport_timer += dt
            if self.teleport_timer >= 180:
                self.teleport_timer = 0
                jump = random.randint(15, 25)
                self.path_idx = min(self.path_idx + jump, len(self.path) - 1)
                self.pos = pygame.Vector2(self.path[self.path_idx])
                engine.particles.explode(self.pos.x, self.pos.y, VIOLET, ExplosionType.RING, 0.5)

        # Healer
        if self.enemy_type == "healer":
            self.heal_timer += dt
            if self.heal_timer >= 90:
                self.heal_timer = 0
                for e in enemies_list:
                    if e.alive and e is not self:
                        if (e.pos - self.pos).length() < 100:
                            e.hp = min(e.max_hp, e.hp + e.max_hp * 0.05)

        # Summoner — spawns mini swarm
        if self.enemy_type == "summoner":
            self.summon_timer += dt
            if self.summon_timer >= 300:
                self.summon_timer = 0
                mini = Enemy(self.path, "swarm", self.wave)
                mini.path_idx = self.path_idx
                mini.pos = pygame.Vector2(self.pos)
                spawned.append(mini)
                engine.particles.emit(self.pos.x, self.pos.y, (180, 100, 220), 6, speed=3)

        return False, spawned

    def take_damage(self, dmg, dmg_type="physical"):
        if not self.alive:
            return

        if self.enemy_type == "ghost" and math.sin(self.phase_timer * 0.03) > 0.8:
            engine.particles.emit(self.pos.x, self.pos.y, (200, 200, 255), 5, speed=3)
            return

        # Elite damage modification (armor, dodge, immune)
        dmg = self.elite.modify_damage_taken(dmg, self)
        if dmg <= 0:
            return

        # Boss phase damage reduction
        if self.boss_phases.active:
            dmg = self.boss_phases.modify_damage(dmg)

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
        # VFX hit flash
        flash_color = YELLOW if crit else WHITE
        engine.vfx.flash(self.pos.x, self.pos.y, flash_color, self.radius if crit else 6)
        if self.hp <= 0:
            self.die()

    def die(self):
        self.alive = False
        if self.enemy_type == "boss":
            engine.audio.play(SoundType.EXPLOSION, 1.0)
            engine.particles.chain_explosion(self.pos.x, self.pos.y, self.color, 150, 8, 2.0)
            engine.vfx.shockwave(self.pos.x, self.pos.y, 200)
            engine.vfx.ring(self.pos.x, self.pos.y, self.color, 150)
            engine.vfx.flash(self.pos.x, self.pos.y, WHITE, 30)
            add_shake(20)
        elif self.enemy_type == "exploder":
            engine.audio.play(SoundType.EXPLOSION, 0.8)
            engine.particles.explode(self.pos.x, self.pos.y, YELLOW, ExplosionType.SHOCKWAVE, 1.5)
            add_shake(8)
        elif self.enemy_type == "tank":
            engine.particles.explode(self.pos.x, self.pos.y, self.color, ExplosionType.NOVA, 1.2)
            add_shake(6)
        else:
            etype = random.choice([ExplosionType.BURST, ExplosionType.SPARKS, ExplosionType.FIREWORK])
            engine.particles.explode(self.pos.x, self.pos.y, self.color, etype, 0.8)
            add_shake(2)

    def get_split_spawns(self):
        """For splitter type — returns list of new enemies on death."""
        if self.enemy_type != "splitter":
            return []
        spawns = []
        for _ in range(2):
            mini = Enemy(self.path, "swarm", self.wave)
            mini.path_idx = self.path_idx
            mini.pos = pygame.Vector2(self.pos.x + random.uniform(-10, 10),
                                      self.pos.y + random.uniform(-10, 10))
            mini.max_hp = int(self.max_hp * 0.4)
            mini.hp = mini.max_hp
            spawns.append(mini)
        return spawns

    def draw(self, surface):
        if not self.alive:
            return
        pos = (int(self.pos.x), int(self.pos.y))
        pulse = 1 + math.sin(self.age * 0.08) * 0.08
        r = int(self.radius * pulse)

        # Dispatch to sprite method
        draw_method = getattr(self, f"_draw_{self.enemy_type}", self._draw_default)
        draw_method(surface, pos, r)

        # Status indicators
        if self.slow_timer > 0:
            pygame.draw.circle(surface, BLUE, pos, r + 5, 1)
        if self.burn_timer > 0:
            pygame.draw.circle(surface, ORANGE, pos, r + 3, 1)
        if self.shield_hp > 0:
            pct = self.shield_hp / max(1, self.max_shield)
            pygame.draw.arc(surface, TEAL,
                            (pos[0] - r - 4, pos[1] - r - 4, (r + 4) * 2, (r + 4) * 2),
                            0, math.pi * 2 * pct, 2)

        # Elite indicators
        self.elite.draw_indicators(surface, pos, r)
        # Boss phase indicator
        self.boss_phases.draw(surface, pos, r)

        # HP bar
        bar_w = self.radius * 2.5
        bar_h = 3
        bx = self.pos.x - bar_w / 2
        by = self.pos.y - self.radius - 8
        pct = self.hp / self.max_hp
        pygame.draw.rect(surface, DARK_GRAY, (int(bx), int(by), int(bar_w), bar_h))
        col = GREEN if pct > 0.5 else YELLOW if pct > 0.25 else RED
        pygame.draw.rect(surface, col, (int(bx), int(by), int(bar_w * pct), bar_h))

    # === PROCEDURAL SPRITES ===

    def _draw_default(self, surface, pos, r):
        pygame.draw.circle(surface, self.color, pos, r)

    def _draw_normal(self, surface, pos, r):
        # Pentagon
        pts = []
        for i in range(5):
            a = self.rot + math.pi * 2 / 5 * i
            pts.append((int(self.pos.x + math.cos(a) * r), int(self.pos.y + math.sin(a) * r)))
        pygame.draw.polygon(surface, self.color, pts)
        pygame.draw.polygon(surface, WHITE, pts, 1)

    def _draw_fast(self, surface, pos, r):
        # Elongated diamond (oriented along movement)
        move_angle = 0
        if self.path_idx < len(self.path) - 1:
            diff = self.path[min(self.path_idx + 1, len(self.path) - 1)] - self.pos
            if diff.length() > 0:
                move_angle = math.atan2(diff.y, diff.x)
        pts = [
            (int(self.pos.x + math.cos(move_angle) * r * 1.8), int(self.pos.y + math.sin(move_angle) * r * 1.8)),
            (int(self.pos.x + math.cos(move_angle + math.pi / 2) * r * 0.5), int(self.pos.y + math.sin(move_angle + math.pi / 2) * r * 0.5)),
            (int(self.pos.x + math.cos(move_angle + math.pi) * r * 0.8), int(self.pos.y + math.sin(move_angle + math.pi) * r * 0.8)),
            (int(self.pos.x + math.cos(move_angle - math.pi / 2) * r * 0.5), int(self.pos.y + math.sin(move_angle - math.pi / 2) * r * 0.5)),
        ]
        pygame.draw.polygon(surface, self.color, pts)
        # Speed lines
        for i in range(3):
            lx = int(self.pos.x - math.cos(move_angle) * (r + 5 + i * 6))
            ly = int(self.pos.y - math.sin(move_angle) * (r + 5 + i * 6))
            pygame.draw.line(surface, (150, 80, 20), (lx, ly),
                             (lx - int(math.cos(move_angle) * 8), ly - int(math.sin(move_angle) * 8)), 1)

    def _draw_tank(self, surface, pos, r):
        # Rounded square with armor plates
        rect = pygame.Rect(pos[0] - r, pos[1] - r, r * 2, r * 2)
        pygame.draw.rect(surface, self.color, rect, border_radius=5)
        # Cross-hatch armor
        pygame.draw.line(surface, (100, 40, 40), (pos[0] - r + 3, pos[1]), (pos[0] + r - 3, pos[1]), 2)
        pygame.draw.line(surface, (100, 40, 40), (pos[0], pos[1] - r + 3), (pos[0], pos[1] + r - 3), 2)
        pygame.draw.rect(surface, (200, 80, 80), rect, 2, border_radius=5)

    def _draw_swarm(self, surface, pos, r):
        # 3 tiny triangles clustered
        for i in range(3):
            offset_a = math.pi * 2 / 3 * i + self.rot
            ox = int(self.pos.x + math.cos(offset_a) * r * 0.4)
            oy = int(self.pos.y + math.sin(offset_a) * r * 0.4)
            tri = []
            for j in range(3):
                a = self.rot + math.pi * 2 / 3 * j
                tri.append((int(ox + math.cos(a) * r * 0.5), int(oy + math.sin(a) * r * 0.5)))
            pygame.draw.polygon(surface, self.color, tri)

    def _draw_boss(self, surface, pos, r):
        # Multi-ring mandala
        for ring in range(3):
            ring_r = r - ring * 6
            if ring_r < 3:
                break
            sides = 6 + ring * 2
            rot_offset = self.rot * (1 + ring * 0.5)
            pts = []
            for i in range(sides):
                a = rot_offset + math.pi * 2 / sides * i
                pts.append((int(self.pos.x + math.cos(a) * ring_r),
                            int(self.pos.y + math.sin(a) * ring_r)))
            color_shift = (
                int(self.color[0] * (1 - ring * 0.2)),
                int(self.color[1] * (1 - ring * 0.1)),
                int(min(255, self.color[2] + ring * 30))
            )
            pygame.draw.polygon(surface, color_shift, pts, 2)
        pygame.draw.circle(surface, WHITE, pos, 6)

    def _draw_healer(self, surface, pos, r):
        # Plus/cross shape
        w = r // 3
        pygame.draw.rect(surface, self.color, (pos[0] - w, pos[1] - r, w * 2, r * 2))
        pygame.draw.rect(surface, self.color, (pos[0] - r, pos[1] - w, r * 2, w * 2))
        # Aura pulse
        aura_r = int(100 * (0.5 + 0.5 * math.sin(self.age * 0.05)))
        pygame.draw.circle(surface, (20, 60, 20), pos, aura_r, 1)

    def _draw_shielded(self, surface, pos, r):
        # Octagon with shield segments
        pts = []
        for i in range(8):
            a = math.pi / 4 * i
            pts.append((int(self.pos.x + math.cos(a) * r), int(self.pos.y + math.sin(a) * r)))
        pygame.draw.polygon(surface, self.color, pts)
        # Shield segments (break off visual)
        shield_pct = self.shield_hp / max(1, self.max_shield)
        segments = int(8 * shield_pct)
        for i in range(segments):
            a1 = math.pi / 4 * i
            a2 = math.pi / 4 * (i + 1)
            p1 = (int(self.pos.x + math.cos(a1) * (r + 4)), int(self.pos.y + math.sin(a1) * (r + 4)))
            p2 = (int(self.pos.x + math.cos(a2) * (r + 4)), int(self.pos.y + math.sin(a2) * (r + 4)))
            pygame.draw.line(surface, TEAL, p1, p2, 3)

    def _draw_exploder(self, surface, pos, r):
        # Spiky sun shape
        pts = []
        spikes = 8
        for i in range(spikes * 2):
            a = self.rot + math.pi / spikes * i
            dist = r if i % 2 == 0 else r * 0.5
            pts.append((int(self.pos.x + math.cos(a) * dist), int(self.pos.y + math.sin(a) * dist)))
        pygame.draw.polygon(surface, self.color, pts)
        # Flicker
        if int(self.age) % 20 < 10:
            pygame.draw.circle(surface, WHITE, pos, r // 3)

    def _draw_ghost(self, surface, pos, r):
        # Wispy transparent shape
        phasing = math.sin(self.phase_timer * 0.03) > 0.8
        alpha = 0.3 if phasing else 0.8
        color = tuple(int(c * alpha) for c in self.color)
        # Wavy body
        pts = []
        for i in range(12):
            a = math.pi * 2 / 12 * i
            wobble = math.sin(self.age * 0.1 + i) * 3
            dist = r + wobble
            pts.append((int(self.pos.x + math.cos(a) * dist), int(self.pos.y + math.sin(a) * dist)))
        pygame.draw.polygon(surface, color, pts)
        # Eyes
        eye_offset = 4
        pygame.draw.circle(surface, WHITE, (pos[0] - eye_offset, pos[1] - 2), 3)
        pygame.draw.circle(surface, WHITE, (pos[0] + eye_offset, pos[1] - 2), 3)

    def _draw_splitter(self, surface, pos, r):
        # Cell-like: outer membrane + nucleus
        pygame.draw.circle(surface, self.color, pos, r)
        pygame.draw.circle(surface, (100, 180, 40), pos, r, 2)
        # Two nuclei (hint it splits)
        pygame.draw.circle(surface, WHITE, (pos[0] - 4, pos[1]), 3)
        pygame.draw.circle(surface, WHITE, (pos[0] + 4, pos[1]), 3)
        # Division line
        pygame.draw.line(surface, (80, 150, 30), (pos[0], pos[1] - r + 2), (pos[0], pos[1] + r - 2), 1)

    def _draw_teleporter(self, surface, pos, r):
        # Unstable diamond with blink indicators
        pts = [
            (pos[0], pos[1] - r),
            (pos[0] + r, pos[1]),
            (pos[0], pos[1] + r),
            (pos[0] - r, pos[1]),
        ]
        # Flicker near teleport
        if self.teleport_timer > 150:
            if int(self.age) % 6 < 3:
                return  # blink out
        pygame.draw.polygon(surface, self.color, pts)
        pygame.draw.polygon(surface, WHITE, pts, 1)
        # Warp rings
        warp_progress = self.teleport_timer / 180
        if warp_progress > 0.5:
            wr = int(r * 2 * (warp_progress - 0.5) * 2)
            pygame.draw.circle(surface, VIOLET, pos, wr, 1)

    def _draw_berserker(self, surface, pos, r):
        # Gets redder and spikier as HP drops
        hp_pct = self.hp / self.max_hp
        rage = 1 - hp_pct
        # Color shifts to bright red
        cr = int(min(255, 200 + rage * 55))
        cg = int(max(0, 50 - rage * 50))
        cb = int(max(0, 30 - rage * 30))
        color = (cr, cg, cb)
        # More spikes with more rage
        spikes = 5 + int(rage * 5)
        pts = []
        for i in range(spikes * 2):
            a = self.rot * (1 + rage) + math.pi / spikes * i
            dist = r if i % 2 == 0 else r * (0.6 - rage * 0.2)
            pts.append((int(self.pos.x + math.cos(a) * dist), int(self.pos.y + math.sin(a) * dist)))
        pygame.draw.polygon(surface, color, pts)
        # Rage aura
        if rage > 0.5:
            pygame.draw.circle(surface, (100, 0, 0), pos, r + 5, 1)

    def _draw_summoner(self, surface, pos, r):
        # Dark robed circle with orbiting dots
        pygame.draw.circle(surface, (60, 30, 80), pos, r)
        pygame.draw.circle(surface, self.color, pos, r, 2)
        # Orbiting minion indicators
        orb_count = 3
        for i in range(orb_count):
            a = self.rot * 1.5 + math.pi * 2 / orb_count * i
            ox = int(self.pos.x + math.cos(a) * (r + 6))
            oy = int(self.pos.y + math.sin(a) * (r + 6))
            pygame.draw.circle(surface, MAGENTA, (ox, oy), 3)
        # Summon charge indicator
        if self.summon_timer > 200:
            charge = (self.summon_timer - 200) / 100
            pygame.draw.circle(surface, MAGENTA, pos, int(r * 0.6 * charge))
