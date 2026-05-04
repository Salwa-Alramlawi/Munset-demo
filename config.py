import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PYANNOTE_API_KEY = os.getenv("PYANNOTE_API_KEY", "")

# --- Whisper Settings (Groq API) ---
WHISPER_MODEL = "whisper-large-v3"
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
