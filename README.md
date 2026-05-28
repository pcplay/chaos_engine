# Chaos Engine

A physics-based idle tower defense game built on a custom Python game engine.

Inspired by "Falling Everything" — evolved into a full tower defense with hero combat, elite enemies, boss phases, skill trees, and explosive particle systems.

## How to Play

```bash
pip install pygame numpy
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
| TAB | Open skill tree |
| 1-9, 0, -, = | Select tower to place |
| Left Click | Place tower / Select tower |
| U | Upgrade selected tower |
| X | Sell tower |
| SPACE | Start next wave early |
| M | Mute/Unmute |
| R | Restart (game over) |
| ESC | Cancel / Back |

### Towers (12 types)

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
| 9 | Laser | Continuous beam, damage ramps over time |
| 0 | Tesla | Passive AOE aura, zaps all in range |
| - | Necro | Killed enemies become ghost allies |
| = | Vortex | Gravity well, pulls + slows enemies |

### Tower Synergies

Place two towers within 120px to activate combo bonuses:

| Combo | Synergy | Effect |
|-------|---------|--------|
| Frost + Lightning | Shatter | 3x damage to frozen enemies |
| Flame + Cannon | Napalm | Splash ignites enemies |
| Frost + Sniper | Ice Spike | +50% sniper damage to slowed |
| Lightning + Tesla | Overcharge | +30% range, +2 chains |
| Necro + Chaos | Dark Ritual | Ghosts deal 2x damage |
| Vortex + Cannon | Implosion | +80% splash to pulled enemies |
| Missile + Sniper | Precision Strike | +100% damage below 50% HP |
| Laser + Frost | Cryo Beam | Laser slows + ramps faster |

### Enemies (13 types)

Normal, Fast, Tank, Swarm, Boss, Healer, Shielded, Exploder, Ghost, Splitter, Teleporter, Berserker, Summoner.

### Elite System (Wave 5+)

Enemies can roll elite affixes — glowing rings indicate elites:

| Affix | Effect |
|-------|--------|
| Regenerating | Heals 2% HP/sec |
| Thorny | Reflects 20% damage |
| Phasing | Immune 2s every 8s |
| Sprinter | 3x speed burst every 5s |
| Vampiric | Heals when hitting base |
| Armored | 40% damage reduction |
| Enraged | Stronger when allies die |
| Evasive | 20% dodge chance |

### Boss Phases (Wave 5+ Bosses)

Bosses cycle through 4 phases: Assault → Shield → Summon → Berserk

### Hero Skill Tree (TAB)

30 skill nodes across 3 branches + transformations:

- **ATK** — Damage, attack speed, crit, double strike, tower damage, lifesteal
- **DEF** — Base HP, move speed, gold interest, tower fire rate
- **CHAOS** — Ability cooldowns, ability damage, chaos aura, chain explosions

### Hero Transformations (Ultimate Forms)

Unlock via skill tree end nodes:

| Form | Branch | Effect |
|------|--------|--------|
| Berserker | ATK | 2.5x damage, attacks explode |
| Shadow | DEF | Invisible, 2x speed, backstab 5x every 3rd hit |
| Chaos Incarnate | CHAOS | No cooldowns, chaos field damages all enemies |

### Chaos Events (Wave 3+)

Random events every 15 seconds: double speed, gold rain, tower frenzy, path scramble, freeze all, surprise boss, MEGA EXPLOSION, gravity flip.

## Architecture

```
chaos_engine/
├── main.py                      # Entry point + game state
├── config.json                  # Tunable parameters
├── build.py                     # PyInstaller build script
├── .github/workflows/
│   └── release.yml              # CI: auto-build exe on tag push
├── game/                        # Game modules
│   ├── states.py                # State machine
│   ├── menu.py                  # Title, settings, controls screens
│   ├── skill_tree.py            # 30-node skill web
│   ├── enemies.py               # 13 enemy types + procedural sprites
│   ├── towers.py                # 12 tower types + projectiles + ghost allies
│   ├── elites.py                # Elite affixes, boss phases, difficulty scaling
│   ├── synergies.py             # Tower synergies + hero transformations
│   └── constants.py             # Colors + shared constants
└── commons/chaos_engine/        # Engine library
    ├── core.py                  # ChaosEngine master class
    ├── particles.py             # 8 explosion types, particle system
    ├── physics.py               # PhysicsBody, collisions, springs, attractors
    ├── chaos.py                 # ChaosField with 8 chaos modes
    ├── entities.py              # Entity + EntityManager (ECS-lite)
    ├── rendering.py             # Camera (resolution scaling), shake, trails
    ├── audio.py                 # Procedural SFX + BGM generation
    ├── ui.py                    # HUD renderer (bars, cooldowns, overlays)
    └── config.py                # JSON config loader with defaults
```

### Engine Features

- **Resizable window** — renders to logical resolution, scales to any window size
- **Particle system** — 8 explosion types + chain explosions
- **Procedural audio** — all SFX and BGM generated mathematically (no audio files)
- **Physics** — bodies, elastic collisions, springs, attractors
- **Chaos field** — 8 modes (random, vortex, explosion, reverse, orbital, spiral, pulse, earthquake)
- **State machine** — stack-based game states with overlay support
- **Config-driven** — all parameters tunable via `config.json`

## Building Executable

```bash
pip install pyinstaller
python build.py
# Output: dist/ChaosEngine.exe
```

Or push a version tag — GitHub Actions builds automatically:
```bash
git tag -a v0.0.2 -m "Release v0.0.2"
git push origin v0.0.2
```

## Tech Stack

- Python 3
- Pygame 2
- NumPy (audio generation)

## Releases

- **v0.0.2** — Elite enemies, boss phases, hero transformations, tower synergies, 30-node skill tree
- **v0.0.1** — Initial release: 12 towers, 13 enemies, skill tree, menu system, procedural audio
