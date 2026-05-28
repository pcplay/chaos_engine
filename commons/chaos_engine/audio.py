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

        # BGM
        self._bgm_generator = BGMGenerator(sample_rate=22050)

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
        if self.muted:
            self._music_channel.set_volume(0)
        else:
            self._music_channel.set_volume(self.master_volume * self.music_volume)
        return self.muted

    def stop_all(self):
        pygame.mixer.stop()

    def play_bgm(self, bars=8):
        """Generate and loop procedural chaos BGM."""
        bgm = self._bgm_generator.generate(bars)
        bgm.set_volume(self.master_volume * self.music_volume)
        self._music_channel.play(bgm, loops=-1)

    def stop_bgm(self):
        self._music_channel.stop()


class BGMGenerator:
    """Generates procedural background music — dark electronic chaos vibes."""

    def __init__(self, sample_rate=22050, bpm=140):
        self.sample_rate = sample_rate
        self.bpm = bpm
        self.beat_samples = int(sample_rate * 60 / bpm)

    def _sine(self, freq, samples):
        t = np.arange(samples) / self.sample_rate
        return np.sin(2 * np.pi * freq * t)

    def _saw(self, freq, samples):
        t = np.arange(samples) / self.sample_rate
        return 2 * (t * freq - np.floor(t * freq + 0.5))

    def _square(self, freq, samples, duty=0.5):
        t = np.arange(samples) / self.sample_rate
        return np.sign(np.sin(2 * np.pi * freq * t) + (duty - 0.5) * 2)

    def _noise_filtered(self, samples, cutoff=0.1):
        noise = np.random.uniform(-1, 1, samples)
        # Simple low-pass via moving average
        kernel_size = max(1, int(1 / cutoff))
        kernel = np.ones(kernel_size) / kernel_size
        return np.convolve(noise, kernel, mode='same')

    def _kick(self):
        """Punchy kick drum."""
        samples = self.beat_samples // 2
        t = np.arange(samples) / self.sample_rate
        # Pitch drops fast from 150hz to 40hz
        freq = 150 * np.exp(-30 * t) + 40
        phase = 2 * np.pi * np.cumsum(freq) / self.sample_rate
        osc = np.sin(phase)
        # Envelope — sharp attack, fast decay
        env = np.exp(-8 * t)
        # Click transient
        click = np.random.uniform(-1, 1, min(100, samples)) * np.exp(-50 * np.arange(min(100, samples)) / self.sample_rate)
        result = np.zeros(samples)
        result[:len(click)] += click * 0.4
        result += osc * env * 0.8
        return result

    def _snare(self):
        """Snare — noise + tone body."""
        samples = self.beat_samples // 3
        t = np.arange(samples) / self.sample_rate
        noise = np.random.uniform(-1, 1, samples)
        tone = self._sine(200, samples)
        env = np.exp(-15 * t)
        return (noise * 0.6 + tone * 0.4) * env * 0.5

    def _hihat(self, open_hat=False):
        """Hi-hat — filtered noise."""
        length = self.beat_samples // (4 if not open_hat else 2)
        t = np.arange(length) / self.sample_rate
        noise = np.random.uniform(-1, 1, length)
        # High-pass feel by subtracting low-pass
        kernel = np.ones(3) / 3
        low = np.convolve(noise, kernel, mode='same')
        hp_noise = noise - low
        decay = 30 if not open_hat else 8
        env = np.exp(-decay * t)
        return hp_noise * env * 0.3

    def _bass_line(self, bars=4):
        """Dark pulsing bass — chaos scale."""
        # Chaos-appropriate notes (minor + diminished)
        notes = [55, 58.27, 65.41, 73.42, 82.41, 87.31, 98.00, 110]
        total_samples = self.beat_samples * 4 * bars
        result = np.zeros(total_samples)

        beat_count = 4 * bars
        for i in range(beat_count):
            note = random.choice(notes)
            start = i * self.beat_samples
            length = self.beat_samples
            t = np.arange(length) / self.sample_rate

            # Saw wave for grit
            osc = self._saw(note, length)
            # Sub bass
            sub = self._sine(note * 0.5, length)
            # Envelope — pumping sidechained feel
            env = np.exp(-3 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t))

            end = min(start + length, total_samples)
            actual_len = end - start
            result[start:end] += (osc[:actual_len] * 0.3 + sub[:actual_len] * 0.4) * env[:actual_len]

        return result * 0.4

    def _lead_synth(self, bars=4):
        """Chaotic lead — arpeggiated, glitchy."""
        # Minor pentatonic + chaos intervals
        scale = [220, 261.6, 293.7, 329.6, 392, 440, 523.3, 587.3, 659.3, 784]
        total_samples = self.beat_samples * 4 * bars
        result = np.zeros(total_samples)

        # 16th note arpeggios
        sixteenth = self.beat_samples // 4
        num_notes = total_samples // sixteenth

        for i in range(num_notes):
            # Occasional rests for rhythm
            if random.random() < 0.3:
                continue

            note = random.choice(scale)
            # Occasional octave jump
            if random.random() < 0.2:
                note *= 2
            # Occasional glitch — pitch bend
            if random.random() < 0.1:
                note *= random.choice([0.95, 1.05, 1.5, 0.75])

            start = i * sixteenth
            length = int(sixteenth * random.uniform(0.5, 0.9))
            if start + length > total_samples:
                break

            t = np.arange(length) / self.sample_rate
            # Mix saw + square for grit
            osc = self._saw(note, length) * 0.5 + self._square(note, length) * 0.3
            # Fast decay envelope
            env = np.exp(-10 * t)
            # Slight vibrato
            vibrato = 1 + 0.01 * np.sin(2 * np.pi * 6 * t)

            end = min(start + length, total_samples)
            actual_len = end - start
            result[start:end] += osc[:actual_len] * env[:actual_len] * vibrato[:actual_len]

        return result * 0.15

    def _pad(self, bars=4):
        """Dark ambient pad — slowly evolving."""
        total_samples = self.beat_samples * 4 * bars
        t = np.arange(total_samples) / self.sample_rate

        # Minor chord drone
        freqs = [110, 130.81, 164.81, 220]
        pad = np.zeros(total_samples)
        for f in freqs:
            # Detuned for width
            pad += self._sine(f * 1.002, total_samples) * 0.15
            pad += self._sine(f * 0.998, total_samples) * 0.15

        # Slow LFO modulation
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t)
        pad *= lfo

        # Filter sweep
        sweep = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t)
        # Simulate filter with amplitude modulation of harmonics
        pad *= (0.3 + 0.7 * sweep)

        return pad * 0.2

    def _drum_pattern(self, bars=4):
        """4-bar drum loop — kicks, snares, hats."""
        total_samples = self.beat_samples * 4 * bars
        result = np.zeros(total_samples)

        for bar in range(bars):
            for beat in range(4):
                pos = (bar * 4 + beat) * self.beat_samples

                # Kick on 1 and 3
                if beat in [0, 2]:
                    kick = self._kick()
                    end = min(pos + len(kick), total_samples)
                    result[pos:end] += kick[:end - pos]

                # Snare on 2 and 4
                if beat in [1, 3]:
                    snare = self._snare()
                    end = min(pos + len(snare), total_samples)
                    result[pos:end] += snare[:end - pos]

                # Hi-hats on every 8th
                for eighth in range(2):
                    hat_pos = pos + eighth * (self.beat_samples // 2)
                    if hat_pos >= total_samples:
                        break
                    is_open = (beat == 1 and eighth == 1)
                    hat = self._hihat(open_hat=is_open)
                    end = min(hat_pos + len(hat), total_samples)
                    result[hat_pos:end] += hat[:end - hat_pos]

                # Extra chaos hits — random ghost notes
                if random.random() < 0.3:
                    ghost_pos = pos + random.randint(0, self.beat_samples - 1)
                    if ghost_pos < total_samples - 200:
                        ghost = self._hihat() * 0.4
                        end = min(ghost_pos + len(ghost), total_samples)
                        result[ghost_pos:end] += ghost[:end - ghost_pos]

        return result

    def generate(self, bars=8):
        """Generate a full BGM loop."""
        drums = self._drum_pattern(bars)
        bass = self._bass_line(bars)
        lead = self._lead_synth(bars)
        pad = self._pad(bars)

        # Mix to same length
        length = min(len(drums), len(bass), len(lead), len(pad))
        mix = drums[:length] + bass[:length] + lead[:length] + pad[:length]

        # Master compression (soft clip)
        mix = np.tanh(mix * 1.5) * 0.7

        # Convert to pygame sound
        mix = np.clip(mix, -1.0, 1.0)
        audio = (mix * 32767).astype(np.int16)
        stereo = np.column_stack((audio, audio))
        return pygame.sndarray.make_sound(stereo)
