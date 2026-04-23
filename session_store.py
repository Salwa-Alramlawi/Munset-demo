"""Session Store — persists court sessions and enables cross-session contradiction detection."""

from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path


STORE_DIR = Path(__file__).parent / "sessions_db"


class SessionStore:
    """Simple file-based store for court sessions (no external DB needed for demo)."""

    def __init__(self, store_dir: str | Path | None = None):
        self.store_dir = Path(store_dir) if store_dir else STORE_DIR
        self.store_dir.mkdir(exist_ok=True)

    def save_session(self, case_number: str, session_data: dict) -> str:
        """Save a court session. Returns the session ID."""
        session_id = f"{case_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        record = {
            "session_id": session_id,
            "case_number": case_number,
            "timestamp": datetime.now().isoformat(),
            "transcript": session_data.get("full_transcript", ""),
            "legal_analysis": session_data.get("legal_analysis", {}),
            "summary": session_data.get("summary", ""),
            "qa_review": session_data.get("qa_review", {}),
            "speakers_statements": self._extract_statements(session_data),
        }
        filepath = self.store_dir / f"{session_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        return session_id

    def get_sessions_for_case(self, case_number: str) -> list[dict]:
        """Retrieve all sessions for a given case number, sorted by date."""
        sessions = []
        for filepath in self.store_dir.glob(f"{case_number}_*.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                sessions.append(json.load(f))
        return sorted(sessions, key=lambda s: s["timestamp"])

    def get_all_cases(self) -> list[str]:
        """List all unique case numbers in the store."""
        cases = set()
        for filepath in self.store_dir.glob("*.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                cases.add(data["case_number"])
        return sorted(cases)

    def detect_cross_session_contradictions(self, case_number: str) -> list[dict]:
        """Compare statements across sessions for the same case to find contradictions."""
        sessions = self.get_sessions_for_case(case_number)
        if len(sessions) < 2:
            return []

        contradictions = []
        for i in range(len(sessions)):
            for j in range(i + 1, len(sessions)):
                s1 = sessions[i]
                s2 = sessions[j]

                # Compare key facts from legal analysis
                facts_1 = set(s1.get("legal_analysis", {}).get("key_facts", []))
                facts_2 = set(s2.get("legal_analysis", {}).get("key_facts", []))

                # Compare claims
                claims_1 = s1.get("legal_analysis", {}).get("claims", [])
                claims_2 = s2.get("legal_analysis", {}).get("claims", [])

                # Compare defenses
                defenses_1 = s1.get("legal_analysis", {}).get("defenses", [])
                defenses_2 = s2.get("legal_analysis", {}).get("defenses", [])

                # Compare speaker statements
                stmts_1 = s1.get("speakers_statements", {})
                stmts_2 = s2.get("speakers_statements", {})

                for speaker in set(list(stmts_1.keys()) + list(stmts_2.keys())):
                    old_stmts = stmts_1.get(speaker, [])
                    new_stmts = stmts_2.get(speaker, [])
                    if old_stmts and new_stmts:
                        contradictions.append({
                            "type": "cross_session_comparison",
                            "speaker": speaker,
                            "session_1": s1["session_id"],
                            "session_1_date": s1["timestamp"],
                            "session_1_statements": old_stmts[:5],
                            "session_2": s2["session_id"],
                            "session_2_date": s2["timestamp"],
                            "session_2_statements": new_stmts[:5],
                            "note": f"يجب مراجعة أقوال {speaker} في الجلستين للتحقق من وجود تناقضات",
                        })

                # Include within-session contradictions from legal analysis
                for s in [s1, s2]:
                    for c in s.get("legal_analysis", {}).get("contradictions", []):
                        contradictions.append({
                            "type": "within_session",
                            "session_id": s["session_id"],
                            "session_date": s["timestamp"],
                            "description": c,
                        })

        return contradictions

    def _extract_statements(self, session_data: dict) -> dict[str, list[str]]:
        """Extract key statements per speaker from transcript segments."""
        statements: dict[str, list[str]] = {}
        segments = session_data.get("transcription", {}).get("segments", [])
        for seg in segments:
            speaker = seg.get("speaker", "غير معروف")
            text = seg.get("text", "").strip()
            if text and len(text) > 20:  # skip very short utterances
                if speaker not in statements:
                    statements[speaker] = []
                statements[speaker].append(text)
        return statements

    def get_session_count(self) -> int:
        """Return total number of stored sessions."""
        return len(list(self.store_dir.glob("*.json")))
