"""Agent 2 — Legal Analysis Agent: extracts structured legal info from transcript.
Makes autonomous decisions:
  - Assigns confidence scores to legal articles (applicable / uncertain / not_applicable)
  - Sends clarification requests to transcription agent when text is ambiguous
Can re-analyze with QA feedback to improve results."""

from __future__ import annotations
import json
import anthropic

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config

ARTICLE_CONFIDENCE_THRESHOLD = 0.6

SYSTEM_PROMPT = """أنت محلل قانوني متخصص في النظام القضائي السعودي.
مهمتك: تحليل محضر جلسة قضائية واستخراج المعلومات التالية بدقة.

## قرار مهم — تقييم انطباق المواد النظامية:
لكل مادة نظامية مذكورة في الجلسة، يجب أن تتخذ قراراً مستقلاً:
- هل هذه المادة تنطبق فعلاً على هذه القضية؟
- قيّم ثقتك في الانطباق (0.0 إلى 1.0)
- إذا كانت الثقة أقل من 0.6 ← أشر إلى ذلك بوضوح مع السبب

## قرار ثانٍ — طلب توضيح:
إذا وجدت في النص عبارة غامضة أو متناقضة تحتاج توضيح من السياق،
أضفها في حقل "clarification_needed".

أجب بصيغة JSON فقط بالهيكل التالي:
{
    "case_type": "نوع القضية",
    "claims": ["قائمة الادعاءات"],
    "defenses": ["قائمة الدفوع"],
    "evidence": ["الأدلة المذكورة"],
    "legal_articles": [
        {
            "article": "اسم المادة ورقمها",
            "confidence": 0.0-1.0,
            "applicability": "applicable | uncertain | not_applicable",
            "reasoning": "سبب القرار باختصار"
        }
    ],
    "requests": {
        "plaintiff": ["طلبات المدعي"],
        "defendant": ["طلبات المدعى عليه"]
    },
    "key_facts": ["الوقائع الجوهرية"],
    "contradictions": ["أي تناقضات في الأقوال"],
    "timeline": ["تسلسل الأحداث المذكورة"],
    "clarification_needed": ["أي عبارة غامضة تحتاج توضيح — اتركها فارغة [] إذا كل شيء واضح"],
    "agent_decisions": {
        "articles_flagged": 0,
        "clarifications_requested": 0
    }
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
    Autonomous decisions:
      - Evaluates confidence in legal article applicability
      - Flags uncertain articles (confidence < 0.6)
      - Requests clarification from transcription agent for ambiguous text
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
            result = json.loads(raw.strip())
        except json.JSONDecodeError:
            return {"raw_analysis": raw, "parse_error": True}

        result["agent_decisions"] = self._make_decisions(result)
        return result

    def _make_decisions(self, analysis: dict) -> dict:
        """Autonomous decision-making on the analysis results."""
        articles = analysis.get("legal_articles", [])
        flagged = 0
        for art in articles:
            if isinstance(art, dict):
                conf = art.get("confidence", 1.0)
                if conf < ARTICLE_CONFIDENCE_THRESHOLD:
                    art["applicability"] = "not_applicable"
                    flagged += 1
                elif conf < 0.8:
                    art["applicability"] = "uncertain"
                    flagged += 1

        clarifications = analysis.get("clarification_needed", [])
        return {
            "articles_flagged": flagged,
            "clarifications_requested": len(clarifications),
            "decision_summary": self._build_decision_summary(flagged, len(clarifications)),
        }

    def _build_decision_summary(self, flagged: int, clarifications: int) -> str:
        parts = []
        if flagged > 0:
            parts.append(f"تم تعليم {flagged} مادة نظامية بثقة منخفضة في الانطباق")
        if clarifications > 0:
            parts.append(f"تم طلب توضيح لـ {clarifications} عبارة غامضة")
        if not parts:
            parts.append("جميع المواد النظامية تنطبق بثقة عالية — لا توضيحات مطلوبة")
        return " | ".join(parts)

    def _send_clarification_requests(self, clarifications: list[str]):
        """Send clarification requests to transcription agent via A2A."""
        for question in clarifications:
            self.protocol.request_clarification(
                from_agent=self.name,
                to_agent="transcription_agent",
                question=question,
            )

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

        # Autonomous action: send clarification requests if needed
        clarifications = result.get("clarification_needed", [])
        if clarifications:
            self._send_clarification_requests(clarifications)

        return message.reply(payload={"legal_analysis": result}, sender=self.name)
