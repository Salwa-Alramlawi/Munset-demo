import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")  # Hugging Face token for pyannote

# --- Whisper Settings ---
WHISPER_MODEL = "large-v3"
WHISPER_LANGUAGE = "ar"

# --- Claude Settings ---
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# --- Speaker Labels ---
DEFAULT_SPEAKERS = {
    "SPEAKER_00": "القاضي",
    "SPEAKER_01": "المدعي",
    "SPEAKER_02": "المدعى عليه",
    "SPEAKER_03": "محامي المدعي",
    "SPEAKER_04": "محامي المدعى عليه",
}
