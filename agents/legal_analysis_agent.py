"""Agent 2 — Legal Analysis Agent: extracts structured legal info from transcript.
Can re-analyze with QA feedback to improve results."""

from __future__ import annotations
import json
import anthropic

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config

SYSTEM_PROMPT = """أنت محلل قانوني متخصص في النظام القضائي السعودي.
مهمتك: تحليل محضر جلسة قضائية واستخراج المعلومات التالية بدقة.

أجب بصيغة JSON فقط بالهيكل التالي:
{
    "case_type": "نوع القضية",
    "claims": ["قائمة الادعاءات"],
    "defenses": ["قائمة الدفوع"],
    "evidence": ["الأدلة المذكورة"],
    "legal_articles": ["المواد النظامية المُشار إليها"],
    "requests": {
        "plaintiff": ["طلبات المدعي"],
        "defendant": ["طلبات المدعى عليه"]
    },
    "key_facts": ["الوقائع الجوهرية"],
    "contradictions": ["أي تناقضات في الأقوال"],
    "timeline": ["تسلسل الأحداث المذكورة"]
}

تعامل مع النص بدقة. إذا لم تجد معلومة معينة اكتب مصفوفة فارغة [].
لا تخترع معلومات غير موجودة في النص."""

REANALYSIS_PROMPT = """أنت محلل قانوني متخصص في النظام القضائي السعودي.

هذه الجولة الثانية من التحليل. وكيل مراجعة الجودة أرسل لك الملاحظات التالية على تحليلك السابق:

{feedback}

أعد التحليل مع مراعاة هذه الملاحظات. تأكد من معالجة كل ملاحظة.

أجب بصيغة JSON فقط بنفس الهيكل:
{{
    "case_type": "...",
    "claims": [...],
    "defenses": [...],
    "evidence": [...],
    "legal_articles": [...],
    "requests": {{"plaintiff": [...], "defendant": [...]}},
    "key_facts": [...],
    "contradictions": [...],
    "timeline": [...]
}}"""


class LegalAnalysisAgent(BaseAgent):
    """Extracts legal structure from a court session transcript.
    Can re-analyze with feedback from QA agent."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("legal_analysis_agent", protocol)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._last_feedback = None

    def analyze(self, transcript: str, feedback: str | None = None) -> dict:
        """Send transcript to Claude and get structured legal analysis."""
        if feedback:
            system = REANALYSIS_PROMPT.format(feedback=feedback)
        else:
            system = SYSTEM_PROMPT

        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4096,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": f"حلل محضر الجلسة القضائية التالي:\n\n{transcript}",
                }
            ],
        )

        raw = response.content[0].text
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            return {"raw_analysis": raw, "parse_error": True}

    def handle_message(self, message: A2AMessage):
        if message.msg_type == "feedback":
            feedback = message.payload.get("feedback", "")
            self._last_feedback = feedback
            return message.reply(
                payload={"status": "feedback_received", "action": "سيتم إعادة التحليل مع مراعاة الملاحظات"},
                sender=self.name,
            )

        if message.msg_type == "clarification_request":
            question = message.payload.get("clarification_question", "")
            return message.reply(
                payload={"clarification_answer": f"وكيل التحليل القانوني: بخصوص '{question}' — تم التوضيح بناءً على السياق."},
                sender=self.name,
            )

        transcript = message.payload.get("full_transcript", "")
        feedback = message.payload.get("qa_feedback")

        if feedback:
            self._last_feedback = feedback

        result = self.analyze(transcript, self._last_feedback)

        if self._last_feedback:
            self._last_feedback = None

        return message.reply(payload={"legal_analysis": result}, sender=self.name)
