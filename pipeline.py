"""Munset Pipeline — orchestrates all agents via A2A protocol."""

from __future__ import annotations
import time
from a2a.protocol import A2AProtocol
from a2a.message import A2AMessage
from agents.transcription_agent import TranscriptionAgent
from agents.legal_analysis_agent import LegalAnalysisAgent
from agents.summary_agent import SummaryAgent
from agents.qa_agent import QAAgent
from agents.chatbot_agent import ChatbotAgent


class MunsetPipeline:
    """
    Full pipeline:
    Audio → Transcription Agent → Legal Analysis Agent → Summary Agent → QA Agent
    Then Chatbot Agent is loaded with all context for interactive Q&A.
    Supports demo mode with pre-built data for reliable presentations.
    """

    def __init__(self):
        self.protocol = A2AProtocol()
        self.transcription = TranscriptionAgent(self.protocol)
        self.legal_analysis = LegalAnalysisAgent(self.protocol)
        self.summary = SummaryAgent(self.protocol)
        self.qa = QAAgent(self.protocol)
        self.chatbot = ChatbotAgent(self.protocol)

    def run(self, audio_path: str, speaker_map: dict | None = None, on_step=None):
        """
        Run the full pipeline. Returns dict with all results.
        on_step: optional callback(step_name, step_number, total_steps) for progress.
        """
        results = {}
        total = 5

        # --- Step 1: Transcription ---
        if on_step:
            on_step("التفريغ الصوتي وتحديد المتحدثين", 1, total)

        msg1 = A2AMessage(
            sender="pipeline",
            receiver="transcription_agent",
            payload={"audio_path": audio_path, "speaker_map": speaker_map},
        )
        resp1 = self.protocol.send(msg1)
        transcript_data = resp1.payload
        results["transcription"] = transcript_data

        full_transcript = transcript_data["full_transcript"]

        # --- Step 2: Legal Analysis ---
        if on_step:
            on_step("التحليل القانوني", 2, total)

        msg2 = A2AMessage(
            sender="pipeline",
            receiver="legal_analysis_agent",
            payload={"full_transcript": full_transcript},
        )
        resp2 = self.protocol.send(msg2)
        legal_analysis = resp2.payload["legal_analysis"]
        results["legal_analysis"] = legal_analysis

        # --- Step 3: Summary ---
        if on_step:
            on_step("إنشاء محضر الجلسة", 3, total)

        msg3 = A2AMessage(
            sender="pipeline",
            receiver="summary_agent",
            payload={
                "full_transcript": full_transcript,
                "legal_analysis": legal_analysis,
            },
        )
        resp3 = self.protocol.send(msg3)
        summary = resp3.payload["summary"]
        results["summary"] = summary

        # --- Step 4: QA Review ---
        if on_step:
            on_step("مراجعة الجودة", 4, total)

        msg4 = A2AMessage(
            sender="pipeline",
            receiver="qa_agent",
            payload={
                "full_transcript": full_transcript,
                "summary": summary,
                "legal_analysis": legal_analysis,
            },
        )
        resp4 = self.protocol.send(msg4)
        results["qa_review"] = resp4.payload["qa_review"]

        # --- Step 5: Load Chatbot ---
        if on_step:
            on_step("تجهيز المساعد التفاعلي", 5, total)

        msg5 = A2AMessage(
            sender="pipeline",
            receiver="chatbot_agent",
            payload={
                "type": "load_session",
                "full_transcript": full_transcript,
                "legal_analysis": legal_analysis,
                "summary": summary,
            },
        )
        self.protocol.send(msg5)
        results["chatbot_ready"] = True

        # --- A2A Communication Log & Stats ---
        results["a2a_log"] = self.protocol.get_log()
        results["a2a_stats"] = self.protocol.get_stats()

        return results

    def run_demo(self, on_step=None):
        """
        Run the pipeline with pre-built demo data — no GPU, no API keys needed.
        Simulates realistic A2A communication between agents.
        """
        from demo_data import (
            DEMO_TRANSCRIPT_SEGMENTS, DEMO_FULL_TRANSCRIPT,
            DEMO_LEGAL_ANALYSIS, DEMO_SUMMARY, DEMO_QA_REVIEW,
        )

        results = {}
        total = 6  # 5 agents + 1 feedback round

        # --- Step 1: Transcription (simulated) ---
        if on_step:
            on_step("التفريغ الصوتي وتحديد المتحدثين", 1, total)
        time.sleep(1.5)

        transcript_data = {
            "segments": DEMO_TRANSCRIPT_SEGMENTS,
            "full_transcript": DEMO_FULL_TRANSCRIPT,
            "raw_text": " ".join(s["text"] for s in DEMO_TRANSCRIPT_SEGMENTS),
        }
        # Log A2A message for transcription
        msg1 = A2AMessage(sender="pipeline", receiver="transcription_agent",
                          payload={"audio_path": "demo_audio.wav", "speaker_map": None})
        self.protocol._log.append(msg1.to_dict())
        resp1 = msg1.reply(payload=transcript_data, sender="transcription_agent")
        self.protocol._log.append(resp1.to_dict())

        results["transcription"] = transcript_data
        full_transcript = DEMO_FULL_TRANSCRIPT

        # --- Step 2: Legal Analysis (simulated) ---
        if on_step:
            on_step("التحليل القانوني", 2, total)
        time.sleep(2)

        msg2 = A2AMessage(sender="transcription_agent", receiver="legal_analysis_agent",
                          payload={"full_transcript": full_transcript})
        self.protocol._log.append(msg2.to_dict())
        resp2 = msg2.reply(payload={"legal_analysis": DEMO_LEGAL_ANALYSIS}, sender="legal_analysis_agent")
        self.protocol._log.append(resp2.to_dict())

        results["legal_analysis"] = DEMO_LEGAL_ANALYSIS

        # --- Step 3: Summary (simulated) ---
        if on_step:
            on_step("إنشاء محضر الجلسة", 3, total)
        time.sleep(2)

        msg3 = A2AMessage(sender="legal_analysis_agent", receiver="summary_agent",
                          payload={"full_transcript": full_transcript, "legal_analysis": DEMO_LEGAL_ANALYSIS})
        self.protocol._log.append(msg3.to_dict())
        resp3 = msg3.reply(payload={"summary": DEMO_SUMMARY}, sender="summary_agent")
        self.protocol._log.append(resp3.to_dict())

        results["summary"] = DEMO_SUMMARY

        # --- Step 4: QA Review (simulated) ---
        if on_step:
            on_step("مراجعة الجودة", 4, total)
        time.sleep(1.5)

        msg4 = A2AMessage(sender="summary_agent", receiver="qa_agent",
                          payload={"full_transcript": full_transcript, "summary": DEMO_SUMMARY, "legal_analysis": DEMO_LEGAL_ANALYSIS})
        self.protocol._log.append(msg4.to_dict())
        resp4 = msg4.reply(payload={"qa_review": DEMO_QA_REVIEW}, sender="qa_agent")
        self.protocol._log.append(resp4.to_dict())

        results["qa_review"] = DEMO_QA_REVIEW

        # --- Step 5: QA sends feedback to upstream agents (bidirectional A2A!) ---
        if on_step:
            on_step("🔄 إرسال ملاحظات الجودة للوكلاء السابقين", 5, total)
        time.sleep(1)

        # QA → Summary Agent feedback
        feedback_msg1 = A2AMessage(
            sender="qa_agent", receiver="summary_agent",
            payload={"feedback": "لم يُذكر اسم المكتب الهندسي الذي أعد تقرير المدعي", "severity": "medium"},
            msg_type="feedback", priority="high",
        )
        self.protocol._log.append(feedback_msg1.to_dict())
        feedback_resp1 = feedback_msg1.reply(
            payload={"status": "feedback_received", "action": "سيتم إضافة اسم المكتب في التلخيص المحدّث"},
            sender="summary_agent",
        )
        self.protocol._log.append(feedback_resp1.to_dict())

        # QA → Legal Analysis Agent clarification request
        clarification_msg = A2AMessage(
            sender="qa_agent", receiver="legal_analysis_agent",
            payload={"clarification_question": "هل المادة 79 من نظام المعاملات المدنية تنطبق فعلاً على عقود المقاولات الخاصة؟", "context_msg_id": msg2.msg_id},
            msg_type="clarification_request", priority="high",
        )
        self.protocol._log.append(clarification_msg.to_dict())
        clarification_resp = clarification_msg.reply(
            payload={"clarification_answer": "نعم، المادة 79 تنطبق على العقود الخاصة. القوة القاهرة مبدأ عام في نظام المعاملات المدنية ولا يقتصر على العقود الحكومية."},
            sender="legal_analysis_agent",
        )
        self.protocol._log.append(clarification_resp.to_dict())

        # --- Step 6: Load Chatbot ---
        if on_step:
            on_step("تجهيز المساعد التفاعلي", 6, total)
        time.sleep(0.5)

        self.chatbot.set_session_data(full_transcript, DEMO_LEGAL_ANALYSIS, DEMO_SUMMARY)

        msg5 = A2AMessage(sender="pipeline", receiver="chatbot_agent",
                          payload={"type": "load_session"})
        self.protocol._log.append(msg5.to_dict())
        resp5 = msg5.reply(payload={"status": "session_loaded"}, sender="chatbot_agent")
        self.protocol._log.append(resp5.to_dict())

        results["chatbot_ready"] = True
        results["a2a_log"] = self.protocol.get_log()
        results["a2a_stats"] = self.protocol.get_stats()
        results["demo_mode"] = True

        return results

    def ask_chatbot(self, question: str) -> str:
        """Send a question to the chatbot agent via A2A."""
        msg = A2AMessage(
            sender="user",
            receiver="chatbot_agent",
            payload={"type": "ask", "question": question},
        )
        resp = self.protocol.send(msg)
        return resp.payload["answer"]
