# Chaos Engine

A physics-based idle tower defense game built on a custom Python game engine.

Inspired by "Falling Everything" — evolved into a full tower defense with hero combat, chaos mechanics, and explosive particle systems.

## How to Play

```bash
pip install pygame
python main.py
```

### Controls

| Key | Action |
|-----|--------|
| WASD / Arrows | Move hero |
| Right Click | Manual attack (2.5x damage) |
| Q | Whirlwind (AOE slash) |
| T | Rally (buff tower fire rate) |
| E | Execute (% HP finisher) |
| F | Chaos Overload (massive AOE + knockback) |
| 1-8 | Select tower to place |
| Left Click | Place tower / Select tower |
| U | Upgrade selected tower |
| X | Sell selected tower |
| SPACE | Start next wave early |
| R | Restart (game over screen) |
| ESC | Cancel placement |

### Towers

| # | Tower | Effect |
|---|-------|--------|
| 1 | Arrow | Fast single target |
| 2 | Cannon | Splash AOE with recoil |
| 3 | Frost | Slows enemies |
| 4 | Lightning | Chain hits 3+ targets |
| 5 | Sniper | Long range, massive single hit |
| 6 | Chaos | Random effect every shot |
| 7 | Flame | Continuous fire stream, burn DOT |
| 8 | Missile | Homing + huge explosion |

### Enemies

Introduced across waves: Normal, Fast, Swarm, Tank, Healer, Exploder, Shielded, Ghost, Boss (every 5 waves).

### Chaos Events (Wave 3+)

Random events every 15 seconds: double speed, gold rain, tower frenzy, path scramble, freeze all, surprise boss, MEGA EXPLOSION, and more.

## Architecture

```
chaos_engine/
├── main.py                      # Game (tower defense)
├── config.json                  # Tunable parameters
└── commons/chaos_engine/        # Engine library
    ├── core.py                  # ChaosEngine master class
    ├── particles.py             # 8 explosion types, particle system
    ├── physics.py               # PhysicsBody, collisions, springs, attractors
    ├── chaos.py                 # ChaosField with 8 chaos modes
    ├── entities.py              # Entity + EntityManager (ECS-lite)
    ├── rendering.py             # Camera (resolution scaling), shake, trails
    ├── ui.py                    # HUD renderer (bars, cooldowns, overlays)
    └── config.py                # JSON config loader with defaults
```

### Engine Features

- **Resizable window** — renders to logical resolution, scales to any window size
- **Particle system** — 8 explosion types (burst, ring, firework, shockwave, nova, sparks, confetti, directional) + chain explosions
- **Physics** — bodies, elastic collisions, springs with strain/break, attractors/repulsors
- **Chaos field** — 8 modes (random, vortex, explosion, reverse, orbital, spiral, pulse, earthquake)
- **Entity system** — tag-based queries, radius search, auto-cleanup
- **Screen shake** — configurable intensity and decay
- **Config-driven** — all parameters tunable via `config.json`

### Using the Engine

```python
from commons.chaos_engine import ChaosEngine, ExplosionType, add_shake

engine = ChaosEngine("My Game", "config.json")

while engine.running:
    surface = engine.begin_frame()
    events = engine.process_events()
    
    # Your game logic here
    engine.particles.explode(400, 300, (255, 50, 50), ExplosionType.NOVA, 2.0)
    add_shake(10)
    
    engine.update_systems()
    engine.particles.draw(surface)
    engine.end_frame()

engine.quit()
```

## Tech Stack

- Python 3
- Pygame 2
- No external dependencies beyond pygame

## Roadmap

- Sound effects + music
- More tower types
- Skill tree for hero
- Endless mode with leaderboard
- Map editor
- Multiplayer co-op
