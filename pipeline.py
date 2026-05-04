"""Munset Pipeline — orchestrates all agents via A2A protocol with quality loop."""

from __future__ import annotations
import json
import time
from a2a.protocol import A2AProtocol
from a2a.message import A2AMessage
from agents.transcription_agent import TranscriptionAgent
from agents.legal_analysis_agent import LegalAnalysisAgent
from agents.summary_agent import SummaryAgent
from agents.qa_agent import QAAgent
from agents.chatbot_agent import ChatbotAgent

MAX_QA_ROUNDS = 2


class MunsetPipeline:
    """
    Full pipeline with quality improvement loop:
    Audio → Transcription → Legal Analysis → Summary → QA Review
      ↓ (if QA rejects)
    QA sends feedback → Legal Analysis re-analyzes → Summary re-generates → QA re-reviews
      ↓ (if QA accepts)
    Chatbot loaded with all context
    """

    def __init__(self):
        self.protocol = A2AProtocol()
        self.transcription = TranscriptionAgent(self.protocol)
        self.legal_analysis = LegalAnalysisAgent(self.protocol)
        self.summary = SummaryAgent(self.protocol)
        self.qa = QAAgent(self.protocol)
        self.chatbot = ChatbotAgent(self.protocol)

    def run(self, audio_path: str, speaker_map: dict | None = None, on_step=None):
        results = {}
        total = 7

        # --- Step 1: Transcription ---
        if on_step:
            on_step("التفريغ الصوتي وتحديد المتحدثين", 1, total)

        msg1 = A2AMessage(
            sender="pipeline", receiver="transcription_agent",
            payload={"audio_path": audio_path, "speaker_map": speaker_map},
        )
        resp1 = self.protocol.send(msg1)
        transcript_data = resp1.payload
        results["transcription"] = transcript_data
        full_transcript = transcript_data["full_transcript"]

        # --- Step 2: Legal Analysis (Round 1) ---
        if on_step:
            on_step("التحليل القانوني", 2, total)

        msg2 = A2AMessage(
            sender="pipeline", receiver="legal_analysis_agent",
            payload={"full_transcript": full_transcript},
        )
        resp2 = self.protocol.send(msg2)
        legal_analysis = resp2.payload["legal_analysis"]

        # --- Step 3: Summary (Round 1) ---
        if on_step:
            on_step("إنشاء محضر الجلسة", 3, total)

        msg3 = A2AMessage(
            sender="pipeline", receiver="summary_agent",
            payload={"full_transcript": full_transcript, "legal_analysis": legal_analysis},
        )
        resp3 = self.protocol.send(msg3)
        summary = resp3.payload["summary"]

        # --- Step 4: QA Review (Round 1) ---
        if on_step:
            on_step("مراجعة الجودة — الجولة الأولى", 4, total)

        msg4 = A2AMessage(
            sender="pipeline", receiver="qa_agent",
            payload={"full_transcript": full_transcript, "summary": summary, "legal_analysis": legal_analysis},
        )
        resp4 = self.protocol.send(msg4)
        qa_review = resp4.payload["qa_review"]

        results["qa_round_1"] = qa_review
        results["qa_rounds"] = 1

        # --- Quality Loop: if QA rejects, re-generate ---
        if qa_review.get("decision") == "reject" and MAX_QA_ROUNDS > 1:
            issues_text = json.dumps(qa_review.get("issues", []), ensure_ascii=False, indent=2)

            # --- Step 5: Re-analyze with feedback ---
            if on_step:
                on_step("🔄 إعادة التحليل القانوني بعد ملاحظات المراجعة", 5, total)

            msg5 = A2AMessage(
                sender="pipeline", receiver="legal_analysis_agent",
                payload={"full_transcript": full_transcript, "qa_feedback": issues_text},
            )
            resp5 = self.protocol.send(msg5)
            legal_analysis = resp5.payload["legal_analysis"]

            # --- Step 6: Re-generate summary with feedback ---
            if on_step:
                on_step("🔄 إعادة إنتاج المحضر بعد ملاحظات المراجعة", 6, total)

            msg6 = A2AMessage(
                sender="pipeline", receiver="summary_agent",
                payload={"full_transcript": full_transcript, "legal_analysis": legal_analysis, "qa_feedback": issues_text},
            )
            resp6 = self.protocol.send(msg6)
            summary = resp6.payload["summary"]

            # --- Step 7: QA Review (Round 2) ---
            if on_step:
                on_step("مراجعة الجودة — الجولة الثانية", 7, total)

            msg7 = A2AMessage(
                sender="pipeline", receiver="qa_agent",
                payload={
                    "full_transcript": full_transcript,
                    "summary": summary,
                    "legal_analysis": legal_analysis,
                    "previous_issues": issues_text,
                },
            )
            resp7 = self.protocol.send(msg7)
            qa_review = resp7.payload["qa_review"]
            results["qa_round_2"] = qa_review
            results["qa_rounds"] = 2

        results["legal_analysis"] = legal_analysis
        results["summary"] = summary
        results["qa_review"] = qa_review

        # --- Load Chatbot ---
        if on_step:
            on_step("تجهيز المساعد التفاعلي", total, total)

        msg_chat = A2AMessage(
            sender="pipeline", receiver="chatbot_agent",
            payload={
                "type": "load_session",
                "full_transcript": full_transcript,
                "legal_analysis": legal_analysis,
                "summary": summary,
            },
        )
        self.protocol.send(msg_chat)
        results["chatbot_ready"] = True
        results["a2a_log"] = self.protocol.get_log()
        results["a2a_stats"] = self.protocol.get_stats()

        return results

    def run_demo(self, on_step=None):
        """Demo mode with simulated quality improvement loop."""
        from demo_data import (
            DEMO_TRANSCRIPT_SEGMENTS, DEMO_FULL_TRANSCRIPT,
            DEMO_LEGAL_ANALYSIS, DEMO_SUMMARY, DEMO_QA_REVIEW_ROUND1,
            DEMO_LEGAL_ANALYSIS_V2, DEMO_SUMMARY_V2, DEMO_QA_REVIEW_ROUND2,
        )

        results = {}
        total = 9

        # --- Step 1: Transcription ---
        if on_step:
            on_step("التفريغ الصوتي وتحديد المتحدثين", 1, total)
        time.sleep(1.5)

        transcript_data = {
            "segments": DEMO_TRANSCRIPT_SEGMENTS,
            "full_transcript": DEMO_FULL_TRANSCRIPT,
            "raw_text": " ".join(s["text"] for s in DEMO_TRANSCRIPT_SEGMENTS),
        }
        msg1 = A2AMessage(sender="pipeline", receiver="transcription_agent",
                          payload={"audio_path": "demo_audio.wav", "speaker_map": None})
        self.protocol._log.append(msg1.to_dict())
        resp1 = msg1.reply(payload=transcript_data, sender="transcription_agent")
        self.protocol._log.append(resp1.to_dict())
        results["transcription"] = transcript_data
        full_transcript = DEMO_FULL_TRANSCRIPT

        # --- Step 2: Legal Analysis (Round 1) ---
        if on_step:
            on_step("التحليل القانوني — الجولة الأولى", 2, total)
        time.sleep(1.5)

        msg2 = A2AMessage(sender="transcription_agent", receiver="legal_analysis_agent",
                          payload={"full_transcript": full_transcript})
        self.protocol._log.append(msg2.to_dict())
        resp2 = msg2.reply(payload={"legal_analysis": DEMO_LEGAL_ANALYSIS}, sender="legal_analysis_agent")
        self.protocol._log.append(resp2.to_dict())

        # --- Step 3: Summary (Round 1) ---
        if on_step:
            on_step("إنشاء محضر الجلسة — الجولة الأولى", 3, total)
        time.sleep(1.5)

        msg3 = A2AMessage(sender="legal_analysis_agent", receiver="summary_agent",
                          payload={"full_transcript": full_transcript, "legal_analysis": DEMO_LEGAL_ANALYSIS})
        self.protocol._log.append(msg3.to_dict())
        resp3 = msg3.reply(payload={"summary": DEMO_SUMMARY}, sender="summary_agent")
        self.protocol._log.append(resp3.to_dict())

        # --- Step 4: QA Review (Round 1) — REJECTS! ---
        if on_step:
            on_step("مراجعة الجودة — الجولة الأولى", 4, total)
        time.sleep(1.5)

        msg4 = A2AMessage(sender="summary_agent", receiver="qa_agent",
                          payload={"full_transcript": full_transcript, "summary": DEMO_SUMMARY, "legal_analysis": DEMO_LEGAL_ANALYSIS})
        self.protocol._log.append(msg4.to_dict())
        resp4 = msg4.reply(payload={"qa_review": DEMO_QA_REVIEW_ROUND1}, sender="qa_agent")
        self.protocol._log.append(resp4.to_dict())

        results["qa_round_1"] = DEMO_QA_REVIEW_ROUND1

        # --- Step 5: QA sends feedback to upstream agents ---
        if on_step:
            on_step("❌ وكيل المراجعة رفض المحضر — إرسال الملاحظات", 5, total)
        time.sleep(1)

        # QA → Summary Agent
        fb1 = A2AMessage(
            sender="qa_agent", receiver="summary_agent",
            payload={"feedback": "- [missing_info][medium] لم يُذكر اسم المكتب الهندسي الذي أعد تقرير المدعي\n- [missing_info][high] لم تُذكر قيمة العقد الإجمالية رغم وجودها ضمنياً في النص"},
            msg_type="feedback", priority="high",
        )
        self.protocol._log.append(fb1.to_dict())
        fb1_resp = fb1.reply(payload={"status": "feedback_received", "action": "سيتم إعادة إنتاج المحضر"}, sender="summary_agent")
        self.protocol._log.append(fb1_resp.to_dict())

        # QA → Legal Analysis Agent
        fb2 = A2AMessage(
            sender="qa_agent", receiver="legal_analysis_agent",
            payload={"feedback": "- [contradiction][high] التناقض في نسبة الإنجاز يحتاج توضيح أكثر: هل يوجد ما يرجّح أحد التقريرين؟\n- [inaccuracy][medium] المادة 78 من نظام المنافسات تنطبق على العقود الحكومية — هل تنطبق على عقد خاص؟"},
            msg_type="feedback", priority="high",
        )
        self.protocol._log.append(fb2.to_dict())
        fb2_resp = fb2.reply(payload={"status": "feedback_received", "action": "سيتم إعادة التحليل مع التوضيحات"}, sender="legal_analysis_agent")
        self.protocol._log.append(fb2_resp.to_dict())

        # --- Step 6: Re-analysis (Round 2) ---
        if on_step:
            on_step("🔄 إعادة التحليل القانوني بعد الملاحظات", 6, total)
        time.sleep(1.5)

        msg5 = A2AMessage(sender="qa_agent", receiver="legal_analysis_agent",
                          payload={"full_transcript": full_transcript, "qa_feedback": "ملاحظات المراجعة"})
        self.protocol._log.append(msg5.to_dict())
        resp5 = msg5.reply(payload={"legal_analysis": DEMO_LEGAL_ANALYSIS_V2}, sender="legal_analysis_agent")
        self.protocol._log.append(resp5.to_dict())

        # --- Step 7: Re-generate summary (Round 2) ---
        if on_step:
            on_step("🔄 إعادة إنتاج المحضر المُحسَّن", 7, total)
        time.sleep(1.5)

        msg6 = A2AMessage(sender="qa_agent", receiver="summary_agent",
                          payload={"full_transcript": full_transcript, "legal_analysis": DEMO_LEGAL_ANALYSIS_V2, "qa_feedback": "ملاحظات المراجعة"})
        self.protocol._log.append(msg6.to_dict())
        resp6 = msg6.reply(payload={"summary": DEMO_SUMMARY_V2}, sender="summary_agent")
        self.protocol._log.append(resp6.to_dict())

        # --- Step 8: QA Review (Round 2) — ACCEPTS! ---
        if on_step:
            on_step("✅ مراجعة الجودة — الجولة الثانية", 8, total)
        time.sleep(1)

        msg7 = A2AMessage(sender="summary_agent", receiver="qa_agent",
                          payload={"full_transcript": full_transcript, "summary": DEMO_SUMMARY_V2, "legal_analysis": DEMO_LEGAL_ANALYSIS_V2})
        self.protocol._log.append(msg7.to_dict())
        resp7 = msg7.reply(payload={"qa_review": DEMO_QA_REVIEW_ROUND2}, sender="qa_agent")
        self.protocol._log.append(resp7.to_dict())

        results["qa_round_2"] = DEMO_QA_REVIEW_ROUND2

        # --- Step 9: Load Chatbot ---
        if on_step:
            on_step("تجهيز المساعد التفاعلي", 9, total)
        time.sleep(0.5)

        self.chatbot.set_session_data(full_transcript, DEMO_LEGAL_ANALYSIS_V2, DEMO_SUMMARY_V2)

        msg8 = A2AMessage(sender="pipeline", receiver="chatbot_agent", payload={"type": "load_session"})
        self.protocol._log.append(msg8.to_dict())
        resp8 = msg8.reply(payload={"status": "session_loaded"}, sender="chatbot_agent")
        self.protocol._log.append(resp8.to_dict())

        results["legal_analysis"] = DEMO_LEGAL_ANALYSIS_V2
        results["summary"] = DEMO_SUMMARY_V2
        results["qa_review"] = DEMO_QA_REVIEW_ROUND2
        results["qa_rounds"] = 2
        results["chatbot_ready"] = True
        results["a2a_log"] = self.protocol.get_log()
        results["a2a_stats"] = self.protocol.get_stats()
        results["demo_mode"] = True

        return results

    def ask_chatbot(self, question: str) -> str:
        msg = A2AMessage(
            sender="user", receiver="chatbot_agent",
            payload={"type": "ask", "question": question},
        )
        resp = self.protocol.send(msg)
        return resp.payload["answer"]
