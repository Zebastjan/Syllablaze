"""
Liquid AI LFM2.5-Audio Backend

Speech-to-text using Liquid AI's end-to-end audio foundation model.

Installation:
    pip install liquid-audio torchaudio

Optional for better performance:
    pip install flash-attn --no-build-isolation

Usage:
    from blaze.backends.liquid import LiquidBackend
    backend = LiquidBackend()
    backend.load("lfm2.5-audio-1.5b")
    result = backend.transcribe(audio_bytes)
"""

from blaze.backends.liquid.backend import LiquidBackend

__all__ = ["LiquidBackend"]
