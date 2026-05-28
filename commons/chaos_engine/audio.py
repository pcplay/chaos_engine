"""
Chaos Engine Audio System
Procedural sound generation + mixer management.
No external audio files needed — generates all SFX mathematically.
"""
import pygame
import numpy as np
import math
import random
from enum import Enum


class SoundType(Enum):
    SHOOT = "shoot"
    EXPLOSION = "explosion"
    HIT = "hit"
    LASER = "laser"
    FROST = "frost"
    LIGHTNING = "lightning"
    MISSILE_LAUNCH = "missile_launch"
    FLAME = "flame"
    POWERUP = "powerup"
    LEVELUP = "levelup"
    WAVE_START = "wave_start"
    WAVE_CLEAR = "wave_clear"
    DAMAGE_TAKEN = "damage_taken"
    DEATH = "death"
    PLACE_TOWER = "place_tower"
    UPGRADE = "upgrade"
    SELL = "sell"
    CHAOS_EVENT = "chaos_event"
    UI_CLICK = "ui_click"
    COIN = "coin"


class SoundGenerator:
    """Generates sound effects procedurally using numpy."""

    def __init__(self, sample_rate=22050):
        self.sample_rate = sample_rate

    def _make_sound(self, samples):
        samples = np.clip(samples, -1.0, 1.0)
        audio = (samples * 32767).astype(np.int16)
        # Stereo
        stereo = np.column_stack((audio, audio))
        sound = pygame.sndarray.make_sound(stereo)
        return sound

    def _envelope(self, length, attack=0.01, decay=0.1, sustain=0.3, release=0.5):
        """ADSR envelope."""
        samples = int(length * self.sample_rate)
        env = np.zeros(samples)
        attack_s = int(attack * samples)
        decay_s = int(decay * samples)
        release_s = int(release * samples)
        sustain_s = samples - attack_s - decay_s - release_s

        # Attack
        if attack_s > 0:
            env[:attack_s] = np.linspace(0, 1, attack_s)
        # Decay
        if decay_s > 0:
            env[attack_s:attack_s + decay_s] = np.linspace(1, sustain, decay_s)
        # Sustain
        if sustain_s > 0:
            env[attack_s + decay_s:attack_s + decay_s + sustain_s] = sustain
        # Release
        if release_s > 0:
            env[-release_s:] = np.linspace(sustain, 0, release_s)

        return env

    def _noise(self, length):
        samples = int(length * self.sample_rate)
        return np.random.uniform(-1, 1, samples)

    def _sine(self, freq, length):
        t = np.linspace(0, length, int(length * self.sample_rate), endpoint=False)
        return np.sin(2 * np.pi * freq * t)

    def _square(self, freq, length):
        return np.sign(self._sine(freq, length))

    def _saw(self, freq, length):
        t = np.linspace(0, length, int(length * self.sample_rate), endpoint=False)
        return 2 * (t * freq - np.floor(t * freq + 0.5))

    def _freq_sweep(self, start_freq, end_freq, length):
        t = np.linspace(0, length, int(length * self.sample_rate), endpoint=False)
        freq = np.linspace(start_freq, end_freq, len(t))
        phase = 2 * np.pi * np.cumsum(freq) / self.sample_rate
        return np.sin(phase)

    def shoot(self, pitch=1.0):
        length = 0.08
        sweep = self._freq_sweep(800 * pitch, 200 * pitch, length)
        env = self._envelope(length, attack=0.005, decay=0.3, sustain=0.0, release=0.7)
        noise = self._noise(length) * 0.15
        return self._make_sound((sweep + noise) * env * 0.4)

    def explosion(self, size=1.0):
        length = 0.4 * size
        noise = self._noise(length)
        # Low-pass by averaging
        kernel_size = int(5 * size)
        if kernel_size > 1:
            kernel = np.ones(kernel_size) / kernel_size
            noise = np.convolve(noise, kernel, mode='same')
        bass = self._sine(40 / size, length) * 0.5
        env = self._envelope(length, attack=0.005, decay=0.2, sustain=0.1, release=0.7)
        return self._make_sound((noise * 0.7 + bass) * env * 0.5)

    def hit(self):
        length = 0.06
        sweep = self._freq_sweep(600, 150, length)
        noise = self._noise(length) * 0.3
        env = self._envelope(length, attack=0.005, decay=0.4, sustain=0.0, release=0.6)
        return self._make_sound((sweep + noise) * env * 0.35)

    def laser(self, pitch=1.0):
        length = 0.15
        sweep = self._freq_sweep(1200 * pitch, 400 * pitch, length)
        env = self._envelope(length, attack=0.005, decay=0.2, sustain=0.1, release=0.7)
        return self._make_sound(sweep * env * 0.3)

    def frost(self):
        length = 0.2
        noise = self._noise(length)
        # High-pass feel
        high = self._sine(3000, length) * 0.2
        sweep = self._freq_sweep(4000, 1000, length) * 0.3
        env = self._envelope(length, attack=0.02, decay=0.3, sustain=0.2, release=0.5)
        return self._make_sound((noise * 0.3 + high + sweep) * env * 0.25)

    def lightning(self):
        length = 0.15
        # Crackle = short noise bursts
        samples = int(length * self.sample_rate)
        signal = np.zeros(samples)
        for _ in range(5):
            start = random.randint(0, samples - 100)
            burst_len = random.randint(20, 80)
            signal[start:start + burst_len] = np.random.uniform(-1, 1, burst_len)
        buzz = self._square(120, length) * 0.3
        env = self._envelope(length, attack=0.001, decay=0.3, sustain=0.1, release=0.6)
        return self._make_sound((signal * 0.6 + buzz) * env * 0.4)

    def missile_launch(self):
        length = 0.3
        sweep = self._freq_sweep(100, 600, length)
        noise = self._noise(length) * 0.4
        env = self._envelope(length, attack=0.02, decay=0.1, sustain=0.5, release=0.4)
        return self._make_sound((sweep * 0.5 + noise) * env * 0.35)

    def flame(self):
        length = 0.12
        noise = self._noise(length)
        # Filtered noise for whoosh
        kernel = np.ones(3) / 3
        noise = np.convolve(noise, kernel, mode='same')
        env = self._envelope(length, attack=0.01, decay=0.2, sustain=0.4, release=0.4)
        return self._make_sound(noise * env * 0.2)

    def powerup(self):
        length = 0.3
        # Rising arpeggio
        t = np.linspace(0, length, int(length * self.sample_rate), endpoint=False)
        freq = 400 + 800 * (t / length)
        signal = np.sin(2 * np.pi * np.cumsum(freq) / self.sample_rate)
        harmonics = np.sin(4 * np.pi * np.cumsum(freq) / self.sample_rate) * 0.3
        env = self._envelope(length, attack=0.01, decay=0.1, sustain=0.6, release=0.3)
        return self._make_sound((signal + harmonics) * env * 0.3)

    def levelup(self):
        length = 0.5
        # Major chord arpeggio
        t = np.linspace(0, length, int(length * self.sample_rate), endpoint=False)
        notes = [523, 659, 784, 1047]  # C5, E5, G5, C6
        signal = np.zeros_like(t)
        note_len = len(t) // len(notes)
        for i, freq in enumerate(notes):
            start = i * note_len
            end = min(start + note_len, len(t))
            signal[start:end] = np.sin(2 * np.pi * freq * t[start:end])
        env = self._envelope(length, attack=0.01, decay=0.05, sustain=0.7, release=0.25)
        return self._make_sound(signal * env * 0.3)

    def wave_start(self):
        length = 0.4
        # Alarm-like rising tone
        sweep = self._freq_sweep(300, 800, length)
        pulse = self._square(4, length) * 0.3
        env = self._envelope(length, attack=0.05, decay=0.1, sustain=0.5, release=0.35)
        return self._make_sound((sweep * 0.6 + pulse * sweep) * env * 0.3)

    def wave_clear(self):
        length = 0.6
        # Triumphant fanfare
        t = np.linspace(0, length, int(length * self.sample_rate), endpoint=False)
        signal = (np.sin(2 * np.pi * 523 * t) * 0.4 +
                  np.sin(2 * np.pi * 659 * t) * 0.3 +
                  np.sin(2 * np.pi * 784 * t) * 0.3)
        env = self._envelope(length, attack=0.02, decay=0.1, sustain=0.5, release=0.38)
        return self._make_sound(signal * env * 0.3)

    def damage_taken(self):
        length = 0.15
        sweep = self._freq_sweep(400, 100, length)
        noise = self._noise(length) * 0.5
        env = self._envelope(length, attack=0.001, decay=0.3, sustain=0.0, release=0.7)
        return self._make_sound((sweep + noise) * env * 0.5)

    def death(self):
        length = 0.8
        sweep = self._freq_sweep(300, 30, length)
        noise = self._noise(length) * 0.4
        env = self._envelope(length, attack=0.01, decay=0.15, sustain=0.3, release=0.54)
        return self._make_sound((sweep * 0.6 + noise) * env * 0.4)

    def place_tower(self):
        length = 0.12
        tone = self._sine(800, length)
        tone2 = self._sine(1200, length) * 0.5
        env = self._envelope(length, attack=0.005, decay=0.3, sustain=0.0, release=0.7)
        return self._make_sound((tone + tone2) * env * 0.25)

    def upgrade(self):
        length = 0.25
        # Rising shimmer
        sweep = self._freq_sweep(600, 1500, length)
        shimmer = self._sine(2400, length) * 0.2
        env = self._envelope(length, attack=0.01, decay=0.1, sustain=0.4, release=0.49)
        return self._make_sound((sweep + shimmer) * env * 0.3)

    def sell(self):
        length = 0.15
        sweep = self._freq_sweep(1000, 400, length)
        env = self._envelope(length, attack=0.005, decay=0.3, sustain=0.0, release=0.7)
        return self._make_sound(sweep * env * 0.25)

    def chaos_event(self):
        length = 0.5
        samples = int(length * self.sample_rate)
        # Distorted warning — two sweeps joined
        half = samples // 2
        t1 = np.linspace(0, 1, half, endpoint=False)
        t2 = np.linspace(0, 1, samples - half, endpoint=False)
        sweep1 = np.sin(2 * np.pi * (200 + 600 * t1) * np.cumsum(np.ones(half)) / self.sample_rate)
        sweep2 = np.sin(2 * np.pi * (800 - 600 * t2) * np.cumsum(np.ones(samples - half)) / self.sample_rate)
        combined = np.concatenate([sweep1, sweep2])
        noise = np.random.uniform(-1, 1, samples) * 0.3
        env = self._envelope(length, attack=0.01, decay=0.1, sustain=0.5, release=0.39)
        # Ensure same length
        min_len = min(len(combined), len(noise), len(env))
        return self._make_sound((combined[:min_len] * 0.6 + noise[:min_len]) * env[:min_len] * 0.35)

    def ui_click(self):
        length = 0.04
        tone = self._sine(1000, length)
        env = self._envelope(length, attack=0.005, decay=0.5, sustain=0.0, release=0.5)
        return self._make_sound(tone * env * 0.2)

    def coin(self):
        length = 0.1
        tone = self._sine(1800, length)
        tone2 = self._sine(2200, length * 0.5)
        padded = np.zeros(int(length * self.sample_rate))
        padded[:len(tone2)] = tone2
        env = self._envelope(length, attack=0.005, decay=0.3, sustain=0.0, release=0.7)
        return self._make_sound((tone * 0.5 + padded * 0.5) * env * 0.2)


class AudioEngine:
    """Manages sound playback, channels, volume, and pooling."""

    def __init__(self, num_channels=32, master_volume=0.7):
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(num_channels)
        self.master_volume = master_volume
        self.sfx_volume = 0.8
        self.music_volume = 0.5
        self.muted = False
        self.generator = SoundGenerator()

        # Pre-generate sound pool
        self._cache = {}
        self._generate_cache()

        # Channel groups
        self._sfx_channels = [pygame.mixer.Channel(i) for i in range(num_channels - 4)]
        self._music_channel = pygame.mixer.Channel(num_channels - 1)
        self._next_channel = 0

    def _generate_cache(self):
        """Pre-generate all sound variations."""
        # Multiple variations per sound type for less repetition
        self._cache[SoundType.SHOOT] = [self.generator.shoot(p) for p in [0.8, 1.0, 1.2]]
        self._cache[SoundType.EXPLOSION] = [self.generator.explosion(s) for s in [0.7, 1.0, 1.5, 2.0]]
        self._cache[SoundType.HIT] = [self.generator.hit() for _ in range(3)]
        self._cache[SoundType.LASER] = [self.generator.laser(p) for p in [0.9, 1.0, 1.1]]
        self._cache[SoundType.FROST] = [self.generator.frost() for _ in range(2)]
        self._cache[SoundType.LIGHTNING] = [self.generator.lightning() for _ in range(3)]
        self._cache[SoundType.MISSILE_LAUNCH] = [self.generator.missile_launch()]
        self._cache[SoundType.FLAME] = [self.generator.flame() for _ in range(2)]
        self._cache[SoundType.POWERUP] = [self.generator.powerup()]
        self._cache[SoundType.LEVELUP] = [self.generator.levelup()]
        self._cache[SoundType.WAVE_START] = [self.generator.wave_start()]
        self._cache[SoundType.WAVE_CLEAR] = [self.generator.wave_clear()]
        self._cache[SoundType.DAMAGE_TAKEN] = [self.generator.damage_taken()]
        self._cache[SoundType.DEATH] = [self.generator.death()]
        self._cache[SoundType.PLACE_TOWER] = [self.generator.place_tower()]
        self._cache[SoundType.UPGRADE] = [self.generator.upgrade()]
        self._cache[SoundType.SELL] = [self.generator.sell()]
        self._cache[SoundType.CHAOS_EVENT] = [self.generator.chaos_event()]
        self._cache[SoundType.UI_CLICK] = [self.generator.ui_click()]
        self._cache[SoundType.COIN] = [self.generator.coin()]

    def play(self, sound_type, volume=1.0):
        """Play a sound effect."""
        if self.muted:
            return
        if sound_type not in self._cache:
            return

        variations = self._cache[sound_type]
        sound = random.choice(variations)

        final_vol = self.master_volume * self.sfx_volume * volume
        sound.set_volume(final_vol)

        # Find free channel
        channel = self._get_channel()
        if channel:
            channel.play(sound)

    def _get_channel(self):
        """Round-robin channel allocation."""
        for _ in range(len(self._sfx_channels)):
            ch = self._sfx_channels[self._next_channel]
            self._next_channel = (self._next_channel + 1) % len(self._sfx_channels)
            if not ch.get_busy():
                return ch
        # All busy — steal oldest
        ch = self._sfx_channels[self._next_channel]
        self._next_channel = (self._next_channel + 1) % len(self._sfx_channels)
        return ch

    def set_master_volume(self, vol):
        self.master_volume = max(0, min(1, vol))

    def set_sfx_volume(self, vol):
        self.sfx_volume = max(0, min(1, vol))

    def set_music_volume(self, vol):
        self.music_volume = max(0, min(1, vol))

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted

    def stop_all(self):
        pygame.mixer.stop()
