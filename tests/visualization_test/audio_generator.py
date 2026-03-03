"""
Audio waveform generator for visualization testing.
Simulates realistic voice-like audio data using Brownian motion and multi-scale modulation.
"""

import numpy as np
from dataclasses import dataclass
from collections import deque
import time
from typing import List


@dataclass
class AudioState:
    """Shared audio state for all visualization patterns."""

    volume: float  # Current RMS, 0.0-1.0
    history: deque  # Ring buffer, most recent last
    peak: float  # Recent peak (for color mapping)
    time_s: float  # Monotonic time (for phase animation)


class WaveformGenerator:
    """Generates realistic voice-like waveform data for testing.

    Uses fractional Brownian motion with multiple time scales to simulate
    organic voice patterns including:
    - Fast jitter (formant variations, ~10-50ms)
    - Medium modulation (syllables, ~100-300ms)
    - Slow phrases (breathing pauses, ~1-4s)
    - Fricative bursts (sudden high-amplitude spikes)
    """

    def __init__(self, history_size: int = 64):
        self.history_size = history_size
        self.history = deque([0.0] * history_size, maxlen=history_size)
        self.start_time = time.monotonic()
        self.is_playing = False

        # Multi-scale Brownian motion state
        self.fast_state = 0.0  # ~20-50ms variations (formants)
        self.medium_state = 0.0  # ~100-300ms variations (syllables)
        self.slow_state = 0.0  # ~1-4s variations (phrases)

        # Phrase state
        self.phrase_active = False
        self.next_phrase_start = 0.0
        self.phrase_end_time = 0.0

        # Smoothing
        self.smoothing_factor = 0.3
        self.current_volume = 0.0

        # Burst generation
        self.burst_cooldown = 0.0

    def toggle_playback(self) -> bool:
        """Toggle play/pause. Returns new state."""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.next_phrase_start = time.monotonic() - self.start_time + 0.3
        return self.is_playing

    def update(self) -> AudioState:
        """Update and return current audio state."""
        current_time = time.monotonic() - self.start_time
        dt = 0.016  # ~60 FPS

        if not self.is_playing:
            # Decay to silence when paused
            self.current_volume *= 0.85
            self.history.append(self.current_volume)
            return AudioState(
                volume=self.current_volume,
                history=deque(self.history, maxlen=self.history_size),
                peak=max(self.history) if self.history else 0.0,
                time_s=current_time,
            )

        # Generate multi-scale Brownian motion
        base_volume = self._generate_voice_volume(current_time, dt)

        # Add fricative bursts
        burst = self._generate_burst(current_time, dt)

        # Add fast jitter (formant-like modulation)
        jitter = np.random.normal(0, 0.03) * (0.5 + 0.5 * base_volume)

        # Combine components
        instantaneous = base_volume + burst + jitter
        instantaneous = np.clip(instantaneous, 0.0, 1.0)

        # Apply smoothing
        self.current_volume = (
            self.current_volume * (1 - self.smoothing_factor)
            + instantaneous * self.smoothing_factor
        )
        self.current_volume = np.clip(self.current_volume, 0.0, 1.0)

        # Update history
        self.history.append(self.current_volume)

        return AudioState(
            volume=self.current_volume,
            history=deque(self.history, maxlen=self.history_size),
            peak=max(self.history) if self.history else 0.0,
            time_s=current_time,
        )

    def _generate_voice_volume(self, t: float, dt: float) -> float:
        """Generate voice-like volume using multi-scale Brownian motion."""

        # Update phrase state (breathing pattern)
        if not self.phrase_active:
            if t >= self.next_phrase_start:
                # Start a new phrase
                self.phrase_active = True
                phrase_duration = np.random.uniform(
                    0.8, 2.5
                )  # 0.8-2.5 seconds of speech
                self.phrase_end_time = t + phrase_duration
                # Reset states for new phrase
                self.slow_state = 0.1
                self.medium_state = 0.0
                self.fast_state = 0.0
        else:
            if t >= self.phrase_end_time:
                # End phrase, start pause
                self.phrase_active = False
                pause_duration = np.random.uniform(0.2, 1.0)  # 0.2-1.0 second pause
                self.next_phrase_start = t + pause_duration
                self.slow_state = 0.0
                return 0.0

        if not self.phrase_active:
            return 0.0

        # Slow variation (phrase-level energy contour)
        # Random walk with mean reversion
        slow_target = 0.4 + 0.3 * np.sin(t * 0.5)  # Gentle rise/fall
        slow_noise = np.random.normal(0, 0.02)
        self.slow_state += (slow_target - self.slow_state) * 0.1 + slow_noise
        self.slow_state = np.clip(self.slow_state, 0.15, 0.9)

        # Medium variation (syllable-level)
        # Faster random walk for syllable boundaries
        medium_noise = np.random.normal(0, 0.05)
        self.medium_state += medium_noise - self.medium_state * 0.1  # Mean reversion
        self.medium_state = np.clip(self.medium_state, -0.3, 0.3)

        # Fast variation (formant jitter)
        fast_noise = np.random.normal(0, 0.08)
        self.fast_state += fast_noise - self.fast_state * 0.3  # Quick mean reversion
        self.fast_state = np.clip(self.fast_state, -0.15, 0.15)

        # Combine scales with different weights
        combined = (
            self.slow_state * 0.7  # Base energy level
            + self.medium_state * 0.25  # Syllable modulation
            + self.fast_state * 0.05  # Fine texture
        )

        return np.clip(combined, 0.0, 1.0)

    def _generate_burst(self, t: float, dt: float) -> float:
        """Generate occasional fricative bursts (s, sh, t, p sounds)."""
        # Cooldown prevents too many bursts
        if self.burst_cooldown > 0:
            self.burst_cooldown -= dt
            return 0.0

        # Only burst during active phrases
        if not self.phrase_active:
            return 0.0

        # Random chance for burst (more likely at higher energy)
        burst_chance = 0.005 + 0.02 * self.slow_state
        if np.random.random() < burst_chance:
            # Generate burst
            burst_intensity = np.random.uniform(0.1, 0.4)
            burst_duration = np.random.uniform(0.03, 0.08)  # 30-80ms
            self.burst_cooldown = burst_duration + np.random.uniform(0.1, 0.3)
            return burst_intensity

        return 0.0
