"""
CHAOS ENGINE — Idle Tower Defense
Entry point. Uses state machine + modular game systems.
"""
import pygame
import random
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import engine
from game.constants import *
from game.states import GameState, StateManager, BaseState
from game.menu import MenuTitleState, MenuSettingsState, MenuControlsState
from game.skill_tree import SkillTree, SkillTreeState
from game.enemies import Enemy, ENEMY_STATS, damage_numbers as _dn_ref
from game.towers import Tower, TOWER_DATA, Projectile, GhostAlly
from commons.chaos_engine import (
    ExplosionType, add_shake, DamageNumber, Trail,
    CHAOS_MODES, SoundType,
)

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


# === Hero (kept in main for now — uses skill tree) ===
HERO_UNLOCK_COST = 500
HERO_BUY_XP_BASE_COST = 50  # scales with level


class Hero:
    def __init__(self, skill_tree):
        self.pos = pygame.Vector2(WIDTH - 100, HEIGHT // 2)
        self.radius = 18
        self.base_speed = 4.5
        self.alive = True
        self.unlocked = False  # must be purchased
        self.trail = Trail(max_length=12)
        self.skill_tree = skill_tree

        self.attack_damage = 15
        self.attack_speed = 22
        self.attack_range = 150
        self.attack_timer = 0
        self.target = None
        self.angle = 0
        self.level = 1
        self.xp = 0
        self.xp_to_level = 150
        self.kills = 0

        self.q_cd = 0
        self.q_max = 200
        self.w_cd = 0
        self.w_max = 360
        self.rally_active = 0
        self.e_cd = 0
        self.e_max = 260
        self.r_cd = 0
        self.r_max = 660

        self.swing_anim = 0
        self.swing_angle = 0
        self.q_anim = 0
        self.e_anim = 0
        self.e_target_pos = None
        self.r_anim = 0
        self.move_bob = 0

    def get_buy_xp_cost(self):
        return HERO_BUY_XP_BASE_COST + self.level * 30

    def get_buy_xp_amount(self):
        return int(self.xp_to_level * 0.25)

    def buy_xp(self, state):
        """Spend gold to gain 25% of level XP. Returns True if purchased."""
        cost = self.get_buy_xp_cost()
        if state["gold"] >= cost:
            state["gold"] -= cost
            self.gain_xp(self.get_buy_xp_amount())
            engine.audio.play(SoundType.COIN, 0.5)
            return True
        return False

    @property
    def speed(self):
        mods = self.skill_tree.get_modifiers()
        return self.base_speed * (1 + mods.get("move_speed_mult", 0))

    def get_damage(self):
        mods = self.skill_tree.get_modifiers()
        return self.attack_damage * (1 + mods.get("attack_damage_mult", 0))

    def get_ability_cd_mult(self):
        mods = self.skill_tree.get_modifiers()
        return max(0.3, 1 + mods.get("ability_cd_mult", 0))

    def get_ability_damage(self):
        mods = self.skill_tree.get_modifiers()
        return self.attack_damage * (1 + mods.get("ability_damage_mult", 0))

    def gain_xp(self, amount):
        if not self.unlocked:
            return
        self.xp += amount
        while self.xp >= self.xp_to_level:
            self.xp -= self.xp_to_level
            self.level += 1
            self.xp_to_level = int(self.xp_to_level * 1.8)  # much steeper curve
            self.attack_damage += 5  # slower scaling
            self.attack_range += 4
            self.attack_speed = max(10, self.attack_speed - 1)
            self.skill_tree.add_point()
            engine.particles.explode(self.pos.x, self.pos.y, GOLD, ExplosionType.CONFETTI, 1.5)
            engine.audio.play(SoundType.LEVELUP)
            add_shake(5)
            damage_numbers.append(DamageNumber(self.pos.x, self.pos.y - 30, self.level, GOLD, True))

    def update(self, keys, enemies, projectiles_list, dt):
        if not self.alive or not self.unlocked:
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

        cd_mult = self.get_ability_cd_mult()
        self.q_cd = max(0, self.q_cd - dt / cd_mult)
        self.w_cd = max(0, self.w_cd - dt / cd_mult)
        self.e_cd = max(0, self.e_cd - dt / cd_mult)
        self.r_cd = max(0, self.r_cd - dt / cd_mult)
        if self.rally_active > 0:
            self.rally_active -= dt

        if self.swing_anim > 0:
            self.swing_anim -= dt
        if self.q_anim > 0:
            self.q_anim -= dt
        if self.e_anim > 0:
            self.e_anim -= dt
        if self.r_anim > 0:
            self.r_anim -= dt

        # Chaos aura DOT
        mods = self.skill_tree.get_modifiers()
        if mods.get("chaos_aura", 0) > 0:
            for e in enemies:
                if e.alive and (e.pos - self.pos).length() < 80:
                    e.take_damage(0.5 * dt)

    def find_target(self, enemies):
        mods = self.skill_tree.get_modifiers()
        atk_range = self.attack_range * (1 + mods.get("attack_range_mult", 0))
        best = None
        best_dist = atk_range
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
            dmg = self.get_damage()
            # Double strike check
            mods = self.skill_tree.get_modifiers()
            hits = 1
            if random.random() < mods.get("double_strike", 0):
                hits = 2
            for _ in range(hits):
                projectiles_list.append(Projectile(
                    self.pos.x, self.pos.y, self.target,
                    dmg, speed=14, color=CYAN
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
                    dmg = self.get_damage() * 2.5
                    projectiles_list.append(Projectile(
                        self.pos.x, self.pos.y, e, dmg,
                        speed=18, color=WHITE, explosion_type=ExplosionType.SPARKS
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
        dmg = self.get_ability_damage() * 1.8
        for e in enemies:
            if e.alive and (e.pos - self.pos).length() < 130:
                e.take_damage(dmg)
                engine.vfx.flash(e.pos.x, e.pos.y, CYAN, 8)
                hits += 1
        engine.particles.explode(self.pos.x, self.pos.y, CYAN, ExplosionType.SHOCKWAVE, 1.5)
        engine.vfx.ring(self.pos.x, self.pos.y, CYAN, 130)
        engine.vfx.shockwave(self.pos.x, self.pos.y, 130)
        add_shake(6)
        if hits:
            self.gain_xp(hits * 5)

    def ability_w(self, towers):
        if self.w_cd > 0:
            return
        self.w_cd = self.w_max
        self.rally_active = 180
        engine.particles.explode(self.pos.x, self.pos.y, GOLD, ExplosionType.RING, 1.0)
        engine.vfx.ring(self.pos.x, self.pos.y, GOLD, 220)

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
            dmg = target.max_hp * 0.35 + self.get_ability_damage() * 2
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
        engine.vfx.shockwave(self.pos.x, self.pos.y, 250)
        engine.vfx.ring(self.pos.x, self.pos.y, MAGENTA, 200)
        engine.vfx.flash(self.pos.x, self.pos.y, WHITE, 20)
        dmg = self.get_ability_damage() * 4
        for e in enemies:
            if not e.alive:
                continue
            e.take_damage(dmg)
            if e.path_idx > 10:
                e.path_idx = max(0, e.path_idx - 25)
                e.pos = pygame.Vector2(e.path[e.path_idx])
            engine.particles.explode(e.pos.x, e.pos.y,
                                     random.choice([MAGENTA, RED, ORANGE, YELLOW]),
                                     random.choice(list(ExplosionType)), 0.6)

    def draw(self, surface):
        if not self.alive or not self.unlocked:
            return
        pos = (int(self.pos.x), int(self.pos.y))
        bob = math.sin(self.move_bob) * 2
        self.trail.draw(surface, CYAN, max_width=5)

        pygame.draw.circle(surface, (20, 35, 40), pos, self.attack_range, 1)

        if self.rally_active > 0:
            ar = 220 + math.sin(engine.frame_count * 0.1) * 8
            pygame.draw.circle(surface, GOLD, pos, int(ar), 2)

        if self.r_anim > 0:
            progress = 1 - self.r_anim / 30
            for i in range(3):
                rr = int(200 * progress) - i * 20
                if rr > 0:
                    pygame.draw.circle(surface, MAGENTA, pos, rr, 2)

        if self.q_anim > 0:
            spin = 1 - self.q_anim / 20
            for i in range(4):
                ba = spin * math.pi * 4 + (math.pi / 2) * i
                blen = 100 + 30 * spin
                bx = int(self.pos.x + math.cos(ba) * blen)
                by = int(self.pos.y + math.sin(ba) * blen)
                pygame.draw.line(surface, CYAN, pos, (bx, by), 2)
                pygame.draw.circle(surface, CYAN, (bx, by), 4)

        if self.e_anim > 0 and self.e_target_pos:
            alpha = self.e_anim / 15
            sx, sy = int(self.e_target_pos.x), int(self.e_target_pos.y)
            pygame.draw.line(surface, (int(255 * alpha), 0, 0), pos, (sx, sy), max(1, int(4 * alpha)))
            cs = int(15 * alpha)
            pygame.draw.line(surface, RED, (sx - cs, sy - cs), (sx + cs, sy + cs), 3)
            pygame.draw.line(surface, RED, (sx + cs, sy - cs), (sx - cs, sy + cs), 3)

        # Body
        draw_y = int(self.pos.y + bob)
        body_pos = (int(self.pos.x), draw_y)
        pygame.draw.circle(surface, (20, 50, 60), body_pos, self.radius)
        gem_color = CYAN if self.level < 5 else GOLD if self.level < 10 else MAGENTA
        pygame.draw.circle(surface, gem_color, body_pos, 5)
        pygame.draw.circle(surface, CYAN, body_pos, self.radius, 2)

        # Blade
        blade_len = self.radius + 16
        swing_offset = 0
        if self.swing_anim > 0:
            swing_offset = math.sin(self.swing_anim / 10 * math.pi) * 0.8
        ba = self.angle + swing_offset
        bx = int(self.pos.x + math.cos(ba) * blade_len)
        by = int(draw_y + math.sin(ba) * blade_len)
        pygame.draw.line(surface, (180, 220, 255), body_pos, (bx, by), 3)
        pygame.draw.circle(surface, CYAN if self.swing_anim > 0 else WHITE, (bx, by), 3)

        # Level
        engine.ui.text(surface, f"Lv{self.level}", int(self.pos.x - 10),
                       int(self.pos.y + self.radius + 10), gem_color, engine.ui.font_small)


# === Base ===
class Base:
    def __init__(self, extra_hp=0):
        self.pos = pygame.Vector2(WIDTH - 60, HEIGHT // 2)
        self.max_hp = 25 + extra_hp
        self.hp = self.max_hp
        self.radius = 32

    def take_damage(self, amount=1):
        self.hp -= amount
        add_shake(10)
        engine.audio.play(SoundType.DAMAGE_TAKEN, 0.8)
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


# === Economy ===
class Economy:
    def __init__(self, extra_interest=0):
        self.gold_per_sec = 2
        self.timer = 0
        self.interest_rate = 0.03 + extra_interest
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


# === Chaos Events ===
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
        engine.audio.play(SoundType.CHAOS_EVENT)

        if event == "double_speed":
            for e in enemies:
                if e.alive:
                    e.base_speed *= 2
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
            engine.ui.text_centered(surface, self.event_text, WIDTH // 2, 90, MAGENTA, engine.ui.font_large)


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
        engine.audio.play(SoundType.WAVE_START)

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
        if w >= 8:
            spawns += ["splitter"] * min(w - 7, 4)
            spawns += ["teleporter"] * min(w - 7, 3)
        if w >= 9:
            spawns += ["berserker"] * min(w - 8, 4)
        if w >= 10:
            spawns += ["summoner"] * min(w - 9, 3)
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


# === Drawing ===
def draw_paths(surface):
    for lane in lanes:
        for i in range(len(lane) - 1):
            p1 = (int(lane[i].x), int(lane[i].y))
            p2 = (int(lane[i + 1].x), int(lane[i + 1].y))
            pygame.draw.line(surface, (22, 22, 32), p1, p2, 10)
            pygame.draw.line(surface, (35, 35, 50), p1, p2, 2)


def draw_shop(surface, gold, selected_tower_obj, shop_selected):
    panel_y = HEIGHT - 95
    pygame.draw.rect(surface, (20, 20, 28), (0, panel_y, WIDTH, 95))
    pygame.draw.line(surface, (50, 50, 65), (0, panel_y), (WIDTH, panel_y), 2)
    x = 10
    idx = 1
    for key, data in TOWER_DATA.items():
        sel = (key == shop_selected)
        box_c = data["color"] if sel else (50, 50, 60)
        pygame.draw.rect(surface, box_c, (x, panel_y + 8, 68, 78), 2 if not sel else 0)
        if sel:
            pygame.draw.rect(surface, (18, 18, 25), (x + 2, panel_y + 10, 64, 74))
        engine.ui.text(surface, data["name"][:6], x + 3, panel_y + 12, data["color"], engine.ui.font_small)
        cost_col = GOLD if gold >= data["cost"] else RED
        engine.ui.text(surface, f"${data['cost']}", x + 3, panel_y + 26, cost_col, engine.ui.font_small)
        engine.ui.text(surface, data["desc"][:8], x + 3, panel_y + 40, (100, 100, 100), engine.ui.font_small)
        hotkey = str(idx) if idx < 10 else "0"
        engine.ui.text(surface, f"[{hotkey}]", x + 48, panel_y + 63, (70, 70, 70), engine.ui.font_small)
        x += 74
        idx += 1


def draw_hud(surface, state, hero, wave_mgr, game_chaos, economy):
    engine.ui.text(surface, f"${state['gold']}", 15, 12, GOLD, engine.ui.font_large)
    engine.ui.text(surface, f"+{economy.gold_per_sec}/s", 15, 40, (180, 150, 50), engine.ui.font_small)
    engine.ui.text(surface, f"Score: {int(state['score'])}", 15, 58, WHITE, engine.ui.font_med)
    engine.ui.text_centered(surface, f"WAVE {wave_mgr.wave}", WIDTH // 2, 20, CYAN, engine.ui.font_large)
    if wave_mgr.between_waves:
        secs = max(0, int(wave_mgr.pause_timer / 60))
        engine.ui.text_centered(surface, f"Next: {secs}s [SPACE]", WIDTH // 2, 45, (120, 120, 120), engine.ui.font_small)
    if hero.unlocked:
        engine.ui.text(surface, f"Hero Lv{hero.level} | Kills:{hero.kills} | SP:{hero.skill_tree.points}",
                       WIDTH - 300, 12, CYAN, engine.ui.font_small)
        xp_pct = hero.xp / hero.xp_to_level
        engine.ui.progress_bar(surface, WIDTH - 300, 30, 150, 8, xp_pct, GOLD)
        buy_cost = hero.get_buy_xp_cost()
        buy_col = GOLD if state["gold"] >= buy_cost else (80, 80, 80)
        engine.ui.text(surface, f"[B] Buy XP: ${buy_cost}", WIDTH - 140, 30, buy_col, engine.ui.font_small)
    else:
        unlock_col = GOLD if state["gold"] >= HERO_UNLOCK_COST else RED
        engine.ui.text(surface, f"[H] Unlock Hero: ${HERO_UNLOCK_COST}",
                       WIDTH - 300, 12, unlock_col, engine.ui.font_med)
        engine.ui.text(surface, "Towers only until hero unlocked",
                       WIDTH - 300, 34, (80, 80, 80), engine.ui.font_small)

    abilities = [
        ("Q", hero.q_cd, hero.q_max, CYAN),
        ("T", hero.w_cd, hero.w_max, GOLD),
        ("E", hero.e_cd, hero.e_max, RED),
        ("F", hero.r_cd, hero.r_max, MAGENTA),
    ]
    if hero.unlocked:
        ax = WIDTH - 300
        for name, cd, mx, col in abilities:
            fill = 1.0 - cd / mx if mx > 0 else 1.0
            engine.ui.cooldown_icon(surface, ax, 45, 30, fill, col, name)
            ax += 38
        engine.ui.text(surface, "[TAB] Skills", WIDTH - 110, 45, (60, 80, 60), engine.ui.font_small)
    game_chaos.draw(surface)


# === Playing State ===
class PlayingState(BaseState):
    def __init__(self, state_manager, difficulty=1):
        self.sm = state_manager
        self.difficulty = difficulty
        self.skill_tree = SkillTree()
        self.skill_tree_state = SkillTreeState(state_manager, self.skill_tree)
        self.skill_tree_open = False
        self.paused = False
        self.paused = False
        self._init_game()

    def _init_game(self):
        regenerate_lanes()
        self.towers = []
        self.enemies = []
        self.projectiles = []
        self.hero = Hero(self.skill_tree)
        mods = self.skill_tree.get_modifiers()
        self.base = Base(extra_hp=int(mods.get("base_hp", 0)))
        self.wave_mgr = WaveManager()
        self.game_chaos = GameChaos()
        self.economy = Economy(extra_interest=mods.get("gold_interest", 0))
        self.selected_tower = None
        self.shop_selected = "arrow"
        self.placing = False
        self.game_over = False
        self.state = {"gold": 200, "score": 0, "wave": 0}

        # Share damage_numbers with enemy module
        global damage_numbers
        damage_numbers = []
        import game.enemies
        game.enemies.damage_numbers = damage_numbers

        engine.particles.particles.clear()
        engine.vfx.clear()
        engine.audio.play_bgm(8)

    def handle_events(self, events):
        if self.skill_tree_open:
            result = self.skill_tree_state.handle_events(events)
            if result == "close_skill_tree":
                self.skill_tree_open = False
            return None

        mouse_pos = engine.mouse_logical()
        keys = pygame.key.get_pressed()

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and self.game_over:
                    self._init_game()
                    continue
                if event.key == pygame.K_SPACE and self.wave_mgr.between_waves:
                    self.wave_mgr.start_wave(self.wave_mgr.wave + 1)
                    self.state["wave"] = self.wave_mgr.wave
                if event.key == pygame.K_TAB:
                    self.skill_tree_open = True

                # Tower hotkeys (1-9, 0 for 10th, minus for 11th, equals for 12th)
                tower_keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                              pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8,
                              pygame.K_9, pygame.K_0, pygame.K_MINUS, pygame.K_EQUALS]
                tower_names = list(TOWER_DATA.keys())
                for i, tk in enumerate(tower_keys):
                    if event.key == tk and i < len(tower_names):
                        self.shop_selected = tower_names[i]
                        self.placing = True

                if event.key == pygame.K_u and self.selected_tower:
                    cost = self.selected_tower.get_upgrade_cost()
                    if cost and self.state["gold"] >= cost:
                        self.state["gold"] -= cost
                        self.selected_tower.upgrade()

                if event.key == pygame.K_x and self.selected_tower:
                    refund = TOWER_DATA[self.selected_tower.tower_type]["cost"] // 2
                    self.state["gold"] += refund
                    self.towers.remove(self.selected_tower)
                    self.selected_tower = None
                    engine.audio.play(SoundType.SELL)

                if event.key == pygame.K_ESCAPE:
                    self.placing = False
                    self.selected_tower = None
                    if not self.placing and not self.selected_tower:
                        self.paused = not self.paused

                if event.key == pygame.K_m:
                    engine.audio.toggle_mute()

                # Hero unlock (H key)
                if event.key == pygame.K_h and not self.hero.unlocked:
                    if self.state["gold"] >= HERO_UNLOCK_COST:
                        self.state["gold"] -= HERO_UNLOCK_COST
                        self.hero.unlocked = True
                        engine.audio.play(SoundType.POWERUP)
                        engine.particles.explode(self.hero.pos.x, self.hero.pos.y, CYAN,
                                                 ExplosionType.NOVA, 2.0)
                        add_shake(8)

                # Buy XP (B key)
                if event.key == pygame.K_b and self.hero.unlocked:
                    self.hero.buy_xp(self.state)

                if event.key == pygame.K_q and self.hero.unlocked:
                    self.hero.ability_q(self.enemies)
                if event.key == pygame.K_t and self.hero.unlocked:
                    self.hero.ability_w(self.towers)
                if event.key == pygame.K_e and self.hero.unlocked:
                    self.hero.ability_e(self.enemies)
                if event.key == pygame.K_f and self.hero.unlocked:
                    self.hero.ability_r(self.enemies)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if mouse_pos.y > HEIGHT - 95:
                        x = 10
                        for key in TOWER_DATA:
                            if x <= mouse_pos.x <= x + 68:
                                self.shop_selected = key
                                self.placing = True
                                break
                            x += 74
                    elif self.placing:
                        cost = TOWER_DATA[self.shop_selected]["cost"]
                        if self.state["gold"] >= cost:
                            can = all((t.pos - mouse_pos).length() > 40 for t in self.towers)
                            if can and mouse_pos.y < HEIGHT - 95:
                                self.state["gold"] -= cost
                                self.towers.append(Tower(mouse_pos.x, mouse_pos.y, self.shop_selected))
                                engine.audio.play(SoundType.PLACE_TOWER)
                                engine.particles.explode(mouse_pos.x, mouse_pos.y,
                                                         TOWER_DATA[self.shop_selected]["color"],
                                                         ExplosionType.CONFETTI, 0.6)
                                self.placing = False
                    else:
                        # Check tower panel buttons first
                        if not self._handle_tower_panel_click(mouse_pos):
                            self.selected_tower = None
                            for t in self.towers:
                                if (t.pos - mouse_pos).length() < 25:
                                    self.selected_tower = t
                                    break
                elif event.button == 3:
                    self.hero.right_click(mouse_pos, self.enemies, self.projectiles)

        return None

    def update(self, dt):
        if self.paused:
            return
        if self.game_over or self.skill_tree_open:
            if self.skill_tree_open:
                self.skill_tree_state.update(dt)
            return

        keys = pygame.key.get_pressed()
        self.hero.update(keys, self.enemies, self.projectiles, dt)

        # Tower damage multiplier from skills
        mods = self.skill_tree.get_modifiers()
        tower_dmg_mult = 1 + mods.get("tower_damage_mult", 0)
        fire_mult = 1.8 if self.hero.rally_active > 0 else 1.0
        for t in self.towers:
            t.update(self.enemies, self.projectiles, dt, fire_mult, tower_dmg_mult)

        self.wave_mgr.update(self.enemies, dt)
        self.state["wave"] = self.wave_mgr.wave

        new_spawns = []
        for e in self.enemies:
            reached, spawned = e.update(self.enemies, dt)
            new_spawns.extend(spawned)
            if reached:
                self.base.take_damage()
                if self.base.hp <= 0:
                    self.game_over = True
                    engine.particles.chain_explosion(self.base.pos.x, self.base.pos.y, RED, 200, 12, 3.0)
                    engine.audio.play(SoundType.DEATH)
                    add_shake(25)
        self.enemies.extend(new_spawns)

        for p in self.projectiles:
            p.update(self.enemies, dt)
        self.projectiles[:] = [p for p in self.projectiles if p.alive]

        # Track kills
        for e in self.enemies:
            if not e.alive and not e._counted:
                e._counted = True
                self.state["gold"] += e.gold_value
                self.state["score"] += e.score_value
                self.hero.gain_xp(int(e.score_value * 0.4))
                self.hero.kills += 1
                self.economy.gold_per_sec = 2 + self.hero.kills // 15
                engine.audio.play(SoundType.COIN, 0.25)
                # Splitter spawns
                for spawn in e.get_split_spawns():
                    self.enemies.append(spawn)
                # Necro tower callback
                for t in self.towers:
                    t.on_enemy_killed(e)

        self.enemies[:] = [e for e in self.enemies if e.alive]
        self.economy.update(self.state, dt)
        self.game_chaos.update(self.state, self.enemies, self.towers, dt)
        engine.particles.update(dt)

        # VFX update + warp grid near hero position
        engine.vfx.update(dt)
        if self.hero.unlocked:
            engine.vfx.warp_grid(self.hero.pos.x, self.hero.pos.y, 30, 80)

        for d in damage_numbers:
            d.update(dt)
        damage_numbers[:] = [d for d in damage_numbers if d.life > 0]

    def draw(self, surface):
        surface.fill(BG_COLOR)

        # VFX background layer (grid + ambient particles)
        engine.vfx.draw_background(surface)

        draw_paths(surface)

        if self.placing:
            mouse_pos = engine.mouse_logical()
            data = TOWER_DATA[self.shop_selected]
            pygame.draw.circle(surface, data["color"], (int(mouse_pos.x), int(mouse_pos.y)), data["range"], 1)
            pygame.draw.circle(surface, data["color"], (int(mouse_pos.x), int(mouse_pos.y)), 18, 2)

        for t in self.towers:
            t.draw(surface, t is self.selected_tower)
        for e in self.enemies:
            e.draw(surface)
        for p in self.projectiles:
            p.draw(surface)
        self.hero.draw(surface)
        self.base.draw(surface)
        engine.particles.draw(surface)

        # VFX foreground layer (beams, lightning, rings, shockwaves, flashes)
        engine.vfx.draw_foreground(surface)

        for d in damage_numbers:
            d.draw(surface)
        draw_hud(surface, self.state, self.hero, self.wave_mgr, self.game_chaos, self.economy)
        draw_shop(surface, self.state["gold"], self.selected_tower, self.shop_selected)

        # Tower upgrade panel (near selected tower)
        if self.selected_tower and not self.game_over:
            self._draw_tower_panel(surface, self.selected_tower)

        # VFX post-process (bloom + vignette) — applied last
        engine.vfx.draw_post_process(surface)

        if self.game_over:
            engine.ui.overlay(surface, 180)
            engine.ui.text_centered(surface, "BASE DESTROYED", WIDTH // 2, HEIGHT // 3 - 30, RED, engine.ui.font_huge)
            lines = [
                f"Score: {int(self.state['score'])}",
                f"Wave: {self.wave_mgr.wave}",
                f"Hero Lv{self.hero.level} — {self.hero.kills} kills",
                f"Towers: {len(self.towers)}",
                "", "R to restart",
            ]
            y = HEIGHT // 3 + 40
            for line in lines:
                engine.ui.text_centered(surface, line, WIDTH // 2, y, WHITE, engine.ui.font_med)
                y += 32

        if self.skill_tree_open:
            self.skill_tree_state.draw(surface)

        if self.paused and not self.game_over:
            engine.ui.overlay(surface, 150)
            engine.ui.text_centered(surface, "PAUSED", WIDTH // 2, HEIGHT // 3, WHITE, engine.ui.font_huge)
            engine.ui.text_centered(surface, "ESC to resume", WIDTH // 2, HEIGHT // 3 + 50,
                                    (120, 120, 120), engine.ui.font_med)

    def _draw_tower_panel(self, surface, tower):
        """Draw upgrade/sell panel near selected tower."""
        data = TOWER_DATA[tower.tower_type]
        # Panel position — offset to right of tower, clamp to screen
        px = int(tower.pos.x + 35)
        py = int(tower.pos.y - 50)
        pw, ph = 140, 95
        if px + pw > WIDTH - 10:
            px = int(tower.pos.x - 35 - pw)
        if py < 10:
            py = 10
        if py + ph > HEIGHT - 100:
            py = HEIGHT - 100 - ph

        # Background
        panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_surf.fill((20, 20, 30, 220))
        surface.blit(panel_surf, (px, py))
        pygame.draw.rect(surface, tower.color, (px, py, pw, ph), 1)

        # Tower info
        engine.ui.text(surface, f"{data['name']} Lv{tower.level}", px + 5, py + 4, tower.color, engine.ui.font_small)
        engine.ui.text(surface, f"DMG:{tower.damage} SPD:{tower.fire_rate}", px + 5, py + 20, (150, 150, 150), engine.ui.font_small)

        # Upgrade button
        upgrade_cost = tower.get_upgrade_cost()
        self._upgrade_btn = pygame.Rect(px + 5, py + 38, pw - 10, 22)
        if upgrade_cost:
            can_afford = self.state["gold"] >= upgrade_cost
            btn_color = GOLD if can_afford else (60, 60, 60)
            pygame.draw.rect(surface, (30, 40, 30) if can_afford else (25, 25, 25), self._upgrade_btn)
            pygame.draw.rect(surface, btn_color, self._upgrade_btn, 1)
            engine.ui.text(surface, f"Upgrade ${upgrade_cost}", px + 10, py + 41, btn_color, engine.ui.font_small)
        else:
            pygame.draw.rect(surface, (25, 25, 25), self._upgrade_btn)
            engine.ui.text(surface, "MAX LEVEL", px + 10, py + 41, GOLD, engine.ui.font_small)

        # Sell button
        sell_value = data["cost"] // 2
        self._sell_btn = pygame.Rect(px + 5, py + 65, pw - 10, 22)
        pygame.draw.rect(surface, (40, 20, 20), self._sell_btn)
        pygame.draw.rect(surface, RED, self._sell_btn, 1)
        engine.ui.text(surface, f"Sell +${sell_value}", px + 10, py + 68, RED, engine.ui.font_small)

    def _handle_tower_panel_click(self, mouse_pos):
        """Check if click hit upgrade/sell buttons. Returns True if handled."""
        if not self.selected_tower:
            return False

        if hasattr(self, '_upgrade_btn') and self._upgrade_btn.collidepoint(mouse_pos.x, mouse_pos.y):
            cost = self.selected_tower.get_upgrade_cost()
            if cost and self.state["gold"] >= cost:
                self.state["gold"] -= cost
                self.selected_tower.upgrade()
            return True

        if hasattr(self, '_sell_btn') and self._sell_btn.collidepoint(mouse_pos.x, mouse_pos.y):
            refund = TOWER_DATA[self.selected_tower.tower_type]["cost"] // 2
            self.state["gold"] += refund
            self.towers.remove(self.selected_tower)
            self.selected_tower = None
            engine.audio.play(SoundType.SELL)
            return True

        return False


# === MAIN ===
state_manager = StateManager()
state_manager.push(MenuTitleState(state_manager))

while engine.running:
    surface = engine.begin_frame()
    events = engine.process_events()

    result = state_manager.handle_events(events)

    if result == GameState.PLAYING:
        state_manager.replace(PlayingState(state_manager))
    elif result == GameState.MENU_TITLE:
        state_manager.replace(MenuTitleState(state_manager))
    elif result == GameState.MENU_SETTINGS:
        state_manager.replace(MenuSettingsState(state_manager))
    elif result == GameState.MENU_CONTROLS:
        state_manager.replace(MenuControlsState(state_manager))

    state_manager.update(engine.dt)
    state_manager.draw(surface)

    engine.end_frame()

engine.quit()
