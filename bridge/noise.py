"""
Background Office Noise Generator & Mixer
==========================================

Generates subtle office ambience with keyboard typing sounds and mixes
it into outgoing TTS audio. Always-on typing creates an immersive
"calling a real office" feel similar to Retell AI.
"""

import os
import numpy as np
import scipy.signal
import logging

logger = logging.getLogger("office-noise")

# Volume of background noise relative to speech (0.0 = silent, 1.0 = full)
NOISE_VOLUME = float(os.getenv("OFFICE_NOISE_VOLUME", "0.03"))

# Duration of the looping noise buffer in seconds
_BUFFER_DURATION_SEC = 10


def _generate_pink_noise(num_samples: int) -> np.ndarray:
    """Generate pink noise (1/f spectrum) using the Voss-McCartney algorithm."""
    white = np.random.randn(num_samples)
    b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004709510])
    a = np.array([1.0, -2.494956002, 2.017265875, -0.522189400])
    pink = scipy.signal.lfilter(b, a, white)
    peak = np.max(np.abs(pink))
    if peak > 0:
        pink = pink / peak
    return pink


def _generate_typing_buffer(sample_rate: int, duration_sec: int) -> np.ndarray:
    """Pre-generate a looping buffer of keyboard typing sounds.

    Uses bandpass-filtered noise bursts instead of sine waves.
    Real key presses are broadband percussive impacts, not tonal.
    """
    num_samples = sample_rate * duration_sec
    typing = np.zeros(num_samples, dtype=np.float32)

    # Bandpass filter for key click frequency range (1kHz-6kHz)
    nyquist = sample_rate / 2.0
    low = min(1000.0 / nyquist, 0.99)
    high = min(6000.0 / nyquist, 0.99)
    if low < high:
        sos_bp = scipy.signal.butter(2, [low, high], btype="band", output="sos")
    else:
        sos_bp = None

    avg_interval = sample_rate // 4  # ~4 keystrokes/sec
    pos = np.random.randint(0, max(1, avg_interval))

    while pos < num_samples:
        # Each keystroke: short noise burst (4-10ms) — like a mechanical key
        click_dur = int(sample_rate * np.random.uniform(0.004, 0.010))
        end = min(pos + click_dur, num_samples)
        n = end - pos
        t = np.arange(n) / sample_rate

        # White noise burst with sharp percussive envelope
        noise_burst = np.random.randn(n)
        envelope = np.exp(-t * np.random.uniform(300, 600))  # Fast decay
        click = noise_burst * envelope

        # Bandpass filter to remove low rumble and extreme highs
        if sos_bp is not None and n > 12:
            click = scipy.signal.sosfilt(sos_bp, click)

        typing[pos:end] += click.astype(np.float32) * np.random.uniform(0.2, 0.5)

        # Random gap to next keystroke (exponential for natural rhythm)
        pos += int(np.random.exponential(avg_interval))
        # Occasionally add a longer pause (thinking/reading)
        if np.random.random() < 0.10:
            pos += int(sample_rate * np.random.uniform(0.4, 1.0))

    # Normalize
    peak = np.max(np.abs(typing))
    if peak > 0:
        typing = typing / peak
    return typing.astype(np.float32)


def _generate_office_ambience(sample_rate: int) -> np.ndarray:
    """Generate a subtle, low-frequency hum (no wind, no modulation)."""
    num_samples = sample_rate * _BUFFER_DURATION_SEC

    pink = _generate_pink_noise(num_samples)

    # Very low cutoff — just a subtle room tone, no "wind"
    cutoff = 300.0
    nyquist = sample_rate / 2.0
    if cutoff < nyquist:
        sos = scipy.signal.butter(6, cutoff / nyquist, btype="low", output="sos")
        filtered = scipy.signal.sosfilt(sos, pink)
    else:
        filtered = pink

    # No modulation — steady, barely perceptible hum
    peak = np.max(np.abs(filtered))
    if peak > 0:
        filtered = filtered / peak

    return filtered.astype(np.float32)


class OfficeNoiseMixer:
    """
    Provides looping office background noise + keyboard typing sounds
    mixed into PCM audio chunks. Always-on typing creates an immersive
    office atmosphere.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._noise_buffer = _generate_office_ambience(sample_rate)
        self._typing_buffer = _generate_typing_buffer(sample_rate, _BUFFER_DURATION_SEC)
        self._noise_pos = 0
        self._typing_pos = 0
        self._volume = NOISE_VOLUME
        self._typing_volume = 0.04  # Subtle but audible typing
        logger.info(
            f"Office noise mixer initialized: {sample_rate}Hz, "
            f"noise={self._volume:.0%}, typing={self._typing_volume:.0%}"
        )

    def mix_into_pcm(self, pcm_data: bytes) -> bytes:
        """Mix background noise + typing into a PCM Int16 audio chunk."""
        if not pcm_data:
            return pcm_data

        speech = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
        num_samples = len(speech)

        noise = self._get_samples(self._noise_buffer, num_samples, is_typing=False)
        typing = self._get_samples(self._typing_buffer, num_samples, is_typing=True)

        mixed = speech + (noise * 32767.0 * self._volume) + (typing * 32767.0 * self._typing_volume)
        mixed = np.clip(mixed, -32768, 32767).astype(np.int16)
        return mixed.tobytes()

    def get_ambient_chunk(self, duration_ms: int = 100) -> bytes:
        """Generate ambient noise + typing chunk (no speech).

        Used to fill silence between speech chunks.
        """
        num_samples = int(self.sample_rate * duration_ms / 1000)

        noise = self._get_samples(self._noise_buffer, num_samples, is_typing=False)
        typing = self._get_samples(self._typing_buffer, num_samples, is_typing=True)

        combined = (noise * self._volume + typing * self._typing_volume) * 32767.0
        return np.clip(combined, -32768, 32767).astype(np.int16).tobytes()

    def _get_samples(self, buffer: np.ndarray, num_samples: int, is_typing: bool) -> np.ndarray:
        """Get the next num_samples from a looping buffer."""
        buf_len = len(buffer)
        pos = self._typing_pos if is_typing else self._noise_pos
        result = np.empty(num_samples, dtype=np.float32)

        written = 0
        while written < num_samples:
            remaining = num_samples - written
            available = buf_len - pos
            chunk_size = min(remaining, available)
            result[written:written + chunk_size] = buffer[pos:pos + chunk_size]
            pos = (pos + chunk_size) % buf_len
            written += chunk_size

        if is_typing:
            self._typing_pos = pos
        else:
            self._noise_pos = pos
        return result

    def reset(self):
        """Reset positions (for new calls)."""
        self._noise_pos = 0
        self._typing_pos = 0
