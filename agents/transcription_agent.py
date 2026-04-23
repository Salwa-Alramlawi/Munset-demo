"""Agent 1 — Transcription Agent: Speech-to-Text + Speaker Diarization."""

from __future__ import annotations
import whisper
import torch
from pyannote.audio import Pipeline as DiarizationPipeline

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
from utils.audio_utils import convert_audio
import config


class TranscriptionAgent(BaseAgent):
    """Converts audio to text and identifies speakers."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("transcription_agent", protocol)
        self._whisper_model = None
        self._diarization_pipeline = None

    # -- lazy loading (heavy models) --
    def _load_whisper(self):
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model(config.WHISPER_MODEL)
        return self._whisper_model

    def _load_diarization(self):
        if self._diarization_pipeline is None:
            self._diarization_pipeline = DiarizationPipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=config.HF_TOKEN,
            )
            if torch.cuda.is_available():
                self._diarization_pipeline.to(torch.device("cuda"))
        return self._diarization_pipeline

    # -- core logic --
    def transcribe(self, audio_path: str, speaker_map: dict[str, str] | None = None) -> dict:
        """Full pipeline: transcribe + diarize + merge."""
        wav_path = convert_audio(audio_path)

        # Step 1: Whisper transcription with timestamps
        model = self._load_whisper()
        result = model.transcribe(
            wav_path,
            language=config.WHISPER_LANGUAGE,
            task="transcribe",
            verbose=False,
        )

        # Step 2: Speaker diarization
        pipeline = self._load_diarization()
        diarization = pipeline(wav_path)

        # Step 3: Merge transcription with speakers
        speaker_map = speaker_map or config.DEFAULT_SPEAKERS
        transcript = self._merge(result["segments"], diarization, speaker_map)

        return {
            "raw_text": result["text"],
            "segments": transcript,
            "full_transcript": self._format_transcript(transcript),
        }

    def _merge(self, segments: list[dict], diarization, speaker_map: dict) -> list[dict]:
        """Assign a speaker label to each Whisper segment."""
        merged = []
        for seg in segments:
            mid_time = (seg["start"] + seg["end"]) / 2
            speaker_id = "UNKNOWN"
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if turn.start <= mid_time <= turn.end:
                    speaker_id = speaker
                    break

            label = speaker_map.get(speaker_id, speaker_id)
            merged.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "speaker_id": speaker_id,
                "speaker": label,
                "text": seg["text"].strip(),
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

    # -- A2A handler --
    def handle_message(self, message: A2AMessage):
        """Handle incoming A2A requests."""
        audio_path = message.payload.get("audio_path")
        speaker_map = message.payload.get("speaker_map")
        result = self.transcribe(audio_path, speaker_map)
        return message.reply(payload=result, sender=self.name)
