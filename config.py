import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Read from environment first, then Streamlit secrets (for cloud deployment)."""
    val = os.getenv(key, "")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


# --- API Keys ---
ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
GROQ_API_KEY = _get_secret("GROQ_API_KEY")
PYANNOTE_API_KEY = _get_secret("PYANNOTE_API_KEY")

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
