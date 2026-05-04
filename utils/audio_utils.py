"""Audio utility functions for preprocessing."""

import os
import tempfile


def get_audio_duration(file_path: str) -> float:
    """Return audio duration in seconds using pydub."""
    from pydub import AudioSegment
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0
