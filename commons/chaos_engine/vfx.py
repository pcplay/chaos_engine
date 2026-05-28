"""
VFX Module — Modern neon/glow visual effects for pygame.

Provides post-processing and overlay effects that simulate shader-like visuals
using only pygame surfaces, alpha blending, and additive compositing.

Inspired by: Geometry Wars, Vampire Survivors, neon wireframe aesthetics.
"""

import pygame
import math
import random


# ---------------------------------------------------------------------------
# 1. Bloom / Glow post-process
# ---------------------------------------------------------------------------

class BloomEffect:
    """
    Fast fake bloom: extract bright pixels, downsample, blur via rescale, blend back.

    Usage:
        bloom = BloomEffect(1200, 800)
        # ... draw your scene onto `surface` ...
        bloom.apply(surface)  # modifies surface in-place
    """

    def __init__(self, width, height, intensity=0.6, threshold=180, downsample=4):
        self.width = width
        self.height = height
        self.intensity = intensity
        self.threshold = threshold
        self.downsample = downsample
        self.small_w = max(1, width // downsample)
        self.small_h = max(1, height // downsample)
        # Pre-allocate work surfaces
        self._bright_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        self._small_surf = pygame.Surface((self.small_w, self.small_h), pygame.SRCALPHA)
        self._bloom_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        # Threshold surface (dark fill for extraction)
        self._threshold_color = (self.threshold, self.threshold, self.threshold)

    def apply(self, surface):
        """Apply bloom to the given surface in-place."""
        # Extract bright areas: copy surface, subtract threshold
        self._bright_surf.blit(surface, (0, 0))
        # Darken to isolate brights — fill with threshold color using BLEND_RGB_SUB
        self._bright_surf.fill(self._threshold_color, special_flags=pygame.BLEND_RGB_SUB)

        # Downsample (acts as blur pass 1)
        pygame.transform.smoothscale(self._bright_surf, (self.small_w, self.small_h), self._small_surf)
        # Upsample (acts as blur pass 2 — smooth interpolation = gaussian-like)
        pygame.transform.smoothscale(self._small_surf, (self.width, self.height), self._bloom_surf)

        # Additive blend back at intensity
        self._bloom_surf.set_alpha(int(255 * self.intensity))
        surface.blit(self._bloom_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def set_intensity(self, intensity):
        self.intensity = max(0.0, min(1.0, intensity))

    def set_threshold(self, threshold):
        self.threshold = max(0, min(255, threshold))
        self._threshold_color = (self.threshold, self.threshold, self.threshold)


# ---------------------------------------------------------------------------
# 2. Neon Trail Renderer
# ---------------------------------------------------------------------------

class NeonTrail:
    """
    Glowing trail with bright center and soft outer glow.

    Usage:
        trail = NeonTrail(color=(0, 255, 255), max_length=30)
        trail.add_point(pos)
        trail.draw(surface)
    """

    def __init__(self, color=(0, 255, 255), max_length=30, width=4, glow_width=12, glow_alpha=80):
        self.color = color
        self.max_length = max_length
        self.width = width
        self.glow_width = glow_width
        self.glow_alpha = glow_alpha
        self.points = []
        # Brighter core
        self.core_color = tuple(min(255, c + 100) for c in color)

    def add_point(self, pos):
        self.points.append((float(pos[0]), float(pos[1])))
        if len(self.points) > self.max_length:
            self.points.pop(0)

    def clear(self):
        self.points.clear()

    def draw(self, surface):
        if len(self.points) < 2:
            return
        n = len(self.points)
        for i in range(1, n):
            t = i / n  # 0 = old, 1 = new
            alpha = t
            p1 = (int(self.points[i - 1][0]), int(self.points[i - 1][1]))
            p2 = (int(self.points[i][0]), int(self.points[i][1]))

            # Outer glow (wider, dimmer)
            glow_a = int(self.glow_alpha * alpha)
            glow_w = max(1, int(self.glow_width * alpha))
            glow_c = tuple(int(c * alpha * 0.5) for c in self.color)
            pygame.draw.line(surface, glow_c, p1, p2, glow_w)

            # Core (thinner, brighter)
            core_w = max(1, int(self.width * alpha))
            core_c = tuple(int(c * alpha) for c in self.core_color)
            pygame.draw.line(surface, core_c, p1, p2, core_w)

    def draw_additive(self, surface):
        """Draw with additive blending for extra glow on dark backgrounds."""
        if len(self.points) < 2:
            return
        # Create temp surface for additive blending
        temp = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self.draw(temp)
        surface.blit(temp, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------
# 3. Pulse Rings
# ---------------------------------------------------------------------------

class PulseRing:
    """A single expanding, fading ring."""

    def __init__(self, x, y, color, max_radius=100, speed=4.0, width=3, life=1.0):
        self.x = x
        self.y = y
        self.color = color
        self.max_radius = max_radius
        self.speed = speed
        self.width = width
        self.radius = 0.0
        self.life = life
        self.alive = True

    def update(self, dt):
        self.radius += self.speed * dt
        self.life -= (self.speed * dt) / self.max_radius
        if self.life <= 0 or self.radius >= self.max_radius:
            self.alive = False

    def draw(self, surface):
        if not self.alive or self.radius < 1:
            return
        alpha = max(0, min(1, self.life))
        c = tuple(int(v * alpha) for v in self.color)
        w = max(1, int(self.width * alpha))
        pygame.draw.circle(surface, c, (int(self.x), int(self.y)), int(self.radius), w)
        # Inner brighter ring
        if self.radius > 3:
            inner_c = tuple(min(255, int(v * alpha * 1.5)) for v in self.color)
            pygame.draw.circle(surface, inner_c, (int(self.x), int(self.y)), int(self.radius - 2), max(1, w // 2))


class PulseRingSystem:
    """
    Manages multiple pulse rings.

    Usage:
        rings = PulseRingSystem()
        rings.spawn(400, 300, (0, 255, 200))
        rings.update(dt)
        rings.draw(surface)
    """

    def __init__(self, max_rings=50):
        self.rings = []
        self.max_rings = max_rings

    def spawn(self, x, y, color, max_radius=100, speed=4.0, width=3):
        if len(self.rings) < self.max_rings:
            self.rings.append(PulseRing(x, y, color, max_radius, speed, width))

    def spawn_multi(self, x, y, color, count=3, delay_frames=5, max_radius=120, speed=3.5):
        """Spawn multiple staggered rings (call once, they auto-stagger via radius offset)."""
        for i in range(count):
            ring = PulseRing(x, y, color, max_radius, speed, width=max(1, 3 - i))
            ring.radius = -i * delay_frames * speed  # negative = delayed start
            self.rings.append(ring)

    def update(self, dt):
        for ring in self.rings:
            ring.update(dt)
        self.rings[:] = [r for r in self.rings if r.alive]

    def draw(self, surface):
        for ring in self.rings:
            if ring.radius > 0:
                ring.draw(surface)


# ---------------------------------------------------------------------------
# 4. Lightning / Electricity Overlay
# ---------------------------------------------------------------------------

class Lightning:
    """
    Animated crackling electricity between two points.

    Usage:
        bolt = Lightning((100, 100), (400, 300), color=(150, 150, 255))
        bolt.update(dt)
        bolt.draw(surface)
    """

    def __init__(self, start, end, color=(150, 180, 255), segments=12,
                 jitter=20, branch_chance=0.3, thickness=2, life=None):
        self.start = start
        self.end = end
        self.color = color
        self.segments = segments
        self.jitter = jitter
        self.branch_chance = branch_chance
        self.thickness = thickness
        self.life = life  # None = infinite
        self._points = []
        self._branches = []
        self._timer = 0
        self._regen_interval = 3  # regenerate shape every N frames
        self.alive = True
        self._generate()

    def _generate(self):
        """Generate a jagged lightning bolt path."""
        sx, sy = float(self.start[0]), float(self.start[1])
        ex, ey = float(self.end[0]), float(self.end[1])
        self._points = [(sx, sy)]
        self._branches = []

        for i in range(1, self.segments):
            t = i / self.segments
            # Interpolate base position
            bx = sx + (ex - sx) * t
            by = sy + (ey - sy) * t
            # Perpendicular jitter
            dx = ex - sx
            dy = ey - sy
            length = math.sqrt(dx * dx + dy * dy) or 1
            nx = -dy / length
            ny = dx / length
            offset = random.uniform(-self.jitter, self.jitter)
            px = bx + nx * offset
            py = by + ny * offset
            self._points.append((px, py))

            # Random branch
            if random.random() < self.branch_chance:
                branch_end = (
                    px + random.uniform(-self.jitter * 2, self.jitter * 2),
                    py + random.uniform(-self.jitter * 2, self.jitter * 2),
                )
                branch_mid = (
                    (px + branch_end[0]) / 2 + random.uniform(-self.jitter, self.jitter),
                    (py + branch_end[1]) / 2 + random.uniform(-self.jitter, self.jitter),
                )
                self._branches.append(((px, py), branch_mid, branch_end))

        self._points.append((ex, ey))

    def update(self, dt):
        self._timer += dt
        if self._timer >= self._regen_interval:
            self._timer = 0
            self._generate()
        if self.life is not None:
            self.life -= dt
            if self.life <= 0:
                self.alive = False

    def set_points(self, start, end):
        """Update endpoints (for moving targets)."""
        self.start = start
        self.end = end
        self._generate()

    def draw(self, surface):
        if not self.alive or len(self._points) < 2:
            return
        # Draw outer glow
        glow_color = tuple(c // 3 for c in self.color)
        for i in range(1, len(self._points)):
            p1 = (int(self._points[i - 1][0]), int(self._points[i - 1][1]))
            p2 = (int(self._points[i][0]), int(self._points[i][1]))
            pygame.draw.line(surface, glow_color, p1, p2, self.thickness + 3)

        # Draw core
        core_color = tuple(min(255, c + 80) for c in self.color)
        for i in range(1, len(self._points)):
            p1 = (int(self._points[i - 1][0]), int(self._points[i - 1][1]))
            p2 = (int(self._points[i][0]), int(self._points[i][1]))
            pygame.draw.line(surface, core_color, p1, p2, self.thickness)

        # Draw bright center
        for i in range(1, len(self._points)):
            p1 = (int(self._points[i - 1][0]), int(self._points[i - 1][1]))
            p2 = (int(self._points[i][0]), int(self._points[i][1]))
            pygame.draw.line(surface, (255, 255, 255), p1, p2, max(1, self.thickness - 1))

        # Draw branches
        branch_color = tuple(c // 2 for c in self.color)
        for (bp1, bp2, bp3) in self._branches:
            pygame.draw.line(surface, branch_color,
                             (int(bp1[0]), int(bp1[1])), (int(bp2[0]), int(bp2[1])), 1)
            pygame.draw.line(surface, branch_color,
                             (int(bp2[0]), int(bp2[1])), (int(bp3[0]), int(bp3[1])), 1)


# ---------------------------------------------------------------------------
# 5. Background Grid
# ---------------------------------------------------------------------------

class BackgroundGrid:
    """
    Subtle animated grid that warps near action points.

    Usage:
        grid = BackgroundGrid(1200, 800)
        grid.set_warp_point(player_x, player_y, strength=30)
        grid.draw(surface)
    """

    def __init__(self, width, height, spacing=60, color=(20, 40, 60), line_width=1):
        self.width = width
        self.height = height
        self.spacing = spacing
        self.color = color
        self.line_width = line_width
        self.warp_points = []  # [(x, y, strength, radius), ...]
        self.scroll_offset = 0.0
        self.scroll_speed = 0.3
        # Cache the surface when no warps are active
        self._cached = None
        self._last_warps = None

    def set_warp_point(self, x, y, strength=30, radius=150):
        """Set a warp influence point (call each frame with active positions)."""
        self.warp_points.append((x, y, strength, radius))

    def clear_warps(self):
        self.warp_points.clear()

    def update(self, dt):
        self.scroll_offset += self.scroll_speed * dt

    def _warp_position(self, gx, gy):
        """Apply warp displacement from all warp points."""
        dx_total = 0.0
        dy_total = 0.0
        for wx, wy, strength, radius in self.warp_points:
            dx = gx - wx
            dy = gy - wy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < radius and dist > 1:
                factor = (1.0 - dist / radius) * strength
                dx_total += (dx / dist) * factor
                dy_total += (dy / dist) * factor
        return gx + dx_total, gy + dy_total

    def draw(self, surface):
        offset = self.scroll_offset % self.spacing
        has_warps = len(self.warp_points) > 0

        if not has_warps:
            # Fast path: straight lines
            for x in range(int(-offset), self.width + self.spacing, self.spacing):
                pygame.draw.line(surface, self.color, (x, 0), (x, self.height), self.line_width)
            for y in range(int(-offset), self.height + self.spacing, self.spacing):
                pygame.draw.line(surface, self.color, (0, y), (self.width, y), self.line_width)
        else:
            # Warped grid: draw as short line segments
            seg_len = self.spacing // 3
            # Vertical lines
            for gx in range(int(-offset), self.width + self.spacing, self.spacing):
                prev = None
                for gy in range(0, self.height + seg_len, seg_len):
                    wx, wy = self._warp_position(gx, gy)
                    cur = (int(wx), int(wy))
                    if prev is not None:
                        pygame.draw.line(surface, self.color, prev, cur, self.line_width)
                    prev = cur
            # Horizontal lines
            for gy in range(int(-offset), self.height + self.spacing, self.spacing):
                prev = None
                for gx in range(0, self.width + seg_len, seg_len):
                    wx, wy = self._warp_position(gx, gy)
                    cur = (int(wx), int(wy))
                    if prev is not None:
                        pygame.draw.line(surface, self.color, prev, cur, self.line_width)
                    prev = cur

        # Clear warps after drawing (must be re-set each frame)
        self.warp_points.clear()


# ---------------------------------------------------------------------------
# 6. Vignette
# ---------------------------------------------------------------------------

class Vignette:
    """
    Dark edges overlay for cinematic feel. Cached — very cheap to draw.

    Usage:
        vignette = Vignette(1200, 800)
        # After drawing everything:
        vignette.draw(surface)
    """

    def __init__(self, width, height, intensity=0.7, color=(0, 0, 0)):
        self.width = width
        self.height = height
        self.intensity = intensity
        self._surface = self._generate(width, height, intensity, color)

    def _generate(self, width, height, intensity, color):
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        cx, cy = width // 2, height // 2
        max_dist = math.sqrt(cx * cx + cy * cy)
        # Draw concentric ellipses from edge inward
        steps = 30
        for i in range(steps):
            t = i / steps  # 0 = inner (transparent), 1 = outer (dark)
            alpha = int(255 * intensity * (t ** 2))
            # Radius from full-screen down
            rx = int(cx * (1.0 + 0.5 * (1 - t)))
            ry = int(cy * (1.0 + 0.5 * (1 - t)))
            # Draw a ring
            ring_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.ellipse(ring_surf, (*color, alpha),
                                (cx - rx, cy - ry, rx * 2, ry * 2))
            # Cut out inner portion
            inner_rx = int(cx * (1.0 + 0.5 * (1 - (i + 1) / steps)))
            inner_ry = int(cy * (1.0 + 0.5 * (1 - (i + 1) / steps)))
            pygame.draw.ellipse(ring_surf, (0, 0, 0, 0),
                                (cx - inner_rx, cy - inner_ry, inner_rx * 2, inner_ry * 2))
            surf.blit(ring_surf, (0, 0))
        return surf

    def draw(self, surface):
        surface.blit(self._surface, (0, 0))

    def set_intensity(self, intensity):
        """Regenerate with new intensity (expensive — don't call every frame)."""
        if abs(intensity - self.intensity) > 0.01:
            self.intensity = intensity
            self._surface = self._generate(self.width, self.height, intensity, (0, 0, 0))


# ---------------------------------------------------------------------------
# 7. Hit Flash
# ---------------------------------------------------------------------------

class HitFlash:
    """
    Brief white overlay on entities when hit.

    Usage:
        flash = HitFlash()
        flash.trigger(entity_rect, color=(255,255,255), duration=6)
        flash.update(dt)
        flash.draw(surface)
    """

    def __init__(self):
        self.flashes = []  # [(rect, color, life, max_life)]

    def trigger(self, rect_or_pos, color=(255, 255, 255), duration=6, radius=20):
        """
        Trigger a hit flash.
        rect_or_pos: pygame.Rect or (x, y) tuple.
        """
        if isinstance(rect_or_pos, pygame.Rect):
            rect = rect_or_pos
        else:
            x, y = rect_or_pos
            rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
        self.flashes.append({
            'rect': rect,
            'color': color,
            'life': duration,
            'max_life': duration,
        })

    def update(self, dt):
        for f in self.flashes:
            f['life'] -= dt
        self.flashes[:] = [f for f in self.flashes if f['life'] > 0]

    def draw(self, surface):
        for f in self.flashes:
            alpha = int(255 * (f['life'] / f['max_life']))
            flash_surf = pygame.Surface((f['rect'].width, f['rect'].height), pygame.SRCALPHA)
            flash_surf.fill((*f['color'], alpha))
            surface.blit(flash_surf, f['rect'].topleft, special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------
# 8. Energy Beam (for laser towers)
# ---------------------------------------------------------------------------

class EnergyBeam:
    """
    Thick gradient beam with animated edge particles.

    Usage:
        beam = EnergyBeam((100, 400), (500, 200), color=(255, 50, 50))
        beam.update(dt)
        beam.draw(surface)
    """

    def __init__(self, start, end, color=(255, 50, 50), width=8, particle_rate=3):
        self.start = start
        self.end = end
        self.color = color
        self.width = width
        self.particle_rate = particle_rate
        self._particles = []  # [(x, y, vx, vy, life)]
        self._pulse = 0.0
        self.active = True

    def set_endpoints(self, start, end):
        self.start = start
        self.end = end

    def update(self, dt):
        if not self.active:
            self._particles.clear()
            return
        self._pulse += 0.15 * dt
        # Spawn edge particles
        sx, sy = float(self.start[0]), float(self.start[1])
        ex, ey = float(self.end[0]), float(self.end[1])
        dx, dy = ex - sx, ey - sy
        length = math.sqrt(dx * dx + dy * dy) or 1
        nx, ny = -dy / length, dx / length  # perpendicular

        for _ in range(self.particle_rate):
            t = random.random()
            px = sx + dx * t
            py = sy + dy * t
            side = random.choice([-1, 1])
            offset = self.width * 0.5 * side
            px += nx * offset
            py += ny * offset
            vx = nx * side * random.uniform(0.5, 2.0)
            vy = ny * side * random.uniform(0.5, 2.0)
            self._particles.append([px, py, vx, vy, 1.0])

        # Update particles
        for p in self._particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= 0.05 * dt
        self._particles[:] = [p for p in self._particles if p[4] > 0]

    def draw(self, surface):
        if not self.active:
            return
        s = (int(self.start[0]), int(self.start[1]))
        e = (int(self.end[0]), int(self.end[1]))
        pulse = 0.8 + 0.2 * math.sin(self._pulse)

        # Outer glow
        glow_w = int(self.width * 2.5 * pulse)
        glow_color = tuple(max(0, c // 4) for c in self.color)
        pygame.draw.line(surface, glow_color, s, e, glow_w)

        # Mid layer
        mid_w = int(self.width * 1.5 * pulse)
        mid_color = tuple(max(0, c // 2) for c in self.color)
        pygame.draw.line(surface, mid_color, s, e, mid_w)

        # Core
        core_w = max(2, int(self.width * pulse))
        pygame.draw.line(surface, self.color, s, e, core_w)

        # Hot center
        hot_w = max(1, int(self.width * 0.4 * pulse))
        hot_color = tuple(min(255, c + 100) for c in self.color)
        pygame.draw.line(surface, hot_color, s, e, hot_w)

        # Edge particles
        for p in self._particles:
            alpha = max(0, min(1, p[4]))
            pc = tuple(int(c * alpha) for c in self.color)
            rad = max(1, int(2 * alpha))
            pygame.draw.circle(surface, pc, (int(p[0]), int(p[1])), rad)

        # Impact glow at endpoint
        impact_r = int(self.width * 1.5 * pulse)
        pygame.draw.circle(surface, self.color, e, impact_r)
        pygame.draw.circle(surface, hot_color, e, max(1, impact_r // 2))


# ---------------------------------------------------------------------------
# 9. Shockwave Distortion
# ---------------------------------------------------------------------------

class Shockwave:
    """
    Expanding ring of dots that simulates a shockwave distortion.

    Usage:
        wave = Shockwave(400, 300, color=(255, 200, 100))
        wave.update(dt)
        wave.draw(surface)
    """

    def __init__(self, x, y, color=(255, 200, 100), max_radius=150,
                 speed=6.0, dot_count=40, dot_size=3):
        self.x = x
        self.y = y
        self.color = color
        self.max_radius = max_radius
        self.speed = speed
        self.dot_count = dot_count
        self.dot_size = dot_size
        self.radius = 0.0
        self.life = 1.0
        self.alive = True
        # Pre-compute angles
        self._angles = [2 * math.pi * i / dot_count for i in range(dot_count)]

    def update(self, dt):
        self.radius += self.speed * dt
        self.life = max(0, 1.0 - self.radius / self.max_radius)
        if self.radius >= self.max_radius:
            self.alive = False

    def draw(self, surface):
        if not self.alive or self.radius < 1:
            return
        alpha = self.life
        ring_width = max(2, int(8 * alpha))

        # Draw ring
        c = tuple(int(v * alpha) for v in self.color)
        pygame.draw.circle(surface, c, (int(self.x), int(self.y)), int(self.radius), ring_width)

        # Draw dots along the ring
        dot_alpha = alpha * 0.8
        dot_c = tuple(min(255, int(v * dot_alpha * 1.5)) for v in self.color)
        for angle in self._angles:
            # Slight jitter for organic feel
            r = self.radius + random.uniform(-2, 2)
            dx = math.cos(angle) * r
            dy = math.sin(angle) * r
            pos = (int(self.x + dx), int(self.y + dy))
            size = max(1, int(self.dot_size * alpha))
            pygame.draw.circle(surface, dot_c, pos, size)


class ShockwaveSystem:
    """Manages multiple shockwaves."""

    def __init__(self, max_waves=20):
        self.waves = []
        self.max_waves = max_waves

    def spawn(self, x, y, color=(255, 200, 100), max_radius=150, speed=6.0):
        if len(self.waves) < self.max_waves:
            self.waves.append(Shockwave(x, y, color, max_radius, speed))

    def update(self, dt):
        for w in self.waves:
            w.update(dt)
        self.waves[:] = [w for w in self.waves if w.alive]

    def draw(self, surface):
        for w in self.waves:
            w.draw(surface)


# ---------------------------------------------------------------------------
# 10. Ambient Floating Particles
# ---------------------------------------------------------------------------

class AmbientParticles:
    """
    Small slow-moving background particles for atmosphere.

    Usage:
        ambient = AmbientParticles(1200, 800, count=80)
        ambient.update(dt)
        ambient.draw(surface)
    """

    def __init__(self, width, height, count=80, color=(40, 80, 120),
                 min_size=1, max_size=3, speed=0.5):
        self.width = width
        self.height = height
        self.color = color
        self.min_size = min_size
        self.max_size = max_size
        self.speed = speed
        # Initialize particles: [x, y, vx, vy, size, alpha_phase]
        self.particles = []
        for _ in range(count):
            self._spawn_particle()

    def _spawn_particle(self, x=None, y=None):
        px = x if x is not None else random.uniform(0, self.width)
        py = y if y is not None else random.uniform(0, self.height)
        angle = random.uniform(0, 2 * math.pi)
        spd = self.speed * random.uniform(0.3, 1.5)
        vx = math.cos(angle) * spd
        vy = math.sin(angle) * spd
        size = random.uniform(self.min_size, self.max_size)
        phase = random.uniform(0, 2 * math.pi)
        self.particles.append([px, py, vx, vy, size, phase])

    def update(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[5] += 0.02 * dt  # phase for pulsing alpha

            # Wrap around screen edges
            if p[0] < -10:
                p[0] = self.width + 10
            elif p[0] > self.width + 10:
                p[0] = -10
            if p[1] < -10:
                p[1] = self.height + 10
            elif p[1] > self.height + 10:
                p[1] = -10

    def draw(self, surface):
        for p in self.particles:
            alpha = 0.4 + 0.3 * math.sin(p[5])
            c = tuple(int(v * alpha) for v in self.color)
            pos = (int(p[0]), int(p[1]))
            size = max(1, int(p[4]))
            pygame.draw.circle(surface, c, pos, size)

    def draw_additive(self, surface):
        """Draw with additive blend for glowy effect."""
        temp = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.draw(temp)
        surface.blit(temp, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------
# VFX Manager — ties all effects together
# ---------------------------------------------------------------------------

class VFXManager:
    """
    Central manager for all VFX systems. Instantiated by the engine.

    Usage (from game code):
        engine.vfx.bloom.apply(surface)
        engine.vfx.pulse_rings.spawn(x, y, color)
        engine.vfx.shockwaves.spawn(x, y)
        engine.vfx.hit_flash.trigger(pos)
    """

    def __init__(self, width, height, enable_bloom=True, enable_vignette=True):
        self.width = width
        self.height = height

        # Post-processing
        self.bloom = BloomEffect(width, height) if enable_bloom else None
        self.vignette = Vignette(width, height, intensity=0.5)

        # Effect systems
        self.pulse_rings = PulseRingSystem()
        self.shockwaves = ShockwaveSystem()
        self.hit_flash = HitFlash()
        self.ambient = AmbientParticles(width, height, count=60)
        self.grid = BackgroundGrid(width, height)

        # Active instances (managed per-frame by game code)
        self.beams = []  # list of EnergyBeam
        self.lightnings = []  # list of Lightning
        self.trails = []  # list of NeonTrail

    def update(self, dt):
        """Update all VFX systems. Call once per frame."""
        self.pulse_rings.update(dt)
        self.shockwaves.update(dt)
        self.hit_flash.update(dt)
        self.ambient.update(dt)
        self.grid.update(dt)

        for beam in self.beams:
            beam.update(dt)
        self.beams[:] = [b for b in self.beams if b.active]

        for bolt in self.lightnings:
            bolt.update(dt)
        self.lightnings[:] = [l for l in self.lightnings if l.alive]

    def draw_background(self, surface):
        """Draw background effects (grid, ambient). Call BEFORE game entities."""
        self.grid.draw(surface)
        self.ambient.draw_additive(surface)

    def draw_foreground(self, surface):
        """Draw foreground effects (beams, lightning, rings, flashes). Call AFTER game entities."""
        # Beams
        for beam in self.beams:
            beam.draw(surface)
        # Lightning
        for bolt in self.lightnings:
            bolt.draw(surface)
        # Trails
        for trail in self.trails:
            trail.draw_additive(surface)
        # Pulse rings
        self.pulse_rings.draw(surface)
        # Shockwaves
        self.shockwaves.draw(surface)
        # Hit flashes
        self.hit_flash.draw(surface)

    def draw_post_process(self, surface):
        """Apply post-processing (bloom, vignette). Call LAST."""
        if self.bloom:
            self.bloom.apply(surface)
        if self.vignette:
            self.vignette.draw(surface)

    # --- Convenience spawners ---

    def spawn_beam(self, start, end, color=(255, 50, 50), width=8):
        """Create and register an energy beam. Returns the beam for further control."""
        beam = EnergyBeam(start, end, color, width)
        self.beams.append(beam)
        return beam

    def spawn_lightning(self, start, end, color=(150, 180, 255), life=30):
        """Create and register a lightning bolt."""
        bolt = Lightning(start, end, color, life=life)
        self.lightnings.append(bolt)
        return bolt

    def spawn_trail(self, color=(0, 255, 255), max_length=30):
        """Create and register a neon trail. Returns trail for adding points."""
        trail = NeonTrail(color, max_length)
        self.trails.append(trail)
        return trail

    def remove_trail(self, trail):
        """Remove a trail from the managed list."""
        if trail in self.trails:
            self.trails.remove(trail)

    def flash(self, pos, color=(255, 255, 255), duration=6, radius=20):
        """Trigger a hit flash at position."""
        self.hit_flash.trigger(pos, color, duration, radius)

    def ring(self, x, y, color, max_radius=100, speed=4.0):
        """Spawn a pulse ring."""
        self.pulse_rings.spawn(x, y, color, max_radius, speed)

    def shockwave(self, x, y, color=(255, 200, 100), max_radius=150, speed=6.0):
        """Spawn a shockwave."""
        self.shockwaves.spawn(x, y, color, max_radius, speed)

    def warp_grid(self, x, y, strength=30, radius=150):
        """Add a warp influence to the background grid this frame."""
        self.grid.set_warp_point(x, y, strength, radius)
