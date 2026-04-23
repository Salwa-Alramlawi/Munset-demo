"""Audio utility functions for preprocessing."""

import os
import tempfile
from pydub import AudioSegment


def convert_audio(file_path: str) -> str:
    """Convert any audio format to WAV 16kHz mono (required by Whisper)."""
    audio = AudioSegment.from_file(file_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    wav_path = os.path.join(
        tempfile.gettempdir(),
        os.path.splitext(os.path.basename(file_path))[0] + ".wav",
    )
    audio.export(wav_path, format="wav")
    return wav_path


def get_audio_duration(file_path: str) -> float:
    """Return audio duration in seconds."""
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0
