"""Agent 1 — Transcription Agent: Speech-to-Text (Groq Whisper API) + Speaker Diarization (pyannote.ai API)."""

from __future__ import annotations
import os
import time
import requests
from groq import Groq

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config


class TranscriptionAgent(BaseAgent):
    """Converts audio to text (Groq Whisper) and identifies speakers (pyannote.ai) — fully cloud-based."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("transcription_agent", protocol)
        self.groq_client = Groq(api_key=config.GROQ_API_KEY)

    def transcribe(self, audio_path: str, speaker_map: dict[str, str] | None = None) -> dict:
        """Full pipeline: Groq Whisper API + pyannote.ai API + merge."""
        whisper_segments = self._transcribe_groq(audio_path)
        diarization = self._diarize_pyannote(audio_path)

        speaker_map = speaker_map or config.DEFAULT_SPEAKERS
        merged = self._merge(whisper_segments, diarization, speaker_map)

        return {
            "raw_text": " ".join(s["text"] for s in merged),
            "segments": merged,
            "full_transcript": self._format_transcript(merged),
        }

    def _transcribe_groq(self, audio_path: str) -> list[dict]:
        """Transcribe audio via Groq Whisper API (fast + cheap)."""
        with open(audio_path, "rb") as f:
            response = self.groq_client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), f.read()),
                model=config.WHISPER_MODEL,
                language=config.WHISPER_LANGUAGE,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        segments = []
        if hasattr(response, "segments") and response.segments:
            for seg in response.segments:
                start = seg["start"] if isinstance(seg, dict) else seg.start
                end = seg["end"] if isinstance(seg, dict) else seg.end
                text = seg["text"] if isinstance(seg, dict) else seg.text
                segments.append({"start": start, "end": end, "text": text.strip()})
        else:
            segments.append({"start": 0.0, "end": 0.0, "text": response.text.strip()})
        return segments

    def _diarize_pyannote(self, audio_path: str) -> list[dict]:
        """Speaker diarization via pyannote.ai cloud API."""
        with open(audio_path, "rb") as f:
            resp = requests.post(
                "https://api.pyannote.ai/v1/diarize",
                headers={"Authorization": f"Bearer {config.PYANNOTE_API_KEY}"},
                files={"audio": f},
            )
        resp.raise_for_status()
        job_id = resp.json()["jobId"]

        for _ in range(90):
            time.sleep(2)
            result = requests.get(
                f"https://api.pyannote.ai/v1/diarize/{job_id}",
                headers={"Authorization": f"Bearer {config.PYANNOTE_API_KEY}"},
            )
            result.raise_for_status()
            data = result.json()
            if data["status"] == "succeeded":
                return data["output"]["diarization"]
            elif data["status"] == "failed":
                raise RuntimeError(f"Diarization failed: {data}")

        raise TimeoutError("Diarization timed out after 3 minutes")

    def _merge(self, whisper_segments: list[dict], diarization: list[dict], speaker_map: dict) -> list[dict]:
        """Assign a speaker label to each Whisper segment using diarization results."""
        merged = []
        for seg in whisper_segments:
            mid_time = (seg["start"] + seg["end"]) / 2
            speaker_id = "UNKNOWN"
            for turn in diarization:
                if turn["start"] <= mid_time <= turn["end"]:
                    speaker_id = turn["speaker"]
                    break

            label = speaker_map.get(speaker_id, speaker_id)
            merged.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "speaker_id": speaker_id,
                "speaker": label,
                "text": seg["text"],
            })
        return merged

    @staticmethod
    def _format_transcript(segments: list[dict]) -> str:
        """Readable transcript with speaker labels."""
        lines = []
        for s in segments:
            timestamp = f"[{s['start']:.1f}s - {s['end']:.1f}s]"
            lines.append(f"{timestamp} {s['speaker']}: {s['text']}")
        return "\n".join(lines)

    def handle_message(self, message: A2AMessage):
        audio_path = message.payload.get("audio_path")
        speaker_map = message.payload.get("speaker_map")
        result = self.transcribe(audio_path, speaker_map)
        return message.reply(payload=result, sender=self.name)
