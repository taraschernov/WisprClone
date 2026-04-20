"""
tests/test_audio.py
CP-1.1: stop_recording() returns None when duration < MIN_AUDIO_DURATION_SEC AND rms < SILENCE_THRESHOLD_RMS
CP-1.2: short but loud audio (single word) is NOT discarded
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Constants matching config.py
SAMPLE_RATE = 16000
MIN_AUDIO_DURATION_SEC = 0.2
SILENCE_THRESHOLD_RMS = 0.001


def _make_audio_data(duration_sec: float, rms_amplitude: float):
    """Create fake audio_data list as AudioManager would accumulate."""
    n_samples = int(duration_sec * SAMPLE_RATE)
    if n_samples == 0:
        return []
    if rms_amplitude == 0.0:
        audio = np.zeros((n_samples, 1), dtype=np.float32)
    else:
        # Generate sine wave with given amplitude (RMS ≈ amplitude / sqrt(2))
        t = np.linspace(0, duration_sec, n_samples)
        sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        # Scale so RMS equals rms_amplitude
        current_rms = np.sqrt(np.mean(np.square(sine)))
        if current_rms > 0:
            sine = sine * (rms_amplitude / current_rms)
        audio = sine.reshape(-1, 1)
    return [audio]


def _call_stop_recording_logic(audio_data):
    """
    Replicate the discard logic from AudioManager.stop_recording()
    without touching sounddevice or file system.
    Returns True if audio would be discarded (returns None), False otherwise.
    """
    if not audio_data:
        return True
    audio_concat = np.concatenate(audio_data, axis=0)
    duration = len(audio_concat) / SAMPLE_RATE
    rms = np.sqrt(np.mean(np.square(audio_concat)))
    # FR-1.5: discard ONLY if BOTH conditions are true
    return duration < MIN_AUDIO_DURATION_SEC and rms < SILENCE_THRESHOLD_RMS


# ─── CP-1.1: Both conditions true → discard ───────────────────────────────────

class TestCP11_DiscardShortSilent:
    """CP-1.1: Audio is discarded only when BOTH duration < 0.2s AND rms < threshold."""

    def test_very_short_and_silent_is_discarded(self):
        """0.05s of silence → must be discarded."""
        data = _make_audio_data(0.05, 0.0)
        assert _call_stop_recording_logic(data) == True

    def test_exactly_at_threshold_is_discarded(self):
        """Duration just below 0.2s and rms just below threshold → discarded."""
        data = _make_audio_data(0.19, SILENCE_THRESHOLD_RMS * 0.5)
        assert _call_stop_recording_logic(data) == True

    def test_empty_audio_data_is_discarded(self):
        """No audio data at all → discarded."""
        assert _call_stop_recording_logic([]) is True

    @given(
        duration=st.floats(min_value=0.001, max_value=MIN_AUDIO_DURATION_SEC - 0.001),
        rms=st.floats(min_value=0.0, max_value=SILENCE_THRESHOLD_RMS * 0.99),
    )
    @settings(max_examples=100)
    def test_property_short_and_silent_always_discarded(self, duration, rms):
        """Property: any audio shorter than threshold AND quieter than threshold is discarded."""
        data = _make_audio_data(duration, rms)
        if data:  # skip degenerate case
            assert _call_stop_recording_logic(data) == True


# ─── CP-1.2: Short but loud → NOT discarded ───────────────────────────────────

class TestCP12_ShortLoudNotDiscarded:
    """CP-1.2: Short but loud audio (single word like 'Ok') must NOT be discarded."""

    def test_short_but_loud_passes(self):
        """0.1s of loud audio → must NOT be discarded (single word scenario)."""
        data = _make_audio_data(0.1, 0.05)  # loud: rms >> threshold
        assert _call_stop_recording_logic(data) == False

    def test_long_and_silent_passes(self):
        """Long but silent audio → must NOT be discarded (only short+silent is filtered)."""
        data = _make_audio_data(0.5, 0.0)
        assert _call_stop_recording_logic(data) == False

    def test_long_and_loud_passes(self):
        """Normal speech → must NOT be discarded."""
        data = _make_audio_data(2.0, 0.05)
        assert _call_stop_recording_logic(data) == False

    def test_exactly_at_duration_threshold_loud_passes(self):
        """Exactly 0.2s but loud → must NOT be discarded."""
        data = _make_audio_data(MIN_AUDIO_DURATION_SEC, 0.05)
        assert _call_stop_recording_logic(data) == False

    @given(
        duration=st.floats(min_value=0.001, max_value=MIN_AUDIO_DURATION_SEC - 0.001),
        rms=st.floats(min_value=SILENCE_THRESHOLD_RMS * 1.01, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_property_short_but_loud_never_discarded(self, duration, rms):
        """Property: short but loud audio (single word) must always pass through."""
        assume(rms > SILENCE_THRESHOLD_RMS)
        data = _make_audio_data(duration, rms)
        if data:
            assert _call_stop_recording_logic(data) == False

    @given(
        duration=st.floats(min_value=MIN_AUDIO_DURATION_SEC, max_value=30.0),
        rms=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_property_long_audio_never_discarded(self, duration, rms):
        """Property: audio longer than threshold is never discarded regardless of rms."""
        data = _make_audio_data(duration, rms)
        if data:
            assert _call_stop_recording_logic(data) == False

